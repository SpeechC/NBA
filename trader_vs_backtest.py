"""Does the trader place the bet the backtest measured? Measured, not argued.

THE BACKTEST is: for every signal, stake $100 at -110 on the strategy's own
LINE, win if the actual total beats that line. No selection, no gate, no rung.

THE TRADER does something materially different. This counts the divergences on
real 2025-26 boards and prices the two side by side:

  A  TRADER AS CONFIGURED   max-edge rung, MIN_EDGE, price band, sigma-distance,
                            book-size, drift guard, one-trade-per-game
  B  BACKTEST-FAITHFUL      the nearest-line rung, every signal, gates bypassed
                            except a sane price band -- the closest thing Kalshi
                            can offer to "bet the line, always"

and reports the funnel: exactly how many signals each gate removes, so the size
of the deviation is visible rather than asserted.
"""
import sys, sqlite3, collections
import numpy as np, pandas as pd
sys.path.insert(0, '.')
sys.path.insert(0, '/mnt/d/Kalshi/nba')
from prepare_data import read_master, season_label
import nba_live_trader as T
import nba_kalshi as NK

TOT = '/home/dpope/data/kalshi_local/kalshi_nba_totals.sqlite'
WIN, LOSE = 100.0 / 1.1, -100.0
ABBR = {'ATL': 'Atlanta', 'BOS': 'Boston', 'BKN': 'Brooklyn', 'CHA': 'Charlotte',
        'CHI': 'Chicago', 'CLE': 'Cleveland', 'DAL': 'Dallas', 'DEN': 'Denver',
        'DET': 'Detroit', 'GSW': 'Golden State', 'HOU': 'Houston', 'IND': 'Indiana',
        'LAC': 'LA Clippers', 'LAL': 'LA Lakers', 'MEM': 'Memphis', 'MIA': 'Miami',
        'MIL': 'Milwaukee', 'MIN': 'Minnesota', 'NOP': 'New Orleans', 'NYK': 'New York',
        'OKC': 'Oklahoma City', 'ORL': 'Orlando', 'PHI': 'Philadelphia', 'PHX': 'Phoenix',
        'POR': 'Portland', 'SAC': 'Sacramento', 'SAS': 'San Antonio', 'TOR': 'Toronto',
        'UTA': 'Utah', 'WAS': 'Washington'}
CFG = {'crewshock': dict(hit=0.5421, line='close'), 'final7': dict(hit=0.5529, line='close')}
for v in CFG.values():
    v['delta'] = T.delta_points(v['hit'])

raw = read_master(verbose=False)
raw['lbl'] = season_label(raw).astype(str)
d = raw[raw['lbl'].str.contains('Regular Season', na=False)].copy()
d['date'] = pd.to_datetime(d['DATE'], errors='coerce')
d['close'] = pd.to_numeric(d['CLOSING TOTAL_H'], errors='coerce')
d['actual'] = pd.to_numeric(d['PTS_H'], errors='coerce') + pd.to_numeric(d['PTS_R'], errors='coerce')
d = d.dropna(subset=['date', 'close', 'actual'])
d = d[d['close'].between(150, 300)].copy()
d['season'] = d['lbl'].str.extract(r'(\d{4})')[0].astype(int)
d['days_left'] = (d.groupby('lbl')['date'].transform('max') - d['date']).dt.days
d['ds'] = d.date.dt.strftime('%Y-%m-%d')
d['h'], d['r'] = d['TEAM_H'].astype(str), d['TEAM_R'].astype(str)
S = d[d.season == 2025]

cw = pd.read_csv('crewshock_walkforward_bets.csv')
cw = cw[cw.season == 2025].copy()
cw['ds'] = pd.to_datetime(cw.date).dt.strftime('%Y-%m-%d')
SIG = {'crewshock': cw.rename(columns={'TEAM_H': 'h', 'TEAM_R': 'r'})[['ds', 'h', 'r']],
       'final7': S[S.days_left <= 7][['ds', 'h', 'r']]}

con = sqlite3.connect('file:' + TOT + '?mode=ro', uri=True)
bk = pd.read_sql("""SELECT m.event_ticker ev, m.ticker, m.floor_strike K,
                           m.pregame_yes_bid bb, m.pregame_yes_ask aa,
                           e.game_date ds, e.away_team, e.home_team
                    FROM markets m JOIN events e USING(event_ticker)
                    WHERE m.pregame_yes_bid IS NOT NULL
                      AND m.pregame_yes_ask IS NOT NULL
                      AND m.floor_strike IS NOT NULL""", con)
con.close()
bk['h'], bk['r'] = bk.home_team.map(ABBR), bk.away_team.map(ABBR)
bk['L'], bk['U'] = bk.bb / 100.0, bk.aa / 100.0

print("=" * 96)
print("WHERE THE TRADER DEVIATES FROM THE BACKTEST -- 2025-26 funnel")
print("=" * 96)
res = {}
for strat in ('crewshock', 'final7'):
    c = CFG[strat]
    j = SIG[strat].merge(bk, on=['ds', 'h', 'r'], how='inner')
    why = collections.Counter()
    A, B = [], []
    for (ev, ds_, h, r), g in j.groupby(['ev', 'ds', 'h', 'r']):
        g = g.sort_values('K')
        m = S[(S.ds == ds_) & (S.h == h) & (S.r == r)]
        if m.empty:
            why['no master row'] += 1; continue
        if len(g) < 4:
            why['ladder < 4 rungs'] += 1; continue
        close, pts = float(m.close.iloc[0]), float(m.actual.iloc[0])
        rungs = [dict(strike=float(k), ticker=t, yes_bid=float(x), yes_ask=float(y),
                      yes_bid_size=999.0, yes_ask_size=999.0,
                      ranges=[(0.0, 1.0, 0.01)], status='active')
                 for k, t, x, y in zip(g.K, g.ticker, g.L, g.U)]
        mu, sg, _ = T.fit_ladder_detail(rungs)
        if mu is None:
            why['no ladder fit'] += 1; continue
        ref = mu
        if (ref - mu) > abs(c['delta']):
            why['drift guard'] += 1; continue
        cands = T.candidates(rungs, ref + c['delta'], sg, ('OVER',))
        st = dict(day_contracts=0, day_notional=0.0, game_contracts=0)
        gated = [x for x in cands if T.gate(x, st) is None]
        inband = [x for x in cands if T.MIN_PRICE <= x['price'] <= T.MAX_PRICE]

        # B -- backtest-faithful: nearest-line rung, no MIN_EDGE, always trade
        if inband:
            x = min(inband, key=lambda q: abs(q['strike'] - close))
            fee = NK.fee(x['price'], 1); won = pts > x['strike']
            B.append(dict(hit=int(won), off=x['strike'] - close,
                          pnl=(1 - x['price'] - fee) if won else (-x['price'] - fee),
                          outlay=x['price'] + fee))
        else:
            why['no in-band rung (both)'] += 1

        # A -- trader as configured
        if not gated:
            if cands and max(q['edge'] for q in cands) < T.MIN_EDGE:
                why['MIN_EDGE'] += 1
            else:
                why['other gate'] += 1
            continue
        x = gated[0]
        fee = NK.fee(x['price'], 1); won = pts > x['strike']
        A.append(dict(hit=int(won), off=x['strike'] - close,
                      pnl=(1 - x['price'] - fee) if won else (-x['price'] - fee),
                      outlay=x['price'] + fee))

    # the backtest itself
    bb = SIG[strat].merge(S[['ds', 'h', 'r', 'close', 'actual']], on=['ds', 'h', 'r'])
    bb = bb[bb.actual != bb.close]
    bwon = (bb.actual > bb.close)
    bpnl = np.where(bwon, WIN, LOSE)
    A, B = pd.DataFrame(A), pd.DataFrame(B)
    res[strat] = (A, B)
    print(f"\n  {strat.upper()}   {len(SIG[strat])} signals -> {len(j.groupby(['ev','ds','h','r']))} "
          f"with a Kalshi board")
    for k, v in why.most_common():
        print(f"      declined: {k:<24} {v:>4}")
    print(f"    {'':<34}{'n':>5}{'hit%':>8}{'mean off':>10}{'ROI':>9}")
    print(f"    {'BACKTEST  bet the line at -110':<34}{len(bb):>5}"
          f"{100*bwon.mean():>7.2f}%{0.0:>+10.2f}{100*bpnl.sum()/(100*len(bb)):>+8.2f}%")
    if len(B):
        print(f"    {'B  Kalshi, nearest-line, always':<34}{len(B):>5}"
              f"{100*B.hit.mean():>7.2f}%{B.off.mean():>+10.2f}"
              f"{100*B.pnl.sum()/B.outlay.sum():>+8.2f}%")
    if len(A):
        print(f"    {'A  TRADER as configured':<34}{len(A):>5}"
              f"{100*A.hit.mean():>7.2f}%{A.off.mean():>+10.2f}"
              f"{100*A.pnl.sum()/A.outlay.sum():>+8.2f}%")

print("\n" + "=" * 96)
print("THE DIVERGENCES, AND WHETHER EACH HAS A BACKTEST")
print("=" * 96)
rows = [
 ("rung instead of line",      "FORCED",   "3-pt grid; nearest rung is 0.69 pts off on average"),
 ("no pushes",                 "FORCED",   "every strike ends .5"),
 ("1 contract vs $100 flat",   "FORCED",   "changes the ROI denominator, not the bet"),
 ("reference = Kalshi mu",     "REASONED", "the close is unknowable at 17:00; mu IS the close (0.001 pts)"),
 ("max-edge rung selection",   "NO BACKTEST", "the +24% came from a synthetic board where the model was right by construction"),
 ("MIN_EDGE = 0.01",           "NO BACKTEST", "the backtest bets every signal"),
 ("price band 0.12-0.88",      "NO BACKTEST", "no analogue"),
 ("MAX_SIGMA_DIST = 1.1",      "NO BACKTEST", "no analogue"),
 ("MIN_BOOK_SIZE = 5",         "NO BACKTEST", "no analogue; inert until the taker flip"),
 ("drift guard",               "REASONED", "declines when the market moved past our own delta"),
 ("one trade per game",        "REASONED", "the backtest tables double-count 104 games"),
 ("OVER only (NO disabled)",   "CONFIG",   "now verified, so this one is closeable"),
]
print(f"  {'divergence':<28}{'basis':<14}note")
for a, b, cnote in rows:
    print(f"  {a:<28}{b:<14}{cnote}")
