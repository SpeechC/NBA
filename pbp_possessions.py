"""Aggregate the possession-level play-by-play to game x team, once, and cache.

Serves both the live-ball turnover test and the second-chance test. Regular
season only; the _po playoff files are not used.

One row per possession is taken via ADV_IS_POSSESSION_FIRST_ROW == 1, verified
to give exactly one row per ADV_POSSESSION_UID, with ADV_POINTS_POSS_CALC
constant within a possession.
"""
import glob
import os
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

SRC = "/mnt/c/NBA2/advanced_stats/pbp_rows"
OUT = "pbp_poss_agg.csv"
COLS = ["GAMEID", "GAMEDATE", "ADV_IS_POSSESSION_FIRST_ROW",
        "ADV_OFFENSE_TEAM_ABBR", "ADV_DEFENSE_TEAM_ABBR",
        "ADV_START_AFTER_STEAL", "ADV_POINTS_POSS_CALC", "ADV_HAS_OREB"]


def build(force=False):
    if os.path.exists(OUT) and not force:
        return pd.read_csv(OUT)
    files = sorted(f for f in glob.glob(f"{SRC}/pbpstats_*_advanced.csv")
                   if "_po_" not in os.path.basename(f))
    out = []
    for f in files:
        d = pd.read_csv(f, usecols=COLS, low_memory=False)
        d = d[d["ADV_IS_POSSESSION_FIRST_ROW"] == 1]
        d["pts"] = pd.to_numeric(d["ADV_POINTS_POSS_CALC"], errors="coerce")
        d["steal"] = pd.to_numeric(d["ADV_START_AFTER_STEAL"],
                                   errors="coerce").fillna(0)
        d["oreb"] = pd.to_numeric(d["ADV_HAS_OREB"], errors="coerce").fillna(0)
        g = d.groupby(["GAMEID", "ADV_OFFENSE_TEAM_ABBR"], as_index=False).agg(
            poss=("pts", "size"),
            pts=("pts", "sum"),
            steal_poss=("steal", "sum"),
            steal_pts=("pts", lambda s: np.nan),
            oreb_poss=("oreb", "sum"))
        # sums conditional on the possession type
        sp = d[d["steal"] == 1].groupby(
            ["GAMEID", "ADV_OFFENSE_TEAM_ABBR"], as_index=False)["pts"].sum()
        sp = sp.rename(columns={"pts": "steal_pts_"})
        op = d[d["oreb"] == 1].groupby(
            ["GAMEID", "ADV_OFFENSE_TEAM_ABBR"], as_index=False)["pts"].sum()
        op = op.rename(columns={"pts": "oreb_pts_"})
        g = g.drop(columns=["steal_pts"]).merge(
            sp, on=["GAMEID", "ADV_OFFENSE_TEAM_ABBR"], how="left").merge(
            op, on=["GAMEID", "ADV_OFFENSE_TEAM_ABBR"], how="left")
        g["steal_pts"] = g["steal_pts_"].fillna(0.0)
        g["oreb_pts"] = g["oreb_pts_"].fillna(0.0)
        g = g.drop(columns=["steal_pts_", "oreb_pts_"])
        g["src"] = os.path.basename(f)
        out.append(g)
        print(f"  {os.path.basename(f):34} {len(d):8,} possessions -> "
              f"{len(g):5,} game-team rows", flush=True)
    A = pd.concat(out, ignore_index=True)
    A = A.rename(columns={"GAMEID": "gid", "ADV_OFFENSE_TEAM_ABBR": "team"})
    A["gid"] = A["gid"].astype(str).str.strip()
    A.to_csv(OUT, index=False)
    return A


def main():
    A = build(force=True)
    print(f"\n{len(A):,} game-team rows, {A['gid'].nunique():,} games")
    A["ppp"] = A["pts"] / A["poss"]
    A["steal_ppp"] = A["steal_pts"] / A["steal_poss"].replace(0, np.nan)
    A["other_ppp"] = ((A["pts"] - A["steal_pts"])
                      / (A["poss"] - A["steal_poss"]).replace(0, np.nan))
    A["oreb_ppp"] = A["oreb_pts"] / A["oreb_poss"].replace(0, np.nan)
    print(f"  possessions per game-team: mean {A['poss'].mean():.2f}")
    print(f"  overall PPP               {A['ppp'].mean():.4f}")
    print(f"  steal-start PPP           {A['steal_ppp'].mean():.4f}")
    print(f"  non-steal PPP             {A['other_ppp'].mean():.4f}")
    print(f"  steal-start premium       "
          f"{A['steal_ppp'].mean()-A['other_ppp'].mean():+.4f}")
    print(f"  steal-start share of poss {A['steal_poss'].sum()/A['poss'].sum():.4f}")
    print(f"  OREB-extended PPP         {A['oreb_ppp'].mean():.4f}")
    print(f"  OREB-extended share       {A['oreb_poss'].sum()/A['poss'].sum():.4f}")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
