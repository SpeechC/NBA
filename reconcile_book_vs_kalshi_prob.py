"""2025-26 reconciliation: the sportsbook closing total vs Kalshi, in PROBABILITY.

A sportsbook total is a LOCATION quoted at ~even money, so its probability
statement is: P(total > close) = 0.50. Kalshi quotes PROBABILITIES at fixed
strikes. To put them on one axis, ask what Kalshi's executable book says the
probability is AT THE SPORTSBOOK'S OWN NUMBER:

    P_kalshi(close) = 1 - Phi((close - mu) / sigma)

with (mu, sigma) from the EXECUTABLE BOUNDS identified set -- no midpoint.

Three statements about the same event, side by side:
    sportsbook   0.5000      by construction
    Kalshi       P_kalshi    what the book we can trade implies
    reality      realised frequency of actual > close

Differences are also shown in POINTS, via dP/dmu = phi(0)/sigma, so "Kalshi is
0.3 points higher than the book" is readable directly.
"""
import sys, sqlite3
import numpy as np, pandas as pd
from scipy.stats import norm
sys.path.insert(0, '.')
sys.path.insert(0, '/mnt/d/Kalshi/nba')
from prepare_data import read_master, season_label
import nba_live_trader as T

TOT = '/home/dpope/data/kalshi_local/kalshi_nba_totals.sqlite'
ABBR = {'ATL': 'Atlanta', 'BOS': 'Boston', 'BKN': 'Brooklyn', 'CHA': 'Charlotte',
        'CHI': 'Chicago', 'CLE': 'Cleveland', 'DAL': 'Dallas', 'DEN': 'Denver',
        'DET': 'Detroit', 'GSW': 'Golden State', 'HOU': 'Houston', 'IND': 'Indiana',
        'LAC': 'LA Clippers', 'LAL': 'LA Lakers', 'MEM': 'Memphis', 'MIA': 'Miami',
        'MIL': 'Milwaukee', 'MIN': 'Minnesota', 'NOP': 'New Orleans', 'NYK': 'New York',
        'OKC': 'Oklahoma City', 'ORL': 'Orlando', 'PHI': 'Philadelphia', 'PHX': 'Phoenix',
        'POR': 'Portland', 'SAC': 'Sacramento', 'SAS': 'San Antonio', 'TOR': 'Toronto',
        'UTA': 'Utah', 'WAS': 'Washington'}

raw = read_master(verbose=False)
raw['lbl'] = season_label(raw).astype(str)
d = raw[raw['lbl'].str.contains('Regular Season', na=False)].copy()
d['date'] = pd.to_datetime(d['DATE'], errors='coerce')
d['close'] = pd.to_numeric(d['CLOSING TOTAL_H'], errors='coerce')
d['actual'] = pd.to_numeric(d['PTS_H'], errors='coerce') + pd.to_numeric(d['PTS_R'], errors='coerce')
d = d.dropna(subset=['date', 'close', 'actual'])
d = d[d['close'].between(150, 300)].copy()
d['season'] = d['lbl'].str.extract(r'(\d{4})')[0].astype(int)
d['ds'] = d.date.dt.strftime('%Y-%m-%d')
d['h'], d['r'] = d['TEAM_H'].astype(str), d['TEAM_R'].astype(str)
S = d[d.season == 2025]

con = sqlite3.connect('file:' + TOT + '?mode=ro', uri=True)
bk = pd.read_sql("""SELECT m.event_ticker ev, m.floor_strike K,
                           m.pregame_yes_bid b, m.pregame_yes_ask a,
                           e.game_date ds, e.away_team, e.home_team
                    FROM markets m JOIN events e USING(event_ticker)
                    WHERE m.pregame_yes_bid IS NOT NULL
                      AND m.pregame_yes_ask IS NOT NULL
                      AND m.floor_strike IS NOT NULL""", con)
con.close()
bk['h'], bk['r'] = bk.home_team.map(ABBR), bk.away_team.map(ABBR)
bk['L'], bk['U'] = bk.b / 100.0, bk.a / 100.0

rows = []
for (ev, ds_, h, r), g in bk.groupby(['ev', 'ds', 'h', 'r']):
    m = S[(S.ds == ds_) & (S.h == h) & (S.r == r)]
    if m.empty or len(g) < 4:
        continue
    g = g.sort_values('K')
    rungs = [dict(strike=float(k), yes_bid=float(x), yes_ask=float(y))
             for k, x, y in zip(g.K, g.L, g.U)]
    mu, sg, feas = T.fit_ladder_detail(rungs)
    if mu is None:
        continue
    close = float(m.close.iloc[0]); act = float(m.actual.iloc[0])
    pk = float(1.0 - norm.cdf((close - mu) / sg))
    # executable bracket at the close: monotone survival means S(close) lies
    # between the quotes of the rungs that straddle it
    below = g[g.K <= close]; above = g[g.K >= close]
    lo = float(above.L.iloc[0]) if len(above) else np.nan      # lowest strike >= close
    hi = float(below.U.iloc[-1]) if len(below) else np.nan     # highest strike <= close
    rows.append(dict(ev=ev, close=close, actual=act, mu=mu, sigma=sg, feas=feas,
                     p_kalshi=pk, over=int(act > close),
                     brk_lo=lo, brk_hi=hi,
                     pts_diff=(pk - 0.5) / (norm.pdf(0) / sg)))
R = pd.DataFrame(rows)
print(f"events reconciled: {len(R)}  (bounds fit feasible on "
      f"{100*R.feas.mean():.1f}%)\n")

print("=" * 86)
print("THREE STATEMENTS ABOUT THE SAME EVENT: P(total > closing total)")
print("=" * 86)
print(f"  {'sportsbook (by construction)':<34}{0.5:>9.4f}")
print(f"  {'Kalshi, executable bounds':<34}{R.p_kalshi.mean():>9.4f}"
      f"   sd {R.p_kalshi.std():.4f}")
print(f"  {'realised':<34}{R.over.mean():>9.4f}"
      f"   se {np.sqrt(R.over.mean()*(1-R.over.mean())/len(R)):.4f}")
print(f"\n  Kalshi minus book: {100*(R.p_kalshi.mean()-0.5):+.2f} pp "
      f"= {R.pts_diff.mean():+.3f} points of line")
print(f"  reality minus book: {100*(R.over.mean()-0.5):+.2f} pp")
print(f"  reality minus Kalshi: {100*(R.over.mean()-R.p_kalshi.mean()):+.2f} pp")
print(f"\n  per-event |Kalshi - 0.5|: median {100*(R.p_kalshi-0.5).abs().median():.2f} pp "
      f"= {(R.pts_diff.abs()).median():.3f} pts;  "
      f"90th pct {(R.pts_diff.abs()).quantile(.9):.3f} pts")

print("\n" + "=" * 86)
print("IS THE DISAGREEMENT INFORMATIVE? bucket by how far Kalshi sits from the book")
print("=" * 86)
R['bkt'] = pd.qcut(R.pts_diff, 5, duplicates='drop')
print(f"  {'Kalshi - book (pts)':>22}{'n':>6}{'P_kalshi':>10}{'realised':>10}"
      f"{'book':>7}{'K beats book by':>17}")
for b, g in R.groupby('bkt', observed=True):
    edge_k = abs(g.over.mean() - g.p_kalshi.mean())
    edge_b = abs(g.over.mean() - 0.5)
    print(f"  {str(b):>22}{len(g):>6}{g.p_kalshi.mean():>10.4f}{g.over.mean():>10.4f}"
          f"{0.5:>7.2f}{100*(edge_b-edge_k):>+16.2f}pp")
print("\n  'K beats book by' is |realised - 0.5| minus |realised - P_kalshi|:")
print("  positive means Kalshi's number was closer to what happened.")

print("\n" + "=" * 86)
print("EXECUTABLE BRACKET AT THE CLOSE (no model at all, pure quotes)")
print("=" * 86)
ok = R.dropna(subset=['brk_lo', 'brk_hi'])
print(f"  n={len(ok)}  the straddling rungs bound P(>close) in "
      f"[{ok.brk_lo.mean():.3f}, {ok.brk_hi.mean():.3f}] on average")
print(f"  0.50 lies inside that executable bracket on "
      f"{100*((ok.brk_lo <= 0.5) & (ok.brk_hi >= 0.5)).mean():.1f}% of events")
print("  (a wide bracket is the 3-pt strike grid, not disagreement)")
R.to_csv('reconcile_book_vs_kalshi_prob.csv', index=False)
