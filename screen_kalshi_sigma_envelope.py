"""Does the EXECUTABLE Kalshi ladder require wider dispersion for high totals?

Supersedes screen_kalshi_sigma_vs_total.py, whose result is STRUCK. That script
fit the ladder to `pregame_mid`. A midpoint is not an executable price, and on
this board the quoted width reaches 82c (median 28c above 90c), so averaging
bid and ask there manufactures a precision nobody can trade. No midpoint is used
anywhere in this file.

METHOD -- the book is an INTERVAL, not a point.
For a candidate (mu, sigma) the model probability at strike K_j is
p_j = 1 - Phi((K_j - mu)/sigma), and a rung costs nothing if the model lies
inside what is actually quoted:

    L_j = (bid_j - p_j)^2   if p_j < bid_j
          0                 if bid_j <= p_j <= ask_j
          (p_j - ask_j)^2   if p_j > ask_j

Rather than minimise to a point estimate, this reports the IDENTIFIED SET --
every (mu, sigma) with zero loss. The object of interest is then the interval
[sigma_lo, sigma_hi] that the executable book actually permits, per game.

SCALE COMES FROM THE BODY. NBA_TOTALS_SKEW_ERROR.md established that the
outcome is right-skewed by OT while the ladder is fitted normal, and that Kalshi
prices ~1.01c of curvature. Fitting outer rungs to a pure normal would let that
skew masquerade as variance, so the feasible set is built on BODY rungs only
(quote interval inside [10c, 90c]); the tails are reported separately as a
consistency check, never as scale.

THE QUESTION: does sigma_lo -- the narrowest dispersion the book permits --
rise with the posted closing total, and at the realised rate of +0.04187
(95% CI [+0.01416, +0.07046], from MATCHUP_HETEROSKEDASTICITY.md)?
"""
import sqlite3, numpy as np, pandas as pd
from scipy.stats import norm

DB = '/home/dpope/data/kalshi_local/kalshi_nba_totals.sqlite'
BODY_LO, BODY_HI = 0.10, 0.90
MU_GRID = np.arange(180.0, 275.01, 0.25)
SG_GRID = np.arange(8.0, 34.01, 0.10)
RNG = np.random.default_rng(11)

ABBR = {  # Kalshi 3-letter -> dfMaster city label. Validated 30/30 below.
    'ATL': 'Atlanta', 'BOS': 'Boston', 'BKN': 'Brooklyn', 'CHA': 'Charlotte',
    'CHI': 'Chicago', 'CLE': 'Cleveland', 'DAL': 'Dallas', 'DEN': 'Denver',
    'DET': 'Detroit', 'GSW': 'Golden State', 'HOU': 'Houston', 'IND': 'Indiana',
    'LAC': 'LA Clippers', 'LAL': 'LA Lakers', 'MEM': 'Memphis', 'MIA': 'Miami',
    'MIL': 'Milwaukee', 'MIN': 'Minnesota', 'NOP': 'New Orleans', 'NYK': 'New York',
    'OKC': 'Oklahoma City', 'ORL': 'Orlando', 'PHI': 'Philadelphia', 'PHX': 'Phoenix',
    'POR': 'Portland', 'SAC': 'Sacramento', 'SAS': 'San Antonio', 'TOR': 'Toronto',
    'UTA': 'Utah', 'WAS': 'Washington'}

con = sqlite3.connect('file:' + DB + '?mode=ro', uri=True)
m = pd.read_sql("""SELECT m.event_ticker, m.floor_strike K,
                          m.pregame_yes_bid b, m.pregame_yes_ask a,
                          e.game_date, e.away_team, e.home_team
                   FROM markets m JOIN events e USING(event_ticker)
                   WHERE m.pregame_yes_bid IS NOT NULL
                     AND m.pregame_yes_ask IS NOT NULL
                     AND m.floor_strike IS NOT NULL""", con)
con.close()
m['b'] = m.b / 100.0
m['a'] = m.a / 100.0
print(f"rungs {len(m)}  events {m.event_ticker.nunique()}  "
      f"quoted width median {(m.a-m.b).median()*100:.1f}c  max {(m.a-m.b).max()*100:.0f}c")

# ---- join the POSTED closing total (exogenous x, not derived from the book) --
raw = pd.read_csv('/mnt/c/NBA2/dfMaster_OT_2017-2026.csv', low_memory=False)
ms = pd.DataFrame({
    'date': pd.to_datetime(raw['DATE'], errors='coerce').dt.strftime('%Y-%m-%d'),
    'h': raw['TEAM_H'].astype(str), 'r': raw['TEAM_R'].astype(str),
    'posted': pd.to_numeric(raw['CLOSING TOTAL_H'], errors='coerce'),
    'pts': pd.to_numeric(raw['TOTAL_PTS'], errors='coerce')}).dropna()
seen = set(m.home_team) | set(m.away_team)
bad = seen - set(ABBR)
print(f"abbreviation map: {len(seen)} seen, {len(bad)} unmapped {sorted(bad) if bad else ''}")
m['h'] = m.home_team.map(ABBR)
m['r'] = m.away_team.map(ABBR)
m = m.merge(ms, left_on=['game_date', 'h', 'r'], right_on=['date', 'h', 'r'], how='inner')
print(f"joined to posted total: {m.event_ticker.nunique()} events")

# ---- identified set per event, from BODY rungs only -------------------------
P = 1.0 - norm.cdf((MU_GRID[None, :, None] - 0) )  # placeholder, computed below
rows = []
for ev, g in m.groupby('event_ticker'):
    body = g[(g.a <= BODY_HI) & (g.b >= BODY_LO)]
    if len(body) < 4 or np.ptp(body.K.values) < 3:
        continue
    K = body.K.values[None, None, :]
    lo = body.b.values[None, None, :]
    hi = body.a.values[None, None, :]
    z = (K - MU_GRID[None, :, None]) / SG_GRID[:, None, None]
    p = 1.0 - norm.cdf(z)                                    # (nsig, nmu, nrung)
    feas = ((p >= lo - 1e-12) & (p <= hi + 1e-12)).all(axis=2)
    if not feas.any():
        continue
    si = np.where(feas.any(axis=1))[0]
    mi = np.where(feas.any(axis=0))[0]
    rows.append(dict(event=ev, posted=g.posted.iloc[0], pts=g.pts.iloc[0],
                     n_body=len(body), n_all=len(g),
                     sg_lo=SG_GRID[si.min()], sg_hi=SG_GRID[si.max()],
                     mu_lo=MU_GRID[mi.min()], mu_hi=MU_GRID[mi.max()]))
L = pd.DataFrame(rows)
print(f"\nidentified sets found for {len(L)} events "
      f"({100*len(L)/m.event_ticker.nunique():.1f}% of joined)")
print(f"  sigma interval width: median {(L.sg_hi-L.sg_lo).median():.2f} pts, "
      f"IQR {(L.sg_hi-L.sg_lo).quantile(.25):.2f}-{(L.sg_hi-L.sg_lo).quantile(.75):.2f}")
print(f"  mu    interval width: median {(L.mu_hi-L.mu_lo).median():.2f} pts")
print(f"  sigma_lo median {L.sg_lo.median():.2f}   sigma_hi median {L.sg_hi.median():.2f}")

# ---- does the ENVELOPE require wider dispersion for high totals? ------------
print("\n" + "=" * 74)
print("DOES THE EXECUTABLE BOOK REQUIRE WIDER SIGMA AT HIGH TOTALS?")
print("=" * 74)
L['tb'] = pd.qcut(L.posted, 6, duplicates='drop')
print(f"  {'posted total':>14s} {'n':>5s} {'sigma_lo':>9s} {'sigma_hi':>9s} {'width':>7s}")
agg = L.groupby('tb', observed=True).agg(mid=('posted', 'mean'), lo=('sg_lo', 'mean'),
                                         hi=('sg_hi', 'mean'), n=('sg_lo', 'size'))
for _, r in agg.iterrows():
    print(f"  {r.mid:14.1f} {int(r.n):5d} {r.lo:9.3f} {r.hi:9.3f} {r.hi-r.lo:7.3f}")


def slope_ci(x, y, nb=2000):
    s = np.polyfit(x, y, 1)[0]
    d = []
    for _ in range(nb):
        i = RNG.integers(0, len(x), len(x))
        d.append(np.polyfit(x[i], y[i], 1)[0])
    return s, *np.percentile(d, [2.5, 97.5])

print()
for nm, col in (('sigma_lo (narrowest the book allows)', 'sg_lo'),
                ('sigma_hi (widest the book allows)', 'sg_hi')):
    s, lo, hi = slope_ci(L.posted.values, L[col].values)
    print(f"  slope of {nm:38s} {s:+.5f}  CI [{lo:+.5f},{hi:+.5f}]")
print(f"  REALISED slope (MATCHUP_HETEROSKEDASTICITY.md)      +0.04187  "
      f"CI [+0.01416,+0.07046]")

print("\n  VERDICT LOGIC: the book PRICES the scaling only if the whole")
print("  identified band moves with the total at the realised rate. If the")
print("  sigma interval is wide, the executable book does not pin sigma at")
print("  all, and neither 'prices it' nor 'misprices it' is supportable.")

# ---- tails as a consistency check, never as scale ---------------------------
print("\n" + "-" * 74)
print("TAIL CHECK (not used for scale): with sigma fixed at its body-implied")
print("lower bound, are the OUTER rungs inside their own quotes?")
viol = tot = 0
for ev, g in m.groupby('event_ticker'):
    r = L[L.event == ev]
    if r.empty:
        continue
    sg = float(r.sg_lo.iloc[0]); mu = float((r.mu_lo.iloc[0] + r.mu_hi.iloc[0]) / 2)
    out = g[(g.a > BODY_HI) | (g.b < BODY_LO)]
    if out.empty:
        continue
    p = 1.0 - norm.cdf((out.K.values - mu) / sg)
    tot += len(out)
    viol += int(((p < out.b.values - 1e-9) | (p > out.a.values + 1e-9)).sum())
print(f"  outer rungs outside their quote under the body-fitted normal: "
      f"{viol} / {tot} ({100*viol/max(tot,1):.1f}%)")
print("  (a high rate is the known ladder curvature, NOT evidence about sigma)")
