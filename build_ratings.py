"""Build team-game efficiency ratings, raw and garbage-time-adjusted.

For every team-game this produces possessions, points scored and points allowed,
computed twice: over all possessions, and over competitive possessions only (the
Bill James safe-lead flag from garbage_time.py). The competitive version is the
whole point — raw OEFF/DEFF average in possessions played after the result was
decided, which carry no information about team strength.

Output: one row per team-game, written to /home/dpope/data/team_game_ratings.parquet
"""

import duckdb
import numpy as np
import pandas as pd

from garbage_time import annotate, possession_table

PBP = "/home/dpope/data/pbp_lineups_all.parquet"
OUT = "/home/dpope/data/team_game_ratings.parquet"

COLS = ["GAME_ID", "EVENTNUM", "PERIOD", "PCTIMESTRING", "EVENTMSGTYPE",
        "EVENTMSGACTIONTYPE", "PLAYER1_ID", "PLAYER1_TEAM_ID", "SCORE",
        "HOMEDESCRIPTION", "VISITORDESCRIPTION"]


def load(season, season_type="RegularSeason"):
    q = f"""SELECT {', '.join(COLS)},
                   lpad(CAST(GAME_ID AS VARCHAR), 10, '0') AS gid
            FROM read_parquet('{PBP}')
            WHERE SEASON = '{season}' AND SEASON_TYPE = '{season_type}'"""
    df = duckdb.connect().execute(q).fetchdf()
    return (df.sort_values(["gid", "PERIOD", "PCTIMESTRING", "EVENTNUM"])
              .reset_index(drop=True))


def team_game(season, season_type="RegularSeason"):
    df = annotate(load(season, season_type))
    p = possession_table(df)
    p["def_team"] = np.where(p["off_is_home"],
                             np.nan, p["home_team"])  # filled below
    # opponent of the possessing team
    teams = p.groupby("gid")["off_team"].unique()
    opp_map = {g: {t: [x for x in ts if x != t][0] for t in ts}
               for g, ts in teams.items() if len(ts) == 2}
    p["def_team"] = [opp_map.get(g, {}).get(t, np.nan)
                     for g, t in zip(p["gid"], p["off_team"])]
    p = p.dropna(subset=["def_team"])

    def agg(sub, tag):
        off = (sub.groupby(["gid", "off_team"])
                  .agg(**{f"poss_{tag}": ("pts", "size"),
                          f"pf_{tag}": ("pts", "sum")}))
        off.index.names = ["gid", "team"]
        dfn = (sub.groupby(["gid", "def_team"])
                  .agg(**{f"pa_{tag}": ("pts", "sum")}))
        dfn.index.names = ["gid", "team"]
        return off.join(dfn, how="outer")

    allp = agg(p, "all")
    comp = agg(p[~p["safe"]], "comp")
    out = allp.join(comp, how="left").reset_index()
    out["season"] = season
    out["season_type"] = season_type

    home = p.groupby("gid")["home_team"].first()
    out["is_home"] = (out["team"] == out["gid"].map(home)).astype(int)
    for tag in ("all", "comp"):
        out[f"oeff_{tag}"] = 100 * out[f"pf_{tag}"] / out[f"poss_{tag}"]
        out[f"deff_{tag}"] = 100 * out[f"pa_{tag}"] / out[f"poss_{tag}"]
    out["gt_share"] = 1 - out["poss_comp"] / out["poss_all"]
    return out


def main():
    seasons = ["2017-18", "2018-19", "2019-20", "2020-21",
               "2021-22", "2022-23", "2023-24", "2024-25"]
    frames = []
    for s in seasons:
        t = team_game(s)
        frames.append(t)
        print(f"{s}: {len(t):,} team-games  "
              f"mean OEFF all {t['oeff_all'].mean():.2f} / comp {t['oeff_comp'].mean():.2f}  "
              f"garbage share {100 * t['gt_share'].mean():.2f}%", flush=True)
    df = pd.concat(frames, ignore_index=True)
    df.to_parquet(OUT, index=False)
    print(f"\nwrote {OUT}  ({len(df):,} rows)")


if __name__ == "__main__":
    main()
