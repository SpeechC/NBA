"""Build the stint table for every season and write it to parquet.

Same logic as stints.build_stints, but the home/away lineup split is vectorised
(the per-stint Python loop was the bottleneck: ~67k iterations per season).

Output: /home/dpope/data/stints_all.parquet
  one row per stint, with home/away five, possessions, points, duration.
"""

import numpy as np
import pandas as pd

from possessions import possession_team
from stints import (PLAYER_COLS, TEAM_HI, TEAM_LO, clock_seconds, event_points,
                    home_team, load, player_team_map)

OUT = "/home/dpope/data/stints_all.parquet"
SEASONS = ["2017-18", "2018-19", "2019-20", "2020-21",
           "2021-22", "2022-23", "2023-24", "2024-25"]


def build(df):
    df = df.reset_index(drop=True).copy()
    df["secs"] = clock_seconds(df)
    df["off_team"] = possession_team(df)

    lu_sorted = np.sort(df[PLAYER_COLS].to_numpy(), axis=1)
    key = pd.Series([hash(tuple(r)) for r in lu_sorted], index=df.index)
    changed = (key != key.shift()) | (df["gid"] != df["gid"].shift()) \
        | (df["PERIOD"] != df["PERIOD"].shift())
    df["stint"] = changed.cumsum()

    pts, pteam = event_points(df)
    ht = home_team(df)
    df["home_team"] = df["gid"].map(ht)
    is_home = pteam == df["home_team"].to_numpy()
    df["pts_home"] = np.where(is_home, pts, 0)
    df["pts_away"] = np.where(~is_home & (pts > 0), pts, 0)

    d = df.dropna(subset=["off_team"]).copy()
    prev = d.groupby(["gid", "PERIOD"], sort=False)["off_team"].shift()
    d["start"] = prev.isna() | (d["off_team"] != prev)
    d["poss_home"] = (d["start"] & (d["off_team"] == d["home_team"])).astype(int)
    d["poss_away"] = (d["start"] & (d["off_team"] != d["home_team"])).astype(int)
    poss = d.groupby("stint")[["poss_home", "poss_away"]].sum()

    df["dt"] = df.groupby("gid", sort=False)["secs"].shift(-1) - df["secs"]
    df["dt"] = df["dt"].fillna(0.0)

    agg = df.groupby("stint").agg(
        gid=("gid", "first"), period=("PERIOD", "first"),
        home_team=("home_team", "first"), start_secs=("secs", "min"),
        seconds=("dt", "sum"), pts_home=("pts_home", "sum"),
        pts_away=("pts_away", "sum")).join(poss).fillna(
            {"poss_home": 0, "poss_away": 0})

    # --- vectorised lineup split -----------------------------------------
    ptm = player_team_map(df)                       # (gid, pid) -> team
    lookup = {f"{g}_{p}": t for (g, p), t in ptm.items()}
    first = df.groupby("stint").first()
    teams = np.empty((len(first), 10), dtype="float64")
    for i, c in enumerate(PLAYER_COLS):
        k = first["gid"].astype(str) + "_" + first[c].astype("int64").astype(str)
        teams[:, i] = k.map(lookup).to_numpy(dtype="float64")
    ids = first[PLAYER_COLS].to_numpy()
    ht_arr = first["home_team"].to_numpy()[:, None]
    is_h = teams == ht_arr
    is_a = (~is_h) & np.isfinite(teams)

    home_l, away_l, nh, na = [], [], [], []
    for r in range(len(first)):
        h = np.sort(ids[r][is_h[r]])
        a = np.sort(ids[r][is_a[r]])
        home_l.append(tuple(h.tolist()))
        away_l.append(tuple(a.tolist()))
        nh.append(len(h))
        na.append(len(a))
    agg["home_lineup"] = home_l
    agg["away_lineup"] = away_l
    agg["n_home"] = nh
    agg["n_away"] = na
    return agg.reset_index()


def main():
    frames = []
    for s in SEASONS:
        df = load(s, "RegularSeason")
        st = build(df)
        st["season"] = s
        ok = ((st["n_home"] == 5) & (st["n_away"] == 5)).mean()
        frames.append(st)
        print(f"{s}: {len(st):,} stints, {st['gid'].nunique():,} games, "
              f"5/5 split {100 * ok:.2f}%, "
              f"poss {st['poss_home'].sum() + st['poss_away'].sum():,.0f}", flush=True)
    out = pd.concat(frames, ignore_index=True)
    out["home_lineup"] = out["home_lineup"].astype(str)
    out["away_lineup"] = out["away_lineup"].astype(str)
    out.to_parquet(OUT, index=False)
    print(f"\nwrote {OUT}  ({len(out):,} stints)")


if __name__ == "__main__":
    main()
