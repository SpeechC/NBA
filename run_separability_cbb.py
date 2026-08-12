"""Apply G4c (conditional separability) to NCAAB 2023-24, totals and moneyline.

PRE-REGISTERED. Feature set fixed at 9 economically motivated variables before
running; one model (L2 logistic, C=0.1); walk-forward expanding window; no
variant tried, no feature selection.

⚠ One season held, so the permutation strata are PRICE ONLY. With more seasons
the null must also stratify by season.
"""
import numpy as np
import pandas as pd

from cbb_model_test import build
from cbb_load import XLSX, SHEET
from gate_separability import walk_forward, report

# 9 features, all pre-game, all economically motivated
FEATS = [
    "pace_sum",      # expected possessions -> scoring environment
    "oeff_sum",      # combined offensive quality
    "deff_sum",      # combined defensive quality
    "oeff_diff",     # mismatch in offence
    "deff_diff",     # mismatch in defence
    "rest_diff",     # schedule spot
    "close_total",   # the line itself (level effects)
    "abs_spread",    # mismatch size
    "exp_total",     # crude pace x efficiency prior
]

BE_TOTALS = 0.5238        # -110, the obtainable price
FLOOR_PP = 0.73           # G6 minimum viable edge, 6123 games/season, 6-yr life


def main():
    g, _ = build()
    g = g.copy()
    g["won"] = (g.total_pts > g.close_total).astype(int)   # over hits
    # price strata for the permutation null: quintiles of the closing total
    g["price_stratum"] = pd.qcut(g.close_total, 5, labels=False,
                                 duplicates="drop").astype(str)
    g["season"] = "2023-24"

    print("#" * 78)
    print("G4c — CONDITIONAL SEPARABILITY, NCAAB 2023-24")
    print("#" * 78)
    print(f"games: {len(g)}   features: {len(FEATS)}   "
          f"walk-forward expanding window")

    d = walk_forward(g, FEATS, "won")
    print(f"walk-forward predictions on {len(d)} games "
          f"(first 1200 used for initial training)")

    report(d, "NCAAB totals — P(over), sorted by predicted probability",
           BE_TOTALS, FLOOR_PP, ["season", "price_stratum"], seed=7)

    # sanity: the same table IN SAMPLE, to show what overfitting looks like
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import make_pipeline
    m = make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=2000))
    m.fit(g[FEATS].values, g.won.values)
    g["p_hat"] = m.predict_proba(g[FEATS].values)[:, 1]
    from gate_separability import bucket_table
    print("\n" + "-" * 78)
    print("IN-SAMPLE version of the same table (NOT a result — shown for contrast)")
    print("-" * 78)
    print(bucket_table(g).to_string())
    print("\nIf the in-sample table separates and the walk-forward one does not,")
    print("that gap IS the finding: the ranking does not generalise.")


if __name__ == "__main__":
    main()
