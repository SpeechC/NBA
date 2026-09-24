"""Where does the 2.14pp residual come from -- the market, or my constant sigma?

If a FLEXIBLE spread->probability mapping collapses the residual, then the
residual was my model's misspecification, not a disagreement between the two
markets. Fitted out-of-sample by season so the flexible map cannot cheat.
"""
import numpy as np, pandas as pd
from scipy.stats import norm
from scipy.optimize import brentq

df = pd.read_csv('/mnt/c/NBA2/dfMaster_OT_2017-2026.csv', low_memory=False)
d = pd.DataFrame({
    'date': pd.to_datetime(df['DATE'], errors='coerce'),
    'spread': pd.to_numeric(df['CLOSING SPREAD_H'], errors='coerce'),
    'ml_h': pd.to_numeric(df['MONEYLINE_H'], errors='coerce'),
    'ml_r': pd.to_numeric(df['MONEYLINE_R'], errors='coerce'),
    'f_h': pd.to_numeric(df['F_H'], errors='coerce'),
    'f_r': pd.to_numeric(df['F_R'], errors='coerce')}).dropna()
d = d[(d.ml_h.abs() >= 100) & (d.ml_r.abs() >= 100)]
d['margin'] = d.f_h - d.f_r
d = d[d.margin != 0]
d['home_win'] = (d.margin > 0).astype(float)
a2p = lambda m: np.where(m < 0, -m / (-m + 100.0), 100.0 / (m + 100.0))
d['p_ml'] = a2p(d.ml_h) / (a2p(d.ml_h) + a2p(d.ml_r))
d['season'] = np.where(d.date.dt.month >= 8, d.date.dt.year, d.date.dt.year - 1)

sig = brentq(lambda s: float((norm.cdf(-d.spread / s) - d.p_ml).mean()), 5, 30)
d['p_const'] = norm.cdf(-d.spread / sig)

# Flexible map: leave-one-season-out mean de-vigged ML at each distinct spread.
d['p_flex'] = np.nan
for s in d.season.unique():
    tr, te = d[d.season != s], d[d.season == s]
    m = tr.groupby('spread').p_ml.mean()
    g = tr.groupby('spread').size()
    m = m[g >= 20]
    d.loc[te.index, 'p_flex'] = te.spread.map(m).values
f = d.dropna(subset=['p_flex']).copy()

print(f"n = {len(f)}   constant sigma = {sig:.3f}")
for nm, c in [('constant-sigma normal', 'p_const'), ('flexible map (OOS)', 'p_flex')]:
    r = f.p_ml - f[c]
    print(f"  {nm:24s} residual sd {r.std():.5f}   |>2pp| {100*(r.abs()>.02).mean():5.1f}%")

print("\nWHICH MARKET IS RIGHT? Brier score against the actual result:")
for nm, c in [('de-vigged moneyline', 'p_ml'), ('spread, constant sigma', 'p_const'),
              ('spread, flexible map', 'p_flex')]:
    b = ((f[c] - f.home_win) ** 2).mean()
    print(f"  {nm:24s} Brier {b:.5f}")

# Quantization floor: how much residual do the quoted increments alone force?
sp = np.sort(f.spread.unique())
print(f"\nspread grid: {np.median(np.diff(sp)):.2f} pt steps")
ml = np.sort(np.abs(pd.concat([f.ml_h, f.ml_r]).unique()))
print(f"moneyline grid: median step {np.median(np.diff(ml)):.1f} cents")
dens = norm.pdf(-f.spread / sig) / sig
print(f"half-point spread rounding  -> {(0.5/np.sqrt(12)*dens).mean()*100:.2f}pp of probability sd")
