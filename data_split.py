"""The train/holdout contract. Import this rather than filtering by hand.

    DEVELOPMENT   2017-18 .. 2023-24   (everything on or before 2024-06-17)
    HOLDOUT       2024-25, 2025-26     (everything after)

The panel begins 2017-12-06 and the first graded prediction is 2018-02-22 --
the intervening ~500 games are the walk-forward's initial training window
(`walk_forward(min_train=500)`), so they are used, just not scored. Nothing
before 2017-10-25 can ever appear: the lagged box-score features need six games
per team first. See SPLIT.md for why the panel cannot start at the season opener.

Fixed 2026-08-11. The boundary is a DATE, not a season label, because the
In-Season Tournament games carry their own labels ("NBA 2024 In-Season
Tournament") and a label filter silently leaks them into the wrong side. That
already happened once in a dev-only screen.

Rules this encodes:

  * model selection, feature choice, hyperparameters and thresholds are decided
    on DEVELOPMENT only;
  * the holdout is READ, never fitted on -- walk-forward training may include
    holdout games only when predicting later holdout games, which is the normal
    expanding window and is not selection;
  * every reported holdout result names which seasons it covers.

`assert_no_holdout()` is a guard: call it on any frame used to CHOOSE something.
It raises if holdout rows are present.
"""

import numpy as np
import pandas as pd

SPLIT_DATE = pd.Timestamp("2024-07-01")      # after the 2024 playoffs, before 2024-25
HOLDOUT_SEASONS = ("2024-2025", "2025-2026")
DEV_LAST_GAME = pd.Timestamp("2024-06-17")   # last game in the development era


def tag(df, date_col="date"):
    """Add an `is_holdout` boolean column, by DATE."""
    d = df.copy()
    d["is_holdout"] = pd.to_datetime(d[date_col]) >= SPLIT_DATE
    return d


def split(df, date_col="date"):
    """Return (development, holdout) frames."""
    d = tag(df, date_col)
    return d[~d["is_holdout"]].copy(), d[d["is_holdout"]].copy()


def dev(df, date_col="date"):
    """Development rows only -- use this for anything that CHOOSES a setting."""
    return split(df, date_col)[0]


def assert_no_holdout(df, date_col="date", what="this step"):
    """Raise if holdout data is present. Call before any selection decision."""
    n = int((pd.to_datetime(df[date_col]) >= SPLIT_DATE).sum())
    if n:
        raise AssertionError(
            f"{what} received {n} holdout rows (>= {SPLIT_DATE.date()}). "
            f"Selection decisions must use development data only -- see "
            f"data_split.py. Use data_split.dev(frame) first.")
    return True


def describe(df, date_col="date"):
    d = tag(df, date_col)
    out = []
    for lab, sub in (("DEVELOPMENT", d[~d["is_holdout"]]), ("HOLDOUT", d[d["is_holdout"]])):
        if len(sub):
            out.append({"set": lab, "games": len(sub),
                        "first": pd.to_datetime(sub[date_col]).min().date(),
                        "last": pd.to_datetime(sub[date_col]).max().date()})
    return pd.DataFrame(out)
