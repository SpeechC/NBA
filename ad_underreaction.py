"""A/D market-underreaction residual. Pre-registered in
PREREG_ad_underreaction.md.

Models A and D are frozen and untouched. Their existing walk-forward predictions
of the line move are used as-is.

    dT      = close_total - open_total
    ADUnder = pm - dT

CrewShock and LeagueFoulState are LOADED from ref_features.csv. They are never
rebuilt here.

The decomposition in section (c) is the gate: ADUnder and the closing residual
share -dT, so line reversion alone would produce a positive coefficient. The
claim survives only if the pm coefficient is positive with dT included.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import ref_shock as rsk
from data_split import SPLIT_DATE
from dispersion_priced import ols
from models_frozen import SPECS, add_pace_terms, walk_forward
from symmetric_features import build

FEAT = "ref_features.csv"
CTRL = rsk.CTRL
BE = 110 / 210


def panel():
    G = add_pace_terms(build()).sort_values("date").reset_index(drop=True)
    G["gid"] = G["gid"].astype(str).str.strip()
    for name, feats in SPECS.items():
        d = G.dropna(subset=feats + ["move_total", "actual_total",
                                     "open_total", "close_total"])
        pm = walk_forward(d[feats].values.astype(float),
                          d["move_total"].values.astype(float),
                          d["date"].values)
        G.loc[d.index, f"pm_{name}"] = pm
    G["dT"] = G["close_total"] - G["open_total"]
    G["Residual"] = G["actual_total"] - G["close_total"]
    for name in SPECS:
        G[f"ADUnder_{name}"] = G[f"pm_{name}"] - G["dT"]
    return G


def attach(G):
    f = pd.read_csv(FEAT)
    f["gid"] = f["gid"].astype(str).str.strip()
    f["date"] = pd.to_datetime(f["date"])
    keep = ["gid", "CrewShock", "LeagueFoulState"]
    n0 = len(G)
    m = G.merge(f[keep], on="gid", how="left")
    assert len(m) == n0
    print(f"  MERGE onto frozen ref_features: {n0:,} A/D panel rows -> "
          f"{m['CrewShock'].notna().sum():,} matched, "
          f"{m['CrewShock'].isna().sum():,} unmatched")
    ctl = rsk.build()[["gid"] + CTRL]
    ctl["gid"] = ctl["gid"].astype(str).str.strip()
    m = m.merge(ctl, on="gid", how="left")
    print(f"  MERGE onto team controls: {m[CTRL[0]].notna().sum():,} matched, "
          f"{m[CTRL[0]].isna().sum():,} unmatched")
    return m


def main():
    G = panel()
    d = attach(G)
    need = ["Residual", "dT", "CrewShock", "LeagueFoulState"] + CTRL
    print(f"\n  panel {len(d):,} games")
    rows = []
    for name in SPECS:
        s = d.dropna(subset=need + [f"pm_{name}", f"ADUnder_{name}"]).copy()
        dev = s[s["date"] < SPLIT_DATE]
        hold = s[s["date"] >= SPLIT_DATE]
        U, P = f"ADUnder_{name}", f"pm_{name}"
        print("\n" + "=" * 96)
        print(f"MODEL {name}   n={len(s):,}  develop {len(dev):,}  "
              f"holdout {len(hold):,}")
        print("=" * 96)
        print(f"  pm sd {s[P].std():.3f}   dT sd {s['dT'].std():.3f}   "
              f"ADUnder sd {s[U].std():.3f}   Residual sd {s['Residual'].std():.2f}")
        print(f"  corr(pm, dT) = {np.corrcoef(s[P], s['dT'])[0,1]:+.4f}   "
              f"[the model's own skill at its real target]")

        print("\n  INDEPENDENCE FROM CrewShock")
        for lab, x in (("develop", dev), ("holdout", hold), ("all", s)):
            pr = np.corrcoef(x[U], x["CrewShock"])[0, 1]
            sp = x[[U, "CrewShock"]].corr(method="spearman").iloc[0, 1]
            r2 = pr ** 2
            print(f"    {lab:8} pearson {pr:+.4f}  spearman {sp:+.4f}  "
                  f"R^2 {r2:.5f}")

        print("\n  (a) PRE-REGISTERED   Residual ~ ADUnder")
        for lab, x in (("develop", dev), ("holdout", hold), ("all", s)):
            b, se, t = ols(x["Residual"].values, x[U].values.reshape(-1, 1))
            print(f"    {lab:8} bU {b[1]:+.4f}  se {se[1]:.4f}  t={t[1]:+.2f}")

        print("\n  (b) A/D INFORMATION ALONE   Residual ~ pm")
        for lab, x in (("develop", dev), ("holdout", hold), ("all", s)):
            b, se, t = ols(x["Residual"].values, x[P].values.reshape(-1, 1))
            print(f"    {lab:8} b_pm {b[1]:+.4f}  se {se[1]:.4f}  t={t[1]:+.2f}")

        print("\n  (c) GATE — DECOMPOSITION   Residual ~ pm + dT")
        print("      claim survives only if b_pm > 0 here")
        for lab, x in (("develop", dev), ("holdout", hold), ("all", s)):
            X = np.column_stack([x[P], x["dT"]])
            b, se, t = ols(x["Residual"].values, X)
            print(f"    {lab:8} b_pm {b[1]:+.4f} (t={t[1]:+5.2f})   "
                  f"b_dT {b[2]:+.4f} (t={t[2]:+5.2f})")

        print("\n  c_market vs c_true for ADUnder")
        for lab, x in (("develop", dev), ("holdout", hold), ("all", s)):
            X = np.column_stack([x[U]] + [x[c] for c in
                                          ["LeagueFoulState"] + CTRL])
            bm, _, tm = ols(x["close_total"].values, X)
            bt, _, tt = ols(x["actual_total"].values, X)
            print(f"    {lab:8} c_market {bm[1]:+.4f} (t={tm[1]:+5.2f})   "
                  f"c_true {bt[1]:+.4f} (t={tt[1]:+5.2f})   "
                  f"gap {bt[1]-bm[1]:+.4f}")

        print("\n  ADDITIVE   Residual ~ CrewShock + ADUnder + League + controls")
        for lab, x in (("develop", dev), ("holdout", hold), ("all", s)):
            X = np.column_stack([x["CrewShock"], x[U], x["LeagueFoulState"]]
                                + [x[c] for c in CTRL])
            b, se, t = ols(x["Residual"].values, X)
            Xr = np.column_stack([x["CrewShock"], x["LeagueFoulState"]]
                                 + [x[c] for c in CTRL])
            br, _, tr = ols(x["Residual"].values, Xr)
            print(f"    {lab:8} bR {b[1]:+.4f} (t={t[1]:+5.2f})   "
                  f"bU {b[2]:+.4f} (t={t[2]:+5.2f})   "
                  f"[bR alone {br[1]:+.4f}]")
            rows.append({"model": name, "window": lab, "n": len(x),
                         "bR": round(b[1], 4), "bU": round(b[2], 4),
                         "t_bU": round(t[2], 2),
                         "bR_alone": round(br[1], 4)})

        print("\n  season signs of bU (diagnostic)")
        out = []
        for y, g in s.groupby(s["date"].dt.year):
            if len(g) < 150:
                continue
            X = np.column_stack([g["CrewShock"], g[U], g["LeagueFoulState"]]
                                + [g[c] for c in CTRL])
            b, _, t = ols(g["Residual"].values, X)
            out.append(f"{y}:{b[2]:+.3f}")
        print("    " + "  ".join(out))
    pd.DataFrame(rows).to_csv("additive_incremental_results.csv", index=False)
    print("\n  wrote additive_incremental_results.csv")


if __name__ == "__main__":
    main()
