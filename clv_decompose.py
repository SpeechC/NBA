"""Is our CLV concentrated in games where a point cannot pay?

CLV is reported in POINTS -- how far the close moved our way. But a bet pays on
which side of the number the game lands, not by how much. A point of line value
is only worth anything when the actual total falls BETWEEN our entry and the
close. Everywhere else the bet won, or lost, at both numbers, and the CLV was
real but economically inert.

If our CLV sits mostly in games that blew past both numbers, we would see
exactly what this project sees: healthy CLV (+1.877) alongside a win rate at
break-even (50.14%). That is the standing unexplained discrepancy -- the measured
conversion of +3.83pp per point predicts ~57%.

Definitions, for bets struck at the OPENING total:

  win_open    did our side win against the number we actually bet
  win_close   would it have won against the closing number
  DECISIVE    win_open != win_close -- the move changed the outcome. This is the
              only situation in which CLV converts into money.

  effective CLV  +1 if the move flipped a loss into a win
                 -1 if it flipped a win into a loss
                  0 otherwise
  mean(effective) x 100 = percentage points of win rate the CLV actually bought.

That number, not the points figure, is what CLV is worth.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import data_split as ds

PP_PER_POINT = 3.83     # measured conversion assumed in earlier work


def load(spec="A"):
    d = pd.read_csv(f"staking_bets_{spec}.csv", parse_dates=["date"])
    # Drop pushes at BOTH numbers. An earlier version dropped only pushes at the
    # open, which silently scored a push at the CLOSE as a loss for over-bets and
    # a win for under-bets -- biasing win@close by however imbalanced our sides
    # are. Both legs of the comparison must be well defined on the same games.
    d = d[(d["actual_total"] != d["open_total"])
          & (d["actual_total"] != d["close_total"])].copy()
    side = np.sign(d["pm"])
    over_o = d["actual_total"] > d["open_total"]
    over_c = d["actual_total"] > d["close_total"]
    d["win_open"] = np.where(side > 0, over_o, ~over_o)
    d["win_close"] = np.where(side > 0, over_c, ~over_c)
    d["side_over"] = side > 0
    d["clv"] = np.where(side > 0, d["move_total"], -d["move_total"])
    d["decisive"] = d["win_open"] != d["win_close"]
    d["effective"] = np.where(d["decisive"],
                              np.where(d["win_open"], 1.0, -1.0), 0.0)
    # how far the result finished from the entry number
    d["dist"] = (d["actual_total"] - d["open_total"]).abs()
    return d


def block(d, label):
    n = len(d)
    return {
        "set": label, "bets": n,
        "CLV pts": round(d["clv"].mean(), 3),
        "win @open %": round(100 * d["win_open"].mean(), 2),
        "win @close %": round(100 * d["win_close"].mean(), 2),
        "REALISED pp": round(100 * (d["win_open"].mean()
                                    - d["win_close"].mean()), 2),
        "predicted pp": round(d["clv"].mean() * PP_PER_POINT, 2),
        "decisive %": round(100 * d["decisive"].mean(), 2),
        "% over bets": round(100 * d["side_over"].mean(), 1),
    }


def main():
    for spec in ("A", "D"):
        d = load(spec)
        dev, ho = ds.split(d)
        print("=" * 112)
        print(f"SPEC {spec} — what the CLV actually bought")
        print("=" * 112)
        rows = []
        for thr in (0.0, 0.75, 1.25):
            for lab, s in (("DEV", dev), ("HOLDOUT", ho)):
                sub = s[s["pm"].abs() > thr]
                if len(sub) >= 50:
                    rows.append({"thr": thr, **block(sub, lab)})
        print(pd.DataFrame(rows).to_string(index=False))

        print(f"\n--- where the CLV sits, spec {spec}, holdout, |pred|>1.25 ---")
        sub = ho[ho["pm"].abs() > 1.25]
        dec, inert = sub[sub["decisive"]], sub[~sub["decisive"]]
        tot = sub["clv"].sum()
        print(f"  decisive games : n={len(dec):4d} ({100*len(dec)/len(sub):5.1f}%)"
              f"   mean CLV {dec['clv'].mean():+.3f}"
              f"   share of total CLV {100*dec['clv'].sum()/tot:5.1f}%")
        print(f"  inert games    : n={len(inert):4d} ({100*len(inert)/len(sub):5.1f}%)"
              f"   mean CLV {inert['clv'].mean():+.3f}"
              f"   share of total CLV {100*inert['clv'].sum()/tot:5.1f}%")

        print(f"\n--- CLV by how far the game finished from our number ---")
        sub = sub.copy()
        sub["band"] = pd.cut(sub["dist"], [-.1, 2, 5, 10, 20, 999],
                             labels=["0-2", "2-5", "5-10", "10-20", "20+"])
        t = sub.groupby("band", observed=True).apply(lambda x: pd.Series({
            "n": len(x), "mean CLV": round(x["clv"].mean(), 3),
            "share of CLV %": round(100 * x["clv"].sum() / tot, 1),
            "decisive %": round(100 * x["decisive"].mean(), 1),
            "win @open %": round(100 * x["win_open"].mean(), 2),
        }), include_groups=False)
        print(t.to_string())
        print()


if __name__ == "__main__":
    main()
