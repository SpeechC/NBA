"""Audit the advanced_stats drop before anything is built on it.

This repo has twice been burned by a vendor file silently changing coverage, so
nothing here gets used until join integrity and per-season coverage are checked
against the master panel and the train/holdout contract.

Checks:
  1  join rate onto the master regular-season panel, BY SEASON
  2  holdout coverage specifically (2024-25, 2025-26) -- the binding constraint
     on every feature that has to span discovery and validation
  3  sanity of PBP_POSS against the known truth (~96-102 per team-game) and
     against the master's own points
  4  internal consistency: PBP_CALC_PTS vs actual points, EV_FTA vs box FTA
  5  which columns are actually usable, i.e. present in BOTH the training
     seasons and the holdout
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ADV = "/mnt/c/NBA2/advanced_stats"


def master():
    from prepare_data import CSV, season_label
    raw = pd.read_csv(CSV, low_memory=False)
    raw["lbl"] = season_label(raw).astype(str)
    d = raw[raw["lbl"].str.contains("Regular Season", na=False)].copy()
    n = lambda c: pd.to_numeric(d[c], errors="coerce")
    d["date"] = pd.to_datetime(d["DATE"], errors="coerce")
    d["yr"] = d["lbl"].str.extract(r"(\d{4})")[0].astype(int)
    d["gid"] = d["GAME-ID"].astype(str).str.strip()
    d["total"] = n("CLOSING TOTAL_H")
    d["actual"] = d["PTS_H"] + d["PTS_R"]
    d["fta_box"] = n("TEAM_FTA_H") + n("TEAM_FTA_R")
    d = d.dropna(subset=["total", "actual", "date"])
    return d[d["total"].between(150, 300)].reset_index(drop=True)


def main():
    m = master()
    a = pd.read_csv(f"{ADV}/game_advanced_stats.csv", low_memory=False)
    a["gid"] = a["GAME-ID"].astype(str).str.strip()
    print(f"master regular-season panel : {len(m):,} games, "
          f"seasons {sorted(m['yr'].unique())}")
    print(f"advanced game file          : {len(a):,} rows, "
          f"{a['gid'].nunique():,} unique GAME-ID, {a.shape[1]} columns")
    dup = a["gid"].duplicated().sum()
    print(f"  duplicate GAME-ID rows: {dup}")

    print("\n" + "=" * 96)
    print("1 — JOIN RATE ONTO THE MASTER PANEL, BY SEASON")
    print("=" * 96)
    j = m.merge(a.drop(columns=["DATE", "TEAM_H", "TEAM_R"], errors="ignore"),
                on="gid", how="left", indicator=True)
    assert len(j) == len(m), f"merge changed row count {len(m)} -> {len(j)}"
    probe = ["ADV_OFF_RTG_H", "PBP_POSS_H", "EV_FOULS_H",
             "PBP_PTS_POSS_SD_H", "PBP_H1_POSS_H",
             "PBP_STATE_LEAD_10P_POSS_H", "EV_SHOOTING_FOULS_H"]
    rows = []
    for y, g in j.groupby("yr"):
        r = {"season": y, "games": len(g),
             "joined": round(100 * (g["_merge"] == "both").mean(), 1)}
        for c in probe:
            r[c.replace("_H", "").replace("PBP_", "").replace("ADV_", "")
              .replace("STATE_", "")] = round(100 * g[c].notna().mean(), 1)
        rows.append(r)
    print(pd.DataFrame(rows).to_string(index=False))

    print("\n" + "=" * 96)
    print("2 — HOLDOUT COVERAGE  (the binding constraint on any new feature)")
    print("=" * 96)
    from data_split import SPLIT_DATE
    dev, hold = j[j["date"] < SPLIT_DATE], j[j["date"] >= SPLIT_DATE]
    print(f"  split date {SPLIT_DATE.date()}   develop {len(dev):,}   "
          f"holdout {len(hold):,}")
    for c in probe:
        print(f"    {c:32} develop {100*dev[c].notna().mean():5.1f}%   "
              f"holdout {100*hold[c].notna().mean():5.1f}%")
    hy = hold.groupby(hold["date"].dt.year)["PBP_POSS_H"].apply(
        lambda s: round(100 * s.notna().mean(), 1))
    print(f"  holdout PBP_POSS_H coverage by calendar year: {dict(hy)}")

    print("\n" + "=" * 96)
    print("3 — SANITY: possessions, points, free throws")
    print("=" * 96)
    s = j.dropna(subset=["PBP_POSS_H", "PBP_POSS_R"])
    print(f"  n with possessions: {len(s):,}")
    for c in ("PBP_POSS_H", "PBP_POSS_R"):
        v = s[c]
        print(f"    {c:14} mean {v.mean():6.2f}  sd {v.std():5.2f}  "
              f"p1 {v.quantile(.01):.0f}  p99 {v.quantile(.99):.0f}   "
              f"[truth is ~96-102 per team-game]")
    gap = (s["PBP_POSS_H"] - s["PBP_POSS_R"]).abs()
    print(f"    |home poss - away poss|: mean {gap.mean():.2f}, "
          f"p99 {gap.quantile(.99):.0f}  [should be small; possessions alternate]")
    s2 = s.dropna(subset=["PBP_CALC_PTS_H", "PBP_CALC_PTS_R"])
    pbp_tot = s2["PBP_CALC_PTS_H"] + s2["PBP_CALC_PTS_R"]
    d_ = pbp_tot - s2["actual"]
    print(f"    PBP_CALC_PTS total vs box total: exact {100*(d_==0).mean():.1f}%,"
          f" within 2 {100*(d_.abs()<=2).mean():.1f}%, mean diff {d_.mean():+.2f}")
    s3 = j.dropna(subset=["EV_FTA_H", "EV_FTA_R", "fta_box"])
    ev = s3["EV_FTA_H"] + s3["EV_FTA_R"]
    d2 = ev - s3["fta_box"]
    print(f"    EV_FTA total vs box FTA (n={len(s3):,}): exact "
          f"{100*(d2==0).mean():.1f}%, within 2 {100*(d2.abs()<=2).mean():.1f}%,"
          f" mean diff {d2.mean():+.2f}")
    ppp = (s2["PBP_CALC_PTS_H"] + s2["PBP_CALC_PTS_R"]) / (
        s2["PBP_POSS_H"] + s2["PBP_POSS_R"])
    print(f"    implied points per possession: mean {ppp.mean():.4f}  "
          f"sd {ppp.std():.4f}  [league truth ~1.09-1.17]")

    print("\n" + "=" * 96)
    print("4 — USABLE COLUMN INVENTORY  (>=80% in BOTH develop and holdout)")
    print("=" * 96)
    num = [c for c in a.columns if c.startswith(("ADV_", "EV_", "PBP_"))
           and pd.api.types.is_numeric_dtype(j[c])]
    cov = pd.DataFrame({
        "col": num,
        "dev": [dev[c].notna().mean() for c in num],
        "hold": [hold[c].notna().mean() for c in num]})
    usable = cov[(cov["dev"] >= .8) & (cov["hold"] >= .8)]
    devonly = cov[(cov["dev"] >= .8) & (cov["hold"] < .8)]
    print(f"  {len(usable)} of {len(num)} numeric advanced columns are usable "
          f"across the split")
    print(f"  {len(devonly)} are develop-only -- unusable for anything that "
          f"must validate out of sample")
    fam = lambda c: ("ADV box" if c.startswith("ADV_") else
                     "EV events" if c.startswith("EV_") else
                     "PBP state" if "_STATE_" in c else
                     "PBP quarter/half" if any(k in c for k in
                        ("_Q1_", "_Q2_", "_Q3_", "_Q4_", "_H1_", "_H2_"))
                     else "PBP game")
    for lab, t in (("usable", usable), ("develop-only", devonly)):
        if len(t):
            print(f"\n  {lab} by family:")
            print(t["col"].map(fam).value_counts().to_string())
    if len(devonly):
        print("\n  develop-only examples: "
              + ", ".join(devonly["col"].head(8).tolist()))


if __name__ == "__main__":
    main()
