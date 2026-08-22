"""High 3PA rate + high rotation concentration ON THE SAME SIDE ->
greater absolute closing-total pricing error?

Mechanism under test: three-point scoring is high variance, and a concentrated
rotation means the same few shooters take those attempts, so their hot/cold
nights are less diluted by teammates. The two conditions must hold for the
SAME team, not merely somewhere in the game.

Prior context: this is the FIFTH dispersion test. The four before it were
  - eff_level_20 -> conditional variance: failed its pre-registration twice
  - residual_screen2 magnitude target: corr -0.0114
  - dispersion itself: correctly priced, gap t=+0.16
  - OREB x late-possession: SMD -0.002, permutation p=0.97

States, strictly prior-only (shift(1), rolling 20, min 10, within season):
  3PA rate       = 3PA / FGA
  rotation HHI   = Herfindahl of within-game minutes share

Thresholds frozen on DEVELOPMENT at the top 20% of each. Development
2017-18..2023-24; SEALED 2024-25.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import refs
import rotation_extract
from dispersion_priced import ols

ADVF = "/mnt/c/NBA2/advanced_stats/game_advanced_stats.csv"
W, MINP = 20, 10
DEV_MAX, SEALED = 2023, 2024
NPERM = 2000
RNG = np.random.default_rng(112358)


def build():
    R = rotation_extract.build()
    R["gid"] = R["gid"].astype(str).str.zfill(10)

    m = refs.build()
    m["gid"] = m["GAME-ID"].astype(str).str.strip()
    m["gidz"] = m["gid"].str.zfill(10)
    n = lambda c: pd.to_numeric(m[c], errors="coerce")
    adv = pd.read_csv(ADVF, low_memory=False)
    adv["gid"] = adv["GAME-ID"].astype(str).str.strip()
    m = m.merge(adv[["gid", "ADV_TEAM_ABBR_H", "ADV_TEAM_ABBR_R"]], on="gid",
                how="left")

    rows = []
    for s in ("H", "R"):
        rows.append(pd.DataFrame({
            "gidz": m["gidz"], "yr": m["yr"], "date": m["date"],
            "team": m[f"ADV_TEAM_ABBR_{s}"],
            "tpa_rate": n(f"3PA_{s}") / n(f"FGA_{s}"),
            "total": m["total"], "actual": m["actual"], "e": m["e"]}))
    L = pd.concat(rows, ignore_index=True)
    L = L.merge(R[["gid", "team", "hhi", "n_players"]].rename(
        columns={"gid": "gidz"}), on=["gidz", "team"], how="inner")
    L = L.sort_values("date").reset_index(drop=True)

    grp = L.groupby(["yr", "team"])
    L["prior_tpa"] = grp["tpa_rate"].transform(
        lambda s: s.shift(1).rolling(W, min_periods=MINP).mean())
    L["prior_hhi"] = grp["hhi"].transform(
        lambda s: s.shift(1).rolling(W, min_periods=MINP).mean())
    return L.dropna(subset=["prior_tpa", "prior_hhi", "e", "total"])


def main():
    L = build()
    L = L[L["yr"] <= SEALED]
    dev = L[L["yr"] <= DEV_MAX]
    q_tpa = dev["prior_tpa"].quantile(0.80)
    q_hhi = dev["prior_hhi"].quantile(0.80)
    print(f"  {len(L):,} team-game rows, {L['gidz'].nunique():,} games")
    print(f"  FROZEN development top-20%: 3PA rate >= {q_tpa:.4f}   "
          f"rotation HHI >= {q_hhi:.4f}")
    print(f"  corr(prior 3PA rate, prior HHI) = "
          f"{np.corrcoef(L['prior_tpa'], L['prior_hhi'])[0,1]:+.4f}"
          f"   [near zero keeps the conjunction meaningful]")

    L["both"] = (L["prior_tpa"] >= q_tpa) & (L["prior_hhi"] >= q_hhi)
    print(f"  team-games satisfying BOTH: {int(L['both'].sum()):,} "
          f"({100*L['both'].mean():.1f}%)   "
          f"independence would predict {100*0.2*0.2:.0f}%")

    G = L.groupby("gidz", as_index=False).agg(
        yr=("yr", "first"), date=("date", "first"),
        cell=("both", "max"), n_side=("both", "sum"),
        total=("total", "first"), actual=("actual", "first"),
        e=("e", "first"))
    G["abs_e"] = G["e"].abs()
    dv, sl = G[G["yr"] <= DEV_MAX], G[G["yr"] == SEALED]
    print(f"\n  games {len(G):,}   development {len(dv):,}   SEALED {len(sl):,}")
    print(f"  qualifying games: development {int(dv['cell'].sum()):,} "
          f"({100*dv['cell'].mean():.1f}%)   sealed {int(sl['cell'].sum()):,} "
          f"({100*sl['cell'].mean():.1f}%)")

    print("\n" + "=" * 92)
    print("PRIMARY — absolute closing-total error, cell vs rest")
    print("=" * 92)
    print(f"  {'window':16}{'n cell':>8}{'|e| cell':>10}{'|e| rest':>10}"
          f"{'diff':>9}{'t':>8}{'SMD':>8}")
    for lab, x in (("development", dv), ("SEALED 2024-25", sl),
                   ("pooled", G)):
        a = x[x["cell"]]["abs_e"]
        b = x[~x["cell"]]["abs_e"]
        d = a.mean() - b.mean()
        se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
        p = np.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2)
        print(f"  {lab:16}{len(a):8,}{a.mean():10.3f}{b.mean():10.3f}"
              f"{d:9.3f}{d/se:8.2f}{d/p:8.4f}")

    print("\n  controlling for the closing total")
    for lab, x in (("development", dv), ("SEALED 2024-25", sl),
                   ("pooled", G)):
        X = np.column_stack([x["cell"].astype(float), x["total"]])
        b_, se_, t_ = ols(x["abs_e"].values, X)
        print(f"  {lab:16} coef on cell {b_[1]:+.4f}  t={t_[1]:+.2f}")

    print("\n" + "=" * 92)
    print("EACH CONDITION ALONE — is the conjunction doing any work?")
    print("=" * 92)
    for col, nm in (("prior_tpa", "3PA rate"), ("prior_hhi", "rotation HHI")):
        q = dev[col].quantile(0.80) if False else (
            q_tpa if col == "prior_tpa" else q_hhi)
        L["_f"] = L[col] >= q
        g2 = L.groupby("gidz", as_index=False).agg(
            yr=("yr", "first"), f=("_f", "max"))
        g2 = g2.merge(G[["gidz", "abs_e"]], on="gidz")
        for lab, x in (("development", g2[g2["yr"] <= DEV_MAX]),
                       ("SEALED", g2[g2["yr"] == SEALED])):
            a = x[x["f"]]["abs_e"]
            b = x[~x["f"]]["abs_e"]
            d = a.mean() - b.mean()
            se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
            print(f"  top-20% {nm:14} {lab:12} |e| {a.mean():7.3f} vs "
                  f"{b.mean():7.3f}   diff {d:+7.3f} (t={d/se:+5.2f})")

    print("\n" + "=" * 92)
    print("DOSE RESPONSE — 0, 1 or 2 qualifying sides in the game")
    print("=" * 92)
    print(f"  {'sides':>7}{'n dev':>8}{'|e| dev':>10}{'n seal':>9}"
          f"{'|e| seal':>11}")
    for k in (0, 1, 2):
        a = dv[dv["n_side"] == k]["abs_e"]
        b = sl[sl["n_side"] == k]["abs_e"]
        print(f"  {k:>7}{len(a):8,}{a.mean() if len(a) else np.nan:10.3f}"
              f"{len(b):9,}{b.mean() if len(b) else np.nan:11.3f}")

    print("\n" + "=" * 92)
    print("FALSIFICATION — signed error should be unaffected")
    print("=" * 92)
    for lab, x in (("development", dv), ("SEALED 2024-25", sl)):
        a = x[x["cell"]]["e"]
        b = x[~x["cell"]]["e"]
        d = a.mean() - b.mean()
        se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
        print(f"  {lab:16} e {a.mean():+7.3f} vs {b.mean():+7.3f}   "
              f"diff {d:+7.3f} (t={d/se:+5.2f})   over% {100*(a>0).mean():.2f}")

    print("\n" + "=" * 92)
    print(f"PERMUTATION — reshuffle the cell flag within season, {NPERM} reps")
    print("=" * 92)
    for lab, x in (("development", dv), ("pooled", G)):
        obs = x[x["cell"]]["abs_e"].mean() - x[~x["cell"]]["abs_e"].mean()
        v = x["abs_e"].values
        yrs = x["yr"].values
        flag = x["cell"].values
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
