"""PREREG_move_injury_combined.md -- the SINGLE combined estimate.

  dTotal = a + bR*MOVE_RIDGE_OOS + bL*MOVE_LATENT_OOS + bI*OUT_late + e

Control-free by design, so it is NOT bound by the rolling(20) team-form
warm-up that removed deciles 1-3 of every season from the A/B sample.
Run exactly once. Decision rule is fixed in section 5 of the prereg.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import injury_market as IM
import opening_line_error_decomposition as OLE

SIDECAR = "/mnt/c/NBA2/move_signal_states.csv"


def ols(y, X):
    A = np.column_stack([np.ones(len(y))] + X)
    b, *_ = np.linalg.lstsq(A, y, rcond=None)
    r = y - A @ b
    se = np.sqrt(np.diag(np.linalg.pinv(A.T @ A)) * (r @ r)
                 / (len(y) - A.shape[1]))
    return b, b / se, 1 - r.var() / y.var()


def main():
    # rebuild the injury states, then join WITHOUT rsk.CTRL
    d0 = IM.build()                       # carries the frozen injury states
    cols = ["OUT_late_DEF", "OUT_late_OFF", "UPGRADE_late_DEF",
            "UPGRADE_late_OFF"]
    states = d0[["gid"] + cols]

    g = OLE.load()
    g["gid"] = g["gid"].astype(str).str.strip()
    g = g[(g["season"] >= 2020) & (g["season"] <= 2024)]
    sc = pd.read_csv(SIDECAR)
    sc["gid"] = sc["GAME-ID"].astype(str).str.strip()
    d = g.merge(sc[["gid", "MOVE_RIDGE_OOS", "MOVE_LATENT_OOS"]], on="gid",
                how="left").merge(states, on="gid", how="left")
    d[cols] = d[cols].fillna(0.0)
    d = d.dropna(subset=["MOVE_RIDGE_OOS", "MOVE_LATENT_OOS", "tmove"])
    d["OUT_late"] = d["OUT_late_DEF"] + d["OUT_late_OFF"]
    d["signed"] = d["OUT_late"] - d["UPGRADE_late_DEF"] - d["UPGRADE_late_OFF"]

    print(f"  sample {len(d):,} games   (controlled A/B sample was 3,489)")
    print(f"  by season: {d.groupby('season').size().to_dict()}")
    print(f"  OUT_late fires on {int((d.OUT_late>0).sum()):,} games")
    # confirm the early-season restoration the prereg predicted
    d = d.sort_values(["season", "date"])
    d["dec"] = (d.groupby("season").cumcount()
                / d.groupby("season")["gid"].transform("size") * 10
                ).astype(int) + 1
    e = d[d.dec <= 3]
    print(f"  early-season (deciles 1-3) games now included: {len(e):,}  "
          f"OUT_late fires on {int((e.OUT_late>0).sum()):,} of them")

    print("\n" + "=" * 92)
    print("THE SINGLE COMBINED ESTIMATE")
    print("=" * 92)
    for lab, x in (("development 2020-24", d[d.season <= 2023]),
                   ("holdout 2024-25", d[d.season == 2024])):
        y = x["tmove"].values
        R, L = x.MOVE_RIDGE_OOS.values, x.MOVE_LATENT_OOS.values
        _, _, r2i = ols(y, [R, L])
        b, t, r2j = ols(y, [R, L, x.OUT_late.values])
        bs, ts, r2s = ols(y, [R, L, x.signed.values])
        print(f"\n  {lab}   n={len(x):,}")
        print(f"    ridge   {b[1]:+.4f} (t={t[1]:+.2f})")
        print(f"    latent  {b[2]:+.4f} (t={t[2]:+.2f})")
        print(f"    OUT_late{b[3]:+.4f} (t={t[3]:+.2f})   <- bI")
        print(f"    R2 incumbents {r2i:+.5f}  ->  joint {r2j:+.5f}   "
              f"incremental {r2j-r2i:+.5f}")
        print(f"    [secondary, not promoted] signed variant "
              f"{bs[3]:+.4f} (t={ts[3]:+.2f})  incr {r2s-r2i:+.5f}")
    print("\n  decision rule (prereg s5): |t(bI)|>=2 both windows same sign; "
          "both incumbents |t|>=2; incremental R2 >= +0.010 on HOLDOUT")


if __name__ == "__main__":
    main()
