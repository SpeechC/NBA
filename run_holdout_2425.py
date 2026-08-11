"""Execute the pre-registered 2024-25 holdout. Run once, when the odds arrive.

Reads PREREGISTRATION.md's fixed protocol: frozen spec A, threshold 1.25, bets
struck and graded at the opening total, CLV as the primary metric.

Usage:
    python run_holdout_2425.py --odds /path/to/dfMaster_with_2425.csv

The odds file must contain the 2024-25 regular season in the same schema as
dfMaster_OT.csv. Nothing in this script tunes anything.
"""
import argparse, warnings
import numpy as np, pandas as pd
from scipy import stats
warnings.filterwarnings("ignore")

THRESH = 1.25
ANCHOR = {"CLV": 1.844, "beat_close": 66.6, "win": 54.05, "ROI": 3.18}
PASS, AMBIG = 1.2, 0.4


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--odds", required=True, help="odds csv including 2024-25")
    a = ap.parse_args()

    import prepare_data
    prepare_data.CSV = a.odds                      # point the pipeline at new data
    from models_frozen import SPECS, add_pace_terms, walk_forward
    from symmetric_features import build

    G = add_pace_terms(build())
    feats = SPECS["A"]
    G = G.dropna(subset=feats + ["move_total", "actual_total", "open_total"])
    G = G.sort_values("date").reset_index(drop=True)
    G["pm"] = walk_forward(G[feats].values, G["move_total"].values.astype(float),
                           G["date"].values)
    d = G.dropna(subset=["pm"])
    ho = d[d["season"].astype(str).str.contains("2024-2025|2024-25")]
    if len(ho) == 0:
        raise SystemExit("no 2024-25 games found — check the season label in the odds file")

    s = ho[(ho["pm"].abs() > THRESH) & (ho["actual_total"] != ho["open_total"])]
    over = (s["actual_total"] > s["open_total"]).values
    win = np.where((s["pm"] > 0).values, over, ~over).astype(float)
    n, w = len(win), win.mean()
    clv = np.where(s["pm"] > 0, s["move_total"], -s["move_total"])
    se = clv.std() / np.sqrt(n)
    lo, hi = clv.mean() - 1.96 * se, clv.mean() + 1.96 * se
    wl, wh = stats.beta.ppf([.025, .975], win.sum() + .5, n - win.sum() + .5)

    print(f"2024-25 HOLDOUT — pre-registered, frozen spec A, threshold {THRESH}")
    print(f"  games in season       {len(ho):,}   bets {n}  "
          f"(selection {100*n/len(ho):.1f}%)")
    print(f"\n  PRIMARY  CLV         {clv.mean():+.3f}  95% CI [{lo:+.3f}, {hi:+.3f}]"
          f"   (anchor {ANCHOR['CLV']:+.3f})")
    verdict = ("PASS" if clv.mean() >= PASS and lo > 0 else
               "AMBIGUOUS" if clv.mean() >= AMBIG and lo > 0 else "FAIL")
    print(f"  VERDICT              {verdict}")
    print(f"\n  secondary:")
    print(f"    beat close         {100*(clv>0).mean():.1f}%   (anchor {ANCHOR['beat_close']}%)")
    print(f"    win rate           {100*w:.2f}%  95% CI [{100*wl:.2f}, {100*wh:.2f}]"
          f"   (anchor {ANCHOR['win']}%)")
    roi = w*(100/110)-(1-w)
    print(f"    ROI -110           {100*roi:+.2f}%   (anchor {ANCHOR['ROI']:+.2f}%)")
    print(f"\n  NOTE: at n={n} the win-rate interval spans break-even by construction.")
    print(f"  ROI is reported, not decisive. CLV is the test.")
    s.to_csv("holdout_2425_bets.csv", index=False)


if __name__ == "__main__":
    main()
