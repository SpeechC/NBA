"""Garbage-time flagging at possession level.

Raw OEFF/DEFF are contaminated by possessions played after the result is decided:
starters sit, the trailing team stops fouling, the leading team milks clock. Those
possessions carry no information about how good a team is, but they are averaged
into every efficiency rating we have used so far.

Flag rule: the **Bill James safe-lead criterion**, adapted to basketball. Take the
lead, subtract 3, add half a point if the leading team has the ball (subtract half
if not); if the result is positive and its square exceeds the seconds remaining,
the lead is safe. It is a published rule with no free parameters to tune, which
matters here — a threshold fitted on this data would be one more researcher
degree of freedom.

"Safe lead" is not identical to "coach has emptied the bench", so the flag is
validated empirically below rather than assumed: if it is picking out garbage
time, flagged possessions should show visibly different pace and efficiency.

Everything is computed on time-ordered events (EVENTNUM is not chronological --
see possessions.py).
"""

import numpy as np
import pandas as pd

from possessions import load_events, possession_team
from stints import event_points

PERIOD_END = 2880


def game_length(period_max):
    return PERIOD_END + np.maximum(period_max - 4, 0) * 300


def annotate(df):
    """Add running margin, seconds remaining, possession id and the safe-lead flag."""
    df = df.reset_index(drop=True).copy()
    df["secs"] = pd.to_numeric(df["PCTIMESTRING"], errors="coerce")
    df["off_team"] = possession_team(df)

    # home team of each game, from which side's description carries the action
    home = df.loc[df["HOMEDESCRIPTION"].notna()].copy()
    home["t"] = pd.to_numeric(home["PLAYER1_TEAM_ID"], errors="coerce")
    home = home[(home["t"] >= 1610612737) & (home["t"] <= 1610612766)]
    ht = home.groupby("gid")["t"].agg(lambda s: s.mode().iloc[0])
    df["home_team"] = df["gid"].map(ht)

    pts, pteam = event_points(df)
    is_home = pteam == df["home_team"].to_numpy()
    df["pts_home"] = np.where(is_home, pts, 0)
    df["pts_away"] = np.where(~is_home & (pts > 0), pts, 0)

    # score BEFORE each event, so a possession is judged on the state it began in
    g = df.groupby("gid", sort=False)
    df["cum_home"] = g["pts_home"].cumsum() - df["pts_home"]
    df["cum_away"] = g["pts_away"].cumsum() - df["pts_away"]
    df["margin"] = df["cum_home"] - df["cum_away"]

    total = df.groupby("gid")["PERIOD"].transform("max").pipe(game_length)
    df["remaining"] = (total - df["secs"]).clip(lower=0)

    # possession id
    prev = g["off_team"].shift()
    period_change = df["PERIOD"] != g["PERIOD"].shift()
    starts = df["off_team"].notna() & (prev.isna() | (df["off_team"] != prev) | period_change)
    df["poss_id"] = starts.cumsum()

    # Bill James safe lead
    lead = df["margin"].abs()
    leader_home = df["margin"] > 0
    leader_has_ball = np.where(leader_home,
                               df["off_team"].to_numpy() == df["home_team"].to_numpy(),
                               df["off_team"].to_numpy() != df["home_team"].to_numpy())
    x = lead - 3 + np.where(leader_has_ball, 0.5, -0.5)
    df["safe"] = (x > 0) & ((x ** 2) > df["remaining"])
    return df


def possession_table(df):
    """One row per possession, with the flag taken from the possession's first event."""
    d = df.dropna(subset=["off_team", "poss_id"]).copy()
    first = d.groupby("poss_id").first()
    pts = d.groupby("poss_id")[["pts_home", "pts_away"]].sum()
    out = first[["gid", "PERIOD", "secs", "remaining", "margin", "safe",
                 "off_team", "home_team"]].join(pts)
    out["off_is_home"] = out["off_team"] == out["home_team"]
    out["pts"] = np.where(out["off_is_home"], out["pts_home"], out["pts_away"])
    return out.reset_index()


def validate(season="2023-24"):
    ev = load_events(season, "RegularSeason")
    ev = ev.merge(
        __import__("stints").load(season)[["gid", "EVENTNUM", "PERIOD",
                                           "HOMEDESCRIPTION", "VISITORDESCRIPTION"]],
        on=["gid", "EVENTNUM", "PERIOD"], how="left")
    df = annotate(ev)
    p = possession_table(df)

    n = len(p)
    gt = p["safe"]
    print(f"season {season}: {n:,} possessions over {p['gid'].nunique():,} games")
    print(f"  flagged garbage time: {gt.sum():,} ({100 * gt.mean():.2f}%)")
    print(f"  games with any garbage time: "
          f"{100 * p.groupby('gid')['safe'].any().mean():.1f}%")
    print()
    print("  points per possession:")
    print(f"    competitive {p.loc[~gt, 'pts'].mean():.4f}   "
          f"garbage {p.loc[gt, 'pts'].mean():.4f}   "
          f"diff {p.loc[gt, 'pts'].mean() - p.loc[~gt, 'pts'].mean():+.4f}")
    print()
    print("  garbage possessions by period:")
    t = p.groupby("PERIOD")["safe"].agg(["size", "sum", "mean"])
    t["pct"] = (100 * t["mean"]).round(2)
    print(t[["size", "sum", "pct"]].to_string())
    print()
    print("  share of a game's possessions flagged (distribution):")
    share = p.groupby("gid")["safe"].mean()
    print("   " + "  ".join(f"p{q}={100 * share.quantile(q / 100):.1f}%"
                            for q in (50, 75, 90, 95, 99)))
    return p


if __name__ == "__main__":
    import sys
    validate(sys.argv[1] if len(sys.argv) > 1 else "2023-24")
