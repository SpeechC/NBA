"""Diagnostics on the PREREG_injury.md market run: (1) where the sample went,
(2) the incremental content of Hypothesis B beyond the frozen movement pair."""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import injury_market as IM
import opening_line_error_decomposition as OLE
import ref_shock as rsk


def ols(y, X):
    A = np.column_stack([np.ones(len(y))] + X)
    b, *_ = np.linalg.lstsq(A, y, rcond=None)
    r = y - A @ b
    se = np.sqrt(np.diag(np.linalg.pinv(A.T @ A)) * (r @ r)
                 / (len(y) - A.shape[1]))
    return b, b / se, 1 - r.var() / y.var()


g = OLE.load()
g = g[(g["season"] >= 2020) & (g["season"] <= 2024)]
ctl = rsk.build()[["gid"] + rsk.CTRL]
ctl["gid"] = ctl["gid"].astype(str).str.strip()
m = g.merge(ctl, on="gid", how="left")
print("=" * 84)
print("SAMPLE LOSS — which control is missing")
print("=" * 84)
print(f"  games in window            {len(g):,}")
print(f"  after control merge, complete {int(m[rsk.CTRL].notna().all(1).sum()):,}")
for c in rsk.CTRL:
    miss = int(m[c].isna().sum())
    if miss:
        print(f"    {c:26} missing on {miss:,}")
print("  by season (complete / total):")
for s, x in m.groupby("season"):
    print(f"    {s}  {int(x[rsk.CTRL].notna().all(1).sum()):>6,} / {len(x):>6,}")

d = IM.build()
print("\n" + "=" * 84)
print("HYPOTHESIS B — incremental content and orthogonality")
print("=" * 84)
d["late_signed"] = (d["OUT_late_DEF"] + d["OUT_late_OFF"]
                    - d["UPGRADE_late_DEF"] - d["UPGRADE_late_OFF"])
d["out_late"] = d["OUT_late_DEF"] + d["OUT_late_OFF"]
d["upg_late"] = d["UPGRADE_late_DEF"] + d["UPGRADE_late_OFF"]
for lab, x in (("development", d[d.season <= 2023]),
               ("holdout 2024-25", d[d.season == 2024])):
    h = x.dropna(subset=["MOVE_RIDGE_OOS", "MOVE_LATENT_OOS"])
    y = h["tmove"].values
    _, _, r2i = ols(y, [h.MOVE_RIDGE_OOS.values, h.MOVE_LATENT_OOS.values])
    _, _, r2j = ols(y, [h.MOVE_RIDGE_OOS.values, h.MOVE_LATENT_OOS.values,
                        h.late_signed.values])
    bs, ts, _ = ols(y, [h.MOVE_RIDGE_OOS.values, h.MOVE_LATENT_OOS.values,
                        h.out_late.values, h.upg_late.values])
    print(f"\n  {lab}  n={len(h):,}")
    print(f"    incumbents R2 {r2i:+.5f}   + LATE {r2j:+.5f}   "
          f"incremental {r2j-r2i:+.5f}")
    print(f"    split:  OUT_late {bs[3]:+.3f} (t={ts[3]:+.2f})   "
          f"UPGRADE_late {bs[4]:+.3f} (t={ts[4]:+.2f})")
    for nm in ("MOVE_RIDGE_OOS", "MOVE_LATENT_OOS"):
        b, t, _ = ols(h[nm].values, [h.late_signed.values])
        print(f"    {nm:16} ~ LATE:  {b[1]:+.4f} (t={t[1]:+.2f})"
              f"   [~0 => orthogonal, not already encoded]")
