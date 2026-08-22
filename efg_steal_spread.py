"""High-eFG focal team facing a high-steal opponent -> larger ABSOLUTE SPREAD
pricing error?

REGIME (either orientation, as specified):
    (HOME focal ADV_EFG in prior-only upper tail q=0.80
     AND ROAD opponent ADV_STL_PER100_OPP_POSS in prior-only upper tail q=0.80)
  OR
    (ROAD focal ADV_EFG in prior-only upper tail q=0.80
     AND HOME opponent ADV_STL_PER100_OPP_POSS in prior-only upper tail q=0.80)

TARGET: |spread pricing error|, where

    spread_resid = (PTS_H - PTS_R) + CLOSING_SPREAD_H

so a home team favoured by 5 (spread -5) winning by 7 gives +2.

Context. This is the sixth dispersion test but the FIRST on the spread market;
the five before it were all on totals and all negative. Prior spread-market
findings from CLOSING.md: margin variance scales with |spread| (t=5.59) on the
sports side, while the moneyline was calibrated within 1.2pp everywhere and the
spread slope of 0.9368 gave ~1.6pp against a 2.38pp hurdle.

Both states are ADV_ box columns with full coverage, so development is
2017-18..2023-24 and the holdout is BOTH 2024-25 and 2025-26.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import refs
from dispersion_priced import ols

ADVF = "/mnt/c/NBA2/advanced_stats/game_advanced_stats.csv"
W, MINP = 20, 10
DEV_MAX = 2023
Q = 0.80
NPERM = 2000
RNG = np.random.default_rng(1414213)


def build():
    m = refs.build()
    m["gid"] = m["GAME-ID"].astype(str).str.strip()
    n = lambda c: pd.to_numeric(m[c], errors="coerce")
    m["spread"] = n("CLOSING SPREAD_H")
    m["margin"] = n("PTS_H") - n("PTS_R")
    m["spread_resid"] = m["margin"] + m["spread"]

    adv = pd.read_csv(ADVF, low_memory=False)
    adv["gid"] = adv["GAME-ID"].astype(str).str.strip()
    cols = ["gid", "ADV_TEAM_ABBR_H", "ADV_TEAM_ABBR_R",
            "ADV_EFG_H", "ADV_EFG_R",
            "ADV_STL_PER100_OPP_POSS_H", "ADV_STL_PER100_OPP_POSS_R"]
    m = m.merge(adv[cols], on="gid", how="left")

    rows = []
    for s, o in (("H", "R"), ("R", "H")):
        rows.append(pd.DataFrame({
            "gid": m["gid"], "yr": m["yr"], "date": m["date"], "side": s,
            "team": m[f"ADV_TEAM_ABBR_{s}"], "opp": m[f"ADV_TEAM_ABBR_{o}"],
            "efg": pd.to_numeric(m[f"ADV_EFG_{s}"], errors="coerce"),
            "stl": pd.to_numeric(m[f"ADV_STL_PER100_OPP_POSS_{s}"],
                                 errors="coerce"),
            "spread": m["spread"], "spread_resid": m["spread_resid"]}))
    L = pd.concat(rows, ignore_index=True).sort_values("date")

    grp = L.groupby(["yr", "team"])
    L["prior_efg"] = grp["efg"].transform(
        lambda s: s.shift(1).rolling(W, min_periods=MINP).mean())
    L["prior_stl"] = grp["stl"].transform(
        lambda s: s.shift(1).rolling(W, min_periods=MINP).mean())
    opp = L[["gid", "team", "prior_stl"]].rename(
        columns={"team": "opp", "prior_stl": "opp_prior_stl"})
    L = L.merge(opp, on=["gid", "opp"], how="left")
    return L.dropna(subset=["prior_efg", "opp_prior_stl", "spread_resid",
                            "spread"])


def main():
    L = build()
    dev = L[L["yr"] <= DEV_MAX]
    q_efg = dev["prior_efg"].quantile(Q)
    q_stl = dev["prior_stl"].quantile(Q)
    print(f"  {len(L):,} ordered team-game rows, {L['gid'].nunique():,} games")
    print(f"  FROZEN development q{Q:.2f}: eFG >= {q_efg:.4f}   "
          f"STL/100 opp poss >= {q_stl:.4f}")
    print(f"  corr(prior eFG, opponent prior STL) = "
          f"{np.corrcoef(L['prior_efg'], L['opp_prior_stl'])[0,1]:+.4f}")

    L["pair"] = (L["prior_efg"] >= q_efg) & (L["opp_prior_stl"] >= q_stl)
    print(f"  ordered pairs satisfying BOTH: {int(L['pair'].sum()):,} "
          f"({100*L['pair'].mean():.2f}%)   independence predicts "
          f"{100*(1-Q)**2:.0f}%")

    G = L.groupby("gid", as_index=False).agg(
        yr=("yr", "first"), date=("date", "first"),
        regime=("pair", "max"), n_pair=("pair", "sum"),
        spread=("spread", "first"), spread_resid=("spread_resid", "first"))
    G["abs_err"] = G["spread_resid"].abs()
    G["abs_spread"] = G["spread"].abs()
    dv = G[G["yr"] <= DEV_MAX]
    hd = G[G["yr"] > DEV_MAX]
    print(f"\n  games {len(G):,}   development {len(dv):,}   "
          f"holdout {len(hd):,} (seasons {sorted(hd['yr'].unique())})")
    print(f"  regime games: development {int(dv['regime'].sum()):,} "
          f"({100*dv['regime'].mean():.1f}%)   holdout "
          f"{int(hd['regime'].sum()):,} ({100*hd['regime'].mean():.1f}%)")
    print(f"  baseline |spread error|: {G['abs_err'].mean():.3f} "
          f"(sd {G['abs_err'].std():.3f})")

    print("\n" + "=" * 92)
    print("PRIMARY — regime minus control, absolute spread pricing error")
    print("=" * 92)
    print(f"  {'window':16}{'n regime':>10}{'|err| reg':>11}{'|err| ctl':>11}"
          f"{'diff':>9}{'t':>8}{'SMD':>8}")
    for lab, x in (("development", dv), ("holdout", hd), ("pooled", G)):
        a = x[x["regime"]]["abs_err"]
        b = x[~x["regime"]]["abs_err"]
        d = a.mean() - b.mean()
        se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
        p = np.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2)
        print(f"  {lab:16}{len(a):10,}{a.mean():11.3f}{b.mean():11.3f}"
              f"{d:9.3f}{d/se:8.2f}{d/p:8.4f}")

    print("\n  controlling for |closing spread| (margin variance scales with it)")
    for lab, x in (("development", dv), ("holdout", hd), ("pooled", G)):
        X = np.column_stack([x["regime"].astype(float), x["abs_spread"]])
        b_, se_, t_ = ols(x["abs_err"].values, X)
        print(f"  {lab:16} coef on regime {b_[1]:+.4f}  t={t_[1]:+.2f}")

    print("\n" + "=" * 92)
    print("EACH CONDITION ALONE — is the conjunction doing the work?")
    print("=" * 92)
    for col, q, nm in (("prior_efg", q_efg, "focal eFG"),
                       ("opp_prior_stl", q_stl, "opponent STL")):
        L["_f"] = L[col] >= q
        g2 = L.groupby("gid", as_index=False).agg(yr=("yr", "first"),
                                                  f=("_f", "max"))
        g2 = g2.merge(G[["gid", "abs_err"]], on="gid")
        for lab, x in (("development", g2[g2["yr"] <= DEV_MAX]),
                       ("holdout", g2[g2["yr"] > DEV_MAX])):
            a, b = x[x["f"]]["abs_err"], x[~x["f"]]["abs_err"]
            d = a.mean() - b.mean()
            se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
            print(f"  top-20% {nm:14} {lab:12} |err| {a.mean():7.3f} vs "
                  f"{b.mean():7.3f}   diff {d:+7.3f} (t={d/se:+5.2f})")

    print("\n" + "=" * 92)
    print("DOSE RESPONSE — 0, 1 or 2 qualifying orientations")
    print("=" * 92)
    print(f"  {'orient':>7}{'n dev':>8}{'|err| dev':>12}{'n hold':>9}"
          f"{'|err| hold':>13}")
    for k in (0, 1, 2):
        a = dv[dv["n_pair"] == k]["abs_err"]
        b = hd[hd["n_pair"] == k]["abs_err"]
        print(f"  {k:>7}{len(a):8,}{a.mean() if len(a) else np.nan:12.3f}"
              f"{len(b):9,}{b.mean() if len(b) else np.nan:13.3f}")

    print("\n" + "=" * 92)
    print("FALSIFICATION — signed spread error should be unaffected")
    print("=" * 92)
    for lab, x in (("development", dv), ("holdout", hd)):
        a, b = x[x["regime"]]["spread_resid"], x[~x["regime"]]["spread_resid"]
        d = a.mean() - b.mean()
        se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
        print(f"  {lab:16} signed {a.mean():+7.3f} vs {b.mean():+7.3f}   "
              f"diff {d:+7.3f} (t={d/se:+5.2f})   "
              f"home cover% {100*(a>0).mean():.2f}")

    print("\n" + "=" * 92)
    print(f"PERMUTATION — reshuffle the regime flag within season, {NPERM} reps")
    print("=" * 92)
    for lab, x in (("development", dv), ("pooled", G)):
        obs = x[x["regime"]]["abs_err"].mean() - x[~x["regime"]]["abs_err"].mean()
        v = x["abs_err"].values
        yrs = x["yr"].values
        flag = x["regime"].values
        blocks = [np.where(yrs == u)[0] for u in np.unique(yrs)]
        null = np.empty(NPERM)
        for j in range(NPERM):
            f2 = flag.copy()
            for b_ in blocks:
                f2[b_] = flag[b_][RNG.permutation(len(b_))]
            null[j] = v[f2].mean() - v[~f2].mean()
        p2 = (1 + np.sum(np.abs(null) >= abs(obs))) / (NPERM + 1)
        print(f"  {lab:14} observed {obs:+.4f}   null {null.mean():+.4f} "
              f"sd {null.std():.4f}   two-sided p={p2:.4f}")


if __name__ == "__main__":
    main()
