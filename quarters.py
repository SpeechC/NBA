"""Quarter-level scoring structure: where the H1/H2 collapse lives, and whether
the Q3/Q4 split is predictable from what a book knows at halftime.

⚠ LIMITATION: this dataset has no quarter lines. Only full-game markets and a
live 2H total. So the market side cannot be tested directly. What CAN be tested
is the precondition for any quarter edge: does quarter scoring contain structure
that a mechanical rule -- "the second half is half the game, split evenly" --
would miss?

Three questions:

  1 WHERE  The H1-H2 gap has collapsed from 2.73 to 0.66 points in eight
           seasons. Which quarter moved? A book calibrated on multi-year
           averages is now most wrong wherever that is.

  2 STATE  Q4 is the low-scoring quarter (54.00 vs ~56). Is that uniform, or
           conditional on the game being close? Close games end in deliberate
           half-court possessions and tight defence; blowouts end with bench
           units and no defence. Those are opposite effects and the average of
           them hides both.

  3 SPLIT  Given what is known AT HALFTIME -- score, margin, first-half pace --
           how much of the Q3 vs Q4 split is predictable? This is the ceiling on
           any quarter-market edge derived from halftime information. If it is
           near zero, no amount of market inefficiency is reachable.
"""
import warnings

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")

from halves import period_scores


def main():
    w = period_scores()
    w = w[(w["h1"] > 60) & (w["h2"] > 60) & (w["h1"] < 160) & (w["h2"] < 160)]
    w["h1_margin"] = (w["home_p1"] + w["home_p2"]) - (w["vis_p1"] + w["vis_p2"])
    w["abs_h1m"] = w["h1_margin"].abs()
    w["q3_margin"] = w["h1_margin"] + (w["home_p3"] - w["vis_p3"])
    w["abs_q3m"] = w["q3_margin"].abs()
    print(f"{len(w):,} games\n")

    print("=" * 92)
    print("1. WHERE is the H1/H2 collapse? Scoring by quarter and season")
    print("=" * 92)
    t = w.groupby("season")[["q1", "q2", "q3", "q4"]].mean().round(2)
    t["H1-H2"] = (t["q1"] + t["q2"] - t["q3"] - t["q4"]).round(2)
    t["Q4 share %"] = (100 * t["q4"] / t[["q1", "q2", "q3", "q4"]].sum(axis=1)).round(2)
    print(t.to_string())
    first, last = t.index[0], t.index[-1]
    print(f"\n  change {first} -> {last}:")
    for q in ("q1", "q2", "q3", "q4"):
        print(f"    {q.upper()}  {t.loc[first,q]:6.2f} -> {t.loc[last,q]:6.2f}   "
              f"{t.loc[last,q]-t.loc[first,q]:+.2f}")

    print("\n" + "=" * 92)
    print("2. STATE — is the Q4 decline uniform or conditional?")
    print("=" * 92)
    w["band"] = pd.cut(w["abs_q3m"], [-1, 5, 10, 15, 20, 99],
                       labels=["0-5", "6-10", "11-15", "16-20", "21+"])
    rows = []
    for b, s in w.groupby("band", observed=True):
        rows.append({"|margin| after Q3": b, "n": len(s),
                     "Q3": round(s["q3"].mean(), 2),
                     "Q4": round(s["q4"].mean(), 2),
                     "Q4-Q3": round((s["q4"] - s["q3"]).mean(), 2),
                     "Q4 sd": round(s["q4"].std(), 2)})
    print(pd.DataFrame(rows).to_string(index=False))
    print("\n  Close games and blowouts pull Q4 in opposite directions;")
    print("  the pooled -1.92 average conceals both.")

    print("\n" + "=" * 92)
    print("3. SPLIT — how predictable is Q3 vs Q4 from HALFTIME information?")
    print("=" * 92)
    X = np.c_[np.ones(len(w)), w["h1"], w["abs_h1m"], w["h1_margin"]]
    names = ["intercept", "h1_total", "|h1 margin|", "h1 margin"]
    for target in ("q3", "q4"):
        y = w[target].values
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        yhat = X @ beta
        r = np.corrcoef(yhat, y)[0, 1]
        print(f"\n  predicting {target.upper()} from halftime info: "
              f"corr {r:.4f}  (R^2 {r*r:.4f})")
        for nm, b in zip(names, beta):
            print(f"    {nm:14} {b:+.4f}")
    # the split itself
    y = (w["q4"] - w["q3"]).values
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = np.corrcoef(X @ beta, y)[0, 1]
    print(f"\n  predicting the Q4-Q3 SPLIT: corr {r:.4f}  (R^2 {r*r:.4f})")
    print(f"  sd of the split: {y.std():.2f} points")
    print(f"  sd explained:    {y.std()*r:.2f} points")

    print("\n" + "=" * 92)
    print("Ceiling check: how big is quarter-level noise?")
    print("=" * 92)
    for q in ("q1", "q2", "q3", "q4"):
        print(f"  {q.upper()}  mean {w[q].mean():6.2f}   sd {w[q].std():5.2f}")
    print(f"\n  A quarter total sits on a distribution with sd ~{w['q4'].std():.1f}")
    print(f"  points. At -110 an edge needs bias > 0.0597 x sd = "
          f"{0.0597*w['q4'].std():.2f} points of systematic error.")


if __name__ == "__main__":
    main()
