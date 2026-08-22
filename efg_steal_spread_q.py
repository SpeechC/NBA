"""CORRECTED-SPECIFICATION test: high-eFG focal team facing a high-steal
opponent -> larger ABSOLUTE SPREAD pricing error.

WHY THIS RERUN EXISTS. efg_steal_spread.py implemented "prior-only upper tail
at q=0.80" as a NUMBER frozen on development (eFG >= 0.5567, STL >= 8.3982).
League steal rate then stepped up in 2024-25, so that cutoff selected 12.5% of
team-games in 2022-23 and 48.7% in 2025-26. The gate stopped denoting "an
unusually high-steal defence at that point in NBA history", which is the
economic object in the hypothesis. The correction is motivated by the PREDICTOR
distribution, not by the outcome.

SEMANTICS. There is no separate DSL in this project; the native prior-only
convention is shift(1).expanding() (dispersion_priced.py, eos_rank.py,
scoring_surprise.py, ml_audit.py) with a 500-game minimum history
(models_frozen.py PROTOCOL). So for each game date t:

    Q80_EFG(t) = 80th percentile of every prior-only EFG state observed in
                 games strictly BEFORE t, expanding over all history
    Q80_STL(t) = the same for the steal state

data_split.py sanctions this explicitly: an expanding window may include
holdout games when thresholding LATER holdout games -- "the normal expanding
window and is not selection".

The team states themselves are unchanged from the prior run: shift(1),
rolling 20, min 10, within season.

REGIME, exactly as specified, either orientation:
    I_H = 1[EFG_H >= Q80_EFG(t)  AND  STL_A >= Q80_STL(t)]
    I_A = 1[EFG_A >= Q80_EFG(t)  AND  STL_H >= Q80_STL(t)]
    Regime = 1[I_H = 1 OR I_A = 1]

q = 0.80 exactly. No other quantile, window or variable is tried.

TARGET, unchanged: |ActualMargin - ClosingImpliedMargin|
    spread_resid = (PTS_H - PTS_R) + CLOSING_SPREAD_H

Predeclared variance control: |closing spread|. Inference: the same within-
season (time-local) permutation of the regime flag.

STATUS. 2024-26 was already read under the frozen-cutoff specification, so this
is CORRECTED-SPECIFICATION HISTORICAL VALIDATION, not a sealed holdout test.
2026-27 is the first clean prospective test.
"""
import math
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
MIN_GAMES = 500          # models_frozen.py PROTOCOL burn-in
NPERM = 2000
RNG = np.random.default_rng(1414213)


def build():
    m = refs.build()
    m["gid"] = m["GAME-ID"].astype(str).str.strip()
    n = lambda c: pd.to_numeric(m[c], errors="coerce")
    m["spread"] = n("CLOSING SPREAD_H")
    m["spread_resid"] = (n("PTS_H") - n("PTS_R")) + m["spread"]

    adv = pd.read_csv(ADVF, low_memory=False)
    adv["gid"] = adv["GAME-ID"].astype(str).str.strip()
    m = m.merge(adv[["gid", "ADV_TEAM_ABBR_H", "ADV_TEAM_ABBR_R",
                     "ADV_EFG_H", "ADV_EFG_R",
                     "ADV_STL_PER100_OPP_POSS_H",
                     "ADV_STL_PER100_OPP_POSS_R"]], on="gid", how="left")

    rows = []
    for s, o in (("H", "R"), ("R", "H")):
        rows.append(pd.DataFrame({
            "gid": m["gid"], "yr": m["yr"], "date": m["date"], "side": s,
            "team": m[f"ADV_TEAM_ABBR_{s}"], "opp": m[f"ADV_TEAM_ABBR_{o}"],
            "efg": pd.to_numeric(m[f"ADV_EFG_{s}"], errors="coerce"),
            "stl": pd.to_numeric(m[f"ADV_STL_PER100_OPP_POSS_{s}"],
                                 errors="coerce"),
            "spread": m["spread"], "spread_resid": m["spread_resid"]}))
    L = pd.concat(rows, ignore_index=True).sort_values(["date", "gid"])

    grp = L.groupby(["yr", "team"])
    L["prior_efg"] = grp["efg"].transform(
        lambda s: s.shift(1).rolling(W, min_periods=MINP).mean())
    L["prior_stl"] = grp["stl"].transform(
        lambda s: s.shift(1).rolling(W, min_periods=MINP).mean())
    opp = L[["gid", "team", "prior_stl"]].rename(
        columns={"team": "opp", "prior_stl": "opp_prior_stl"})
    L = L.merge(opp, on=["gid", "opp"], how="left")
    L = L.dropna(subset=["prior_efg", "prior_stl", "opp_prior_stl",
                         "spread_resid", "spread"])
    return L.sort_values(["date", "gid"]).reset_index(drop=True)


def expanding_q(L, col, q=Q):
    """80th percentile of every value observed in games strictly BEFORE each
    game's date. Expanding over all history, per the project convention."""
    v = L[col].to_numpy(dtype=float)
    dates = L["date"].to_numpy()
    # index of the first row of each date, and how many GAMES precede it
    starts = np.flatnonzero(np.r_[True, dates[1:] != dates[:-1]])
    out = np.full(len(L), np.nan)
    gid = L["gid"].to_numpy()
    for i, s in enumerate(starts):
        if s == 0:
            continue
        if len(np.unique(gid[:s])) < MIN_GAMES:
            continue
        thr = np.quantile(v[:s], q)
        e = starts[i + 1] if i + 1 < len(starts) else len(L)
        out[s:e] = thr
    return out


def main():
    L = build()
    L["q_efg"] = expanding_q(L, "prior_efg")
    L["q_stl"] = expanding_q(L, "prior_stl")
    n_pre = L["gid"].nunique()
    L = L.dropna(subset=["q_efg", "q_stl"])
    print(f"  {len(L):,} ordered team-game rows, {L['gid'].nunique():,} games "
          f"(burn-in dropped {n_pre - L['gid'].nunique():,} games to reach the "
          f"{MIN_GAMES}-game minimum history)")

    # own eFG in tail AND OPPONENT steal state in tail, per orientation
    L["pair"] = (L["prior_efg"] >= L["q_efg"]) & (L["opp_prior_stl"] >= L["q_stl"])

    print("\n" + "=" * 100)
    print("STATE-DEFINITION AUDIT — does the expanding quantile hold its tail "
          "meaning over time?")
    print("=" * 100)
    print(f"  {'season':>7}{'eFG q80':>10}{'% above':>9}{'STL q80':>10}"
          f"{'% above':>9}{'1-orient %':>12}{'regime %':>10}")
    Gp = L.groupby("gid", as_index=False).agg(yr=("yr", "first"),
                                              regime=("pair", "max"))
    for y, g in L.groupby("yr"):
        gg = Gp[Gp["yr"] == y]
        print(f"  {y:>7}{g['q_efg'].mean():10.4f}"
              f"{100*(g['prior_efg']>=g['q_efg']).mean():8.1f}%"
              f"{g['q_stl'].mean():10.4f}"
              f"{100*(g['prior_stl']>=g['q_stl']).mean():8.1f}%"
              f"{100*g['pair'].mean():11.2f}%{100*gg['regime'].mean():9.2f}%")
    print(f"\n  benchmark under independence: one orientation "
          f"{100*(1-Q)**2:.2f}%, game-level either-or "
          f"{100*(1-(1-(1-Q)**2)**2):.2f}%")
    print(f"  corr(prior eFG, opponent prior STL) = "
          f"{np.corrcoef(L['prior_efg'], L['opp_prior_stl'])[0,1]:+.4f}")

    G = L.groupby("gid", as_index=False).agg(
        yr=("yr", "first"), date=("date", "first"),
        regime=("pair", "max"), n_pair=("pair", "sum"),
        spread=("spread", "first"), spread_resid=("spread_resid", "first"))
    G["abs_err"] = G["spread_resid"].abs()
    G["abs_spread"] = G["spread"].abs()

    WIN = [("Development", G[G["yr"] <= DEV_MAX]),
           ("2024-25", G[G["yr"] == 2024]),
           ("2025-26", G[G["yr"] == 2025]),
           ("Holdout", G[G["yr"] > DEV_MAX]),
           ("Pooled", G)]

    print("\n" + "=" * 100)
    print("PRIMARY — absolute spread pricing error, regime minus control")
    print("=" * 100)
    print(f"  {'window':14}{'N regime':>10}{'N control':>11}{'regime |err|':>14}"
          f"{'control |err|':>15}{'diff':>8}{'SMD':>8}{'regime %':>10}")
    for lab, x in WIN:
        a, b = x[x["regime"]]["abs_err"], x[~x["regime"]]["abs_err"]
        d = a.mean() - b.mean()
        p = np.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2)
        print(f"  {lab:14}{len(a):10,}{len(b):11,}{a.mean():14.3f}"
              f"{b.mean():15.3f}{d:8.3f}{d/p:8.4f}"
              f"{100*x['regime'].mean():9.1f}%")

    print("\n  with the predeclared |closing spread| variance control")
    print(f"  {'window':14}{'raw diff':>10}{'t':>8}{'ctrl diff':>12}{'t':>8}")
    for lab, x in WIN:
        a, b = x[x["regime"]]["abs_err"], x[~x["regime"]]["abs_err"]
        d = a.mean() - b.mean()
        se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
        X = np.column_stack([x["regime"].astype(float), x["abs_spread"]])
        b_, s_, t_ = ols(x["abs_err"].values, X)
        print(f"  {lab:14}{d:10.3f}{d/se:8.2f}{b_[1]:+12.4f}{t_[1]:8.2f}")

    print("\n" + "=" * 100)
    print("FALSIFICATION — dispersion, not a directional miss in disguise")
    print("=" * 100)
    print(f"  {'window':14}{'signed diff':>13}{'t':>8}{'|err| diff':>13}{'t':>8}"
          f"{'mechanical':>12}")
    for lab, x in WIN:
        a, b = x[x["regime"]]["spread_resid"], x[~x["regime"]]["spread_resid"]
        ds = a.mean() - b.mean()
        se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
        aa, bb = x[x["regime"]]["abs_err"], x[~x["regime"]]["abs_err"]
        da = aa.mean() - bb.mean()
        sa = np.sqrt(aa.var(ddof=1) / len(aa) + bb.var(ddof=1) / len(bb))
        # how much of the |err| gap a pure mean shift of ds would produce
        sd = x["spread_resid"].std()
        ef = lambda mu: (sd * np.sqrt(2 / np.pi) * np.exp(-mu**2 / (2*sd**2))
                         + mu * math.erf(mu / (sd * np.sqrt(2))))
        print(f"  {lab:14}{ds:+13.3f}{ds/se:8.2f}{da:+13.3f}{da/sa:8.2f}"
              f"{ef(a.mean()) - ef(b.mean()):12.3f}")
    print("  'mechanical' = the |err| gap a pure mean shift of that size would "
          "produce on its own")

    print("\n" + "=" * 100)
    print("SEASON SIGN")
    print("=" * 100)
    print(f"  {'season':>7}{'n regime':>10}{'regime':>9}{'control':>9}"
          f"{'diff':>8}{'t':>7}")
    pos = 0
    for y, x in G.groupby("yr"):
        a, b = x[x["regime"]]["abs_err"], x[~x["regime"]]["abs_err"]
        if len(a) < 8:
            print(f"  {y:>7}{len(a):>10}   (too few to report)")
            continue
        d = a.mean() - b.mean()
        se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
        pos += d > 0
        print(f"  {y:>7}{len(a):10,}{a.mean():9.3f}{b.mean():9.3f}{d:8.3f}"
              f"{d/se:7.2f}")
    print(f"  seasons positive: {pos} / {G['yr'].nunique()}")

    print("\n" + "=" * 100)
    print(f"TIME-LOCAL PERMUTATION — regime flag reshuffled within season, "
          f"{NPERM} reps")
    print("=" * 100)
    for lab, x in WIN:
        obs = x[x["regime"]]["abs_err"].mean() - x[~x["regime"]]["abs_err"].mean()
        v, yrs, flag = (x["abs_err"].values, x["yr"].values,
                        x["regime"].values)
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
