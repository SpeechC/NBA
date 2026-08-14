"""League foul regime vs referee identity shock. Pre-registered in
PREREG_ref_regime.md.

Three primary tests, nothing else:

  1  continuous coefficient gap, BOTH states estimated simultaneously
  2  TIME-LOCAL crew permutation of the CrewShock gap -- crews randomized
     within disjoint 7-day blocks, so the league foul climate is held fixed
     while referee identity is randomized
  3  frozen extreme regime, CrewShock >= develop Q85 primary, Q90 secondary

Season-by-season coefficients are diagnostics, not tests.

The crew permutation cannot serve as a null for the LEAGUE coefficient, since
reshuffling crews leaves LeagueFoulState untouched. That coefficient gets a
moving-block bootstrap over calendar time instead.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import ref_features as rf
import ref_shock as rsk
from data_split import SPLIT_DATE
from dispersion_priced import ols

NPERM, NBOOT = 1000, 1000
BLOCK_DAYS = 7
BOOT_BLOCK = 200
BE = 110 / 210
RNG = np.random.default_rng(8128)
STATES = ["LeagueFoulState", "CrewShock"]


def build():
    d = rsk.build().drop(columns=["CrewFoul"], errors="ignore")
    feat, k, sig, _ = rf.build(save=False)
    feat = feat[["gid"] + STATES + ["min_prior"]]
    assert not (set(feat.columns) & set(d.columns)) - {"gid"}
    n0 = len(d)
    d = d.merge(feat, on="gid", how="left")
    assert len(d) == n0
    d = d.dropna(subset=STATES + rsk.CTRL + ["e"]).reset_index(drop=True)
    d["blk"] = (d["yr"].astype(str) + "_"
                + ((d["date"] - d.groupby("yr")["date"].transform("min"))
                   .dt.days // BLOCK_DAYS).astype(str))
    return d, k, sig


def gaps(x, states=STATES):
    """Returns {state: (c_market, c_true, gap, t_gap)} from one X matrix."""
    X = np.column_stack([x[s] for s in states] + [x[c] for c in rsk.CTRL])
    bm, sem, tm = ols(x["total"].values, X)
    bt, set_, tt = ols(x["actual"].values, X)
    bg, seg, tg = ols(x["e"].values, X)
    return {s: (bm[i + 1], bt[i + 1], bg[i + 1], tg[i + 1])
            for i, s in enumerate(states)}


def main():
    d, k, sig = build()
    dev = d[d["date"] < SPLIT_DATE]
    hold = d[d["date"] >= SPLIT_DATE]
    print("=" * 100)
    print("LEAGUE FOUL REGIME vs REFEREE IDENTITY SHOCK")
    print("=" * 100)
    print(f"  {len(d):,} games   develop {len(dev):,}   holdout {len(hold):,}"
          f"   features built on the full 9,489-game universe")
    print(f"  corr(CrewShock, LeagueFoulState) = "
          f"{d[STATES].corr().iloc[0,1]:+.4f}")
    for s in STATES:
        r2 = np.corrcoef(d[s], d[rsk.CTRL].values @ np.linalg.lstsq(
            d[rsk.CTRL].values, d[s].values, rcond=None)[0])[0, 1] ** 2
        print(f"  R^2 of {s:16} on the {len(rsk.CTRL)} team controls: {r2:.5f}")
    nb = d.groupby("blk").size()
    print(f"  {d['blk'].nunique()} disjoint {BLOCK_DAYS}-day blocks, "
          f"median {nb.median():.0f} games each")

    print("\n" + "=" * 100)
    print("TEST 1 — CONTINUOUS GAP, both states estimated together")
    print("=" * 100)
    print(f"    {'window':9} {'state':17} {'c_market':>10} {'c_true':>9} "
          f"{'GAP':>9} {'t':>7}")
    res = {}
    for lab, x in (("develop", dev), ("holdout", hold), ("all", d)):
        g = gaps(x)
        res[lab] = g
        for s in STATES:
            cm, ca, gp, t = g[s]
            print(f"    {lab:9} {s:17} {cm:10.3f} {ca:9.3f} {gp:9.3f} {t:7.2f}")
        print()

    print("=" * 100)
    print("TEST 2 — TIME-LOCAL crew permutation of the CrewShock gap")
    print("=" * 100)
    print(f"  Crews randomized within {BLOCK_DAYS}-day blocks. League climate")
    print(f"  held fixed. The null mean MUST come back near zero.")
    uni = rf.universe()
    ublk = (uni["yr"].astype(str) + "_"
            + ((uni["date"] - uni.groupby("yr")["date"].transform("min"))
               .dt.days // BLOCK_DAYS).astype(str)).values
    ucrew = uni[["ref1", "ref2", "ref3"]].values
    ublocks = [np.where(ublk == b)[0] for b in pd.unique(ublk)]
    ugid = uni["gid"].values
    keep = pd.Series(np.arange(len(uni)), index=ugid).reindex(d["gid"]).values

    obs = {lab: res[lab]["CrewShock"][2] for lab in ("develop", "holdout", "all")}
    null = {lab: np.empty(NPERM) for lab in obs}
    sub = uni.copy()
    dd = d.copy()
    for j in range(NPERM):
        perm = ucrew.copy()
        for b in ublocks:
            if len(b) > 1:
                perm[b] = ucrew[b][RNG.permutation(len(b))]
        sub["ref1"], sub["ref2"], sub["ref3"] = perm[:, 0], perm[:, 1], perm[:, 2]
        cs = rf.matched_ref_effect(sub, k)["CrewShock"].values
        dd["CrewShock"] = cs[keep]
        for lab, x in (("develop", dd[dd["date"] < SPLIT_DATE]),
                       ("holdout", dd[dd["date"] >= SPLIT_DATE]),
                       ("all", dd)):
            null[lab][j] = gaps(x)["CrewShock"][2]
    print(f"\n    {'window':9} {'observed':>10} {'null mean':>11} "
          f"{'null sd':>9} {'z':>7} {'p':>8}")
    for lab in ("develop", "holdout", "all"):
        n_ = null[lab]
        p = (1 + np.sum(n_ >= obs[lab])) / (NPERM + 1)
        z = (obs[lab] - n_.mean()) / n_.std()
        print(f"    {lab:9} {obs[lab]:10.4f} {n_.mean():11.4f} "
              f"{n_.std():9.4f} {z:7.2f} {p:8.4f}")

    print("\n" + "=" * 100)
    print("LEAGUE COEFFICIENT — moving-block bootstrap over calendar time")
    print("=" * 100)
    dsort = d.sort_values("date").reset_index(drop=True)
    nblk = int(np.ceil(len(dsort) / BOOT_BLOCK))
    starts = np.arange(len(dsort) - BOOT_BLOCK)
    bl = np.empty(NBOOT)
    for j in range(NBOOT):
        pick = RNG.choice(starts, nblk, replace=True)
        idx = np.concatenate([np.arange(s, s + BOOT_BLOCK) for s in pick])
        bl[j] = gaps(dsort.iloc[idx])["LeagueFoulState"][2]
    o = res["all"]["LeagueFoulState"][2]
    print(f"    observed league gap {o:+.4f}   bootstrap sd {bl.std():.4f}   "
          f"z={o/bl.std():+.2f}   "
          f"share of draws <= 0: {100*np.mean(bl <= 0):.1f}%")
    print(f"    (OLS t was {res['all']['LeagueFoulState'][3]:+.2f}; the block "
          f"bootstrap respects serial correlation)")

    print("\n" + "=" * 100)
    print("TEST 3 — FROZEN EXTREME REGIME")
    print("=" * 100)
    for q, tag in ((0.85, "PRIMARY Q85"), (0.90, "secondary Q90")):
        thr = dev["CrewShock"].quantile(q)
        print(f"\n  {tag}   develop threshold CrewShock >= {thr:+.4f}")
        print(f"    {'window':9} {'n':>6} {'mean e':>9} {'over %':>8} "
              f"{'1.96se':>8} {'edge vs BE':>11}")
        for lab, x in (("develop", dev), ("holdout", hold)):
            g = x[x["CrewShock"] >= thr]
            ov = (g["e"] > 0).mean()
            se = 1.96 * np.sqrt(ov * (1 - ov) / len(g))
            print(f"    {lab:9} {len(g):6,} {g['e'].mean():9.3f} "
                  f"{100*ov:8.2f} {100*se:8.2f} {100*ov-100*BE:11.2f}")
        for y in sorted(hold["yr"].unique()):
            g = hold[(hold["yr"] == y) & (hold["CrewShock"] >= thr)]
            ov = (g["e"] > 0).mean()
            print(f"      {y:<7} {len(g):6,} {g['e'].mean():9.3f} "
                  f"{100*ov:8.2f}")

    print("\n" + "=" * 100)
    print("DIAGNOSTIC — season-by-season gaps (not hypothesis tests)")
    print("=" * 100)
    print(f"    {'season':8} {'n':>6} {'crew gap':>10} {'league gap':>12} "
          f"{'mean e':>9}")
    for y, g in d.groupby("yr"):
        if len(g) < 150:
            continue
        gg = gaps(g)
        print(f"    {y:<8} {len(g):6,} {gg['CrewShock'][2]:10.3f} "
              f"{gg['LeagueFoulState'][2]:12.3f} {g['e'].mean():9.3f}")


if __name__ == "__main__":
    main()
