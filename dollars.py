"""$won. Every variant, both prices. No proxy metrics.

Quadratic capped staking, $100 unit (staking.py). Bets struck at the OPENING
total. Pushes pay nothing. Development is 6 seasons, holdout is 2.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import data_split as ds
import staking

DEV_SEASONS, HO_SEASONS = 6, 2


def main():
    rows, per_season = [], []
    for spec in ("A", "D"):
        d = pd.read_csv(f"staking_bets_{spec}.csv", parse_dates=["date"])
        d = ds.tag(d)
        for thr in (0.0, 0.75, 1.25):
            sel = d[d["pm"].abs() > thr]
            for price in ("-110", "-105"):
                b = staking.settle(sel, price=price)
                b = ds.tag(b)
                dev, ho = b[~b["is_holdout"]], b[b["is_holdout"]]
                for lab, s, nseas in (("DEV", dev, DEV_SEASONS),
                                      ("HOLDOUT", ho, HO_SEASONS)):
                    live = s[~s["push"]]
                    risked = live["stake_$"].sum()
                    won = s["$won"].sum()
                    rows.append({
                        "spec": spec, "thr": thr, "price": price, "set": lab,
                        "bets": len(s), "risked $": round(risked),
                        "$won": round(won),
                        "$/season": round(won / nseas),
                        "ROI %": round(100 * won / risked, 2) if risked else np.nan,
                        "win %": round(100 * live["won"].mean(), 2),
                    })
            if thr in (0.75, 1.25):
                b = ds.tag(staking.settle(sel, price="-110"))
                for s, sub in b.groupby("season_lbl"):
                    per_season.append({
                        "spec": spec, "thr": thr, "season": s,
                        "set": "HOLDOUT" if sub["is_holdout"].iloc[0] else "dev",
                        "$won": round(sub["$won"].sum())})

    t = pd.DataFrame(rows)
    print("=" * 104)
    print("$won — quadratic capped staking, $100 unit")
    print("=" * 104)
    for price in ("-110", "-105"):
        print(f"\n--- priced at {price} ---")
        print(t[t["price"] == price].drop(columns=["price"]).to_string(index=False))

    print("\n" + "=" * 104)
    print("Season by season at -110")
    print("=" * 104)
    p = pd.DataFrame(per_season)
    piv = p.pivot_table(index=["season"], columns=["spec", "thr"],
                        values="$won", aggfunc="sum")
    print(piv.to_string())
    t.to_csv("dollars.csv", index=False)


if __name__ == "__main__":
    main()
