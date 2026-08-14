"""Diagnostics on the Y1 result from residual_screen2.py before believing it.

Three ways it could be spurious, in the order they are most likely:

  1 INDEX ALIGNMENT. The per-team panel is built by concatenating the home and
    away views of the same frame, so it carries DUPLICATE index labels. Feature
    columns are then assigned from a groupby-transform. If pandas aligned on a
    duplicated index anywhere, features would be silently scrambled. Rebuilt
    here with a clean RangeIndex and compared value-for-value.

  2 BETWEEN-SEASON DRIFT. Quintiles are formed on predictions POOLED across
    test seasons. If later seasons have both higher predictions and higher
    realised e, the pooled table shows separation that is entirely a
    season-level effect and worthless within any single season. Recomputed
    with quintiles formed WITHIN each test season.

  3 CHANCE / procedure artifact. The whole walk-forward is rerun on residuals
    permuted within season, which destroys any real game-level signal while
    preserving season means, feature distributions and the fitting procedure.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

import residual_screen2 as R

NPERM = 300
RNG = np.random.default_rng(7)


def clean_features(d, P, use_pbp):
    """Same as R.features but with the duplicate index removed first."""
    P = P.sort_values("date").reset_index(drop=True)
    return R.features(d, P, use_pbp)


def main():
    d, P = R.build()
    print("=" * 96)
    print("1 — INDEX ALIGNMENT")
    print("=" * 96)
    print(f"  panel index has duplicates: {P.index.has_duplicates}  "
          f"({len(P):,} rows, {P.index.nunique():,} distinct labels)")
    z_old, feats = R.features(d, P, False)
    z_new, _ = clean_features(d, P, False)
    z_old = z_old.dropna(subset=feats + ["e"]).sort_values("gid")
    z_new = z_new.dropna(subset=feats + ["e"]).sort_values("gid")
    same_rows = len(z_old) == len(z_new) and (z_old["gid"].values ==
                                              z_new["gid"].values).all()
    print(f"  same rows survive: {same_rows}  ({len(z_old):,} vs {len(z_new):,})")
    if same_rows:
        bad = [c for c in feats
               if not np.allclose(z_old[c].values, z_new[c].values,
                                  equal_nan=True)]
        print(f"  feature columns that differ: {len(bad)} of {len(feats)}"
              + (f"  -> {bad[:6]}" if bad else "   [clean]"))
    z = z_new

    print("\n" + "=" * 96)
    print("2 — BETWEEN-SEASON DRIFT")
    print("=" * 96)
    Pz = R.walk(z, feats, "e", "ridge")
    print("  per test season: does the model separate WITHIN the season?")
    print(f"    {'season':8} {'n':>6} {'mean e':>8} {'mean pred':>10}"
          f" {'Q5-Q1 e':>9} {'Q5 over%':>9} {'Q1 over%':>9}")
    rows = []
    for y, g in Pz.groupby("yr"):
        g = g.copy()
        g["q"] = pd.qcut(g["pred"], 5, labels=[1, 2, 3, 4, 5], duplicates="drop")
        q = g.groupby("q", observed=True)
        e5 = q["e"].mean().iloc[-1] - q["e"].mean().iloc[0]
        o5 = 100 * (q.apply(lambda s: (s["e"] > 0).mean())).iloc[-1]
        o1 = 100 * (q.apply(lambda s: (s["e"] > 0).mean())).iloc[0]
        rows.append({"yr": y, "n": len(g), "e": g["e"].mean(),
                     "pred": g["pred"].mean(), "d": e5, "o5": o5, "o1": o1})
        print(f"    {y:<8} {len(g):>6,} {g['e'].mean():>8.3f} "
              f"{g['pred'].mean():>10.3f} {e5:>9.3f} {o5:>9.2f} {o1:>9.2f}")
    T = pd.DataFrame(rows)
    rb = np.corrcoef(T["pred"], T["e"])[0, 1]
    print(f"\n  between-season corr(season mean pred, season mean e) = {rb:+.4f}"
          f"   over {len(T)} seasons")
    print(f"  seasons with positive within-season Q5-Q1: "
          f"{(T['d'] > 0).sum()} of {len(T)}")
    dm = Pz.copy()
    dm["e_dm"] = dm["e"] - dm.groupby("yr")["e"].transform("mean")
    dm["p_dm"] = dm["pred"] - dm.groupby("yr")["pred"].transform("mean")
    r = np.corrcoef(dm["p_dm"], dm["e_dm"])[0, 1]
    t = r * np.sqrt(len(dm) - 2) / np.sqrt(1 - r * r)
    r0 = np.corrcoef(Pz["pred"], Pz["e"])[0, 1]
    print(f"  pooled corr {r0:+.4f}   ->  WITHIN-SEASON corr {r:+.4f}  t={t:+.2f}")

    print("\n  within-season-demeaned quintiles (the honest table)")
    dm["q"] = dm.groupby("yr")["pred"].transform(
        lambda s: pd.qcut(s, 5, labels=False, duplicates="drop"))
    out = []
    for q, g in dm.groupby("q", observed=True):
        ov = (g["e"] > 0).mean()
        out.append({"Q": int(q) + 1, "n": len(g),
                    "actual e": round(g["e"].mean(), 3),
                    "over %": round(100 * ov, 2),
                    "1.96se": round(100 * 1.96 * np.sqrt(ov * (1 - ov) / len(g)), 2)})
    print(pd.DataFrame(out).to_string(index=False))

    print("\n" + "=" * 96)
    print("3 — PERMUTATION NULL on the whole walk-forward")
    print("=" * 96)
    obs = r0
    yrs = z["yr"].values
    blocks = [np.where(yrs == u)[0] for u in np.unique(yrs)]
    e0 = z["e"].values.copy()
    null = np.empty(NPERM)
    zz = z.copy()
    for k in range(NPERM):
        ep = e0.copy()
        for b in blocks:
            ep[b] = e0[b][RNG.permutation(len(b))]
        zz["e"] = ep
        Pp = R.walk(zz, feats, "e", "ridge")
        null[k] = np.corrcoef(Pp["pred"], Pp["e"])[0, 1]
    p = (1 + np.sum(null >= obs)) / (NPERM + 1)
    print(f"  observed pooled corr {obs:+.4f}")
    print(f"  null over {NPERM} within-season residual permutations: "
          f"mean {null.mean():+.4f}  sd {null.std():.4f}  "
          f"95th {np.percentile(null, 95):+.4f}")
    print(f"  p = {p:.4f}")

    print("\n" + "=" * 96)
    print("4 — WHICH FEATURES CARRY IT?")
    print("=" * 96)
    tr = z[z["yr"] <= 2023]
    sc = StandardScaler().fit(tr[feats])
    m = Ridge(alpha=200.0).fit(sc.transform(tr[feats]), tr["e"])
    C = pd.DataFrame({"feature": feats, "coef": m.coef_}).reindex(
        np.argsort(-np.abs(m.coef_)))
    print(C.head(12).to_string(index=False))
    print("\n  market-state features only (total, spread, abs_spread):")
    mk = ["total", "spread", "abs_spread"]
    Pm = R.walk(z, mk, "e", "ridge")
    rm = np.corrcoef(Pm["pred"], Pm["e"])[0, 1]
    Pm["e_dm"] = Pm["e"] - Pm.groupby("yr")["e"].transform("mean")
    Pm["p_dm"] = Pm["pred"] - Pm.groupby("yr")["pred"].transform("mean")
    rmw = np.corrcoef(Pm["p_dm"], Pm["e_dm"])[0, 1]
    print(f"    pooled corr {rm:+.4f}   within-season corr {rmw:+.4f}")
    proc = [c for c in feats if c not in mk]
    Pp2 = R.walk(z, proc, "e", "ridge")
    rp = np.corrcoef(Pp2["pred"], Pp2["e"])[0, 1]
    Pp2["e_dm"] = Pp2["e"] - Pp2.groupby("yr")["e"].transform("mean")
    Pp2["p_dm"] = Pp2["pred"] - Pp2.groupby("yr")["pred"].transform("mean")
    rpw = np.corrcoef(Pp2["p_dm"], Pp2["e_dm"])[0, 1]
    print(f"  process features only ({len(proc)}):")
    print(f"    pooled corr {rp:+.4f}   within-season corr {rpw:+.4f}")


if __name__ == "__main__":
    main()
