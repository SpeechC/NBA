"""$won by season for every spec, at the 0.75 level.

Quadratic capped staking (staking.py), $100 unit, graded at -110 on the opening
total. Bets are placed where |pred| > 0.75; stake is min(pred^2, 3) units.

NOTE ON 0.75: this level was identified by inspecting holdout results, so figures
below the 1.25 pre-registered threshold are exploratory. They are reported at the
user's direction and are not a pre-registered test. 1.25 is shown alongside for
reference.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import data_split as ds
import staking
from models_frozen import (BOX, MARKET, PACE_EFF, PACE_TERMS, SPECS,
                           add_pace_terms, walk_forward)
from symmetric_features import build

LEVEL = 0.75

MODELS = {
    "A": SPECS["A"],
    "D": SPECS["D"],
    "B": (MARKET + [f"h_f_{v}" for v in BOX + PACE_EFF]
          + [f"a_f_{v}" for v in BOX + PACE_EFF]),
    "C": (MARKET + [f"h_f_{v}" for v in BOX + PACE_EFF]
          + [f"a_f_{v}" for v in BOX + PACE_EFF] + PACE_TERMS),
    "A_nodis": [f for f in SPECS["A"] if f != "dis_open"],
    "D_nodis": [f for f in SPECS["D"] if f != "dis_open"],
}


def season_of(d):
    y = d["date"].dt.year
    return np.where(d["date"].dt.month >= 7,
                    y.astype(str) + "-" + (y + 1).astype(str),
                    (y - 1).astype(str) + "-" + y.astype(str))


def main():
    G = add_pace_terms(build()).sort_values("date").reset_index(drop=True)
    pnl, detail = {}, []

    for name, feats in MODELS.items():
        d = G.dropna(subset=feats + ["move_total", "actual_total", "open_total"])
        d = d.sort_values("date").reset_index(drop=True)
        d["pm"] = walk_forward(d[feats].values,
                               d["move_total"].values.astype(float),
                               d["date"].values)
        d = d.dropna(subset=["pm"]).copy()
        d["season_lbl"] = season_of(d)

        for lvl in (LEVEL, 1.25):
            sel = d[d["pm"].abs() > lvl].copy()
            b = ds.tag(staking.settle(sel, price="-110"))
            if lvl == LEVEL:
                pnl[name] = b.groupby("season_lbl")["$won"].sum()
            for s, sub in b.groupby("season_lbl"):
                live = sub[~sub["push"]]
                detail.append({
                    "model": name, "level": lvl, "season": s,
                    "set": "HOLDOUT" if sub["is_holdout"].iloc[0] else "dev",
                    "bets": len(sub), "risked $": round(live["stake_$"].sum(), 2),
                    "$won": round(sub["$won"].sum(), 2),
                    "win %": round(100 * live["won"].mean(), 2) if len(live) else np.nan})
        print(f"  done {name}", flush=True)

    tab = pd.DataFrame(pnl).round(2)
    hold = ds.HOLDOUT_SEASONS
    tab.index = [f"{s}  {'<< OUT OF SAMPLE' if s in hold else ''}" for s in tab.index]

    print("\n" + "=" * 104)
    print(f"$won BY SEASON — quadratic capped staking, $100 unit, -110, level {LEVEL}")
    print("=" * 104)
    print(tab.to_string())

    raw = pd.DataFrame(pnl)
    dev_m = raw.loc[[s for s in raw.index if s not in hold]].sum()
    ho_m = raw.loc[[s for s in raw.index if s in hold]].sum()
    print("\n" + "-" * 104)
    print(pd.DataFrame({"DEV total $": dev_m.round(2),
                        "HOLDOUT total $": ho_m.round(2),
                        "ALL $": (dev_m + ho_m).round(2)}).to_string())

    det = pd.DataFrame(detail)
    det.to_csv("season_pnl.csv", index=False)
    print("\n\n=== supporting detail, level 0.75 ===")
    print(det[det["level"] == LEVEL].to_string(index=False))
    print("\n=== same at the pre-registered 1.25, for reference ===")
    print(det[det["level"] == 1.25]
          .pivot_table(index="season", columns="model", values="$won")
          .round(2).to_string())


if __name__ == "__main__":
    main()
