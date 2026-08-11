"""FROZEN production specifications: models A and D. Do not tune.

Frozen 2026-08-11 against the 2019-01-01 → 2024-04-14 sample.

The point of freezing is that the in-sample work is finished. Roughly twenty model
variants and nine estimator families have now been evaluated on these six seasons;
no further backtest on this data can distinguish +0.5% from -0.5% ROI. Anything
that changes below invalidates the forward test that these are frozen for.

If a change is genuinely needed, add a NEW spec with a new name and a new frozen
date. Do not edit A or D.

---------------------------------------------------------------------------
TARGET      move_total = closing_total - opening_total
BET         over if prediction > 0, under if < 0, struck at the OPENING total,
            graded against the OPENING total, pushes void
ESTIMATOR   StandardScaler -> RidgeCV(alphas = logspace(-2, 3, 20))
PROTOCOL    expanding window, refit every 7 days, min 500 games of history
---------------------------------------------------------------------------

Why ridge and not a tree: on this target ridge beat XGBoost, LightGBM, CatBoost,
RandomForest and ExtraTrees on correlation, CLV and beat-close simultaneously.
The clean ordering across all nine families was by regularisation strength, not
flexibility. Median selected alpha ~26, i.e. heavy shrinkage. This is a low
signal-to-noise problem and flexible learners fit the noise.

Why two specs and not one: A has the better SHAPE (ROI monotone across all nine
thresholds, which is the structural evidence the signal is real); D has the better
PEAK and uses 6 fewer features. They are within noise of each other on this
sample and the disagreement is not resolvable here -- so both are carried forward
and the forward test decides.
"""

import numpy as np
from sklearn.linear_model import RidgeCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

FROZEN_ON = "2026-08-11"
BACKTEST_SPAN = ("2019-01-01", "2024-04-14")

BOX = ["2PA", "2P%", "3PA", "3P%", "FTA", "FT%", "ORB", "DRB",
       "AST", "STL", "BLK", "TOV", "PF"]
PACE_EFF = ["PACE", "OEFF", "DEFF"]

# market state, common to both specs
MARKET = ["open_total", "dis_open"]

# pace constructions used only by D
PACE_TERMS = ["pace_sum", "pace_diff", "pace_absdiff", "pace_prod",
              "oeff_sum", "deff_sum", "implied_minus_open"]

# --- SPEC A: 21 features -----------------------------------------------------
# home team gets all 16 lagged variables, away team only pace/efficiency.
# The asymmetry is a known defect, deliberately retained: correcting it (spec B,
# 34 features) did not improve correlation (0.294 -> 0.288) and broke nothing
# either way. A is frozen AS BACKTESTED, not as it should ideally have been.
FEATURES_A = (MARKET
              + [f"h_f_{v}" for v in BOX + PACE_EFF]
              + [f"a_f_{v}" for v in PACE_EFF])

# --- SPEC D: 15 features -----------------------------------------------------
# pace and efficiency only, symmetric, plus explicit pace constructions.
# The box-score variables are dropped: they carry no incremental signal.
FEATURES_D = (MARKET
              + [f"h_f_{v}" for v in PACE_EFF]
              + [f"a_f_{v}" for v in PACE_EFF]
              + PACE_TERMS)

SPECS = {"A": FEATURES_A, "D": FEATURES_D}

# Reference backtest, so any future run can be compared against a fixed anchor.
# ROI at -110. Every interval except threshold 2.0 includes zero.
BACKTEST = {
    "A": {0.0: -3.04, 0.25: -2.99, 0.50: -1.71, 0.75: +0.08, 1.00: +0.86,
          1.25: +3.18, 1.50: +5.51, 1.75: +9.20, 2.00: +16.82},
    "D": {0.0: -3.96, 0.25: -3.26, 0.50: -2.91, 0.75: -1.68, 1.00: +2.59,
          1.25: +3.13, 1.50: +0.92, 1.75: +3.64, 2.00: +20.36},
}
OPERATING_THRESHOLD = 1.25   # peak expected profit per season, both specs


def make_estimator():
    """The frozen estimator. Alpha is chosen by internal LOO at every refit."""
    return make_pipeline(StandardScaler(),
                         RidgeCV(alphas=np.logspace(-2, 3, 20)))


def add_pace_terms(g):
    """Derived pace columns required by spec D. Expects h_f_/a_f_ columns."""
    g = g.copy()
    g["pace_sum"] = g["h_f_PACE"] + g["a_f_PACE"]
    g["pace_diff"] = g["h_f_PACE"] - g["a_f_PACE"]
    g["pace_absdiff"] = g["pace_diff"].abs()
    g["pace_prod"] = g["h_f_PACE"] * g["a_f_PACE"] / 100
    g["oeff_sum"] = g["h_f_OEFF"] + g["a_f_OEFF"]
    g["deff_sum"] = g["h_f_DEFF"] + g["a_f_DEFF"]
    g["implied_total"] = (g["pace_sum"] / 2) * g["oeff_sum"] / 100
    g["implied_minus_open"] = g["implied_total"] - g["open_total"]
    return g


def walk_forward(X, y, dates, step_days=7, min_train=500):
    """Expanding-window refit. Never sees a game that had not finished."""
    import pandas as pd
    pred = np.full(len(y), np.nan)
    uniq = np.unique(dates)
    counts = np.cumsum([np.sum(dates == u) for u in uniq])
    idx = np.searchsorted(counts, min_train)
    if idx >= len(uniq):
        return pred
    cuts = pd.date_range(pd.Timestamp(uniq[idx]),
                         pd.Timestamp(uniq.max()) + pd.Timedelta(days=1),
                         freq=f"{step_days}D")
    for i, cut in enumerate(cuts):
        nxt = (cuts[i + 1] if i + 1 < len(cuts)
               else pd.Timestamp(uniq.max()) + pd.Timedelta(days=1))
        tr = dates < np.datetime64(cut)
        te = (dates >= np.datetime64(cut)) & (dates < np.datetime64(nxt))
        if te.sum() == 0 or tr.sum() < min_train:
            continue
        m = make_estimator()
        m.fit(X[tr], y[tr])
        pred[te] = m.predict(X[te])
    return pred


def bet_side(prediction, threshold=OPERATING_THRESHOLD):
    """+1 = bet OVER at the opening total, -1 = bet UNDER, 0 = no bet."""
    p = np.asarray(prediction, dtype=float)
    return np.where(np.abs(p) <= threshold, 0, np.sign(p)).astype(int)
