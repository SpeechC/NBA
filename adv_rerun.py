"""Two re-runs the advanced_stats drop makes possible.

A. REFEREE MECHANISM, properly measured.
   The earlier foul test used the master's TEAM_FTA, which the audit showed is
   a running average, not a per-game box score. ADV_PF_PER100_OPP_POSS and
   ADV_FTA_RATE are true per-game values and span the full train/holdout split,
   so the mechanism question can be asked for real: do the officials who move
   scoring also move foul calls?

B. THE PRE-REGISTERED eff_level_20 TEST ON ITS INTENDED BASIS.
   PREREG_eff_variance.md states explicitly that the vendor TEAM_OEFF was a
   substitute forced by coverage, and that "if a different eff_level_20 was
   intended, this test does not answer that hypothesis and must be re-run."
   ADV_OFF_RTG is the true per-game offensive rating and is 100% covered in
   both develop and holdout. Everything else about the design -- discovery
   through 2023-24, validation 2024-25 and 2025-26, discovery-frozen q80 tail
   cutoff, discovery-fitted quintile edges, the same five success criteria --
   is carried over unchanged from the pre-registration.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ADV = "/mnt/c/NBA2/advanced_stats/game_advanced_stats.csv"
COLS = ["ADV_OFF_RTG_H", "ADV_OFF_RTG_R", "ADV_PF_PER100_OPP_POSS_H",
        "ADV_PF_PER100_OPP_POSS_R", "ADV_FTA_RATE_H", "ADV_FTA_RATE_R",
        "ADV_EFG_H", "ADV_EFG_R"]


def attach(d):
    a = pd.read_csv(ADV, low_memory=False)
    a["gid"] = a["GAME-ID"].astype(str).str.strip()
    a = a[["gid"] + COLS]
    clash = set(a.columns) & set(d.columns) - {"gid"}
    assert not clash, f"column collision: {clash}"
    key = d["GAME-ID"].astype(str).str.strip() if "GAME-ID" in d else d["gid"]
    d = d.assign(gid=key)
    n0 = len(d)
    d = d.merge(a, on="gid", how="left")
    assert len(d) == n0, "merge changed row count"
    d["pf_rate"] = d["ADV_PF_PER100_OPP_POSS_H"] + d["ADV_PF_PER100_OPP_POSS_R"]
    d["fta_rate"] = d["ADV_FTA_RATE_H"] + d["ADV_FTA_RATE_R"]
    return d


# --------------------------------------------------------------- A. referees
def part_a():
    import refs
    d = attach(refs.build())
    reflist = sorted(set(d["ref1"]) | set(d["ref2"]) | set(d["ref3"]))
    print("=" * 96)
    print("A — REFEREE MECHANISM on TRUE per-game foul rates")
    print("=" * 96)
    for src, tgt in (("pf_rate", "pf_dm"), ("fta_rate", "ftr_dm")):
        d[tgt] = d[src] - d.groupby("yr")[src].transform("mean")
    for tgt, lab in (("pf_dm", "fouls per 100 opp poss"),
                     ("ftr_dm", "FTA rate (FTA/FGA)"),
                     ("pts_dm", "total points [reference]"),
                     ("e", "closing-total residual [reference]")):
        sub = d.dropna(subset=[tgt]).copy()
        y = sub[tgt].values
        print(f"  n={len(sub):,}  sd={y.std():.3f}")
        m, c, k, p, pm = refs.perm_test(sub, y, reflist, lab)
        if tgt in ("pf_dm", "ftr_dm"):
            refs.leaderboard(sub, reflist, m, c, k, y, lab)

    print("\n  Does a referee's scoring effect line up with their foul effect?")
    keep = None
    est = {}
    for tgt in ("pf_dm", "e"):
        sub = d.dropna(subset=[tgt]).copy()
        C = refs.codes(sub, reflist)
        flat = C.ravel()
        cnt = np.bincount(flat[flat >= 0], minlength=len(reflist)).astype(float)
        m = refs.ref_means(C, sub[tgt].values, len(reflist), cnt)
        k = cnt >= 100
        keep = k if keep is None else (keep & k)
        est[tgt] = (m, cnt)
    x = est["pf_dm"][0][keep] - est["pf_dm"][0][keep].mean()
    yv = est["e"][0][keep] - est["e"][0][keep].mean()
    r = np.corrcoef(x, yv)[0, 1]
    t = r * np.sqrt(len(x) - 2) / np.sqrt(1 - r * r)
    print(f"    corr(ref foul-rate effect, ref closing-residual effect) = "
          f"{r:+.4f}  t={t:+.2f}  over {keep.sum()} officials")


# ------------------------------------------------- B. pre-registered re-run
def part_b():
    import eff_variance as ev
    print("\n\n" + "=" * 96)
    print("B — PRE-REGISTERED eff_level_20 ON ITS INTENDED BASIS (ADV_OFF_RTG)")
    print("=" * 96)
    d = attach(ev.build())
    P = pd.concat([
        pd.DataFrame({"gid": d["gid"], "yr": d["yr"], "date": d["date"],
                      "team": d[f"TEAM_{s}"], "oeff": d[f"ADV_OFF_RTG_{s}"],
                      "side": s})
        for s in ("H", "R")]).sort_values("date")
    g = P.groupby(["yr", "team"])["oeff"]
    P["r20"] = g.transform(
        lambda s: s.shift(1).rolling(20, min_periods=12).mean())
    W = P[["gid", "side", "r20"]]
    h = W[W["side"] == "H"].drop(columns="side").rename(columns={"r20": "t20_h"})
    a = W[W["side"] == "R"].drop(columns="side").rename(columns={"r20": "t20_a"})
    assert not {"t20_h", "t20_a"} & set(d.columns), "name collision"
    d = d.merge(h, on="gid").merge(a, on="gid")
    d["eff_true_20"] = d["t20_h"] + d["t20_a"]
    cov = d["eff_true_20"].notna().groupby(d["yr"]).mean().round(3)
    print(f"  feature coverage by season: {dict(cov)}")
    old = d[["eff_level_20", "eff_true_20"]].dropna()
    print(f"  corr(vendor eff_level_20, true-rating eff_true_20) = "
          f"{np.corrcoef(old['eff_level_20'], old['eff_true_20'])[0,1]:+.4f}")
    print(f"  sd: vendor {old['eff_level_20'].std():.2f}   "
          f"true {old['eff_true_20'].std():.2f}")
    ev.run(d, "eff_true_20", "PRIMARY TEST, intended basis")


if __name__ == "__main__":
    part_a()
    part_b()
