"""Reproduce the frozen backtest from models_frozen.py alone.

Run this after any refactor. If the numbers drift, the frozen spec has been
broken and the forward test is no longer comparable to the record.
"""
import numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore")
from models_frozen import SPECS, BACKTEST, add_pace_terms, walk_forward
from symmetric_features import build

def main():
    G = add_pace_terms(build())
    print(f"sample {len(G):,} games  {G['date'].min().date()} .. {G['date'].max().date()}\n")
    ok = True
    for name, feats in SPECS.items():
        d = G.dropna(subset=feats + ["move_total", "actual_total", "open_total"]).reset_index(drop=True)
        p = walk_forward(d[feats].values, d["move_total"].values.astype(float), d["date"].values)
        d = d.assign(pm=p).dropna(subset=["pm"])
        print(f"--- spec {name} ({len(feats)} features) ---")
        for thr, expected in BACKTEST[name].items():
            s = d[(d["pm"].abs() > thr) & (d["actual_total"] != d["open_total"])]
            over = (s["actual_total"] > s["open_total"]).values
            win = np.where((s["pm"] > 0).values, over, ~over).astype(float)
            w = win.mean()
            roi = 100 * (w * (100 / 110) - (1 - w))
            flag = "OK" if abs(roi - expected) < 0.05 else "*** DRIFT ***"
            ok &= abs(roi - expected) < 0.05
            print(f"  thr {thr:<5} n={len(win):5d}  ROI {roi:+7.2f}  expected {expected:+7.2f}  {flag}")
    print("\nFROZEN SPEC VERIFIED" if ok else "\n*** SPEC HAS DRIFTED ***")

if __name__ == "__main__":
    main()
