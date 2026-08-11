"""Are A and D still the best specs on the rebuilt 2017-start panel?

The panel changed materially today (7,335 -> 8,696 games) and `dis_open` is
noisier because its burn-in was cut. Both are reasons the earlier spec ranking
might not survive, so it is re-run rather than assumed.

DEVELOPMENT ONLY. Choosing a spec is selection; the holdout may not inform it.

Includes two specs the earlier work never tested, and which today's changes make
worth asking about:

  A_nodis / D_nodis -- the frozen specs with `dis_open` REMOVED.

That matters beyond accuracy. `dis_open` is a walk-forward model output, and
producing it costs ~250 games of burn-in off the front of the panel plus two
whole modelling stages (an XGBoost score model and a calibration). It ranked
15th of 21 by coefficient in spec A. If dropping it is close to free, the panel
could start at 2017-10-25 -- the hard feature floor -- and the pipeline would
lose its most fragile component.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import data_split as ds
from models_frozen import (BOX, MARKET, PACE_EFF, PACE_TERMS, SPECS,
                           add_pace_terms, walk_forward)
from symmetric_features import build

THR = 1.25

CANDIDATES = {
    "A  (frozen, 21)": SPECS["A"],
    "D  (frozen, 15)": SPECS["D"],
    "B  (symmetric, 34)": (MARKET + [f"h_f_{v}" for v in BOX + PACE_EFF]
                           + [f"a_f_{v}" for v in BOX + PACE_EFF]),
    "C  (symmetric+pace, 41)": (MARKET + [f"h_f_{v}" for v in BOX + PACE_EFF]
                                + [f"a_f_{v}" for v in BOX + PACE_EFF] + PACE_TERMS),
    "A_nodis (20)": [f for f in SPECS["A"] if f != "dis_open"],
    "D_nodis (14)": [f for f in SPECS["D"] if f != "dis_open"],
    "market only (2)": list(MARKET),
    "open_total only (1)": ["open_total"],
}


def main():
    G = add_pace_terms(build()).sort_values("date").reset_index(drop=True)
    rows = []
    for name, feats in CANDIDATES.items():
        miss = [f for f in feats if f not in G.columns]
        if miss:
            print(f"SKIP {name}: missing {miss}")
            continue
        d = G.dropna(subset=feats + ["move_total", "actual_total", "open_total"])
        d = d.sort_values("date").reset_index(drop=True)
        d["pm"] = walk_forward(d[feats].values,
                               d["move_total"].values.astype(float),
                               d["date"].values)
        d = d.dropna(subset=["pm"])

        dev = ds.dev(d)
        ds.assert_no_holdout(dev, what=f"spec comparison ({name})")

        corr = np.corrcoef(dev["pm"], dev["move_total"])[0, 1]
        b = dev[(dev["pm"].abs() > THR) & (dev["actual_total"] != dev["open_total"])]
        over = (b["actual_total"] > b["open_total"]).values
        win = np.where((b["pm"] > 0).values, over, ~over).astype(float)
        clv = np.where(b["pm"] > 0, b["move_total"], -b["move_total"])
        w = win.mean()
        se = clv.std() / np.sqrt(len(clv))
        rows.append({"spec": name, "k": len(feats), "dev games": len(dev),
                     "corr": round(corr, 4), "bets": len(b),
                     "CLV": round(clv.mean(), 3),
                     "CLV lo": round(clv.mean() - 1.96 * se, 3),
                     "beat%": round(100 * (clv > 0).mean(), 2),
                     "win%": round(100 * w, 2),
                     "ROI110": round(100 * (w * (100 / 110) - (1 - w)), 2)})
        print(f"  done {name}", flush=True)

    t = pd.DataFrame(rows).sort_values("CLV", ascending=False)
    print("\n" + "=" * 110)
    print(f"SPEC COMPARISON — development only, frozen estimator, threshold {THR}")
    print("=" * 110)
    print(t.to_string(index=False))
    t.to_csv("spec_recheck.csv", index=False)


if __name__ == "__main__":
    main()
