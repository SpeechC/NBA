"""Rest and travel features derived from the schedule in dfMaster.csv.

Rest
----
The file's `TEAM REST DAYS` column is categorical and conflates rest with
schedule density (`B2B`, `3IN4`, `3IN4-B2B`, `4IN5-B2B`, `5IN6-B2B2B`). It is
also *more* accurate than anything derivable from the dates in this file: it was
computed on the full schedule, before overtime games were removed. Deriving rest
from date gaps agrees with it on only 92.9% of team-games, and every disagreement
is in one direction (derived rest too high), because the previous game is missing.

So rest is parsed from the label, and the date gap is used only as a detector:
where derived rest exceeds the label, a game has been removed from the itinerary,
and the team's previous *location* is therefore unknown.

Travel
------
Computed from the sequence of hosts in the schedule. Arena coordinates and time
zones are hardcoded below — that part is external reference data, not from the
dataset; the itinerary itself is. Where the itinerary has a hole (see above),
distance and time-zone shift are set to NaN and flagged; XGBoost handles NaN
natively by learning a default split direction.

These are known before tip-off, so they are legitimate predictors, but note they
are *not* designed features in the paper's sense: they describe the upcoming
game, not a lagged mean of past games.
"""

import numpy as np
import pandas as pd

# lat, lon, standard UTC offset
ARENAS = {
    "Atlanta": (33.757, -84.396, -5), "Boston": (42.366, -71.062, -5),
    "Brooklyn": (40.683, -73.975, -5), "Charlotte": (35.225, -80.839, -5),
    "Chicago": (41.881, -87.674, -6), "Cleveland": (41.496, -81.688, -5),
    "Dallas": (32.790, -96.810, -6), "Denver": (39.749, -105.008, -7),
    "Detroit": (42.341, -83.055, -5), "Golden State": (37.768, -122.388, -8),
    "Houston": (29.751, -95.362, -6), "Indiana": (39.764, -86.156, -5),
    "LA Clippers": (34.043, -118.267, -8), "LA Lakers": (34.043, -118.267, -8),
    "Memphis": (35.138, -90.051, -6), "Miami": (25.781, -80.187, -5),
    "Milwaukee": (43.045, -87.917, -6), "Minnesota": (44.979, -93.276, -6),
    "New Orleans": (29.949, -90.082, -6), "New York": (40.751, -73.994, -5),
    "Oklahoma City": (35.463, -97.515, -6), "Orlando": (28.539, -81.384, -5),
    "Philadelphia": (39.901, -75.172, -5), "Phoenix": (33.446, -112.071, -7),
    "Portland": (45.532, -122.667, -8), "Sacramento": (38.580, -121.500, -8),
    "San Antonio": (29.427, -98.438, -6), "Toronto": (43.643, -79.379, -5),
    "Utah": (40.768, -111.901, -7), "Washington": (38.898, -77.021, -5),
}

REST_MAP = {"B2B": 0, "1": 1, "2": 2, "3+": 3,
            "3IN4": 1, "3IN4-B2B": 0, "4IN5-B2B": 0, "4IN5": 1, "5IN6-B2B2B": 0}


def haversine(a, b):
    if a is None or b is None:
        return np.nan
    lat1, lon1, lat2, lon2 = map(np.radians, [a[0], a[1], b[0], b[1]])
    h = (np.sin((lat2 - lat1) / 2) ** 2
         + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2)
    return float(2 * 6371 * np.arcsin(np.sqrt(h)))


def add_rest_travel(panel, raw):
    """panel: team-game rows (season, team, date, game_id, home). raw: source rows."""
    host = raw.set_index("GAME-ID")["TEAM_H"]
    lab_h = raw.set_index("GAME-ID")["TEAM\nREST DAYS_H"]
    lab_r = raw.set_index("GAME-ID")["TEAM\nREST DAYS_R"]

    p = panel.copy()
    p["host"] = p["game_id"].map(host)
    p["restlab"] = np.where(p["home"] == 1,
                            p["game_id"].map(lab_h), p["game_id"].map(lab_r))

    p = p.sort_values(["season", "team", "date"]).reset_index(drop=True)
    grp = p.groupby(["season", "team"], sort=False)

    p["rest_days"] = p["restlab"].map(REST_MAP).astype(float)
    p["is_b2b"] = (p["rest_days"] == 0).astype(float)
    p["is_3in4"] = p["restlab"].isin(["3IN4", "3IN4-B2B"]).astype(float)
    p["is_4in5"] = p["restlab"].isin(["4IN5", "4IN5-B2B", "5IN6-B2B2B"]).astype(float)

    # itinerary hole detector: derived rest above the label means a game was removed
    gap = grp["date"].diff().dt.days
    p["rest_calc"] = gap - 1
    p["itinerary_gap"] = ((p["rest_calc"] > p["rest_days"])
                          & p["rest_days"].notna() & p["rest_calc"].notna()).astype(float)

    prev_host = grp["host"].shift(1)
    coords = p["host"].map(ARENAS)
    prev_coords = prev_host.map(ARENAS)
    dist, tz = [], []
    for c, pc, hole, first in zip(coords, prev_coords, p["itinerary_gap"], prev_host.isna()):
        if first or hole == 1 or not isinstance(c, tuple) or not isinstance(pc, tuple):
            dist.append(np.nan)
            tz.append(np.nan)
        else:
            dist.append(haversine(pc, c))
            tz.append(c[2] - pc[2])  # positive = travelled east (lost hours)
    p["travel_km"] = dist
    p["tz_shift"] = tz

    # --- home/road streaks -------------------------------------------------
    # a "run" is a maximal block of consecutive games with the same venue type
    key = [p["season"], p["team"]]
    run_start = p["home"].ne(p.groupby(key, sort=False)["home"].shift()).fillna(True)
    run_id = run_start.groupby(key).cumsum()
    streak = p.groupby([p["season"], p["team"], run_id], sort=False).cumcount() + 1
    p["road_trip_game"] = np.where(p["home"] == 0, streak, 0).astype(float)
    p["home_stand_game"] = np.where(p["home"] == 1, streak, 0).astype(float)
    # signed: positive deep into a home stand, negative deep into a road trip
    p["streak_signed"] = np.where(p["home"] == 1, streak, -streak).astype(float)

    # days since the team last played at home (0 when at home); how long they
    # have been living out of a suitcase, which trip length alone misses
    last_home = p["date"].where(p["home"] == 1)
    last_home = last_home.groupby(key, sort=False).ffill()
    p["days_away"] = np.where(p["home"] == 1, 0.0,
                              (p["date"] - last_home).dt.days.astype(float))
    # first home game after a road trip of 3+
    prev_trip = p.groupby(key, sort=False)["road_trip_game"].shift().fillna(0)
    p["is_return_home"] = ((p["home"] == 1) & (prev_trip >= 3)).astype(float)

    # --- schedule density --------------------------------------------------
    # accurate only on the complete file; on the overtime-free file these
    # undercount, which is why the categorical 3IN4/4IN5 flags are kept too
    dens = []
    for _, sub in p.groupby(key, sort=False):
        dt = sub["date"].values.astype("datetime64[D]").astype(int)
        d7 = [(np.sum((dt >= t - 7) & (dt < t))) for t in dt]
        d14 = [(np.sum((dt >= t - 14) & (dt < t))) for t in dt]
        dens.append(pd.DataFrame({"games_last_7": d7, "games_last_14": d14},
                                 index=sub.index))
    p = p.join(pd.concat(dens).astype(float))

    # kilometres travelled in the trailing 7 days
    cum = []
    for _, sub in p.groupby(key, sort=False):
        dt = sub["date"].values.astype("datetime64[D]").astype(int)
        km = sub["travel_km"].fillna(0).values
        cum.append(pd.Series([km[(dt >= t - 7) & (dt <= t)].sum() for t in dt],
                             index=sub.index))
    p["travel_km_7d"] = pd.concat(cum).astype(float)

    return p


# tested previously
FEATURES = ["rest_days", "is_b2b", "is_3in4", "is_4in5",
            "travel_km", "tz_shift", "road_trip_game"]

# home stands, trip fatigue and density -- not previously tested
STREAK_FEATURES = ["home_stand_game", "streak_signed", "days_away",
                   "is_return_home", "games_last_7", "games_last_14", "travel_km_7d"]
