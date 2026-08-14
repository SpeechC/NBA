"""CrewShock -> foul-type decomposition. Mechanism validation only; the
trading strategy is not altered by this test.

Predictions, fixed in advance:
    b_DefensiveFouls > 0
    b_DefensiveFouls >> b_OffensiveFouls

CrewShock, LeagueFoulState, controls and split are the definitive frozen
versions. Foul classes come from foul_types.py (EVENTMSGACTIONTYPE-based,
audited). Development 2017-18..2023-24; sealed 2024-25; no 2025-26 PBP.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import foul_types
import ref_features as rf
import ref_shock as rsk
import refs
from crew_offense import cluster_ols
from data_split import SPLIT_DATE
from dispersion_priced import ols

CTRL = rsk.CTRL
ADVF = "/mnt/c/NBA2/advanced_stats/game_advanced_stats.csv"
DEV_MAX, SEALED = 2023, 2024
W20, MINP = 20, 10
NPERM = 300
BLOCK_DAYS = 7
RNG = np.random.default_rng(60302)

TARGETS = [
    ("total_fouls", "Total fouls"),
    ("defensive_fouls", "Defensive fouls"),
    ("offensive_fouls", "Offensive fouls"),
    ("def_per100", "Defensive fouls/100"),
    ("off_per100", "Offensive fouls/100"),
    ("n_def_shooting", "Shooting defensive fouls"),
    ("n_def_nonshooting", "Nonshooting defensive fouls"),
    ("fta_def", "FTA from defensive fouls"),
    ("fta_def_shooting", "FTA from shooting fouls"),
    ("fta_def_nonshooting", "FTA from nonshooting fouls"),
]


def build():
    m = refs.build()
    m["gid"] = m["GAME-ID"].astype(str).str.strip().str.zfill(10)
    F = foul_types.build()
    F["gid"] = F["gid"].astype(str).str.zfill(10)
    n0 = len(m)
    m = m.merge(F, on="gid", how="left")
    assert len(m) == n0

    adv = pd.read_csv(ADVF, low_memory=False)
    adv["gid"] = adv["GAME-ID"].astype(str).str.strip().str.zfill(10)
    adv["poss_g"] = (pd.to_numeric(adv["PBP_POSS_H"], errors="coerce")
                     + pd.to_numeric(adv["PBP_POSS_R"], errors="coerce"))
    m = m.merge(adv[["gid", "poss_g", "PBP_POSS_H", "PBP_POSS_R"]],
                on="gid", how="left")

    f = pd.read_csv("ref_features.csv")
    f["gid"] = f["gid"].astype(str).str.strip().str.zfill(10)
    m = m.merge(f[["gid", "CrewShock", "LeagueFoulState"]], on="gid", how="left")
    ctl = rsk.build()[["gid"] + CTRL]
    ctl["gid"] = ctl["gid"].astype(str).str.strip().str.zfill(10)
    m = m.merge(ctl, on="gid", how="left")

    m["def_per100"] = 100 * m["defensive_fouls"] / m["poss_g"]
    m["off_per100"] = 100 * m["offensive_fouls"] / m["poss_g"]
    return m


def reg(x, col):
    X = np.column_stack([x["CrewShock"], x["LeagueFoulState"]]
                        + [x[c] for c in CTRL])
    b, se, t = ols(x[col].values, X)
    return b[1], se[1], t[1]


def main():
    d = build()
    need = (["CrewShock", "LeagueFoulState", "poss_g", "actual", "e",
             "defensive_fouls", "offensive_fouls", "total_fouls", "fta_def",
             "ftm_def", "def_fouls_H", "def_fouls_R"] + CTRL
            + [c for c, _ in TARGETS])
    s = d.dropna(subset=[c for c in need if c in d.columns]).copy()
    s = s[s["yr"] <= SEALED]
    dev = s[s["yr"] <= DEV_MAX]
    seal = s[s["yr"] == SEALED]
    sd_dev = dev["CrewShock"].std()
    print(f"  analysis sample {len(s):,}   development {len(dev):,}   "
          f"SEALED 2024-25 {len(seal):,}")
    print(f"  CrewShock sd (development) = {sd_dev:.4f}")

    print("\n" + "=" * 102)
    print("PRIMARY DECOMPOSITION   Y ~ CrewShock + LeagueFoulState + controls")
    print("=" * 102)
    print(f"  {'Outcome':30} {'Dev b':>16} {'2024-25 b':>16} {'All b':>16} "
          f"{'1SD effect':>11}")
    devres = {}
    for col, name in TARGETS:
        cells = []
        for x in (dev, seal, s):
            b, se, t = reg(x, col)
            cells.append((b, t))
        devres[col] = cells[0][0]
        print(f"  {name:30} "
              f"{cells[0][0]:+8.4f}({cells[0][1]:+5.2f}) "
              f"{cells[1][0]:+8.4f}({cells[1][1]:+5.2f}) "
              f"{cells[2][0]:+8.4f}({cells[2][1]:+5.2f}) "
              f"{cells[0][0]*sd_dev:+11.3f}")

    print("\n  season-by-season (defensive vs offensive fouls)")
    print(f"    {'season':8} {'n':>6} {'b_def':>16} {'b_off':>16}")
    for y, g in s.groupby("yr"):
        bd = reg(g, "defensive_fouls")
        bo = reg(g, "offensive_fouls")
        print(f"    {y:<8} {len(g):6,} {bd[0]:+8.4f}({bd[2]:+5.2f}) "
              f"{bo[0]:+8.4f}({bo[2]:+5.2f})")

    print("\n" + "=" * 102)
    print("SHARES OF THE CREWSHOCK FOUL INCREASE (development coefficients)")
    print("=" * 102)
    bt = devres["total_fouls"]
    bd = devres["defensive_fouls"]
    bo = devres["offensive_fouls"]
    bu = bt - bd - bo
    print(f"  d(total)      {bt:+.4f}")
    print(f"  d(defensive)  {bd:+.4f}   share {100*bd/bt:6.1f}%")
    print(f"  d(offensive)  {bo:+.4f}   share {100*bo/bt:6.1f}%")
    print(f"  d(unknown)    {bu:+.4f}   share {100*bu/bt:6.1f}%  "
          f"[loose-ball, technicals, ...]")

    print("\n" + "=" * 102)
    print("MECHANISM ACCOUNTING  (development, per 1 SD CrewShock)")
    print("=" * 102)
    chain = {}
    for col in ("defensive_fouls", "fta_def", "ftm_def", "actual"):
        b, se, t = reg(dev, col)
        chain[col] = b * sd_dev
    print(f"  d DefensiveFouls  {chain['defensive_fouls']:+.3f}")
    print(f"  d FTA(def)        {chain['fta_def']:+.3f}")
    print(f"  d FTM(def)        {chain['ftm_def']:+.3f}")
    print(f"  d Points          {chain['actual']:+.3f}")
    print(f"\n  FTA per incremental defensive foul    "
          f"{chain['fta_def']/chain['defensive_fouls']:.3f}")
    print(f"  FTM per incremental defensive foul    "
          f"{chain['ftm_def']/chain['defensive_fouls']:.3f}")
    print(f"  points per incremental defensive foul "
          f"{chain['actual']/chain['defensive_fouls']:.3f}")

    print("\n" + "=" * 102)
    print("TEAM-SIDE SYMMETRY (development)")
    print("=" * 102)
    co = {}
    for col, nm in (("def_fouls_H", "HOME defensive fouls"),
                    ("def_fouls_R", "AWAY defensive fouls")):
        b, se, t = reg(dev, col)
        co[col] = b
        print(f"  {nm:24} {b:+.4f} (t={t:+.2f})")
    tot = co["def_fouls_H"] + co["def_fouls_R"]
    print(f"  normalised shares: home {co['def_fouls_H']/tot:.4f}  "
          f"away {co['def_fouls_R']/tot:.4f}")

    print("\n" + "=" * 102)
    print("SECONDARY — does CrewShock amplify foul-prone defenses?")
    print("  team-game rows, W=20 prior-only DefFoulPropensity, game-clustered")
    print("=" * 102)
    adv = pd.read_csv(ADVF, low_memory=False)
    adv["gid"] = adv["GAME-ID"].astype(str).str.strip().str.zfill(10)
    rows = []
    for side, opp in (("H", "R"), ("R", "H")):
        rows.append(pd.DataFrame({
            "gid": s["gid"], "yr": s["yr"], "date": s["date"],
            "team": s[f"TEAM_{side}"], "home": 1 if side == "H" else 0,
            "def_com": s[f"def_fouls_{side}"],
            "opp_poss": s[f"PBP_POSS_{opp}"],
            "CrewShock": s["CrewShock"],
            "LeagueFoulState": s["LeagueFoulState"]}))
    P = pd.concat(rows, ignore_index=True).dropna(
        subset=["def_com", "opp_poss"])
    P = P.sort_values("date").reset_index(drop=True)
    P["rate"] = 100 * P["def_com"] / P["opp_poss"]
    g = P.groupby(["yr", "team"])
    P["prop"] = g["rate"].transform(
        lambda v: v.shift(1).rolling(W20, min_periods=MINP).mean())
    P = P.dropna(subset=["prop"])
    pdev = P[P["yr"] <= DEV_MAX]
    mu, sd_ = pdev["prop"].mean(), pdev["prop"].std()
    P["zprop"] = (P["prop"] - mu) / sd_
    for lab, x in (("development", P[P["yr"] <= DEV_MAX]),
                   ("SEALED 2024-25", P[P["yr"] == SEALED])):
        X = np.column_stack([x["CrewShock"], x["zprop"],
                             x["CrewShock"] * x["zprop"], x["home"],
                             x["LeagueFoulState"]])
        b, se, t = cluster_ols(x["def_com"].values, X, x["gid"].values)
        print(f"  {lab:16} n={len(x):6,}  bR {b[1]:+.4f}(t={t[1]:+5.2f})  "
              f"bF {b[2]:+.4f}(t={t[2]:+5.2f})  "
              f"delta {b[3]:+.4f}(t={t[3]:+5.2f})")

    print("\n" + "=" * 102)
    print(f"TIME-LOCAL PERMUTATION — contrast b_def - b_off, {NPERM} reshuffles")
    print("=" * 102)
    obs = devres["defensive_fouls"] - devres["offensive_fouls"]
    obs_all = (reg(s, "defensive_fouls")[0] - reg(s, "offensive_fouls")[0])
    uni = rf.universe()
    k = rf.estimate_k(uni)[0]
    ublk = (uni["yr"].astype(str) + "_"
            + ((uni["date"] - uni.groupby("yr")["date"].transform("min"))
               .dt.days // BLOCK_DAYS).astype(str)).values
    ucrew = uni[["ref1", "ref2", "ref3"]].values
    ublocks = [np.where(ublk == b_)[0] for b_ in pd.unique(ublk)]
    keep = pd.Series(np.arange(len(uni)),
                     index=uni["gid"].astype(str).str.zfill(10)
                     ).reindex(s["gid"]).values
    sub = uni.copy()
    ss = s.copy()
    null_d, null_a = np.empty(NPERM), np.empty(NPERM)
    for j in range(NPERM):
        perm = ucrew.copy()
        for b_ in ublocks:
            if len(b_) > 1:
                perm[b_] = ucrew[b_][RNG.permutation(len(b_))]
        sub["ref1"], sub["ref2"], sub["ref3"] = perm[:, 0], perm[:, 1], perm[:, 2]
        cs = rf.matched_ref_effect(sub, k)["CrewShock"].values
        ss["CrewShock"] = cs[keep]
        dv = ss[ss["yr"] <= DEV_MAX]
        null_d[j] = (reg(dv, "defensive_fouls")[0]
                     - reg(dv, "offensive_fouls")[0])
        null_a[j] = (reg(ss, "defensive_fouls")[0]
                     - reg(ss, "offensive_fouls")[0])
    for lab, o, n_ in (("development", obs, null_d), ("pooled", obs_all, null_a)):
        p = (1 + np.sum(n_ >= o)) / (NPERM + 1)
        print(f"  {lab:12} observed {o:+.4f}   null mean {n_.mean():+.4f} "
              f"sd {n_.std():.4f}   z={(o-n_.mean())/n_.std():+.2f}   "
              f"p={p:.4f}")


if __name__ == "__main__":
    main()
