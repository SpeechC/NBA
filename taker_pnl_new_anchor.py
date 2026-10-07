"""Taker P&L per strategy with the NEW bounds-only anchor. 2025-26.

Reproduces the LIVE configuration exactly as it now stands:
  * price paid is the ASK, fee charged              (take=True default, 2a86820)
  * (mu, sigma) from the EXECUTABLE BOUNDS only     (fit_ladder, 77879a6)
  * reference line per strategy, as signals() sets it:
        crewshock, final7   ref = None -> the Kalshi ladder centre
        move                ref = the captured sportsbook OPENER
  * stale-reference drift guard, max-edge rung, MIN_EDGE and the price band
  * settled against the actual final total

NOTE on the drift guard: for crewshock and final7 the reference IS mu_mkt, so
drift is identically zero and the guard cannot fire. That is correct -- the
guard exists for the opener-settled pair, whose reference was captured hours
earlier and can go stale.

BOOKS: crewshock and final7 settle vs the CLOSE and fill late, so the pregame
snapshot is the right book and covers the full season. move settles vs the
OPENER and fills 09:00 ET, so its right book is the 1-minute candle
reconstruction -- which exists for only 54 events, hence a tiny n.

PACEGAP IS NOT REPLAYED. Its signal is E_pace from the frozen engine; there is
no per-game 2025-26 export (checked: no CSV in the repo carries an E_pace
column, and pace_signal.py writes none), so reconstructing it means running
frozen_models walk-forward across the season. Stated, not approximated.
"""
import sys, sqlite3, numpy as np, pandas as pd
sys.path.insert(0, '.')
sys.path.insert(0, '/mnt/d/Kalshi/nba')
from prepare_data import read_master, season_label
import nba_live_trader as T
import nba_kalshi as NK

TOT = '/home/dpope/data/kalshi_local/kalshi_nba_totals.sqlite'
CAND = '/home/dpope/data/kalshi_local/kalshi_nba_candles.sqlite'
ABBR = {'ATL': 'Atlanta', 'BOS': 'Boston', 'BKN': 'Brooklyn', 'CHA': 'Charlotte',
        'CHI': 'Chicago', 'CLE': 'Cleveland', 'DAL': 'Dallas', 'DEN': 'Denver',
        'DET': 'Detroit', 'GSW': 'Golden State', 'HOU': 'Houston', 'IND': 'Indiana',
        'LAC': 'LA Clippers', 'LAL': 'LA Lakers', 'MEM': 'Memphis', 'MIA': 'Miami',
        'MIL': 'Milwaukee', 'MIN': 'Minnesota', 'NOP': 'New Orleans', 'NYK': 'New York',
        'OKC': 'Oklahoma City', 'ORL': 'Orlando', 'PHI': 'Philadelphia', 'PHX': 'Phoenix',
        'POR': 'Portland', 'SAC': 'Sacramento', 'SAS': 'San Antonio', 'TOR': 'Toronto',
        'UTA': 'Utah', 'WAS': 'Washington'}
CFG = {'crewshock': dict(hit=0.5421, ref='kalshi', book='pregame', sides=('OVER',)),
       'final7':    dict(hit=0.5529, ref='kalshi', book='pregame', sides=('OVER',)),
       'move':      dict(hit=0.5344, ref='open',   book='0900',    sides=('OVER',))}
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
S = d[d.season == 2025]

cw = pd.read_csv('crewshock_walkforward_bets.csv')
cw = cw[cw.season == 2025].copy()
cw['ds'] = pd.to_datetime(cw.date).dt.strftime('%Y-%m-%d')
mv = pd.read_csv('/mnt/c/NBA2/move_signal_states.csv')
mv = mv[(mv.SEASON == 2025) & mv.MOVE_COMBINED_OOS.notna()].copy()
mv['gid'] = mv['GAME-ID'].astype(str).str.replace(r'\.0$', '', regex=True)
mv = mv[mv.MOVE_COMBINED_OOS.abs() >= 1.0].merge(S[['gid', 'ds', 'h', 'r']], on='gid')
mv['dir'] = np.where(mv.MOVE_COMBINED_OOS > 0, 'OVER', 'UNDER')
SIG = {'crewshock': cw.rename(columns={'TEAM_H': 'h', 'TEAM_R': 'r'})[['ds', 'h', 'r']].assign(dir='OVER'),
       'final7': S[S.days_left <= 7][['ds', 'h', 'r']].assign(dir='OVER'),
       'move': mv[['ds', 'h', 'r', 'dir']]}


def pregame_book():
    con = sqlite3.connect('file:' + TOT + '?mode=ro', uri=True)
    b = pd.read_sql("""SELECT m.event_ticker ev, m.ticker, m.floor_strike K,
                              m.pregame_yes_bid bb, m.pregame_yes_ask aa,
                              e.game_date ds, e.away_team, e.home_team
                       FROM markets m JOIN events e USING(event_ticker)
                       WHERE m.pregame_yes_bid IS NOT NULL
                         AND m.pregame_yes_ask IS NOT NULL
                         AND m.floor_strike IS NOT NULL""", con)
    con.close()
    return b


def book_0900():
    con = sqlite3.connect('file:' + CAND + '?mode=ro', uri=True)
    c = pd.read_sql("""SELECT event_ticker ev, ticker, end_period_ts ts, game_date ds,
                              strike_label K, yes_bid_close bb, yes_ask_close aa
                       FROM candles WHERE period_interval=1""", con)
    mk = pd.read_sql("SELECT DISTINCT ticker, floor_strike FROM markets", con)
    con.close()
    c = c.merge(mk, on='ticker', how='left')
    c['K'] = c.floor_strike.fillna(c.K)
    c = c.dropna(subset=['K', 'bb', 'aa'])
    tsu = pd.to_datetime(c.ts, unit='s', utc=True)
    c = c[(tsu.dt.strftime('%Y-%m-%d') == c.ds) & (tsu.dt.hour <= 13)]
    c = c.sort_values('ts').groupby(['ev', 'ticker'], as_index=False).last()
    con = sqlite3.connect('file:' + TOT + '?mode=ro', uri=True)
    em = pd.read_sql("SELECT DISTINCT event_ticker ev, away_team, home_team FROM events", con)
    con.close()
    return c.merge(em, on='ev', how='left')


BOOKS = {}
for nm, fn in (('pregame', pregame_book), ('0900', book_0900)):
    b = fn()
    b['h'], b['r'] = b.home_team.map(ABBR), b.away_team.map(ABBR)
    b['L'], b['U'] = b.bb / 100.0, b.aa / 100.0
    BOOKS[nm] = b
    print(f"book {nm:8s}: {b.ev.nunique()} events, {len(b)} rungs")


def replay(strat):
    c = CFG[strat]
    j = SIG[strat].merge(BOOKS[c['book']], on=['ds', 'h', 'r'], how='inner')
    out = []
    for (ev, ds_, h, r), g in j.groupby(['ev', 'ds', 'h', 'r']):
        g = g.sort_values('K')
        m = S[(S.ds == ds_) & (S.h == h) & (S.r == r)]
        if m.empty or len(g) < 4:
            continue
        pts = float(m.actual.iloc[0])
        rungs = [dict(strike=float(k), ticker=t, yes_bid=float(x), yes_ask=float(y),
                      yes_bid_size=999.0, yes_ask_size=999.0,
                      ranges=[(0.0, 1.0, 0.01)], status='active')
                 for k, t, x, y in zip(g.K, g.ticker, g.L, g.U)]
        mu_mkt, sg, feas = T.fit_ladder_detail(rungs)     # BOUNDS ONLY
        if mu_mkt is None:
            continue
        ref = mu_mkt if c['ref'] == 'kalshi' else float(m['open'].iloc[0])
        if not np.isfinite(ref):
            continue
        dirn = g.dir.iloc[0]
        signed = c['delta'] if dirn == 'OVER' else -c['delta']
        drift = mu_mkt - ref
        against = -drift if dirn == 'OVER' else drift
        if against > abs(c['delta']):
            out.append(dict(traded=False, why='drift', feas=feas)); continue
        cands = T.candidates(rungs, ref + signed, sg, (dirn,))
        ok = [x for x in cands
              if T.gate(x, dict(day_contracts=0, day_notional=0.0, game_contracts=0)) is None]
        if not ok:
            out.append(dict(traded=False, why='gate', feas=feas)); continue
        x = ok[0]
        fee = NK.fee(x['price'], 1)
        won = (pts > x['strike']) if dirn == 'OVER' else (pts < x['strike'])
        out.append(dict(traded=True, feas=feas, dir=dirn, ask=x['price'],
                        strike=x['strike'], off=x['strike'] - ref, won=bool(won),
                        pnl=(1 - x['price'] - fee) if won else (-x['price'] - fee),
                        outlay=x['price'] + fee))
    return pd.DataFrame(out)


print("\n" + "=" * 94)
print("TAKER P&L, 2025-26, NEW BOUNDS-ONLY ANCHOR -- settled on the actual total")
print("=" * 94)
print(f"  {'strategy':>10}{'ref':>9}{'book':>9}{'sig':>6}{'traded':>8}{'hit%':>8}"
      f"{'ask':>7}{'off':>7}{'P&L':>9}{'outlay':>9}{'ROI':>9}{'feas%':>7}")
tot_p = tot_o = tot_n = 0
for strat in ('crewshock', 'final7', 'move'):
    R = replay(strat)
    t = R[R.traded] if len(R) else R
    n_sig = len(SIG[strat][SIG[strat].dir.isin(CFG[strat]['sides'])])
    if not len(t):
        print(f"  {strat:>10}{CFG[strat]['ref']:>9}{CFG[strat]['book']:>9}"
              f"{n_sig:>6}{0:>8}   -- none traded --")
        continue
    tot_p += t.pnl.sum(); tot_o += t.outlay.sum(); tot_n += len(t)
    print(f"  {strat:>10}{CFG[strat]['ref']:>9}{CFG[strat]['book']:>9}{n_sig:>6}"
          f"{len(t):>8}{100*t.won.mean():>7.2f}%{t.ask.mean():>7.3f}"
          f"{t.off.mean():>+7.2f}{t.pnl.sum():>+9.2f}{t.outlay.sum():>9.2f}"
          f"{100*t.pnl.sum()/t.outlay.sum():>+8.2f}%{100*R.feas.mean():>6.1f}%")
print(f"  {'pacegap':>10}{'open':>9}{'0900':>9}{'--':>6}{'--':>8}"
      f"   NOT REPLAYED (no per-game E_pace export)")
print("  " + "-" * 92)
print(f"  {'TOTAL':>10}{'':>18}{'':>6}{tot_n:>8}{'':>8}{'':>7}{'':>7}"
      f"{tot_p:>+9.2f}{tot_o:>9.2f}{100*tot_p/tot_o:>+8.2f}%")
print("\n  'off' is the traded strike minus the reference line, in points.")
print("  'feas%' is how often the bounds identified set was non-empty; the rest")
print("  used the hinge-loss fallback, which keeps the anchor always defined.")
print("\n  SCALE CAVEAT: move's n is tiny because the 09:00 ET book exists for")
print("  only 54 events. crewshock and final7 cover the full season.")
