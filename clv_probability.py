"""CLV in probability space, not points — the technique worth taking from Brier.

The Brier framework's real contribution is insisting that forecasts live in
PROBABILITY space, where a proper scoring rule applies. Our CLV has been measured
in points, which is why 88% of it turned out to be economically inert (§17): a
point is worth a great deal near the number and nothing at all far from it.

Convert instead. If the closing total C is the market's fair number, then the
market implies the game's total is distributed around C with sd σ (measured on
our own data, ~18.1). A bet struck at the opening total L therefore has a
market-implied win probability of

    p_market = Φ(clv / σ)          clv = signed move in our favour

This has three properties the points measure lacks:

  * bounded -- p can never exceed 1, so a 20-point move cannot claim 20x the
    value of a 1-point move
  * diminishing -- automatically discounts moves in games whose totals were
    never going to land nearby
  * comparable -- a 2-point move on a 210 total and on a 240 total convert
    differently, as they should

And it produces a falsifiable prediction: if the close is fair, our realised win
rate should equal mean(p_market). Testing that turns the standing "CLV does not
convert" complaint into a measurement of exactly where the assumption fails.
"""
import warnings

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")

import data_split as ds

BREAK_EVEN = 110 / 210          # 0.5238 at -110


def load(spec="A"):
    d = pd.read_csv(f"staking_bets_{spec}.csv", parse_dates=["date"])
    d = d[(d["actual_total"] != d["open_total"])
          & (d["actual_total"] != d["close_total"])].copy()
    side = np.sign(d["pm"])
    d["clv"] = np.where(side > 0, d["move_total"], -d["move_total"])
    over_o = d["actual_total"] > d["open_total"]
    d["won"] = np.where(side > 0, over_o, ~over_o)
    return ds.tag(d)


def main():
    for spec in ("A",):
        d = load(spec)
        # sigma of the total around the closing line, measured on our own data
        sigma = (d["actual_total"] - d["close_total"]).std()
        print(f"σ of total around the close = {sigma:.2f} points\n")

        # empirical alternative to the normal assumption
        resid = (d["actual_total"] - d["close_total"]).values
        ecdf = lambda x: np.searchsorted(np.sort(resid), x) / len(resid)

        d["p_norm"] = stats.norm.cdf(d["clv"] / sigma)
        d["p_emp"] = [0.5 + (ecdf(c) - ecdf(0)) if c >= 0
                      else 0.5 - (ecdf(0) - ecdf(c)) for c in d["clv"]]

        print("=" * 100)
        print(f"SPEC {spec} — does the probability-space CLV predict the win rate?")
        print("=" * 100)
        rows = []
        for thr in (0.0, 0.75, 1.25):
            for lab, s in (("DEV", ds.dev(d)),
                           ("HOLDOUT", d[d["is_holdout"]])):
                sub = s[s["pm"].abs() > thr]
                if len(sub) < 50:
                    continue
                act = sub["won"].mean()
                se = np.sqrt(act * (1 - act) / len(sub))
                rows.append({
                    "thr": thr, "set": lab, "n": len(sub),
                    "CLV pts": round(sub["clv"].mean(), 3),
                    "pred win% (normal)": round(100 * sub["p_norm"].mean(), 2),
                    "pred win% (empirical)": round(100 * sub["p_emp"].mean(), 2),
                    "OLD linear 3.83pp": round(50 + 3.83 * sub["clv"].mean(), 2),
                    "ACTUAL win%": round(100 * act, 2),
                    "gap vs normal pp": round(100 * (act - sub["p_norm"].mean()), 2),
                    "gap t": round((act - sub["p_norm"].mean()) / se, 2),
                })
        t = pd.DataFrame(rows)
        print(t.to_string(index=False))

        print("\n" + "=" * 100)
        print("What this says")
        print("=" * 100)
        ho = d[d["is_holdout"] & (d["pm"].abs() > 1.25)]
        pm_, act = ho["p_norm"].mean(), ho["won"].mean()
        print(f"  holdout, |pred|>1.25, n={len(ho)}")
        print(f"    if the close were FAIR, our entry is worth   {100*pm_:.2f}%")
        print(f"    break-even at -110                           {100*BREAK_EVEN:.2f}%")
        print(f"    -> implied edge from CLV alone               {100*(pm_-BREAK_EVEN):+.2f}pp")
        print(f"    ACTUAL                                       {100*act:.2f}%")
        print(f"    -> shortfall against the fair-close model    {100*(act-pm_):+.2f}pp")
        print()
        print("  The probability model says our CLV should make us profitable.")
        print("  It does not. The gap is not in the conversion -- it is the")
        print("  assumption that the closing line is fair FOR THE GAMES WE PICK.")

        print("\n" + "=" * 100)
        print("Calibration of the probability CLV (holdout, all bets)")
        print("=" * 100)
        h = d[d["is_holdout"]].copy()
        h["bin"] = pd.qcut(h["p_norm"], 6, duplicates="drop")
        c = h.groupby("bin", observed=True).apply(lambda x: pd.Series({
            "n": len(x), "mean CLV": round(x["clv"].mean(), 2),
            "predicted %": round(100 * x["p_norm"].mean(), 2),
            "actual %": round(100 * x["won"].mean(), 2),
            "diff pp": round(100 * (x["won"].mean() - x["p_norm"].mean()), 2),
        }), include_groups=False)
        print(c.to_string())


if __name__ == "__main__":
    main()
