"""Do top-20% offensive-rebounding teams facing top-20% late-possession
opponents produce larger ABSOLUTE closing-total pricing errors?

Dispersion hypothesis, not directional. Target |actual - closing|.

Prior context, stated up front so the result is read correctly:
  - the pre-registered eff_level_20 -> conditional variance test FAILED
  - residual_screen2's magnitude target was dead (corr -0.0114 full split)
  - dispersion itself was measured as CORRECTLY PRICED: c_market +4.24
    (t=+12.5) against c_true +4.43, gap t=+0.16

States, both strictly prior-only (shift(1), rolling 20, min 10, within season):
  own OREB rate            = OREB extensions / own possessions
  opponent LATE18 share    = PBP_LATE18_SHARE, share of possessions running
                             18+ seconds

Cell definition, thresholds frozen on DEVELOPMENT:
  a game qualifies if EITHER ordered pair has
      offense in top 20% OREB rate AND its opponent in top 20% LATE18 share

Development 2017-18..2023-24; SEALED 2024-25 (play-by-play ends there).
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import oreb_extract
import refs
from dispersion_priced import ols

ADVF = "/mnt/c/NBA2/advanced_stats/game_advanced_stats.csv"
W, MINP = 20, 10
DEV_MAX, SEALED = 2023, 2024
NPERM = 2000
RNG = np.random.default_rng(8675309)


def build():
    P = oreb_extract.build()
    g = oreb_extract.game_team(P)
    g["gid"] = g["gid"].astype(str).str.zfill(10)

    m = refs.build()
    m["gid"] = m["GAME-ID"].astype(str).str.strip()
    m["gidz"] = m["gid"].str.zfill(10)
    adv = pd.read_csv(ADVF, low_memory=False)
    adv["gid"] = adv["GAME-ID"].astype(str).str.strip()
    keep = ["gid", "ADV_TEAM_ABBR_H", "ADV_TEAM_ABBR_R",
            "PBP_LATE18_SHARE_H", "PBP_LATE18_SHARE_R"]
    m = m.merge(adv[keep], on="gid", how="left")

    rows = []
    for s, o in (("H", "R"), ("R", "H")):
        rows.append(pd.DataFrame({
            "gidz": m["gidz"], "yr": m["yr"], "date": m["date"], "side": s,
            "team": m[f"ADV_TEAM_ABBR_{s}"], "opp": m[f"ADV_TEAM_ABBR_{o}"],
            "late18": pd.to_numeric(m[f"PBP_LATE18_SHARE_{s}"],
                                    errors="coerce"),
            "total": m["total"], "actual": m["actual"], "e": m["e"]}))
    L = pd.concat(rows, ignore_index=True)
    L = L.merge(g[["gid", "team", "oreb_rate"]].rename(columns={"gid": "gidz"}),
                on=["gidz", "team"], how="inner")
    L = L.sort_values("date").reset_index(drop=True)

    grp = L.groupby(["yr", "team"])
    L["prior_oreb"] = grp["oreb_rate"].transform(
        lambda s: s.shift(1).rolling(W, min_periods=MINP).mean())
    L["prior_late18"] = grp["late18"].transform(
        lambda s: s.shift(1).rolling(W, min_periods=MINP).mean())
    # attach the OPPONENT's prior late-possession state
    opp = L[["gidz", "team", "prior_late18"]].rename(
        columns={"team": "opp", "prior_late18": "opp_prior_late18"})
    L = L.merge(opp, on=["gidz", "opp"], how="left")
    return L.dropna(subset=["prior_oreb", "opp_prior_late18", "e", "total"])


def main():
    L = build()
    L = L[L["yr"] <= SEALED]
    dev = L[L["yr"] <= DEV_MAX]
    q_oreb = dev["prior_oreb"].quantile(0.80)
    q_late = dev["prior_late18"].quantile(0.80)
    print(f"  {len(L):,} ordered team-game rows, "
          f"{L['gidz'].nunique():,} games")
    print(f"  FROZEN development thresholds: OREB rate top-20% >= "
          f"{q_oreb:.4f}   LATE18 share top-20% >= {q_late:.4f}")
    print(f"  corr(prior OREB, opponent prior LATE18) = "
          f"{np.corrcoef(L['prior_oreb'], L['opp_prior_late18'])[0,1]:+.4f}")

    L["pair"] = (L["prior_oreb"] >= q_oreb) & (L["opp_prior_late18"] >= q_late)
    G = L.groupby("gidz", as_index=False).agg(
        yr=("yr", "first"), date=("date", "first"),
        cell=("pair", "max"), n_pair=("pair", "sum"),
        total=("total", "first"), actual=("actual", "first"),
        e=("e", "first"))
    G["abs_e"] = G["e"].abs()
    dev, seal = G[G["yr"] <= DEV_MAX], G[G["yr"] == SEALED]
    print(f"\n  games {len(G):,}   development {len(dev):,}   "
          f"SEALED {len(seal):,}")
    print(f"  qualifying games: development "
          f"{int(dev['cell'].sum()):,} ({100*dev['cell'].mean():.1f}%)   "
          f"sealed {int(seal['cell'].sum()):,} "
          f"({100*seal['cell'].mean():.1f}%)")

    print("\n" + "=" * 92)
    print("PRIMARY — absolute closing-total error, cell vs rest")
    print("=" * 92)
    print(f"  {'window':16}{'n cell':>8}{'|e| cell':>10}{'|e| rest':>10}"
          f"{'diff':>9}{'t':>8}{'SMD':>8}")
    for lab, x in (("development", dev), ("SEALED 2024-25", seal),
                   ("pooled", G)):
        a = x[x["cell"]]["abs_e"]
        b = x[~x["cell"]]["abs_e"]
        d = a.mean() - b.mean()
        se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
        p = np.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2)
        print(f"  {lab:16}{len(a):8,}{a.mean():10.3f}{b.mean():10.3f}"
              f"{d:9.3f}{d/se:8.2f}{d/p:8.4f}")

    print("\n  same, controlling for the closing total (bigger totals -> "
          "bigger absolute errors)")
    print(f"  {'window':16}{'coef on cell':>14}{'t':>8}")
    for lab, x in (("development", dev), ("SEALED 2024-25", seal),
                   ("pooled", G)):
        X = np.column_stack([x["cell"].astype(float), x["total"]])
        b_, se_, t_ = ols(x["abs_e"].values, X)
        print(f"  {lab:16}{b_[1]:+14.4f}{t_[1]:8.2f}")

    print("\n" + "=" * 92)
    print("FALSIFICATION — the SIGNED error should be unaffected")
    print("=" * 92)
    print(f"  {'window':16}{'e cell':>10}{'e rest':>10}{'diff':>9}{'t':>8}"
          f"{'over% cell':>12}")
    for lab, x in (("development", dev), ("SEALED 2024-25", seal),
                   ("pooled", G)):
        a = x[x["cell"]]["e"]
        b = x[~x["cell"]]["e"]
        d = a.mean() - b.mean()
        se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
        print(f"  {lab:16}{a.mean():10.3f}{b.mean():10.3f}{d:9.3f}"
              f"{d/se:8.2f}{100*(a>0).mean():11.2f}%")

    print("\n" + "=" * 92)
    print("DOSE RESPONSE — 0, 1 or 2 qualifying ordered pairs in the game")
    print("=" * 92)
    print(f"  {'pairs':>7}{'n dev':>8}{'|e| dev':>10}{'n seal':>9}"
          f"{'|e| seal':>11}")
    for k in (0, 1, 2):
        a = dev[dev["n_pair"] == k]["abs_e"]
        b = seal[seal["n_pair"] == k]["abs_e"]
        print(f"  {k:>7}{len(a):8,}{a.mean():10.3f}{len(b):9,}"
              f"{b.mean() if len(b) else np.nan:11.3f}")

    print("\n" + "=" * 92)
    print(f"PERMUTATION — reshuffle the cell flag within season, {NPERM} reps")
    print("=" * 92)
    for lab, x in (("development", dev), ("pooled", G)):
        obs = (x[x["cell"]]["abs_e"].mean()
               - x[~x["cell"]]["abs_e"].mean())
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
        print(f"  {lab:14} observed {obs:+.4f}   null mean {null.mean():+.4f}"
              f"  sd {null.std():.4f}   two-sided p={p2:.4f}")


if __name__ == "__main__":
    main()
