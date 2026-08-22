"""Bonus (penalty) state extraction from the raw play-by-play.

NBA rule: a team shoots bonus free throws once its OPPONENT has committed 5
team fouls in the quarter. Technical fouls do not count toward the team foul
total; personal fouls, including offensive fouls and loose-ball fouls, do.

For each (game, quarter, committing team) we find the clock time of the 5th
counted team foul. That instant is when the OPPONENT enters the bonus, and the
remaining quarter time is the opponent's bonus exposure.

Then every foul is flagged as pre-bonus or in-bonus from the perspective of the
committing team's running count, and free throws are attributed to the foul
that produced them (same game, period and clock, nearest preceding EVENTNUM).

Also flags POSSESSION-PRESERVING free-throw events, where the offended team
keeps the ball: technicals, flagrants, defensive three seconds, clear-path and
transition take fouls.
"""
import os
import warnings

import duckdb
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

PBP = "/home/dpope/data/pbp_lineups_all.parquet"
OUT = "bonus_game_team.csv"

# EVENTMSGACTIONTYPE groups, consistent with foul_types.py
OFFENSIVE = (4, 26)
DEF_SHOOT = (2, 29)
# possession-preserving: technical, flagrant, def 3 sec, clear path, take foul
PRESERVING = (11, 12, 16, 18, 19, 25, 30, 9, 17, 28)

SQL = f"""
SELECT lpad(CAST(GAME_ID AS VARCHAR),10,'0')          AS gid,
       PERIOD                                         AS q,
       EVENTNUM, EVENTMSGTYPE AS msg, EVENTMSGACTIONTYPE AS act,
       PCTIMESTRING                                   AS clock,
       PLAYER1_TEAM_ABBREVIATION                      AS team,
       upper(coalesce(HOMEDESCRIPTION,'') || ' ' ||
             coalesce(NEUTRALDESCRIPTION,'') || ' ' ||
             coalesce(VISITORDESCRIPTION,''))         AS descr
FROM read_parquet('{PBP}')
WHERE SEASON_TYPE = 'RegularSeason' AND PERIOD <= 4
  AND EVENTMSGTYPE IN (3, 6)
ORDER BY gid, EVENTNUM
"""


QLEN = 720.0   # seconds in a regulation quarter


def secs(s, q):
    """In THIS parquet build PCTIMESTRING is seconds ELAPSED in the GAME
    (integer, increasing across quarters), not a MM:SS clock. Return seconds
    REMAINING IN THE QUARTER, so larger = earlier in the quarter."""
    v = pd.to_numeric(s, errors="coerce")
    return (QLEN * pd.to_numeric(q, errors="coerce") - v).clip(0, QLEN)


def build(force=False):
    if os.path.exists(OUT) and not force:
        return pd.read_csv(OUT, dtype={"gid": str})
    e = duckdb.connect().execute(SQL).fetchdf()
    e["gid"] = e["gid"].astype(str)
    e["sec_left"] = secs(e["clock"], e["q"])
    e["tech"] = e["descr"].str.contains("TECHNICAL", regex=False)

    f = e[(e["msg"] == 6) & e["team"].notna()].copy()
    f["counts"] = ~f["tech"]                       # team-foul eligible
    f = f.sort_values(["gid", "q", "team", "EVENTNUM"])
    f["team_foul_no"] = f.groupby(["gid", "q", "team"])["counts"].cumsum()
    # the committing team's foul is IN BONUS if it is their 6th or later
    f["in_bonus"] = f["counts"] & (f["team_foul_no"] >= 6)
    f["is_off"] = f["act"].isin(OFFENSIVE)
    f["is_shoot"] = f["act"].isin(DEF_SHOOT)
    f["nonshoot_def"] = f["counts"] & ~f["is_off"] & ~f["is_shoot"]
    f["preserving"] = f["act"].isin(PRESERVING) | f["tech"]

    # attribute free throws to the nearest preceding foul in the same
    # game / period / clock
    ft = e[e["msg"] == 3].copy()
    ft["made"] = ~ft["descr"].str.contains("MISS", regex=False)
    ft = ft.sort_values("EVENTNUM", kind="stable")
    fs = f.sort_values("EVENTNUM", kind="stable")
    j = pd.merge_asof(
        ft[["gid", "q", "clock", "EVENTNUM", "made"]],
        fs[["gid", "q", "clock", "EVENTNUM", "team", "in_bonus",
            "nonshoot_def", "preserving"]].rename(columns={"EVENTNUM": "fn"}),
        left_on="EVENTNUM", right_on="fn", by=["gid", "q", "clock"],
        direction="backward")
    j = j.dropna(subset=["fn"])
    fta = j.groupby(["gid", "q", "team"], as_index=False).agg(
        fta=("EVENTNUM", "size"), ftm=("made", "sum"))
    bon = j[j["in_bonus"] & j["nonshoot_def"]].groupby(
        ["gid", "q", "team"], as_index=False).agg(
        bonus_fta=("EVENTNUM", "size"), bonus_ftm=("made", "sum"))
    pres = j[j["preserving"]].groupby(["gid", "q", "team"],
                                      as_index=False).agg(
        pres_fta=("EVENTNUM", "size"), pres_ftm=("made", "sum"))

    # bonus entry: clock at the committing team's 5th counted foul
    fifth = f[f["counts"] & (f["team_foul_no"] == 5)].groupby(
        ["gid", "q", "team"], as_index=False)["sec_left"].max()
    fifth = fifth.rename(columns={"sec_left": "entry_sec_left"})

    agg = f.groupby(["gid", "q", "team"], as_index=False).agg(
        fouls=("counts", "sum"),
        fouls_in_bonus=("in_bonus", "sum"),
        nonshoot_in_bonus=("nonshoot_def", lambda s: np.nan))
    ns = f[f["in_bonus"] & f["nonshoot_def"]].groupby(
        ["gid", "q", "team"], as_index=False).size().rename(
        columns={"size": "nonshoot_in_bonus"})
    agg = agg.drop(columns=["nonshoot_in_bonus"]).merge(
        ns, on=["gid", "q", "team"], how="left")
    for t in (fifth, fta, bon, pres):
        agg = agg.merge(t, on=["gid", "q", "team"], how="left")
    agg["entry_sec_left"] = agg["entry_sec_left"].fillna(0.0)
    agg["reached_bonus"] = agg["fouls"] >= 5
    # opponent's bonus exposure in this quarter, in minutes
    agg["opp_bonus_min"] = np.where(agg["reached_bonus"],
                                    agg["entry_sec_left"] / 60.0, 0.0)
    for c in ("nonshoot_in_bonus", "bonus_fta", "bonus_ftm", "fta", "ftm",
              "pres_fta", "pres_ftm"):
        agg[c] = agg[c].fillna(0.0)
    agg.to_csv(OUT, index=False)
    return agg


def main():
    a = build(force=True)
    print(f"  {len(a):,} game-quarter-team rows, {a['gid'].nunique():,} games")
    print(f"\n  quarters in which the committing team reached 5 team fouls: "
          f"{100*a['reached_bonus'].mean():.2f}%")
    r = a[a["reached_bonus"]]
    print(f"  clock remaining at the 5th foul (= opponent bonus exposure):")
    print(f"    mean {r['entry_sec_left'].mean():.1f}s "
          f"({r['entry_sec_left'].mean()/60:.2f} min)   "
          f"median {r['entry_sec_left'].median():.0f}s")
    print(f"\n  by quarter")
    t = a.groupby("q").agg(n=("gid", "size"),
                           reached=("reached_bonus", "mean"),
                           entry=("entry_sec_left", "mean"),
                           opp_min=("opp_bonus_min", "mean"),
                           nsb=("nonshoot_in_bonus", "mean"),
                           bfta=("bonus_fta", "mean"),
                           bftm=("bonus_ftm", "mean"))
    t["reached %"] = (100 * t["reached"]).round(2)
    t["entry s"] = t["entry"].round(1)
    print(t[["n", "reached %", "entry s", "opp_min", "nsb", "bfta",
             "bftm"]].round(3).to_string())

    print(f"\n  bonus-state non-shooting fouls per game-quarter-team "
          f"{a['nonshoot_in_bonus'].mean():.3f}")
    print(f"  FTA from bonus non-shooting fouls {a['bonus_fta'].mean():.3f}"
          f"   FTM {a['bonus_ftm'].mean():.3f}")
    print(f"  all FTA attributed to fouls {a['fta'].mean():.3f}")
    print(f"  share of FTA that is bonus non-shooting: "
          f"{100*a['bonus_fta'].sum()/a['fta'].sum():.2f}%")
    print(f"\n  POSSESSION-PRESERVING FT events (technical, flagrant, "
          f"def-3s, clear path, take):")
    print(f"    FTA {a['pres_fta'].mean():.4f} per game-quarter-team   "
          f"share of all FTA {100*a['pres_fta'].sum()/a['fta'].sum():.2f}%")
    print(f"    points {2*a['pres_ftm'].sum()/a['gid'].nunique()*0:.0f}"
          f"   per game {a.groupby('gid')['pres_ftm'].sum().mean():.3f} FTM")


if __name__ == "__main__":
    main()
