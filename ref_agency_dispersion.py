"""Referee agency in the Q4 deficit response — executes PREREG_ref_agency_dispersion.md.

Estimand is a VARIANCE: do per-official deficit slopes disperse beyond noise?
Null: permute official labels WITHIN SEASON (preserves every game-level fact and
every official's game count; destroys only referee identity).
"""
import warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
from foul_q4 import build

MING, NPERM = 150, 5000              # FROZEN in the prereg
RNG = np.random.default_rng(42)


def slopes(code, K, D, F, y, n_min):
    """beta on D from y ~ 1 + D + F, per group, via batched 3x3 normal equations."""
    bc = lambda w: np.bincount(code, weights=w, minlength=K)
    n = np.bincount(code, minlength=K).astype(float)
    sD, sF, sy = bc(D), bc(F), bc(y)
    sDD, sDF, sFF = bc(D * D), bc(D * F), bc(F * F)
    sDy, sFy = bc(D * y), bc(F * y)
    XtX = np.empty((K, 3, 3)); Xty = np.empty((K, 3))
    XtX[:, 0, 0] = n;   XtX[:, 0, 1] = sD;  XtX[:, 0, 2] = sF
    XtX[:, 1, 0] = sD;  XtX[:, 1, 1] = sDD; XtX[:, 1, 2] = sDF
    XtX[:, 2, 0] = sF;  XtX[:, 2, 1] = sDF; XtX[:, 2, 2] = sFF
    Xty[:, 0] = sy; Xty[:, 1] = sDy; Xty[:, 2] = sFy
    ok = n >= n_min
    b = np.full(K, np.nan)
    if ok.sum():
        try:
            sol = np.linalg.solve(XtX[ok], Xty[ok][..., None])
            b[ok] = sol[:, 1, 0]
        except np.linalg.LinAlgError:
            for j in np.where(ok)[0]:
                b[j] = np.linalg.lstsq(XtX[j], Xty[j], rcond=None)[0][1]
    return b, n


def wvar(b, n):
    m = np.isfinite(b)
    w = n[m] / n[m].sum()
    mu = np.sum(w * b[m])
    return float(np.sum(w * (b[m] - mu) ** 2)), float(mu), int(m.sum())


g = build(drop_last3=True)
g["gid"] = g.gid.astype(str).str.strip()
rf = pd.read_csv("ref_features.csv"); rf["gid"] = rf.gid.astype(str).str.strip()
j = g.merge(rf[["gid", "ref1", "ref2", "ref3"]], on="gid", how="inner")
long = pd.concat([j[["gid", "season", "D", "dFTA", "dFGA", "dNTO"]]
                  .assign(ref=j[f"ref{i}"]) for i in (1, 2, 3)]).dropna(subset=["ref"])
long = long.reset_index(drop=True)
codes, uniq = pd.factorize(long.ref); K = len(uniq)
D = long.D.values.astype(float); F = long.dFGA.values.astype(float)
yF = long.dFTA.values.astype(float); yN = long.dNTO.values.astype(float)
seas = pd.factorize(long.season)[0]
print(f"official-games {len(long):,}   officials {K}   seasons {seas.max()+1}")

# ---- P0 --------------------------------------------------------------------
X = np.column_stack([np.ones(len(long)), D, F])
bp = np.linalg.lstsq(X, yF, rcond=None)[0]
print(f"\n=== P0 POSITIVE CONTROL ===")
print(f"    pooled dFTA ~ D | dFGA  = {bp[1]:+.5f}   (prereg expects ~ +0.047)")
mD = long.groupby("ref").D.agg(["mean", "size"])
mD = mD[mD["size"] >= MING]
print(f"    BALANCE: mean D by official, {len(mD)} officials with >={MING} games")
print(f"      range {mD['mean'].min():.2f} - {mD['mean'].max():.2f}   "
      f"sd {mD['mean'].std():.3f}   pooled mean {long.D.mean():.2f}")

def run(y, lab, one_sided=True):
    b, n = slopes(codes, K, D, F, y, MING)
    V, mu, nof = wvar(b, n)
    null = np.empty(NPERM)
    for i in range(NPERM):
        pc = codes.copy()
        for s in range(seas.max() + 1):
            m = seas == s
            pc[m] = RNG.permutation(pc[m])          # preserves per-season counts
        bb, nn = slopes(pc, K, D, F, y, MING)
        null[i] = wvar(bb, nn)[0]
    p = (1 + np.sum(null >= V)) / (NPERM + 1)
    print(f"\n    {lab}")
    print(f"      officials used {nof}   mean slope {mu:+.5f}   "
          f"observed slope sd {np.sqrt(V):.5f}")
    print(f"      V_obs {V:.6e}   null median {np.median(null):.6e}  "
          f"95th pct {np.percentile(null,95):.6e}")
    print(f"      p = {p:.4f}   -> {'ABOVE null' if p < 0.05 else 'not above null'}")
    return V, null, p, np.sqrt(V)

print("\n=== P1 PRIMARY — dispersion of the dFTA deficit slope ===")
V1, n1, p1, sd1 = run(yF, "dFTA slope dispersion")
print("\n=== P2 PLACEBO — dNTO (no whistle; a ref cannot cause a bad pass) ===")
V2, n2, p2, sd2 = run(yN, "dNTO slope dispersion")

print("\n=== VERDICT (prereg §6) ===")
a1, a2 = p1 < 0.05, p2 < 0.05
if a1 and not a2:  v = "REFEREE AGENCY SUPPORTED"
elif a1 and a2:    v = "VOID — placebo also fires; statistic is confounded"
elif not a1 and not a2: v = "no agency detectable AT THIS POWER"
else:              v = "VOID — placebo fires without the primary"
print(f"    P1 {'above' if a1 else 'not above'} | P2 placebo "
      f"{'ALSO ABOVE' if a2 else 'clean'}  ->  {v}")
imp = np.sqrt(np.median(n1))
print(f"\n    implied noise-only slope sd {imp:.5f}; observed {sd1:.5f}; "
      f"excess {max(sd1**2-np.median(n1),0)**0.5 if sd1**2>np.median(n1) else 0:.5f}")
print(f"    MDE per prereg §3: dispersion sd below ~0.015 (~30% of the "
      f"{bp[1]:+.4f} mean) is unresolvable")
