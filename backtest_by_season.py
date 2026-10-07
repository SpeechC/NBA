"""By-season backtest for all four live models: book and Kalshi taker.

*** KALSHI HAS EXACTLY ONE SEASON OF DATA. *** Books exist only for 2025-26, so
the Kalshi column cannot be shown by season for 2017-2024 and never will be --
settled markets are purged from the API and were never collected. Shown as a
single 2025-26 row, not an empty grid pretending otherwise.

BOOK is -110 flat $100, graded against each strategy's own settlement line --
the CLOSE for crewshock/final7, the OPENER for move/pacegap. A sportsbook price
is take-it-or-leave-it, so -110 already IS the taker price there; the
taker/maker distinction only exists on Kalshi.

KALSHI is the live configuration: max-edge rung at the ASK, fee, (mu, sigma)
from executable bounds, reference per strategy, drift guard, MIN_EDGE, price
band, settled on the actual.

Pushes are dropped from the book (a no-action; impossible on Kalshi where every
strike ends .5).
"""
import sys, os, sqlite3
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
CFG = {'crewshock': dict(hit=0.5421, line='close', ref='kalshi'),
       'final7':    dict(hit=0.5529, line='close', ref='kalshi'),
       'move':      dict(hit=0.5344, line='open',  ref='open'),
       'pacegap':   dict(hit=0.5259, line='open',  ref='open')}
for v in CFG.values():
    v['delta'] = T.delta_points(v['hit'])

raw = read_master(verbose=False)
raw['lbl'] = season_label(raw).astype(str)
d = raw[raw['lbl'].str.contains('Regular Season', na=False)].copy()
d['date'] = pd.to_datetime(d['DATE'], errors='coerce')
d['close'] = pd.to_numeric(d['CLOSING TOTAL_H'], errors='coerce')
d['open'] = pd.to_numeric(d['OPENING TOTAL_H'], errors='coerce')
d['actual'] = pd.to_numeric(d['PTS_H'], errors='coerce') + pd.to_numeric(d['PTS_R'], errors='coerce')
d['gid'] = d['GAME-ID'].astype(str).str.replace(r'\.0$', '', regex=True)
d = d.dropna(subset=['date', 'close', 'actual'])
d = d[d['close'].between(150, 300)].copy()
d['season'] = d['lbl'].str.extract(r'(\d{4})')[0].astype(int)
d['days_left'] = (d.groupby('lbl')['date'].transform('max') - d['date']).dt.days
d['ds'] = d.date.dt.strftime('%Y-%m-%d')
d['h'], d['r'] = d['TEAM_H'].astype(str), d['TEAM_R'].astype(str)

# ------------------------------------------------------------------ signals
SIG = {}
cw = pd.read_csv('crewshock_walkforward_bets.csv')
cw['ds'] = pd.to_datetime(cw.date).dt.strftime('%Y-%m-%d')
SIG['crewshock'] = cw.rename(columns={'TEAM_H': 'h', 'TEAM_R': 'r'})[['ds', 'h', 'r']].assign(dir='OVER')
SIG['final7'] = d[d.days_left <= 7][['ds', 'h', 'r']].assign(dir='OVER')
mv = pd.read_csv('/mnt/c/NBA2/move_signal_states.csv')
mv = mv[mv.MOVE_COMBINED_OOS.notna()].copy()
mv['gid'] = mv['GAME-ID'].astype(str).str.replace(r'\.0$', '', regex=True)
mv = mv[mv.MOVE_COMBINED_OOS.abs() >= 1.0].merge(d[['gid', 'ds', 'h', 'r']], on='gid')
SIG['move'] = mv.assign(dir=np.where(mv.MOVE_COMBINED_OOS > 0, 'OVER', 'UNDER'))[['ds', 'h', 'r', 'dir']]
PGF = 'pacegap_backfill_all.csv'
if os.path.exists(PGF):
    pg = pd.read_csv(PGF)
    pg = pg[pg.bet_flag == 1]
    SIG['pacegap'] = pg.rename(columns={'game_date': 'ds', 'TEAM_H': 'h', 'TEAM_R': 'r'}) \
        .assign(dir=np.where(pg.side.values > 0, 'OVER', 'UNDER'))[['ds', 'h', 'r', 'dir']]

# ------------------------------------------------------------------ book
def book_rows(strat, over_only=False):
    c = CFG[strat]; s = SIG[strat]
    if over_only:
        s = s[s.dir == 'OVER']
    j = s.merge(d[['ds', 'h', 'r', 'season', c['line'], 'actual']],
                on=['ds', 'h', 'r'], how='inner').dropna(subset=[c['line']])
    j = j[j.actual != j[c['line']]]
    j = j.assign(won=np.where(j.dir == 'OVER', j.actual > j[c['line']],
                              j.actual < j[c['line']]))
    j['pnl'] = np.where(j.won, WIN, LOSE)
    return j


print("=" * 100)
print("BOOK -- sportsbook -110, $100 flat, by season  (a sportsbook price IS the taker price)")
print("=" * 100)
seasons = sorted(d.season.unique())
for strat in ('crewshock', 'final7', 'move', 'pacegap'):
    if strat not in SIG:
        print(f"\n  {strat.upper()}: backfill still running")
        continue
    b = book_rows(strat)
    bo = book_rows(strat, over_only=True)
    two = CFG[strat]['line'] == 'open'
    print(f"\n  {strat.upper()}   ({'OVER/UNDER' if two else 'OVER only'})")
    hdr = f"    {'season':>8}{'bets':>7}{'hit%':>8}{'P&L':>9}{'ROI':>9}"
    if two:
        hdr += f"  |{'OVER-only n':>12}{'hit%':>8}{'ROI':>9}"
    print(hdr)
    for s in seasons:
        g = b[b.season == s]
        if not len(g):
            continue
        line = (f"    {s:>8}{len(g):>7}{100*g.won.mean():>7.2f}%{g.pnl.sum():>+9.0f}"
                f"{100*g.pnl.sum()/(100*len(g)):>+8.2f}%")
        if two:
            go = bo[bo.season == s]
            line += (f"  |{len(go):>12}{100*go.won.mean():>7.2f}%"
                     f"{100*go.pnl.sum()/(100*len(go)):>+8.2f}%" if len(go) else
                     f"  |{'--':>12}{'--':>8}{'--':>9}")
        print(line)
    tot = f"    {'ALL':>8}{len(b):>7}{100*b.won.mean():>7.2f}%{b.pnl.sum():>+9.0f}" \
          f"{100*b.pnl.sum()/(100*len(b)):>+8.2f}%"
    if two:
        tot += (f"  |{len(bo):>12}{100*bo.won.mean():>7.2f}%"
                f"{100*bo.pnl.sum()/(100*len(bo)):>+8.2f}%")
    print(tot)

# ------------------------------------------------------------------ Kalshi
print("\n" + "=" * 100)
print("KALSHI TAKER -- 2025-26 ONLY. Books do not exist for any earlier season and")
print("never will: settled markets are purged from the API and were not collected.")
print("=" * 100)
S25 = d[d.season == 2025]
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

print(f"  {'strategy':>10}{'book':>10}{'sig':>6}{'traded':>8}{'hit%':>8}"
      f"{'P&L':>9}{'outlay':>9}{'ROI':>9}")
for strat in ('crewshock', 'final7', 'move', 'pacegap'):
    if strat not in SIG:
        print(f"  {strat:>10}  backfill still running"); continue
    c = CFG[strat]
    s = SIG[strat]
    s = s[s.dir == 'OVER']                     # pregame book; UNDER needs 09:00
    j = s.merge(bk, on=['ds', 'h', 'r'], how='inner')
    nsig = len(s.merge(S25[['ds', 'h', 'r']], on=['ds', 'h', 'r']))
    out = []
    for (ev, ds_, h, r), g in j.groupby(['ev', 'ds', 'h', 'r']):
        g = g.sort_values('K')
        m = S25[(S25.ds == ds_) & (S25.h == h) & (S25.r == r)]
        if m.empty or len(g) < 4:
            continue
        pts = float(m.actual.iloc[0])
        rungs = [dict(strike=float(k), ticker=t, yes_bid=float(x), yes_ask=float(y),
                      yes_bid_size=999.0, yes_ask_size=999.0,
                      ranges=[(0.0, 1.0, 0.01)], status='active')
                 for k, t, x, y in zip(g.K, g.ticker, g.L, g.U)]
        mu, sg, _ = T.fit_ladder_detail(rungs)
        if mu is None:
            continue
        ref = mu if c['ref'] == 'kalshi' else float(m['open'].iloc[0])
        if not np.isfinite(ref) or (ref - mu) > abs(c['delta']):
            continue
        cand = [x for x in T.candidates(rungs, ref + c['delta'], sg, ('OVER',))
                if T.gate(x, dict(day_contracts=0, day_notional=0.0, game_contracts=0)) is None]
        if not cand:
            continue
        x = cand[0]; fee = NK.fee(x['price'], 1); won = pts > x['strike']
        out.append(dict(hit=int(won), pnl=(1 - x['price'] - fee) if won else (-x['price'] - fee),
                        outlay=x['price'] + fee))
    R = pd.DataFrame(out)
    lbl = 'pregame' if c['ref'] == 'kalshi' else 'pregame*'
    if not len(R):
        print(f"  {strat:>10}{lbl:>10}{nsig:>6}{0:>8}   -- none traded --")
        continue
    print(f"  {strat:>10}{lbl:>10}{nsig:>6}{len(R):>8}{100*R.hit.mean():>7.2f}%"
          f"{R.pnl.sum():>+9.2f}{R.outlay.sum():>9.2f}"
          f"{100*R.pnl.sum()/R.outlay.sum():>+8.2f}%")
print("\n  * move and pacegap settle against the OPENER and fill 09:00 ET, so the")
print("    pregame (near-close) book is the WRONG book for them -- shown only to")
print("    make the sample visible. Their correct 09:00 book covers 54 events.")
print("  OVER-only throughout: the pregame snapshot cannot price the UNDER leg at")
print("    the right time of day for the opener-settled pair.")
