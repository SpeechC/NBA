"""HISTORICAL taker P&L, ROI and hit rate per strategy -- 2025-26 only.

WHY ONE SEASON. The team-stats database carries historical LINES back to 2017
but no bid/ask. Kalshi books exist only for 2025-26, so a taker replay -- which
by definition needs an executable ask -- cannot reach any earlier season. The
8-season records in MONITOR_SEASON_PNL.md are sportsbook results at -110 and
are NOT comparable; they are shown beside these only as context.

WHAT IS REPLAYED. Each strategy's real 2025-26 signals, re-priced through the
trader's own candidates() and gate() with take=True (now the default), buying
the max-edge rung AT THE ASK, paying the Kalshi fee, and SETTLED AGAINST THE
ACTUAL FINAL TOTAL. These are realised outcomes, not expected values.

BOOK CHOICE MATTERS AND IS NOT UNIFORM:
  crewshock, final7  settle vs the CLOSE and fill late  -> pregame_* snapshot
                     is the right book, and it covers the full season.
  move               settles vs the OPENER and fills 09:00 ET -> the right book
                     is the 09:00 candle reconstruction, which exists for only
                     54 events. Reported on both, with the near-close figure
                     labelled as the wrong book.
  pacegap            NOT INCLUDED. Its signal is E_pace from the frozen engine
                     and no per-game 2025-26 export exists; reconstructing it
                     means running frozen_models walk-forward over the season.
                     Stated rather than approximated.

UNDER legs need the NO side, which is disabled (NBA_NO_SIDE_VERIFIED unset), so
the live configuration is OVER-only. Both are shown for move.
"""
import sys, sqlite3, numpy as np, pandas as pd
from scipy.stats import norm

sys.path.insert(0, '/mnt/d/Kalshi/nba')
import nba_live_trader as T
import nba_kalshi as NK

TOT = '/home/dpope/data/kalshi_local/kalshi_nba_totals.sqlite'
CAND = '/home/dpope/data/kalshi_local/kalshi_nba_candles.sqlite'
SIG_GRID = np.arange(9.0, 30.001, 0.05)
SLACK, BIG = 0.005, 1e9
ABBR = {'ATL': 'Atlanta', 'BOS': 'Boston', 'BKN': 'Brooklyn', 'CHA': 'Charlotte',
        'CHI': 'Chicago', 'CLE': 'Cleveland', 'DAL': 'Dallas', 'DEN': 'Denver',
        'DET': 'Detroit', 'GSW': 'Golden State', 'HOU': 'Houston', 'IND': 'Indiana',
        'LAC': 'LA Clippers', 'LAL': 'LA Lakers', 'MEM': 'Memphis', 'MIA': 'Miami',
        'MIL': 'Milwaukee', 'MIN': 'Minnesota', 'NOP': 'New Orleans', 'NYK': 'New York',
        'OKC': 'Oklahoma City', 'ORL': 'Orlando', 'PHI': 'Philadelphia', 'PHX': 'Phoenix',
        'POR': 'Portland', 'SAC': 'Sacramento', 'SAS': 'San Antonio', 'TOR': 'Toronto',
        'UTA': 'Utah', 'WAS': 'Washington'}
DELTA = {k: T.delta_points(v) for k, v in
         (('crewshock', 0.5421), ('final7', 0.5529), ('move', 0.5344))}

# ------------------------------------------------------------------ master
raw = pd.read_csv('/mnt/c/NBA2/dfMaster_OT_2017-2026.csv', low_memory=False)
ds = raw['DATASET_H'].fillna(raw['BIGDATABALL\nDATASET_H']).astype(str)
M = pd.DataFrame({
    'date': pd.to_datetime(raw['DATE'], errors='coerce'),
    'gid': raw['GAME-ID'].astype(str).str.replace(r'\.0$', '', regex=True),
    'h': raw['TEAM_H'].astype(str), 'r': raw['TEAM_R'].astype(str),
    'close': pd.to_numeric(raw['CLOSING TOTAL_H'], errors='coerce'),
    'open': pd.to_numeric(raw['OPENING TOTAL_H'], errors='coerce'),
    'pts': pd.to_numeric(raw['TOTAL_PTS'], errors='coerce'),
    # 'Play-In' is a SEPARATE label from 'Playoffs' in DATASET_H. Matching only
    # 'Playoff' lets the 6 play-in games through, which pushed the 2025-26
    # "last regular-season date" from 2026-04-12 to 2026-04-17 and moved final7's
    # whole 7-day window -- 21 signals instead of the documented 69. The live
    # trader takes NBA_LAST_REGULAR from the environment, so the same mistake
    # there would bet the wrong week.
    'playoff': ds.str.contains('Playoff|Play-In', case=False,
                               regex=True)}).dropna(subset=['date', 'pts'])
M['season'] = np.where(M.date.dt.month >= 8, M.date.dt.year, M.date.dt.year - 1)
M['ds'] = M.date.dt.strftime('%Y-%m-%d')
S25 = M[M.season == 2025]
last_reg = S25[~S25.playoff].date.max()
print(f"2025-26: {len(S25)} games, last regular-season date {last_reg.date()}")

# ------------------------------------------------------------------ signals
sig = {}

cw = pd.read_csv('crewshock_walkforward_bets.csv')
cw = cw[cw.season == 2025].copy()
cw['ds'] = pd.to_datetime(cw.date).dt.strftime('%Y-%m-%d')
sig['crewshock'] = cw.assign(dir='OVER', line='close')[['ds', 'TEAM_H', 'TEAM_R', 'dir', 'line']] \
    .rename(columns={'TEAM_H': 'h', 'TEAM_R': 'r'})
print(f"  crewshock signals 2025-26: {len(cw)}")

f7 = S25[(~S25.playoff) & (S25.date > last_reg - pd.Timedelta(days=7))]
sig['final7'] = f7.assign(dir='OVER', line='close')[['ds', 'h', 'r', 'dir', 'line']]
print(f"  final7 signals 2025-26:    {len(f7)}  "
      f"({(last_reg - pd.Timedelta(days=6)).date()} .. {last_reg.date()})")

mv = pd.read_csv('/mnt/c/NBA2/move_signal_states.csv')
mv = mv[(mv.SEASON == 2025) & mv.MOVE_COMBINED_OOS.notna()].copy()
mv = mv[mv.MOVE_COMBINED_OOS.abs() >= 1.0]            # THRESH_PRIMARY, frozen
mv['gid'] = mv['GAME-ID'].astype(str).str.replace(r'\.0$', '', regex=True)
mv = mv.merge(M[['gid', 'ds', 'h', 'r']], on='gid', how='inner')
mv['dir'] = np.where(mv.MOVE_COMBINED_OOS > 0, 'OVER', 'UNDER')
sig['move'] = mv.assign(line='open')[['ds', 'h', 'r', 'dir', 'line']]
print(f"  move signals 2025-26:      {len(mv)}  "
      f"(OVER {int((mv.dir=='OVER').sum())} / UNDER {int((mv.dir=='UNDER').sum())})")
print("  pacegap: NOT REPLAYED -- no per-game 2025-26 E_pace export exists")

# ------------------------------------------------------------------ books
def load_pregame():
    con = sqlite3.connect('file:' + TOT + '?mode=ro', uri=True)
    m = pd.read_sql("""SELECT m.event_ticker ev, m.ticker, m.floor_strike K,
                              m.pregame_yes_bid b, m.pregame_yes_ask a,
                              e.game_date, e.away_team, e.home_team
                       FROM markets m JOIN events e USING(event_ticker)
                       WHERE m.pregame_yes_bid IS NOT NULL
                         AND m.pregame_yes_ask IS NOT NULL
                         AND m.floor_strike IS NOT NULL""", con)
    con.close()
    m['L'], m['U'] = m.b / 100.0, m.a / 100.0
    m['h'], m['r'] = m.home_team.map(ABBR), m.away_team.map(ABBR)
    return m.rename(columns={'game_date': 'ds'})


def load_0900():
    con = sqlite3.connect('file:' + CAND + '?mode=ro', uri=True)
    c = pd.read_sql("""SELECT event_ticker ev, ticker, end_period_ts ts, game_date,
                              strike_label K, yes_bid_close b, yes_ask_close a
                       FROM candles WHERE period_interval=1""", con)
    mk = pd.read_sql("SELECT DISTINCT ticker, floor_strike FROM markets", con)
    con.close()
    c = c.merge(mk, on='ticker', how='left')
    c['K'] = c.floor_strike.fillna(c.K)
    c = c.dropna(subset=['K', 'b', 'a'])
    tsu = pd.to_datetime(c.ts, unit='s', utc=True)
    c = c[(tsu.dt.strftime('%Y-%m-%d') == c.game_date) & (tsu.dt.hour <= 13)]
    c = c.sort_values('ts').groupby(['ev', 'ticker'], as_index=False).last()
    con = sqlite3.connect('file:' + TOT + '?mode=ro', uri=True)
    em = pd.read_sql("SELECT DISTINCT event_ticker ev, away_team, home_team FROM events", con)
    con.close()
    c = c.merge(em, on='ev', how='left')
    c['L'], c['U'] = c.b / 100.0, c.a / 100.0
    c['h'], c['r'] = c.home_team.map(ABBR), c.away_team.map(ABBR)
    return c.rename(columns={'game_date': 'ds'})


def mu_sigma(K, Lo_, Up_):
    Lo = np.clip(Lo_ - SLACK, 1e-9, 1 - 1e-9); Up = np.clip(Up_ + SLACK, 1e-9, 1 - 1e-9)
    zL = np.where(np.isfinite(norm.ppf(1 - Lo)), norm.ppf(1 - Lo), BIG)
    zU = np.where(np.isfinite(norm.ppf(1 - Up)), norm.ppf(1 - Up), -BIG)
    lo = (K[None, :] - SIG_GRID[:, None] * zL[None, :]).max(axis=1)
    hi = (K[None, :] - SIG_GRID[:, None] * zU[None, :]).min(axis=1)
    ok = np.where(lo <= hi + 1e-9)[0]
    if len(ok) == 0:
        return None, T.SIGMA_REF
    i = ok[len(ok) // 2]
    return float((lo[i] + hi[i]) / 2.0), float(SIG_GRID[i])


def replay(strat, book, allow_under):
    s = sig[strat]
    if not allow_under:
        s = s[s.dir == 'OVER']
    j = s.merge(book, on=['ds', 'h', 'r'], how='inner')
    ref_col = s.line.iloc[0]
    out = []
    for (ev, ds_, h, r), g in j.groupby(['ev', 'ds', 'h', 'r']):
        g = g.sort_values('K')
        if len(g) < 4:
            continue
        mrow = M[(M.ds == ds_) & (M.h == h) & (M.r == r)]
        if mrow.empty or pd.isna(mrow[ref_col].iloc[0]):
            continue
        Lref, pts = float(mrow[ref_col].iloc[0]), float(mrow.pts.iloc[0])
        dirn = g.dir.iloc[0]
        mu_mkt, sg = mu_sigma(g.K.values, g.L.values, g.U.values)
        sgn = 1.0 if dirn == 'OVER' else -1.0
        if mu_mkt is not None and sgn * (mu_mkt - Lref) < -abs(DELTA[strat]):
            out.append(dict(ev=ev, traded=False, why='drift')); continue
        rungs = [dict(strike=float(k), ticker=t, yes_bid=float(bb), yes_ask=float(aa),
                      yes_bid_size=999.0, yes_ask_size=999.0,
                      ranges=[(0.0, 1.0, 0.01)], status='active')
                 for k, t, bb, aa in zip(g.K, g.ticker, g.L, g.U)]
        cands = T.candidates(rungs, Lref + sgn * DELTA[strat], sg, (dirn,))   # take=True
        st = dict(day_contracts=0, day_notional=0.0, game_contracts=0)
        ok = [x for x in cands if T.gate(x, st) is None]
        if not ok:
            out.append(dict(ev=ev, traded=False, why='gate')); continue
        x = ok[0]
        fee = NK.fee(x['price'], 1)
        won = (pts > x['strike']) if dirn == 'OVER' else (pts < x['strike'])
        out.append(dict(ev=ev, traded=True, dir=dirn, strike=x['strike'],
                        ask=x['price'], fee=fee, won=bool(won),
                        pnl=(1 - x['price'] - fee) if won else (-x['price'] - fee),
                        outlay=x['price'] + fee, sb_won=bool(pts > Lref) if dirn == 'OVER'
                        else bool(pts < Lref)))
    return pd.DataFrame(out)


pre, b09 = load_pregame(), load_0900()
print(f"\nbooks: pregame {pre.ev.nunique()} events | 09:00 ET {b09.ev.nunique()} events")

print("\n" + "=" * 92)
print("HISTORICAL TAKER RESULTS, 2025-26 -- settled against the actual final total")
print("=" * 92)
print(f"  {'strategy':>10s} {'book':>10s} {'sig':>5s} {'traded':>7s} {'hit%':>7s} "
      f"{'P&L':>9s} {'outlay':>8s} {'ROI':>8s} {'c/ct':>7s} {'SB hit%':>8s}")
rowsum = []
PLAN = [('crewshock', 'pregame (right)', pre, False),
        ('final7', 'pregame (right)', pre, False),
        ('move', '09:00 (right)', b09, False),
        ('move', 'pregame (WRONG)', pre, False),
        ('move', '09:00 +UNDER', b09, True)]
for strat, lbl, bk, au in PLAN:
    R = replay(strat, bk, au)
    t = R[R.traded] if len(R) else R
    n_sig = (sig[strat].dir == 'OVER').sum() if not au else len(sig[strat])
    if not len(t):
        print(f"  {strat:>10s} {lbl:>10s} {n_sig:5d} {0:7d}   -- no traded games --")
        continue
    pnl, out_ = t.pnl.sum(), t.outlay.sum()
    print(f"  {strat:>10s} {lbl:>16s} {n_sig:5d} {len(t):7d} {100*t.won.mean():6.2f}% "
          f"{pnl:+9.2f} {out_:8.2f} {100*pnl/out_:+7.2f}% {100*pnl/len(t):+6.2f}c "
          f"{100*t.sb_won.mean():7.2f}%")
    if lbl.endswith('(right)') or lbl == '09:00 (right)':
        rowsum.append((strat, len(t), pnl, out_))

print("\n" + "-" * 92)
print("LIVE CONFIGURATION TOTAL (right book, OVER-only, as the trader is now armed)")
n = sum(x[1] for x in rowsum); P = sum(x[2] for x in rowsum); O = sum(x[3] for x in rowsum)
print(f"  {n} trades   P&L {P:+.2f}$   outlay {O:.2f}$   ROI {100*P/O:+.2f}%")
print("  pacegap excluded (no 2025-26 signal export); move's n is small because the")
print("  09:00 ET book exists for only 54 events.")
print("\n  'SB hit%' is the same games graded against the LINE at a sportsbook --")
print("  the old basis. It is not comparable to Kalshi hit%, which grades a RUNG.")
