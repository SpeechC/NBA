"""DTO/NTO decomposition of the Q4 comeback effect — executes PREREG_dto_nto_q4.md."""
import math, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
from dto_nto_build import build

NPERM = 5000
RNG = np.random.default_rng(42)
PPP = 1.12                      # points per possession, fixed in the prereg


def ols_t(y, cols):
    X = np.column_stack([np.ones(len(y))] + list(cols))
    ok = np.isfinite(y) & np.all(np.isfinite(X), axis=1)
    X, y = X[ok], y[ok]
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = y - X @ b; n, k = X.shape
    se = np.sqrt(np.diag((r @ r / (n - k)) * np.linalg.pinv(X.T @ X)))
    return b, b / se, int(n)


def fl(d, y, key, ctl, lab, one_sided=True):
    Z = np.column_stack([np.ones(len(d))] + [d[c].values for c in ctl])
    bz, *_ = np.linalg.lstsq(Z, y, rcond=None)
    resid = y - Z @ bz
    b, t, n = ols_t(y, [d[key].values] + [d[c].values for c in ctl])
    obs = b[1]
    yrs = d.season.values
    blocks = [np.where(yrs == u)[0] for u in np.unique(yrs)]
    null = np.empty(NPERM)
    for i in range(NPERM):
        r = resid.copy()
        for bl in blocks:
            r[bl] = resid[bl][RNG.permutation(len(bl))]
        bb, _, _ = ols_t(Z @ bz + r, [d[key].values] + [d[c].values for c in ctl])
        null[i] = bb[1]
    p1 = (1 + np.sum(null >= obs)) / (NPERM + 1)
    p2 = (1 + np.sum(np.abs(null) >= abs(obs))) / (NPERM + 1)
    pv = f"p1={p1:.4f}" if one_sided else f"p2={p2:.4f}"
    print(f"    {lab:<34} beta {obs:+.5f} (t={t[1]:+.2f})  FL sd {null.std():.5f}  {pv}")
    return obs


d = build()
for s in sorted(d.season.unique())[:-1]:
    d[f"S{s[4:8]}"] = (d.season == s).astype(float)
S = [c for c in d.columns if c.startswith("S2")]
d["Y"] = d.dDTO - d.dNTO
print(f"n={len(d):,} games, {d.season.nunique()} seasons, D>=12 on {int((d.D>=12).sum()):,}")

print("\n=== P0 POSITIVE CONTROL — is the Q4 comeback effect present here? ===")
b, t, n = ols_t(d.q4_trail_margin.values, [d.D.values] + [d[c].values for c in S])
print(f"    q4_trail_margin ~ D            beta {b[1]:+.5f} (t={t[1]:+.2f})")
hi = d[d.D >= 12]
print(f"    mean Q4 trailing margin at D>=12: {hi.q4_trail_margin.mean():+.3f} pts "
      f"(n={len(hi):,})   audit recorded +1.65")
print(f"    {'PASS' if hi.q4_trail_margin.mean() > 0.5 else 'FAIL'}")

print("\n=== P1 PRIMARY — Y = dDTO - dNTO  ~ D   (predicted > 0) ===")
bY = fl(d, d.Y.values, "D", S, "Y ~ D  (diff-in-diff)")

print("\n=== P2 COMPETING EXPLANATION — garbage time ===")
bN = fl(d, d.dNTO.values, "D", S, "dNTO ~ D (player behaviour)", one_sided=False)
bD = fl(d, d.dDTO.values, "D", S, "dDTO ~ D (whistle)", one_sided=False)

print("\n=== P3 MAGNITUDE — can this explain +1.65 points? ===")
mD = float(np.mean(d.D[d.D >= 12]))
print(f"    mean deficit in the D>=12 cell: {mD:.1f}")
for lab, beta in (("DTO channel", bD), ("NTO channel", bN), ("net (Y)", bY)):
    to = beta * mD
    print(f"    {lab:<14} {beta:+.5f} TO per point of deficit -> {to:+.3f} net TOs "
          f"at D={mD:.0f}  ->  {to*PPP:+.3f} pts")
print(f"    the audit's Q4 comeback effect at D>=12: +1.65 pts")
tot = bD * mD * PPP
print(f"    DTO channel explains {100*tot/1.65:+.1f}% of it")

print("\n=== observed differentials by deficit bucket (descriptive) ===")
print(f"    {'D bucket':<12}{'n':>7}{'dDTO':>9}{'dNTO':>9}{'Y':>9}{'Q4 trail margin':>18}")
for lo, hi_, lab in [(1,6,'1-5'),(6,12,'6-11'),(12,20,'12-19'),(20,99,'20+')]:
    g = d[(d.D >= lo) & (d.D < hi_)]
    if len(g) < 50: continue
    print(f"    {lab:<12}{len(g):>7,}{g.dDTO.mean():>+9.3f}{g.dNTO.mean():>+9.3f}"
          f"{g.Y.mean():>+9.3f}{g.q4_trail_margin.mean():>+18.3f}")
