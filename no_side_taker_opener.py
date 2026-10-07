"""NO side as a taker, on the CORRECT 09:00 ET book. Both directions.

The 1,312-ladder run in no_side_taker_test.py put UNDER ABOVE over
(+4.66c vs +3.59c for move), which is backwards -- a NO take pays the full
spread on the thinner mirrored book and cannot be structurally better. The
cause is the same defect already corrected once for the OVER side: those are
near-CLOSE ladders being used for OPENER-settled strategies, so the gate
selects games whose line moved, and grading with the UNCONDITIONAL D_open
distribution then overstates the winning side. For UNDER the bias points the
other way (select games that moved UP, overstate P(under)), which is exactly
why UNDER came out flattered.

This rebuilds the 09:00 ET book from 1-minute candles and prices both
directions there, which is the only apples-to-apples read available.
"""
import sys, sqlite3, numpy as np, pandas as pd
from scipy.stats import norm

sys.path.insert(0, '/mnt/d/Kalshi/nba')
import nba_live_trader as T
import nba_kalshi as NK

CAND = '/home/dpope/data/kalshi_local/kalshi_nba_candles.sqlite'
TOT = '/home/dpope/data/kalshi_local/kalshi_nba_totals.sqlite'
SIG_GRID = np.arange(9.0, 30.001, 0.05)
SLACK, BIG, TARGET_UTC_HOUR = 0.005, 1e9, 13
ABBR = {'ATL': 'Atlanta', 'BOS': 'Boston', 'BKN': 'Brooklyn', 'CHA': 'Charlotte',
        'CHI': 'Chicago', 'CLE': 'Cleveland', 'DAL': 'Dallas', 'DEN': 'Denver',
        'DET': 'Detroit', 'GSW': 'Golden State', 'HOU': 'Houston', 'IND': 'Indiana',
        'LAC': 'LA Clippers', 'LAL': 'LA Lakers', 'MEM': 'Memphis', 'MIA': 'Miami',
        'MIL': 'Milwaukee', 'MIN': 'Minnesota', 'NOP': 'New Orleans', 'NYK': 'New York',
        'OKC': 'Oklahoma City', 'ORL': 'Orlando', 'PHI': 'Philadelphia', 'PHX': 'Phoenix',
        'POR': 'Portland', 'SAC': 'Sacramento', 'SAS': 'San Antonio', 'TOR': 'Toronto',
        'UTA': 'Utah', 'WAS': 'Washington'}
STRATS = {'move': dict(hit=0.5344, n_sig=350), 'pacegap': dict(hit=0.5259, n_sig=352)}

raw = pd.read_csv('/mnt/c/NBA2/dfMaster_OT_2017-2026.csv', low_memory=False)
base = pd.DataFrame({
    'ds': pd.to_datetime(raw['DATE'], errors='coerce').dt.strftime('%Y-%m-%d'),
    'h': raw['TEAM_H'].astype(str), 'r': raw['TEAM_R'].astype(str),
    'open': pd.to_numeric(raw['OPENING TOTAL_H'], errors='coerce'),
    'pts': pd.to_numeric(raw['TOTAL_PTS'], errors='coerce')}).dropna()
Dopen = np.sort((base.pts - base['open']).values)
for v in STRATS.values():
    v['delta'] = T.delta_points(v['hit'])
    v['s_over'] = float(-np.quantile(Dopen, 1.0 - v['hit']))
    v['s_under'] = float(np.quantile(Dopen, v['hit']))

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
c['hour'], c['date'] = tsu.dt.hour, tsu.dt.strftime('%Y-%m-%d')
c = c[(c.date == c.game_date) & (c.hour <= TARGET_UTC_HOUR)]
c = c.sort_values('ts').groupby(['ev', 'ticker'], as_index=False).last()
con = sqlite3.connect('file:' + TOT + '?mode=ro', uri=True)
em = pd.read_sql("SELECT DISTINCT event_ticker ev, away_team, home_team FROM events", con)
con.close()
c = c.merge(em, on='ev', how='left')
c['h'] = c.home_team.map(ABBR); c['r'] = c.away_team.map(ABBR)
c = c.merge(base, left_on=['game_date', 'h', 'r'], right_on=['ds', 'h', 'r'], how='inner')
c['L'], c['U'] = c.b / 100.0, c.a / 100.0
print(f"09:00 ET books: {c.ev.nunique()} events, {len(c)} rungs")


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


T.NO_SIDE_VERIFIED = True          # price the economics as if the schema worked
out = []
for ev, g in c.groupby('ev'):
    g = g.sort_values('K')
    if len(g) < 4:
        continue
    mu_mkt, sig = mu_sigma(g.K.values, g.L.values, g.U.values)
    rungs = [dict(strike=float(kk), ticker=t, yes_bid=float(bb), yes_ask=float(aa),
                  yes_bid_size=999.0, yes_ask_size=999.0,
                  ranges=[(0.0, 1.0, 0.01)], status='active')
             for kk, t, bb, aa in zip(g.K, g.ticker, g.L, g.U)]
    Lref, pts = g['open'].iloc[0], g.pts.iloc[0]
    for name, v in STRATS.items():
        for dirn in ('OVER', 'UNDER'):
            sgn = 1.0 if dirn == 'OVER' else -1.0
            if mu_mkt is not None and sgn * (mu_mkt - Lref) < -abs(v['delta']):
                out.append(dict(strat=name, dir=dirn, traded=False)); continue
            cands = T.candidates(rungs, Lref + sgn * v['delta'], sig, (dirn,), take=True)
            st = dict(day_contracts=0, day_notional=0.0, game_contracts=0)
            ok = [x for x in cands if T.gate(x, st) is None]
            if not ok:
                out.append(dict(strat=name, dir=dirn, traded=False)); continue
            x = ok[0]
            if dirn == 'OVER':
                pw = float(np.mean(Dopen > (x['strike'] - Lref - v['s_over'])))
                won = pts > x['strike']
            else:
                pw = float(np.mean(Dopen < (x['strike'] - Lref + v['s_under'])))
                won = pts < x['strike']
            fee = NK.fee(x['price'], 1)
            out.append(dict(strat=name, dir=dirn, traded=True, ask=x['price'],
                            believed=x['edge'], p_emp=pw,
                            ev=pw * (1 - x['price']) - (1 - pw) * x['price'] - fee,
                            outlay=x['price'] + fee,
                            pnl=(1 - x['price'] - fee) if won else (-x['price'] - fee)))
R = pd.DataFrame(out)

print("\n" + "=" * 78)
print("NO vs YES AS A TAKER, 09:00 ET BOOK (the correct book for these two)")
print("=" * 78)
print(f"  {'strategy':>9s} {'dir':>6s} {'n':>4s} {'pass%':>6s} {'ask':>6s} "
      f"{'believed':>9s} {'p_emp':>7s} {'EV/ct':>8s} {'ROI':>7s} {'realised/ct':>12s}")
agg = {}
for (s, d), g in R.groupby(['strat', 'dir']):
    t = g[g.traded]
    if not len(t):
        print(f"  {s:>9s} {d:>6s}    0   0.0%   (never passes)"); continue
    agg[(s, d)] = dict(n=len(t), pr=len(t) / len(g), ev=t.ev.mean(),
                       outlay=t.outlay.mean())
    print(f"  {s:>9s} {d:>6s} {len(t):4d} {100*len(t)/len(g):5.1f}% {t.ask.mean():6.3f} "
          f"{t.believed.mean()*100:+8.2f}c {t.p_emp.mean():7.4f} "
          f"{t.ev.mean()*100:+7.2f}c {100*t.ev.mean()/t.outlay.mean():+6.2f}% "
          f"{t.pnl.mean()*100:+11.2f}c")

print("\n" + "=" * 78)
print("WHAT ARMING THE NO SIDE WOULD ADD -- season, 1 contract, taker")
print("=" * 78)
DEPTH_PASS = 0.85          # measured live: NO size >= 5 on 85% of in-band rungs
print(f"  live depth haircut applied to the UNDER leg: {DEPTH_PASS:.0%} "
      f"(NO take consumes the thinner yes_bid book)")
tot_ev = tot_out = tot_n = 0.0
for s in STRATS:
    half = STRATS[s]['n_sig'] / 2.0
    for d in ('OVER', 'UNDER'):
        if (s, d) not in agg:
            continue
        a = agg[(s, d)]
        n = half * a['pr'] * (DEPTH_PASS if d == 'UNDER' else 1.0)
        e, o = n * a['ev'], n * a['outlay']
        tag = '' if d == 'OVER' else '  <-- NEW if NO armed'
        print(f"  {s:>9s} {d:>6s} {n:6.0f} trades {e:+8.2f}$ EV  "
              f"{o:7.2f}$ outlay  {100*e/o if o else 0:+6.2f}% ROI{tag}")
        if d == 'UNDER':
            tot_ev += e; tot_out += o; tot_n += n
print(f"\n  UNDER leg total: {tot_n:.0f} trades  {tot_ev:+.2f}$ EV  "
      f"{tot_out:.2f}$ outlay  ROI {100*tot_ev/tot_out if tot_out else 0:+.2f}%")
print(f"  (before one-trade-per-game claiming against the OVER legs, which will"
      f"\n   cut this further -- UNDER competes for the same games)")
R.to_csv('/home/dpope/projects/nba_entropy_replication/no_side_taker_opener_detail.csv',
         index=False)
