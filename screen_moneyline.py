"""Stage 1 screen for MONEYLINE markets. Portable to any sport.

A moneyline is not a line-vs-outcome residual, so the totals framework does not
transfer. There is no `b`, no `sigma`, no points. The question is CALIBRATION:
does the devigged implied probability match the realised frequency?

Needs three columns:

    date | ml_a | ml_b | won_a        (both sides' American closing prices)

WHY THE DECISION STATISTIC IS ROI, NOT WIN RATE
-----------------------------------------------
On a spread or total every bet pays the same, so win rate and profit are the
same question. On a moneyline they are not: a 30% shot at +250 is profitable
and a 70% favourite at -400 is not. Rank moneyline cells on ROI per unit
staked. `edge_pp` is meaningless here.

WHY DETECTION TIME IS PRICE-DEPENDENT
-------------------------------------
A bet at decimal odds d has profit variance ~ p(1-p)*d^2, so the games needed
to confirm a given ROI scale with d^2. A 2% edge on -200 favourites confirms
several times faster than the same 2% on +400 dogs. On totals, detection time
was sport-independent; on moneylines it is PRICE-dependent, and longshot cells
are often unconfirmable in any realistic sample. `n_to_detect` reports this per
cell and it is frequently the binding constraint.

DEVIG
-----
Both sides' raw implied probabilities sum to more than 1; the excess is the
hold. Proportional devig (divide each by the sum) is the default. It slightly
under-corrects favourites relative to a power devig, which matters at extreme
prices -- filter those out rather than trusting the devig there.
"""
import numpy as np
import pandas as pd

POWER_K = 7.84


def _clean(american):
    """American prices as float, with 0 (an impossible price) mapped to NaN.

    A literal 0 in a price column is a parse artifact, not a quote, and it
    silently produces inf/divide-by-zero downstream. Fail it loudly as NaN.
    """
    a = np.asarray(american, dtype=float)
    return np.where(a == 0, np.nan, a)


def implied(american):
    """Raw implied probability from an American price."""
    a = _clean(american)
    return np.where(a < 0, -a / (-a + 100.0), 100.0 / (a + 100.0))


def decimal(american):
    """Decimal odds (profit multiple + 1)."""
    a = _clean(american)
    return np.where(a < 0, 1.0 + 100.0 / -a, 1.0 + a / 100.0)


def devig(ml_a, ml_b, method="proportional"):
    """Fair probabilities for side A and B, plus the hold."""
    ra, rb = implied(ml_a), implied(ml_b)
    s = ra + rb
    if method == "proportional":
        return ra / s, rb / s, s - 1.0
    raise ValueError(method)


def screen_ml(df, ml_a_col, ml_b_col, won_a_col, label, games_per_season,
              max_abs_price=2000, n_buckets=6, limit=None):
    """Calibration screen for one moneyline market."""
    d = df[[ml_a_col, ml_b_col, won_a_col]].dropna().copy()
    d = d[(d[ml_a_col].abs() <= max_abs_price) &
          (d[ml_b_col].abs() <= max_abs_price)]
    pa, pb, hold = devig(d[ml_a_col].values, d[ml_b_col].values)
    d["p_fair"] = pa
    d["hold"] = hold
    d["won"] = d[won_a_col].astype(float)

    # stack both sides so every bet is one row: fair prob, decimal odds, result
    rows = pd.DataFrame({
        "p_fair": np.concatenate([pa, pb]),
        "dec": np.concatenate([decimal(d[ml_a_col].values),
                               decimal(d[ml_b_col].values)]),
        "won": np.concatenate([d["won"].values, 1.0 - d["won"].values]),
    })
    rows["profit"] = np.where(rows.won > 0, rows.dec - 1.0, -1.0)
    rows["edge"] = rows.won - rows.p_fair

    n = len(rows)
    roi = rows.profit.mean()
    se_roi = rows.profit.std() / np.sqrt(n)
    # calibration: realised minus fair, pooled
    cal = rows.edge.mean()
    se_cal = rows.edge.std() / np.sqrt(n)
    # detection: games needed to confirm the observed ROI at 80% power
    n_req = POWER_K * rows.profit.var() / roi ** 2 if roi else np.inf

    return {
        "market": label, "bets": n, "games/season": games_per_season,
        "hold %": round(100 * hold.mean(), 2),
        "mean |price|": int(np.abs(np.concatenate(
            [d[ml_a_col].values, d[ml_b_col].values])).mean()),
        "calib (real-fair)": round(100 * cal, 3),
        "calib t": round(cal / se_cal, 2),
        "ROI %": round(100 * roi, 3),
        "ROI t": round(roi / se_roi, 2),
        "ROI 95% lo": round(100 * (roi - 1.96 * se_roi), 2),
        "ROI 95% hi": round(100 * (roi + 1.96 * se_roi), 2),
        "bets to detect": int(n_req) if np.isfinite(n_req) else None,
        "seasons to detect": round(n_req / (2 * games_per_season), 1)
        if np.isfinite(n_req) else None,
        "limit": limit,
    }


def calibration_table(df, ml_a_col, ml_b_col, won_a_col,
                      max_abs_price=2000, edges=(0, .1, .25, .4, .6, .75, .9, 1)):
    """Realised vs fair probability by bucket -- the favourite-longshot test."""
    d = df[[ml_a_col, ml_b_col, won_a_col]].dropna().copy()
    d = d[(d[ml_a_col].abs() <= max_abs_price) &
          (d[ml_b_col].abs() <= max_abs_price)]
    pa, pb, _ = devig(d[ml_a_col].values, d[ml_b_col].values)
    rows = pd.DataFrame({
        "p_fair": np.concatenate([pa, pb]),
        "dec": np.concatenate([decimal(d[ml_a_col].values),
                               decimal(d[ml_b_col].values)]),
        "won": np.concatenate([d[won_a_col].values.astype(float),
                               1.0 - d[won_a_col].values.astype(float)]),
    })
    rows["profit"] = np.where(rows.won > 0, rows.dec - 1.0, -1.0)
    rows["bucket"] = pd.cut(rows.p_fair, edges)
    t = rows.groupby("bucket", observed=True).agg(
        bets=("won", "size"),
        fair=("p_fair", "mean"),
        realised=("won", "mean"),
        roi=("profit", "mean"),
    )
    t["dev pp"] = 100 * (t.realised - t.fair)
    t["se pp"] = 100 * np.sqrt(t.realised * (1 - t.realised) / t.bets)
    t["ROI %"] = 100 * t.roi
    t["roi se"] = 100 * rows.groupby("bucket", observed=True).profit.std() / \
        np.sqrt(t.bets)
    return t[["bets", "fair", "realised", "dev pp", "se pp", "ROI %", "roi se"]].round(3)
