"""Guard against the two sources drifting apart.

The panel is assembled from two files that must cover the same era:

  prepare_data.CSV          -> the box scores, which become the lagged form features
  movement_full_games.csv   -> the market columns (open/close totals, movement)

They are joined on game id. If one covers 2017-2026 and the other stops in June
2024, the join still SUCCEEDS -- it just fills every form feature with NaN for the
uncovered games, and the downstream `dropna` silently deletes them. The result
looks like a clean run on a smaller panel, with no error anywhere.

This has bitten the project twice. Run it before any backtest or holdout.

    python check_data_source.py        # exit 0 = sources agree
"""

import sys

import pandas as pd

import data_split as ds
from prepare_data import CSV, SEASON_COLS


def main():
    ok = True

    mv = pd.read_csv("movement_full_games.csv", parse_dates=["date"], low_memory=False)
    mv_last, mv_n = mv["date"].max(), len(mv)

    raw = pd.read_csv(CSV, low_memory=False, usecols=lambda c: c in ("DATE",) or c in SEASON_COLS)
    box_last = pd.to_datetime(raw["DATE"], errors="coerce").max()
    box_n = len(raw)

    print(f"box scores   {CSV}")
    print(f"             {box_n:,} rows, last game {box_last.date()}")
    print(f"movement     movement_full_games.csv")
    print(f"             {mv_n:,} games, last game {mv_last.date()}\n")

    gap = (mv_last - box_last).days
    if gap > 30:
        print(f"FAIL  movement file runs {gap} days past the box-score file.")
        print(f"      Every lagged form feature will be NaN for those games and the")
        print(f"      panel will truncate at {box_last.date()} without raising.")
        print(f"      Fix: point prepare_data.CSV at the newer odds export.")
        ok = False
    elif gap < -30:
        print(f"WARN  box-score file runs {-gap} days past the movement file;")
        print(f"      regenerate movement_full_games.csv to use the newer games.")
    else:
        print(f"OK    sources agree to within {abs(gap)} days.")

    # both holdout seasons must be reachable
    for lo, hi, name in ((ds.SPLIT_DATE, pd.Timestamp("2025-07-01"), "2024-25"),
                         (pd.Timestamp("2025-07-01"), pd.Timestamp("2026-09-01"), "2025-26")):
        n_mv = int(((mv["date"] >= lo) & (mv["date"] < hi)).sum())
        d = pd.to_datetime(raw["DATE"], errors="coerce")
        n_bx = int(((d >= lo) & (d < hi)).sum())
        status = "OK  " if (n_mv > 500 and n_bx > 500) else "FAIL"
        if status == "FAIL":
            ok = False
        print(f"{status}  holdout {name}: {n_mv:,} movement games, {n_bx:,} box-score rows")

    print("\n" + ("PASS - safe to run backtests." if ok else
                  "FAIL - fix the sources before running anything."))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
