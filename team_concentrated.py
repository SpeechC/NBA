"""Are team effects concentrated in a FEW teams rather than present on average?

The earlier tests (§13) measured average structure: a correlation across all 30
teams, and a permutation on the whole distribution. Both are diluted to nothing
if the effect is real for four teams and absent for twenty-six. That is a
different hypothesis and needs a different test.

Season-level drift must be removed first: league mean |move| rises from 2.04 in
2017-18 to 2.80 in 2024-25, so a raw per-team average would make every team look
like it is trending. Everything below uses each team-season's DEVIATION from
that season's league mean.

  1. per-team t-test across seasons, Benjamini-Hochberg corrected -- with 30
     teams tested, roughly 1.5 will clear p<0.05 by chance alone
  2. consistency: how many seasons a team sits above the league mean (binomial)
  3. tail persistence: do the top-5 teams in season t stay near the top in t+1?
     This is the version that matters for trading a small subset
  4. if any team survives, does betting it actually pay?
"""
import warnings

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")
RNG = np.random.default_rng(0)

from team_moves import load, long


def bh(p, q=0.10):
    """Benjamini-Hochberg. Returns boolean array of discoveries."""
    p = np.asarray(p)
    n = len(p)
    order = np.argsort(p)
    thresh = q * (np.arange(1, n + 1)) / n
    passed = p[order] <= thresh
    k = np.max(np.where(passed)[0]) + 1 if passed.any() else 0
    out = np.zeros(n, dtype=bool)
    out[order[:k]] = True
    return out


def main():
    L = long(load())

    # deviation from the league mean of the same season
    ts = L.groupby(["season_lbl", "team"])["abs_move"].agg(["mean", "size"])
    ts = ts.reset_index().rename(columns={"mean": "team_mean", "size": "n"})
    lg = L.groupby("season_lbl")["abs_move"].mean().rename("league_mean")
    ts = ts.merge(lg, on="season_lbl")
    ts["dev"] = ts["team_mean"] - ts["league_mean"]

    print(f"{ts['team'].nunique()} teams x {ts['season_lbl'].nunique()} seasons")
    print("league mean |move| by season:")
    print("  " + "  ".join(f"{s[:7]}={v:.2f}" for s, v in lg.items()))

    print("\n" + "=" * 94)
    print("1. Per-team test: is this team's deviation consistently non-zero?")
    print("=" * 94)
    rows = []
    for team, sub in ts.groupby("team"):
        d = sub["dev"].values
        t, p = stats.ttest_1samp(d, 0.0)
        rows.append({"team": team, "seasons": len(d), "mean dev": d.mean(),
                     "sd": d.std(ddof=1), "t": t, "p": p,
                     "seasons above": int((d > 0).sum())})
    r = pd.DataFrame(rows).sort_values("p")
    r["BH q<0.10"] = bh(r["p"].values, 0.10)
    r["Bonferroni p<0.05"] = r["p"] < 0.05 / len(r)
    print(r.head(10).round(4).to_string(index=False))
    print(f"\n  teams with raw p<0.05:        {int((r['p']<0.05).sum())} "
          f"(expected ~{0.05*len(r):.1f} by chance)")
    print(f"  surviving BH FDR q<0.10:      {int(r['BH q<0.10'].sum())}")
    print(f"  surviving Bonferroni p<0.05:  {int(r['Bonferroni p<0.05'].sum())}")

    print("\n" + "=" * 94)
    print("2. Consistency: seasons above league mean (8 seasons, binomial)")
    print("=" * 94)
    c = r[["team", "seasons", "seasons above", "mean dev"]].copy()
    c["p_binom"] = [stats.binomtest(int(a), int(n), 0.5).pvalue
                    for a, n in zip(c["seasons above"], c["seasons"])]
    c = c.sort_values("p_binom")
    print(c.head(8).round(4).to_string(index=False))
    print(f"\n  teams at 7+/8 or 1-/8:  "
          f"{int(((c['seasons above']>=7)|(c['seasons above']<=1)).sum())}  "
          f"(expected ~{2*len(c)*(8+1)/2**8:.1f} by chance)")

    print("\n" + "=" * 94)
    print("3. Tail persistence: do the top teams STAY at the top?")
    print("=" * 94)
    piv = ts.pivot(index="team", columns="season_lbl", values="dev")
    seasons = list(piv.columns)
    hits5, hits10, n_pairs = 0, 0, 0
    for i in range(len(seasons) - 1):
        a, b = piv[seasons[i]].dropna(), piv[seasons[i + 1]].dropna()
        common = a.index.intersection(b.index)
        a, b = a[common], b[common]
        top_a = set(a.sort_values(ascending=False).head(5).index)
        top_b5 = set(b.sort_values(ascending=False).head(5).index)
        top_b10 = set(b.sort_values(ascending=False).head(10).index)
        hits5 += len(top_a & top_b5)
        hits10 += len(top_a & top_b10)
        n_pairs += 5
    print(f"  top-5 in season t that remain top-5  in t+1: {hits5}/{n_pairs} "
          f"= {100*hits5/n_pairs:.1f}%   (chance {100*5/30:.1f}%)")
    print(f"  top-5 in season t that remain top-10 in t+1: {hits10}/{n_pairs} "
          f"= {100*hits10/n_pairs:.1f}%   (chance {100*10/30:.1f}%)")

    # permutation null for the top-5 -> top-5 count
    null = []
    for _ in range(4000):
        h = 0
        for i in range(len(seasons) - 1):
            perm_a = RNG.permutation(30)[:5]
            perm_b = RNG.permutation(30)[:5]
            h += len(set(perm_a) & set(perm_b))
        null.append(h)
    null = np.array(null)
    print(f"  permutation null: {null.mean():.1f} +/- {null.std():.1f}, "
          f"observed {hits5} at percentile {100*np.mean(null<hits5):.1f}")

    print("\n" + "=" * 94)
    print("4. Extremes over the whole sample: biggest |mean dev| teams")
    print("=" * 94)
    ex = r.reindex(r["mean dev"].abs().sort_values(ascending=False).index)
    print(ex.head(6)[["team", "mean dev", "sd", "t", "p", "seasons above"]]
          .round(4).to_string(index=False))
    print("\n  sd column is the season-to-season swing of that team's own")
    print("  deviation. Compare it to mean dev: if sd dominates, the team's")
    print("  'effect' is a different number every year.")


if __name__ == "__main__":
    main()
