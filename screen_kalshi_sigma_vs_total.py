"""*** INVALID -- DO NOT CITE. Superseded by screen_kalshi_sigma_envelope.py. ***

This script fit the ladder to `pregame_mid`. A midpoint is NOT an executable
price, and quoted width on this board reaches 82c (median 28c above 90c), so
averaging bid and ask manufactures a precision nobody can trade. Its headline
numbers -- sigma slope +0.06222 and mean implied sigma 18.214 -- are withdrawn.

STANDING RULE: no midpoint anywhere in this project. Bid/ask interval
inference only. Retained so the error stays legible; see KALSHI_SIGMA_ENVELOPE.md.
"""
"""Does the Kalshi totals ladder price the dispersion that actually exists?

screen_matchup_heteroskedasticity.py found that matchup features predict NO
dispersion out of sample (OOS corr = -0.014), but that sd(D) DOES rise with the
closing total itself: 17.09 -> 19.32 across total quintiles, VarRatio 1.278.

That is only useful if the market fails to price it. Kalshi quotes a whole
ladder per game, so its sigma is directly observable -- invert the rungs rather
than assume anything:

    Phi^-1(1 - p_mid) = (K - mu)/sigma      regress z on K per event
    sigma = 1/slope,  mu = -intercept * sigma

Then compare Kalshi's sigma-vs-total slope with the realised one. If Kalshi
scales sigma with the total at the rate the outcomes demand, the dispersion
structure is priced and there is nothing to trade. If it under-scales, high-
total games have fatter tails than the ladder says, and the far rungs are
mispriced in a known direction.

Uses `pregame_mid` -- the last pregame snapshot, not a settled or in-play mark.
"""
import sqlite3, numpy as np, pandas as pd
from scipy.stats import norm

DB = '/home/dpope/data/kalshi_local/kalshi_nba_totals.sqlite'
con = sqlite3.connect('file:' + DB + '?mode=ro', uri=True)
m = pd.read_sql("""SELECT event_ticker, game_date, floor_strike K, pregame_mid p,
                          volume FROM markets
                   WHERE pregame_mid IS NOT NULL AND floor_strike IS NOT NULL""", con)
con.close()
m['p'] = m.p / 100.0 if m.p.max() > 1.5 else m.p
m = m[(m.p > 0.02) & (m.p < 0.98)]
print(f"rungs {len(m)}   events {m.event_ticker.nunique()}")

rows = []
for ev, g in m.groupby('event_ticker'):
    g = g.dropna(subset=['K', 'p'])
    if len(g) < 4:
        continue
    z = norm.ppf(1 - g.p.values)
    K = g.K.values
    if np.ptp(K) < 3:
        continue
    b, a = np.polyfit(K, z, 1)          # z = b*K + a
    if b <= 1e-6:
        continue
    sig = 1.0 / b
    mu = -a * sig
    if not (5 < sig < 40) or not (150 < mu < 300):
        continue
    resid = z - (b * K + a)
    rows.append(dict(event=ev, date=g.game_date.iloc[0], mu=mu, sigma=sig,
                     n=len(g), fit_rmse=float(np.sqrt((resid ** 2).mean())),
                     vol=g.volume.sum()))
L = pd.DataFrame(rows)
print(f"ladders inverted {len(L)}   median sigma {L.sigma.median():.3f}   "
      f"median fit rmse {L.fit_rmse.median():.4f}")

# ---- realised dispersion vs the line, same season, from the master file -----
raw = pd.read_csv('/mnt/c/NBA2/dfMaster_OT_2017-2026.csv', low_memory=False)
o = pd.DataFrame({
    'date': pd.to_datetime(raw['DATE'], errors='coerce'),
    'total': pd.to_numeric(raw['CLOSING TOTAL_H'], errors='coerce'),
    'pts': pd.to_numeric(raw['TOTAL_PTS'], errors='coerce')}).dropna()
o['D'] = o.pts - o.total
o['season'] = np.where(o.date.dt.month >= 8, o.date.dt.year, o.date.dt.year - 1)

print("\n" + "=" * 74)
print("SLOPE OF SIGMA AGAINST THE TOTAL")
print("=" * 74)

# realised: sd(D) within total bins, all 9 seasons (more power than one season)
o['tb'] = pd.qcut(o.total, 8, duplicates='drop')
rr = o.groupby('tb', observed=True).agg(mid=('total', 'mean'), sd=('D', 'std'), n=('D', 'size'))
sr = np.polyfit(rr.mid, rr.sd, 1)[0]
print(f"  REALISED  sd(actual-total) vs total, 8 bins, n={len(o)}")
for _, r in rr.iterrows():
    print(f"     total {r.mid:7.1f}   sd {r.sd:6.3f}   n {int(r.n):5d}")
print(f"     slope = {sr:+.5f} sigma points per point of total")

# kalshi: its own sigma vs its own mu
kb = pd.qcut(L.mu, 8, duplicates='drop')
kk = L.groupby(kb, observed=True).agg(mid=('mu', 'mean'), sg=('sigma', 'mean'), n=('sigma', 'size'))
sk = np.polyfit(kk.mid, kk.sg, 1)[0]
print(f"\n  KALSHI    implied sigma vs implied mu, 8 bins, n={len(L)}")
for _, r in kk.iterrows():
    print(f"     mu    {r.mid:7.1f}   sigma {r.sg:6.3f}   n {int(r.n):5d}")
print(f"     slope = {sk:+.5f}")

# bootstrap both slopes
rng = np.random.default_rng(7)
def bslope(x, y, nb=2000):
    out = []
    for _ in range(nb):
        i = rng.integers(0, len(x), len(x))
        df = pd.DataFrame({'x': x[i], 'y': y[i]})
        try:
            q = pd.qcut(df.x, 8, duplicates='drop')
            gg = df.groupby(q, observed=True).agg(mx=('x', 'mean'), sy=('y', 'std'))
            out.append(np.polyfit(gg.mx, gg.sy, 1)[0])
        except Exception:
            pass
    return np.percentile(out, [2.5, 97.5])

lo, hi = bslope(o.total.values, o.D.values)
print(f"\n  realised slope 95% CI  [{lo:+.5f}, {hi:+.5f}]")
print(f"  kalshi   slope         {sk:+.5f}")
print(f"  -> Kalshi is {'INSIDE' if lo <= sk <= hi else 'OUTSIDE'} the realised interval")

print("\n  level check (is the ladder's sigma right on average?)")
s25 = o[o.season == 2025]
print(f"     realised sd(D) 2025-26 season : {s25.D.std():.3f}  (n={len(s25)})")
print(f"     Kalshi median implied sigma    : {L.sigma.median():.3f}")
print(f"     mean                            : {L.sigma.mean():.3f}")
