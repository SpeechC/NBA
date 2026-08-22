"""Offensive-rebound possession extensions, extracted once and cached.

An OREB does NOT create a new possession. It retains the existing offensive
possession and creates another scoring opportunity inside it. The extraction
reflects that: possessions are the unit, extensions are counted within them,
and scoring is split into first-chance and second-chance.

Structure of the source, verified by inspection:
  (GAME_ID, PERIOD, STARTTIME, ENDTIME) delimits one possession; every event
  row inside it repeats the same pair.
  OFFENSIVEREBOUNDS is a possession-level COUNT repeated on every row.
  SCORE is populated only on scoring events, giving a running "H - A" total.

Within a possession a defensive rebound ends it, so it can only be the last
rebound. Therefore the first `OFFENSIVEREBOUNDS` rebound events are the
offensive ones, and any event occurring after the first rebound is
second-chance.

Dead-ball and team rebounds that pbpstats does not count toward
OFFENSIVEREBOUNDS are excluded automatically: the count drives the flag, not
the raw msg-4 events.
"""
import os
import warnings

import duckdb
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

PBP = "/home/dpope/data/pbp_lineups_all.parquet"
POSS_ROWS = "/mnt/c/NBA2/advanced_stats/pbp_rows"
OUT = "oreb_possessions.csv"

SQL = f"""
WITH ev AS (
  SELECT lpad(CAST(GAME_ID AS VARCHAR),10,'0')            AS gid,
         PERIOD, STARTTIME, ENDTIME, EVENTNUM,
         EVENTMSGTYPE                                     AS msg,
         COALESCE(OFFENSIVEREBOUNDS, 0)                   AS oreb_cnt,
         COALESCE(TURNOVERS, 0)                           AS tov,
         COALESCE(FG2A,0) + COALESCE(FG3A,0)              AS fga_poss,
         PLAYER1_TEAM_ABBREVIATION                        AS p1team,
         TRY_CAST(split_part(SCORE,' - ',1) AS INTEGER)
       + TRY_CAST(split_part(SCORE,' - ',2) AS INTEGER)   AS tot
  FROM read_parquet('{PBP}')
  WHERE SEASON_TYPE = 'RegularSeason' AND PERIOD <= 4
    AND STARTTIME IS NOT NULL AND ENDTIME IS NOT NULL
),
ff AS (
  SELECT *,
    last_value(tot IGNORE NULLS) OVER (
      PARTITION BY gid ORDER BY EVENTNUM
      ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)   AS tot_ff
  FROM ev
),
pts AS (
  SELECT *,
    COALESCE(tot_ff - lag(tot_ff) OVER (PARTITION BY gid ORDER BY EVENTNUM),
             0)                                           AS pts
  FROM ff
),
mark AS (
  SELECT *,
    sum(CASE WHEN msg = 4 THEN 1 ELSE 0 END) OVER (
      PARTITION BY gid, PERIOD, STARTTIME, ENDTIME ORDER BY EVENTNUM
      ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)   AS reb_seen
  FROM pts
)
SELECT gid, PERIOD, STARTTIME, ENDTIME,
       mode(p1team) FILTER (WHERE msg IN (1,2,5))         AS team,
       max(oreb_cnt)                                      AS oreb_ext,
       max(tov)                                           AS tov,
       max(fga_poss)                                      AS fga,
       sum(pts)                                           AS pts,
       sum(CASE WHEN reb_seen >= 1 AND oreb_cnt >= 1 THEN pts ELSE 0 END)
                                                          AS pts_2c,
       sum(CASE WHEN msg = 3 AND reb_seen >= 1 AND oreb_cnt >= 1
                THEN 1 ELSE 0 END)                        AS fta_2c,
       sum(CASE WHEN msg IN (1,2) AND reb_seen >= 1 AND oreb_cnt >= 1
                THEN 1 ELSE 0 END)                        AS fga_2c
FROM mark
GROUP BY gid, PERIOD, STARTTIME, ENDTIME
"""


def build(force=False):
    if os.path.exists(OUT) and not force:
        return pd.read_csv(OUT, dtype={"gid": str})
    con = duckdb.connect()
    P = con.execute(SQL).fetchdf()
    P["gid"] = P["gid"].astype(str)
    P["pts_1c"] = P["pts"] - P["pts_2c"]
    print(f"  {len(P):,} possessions extracted")

    print(f"  offensive team derived in-source for "
          f"{100*P['team'].notna().mean():.2f}% of possessions")
    P.to_csv(OUT, index=False)
    return P


def game_team(P):
    """Aggregate possessions to game x offensive team."""
    P = P.dropna(subset=["team"])
    g = P.groupby(["gid", "team"], as_index=False).agg(
        poss=("pts", "size"),
        pts=("pts", "sum"),
        oreb_ext=("oreb_ext", "sum"),
        poss_with_oreb=("oreb_ext", lambda s: int((s >= 1).sum())),
        pts_2c=("pts_2c", "sum"),
        pts_1c=("pts_1c", "sum"),
        fga_2c=("fga_2c", "sum"),
        fta_2c=("fta_2c", "sum"),
        fga=("fga", "sum"),
        tov=("tov", "sum"))
    g["oreb_rate"] = g["oreb_ext"] / g["poss"]
    return g


def main():
    P = build(force=True)
    print(f"\n  possessions {len(P):,}   games {P['gid'].nunique():,}")
    print(f"  OREB extensions per possession: mean {P['oreb_ext'].mean():.4f}")
    print(f"  possessions with >=1 OREB: {100*(P['oreb_ext']>=1).mean():.2f}%")
    print(f"  distribution of extensions per possession:")
    print("    " + "  ".join(
        f"{int(k)}:{v:,}" for k, v in
        P["oreb_ext"].value_counts().sort_index().head(6).items()))
    print(f"\n  points per possession        {P['pts'].mean():.4f}")
    print(f"  first-chance points/poss     {P['pts_1c'].mean():.4f}")
    print(f"  second-chance points/poss    {P['pts_2c'].mean():.4f}")
    ext = P[P["oreb_ext"] >= 1]
    print(f"\n  possessions WITH an extension (n={len(ext):,}):")
    print(f"    points/poss {ext['pts'].mean():.4f}   "
          f"of which second-chance {ext['pts_2c'].mean():.4f}")
    print(f"    second-chance points per EXTENSION "
          f"{ext['pts_2c'].sum()/ext['oreb_ext'].sum():.4f}")
    print(f"    second-chance FGA per extension "
          f"{ext['fga_2c'].sum()/ext['oreb_ext'].sum():.4f}   "
          f"FTA per extension {ext['fta_2c'].sum()/ext['oreb_ext'].sum():.4f}")
    noext = P[P["oreb_ext"] == 0]
    print(f"  possessions WITHOUT (n={len(noext):,}): points/poss "
          f"{noext['pts'].mean():.4f}")

    g = game_team(P)
    print(f"\n  game-team rows {len(g):,}")
    print(f"  per game-team: poss {g['poss'].mean():.2f}   "
          f"OREB ext {g['oreb_ext'].mean():.2f}   "
          f"2C points {g['pts_2c'].mean():.2f}   "
          f"OREB rate {g['oreb_rate'].mean():.4f}")

    # cross-check against the advanced box OREB%
    adv = pd.read_csv("/mnt/c/NBA2/advanced_stats/game_advanced_stats.csv",
                      low_memory=False)
    adv["gid"] = adv["GAME-ID"].astype(str).str.strip().str.zfill(10)
    chk = []
    for s in ("H", "R"):
        chk.append(pd.DataFrame({"gid": adv["gid"],
                                 "team": adv[f"ADV_TEAM_ABBR_{s}"],
                                 "oreb_pct": adv[f"ADV_OREB_PCT_{s}"]}))
    C = pd.concat(chk).dropna()
    j = g.merge(C, on=["gid", "team"], how="inner")
    print(f"\n  cross-check vs ADV_OREB_PCT on {len(j):,} game-teams: "
          f"corr(oreb_ext, OREB%) = "
          f"{np.corrcoef(j['oreb_ext'], j['oreb_pct'])[0,1]:+.4f}")
    print(f"  wrote {OUT}")


if __name__ == "__main__":
    main()
