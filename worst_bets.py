"""THE WORST BETS IN THE NBA — measured taker ROI, as a menu of maker seats.

Market-making logic: the taker's negative ROI is the maker's gross revenue.
A seat is good if the ROI is bad because of HOLD (spread+fee+overround) and the
flow is retail noise; a seat is a trap if the ROI is bad because the flow is
informed. This script measures the hold side of the ledger from our own data:

  A  NBA MONEYLINE by price band, 8 seasons -- bet every side at its listed
     price, realized ROI. The favourite-longshot structure concentrates hold
     on the longshot side.
  B  KALSHI LADDER RUNGS by side and moneyness -- buy Yes at the ask / No at
     (1-bid) plus the taker fee, realized ROI per rung position.
  C  KALSHI RANGE (BAND) TRADES -- Yes at the lower strike + No at the upper,
     both at the ask, both fees. The two-leg construction doubles the toll.
  D  reference rows: -110 spread/total at the measured 50%ish hit rates.

All realized, no modeling. Where n is small the SE is printed -- the point is
the ordering of holds, not precise ROIs.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import kalshi_calib as KC
import refs

FEE_K = 0.07


def fee(p):
    return FEE_K * p * (1 - p)


def roi_row(profits, costs):
    n = len(profits)
    roi = 100 * profits.sum() / costs.sum()
    se = 100 * profits.std(ddof=1) / np.sqrt(n) / costs.mean() if n > 2 else np.nan
    return n, roi, se


def main():
    print("=" * 96)
    print("A — NBA MONEYLINE, realized ROI by price band (2017-18..2025-26)")
    print("=" * 96)
    m = refs.build()
    n_ = lambda c: pd.to_numeric(m[c], errors="coerce")
    rows = []
    for s, o in (("H", "R"), ("R", "H")):
        rows.append(pd.DataFrame({
            "ml": n_(f"MONEYLINE_{s}"),
            "win": (n_(f"PTS_{s}") > n_(f"PTS_{o}")).astype(float)}))
    L = pd.concat(rows).dropna()
    L = L[L["ml"].abs() >= 100]
    L["profit"] = np.where(L["win"] == 1,
                           np.where(L["ml"] > 0, L["ml"] / 100, 100 / -L["ml"]),
                           -1.0)
    bands = [(-100000, -400, "heavy fav  <= -400"),
             (-400, -150, "favourite  -400..-150"),
             (-150, 150, "near pickem"),
             (150, 400, "underdog   +150..+400"),
             (400, 100000, "LONGSHOT   >= +400")]
    print(f"  {'band':24}{'n':>8}{'win %':>8}{'ROI %':>8}{'se':>6}")
    for lo, hi, lab in bands:
        s = L[(L["ml"] > lo) & (L["ml"] <= hi)]
        if not len(s):
            continue
        nn, roi, se = roi_row(s["profit"], pd.Series(np.ones(len(s))))
        print(f"  {lab:24}{nn:>8,}{100*s['win'].mean():>8.2f}{roi:>+8.2f}"
              f"{se:>6.2f}")

    print("\n" + "=" * 96)
    print("B — KALSHI LADDER RUNGS, realized taker ROI by moneyness "
          "(2025-26 regular season)")
    print("=" * 96)
    u = KC.load()
    u = u[~((u["bid"] <= 0) & (u["ask"] >= 1.0))]
    u = u[u["bucket"] == "regular"].copy()
    u = u[(u["mid"] > 0.03) & (u["mid"] < 0.97)]
    recs = []
    for side in ("YES", "NO"):
        c = (u["ask"] if side == "YES" else 1 - u["bid"]).values
        cost = c + fee(c)
        w = u["win"].values if side == "YES" else 1 - u["win"].values
        prof = w - cost
        recs.append(pd.DataFrame({"side": side, "mid": u["mid"].values,
                                  "cost": cost, "profit": prof}))
    R = pd.concat(recs)
    R["bucket"] = pd.cut(R["mid"], [0, .15, .3, .45, .55, .7, .85, 1.0])
    print(f"  {'mid bucket':>14}{'side':>6}{'n':>7}{'mean cost':>11}"
          f"{'ROI %':>8}{'se':>6}")
    t = R.groupby(["bucket", "side"], observed=True)
    for (b, side), g in t:
        nn, roi, se = roi_row(g["profit"], g["cost"])
        print(f"  {str(b):>14}{side:>6}{nn:>7,}{g['cost'].mean():>11.3f}"
              f"{roi:>+8.2f}{se:>6.2f}")

    print("\n" + "=" * 96)
    print("C — KALSHI RANGE (BAND) TRADES, realized ROI (both legs at the ask)")
    print("=" * 96)
    u2 = u.sort_values(["event_ticker", "floor_strike"])
    out = []
    for ev, g in u2.groupby("event_ticker"):
        g = g.reset_index(drop=True)
        act = g["actual"].iloc[0]
        mu = g["mid"].values
        for i in range(len(g) - 1):
            k1, k2 = g["floor_strike"].iloc[i], g["floor_strike"].iloc[i + 1]
            c1 = g["ask"].iloc[i]
            c2 = 1 - g["bid"].iloc[i + 1]
            cost = c1 + fee(c1) + c2 + fee(c2)
            inside = (act > k1) and (act <= k2)
            prof = (2.0 if inside else 1.0) - cost
            zc = abs(((k1 + k2) / 2 - g["mid"].mean()))  # crude centering
            out.append({"z": (mu[i] + mu[i + 1]) / 2, "cost": cost,
                        "profit": prof})
    B = pd.DataFrame(out)
    B["bucket"] = pd.cut(B["z"], [0, .3, .45, .55, .7, 1.0])
    print(f"  {'band position (mid)':>20}{'n':>8}{'cost':>8}{'ROI %':>8}"
          f"{'se':>6}")
    for b, g in B.groupby("bucket", observed=True):
        nn, roi, se = roi_row(g["profit"], g["cost"])
        print(f"  {str(b):>20}{nn:>8,}{100*g['cost'].mean():>8.1f}"
              f"{roi:>+8.2f}{se:>6.2f}")
    nn, roi, se = roi_row(B["profit"], B["cost"])
    print(f"  {'ALL BANDS':>20}{nn:>8,}{100*B['cost'].mean():>8.1f}"
          f"{roi:>+8.2f}{se:>6.2f}")

    print("\n" + "=" * 96)
    print("D — REFERENCE: the standard -110 bet")
    print("=" * 96)
    e = (m["actual"] - m["total"]).dropna()
    for lab, w in (("totals over", (e > 0).mean()),
                   ("totals under", (e < 0).mean())):
        roi = 100 * (w * 100 / 110 - (1 - w))
        print(f"  {lab:14} hit {100*w:.2f}%   ROI {roi:+.2f}%")


if __name__ == "__main__":
    main()
