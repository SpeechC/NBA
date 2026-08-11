"""Stint extraction: contiguous 5-on-5 lineup blocks with possessions and points.

A stint is a maximal run of events over which all ten on-court players stay the
same. It is the unit that player-impact models (RAPM and relatives) consume, and
the unit garbage-time flagging operates on.

`PLAYER1`-`PLAYER10` arrive as ten ids in arbitrary order, not split by team, so
team membership is recovered per game from the `PLAYER{1,2,3}_ID` /
`PLAYER{1,2,3}_TEAM_ID` pairs that appear throughout that game's events. Doing it
per game rather than per season is deliberate — players get traded mid-season.

Points are computed from events rather than parsed from the `SCORE` string:
a made field goal is worth 3 if its description contains "3PT" else 2, and a made
free throw (`SCORE IS NOT NULL` on an `EVENTMSGTYPE=3` row) is worth 1. That
avoids depending on the visitor-home ordering convention inside `SCORE`.

Validation targets, both independent of any modelling choice:
  * stint seconds must sum to 2880 per game plus 300 per overtime period
  * stint points must sum to the final score in the odds file
"""

import duckdb
import numpy as np
import pandas as pd

PBP = "/home/dpope/data/pbp_lineups_all.parquet"
TEAM_LO, TEAM_HI = 1610612737, 1610612766
PLAYER_COLS = [f"PLAYER{i}" for i in range(1, 11)]

COLS = ["GAME_ID", "EVENTNUM", "PERIOD", "PCTIMESTRING", "EVENTMSGTYPE",
        "EVENTMSGACTIONTYPE", "PLAYER1_ID", "PLAYER1_TEAM_ID",
        "PLAYER2_ID", "PLAYER2_TEAM_ID", "PLAYER3_ID", "PLAYER3_TEAM_ID",
        "SCORE", "HOMEDESCRIPTION", "VISITORDESCRIPTION", "NEUTRALDESCRIPTION"]


def load(season, season_type="RegularSeason", path=PBP):
    q = f"""SELECT {', '.join(COLS + PLAYER_COLS)},
                   lpad(CAST(GAME_ID AS VARCHAR), 10, '0') AS gid
            FROM read_parquet('{path}')
            WHERE SEASON = '{season}' AND SEASON_TYPE = '{season_type}'
            ORDER BY GAME_ID, PERIOD, EVENTNUM"""
    df = duckdb.connect().execute(q).fetchdf()
    # EVENTNUM does not sort events chronologically -- only 7.2% of games have
    # PCTIMESTRING monotonic in EVENTNUM order, and the excursions are large
    # (hundreds of seconds), not tie-breaking. Ordering by time within period,
    # with EVENTNUM breaking ties, is required for durations to telescope.
    return (df.sort_values(["gid", "PERIOD", "PCTIMESTRING", "EVENTNUM"])
              .reset_index(drop=True))


def clock_seconds(df):
    """Seconds elapsed since tip.

    NOTE: contrary to the schema doc's description of `PCTIMESTRING` as an
    "MM:SS string" of clock *remaining*, the build already stores it as an
    INTEGER of seconds *elapsed since tip*: period 1 spans 0-720, period 4 ends
    at 2880, each overtime adds 300. So it is used directly. Parsing it as
    MM:SS silently produces times in the hundreds of thousands of seconds.
    """
    return pd.to_numeric(df["PCTIMESTRING"], errors="coerce").to_numpy()


def player_team_map(df):
    """(gid, player_id) -> team_id, built from this game's own event rows."""
    frames = []
    for i in (1, 2, 3):
        f = df[["gid", f"PLAYER{i}_ID", f"PLAYER{i}_TEAM_ID"]].copy()
        f.columns = ["gid", "pid", "tid"]
        frames.append(f)
    m = pd.concat(frames, ignore_index=True)
    m["pid"] = pd.to_numeric(m["pid"], errors="coerce")
    m["tid"] = pd.to_numeric(m["tid"], errors="coerce")
    m = m[(m["tid"] >= TEAM_LO) & (m["tid"] <= TEAM_HI) & (m["pid"] > 0)]
    # a player id in the team block is a team rebound row, not a player
    m = m[(m["pid"] < TEAM_LO) | (m["pid"] > TEAM_HI)]
    return m.drop_duplicates(subset=["gid", "pid"]).set_index(["gid", "pid"])["tid"]


def home_team(df):
    """team_id whose actions appear in HOMEDESCRIPTION."""
    d = df[df["HOMEDESCRIPTION"].notna()].copy()
    d["t"] = pd.to_numeric(d["PLAYER1_TEAM_ID"], errors="coerce")
    d = d[(d["t"] >= TEAM_LO) & (d["t"] <= TEAM_HI)]
    return d.groupby("gid")["t"].agg(lambda s: s.mode().iloc[0])


def event_points(df):
    """Points scored on each event, and the team that scored them."""
    ev = df["EVENTMSGTYPE"].to_numpy()
    desc = (df["HOMEDESCRIPTION"].fillna("") + " "
            + df["VISITORDESCRIPTION"].fillna("")).str.upper()
    is3 = desc.str.contains("3PT").to_numpy()
    made_ft = (ev == 3) & df["SCORE"].notna().to_numpy()
    pts = np.where(ev == 1, np.where(is3, 3, 2), 0) + np.where(made_ft, 1, 0)
    team = pd.to_numeric(df["PLAYER1_TEAM_ID"], errors="coerce").to_numpy()
    return pts, team


def build_stints(df):
    from possessions import possession_team

    df = df.reset_index(drop=True).copy()
    df["secs"] = clock_seconds(df)
    df["off_team"] = possession_team(df)

    # lineup key: the ten ids, order-independent
    lu = df[PLAYER_COLS].to_numpy()
    lu_sorted = np.sort(lu, axis=1)
    key = pd.Series([hash(tuple(r)) for r in lu_sorted], index=df.index)

    changed = (key != key.shift()) | (df["gid"] != df["gid"].shift()) \
        | (df["PERIOD"] != df["PERIOD"].shift())
    df["stint"] = changed.cumsum()

    pts, pteam = event_points(df)
    ht = home_team(df)
    df["home_team"] = df["gid"].map(ht)
    df["pts_home"] = np.where(pteam == df["home_team"].to_numpy(), pts, 0)
    df["pts_away"] = np.where((pteam != df["home_team"].to_numpy())
                              & (pts > 0), pts, 0)

    # possession starts, attributed to the team taking the ball
    d = df.dropna(subset=["off_team"]).copy()
    prev = d.groupby(["gid", "PERIOD"], sort=False)["off_team"].shift()
    d["start"] = prev.isna() | (d["off_team"] != prev)
    d["poss_home"] = (d["start"] & (d["off_team"] == d["home_team"])).astype(int)
    d["poss_away"] = (d["start"] & (d["off_team"] != d["home_team"])).astype(int)
    poss = d.groupby("stint")[["poss_home", "poss_away"]].sum()

    # Duration is accumulated at EVENT level, not from stint start/end.
    # During rapid substitutions several stints share a timestamp, so
    # stint-level start/end intervals overlap on ~3.4% of stints and a
    # clipped difference breaks the telescoping sum (~+90s per game). Summing
    # per-event gaps telescopes exactly to (last event - first event).
    df["dt"] = df.groupby("gid", sort=False)["secs"].shift(-1) - df["secs"]
    df["dt"] = df["dt"].fillna(0.0)

    agg = df.groupby("stint").agg(
        gid=("gid", "first"), period=("PERIOD", "first"),
        home_team=("home_team", "first"),
        start_secs=("secs", "min"), end_secs=("secs", "max"),
        seconds=("dt", "sum"),
        pts_home=("pts_home", "sum"), pts_away=("pts_away", "sum"),
        n_events=("EVENTNUM", "size"))
    agg = agg.join(poss).fillna({"poss_home": 0, "poss_away": 0})

    # split the ten on-court ids into home five / away five
    ptm = player_team_map(df)
    first_rows = df.groupby("stint").first()
    lineups = []
    for stint, row in first_rows.iterrows():
        g = row["gid"]
        ids = [row[c] for c in PLAYER_COLS]
        teams = [ptm.get((g, i), np.nan) for i in ids]
        h = sorted([i for i, t in zip(ids, teams) if t == row["home_team"]])
        a = sorted([i for i, t in zip(ids, teams)
                    if pd.notna(t) and t != row["home_team"]])
        lineups.append((stint, tuple(h), tuple(a), len(h), len(a)))
    lu_df = pd.DataFrame(lineups, columns=["stint", "home_lineup", "away_lineup",
                                           "n_home", "n_away"]).set_index("stint")
    return agg.join(lu_df).reset_index()


def validate(season="2023-24"):
    df = load(season)
    st = build_stints(df)
    print(f"season {season}: {len(st):,} stints over {st['gid'].nunique():,} games "
          f"({len(st) / st['gid'].nunique():.1f} per game)")

    # 1. time must reconcile
    per_game = st.groupby("gid").agg(secs=("seconds", "sum"),
                                     maxp=("period", "max"))
    expect = 2880 + np.maximum(per_game["maxp"] - 4, 0) * 300
    dt = per_game["secs"] - expect
    print(f"  time: exact on {100 * (dt.abs() < 1).mean():.1f}% of games, "
          f"within 5s on {100 * (dt.abs() <= 5).mean():.1f}%  (mean err {dt.mean():+.2f}s)")

    # 2. lineups must split 5/5
    ok = (st["n_home"] == 5) & (st["n_away"] == 5)
    print(f"  lineups splitting exactly 5/5: {100 * ok.mean():.2f}%")

    # 3. points must reconcile to the final score
    odds = pd.read_parquet("/home/dpope/data/dfMaster_OT.parquet")
    odds["gid"] = (odds["GAME-ID"].astype(str)
                   .str.replace(r"\.0$", "", regex=True).str.zfill(10))
    truth = odds.set_index("gid")[["PTS_H", "PTS_R"]]
    pg = st.groupby("gid")[["pts_home", "pts_away"]].sum().join(truth, how="inner")
    eh = pg["pts_home"] - pd.to_numeric(pg["PTS_H"], errors="coerce")
    ea = pg["pts_away"] - pd.to_numeric(pg["PTS_R"], errors="coerce")
    print(f"  points: home exact on {100 * (eh == 0).mean():.1f}%, "
          f"away exact on {100 * (ea == 0).mean():.1f}%  "
          f"(n={len(pg)}, mean err {eh.mean():+.2f}/{ea.mean():+.2f})")
    return st


if __name__ == "__main__":
    import sys
    validate(sys.argv[1] if len(sys.argv) > 1 else "2023-24")
