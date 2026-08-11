"""Rich possession-level team features from play-by-play — the untested dimension.

Everything pbp-derived so far has been an aggregate the box score already contains
(possessions, efficiency, garbage-time-adjusted efficiency, player impact). This
builds the part the box score CANNOT express:

  * POSSESSION CONTEXT -- `STARTTYPE` records how each possession began (off a
    made basket, off a steal, off a dead ball, out of a timeout, off a missed
    three...). Transition versus half-court is invisible in a box score.
  * SHOT MIX -- dunk / layup / jumper / three / contested, parsed from the event
    description. Shot *type* is recoverable; shot *location* is not (no x/y in
    this export).
  * GAME STATE -- `STARTSCOREDIFFERENTIAL` gives the margin each possession began
    at, so possessions can be split by competitive state.

Output: one row per team-game, ~30 features, written to
/home/dpope/data/pbp_team_features.parquet

These are then lagged and tested two ways -- raw into ridge, and PCA-compressed --
against the frozen baseline.
"""

import duckdb
import numpy as np
import pandas as pd

PBP = "/home/dpope/data/pbp_lineups_all.parquet"
OUT = "/home/dpope/data/pbp_team_features.parquet"
TEAM_LO, TEAM_HI = 1610612737, 1610612766


def build_season(season):
    """Team-game possession-context and shot-mix features for one season."""
    con = duckdb.connect()
    q = f"""
    WITH ev AS (
      SELECT
        lpad(CAST(GAME_ID AS VARCHAR),10,'0')             AS gid,
        CASE WHEN PLAYER1_TEAM_ID BETWEEN {TEAM_LO} AND {TEAM_HI}
             THEN PLAYER1_TEAM_ID
             WHEN PLAYER1_ID  BETWEEN {TEAM_LO} AND {TEAM_HI}
             THEN PLAYER1_ID END                          AS team,
        EVENTMSGTYPE                                      AS ev,
        STARTTYPE,
        STARTSCOREDIFFERENTIAL                            AS sdiff,
        lower(coalesce(HOMEDESCRIPTION, VISITORDESCRIPTION, '')) AS txt
      FROM read_parquet('{PBP}')
      WHERE SEASON = '{season}' AND SEASON_TYPE = 'RegularSeason'
    )
    SELECT gid, team,
      count(*)                                                        AS n_ev,
      -- possession context: share of possessions by how they started
      sum(CASE WHEN STARTTYPE LIKE '%Steal%'      THEN 1 ELSE 0 END)  AS st_steal,
      sum(CASE WHEN STARTTYPE LIKE '%Dead Ball%'  THEN 1 ELSE 0 END)  AS st_deadball,
      sum(CASE WHEN STARTTYPE LIKE '%Timeout%'    THEN 1 ELSE 0 END)  AS st_timeout,
      sum(CASE WHEN STARTTYPE LIKE '%At Rim%'     THEN 1 ELSE 0 END)  AS st_rim,
      sum(CASE WHEN STARTTYPE LIKE '%Arc 3%'      THEN 1 ELSE 0 END)  AS st_arc3,
      sum(CASE WHEN STARTTYPE LIKE '%Corner 3%'   THEN 1 ELSE 0 END)  AS st_corner3,
      sum(CASE WHEN STARTTYPE LIKE '%Mid-Range%'  THEN 1 ELSE 0 END)  AS st_mid,
      sum(CASE WHEN STARTTYPE LIKE '%FT%'         THEN 1 ELSE 0 END)  AS st_ft,
      sum(CASE WHEN STARTTYPE LIKE '%Miss%'       THEN 1 ELSE 0 END)  AS st_miss,
      sum(CASE WHEN STARTTYPE LIKE '%Make%'       THEN 1 ELSE 0 END)  AS st_make,
      sum(CASE WHEN STARTTYPE IS NOT NULL         THEN 1 ELSE 0 END)  AS st_any,
      -- shot mix, from description text
      sum(CASE WHEN ev IN (1,2) AND txt LIKE '%3pt%'        THEN 1 ELSE 0 END) AS sh_three,
      sum(CASE WHEN ev IN (1,2) AND txt LIKE '%dunk%'       THEN 1 ELSE 0 END) AS sh_dunk,
      sum(CASE WHEN ev IN (1,2) AND txt LIKE '%layup%'      THEN 1 ELSE 0 END) AS sh_layup,
      sum(CASE WHEN ev IN (1,2) AND txt LIKE '%jump shot%'  THEN 1 ELSE 0 END) AS sh_jumper,
      sum(CASE WHEN ev IN (1,2) AND (txt LIKE '%fadeaway%' OR txt LIKE '%turnaround%'
                                     OR txt LIKE '%step back%') THEN 1 ELSE 0 END) AS sh_tough,
      sum(CASE WHEN ev IN (1,2) AND txt LIKE '%driving%'    THEN 1 ELSE 0 END) AS sh_drive,
      sum(CASE WHEN ev IN (1,2) AND txt LIKE '%pullup%'     THEN 1 ELSE 0 END) AS sh_pullup,
      sum(CASE WHEN ev IN (1,2)                             THEN 1 ELSE 0 END) AS sh_any,
      sum(CASE WHEN ev = 1                                  THEN 1 ELSE 0 END) AS sh_made,
      -- assisted share: made shots whose description names an assist
      sum(CASE WHEN ev = 1 AND txt LIKE '%ast%'             THEN 1 ELSE 0 END) AS sh_assisted,
      -- game state the possessions were played in
      avg(CAST(sdiff AS DOUBLE))                                       AS sdiff_mean,
      stddev_pop(CAST(sdiff AS DOUBLE))                                AS sdiff_sd
    FROM ev
    WHERE team IS NOT NULL
    GROUP BY gid, team
    """
    d = con.execute(q).fetchdf()
    if d.empty:
        return d
    # convert counts to rates so team pace does not dominate every feature
    for c in [c for c in d.columns if c.startswith("st_") and c not in ("st_any",)]:
        d[c] = d[c] / d["st_any"].replace(0, np.nan)
    for c in [c for c in d.columns if c.startswith("sh_") and c not in ("sh_any",)]:
        d[c] = d[c] / d["sh_any"].replace(0, np.nan)
    d["st_cover"] = d["st_any"] / d["n_ev"]
    d["season"] = season
    return d.drop(columns=["n_ev"])


def main():
    seasons = ["2017-18", "2018-19", "2020-21", "2021-22", "2022-23",
               "2023-24", "2024-25"]
    frames = []
    for s in seasons:
        d = build_season(s)
        frames.append(d)
        print(f"{s}: {len(d):,} team-games, {d.shape[1]} cols, "
              f"STARTTYPE coverage {100 * d['st_cover'].mean():.1f}%", flush=True)
    out = pd.concat(frames, ignore_index=True)
    out.to_parquet(OUT, index=False)
    print(f"\nwrote {OUT}  ({len(out):,} rows, {out.shape[1]} columns)")
    print(out.describe().T[["mean", "std", "min", "max"]].round(4).to_string())


if __name__ == "__main__":
    main()
