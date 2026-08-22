"""Rotation concentration per game-team, from the lineup play-by-play.

PLAYER1..PLAYER5 and PLAYER6..PLAYER10 hold the two on-court fives. Each event
carries the game clock in seconds elapsed, so the interval to the next event is
credited to whichever ten players were on the floor.

Concentration is the Herfindahl index of a team's within-game minutes share:

    HHI = sum_p (share_p)^2      1/5 = 0.200 is a perfectly even five-man
                                 split; higher means minutes concentrated in
                                 fewer players (shorter rotation)

Also emitted: n_players used, and the top-7 minutes share.

Group-to-team mapping is by majority vote — events whose acting player sits in
slots 1-5 attribute their team abbreviation to group A, and vice versa.
"""
import os
import warnings

import duckdb
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

PBP = "/home/dpope/data/pbp_lineups_all.parquet"
OUT = "rotation_game_team.csv"

SLOTS = "\n  UNION ALL\n".join(
    f"  SELECT gid, dt, {('\'A\'' if i <= 5 else '\'B\'')} AS grp, "
    f"PLAYER{i} AS pid FROM base"
    for i in range(1, 11))

SQL = f"""
WITH ev AS (
  SELECT lpad(CAST(GAME_ID AS VARCHAR),10,'0')            AS gid,
         EVENTNUM, PERIOD,
         CAST(PCTIMESTRING AS DOUBLE)                     AS t,
         PLAYER1, PLAYER2, PLAYER3, PLAYER4, PLAYER5,
         PLAYER6, PLAYER7, PLAYER8, PLAYER9, PLAYER10
  FROM read_parquet('{PBP}')
  WHERE SEASON_TYPE = 'RegularSeason' AND PERIOD <= 4
),
base AS (
  SELECT *, GREATEST(COALESCE(
      lead(t) OVER (PARTITION BY gid ORDER BY EVENTNUM) - t, 0), 0) AS dt
  FROM ev
),
long AS (
{SLOTS}
)
SELECT gid, grp, pid, sum(dt) AS secs
FROM long
WHERE pid IS NOT NULL AND pid > 0
GROUP BY gid, grp, pid
"""

MAPSQL = f"""
WITH ev AS (
  SELECT lpad(CAST(GAME_ID AS VARCHAR),10,'0')  AS gid,
         PLAYER1_ID                             AS aid,
         PLAYER1_TEAM_ABBREVIATION              AS abbr,
         PLAYER1, PLAYER2, PLAYER3, PLAYER4, PLAYER5
  FROM read_parquet('{PBP}')
  WHERE SEASON_TYPE = 'RegularSeason' AND PERIOD <= 4
    AND PLAYER1_TEAM_ABBREVIATION IS NOT NULL AND PLAYER1_ID > 0
)
SELECT gid, abbr,
       sum(CASE WHEN aid IN (PLAYER1,PLAYER2,PLAYER3,PLAYER4,PLAYER5)
                THEN 1 ELSE 0 END)              AS in_A,
       count(*)                                 AS n
FROM ev GROUP BY gid, abbr
"""


def build(force=False):
    if os.path.exists(OUT) and not force:
        return pd.read_csv(OUT, dtype={"gid": str})
    con = duckdb.connect()
    P = con.execute(SQL).fetchdf()
    P["gid"] = P["gid"].astype(str)
    print(f"  {len(P):,} game-group-player rows")

    M = con.execute(MAPSQL).fetchdf()
    M["gid"] = M["gid"].astype(str)
    M["frac_A"] = M["in_A"] / M["n"]
    M["grp"] = np.where(M["frac_A"] > 0.5, "A", "B")
    M = M[M["n"] >= 20][["gid", "grp", "abbr"]]
    # keep only games where the two abbreviations map to distinct groups
    ok = M.groupby("gid")["grp"].nunique() == 2
    M = M[M["gid"].isin(ok[ok].index)]
    print(f"  group->team mapping resolved for {M['gid'].nunique():,} games")

    P = P.merge(M, on=["gid", "grp"], how="inner")
    tot = P.groupby(["gid", "grp"])["secs"].transform("sum")
    P["share"] = P["secs"] / tot
    g = P.groupby(["gid", "grp", "abbr"], as_index=False).agg(
        hhi=("share", lambda s: float((s ** 2).sum())),
        n_players=("share", "size"),
        team_secs=("secs", "sum"))
    top7 = (P.sort_values("share", ascending=False)
              .groupby(["gid", "grp"]).head(7)
              .groupby(["gid", "grp"], as_index=False)["share"].sum()
              .rename(columns={"share": "top7_share"}))
    g = g.merge(top7, on=["gid", "grp"], how="left")
    g = g.rename(columns={"abbr": "team"}).drop(columns=["grp"])
    g.to_csv(OUT, index=False)
    return g


def main():
    g = build(force=True)
    print(f"\n  {len(g):,} game-team rows, {g['gid'].nunique():,} games")
    print(f"  minutes per team-game: {g['team_secs'].mean()/60:.1f} "
          f"(expect ~240 for five players x 48 min)")
    print(f"  players used  mean {g['n_players'].mean():.2f}  "
          f"median {g['n_players'].median():.0f}  "
          f"p5 {g['n_players'].quantile(.05):.0f}  "
          f"p95 {g['n_players'].quantile(.95):.0f}")
    print(f"  HHI           mean {g['hhi'].mean():.4f}  "
          f"sd {g['hhi'].std():.4f}  "
          f"p5 {g['hhi'].quantile(.05):.4f}  p95 {g['hhi'].quantile(.95):.4f}")
    print(f"    (0.200 = even five-man split; 1/n_players is the even-rotation "
          f"floor)")
    print(f"  top-7 share   mean {g['top7_share'].mean():.4f}  "
          f"sd {g['top7_share'].std():.4f}")
    print(f"\n  corr(HHI, n_players) = "
          f"{np.corrcoef(g['hhi'], g['n_players'])[0,1]:+.4f}  "
          f"[should be strongly negative]")
    print(f"  corr(HHI, top7 share) = "
          f"{np.corrcoef(g['hhi'], g['top7_share'])[0,1]:+.4f}")
    print(f"\n  wrote {OUT}")


if __name__ == "__main__":
    main()
