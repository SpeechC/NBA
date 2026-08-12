"""Reconcile the 451 vs 537 final-week game counts, and check for totals juice."""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

from prepare_data import CSV, season_label


def main():
    raw = pd.read_csv(CSV, low_memory=False)
    raw["lbl"] = season_label(raw).astype(str)
    d = raw[raw["lbl"].str.contains("Regular Season", na=False)].copy()
    d["date"] = pd.to_datetime(d["DATE"], errors="coerce")
    d["close"] = pd.to_numeric(d["CLOSING TOTAL_H"], errors="coerce")
    d["open"] = pd.to_numeric(d["OPENING TOTAL_H"], errors="coerce")
    d["actual"] = d["PTS_H"] + d["PTS_R"]
    d = d.dropna(subset=["close", "date", "actual"])

    base = d[d["close"].between(150, 300)].copy()
    base["dl"] = (base.groupby("lbl")["date"].transform("max")
                  - base["date"]).dt.days
    print(f"universe A: close in [150,300]              n={len(base):,}")
    print(f"   dl <= 6  (7 distinct days): {int((base['dl']<=6).sum())}")
    print(f"   dl <= 7  (8 distinct days): {int((base['dl']<=7).sum())}")

    b2 = base.dropna(subset=["open"])
    b2 = b2[b2["open"].between(150, 300)].copy()
    b2["dl"] = (b2.groupby("lbl")["date"].transform("max")
                - b2["date"]).dt.days
    print(f"\nuniverse B: close AND open in [150,300]     n={len(b2):,}")
    print(f"   dl <= 6: {int((b2['dl']<=6).sum())}")
    print(f"   dl <= 7: {int((b2['dl']<=7).sum())}")

    print("\nnon-push subsets (resid != 0), universe B:")
    b2["r"] = b2["actual"] - b2["close"]
    for k in (6, 7):
        s = b2[(b2["dl"] <= k) & (b2["r"] != 0)]
        print(f"   dl <= {k}: {len(s)}")

    print("\n--- odds columns: is there totals juice? ---")
    for c in ["CLOSING\nODDS_H", "OPENING ODDS_H", "CLOSING\nODDS_R",
              "OPENING ODDS_R"]:
        if c not in d.columns:
            print(f"  {c!r} absent")
            continue
        v = pd.to_numeric(d[c], errors="coerce")
        print(f"  {c!r:22} cov {100*v.notna().mean():5.1f}%  "
              f"median {v.median()}  p10 {v.quantile(.1)}  p90 {v.quantile(.9)}")


if __name__ == "__main__":
    main()
