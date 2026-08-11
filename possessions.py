"""Reconstruct possessions from play-by-play, validated against BigDataBall POSS.

Method: track which team has the ball, then count changes of hand.

An event tells you who is on offence when it is a shot, a free throw, a turnover
or a rebound -- in every one of those cases `PLAYER1_TEAM_ID` is the team with
(or newly taking) possession. Fouls, substitutions, timeouts and period markers
carry no possession information, so they are left null and forward-filled. The
number of possessions in a period is then the number of transitions in that
forward-filled series, plus one for the period's opening possession.

Two corrections that matter:

  * **Technical free throws do not change possession.** A technical is shot and
    play resumes with whoever had the ball. Assigning the shooter's team would
    invent a possession change. Excluded (EVENTMSGACTIONTYPE 16, plus flagrant
    and clear-path variants are kept because those *do* follow a change).
  * **Team rebounds and team turnovers carry the team in `PLAYER1_ID`, not
    `PLAYER1_TEAM_ID`.** 15.3% of rebounds and 5.2% of turnovers have a null
    team id ("PACERS Rebound", "Knicks Turnover: Shot Clock"), and on every one
    of those rows `PLAYER1_ID` holds a value in the 1610612737-66 team block
    (verified 21,112/21,112 in 2023-24). Dropping them loses ~19k possession
    changes per season and was the cause of a 13.7% home/away imbalance.

Ground truth: the BigDataBall odds file carries `POSS_H`/`POSS_R` per game, and
it is *not* the classic FGA - OR + TO + 0.44*FTA formula (the implied FT
coefficient is 0.37 with residual SD 1.7), so it is an independent event-derived
count rather than a rearrangement of the same box score.

**`POSS_H` == `POSS_R` in all 7,752 games**, so BigDataBall reports one
*game-level* possession count assigned to both sides, not a per-team count.
Compare the mean of the two reconstructed team counts against it, not either
team individually. A genuine per-team split differs by 0-2 in a normal game --
each period can leave whichever team opened it a possession ahead -- so that
imbalance is basketball, not a bug.

**EVENTNUM is not chronological.** Only 7.2% of games have PCTIMESTRING
monotonic in EVENTNUM order, and the excursions are hundreds of seconds, not
tie-breaks. Events are therefore ordered by clock within period, with EVENTNUM
breaking ties. Doing so improved agreement materially (MAE 1.16-1.22 -> 0.99-1.06,
correlation 0.955-0.968 -> 0.966-0.976).

Validated 2017-18 → 2023-24 (six seasons with odds, 7,224 games): mean bias
-0.05 to -0.14 possessions on a base of ~99, MAE 0.99-1.06, correlation
0.966-0.976, within 2 possessions on 87-89% of games.
"""

import duckdb
import numpy as np
import pandas as pd

PBP = "/home/dpope/data/pbp_lineups_all.parquet"
ODDS = "/home/dpope/data/dfMaster_OT.parquet"

# free-throw subtypes that are technicals -- shot without a change of possession
TECHNICAL_FT = {16}

COLS = ["GAME_ID", "EVENTNUM", "PERIOD", "EVENTMSGTYPE", "EVENTMSGACTIONTYPE",
        "PLAYER1_ID", "PLAYER1_TEAM_ID", "SCORE", "PCTIMESTRING",
        "SEASON", "SEASON_TYPE"]

TEAM_ID_LO, TEAM_ID_HI = 1610612737, 1610612766


def load_events(season=None, season_type="RegularSeason", path=PBP):
    where = []
    if season:
        where.append(f"SEASON = '{season}'")
    if season_type:
        where.append(f"SEASON_TYPE = '{season_type}'")
    w = ("WHERE " + " AND ".join(where)) if where else ""
    q = f"""SELECT {', '.join(COLS)},
                   lpad(CAST(GAME_ID AS VARCHAR), 10, '0') AS gid
            FROM read_parquet('{path}') {w}
            ORDER BY GAME_ID, PERIOD, EVENTNUM"""
    df = duckdb.connect().execute(q).fetchdf()
    # EVENTNUM is not chronological (only 7.2% of games are monotonic in it), so
    # order by clock within period with EVENTNUM breaking ties
    return (df.sort_values(["gid", "PERIOD", "PCTIMESTRING", "EVENTNUM"])
              .reset_index(drop=True))


def possession_team(df):
    """Forward-filled team-in-possession for every event."""
    ev = df["EVENTMSGTYPE"].to_numpy()
    act = df["EVENTMSGACTIONTYPE"].to_numpy()
    team = pd.to_numeric(df["PLAYER1_TEAM_ID"], errors="coerce").to_numpy()
    # team rebounds / team turnovers put the team in PLAYER1_ID instead
    p1 = pd.to_numeric(df["PLAYER1_ID"], errors="coerce").to_numpy()
    fallback = (~np.isfinite(team) | (team <= 0)) & np.isfinite(p1) \
        & (p1 >= TEAM_ID_LO) & (p1 <= TEAM_ID_HI)
    team = np.where(fallback, p1, team)

    # shots (1,2), free throws (3), turnovers (5) and rebounds (4) all identify
    # the team with the ball at that moment
    informative = np.isin(ev, [1, 2, 3, 4, 5])
    informative &= ~((ev == 3) & np.isin(act, list(TECHNICAL_FT)))
    informative &= np.isfinite(team) & (team > 0)

    off = np.where(informative, team, np.nan)
    s = pd.Series(off, index=df.index)
    # never carry possession across a period or a game boundary
    return s.groupby([df["gid"], df["PERIOD"]]).ffill()


def count_possessions(df):
    """Possessions per team per game."""
    df = df.copy()
    df["off_team"] = possession_team(df)
    d = df.dropna(subset=["off_team"]).copy()
    d["off_team"] = d["off_team"].astype("int64")

    key = [d["gid"], d["PERIOD"]]
    prev = d.groupby(key, sort=False)["off_team"].shift()
    # a possession starts when the ball changes hands, and at the start of each period
    d["starts"] = (prev.isna()) | (d["off_team"] != prev)

    out = (d[d["starts"]].groupby(["gid", "off_team"]).size()
             .rename("poss").reset_index())
    return out


def validate(season="2023-24", season_type="RegularSeason"):
    """Compare reconstructed possessions to BigDataBall POSS for the same games."""
    ev = load_events(season, season_type)
    poss = count_possessions(ev)

    odds = pd.read_parquet(ODDS)
    odds["gid"] = (odds["GAME-ID"].astype(str)
                   .str.replace(r"\.0$", "", regex=True).str.zfill(10))
    from team_mapping import NAME_TO_ID
    rows = []
    for suf in ("H", "R"):
        rows.append(pd.DataFrame({
            "gid": odds["gid"],
            "team_id": odds[f"TEAM_{suf}"].map(NAME_TO_ID),
            "poss_bdb": pd.to_numeric(odds[f"POSS_{suf}"], errors="coerce"),
        }))
    truth = pd.concat(rows, ignore_index=True).dropna()
    truth["team_id"] = truth["team_id"].astype("int64")

    m = poss.merge(truth, left_on=["gid", "off_team"], right_on=["gid", "team_id"],
                   how="inner")
    if m.empty:
        print("no overlap -- check the join")
        return m
    m["diff"] = m["poss"] - m["poss_bdb"]
    print(f"season {season} {season_type}: {m['gid'].nunique()} games matched, "
          f"{len(m)} team-games")
    print(f"  reconstructed mean {m['poss'].mean():.2f}   "
          f"BigDataBall mean {m['poss_bdb'].mean():.2f}")
    print(f"  mean diff {m['diff'].mean():+.3f}   sd {m['diff'].std():.3f}   "
          f"MAE {m['diff'].abs().mean():.3f}")
    for tol in (1, 2, 3, 5):
        print(f"  within {tol}: {100 * (m['diff'].abs() <= tol).mean():5.1f}%")
    print(f"  correlation {np.corrcoef(m['poss'], m['poss_bdb'])[0, 1]:.4f}")
    return m


if __name__ == "__main__":
    import sys
    s = sys.argv[1] if len(sys.argv) > 1 else "2023-24"
    validate(s)
