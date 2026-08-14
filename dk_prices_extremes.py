"""Does DK price the H1-heavy and H2-heavy visitors correctly?

Groups are formed ONLY from the frozen pre-2023 signal S_j, so the grouping
cannot be contaminated by 2023-24 outcomes or prices. Then, per group:

    S_j  what 2017-2022 road history said
    M_j  what DK's H1 line implies:  FG_line - 2*H1_line
    A_j  what actually happened in 2023-24
    E_j  A_j - M_j, the pricing error

Three distinct questions, often conflated:

  1 DOES DK DISTINGUISH THEM AT ALL?   spread in M across groups
  2 DOES IT GET THE SIZE RIGHT?        regress A on M -- slope 1 means correctly
                                       scaled, <1 means DK over-differentiates,
                                       >1 means it under-differentiates
  3 IS ANY GROUP MISPRICED?            E by group, against its own noise

⚠ Roughly 28 games per visitor, and the game-level allocation has a standard
deviation near 24 points, so a team's A_j carries a standard error around 4.5.
Team-level errors are mostly sampling noise (lambda = 0.244); the GROUP means
are the reliable quantity.
"""
import warnings

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")


def main():
    from team_market_error import build
    j, sig = build()

    agg = j.groupby("visitor").agg(n=("E", "size"), A=("A", "mean"),
                                   M=("M", "mean"), E=("E", "mean"),
                                   A_sd=("A", "std")).reset_index()
    agg = agg.merge(sig[["team", "S"]].rename(columns={"team": "visitor"}),
                    on="visitor")
    agg["se_A"] = agg["A_sd"] / np.sqrt(agg["n"])
    agg["grp"] = pd.qcut(agg["S"], 3,
                         labels=["H1-heavy (S<0)", "neutral", "H2-heavy (S>0)"])

    print("\n" + "=" * 104)
    print("1 — DOES DK DISTINGUISH THE GROUPS? (groups frozen from pre-2023)")
    print("=" * 104)
    rows = []
    for g, s in agg.groupby("grp", observed=True):
        gj = j[j["visitor"].isin(s["visitor"])]
        rows.append({"group": g, "teams": len(s), "games": len(gj),
                     "frozen S": round(s["S"].mean(), 2),
                     "DK implied M": round(gj["M"].mean(), 2),
                     "actual A": round(gj["A"].mean(), 2),
                     "error E": round(gj["E"].mean(), 2),
                     "se(E)": round(gj["E"].std() / np.sqrt(len(gj)), 2)})
    t = pd.DataFrame(rows)
    print(t.to_string(index=False))
    print(f"\n  DK spread across groups: "
          f"{t['DK implied M'].max() - t['DK implied M'].min():+.2f} points")
    print(f"  actual spread:           "
          f"{t['actual A'].max() - t['actual A'].min():+.2f} points")
    print(f"  frozen-signal spread:    "
          f"{t['frozen S'].max() - t['frozen S'].min():+.2f} points")

    print("\n" + "=" * 104)
    print("2 — DOES DK GET THE SIZE RIGHT? (team level, A on M)")
    print("=" * 104)
    b, a = np.polyfit(agg["M"], agg["A"], 1)
    r = np.corrcoef(agg["M"], agg["A"])[0, 1]
    tt = r * np.sqrt(len(agg) - 2) / np.sqrt(1 - r * r)
    print(f"  A_j = {a:+.3f} + {b:+.3f} * M_j     corr {r:+.3f}  t={tt:+.2f}  "
          f"n={len(agg)} teams")
    print(f"  slope {b:.3f}: "
          + ("DK UNDER-differentiates (actual moves more than priced)"
             if b > 1.15 else
             "DK OVER-differentiates (actual moves less than priced)"
             if b < 0.85 else "correctly scaled, within noise"))

    print("\n" + "=" * 104)
    print("3 — THE EXTREMES, team by team")
    print("=" * 104)
    ex = pd.concat([agg.nsmallest(5, "S"), agg.nlargest(5, "S")])
    ex = ex.sort_values("S")
    print(ex[["visitor", "n", "S", "M", "A", "E", "se_A"]].round(2)
          .to_string(index=False))
    print("\n  read: S = history, M = DK's price, A = what happened,")
    print("        E = A - M.  se_A is the noise on a single team's A.")

    print("\n" + "=" * 104)
    print("IS ANY GROUP SIGNIFICANTLY MISPRICED?")
    print("=" * 104)
    for g, s in agg.groupby("grp", observed=True):
        gj = j[j["visitor"].isin(s["visitor"])]
        m, se = gj["E"].mean(), gj["E"].std() / np.sqrt(len(gj))
        print(f"  {str(g):18} n={len(gj):3d}  E={m:+6.2f}  se={se:.2f}  "
              f"t={m/se:+.2f}  95% CI [{m-1.96*se:+.2f}, {m+1.96*se:+.2f}]")
    a1 = j[j["visitor"].isin(agg[agg["grp"] == "H1-heavy (S<0)"]["visitor"])]["E"]
    a2 = j[j["visitor"].isin(agg[agg["grp"] == "H2-heavy (S>0)"]["visitor"])]["E"]
    tt, pp = stats.ttest_ind(a1, a2, equal_var=False)
    print(f"\n  H1-heavy vs H2-heavy group error: {a1.mean():+.2f} vs "
          f"{a2.mean():+.2f}   diff {a1.mean()-a2.mean():+.2f}  "
          f"t={tt:+.2f}  p={pp:.3f}")


if __name__ == "__main__":
    main()
