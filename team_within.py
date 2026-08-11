"""Within-season vs across-season team persistence.

If team profiles change season to season -- roster turnover, coaching, injuries --
then pooling teams across seasons is the wrong unit, and a team effect could be
real WITHIN a season while vanishing ACROSS seasons.

That is a falsifiable prediction, and it separates two very different worlds:

  within +, across 0   team effect is real but must be estimated on the fly,
                       like every other feature in the model (rolling, lagged)
  within 0, across 0   there is no team effect; roster turnover explains nothing
                       because there was never anything to decay

Split-half within season: correlate a team's mean |move| over the first half of
its games against the second half. Same team, same season, same roster.

The comparison is only fair if both halves have the same sample size, so the
across-season figure is recomputed on half-seasons too -- otherwise within-season
looks worse purely from having fewer games per estimate.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
RNG = np.random.default_rng(0)

from team_moves import load, long


def main():
    L = long(load())
    L = L.sort_values("date")

    # each team-season split into first and second half of ITS OWN schedule
    L["gno"] = L.groupby(["season_lbl", "team"]).cumcount()
    L["n_ts"] = L.groupby(["season_lbl", "team"])["gno"].transform("size")
    L["half"] = np.where(L["gno"] < L["n_ts"] / 2, 1, 2)

    hs = L.groupby(["season_lbl", "team", "half"])["abs_move"].agg(["mean", "size"])
    hs = hs.reset_index()

    print("=" * 88)
    print("1. WITHIN-season persistence: first half vs second half, same roster")
    print("=" * 88)
    rows = []
    for s, sub in hs.groupby("season_lbl"):
        p = sub.pivot(index="team", columns="half", values="mean").dropna()
        n = sub.pivot(index="team", columns="half", values="size").dropna()
        if len(p) >= 20:
            rows.append({"season": s, "teams": len(p),
                         "games/half": int(n.mean().mean()),
                         "corr": round(np.corrcoef(p[1], p[2])[0, 1], 3)})
    w = pd.DataFrame(rows)
    print(w.to_string(index=False))
    print(f"\n  mean within-season correlation: {w['corr'].mean():+.3f}")

    print("\n" + "=" * 88)
    print("2. ACROSS-season, on HALF-seasons, so sample sizes match")
    print("=" * 88)
    # first half of season t vs first half of season t+1
    f = hs[hs["half"] == 1].pivot(index="team", columns="season_lbl", values="mean")
    seasons = list(f.columns)
    rows = []
    for i in range(len(seasons) - 1):
        pair = f[[seasons[i], seasons[i + 1]]].dropna()
        if len(pair) >= 20:
            rows.append({"from": seasons[i], "to": seasons[i + 1],
                         "corr": round(np.corrcoef(pair.iloc[:, 0],
                                                   pair.iloc[:, 1])[0, 1], 3)})
    a = pd.DataFrame(rows)
    print(a.to_string(index=False))
    print(f"\n  mean across-season correlation (half-seasons): {a['corr'].mean():+.3f}")

    print("\n" + "=" * 88)
    print("3. What a null looks like at this sample size")
    print("=" * 88)
    # shuffle abs_move within season, recompute within-season split-half corr
    null = []
    for _ in range(500):
        Ls = L.copy()
        Ls["abs_move"] = Ls.groupby("season_lbl")["abs_move"].transform(
            lambda x: RNG.permutation(x.values))
        h2 = Ls.groupby(["season_lbl", "team", "half"])["abs_move"].mean().reset_index()
        cs = []
        for s, sub in h2.groupby("season_lbl"):
            p = sub.pivot(index="team", columns="half", values="abs_move").dropna()
            if len(p) >= 20:
                cs.append(np.corrcoef(p[1], p[2])[0, 1])
        null.append(np.mean(cs))
    null = np.array(null)
    obs = w["corr"].mean()
    print(f"  observed within-season corr {obs:+.3f}")
    print(f"  null                        {null.mean():+.3f} +/- {null.std():.3f}")
    print(f"  percentile of observed      {100*np.mean(null < obs):.1f}")

    print("\n" + "=" * 88)
    print("VERDICT")
    print("=" * 88)
    if obs > null.mean() + 2 * null.std():
        print("  within-season persistence is real -> a rolling team-|move| feature")
        print("  is worth testing; pooling across seasons was the wrong unit.")
    else:
        print("  within-season persistence is NOT distinguishable from noise.")
        print("  Roster turnover does not explain the absent across-season effect,")
        print("  because there is no within-season effect to decay in the first")
        print("  place. Team-level move magnitude is noise at every horizon.")


if __name__ == "__main__":
    main()
