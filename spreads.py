"""Two executable leads in the spread market, from the §21 omnibus tests.

Both are properties of the LINE, knowable the moment it is posted, so neither
can suffer the look-ahead failure that killed the departed-star signal.

LEAD 1 — the spread overreacts.
  Mincer-Zarnowitz gave slope 0.9368 (se 0.0186, ~3.4 se below 1.0). A 10-point
  favourite behaves like a 9.37-point favourite, so the underdog is undervalued
  and the shortfall GROWS with the spread. Prediction: underdog ATS cover rate
  rises with |spread|.

LEAD 2 — the spread→moneyline mapping assumes constant variance.
  |spread| predicts margin variance at t = 5.59. If books convert spread to
  moneyline through a fixed variance, then at large spreads the true outcome
  distribution is WIDER than assumed, upsets are commoner than priced, and the
  favourite's implied win probability is overstated. Prediction: actual favourite
  win rate falls below the devigged implied probability, increasingly so at
  large spreads.

The two predictions are independent -- one about the spread market, one about
the moneyline -- but they come from the same underlying defect, so agreement
between them is meaningful rather than double-counting.

Reported development/holdout separately per the standing split.
"""
import warnings

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")

import data_split as ds

BE = 110 / 210


def load():
    from prepare_data import CSV, season_label
    raw = pd.read_csv(CSV, low_memory=False)
    raw["season"] = season_label(raw).astype(str)
    d = raw[raw["season"].str.contains("Regular Season", na=False)].copy()
    d["date"] = pd.to_datetime(d["DATE"], errors="coerce")
    d["spread"] = pd.to_numeric(d["CLOSING SPREAD_H"], errors="coerce")
    d["ml_h"] = pd.to_numeric(d["MONEYLINE_H"], errors="coerce")
    d["ml_r"] = pd.to_numeric(d["MONEYLINE_R"], errors="coerce")
    d["margin"] = d["PTS_H"] - d["PTS_R"]
    d = d.dropna(subset=["spread", "date", "margin"])
    d["home_cover"] = d["margin"] + d["spread"]
    d = d[d["home_cover"] != 0]
    # underdog side: positive spread means the home team is the dog
    d["dog_cover"] = np.where(d["spread"] > 0, d["home_cover"], -d["home_cover"])
    d["abs_spread"] = d["spread"].abs()
    d["fav_won"] = np.where(d["spread"] < 0, d["margin"] > 0, d["margin"] < 0)
    return ds.tag(d.sort_values("date"))


def amer_to_prob(ml):
    return np.where(ml < 0, -ml / (-ml + 100), 100 / (ml + 100))


def blk(s, lab, col="dog_cover"):
    w = (s[col] > 0).mean()
    se = np.sqrt(w * (1 - w) / len(s))
    return {"split": lab, "n": len(s), "dog cover %": round(100 * w, 2),
            "95% CI": f"[{100*(w-1.96*se):.1f}, {100*(w+1.96*se):.1f}]",
            "ROI110": round(100 * (w * (100 / 110) - (1 - w)), 2)}


def main():
    d = load()
    dev, ho = ds.split(d)
    print(f"{len(d):,} games   dev {len(dev):,}   holdout {len(ho):,}\n")

    print("=" * 100)
    print("LEAD 1 — does the underdog cover more as the spread grows?")
    print("=" * 100)
    bins = [0, 3, 6, 9, 12, 60]
    labs = ["0-3", "3-6", "6-9", "9-12", "12+"]
    for name, s in (("DEVELOPMENT", dev), ("HOLDOUT", ho)):
        s = s.copy()
        s["band"] = pd.cut(s["abs_spread"], bins, labels=labs, right=False)
        rows = [blk(g, str(b)) for b, g in s.groupby("band", observed=True)
                if len(g) >= 60]
        print(f"\n  {name}")
        print(pd.DataFrame(rows).to_string(index=False))
    print(f"\n  break-even {100*BE:.2f}%")
    print("\n  by season, |spread| >= 9:")
    big = d[d["abs_spread"] >= 9]
    print(big.groupby("season").apply(lambda x: pd.Series({
        "n": len(x), "dog cover %": round(100 * (x["dog_cover"] > 0).mean(), 2)}),
        include_groups=False).to_string())

    print("\n" + "=" * 100)
    print("LEAD 2 — is the favourite's moneyline probability overstated?")
    print("=" * 100)
    m = d.dropna(subset=["ml_h", "ml_r"]).copy()
    ph, pa = amer_to_prob(m["ml_h"]), amer_to_prob(m["ml_r"])
    tot = ph + pa
    m["p_home"] = ph / tot
    m["p_fav"] = np.where(m["spread"] < 0, m["p_home"], 1 - m["p_home"])
    m = m[(m["p_fav"] > 0.5) & (m["p_fav"] < 0.99)]
    m["band"] = pd.cut(m["abs_spread"], bins, labels=labs, right=False)
    rows = []
    for b, g in m.groupby("band", observed=True):
        if len(g) < 60:
            continue
        imp, act = g["p_fav"].mean(), g["fav_won"].mean()
        se = np.sqrt(act * (1 - act) / len(g))
        # ROI backing the underdog moneyline at the devigged fair price
        dog_p = 1 - imp
        dog_actual = 1 - act
        payout = (1 - dog_p) / dog_p
        rows.append({"|spread|": str(b), "n": len(g),
                     "implied fav win %": round(100 * imp, 2),
                     "actual fav win %": round(100 * act, 2),
                     "gap pp": round(100 * (act - imp), 2),
                     "t": round((act - imp) / se, 2),
                     "dog ML ROI %": round(100 * (dog_actual * payout
                                                  - (1 - dog_actual)), 2)})
    print(pd.DataFrame(rows).to_string(index=False))
    print("\n  gap < 0 means the favourite wins LESS than priced -> back the dog.")
    print("  ROI shown at the DEVIGGED fair price, so it is the gross edge")
    print("  before the book's actual margin -- a ceiling, not a realisable return.")

    print("\n  margin sd by |spread| band (the mechanism):")
    for b, g in d.groupby(pd.cut(d["abs_spread"], bins, labels=labs, right=False),
                          observed=True):
        print(f"    {str(b):6} n={len(g):5,}  sd(margin) {g['margin'].std():.2f}")


if __name__ == "__main__":
    main()
