"""Which teams score more in H1 vs H2, by season.

Values are a team's OWN scoring: H2 minus H1, in points per game.
    negative -> scores more in the FIRST half
    positive -> scores more in the SECOND half

Three views: all games, road only, home only. Road is the one carrying the
persistent signal (Var_true 3.17, lambda 0.858, year-over-year +0.44); home
heterogeneity is about six times smaller.

Regulation only (periods 1-4), so overtime does not distort the split.
2019-20 is absent -- the odds file that anchors the join does not carry it.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

pd.set_option("display.width", 220)


def table(L, mask, label):
    s = L[mask]
    piv = s.pivot_table(index="team", columns="yr", values="h21", aggfunc="mean")
    piv.columns = [f"{c}-{str(c+1)[2:]}" for c in piv.columns]
    piv["MEAN"] = piv.mean(axis=1)
    piv = piv.sort_values("MEAN")
    print("\n" + "=" * 110)
    print(f"{label}   (negative = more scoring in H1, positive = more in H2)")
    print("=" * 110)
    print(piv.round(1).to_string())
    return piv


def main():
    from bench_oos import build as bench_build
    _, L = bench_build()
    print(f"{len(L):,} team-games, {L['team'].nunique()} teams, "
          f"seasons {sorted(L['yr'].unique())}")
    print(f"league mean H2-H1: all {L['h21'].mean():+.2f}   "
          f"road {L[L['road']]['h21'].mean():+.2f}   "
          f"home {L[~L['road']]['h21'].mean():+.2f}")

    allg = table(L, L["team"].notna(), "ALL GAMES")
    road = table(L, L["road"], "ROAD GAMES ONLY  <- the persistent signal")
    table(L, ~L["road"], "HOME GAMES ONLY")

    print("\n" + "=" * 110)
    print("EXTREMES on the road, by career mean")
    print("=" * 110)
    r = road["MEAN"].sort_values()
    print("\n  most H1-heavy on the road (score early, fade after halftime):")
    for t, v in r.head(6).items():
        yrs = road.loc[t].drop("MEAN")
        print(f"    {t:14} {v:+.2f}   seasons: "
              + " ".join(f"{x:+.1f}" for x in yrs.values))
    print("\n  most H2-heavy on the road (start slow, score after halftime):")
    for t, v in r.tail(6).items():
        yrs = road.loc[t].drop("MEAN")
        print(f"    {t:14} {v:+.2f}   seasons: "
              + " ".join(f"{x:+.1f}" for x in yrs.values))

    print("\n" + "=" * 110)
    print("CONSISTENCY — how often does a team keep its sign on the road?")
    print("=" * 110)
    yrs = [c for c in road.columns if c != "MEAN"]
    sgn = np.sign(road[yrs])
    road2 = road.copy()
    road2["same_sign"] = (sgn.eq(np.sign(road["MEAN"]), axis=0)).sum(axis=1)
    road2["n_seasons"] = sgn.notna().sum(axis=1)
    out = road2[["MEAN", "same_sign", "n_seasons"]].sort_values("MEAN")
    print(out.round(2).to_string())
    print(f"\n  mean seasons agreeing with the career sign: "
          f"{out['same_sign'].mean():.2f} of {out['n_seasons'].mean():.1f}")


if __name__ == "__main__":
    main()
