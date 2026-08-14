"""Heavy-favourite moneylines: the one cell where the market's error pointed
toward a bet.

Calibration showed favourites at |spread| >= 14 winning 92.76% against a devigged
89.63% -- a +3.13pp gap on 442 games, in the tail region where a Gaussian
spread->probability map would be most wrong and where books hold the most.

⚠ PROVENANCE. This cell was found by inspecting a calibration table at the end of
a long search, not pre-registered. It is one bucket of one moment of one market,
and the honest prior is that it is the tail of a multiplicity distribution. It is
reported with the season-by-season split and a threshold ladder precisely so that
the reader can see whether it holds up rather than take the pooled number.

⚠ AND THE DEVIGGED GAP IS NOT THE RETURN. Profit depends on the RAW price. A
heavy favourite carries a large overround, so a +3pp edge against the devigged
probability can still be a loss at the posted number. Everything below uses the
actual moneyline.

Reported per threshold: n, favourite win rate, mean price, the implied
break-even, ROI backing the favourite, ROI backing the dog, and the hold.
"""
import warnings

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")


def prof(price):
    p = pd.to_numeric(price, errors="coerce")
    return np.where(p < 0, 100.0 / np.abs(p), p / 100.0)


def imp(price):
    p = pd.to_numeric(price, errors="coerce")
    return np.where(p < 0, -p / (-p + 100.0), 100.0 / (p + 100.0))


def load():
    from prepare_data import CSV, season_label
    raw = pd.read_csv(CSV, low_memory=False)
    raw["lbl"] = season_label(raw).astype(str)
    d = raw[raw["lbl"].str.contains("Regular Season", na=False)].copy()
    n = lambda c: pd.to_numeric(d[c], errors="coerce")
    d["spread"] = n("CLOSING SPREAD_H")
    d["mlh"], d["mla"] = n("MONEYLINE_H"), n("MONEYLINE_R")
    d["margin"] = d["PTS_H"] - d["PTS_R"]
    d["yr"] = d["lbl"].str.extract(r"(\d{4})")[0].astype(int)
    d = d.dropna(subset=["spread", "mlh", "mla", "margin"])
    d = d[d["margin"] != 0]
    home_fav = d["spread"] < 0
    d["fav_price"] = np.where(home_fav, d["mlh"], d["mla"])
    d["dog_price"] = np.where(home_fav, d["mla"], d["mlh"])
    d["fav_won"] = np.where(home_fav, d["margin"] > 0, d["margin"] < 0)
    d["abs_spread"] = d["spread"].abs()
    d["hold"] = imp(d["fav_price"]) + imp(d["dog_price"]) - 1.0
    # sanity: heavy favourites should be priced well below -100
    d = d[(d["fav_price"] < -100) & (d["dog_price"] > 100)]
    return d


def block(s, lab):
    n = len(s)
    w = s["fav_won"].mean()
    se = np.sqrt(w * (1 - w) / n)
    fp, dp = prof(s["fav_price"]), prof(s["dog_price"])
    roi_f = (w * fp.mean() - (1 - w))
    roi_d = ((1 - w) * dp.mean() - w)
    be_f = 1 / (1 + fp.mean())
    return {"cell": lab, "n": n,
            "fav win %": round(100 * w, 2),
            "95% CI": f"[{100*(w-1.96*se):.2f}, {100*(w+1.96*se):.2f}]",
            "mean fav price": round(s["fav_price"].mean(), 1),
            "break-even %": round(100 * be_f, 2),
            "edge pp": round(100 * (w - be_f), 2),
            "ROI fav %": round(100 * roi_f, 2),
            "ROI dog %": round(100 * roi_d, 2),
            "hold %": round(100 * s["hold"].mean(), 2)}


def main():
    d = load()
    print(f"{len(d):,} games with both moneylines and a decided outcome\n")

    print("=" * 122)
    print("THRESHOLD LADDER — backing the favourite at the actual price")
    print("=" * 122)
    rows = [block(d, "all games")]
    for k in (8, 10, 12, 14, 16, 18):
        s = d[d["abs_spread"] >= k]
        if len(s) >= 100:
            rows.append(block(s, f"|spread| >= {k}"))
    print(pd.DataFrame(rows).to_string(index=False))
    print("\n  'edge pp' is the win rate minus the break-even implied by the")
    print("  ACTUAL price, so it already contains the vig.")

    print("\n" + "=" * 122)
    print("SEASON BY SEASON — |spread| >= 14")
    print("=" * 122)
    big = d[d["abs_spread"] >= 14]
    rows = []
    for y, s in big.groupby("yr"):
        w = s["fav_won"].mean()
        fp = prof(s["fav_price"])
        rows.append({"season": y, "n": len(s),
                     "fav win %": round(100 * w, 2),
                     "break-even %": round(100 / (1 + fp.mean()), 2),
                     "ROI fav %": round(100 * (w * fp.mean() - (1 - w)), 2)})
    t = pd.DataFrame(rows)
    print(t.to_string(index=False))
    pos = int((t["ROI fav %"] > 0).sum())
    print(f"\n  seasons profitable: {pos}/{len(t)}")
    print(f"  pooled ROI {100*(big['fav_won'].mean()*prof(big['fav_price']).mean() - (1-big['fav_won'].mean())):+.2f}%")

    print("\n" + "=" * 122)
    print("HOW BIG IS THE HOLD OUT THERE?")
    print("=" * 122)
    d["b"] = pd.cut(d["abs_spread"], [0, 4, 8, 12, 16, 40],
                    labels=["0-4", "4-8", "8-12", "12-16", "16+"])
    for b, s in d.groupby("b", observed=True):
        print(f"  |spread| {str(b):6} n={len(s):5,}  mean fav price "
              f"{s['fav_price'].mean():8.1f}  hold {100*s['hold'].mean():5.2f}%  "
              f"fav win {100*s['fav_won'].mean():5.2f}%")

    print("\n" + "=" * 122)
    print("PERMUTATION — is the |spread|>=14 cell unusual among the ladder?")
    print("=" * 122)
    rng = np.random.default_rng(0)
    obs = big["fav_won"].mean() - (1 / (1 + prof(big["fav_price"]).mean()))
    null = []
    for _ in range(4000):
        s = d.sample(len(big), random_state=int(rng.integers(1e9)))
        null.append(s["fav_won"].mean() - (1 / (1 + prof(s["fav_price"]).mean())))
    null = np.array(null)
    print(f"  observed edge {100*obs:+.2f}pp   random same-size subsets "
          f"{100*null.mean():+.2f} ± {100*null.std():.2f}pp   "
          f"percentile {100*np.mean(null < obs):.1f}")
    print("  (this compares against random games, NOT against other thresholds --")
    print("   the ladder itself was inspected, so treat the cell as exploratory)")


if __name__ == "__main__":
    main()
