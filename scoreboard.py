"""The variant ladder judged on decisions, not regressions.

Every metric here is something a bettor experiences. Regression coefficients are
gone: squared error on margin rewards predicting blowouts, while a bet only cares
which side of one number the game lands on.

Priority order, most to least informative per game:
  1. CLV and beat-the-close rate  -- continuous, highest power, hardest to fool
  2. log loss and Brier           -- proper scoring rules vs a coin flip
  3. win rate and ROI             -- with binomial / bootstrap intervals
  4. Kelly growth                 -- last, because sizing never creates edge

Bet selection uses the signal orthogonal to the closing line. The raw
(model - line) signal is ~-0.94 correlated with the line itself, so betting it is
mostly "back the underdog" rather than backing the model's opinion.
"""

import numpy as np
import pandas as pd
from scipy import stats

from prepare_data import VARS
from rest_travel import FEATURES as RT
from walkforward import VIG_BREAKEVEN
from walkforward_pace import ALLV, EXT, walk_forward
from walkforward_totals import build, to_games

RNG = np.random.default_rng(0)
CAL_EVERY = 25      # refit the calibration every N games
CAL_MIN = 800       # games before the first calibration


def wf_calibrate(model, actual, min_train=CAL_MIN, step=CAL_EVERY):
    """Expanding-window affine calibration, refit every `step` games."""
    out = np.full(len(model), np.nan)
    coef = None
    for i in range(min_train, len(model)):
        if coef is None or (i - min_train) % step == 0:
            A = np.column_stack([np.ones(i), model[:i]])
            coef, *_ = np.linalg.lstsq(A, actual[:i], rcond=None)
        out[i] = coef[0] + coef[1] * model[i]
    return out


def score(d, line, actual, open_line, label):
    """d must carry: cal (calibrated model), line, actual, open_line."""
    d = d.dropna(subset=["cal", line, actual]).copy()
    d = d[d[actual] != d[line]]                      # drop pushes
    n = len(d)

    # signal orthogonal to the line, walk-forward so nothing is fit in-sample
    o = np.full(n, np.nan)
    cal, ln = d["cal"].values, d[line].values
    coef = None
    for i in range(CAL_MIN, n):
        if coef is None or (i - CAL_MIN) % CAL_EVERY == 0:
            A = np.column_stack([np.ones(i), ln[:i]])
            coef, *_ = np.linalg.lstsq(A, cal[:i], rcond=None)
        o[i] = cal[i] - (coef[0] + coef[1] * ln[i])
    d["ortho"] = o
    d = d.dropna(subset=["ortho"])
    n = len(d)

    over = (d[actual] > d[line]).values
    bet_over = d["ortho"].values > 0
    win = np.where(bet_over, over, ~over).astype(float)
    wr = win.mean()

    # walk-forward probability that the bet's side lands, from the signal alone
    resid = (d[actual] - d[line]).values
    p = np.full(n, np.nan)
    coef = None
    for i in range(CAL_MIN, n):
        if coef is None or (i - CAL_MIN) % CAL_EVERY == 0:
            A = np.column_stack([np.ones(i), d["ortho"].values[:i]])
            coef, *_ = np.linalg.lstsq(A, resid[:i], rcond=None)
            sig = float(np.std(resid[:i] - A @ coef))
        p[i] = stats.norm.cdf((coef[0] + coef[1] * d["ortho"].values[i]) / sig)
    m = ~np.isnan(p)
    pp = np.clip(p[m], 1e-6, 1 - 1e-6)
    oo = over[m].astype(float)
    ll = float(-(oo * np.log(pp) + (1 - oo) * np.log(1 - pp)).mean())
    ll0 = float(np.log(2))
    brier = float(((pp - oo) ** 2).mean())

    # CLV
    mv = (d[line] - d[open_line]).values
    clv = np.where(bet_over, mv, -mv)
    clv = clv[~np.isnan(clv)]
    clv_se = clv.std() / np.sqrt(len(clv))

    # intervals
    lo, hi = stats.beta.ppf([.025, .975], win.sum() + .5, n - win.sum() + .5)
    bs = np.array([RNG.choice(win, n, replace=True).mean() for _ in range(4000)])
    roi_bs = bs * (100 / 110) - (1 - bs)
    roi = wr * (100 / 110) - (1 - wr)

    return {
        "variant": label, "n": n,
        "CLV pts": clv.mean(), "CLV lo": clv.mean() - 1.96 * clv_se,
        "CLV hi": clv.mean() + 1.96 * clv_se,
        "beat close %": 100 * (clv > 0).mean(),
        "log loss": ll, "vs coin": ll - ll0,
        "Brier": brier,
        "win %": 100 * wr, "win lo": 100 * lo, "win hi": 100 * hi,
        "ROI %": 100 * roi, "ROI lo": 100 * np.percentile(roi_bs, 2.5),
        "ROI hi": 100 * np.percentile(roi_bs, 97.5),
        "P(ROI>0) %": 100 * (roi_bs > 0).mean(),
    }


def main():
    panel, market = build()
    base = [f"f_{v}" for v in ALLV] + [f"f_{v}_opp" for v in EXT]
    variants = {
        "paper6": [f"f_{v}" for v in ["DRB", "2P%", "FT%", "ORB", "AST", "3PA"]],
        "paper13": [f"f_{v}" for v in VARS],
        "pace16": [f"f_{v}" for v in ALLV],
        "matchup": base,
        "matchup+rest+travel": base + RT + [c + "_opp" for c in RT],
    }

    spreads, totals = [], []
    for name, cols in variants.items():
        g = to_games(walk_forward(panel, cols), market).reset_index(drop=True)
        g["cal"] = wf_calibrate(g["model_margin"].values, g["actual_margin"].values)
        spreads.append(score(g, "market_margin", "actual_margin", "open_margin", name))
        g["cal"] = wf_calibrate(g["model_total"].values, g["actual_total"].values)
        totals.append(score(g, "close_total", "actual_total", "open_total", name))
        print(f"{name:22} spread ROI {spreads[-1]['ROI %']:+.2f}%  CLV {spreads[-1]['CLV pts']:+.3f}"
              f" | total ROI {totals[-1]['ROI %']:+.2f}%  CLV {totals[-1]['CLV pts']:+.3f}",
              flush=True)

    sp = pd.DataFrame(spreads).set_index("variant")
    to = pd.DataFrame(totals).set_index("variant")
    cols_a = ["n", "CLV pts", "CLV lo", "CLV hi", "beat close %"]
    cols_b = ["log loss", "vs coin", "Brier"]
    cols_c = ["win %", "win lo", "win hi", "ROI %", "ROI lo", "ROI hi", "P(ROI>0) %"]

    L = ["# Decision scoreboard\n",
         "No regression coefficients. Every number here is something a bettor "
         "experiences. Bets are selected on the signal orthogonal to the closing line.\n",
         f"Break-even at -110 is {100 * VIG_BREAKEVEN:.2f}%. Coin-flip log loss is "
         f"{np.log(2):.5f} and coin-flip Brier is 0.25000; `vs coin` below zero means the "
         "model's probabilities beat a coin flip, above zero means they are worse.\n"]
    for title, df in [("Spreads", sp), ("Totals", to)]:
        L += [f"\n## {title}\n",
              "\n**1. Closing line value** (highest power per game)\n",
              df[cols_a].round(3).to_markdown(),
              "\n\n**2. Proper scoring rules**\n", df[cols_b].round(5).to_markdown(),
              "\n\n**3. Win rate and ROI**\n", df[cols_c].round(2).to_markdown(), "\n"]
    open("SCOREBOARD.md", "w").write("\n".join(L))
    print("\nSPREADS\n", sp[cols_a + cols_b].round(4).to_string())
    print("\n", sp[cols_c].round(2).to_string())
    print("\nTOTALS\n", to[cols_a + cols_b].round(4).to_string())
    print("\n", to[cols_c].round(2).to_string())


if __name__ == "__main__":
    main()
