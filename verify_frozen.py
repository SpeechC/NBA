"""Reproduce the frozen backtest from models_frozen.py alone.

Run this after any refactor. If the numbers drift, the frozen spec has been
broken and the forward test is no longer comparable to the record.

Two things this now does that it did not originally:

  * it evaluates DEVELOPMENT GAMES ONLY. When the holdout seasons were added to
    the panel this script kept scoring everything, so it was comparing a
    dev+holdout ROI against a dev-only anchor and would have reported drift that
    was really just the holdout being included.
  * it checks against BACKTEST_CURRENT (the 2017-2026 export) and reports
    BACKTEST (the original vintage) alongside, so a data refresh is visible as a
    data refresh rather than being mistaken for a broken specification.

Run `python check_data_source.py` first -- if the box-score and movement files
disagree, this script will still "pass" on a silently truncated panel.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import data_split as ds
from models_frozen import (BACKTEST, BACKTEST_CURRENT, SPECS, add_pace_terms,
                           walk_forward)
from symmetric_features import build

TOL = 0.05


def main():
    G = add_pace_terms(build())
    print(f"panel {len(G):,} games  {G['date'].min().date()} .. {G['date'].max().date()}")
    print(ds.describe(G).to_string(index=False) + "\n")

    ok = True
    for name, feats in SPECS.items():
        d = G.dropna(subset=feats + ["move_total", "actual_total", "open_total"])
        d = d.sort_values("date").reset_index(drop=True)
        p = walk_forward(d[feats].values, d["move_total"].values.astype(float),
                         d["date"].values)
        d = d.assign(pm=p).dropna(subset=["pm"])

        # score the development era only -- the anchors are development anchors
        dev = ds.dev(d)
        ds.assert_no_holdout(dev, what=f"spec {name} verification")

        print(f"--- spec {name} ({len(feats)} features), development only "
              f"({len(dev):,} games) ---")
        for thr, expected in BACKTEST_CURRENT[name].items():
            s = dev[(dev["pm"].abs() > thr) & (dev["actual_total"] != dev["open_total"])]
            over = (s["actual_total"] > s["open_total"]).values
            win = np.where((s["pm"] > 0).values, over, ~over).astype(float)
            w = win.mean()
            roi = 100 * (w * (100 / 110) - (1 - w))
            good = abs(roi - expected) < TOL
            ok &= good
            print(f"  thr {thr:<5} n={len(win):5d}  ROI {roi:+7.2f}  "
                  f"expected {expected:+7.2f}  {'OK' if good else '*** DRIFT ***'}"
                  f"   (frozen vintage {BACKTEST[name][thr]:+.2f})")

    print("\nFROZEN SPEC VERIFIED" if ok else
          "\n*** SPEC HAS DRIFTED -- investigate before trusting any result ***")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
