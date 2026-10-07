"""Two gaps exposed by asking "why aren't we using Kalshi's closing line?"

ANSWER: we are. signals() passes ref=None for crewshock and final7, and run()
does `ref = s["ref"] if s["ref"] is not None else mu_mkt`, so for the two
close-settled strategies the reference IS the Kalshi ladder's own centre. That
is the right design -- the closing total is not knowable at 17:00 ET when
CrewShock fills, and this programme established that the ladder's implied mu IS
the close. The opener-settled pair (pacegap, move) correctly uses the captured
sportsbook opener instead, which IS knowable at 09:00.

But it exposes two problems:

GAP 1  mu_mkt comes from fit_ladder(), which regresses Phi^-1(1 - p_MID) on
       strike. So for crewshock and final7 the ANCHOR OF THE ENTIRE BET is
       mid-derived, not just the drift guard. That is a materially bigger
       exposure to the no-midpoint rule than previously recorded.

GAP 2  Every backtest in this thread used the sportsbook CLOSING TOTAL as the
       reference for crewshock and final7. The live trader uses mu_mkt. Those
       are not the same number, so the measured results were for a rule the
       trader does not run.

Both are quantified here on the 1,312-event 2025-26 board.
"""
import sys, sqlite3, numpy as np, pandas as pd
from scipy.stats import norm
sys.path.insert(0, '.')
sys.path.insert(0, '/mnt/d/Kalshi/nba')
from prepare_data import read_master, season_label
import nba_live_trader as T
import nba_kalshi as NK

TOT = '/home/dpope/data/kalshi_local/kalshi_nba_totals.sqlite'
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
DELTA = {'crewshock': T.delta_points(0.5421), 'final7': T.delta_points(0.5529)}

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
sig = {'crewshock': cw.rename(columns={'TEAM_H': 'h', 'TEAM_R': 'r'})[['ds', 'h', 'r']],
       'final7': S[S.days_left <= 7][['ds', 'h', 'r']]}

con = sqlite3.connect('file:' + TOT + '?mode=ro', uri=True)
bk = pd.read_sql("""SELECT m.event_ticker ev, m.ticker, m.floor_strike K,
                           m.pregame_yes_bid b, m.pregame_yes_ask a,
                           e.game_date ds, e.away_team, e.home_team
                    FROM markets m JOIN events e USING(event_ticker)
                    WHERE m.pregame_yes_bid IS NOT NULL
                      AND m.pregame_yes_ask IS NOT NULL
                      AND m.floor_strike IS NOT NULL""", con)
con.close()
bk['L'], bk['U'] = bk.b / 100.0, bk.a / 100.0
bk['h'], bk['r'] = bk.home_team.map(ABBR), bk.away_team.map(ABBR)


def mu_bounds(K, Lo_, Up_):
    Lo = np.clip(Lo_ - SLACK, 1e-9, 1 - 1e-9); Up = np.clip(Up_ + SLACK, 1e-9, 1 - 1e-9)
    zL = np.where(np.isfinite(norm.ppf(1 - Lo)), norm.ppf(1 - Lo), BIG)
    zU = np.where(np.isfinite(norm.ppf(1 - Up)), norm.ppf(1 - Up), -BIG)
    lo = (K[None, :] - SIG_GRID[:, None] * zL[None, :]).max(axis=1)
    hi = (K[None, :] - SIG_GRID[:, None] * zU[None, :]).min(axis=1)
    ok = np.where(lo <= hi + 1e-9)[0]
    if len(ok) == 0:
        return np.nan, T.SIGMA_REF
    i = ok[len(ok) // 2]
    return (lo[i] + hi[i]) / 2.0, SIG_GRID[i]


# ------------------------------------------------- GAP 1: mid vs bounds anchor
rows = []
for ev, g in bk.groupby('ev'):
    g = g.sort_values('K')
    if len(g) < 4:
        continue
    rungs = [dict(strike=float(k), yes_bid=float(bb), yes_ask=float(aa))
             for k, bb, aa in zip(g.K, g.L, g.U)]
    mm, sm = T.fit_ladder_mid(rungs)                 # the OLD mid-based anchor
    mb, sb = mu_bounds(g.K.values, g.L.values, g.U.values)
    if mm is None or not np.isfinite(mb):
        continue
    mrow = S[(S.ds == g.ds.iloc[0]) & (S.h == g.h.iloc[0]) & (S.r == g.r.iloc[0])]
    rows.append(dict(ev=ev, mu_mid=mm, sig_mid=sm, mu_bnd=mb, sig_bnd=sb,
                     close=float(mrow.close.iloc[0]) if len(mrow) else np.nan))
A = pd.DataFrame(rows)
A['mid_minus_bnd'] = A.mu_mid - A.mu_bnd
A['mid_minus_close'] = A.mu_mid - A.close
print("=" * 84)
print("GAP 1 -- the live anchor is MID-derived. How much does that move it?")
print("=" * 84)
print(f"  n={len(A)} events with both estimates")
print(f"  mu_mid - mu_bounds : mean {A.mid_minus_bnd.mean():+.4f}  "
      f"median {A.mid_minus_bnd.median():+.4f}  sd {A.mid_minus_bnd.std():.4f} pts")
print(f"  |diff| > 0.5 pt on {100*(A.mid_minus_bnd.abs()>0.5).mean():.1f}% of events, "
      f"> 1 pt on {100*(A.mid_minus_bnd.abs()>1).mean():.1f}%")
pp = norm.pdf(0) / T.SIGMA_REF
print(f"  at {100*pp:.3f} pp of win rate per point, that sd is "
      f"{100*A.mid_minus_bnd.std()*pp:.2f} pp of probability")
print(f"  sigma: mid {A.sig_mid.median():.3f}  bounds {A.sig_bnd.median():.3f}")
print(f"\n  for scale, mu_mid - sportsbook close: mean "
      f"{A.mid_minus_close.mean():+.4f}  sd {A.mid_minus_close.std():.4f} pts")

# ------------------------------------------------- GAP 2: which ref was tested
def replay(strat, ref_mode):
    j = sig[strat].merge(bk, on=['ds', 'h', 'r'], how='inner')
    out = []
    for (ev, ds_, h, r), g in j.groupby(['ev', 'ds', 'h', 'r']):
        g = g.sort_values('K')
        mrow = S[(S.ds == ds_) & (S.h == h) & (S.r == r)]
        if mrow.empty or len(g) < 4:
            continue
        pts = float(mrow.actual.iloc[0])
        rungs = [dict(strike=float(k), ticker=t, yes_bid=float(bb), yes_ask=float(aa),
                      yes_bid_size=999.0, yes_ask_size=999.0,
                      ranges=[(0.0, 1.0, 0.01)], status='active')
                 for k, t, bb, aa in zip(g.K, g.ticker, g.L, g.U)]
        mm, sm = T.fit_ladder_mid(rungs)
        mb, sb, feas = T.fit_ladder_detail(rungs)
        if mm is None:
            continue
        if ref_mode == 'close':
            ref, sg = float(mrow.close.iloc[0]), sb
        elif ref_mode == 'mu_mid':              # exactly what the trader does
            ref, sg = mm, sm
        else:                                   # NEW live estimator, no midpoint
            ref, sg = mb, sb
        if not np.isfinite(ref):
            continue
        cands = T.candidates(rungs, ref + DELTA[strat], sg, ('OVER',))
        ok = [c for c in cands
              if T.gate(c, dict(day_contracts=0, day_notional=0.0, game_contracts=0)) is None]
        if not ok:
            continue
        c = ok[0]
        fee = NK.fee(c['price'], 1)
        won = pts > c['strike']
        out.append(dict(hit=bool(won), ask=c['price'],
                        pnl=(1 - c['price'] - fee) if won else (-c['price'] - fee),
                        outlay=c['price'] + fee, off=c['strike'] - ref))
    return pd.DataFrame(out)


print("\n" + "=" * 84)
print("GAP 2 -- my backtests used the CLOSE as ref; the trader uses mu_mkt")
print("=" * 84)
print(f"  {'strategy':>10}{'reference':>22}{'n':>6}{'hit%':>8}{'P&L':>9}{'ROI':>9}{'mean off':>10}")
for strat in ('crewshock', 'final7'):
    for mode, lbl in (('close', 'sportsbook close'),
                      ('mu_mid', 'Kalshi mu (MID) = LIVE'),
                      ('mu_bnd', 'Kalshi mu (BOUNDS) = NEW')):
        R = replay(strat, mode)
        if not len(R):
            continue
        print(f"  {strat:>10}{lbl:>22}{len(R):>6}{100*R.hit.mean():>7.2f}%"
              f"{R.pnl.sum():>+9.2f}{100*R.pnl.sum()/R.outlay.sum():>+8.2f}%"
              f"{R.off.mean():>+10.2f}")
print("\n  The 'LIVE' row is the configuration actually armed in cron.")
