"""ROI across the full range of prediction thresholds.

Two things this is meant to show, beyond the headline ROI:

  * the SAMPLE-SIZE TRADE-OFF. ROI rises with selectivity almost mechanically --
    filter hard enough and any signal looks strong on the survivors. The honest
    view pairs each ROI with its bet count and its interval.
  * the VOLUME TRADE-OFF. A high ROI on 30 bets a season is worth less money than
    a modest ROI on 300. Expected seasonal profit at a fixed stake is the metric a
    bettor actually cares about, and it peaks in the middle, not at the extremes.

Prices at -110 and -105 are both shown, because execution has moved the numbers
more than any modelling change in this project.
"""

import warnings

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import RidgeCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from symmetric_features import build, walk
from walkforward_pace import ALLV, EXT

warnings.filterwarnings("ignore")
RNG = np.random.default_rng(0)
STAKE = 1000.0          # risked per bet, for the profit column


def sweep(G, feats, label, thresholds):
    d = G.dropna(subset=feats + ["move_total", "actual_total", "open_total"])
    d = d.reset_index(drop=True)
    p = walk(d[feats].values, d["move_total"].values.astype(float), d["date"].values)
    d = d.assign(pm=p).dropna(subset=["pm"])
    seasons = d["date"].dt.year.nunique()
    span_seasons = (d["date"].max() - d["date"].min()).days / 365.25

    rows = []
    for thr in thresholds:
        s = d[d["pm"].abs() > thr]
        s = s[s["actual_total"] != s["open_total"]]
        if len(s) < 40:
            continue
        over = (s["actual_total"] > s["open_total"]).values
        win = np.where((s["pm"] > 0).values, over, ~over).astype(float)
        n, w = len(win), win.mean()
        lo, hi = stats.beta.ppf([.025, .975], win.sum() + .5, n - win.sum() + .5)
        bs = np.array([RNG.choice(win, n, replace=True).mean() for _ in range(6000)])
        roi110 = w * (100 / 110) - (1 - w)
        roi105 = w * (100 / 105) - (1 - w)
        roi_bs = bs * (100 / 110) - (1 - bs)
        clv = np.where(s["pm"] > 0, s["move_total"], -s["move_total"])
        per_season = n / span_seasons
        rows.append({
            "spec": label, "thr": thr, "n": n, "bets/season": per_season,
            "CLV": clv.mean(), "beat close %": 100 * (clv > 0).mean(),
            "win %": 100 * w, "win lo": 100 * lo, "win hi": 100 * hi,
            "ROI -110 %": 100 * roi110,
            "ROI lo": 100 * np.percentile(roi_bs, 2.5),
            "ROI hi": 100 * np.percentile(roi_bs, 97.5),
            "P(ROI>0) %": 100 * (roi_bs > 0).mean(),
            "ROI -105 %": 100 * roi105,
            "$/season @-110": per_season * STAKE * roi110,
            "$/season @-105": per_season * STAKE * roi105,
        })
    return pd.DataFrame(rows)


def main():
    G = build()
    MKT = ["open_total", "dis_open"]
    paceX = ["pace_sum", "pace_diff", "pace_absdiff", "pace_prod",
             "oeff_sum", "deff_sum", "implied_minus_open"]
    specD = MKT + [f"h_f_{v}" for v in EXT] + [f"a_f_{v}" for v in EXT] + paceX
    specA = MKT + [f"h_f_{v}" for v in ALLV] + [f"a_f_{v}" for v in EXT]

    thr = [0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0]
    cols_a = ["thr", "n", "bets/season", "CLV", "beat close %", "win %",
              "win lo", "win hi"]
    cols_b = ["thr", "n", "ROI -110 %", "ROI lo", "ROI hi", "P(ROI>0) %",
              "ROI -105 %", "$/season @-110", "$/season @-105"]

    for feats, label in ((specD, "D pace/eff only (15 features)"),
                         (specA, "A current (21 features)")):
        r = sweep(G, feats, label, thr)
        print(f"\n=== {label} ===")
        print(r[cols_a].round(3).to_string(index=False))
        print()
        print(r[cols_b].round(2).to_string(index=False))
        r.to_csv(f"sweep_{label.split()[0]}.csv", index=False)

    print(f"\n$/season assumes ${STAKE:,.0f} risked per bet, flat staking.")
    print("break-even win rate: 52.38% at -110, 51.22% at -105")


if __name__ == "__main__":
    main()
