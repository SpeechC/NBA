"""Value of a non-shooting defensive foul in each rules state.

    V_prebonus = E[points the offense scores from the ensuing side-out
                   inbound until THAT SAME possession ends]
    V_bonus    = E[points generated once the same foul instead sends the
                   offense to the line in the penalty]
    dV         = V_bonus - V_prebonus

The pre-bonus counterfactual is measured EMPIRICALLY -- points actually scored
in the remainder of that possession -- rather than assumed from league PPP.
That matters because the shot clock after a defensive foul either stays or
resets to 14 depending on circumstance; measuring the realised remainder
absorbs whichever rule applied.

Restricted to fouls whose free-throw consequence depends PURELY on bonus
state: EVENTMSGACTIONTYPE 1 (personal) and 27 (personal block). Excluded are
clear-path (9), defensive three seconds (17), away-from-play (6) and take
fouls (28), which award free throws regardless of the penalty, plus all
shooting and offensive fouls.
"""
import warnings

import numpy as np
import pandas as pd
import duckdb

warnings.filterwarnings("ignore")

PBP = "/home/dpope/data/pbp_lineups_all.parquet"
DEV_MAX = 2023
QLEN = 720.0
BONUS_SUBJECT = (1, 27)

SQL = f"""
WITH ev AS (
  SELECT lpad(CAST(GAME_ID AS VARCHAR),10,'0')            AS gid,
         PERIOD AS q, STARTTIME, ENDTIME, EVENTNUM,
         EVENTMSGTYPE AS msg, EVENTMSGACTIONTYPE AS act,
         PLAYER1_TEAM_ABBREVIATION                        AS team,
         upper(coalesce(HOMEDESCRIPTION,'') || ' ' ||
               coalesce(VISITORDESCRIPTION,''))           AS descr,
         TRY_CAST(split_part(SCORE,' - ',1) AS INTEGER)
       + TRY_CAST(split_part(SCORE,' - ',2) AS INTEGER)   AS tot
  FROM read_parquet('{PBP}')
  WHERE SEASON_TYPE = 'RegularSeason' AND PERIOD <= 4
    AND STARTTIME IS NOT NULL AND ENDTIME IS NOT NULL
),
ff AS (
  SELECT *, last_value(tot IGNORE NULLS) OVER (
      PARTITION BY gid ORDER BY EVENTNUM
      ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)   AS tot_ff
  FROM ev
),
p AS (
  SELECT *, COALESCE(tot_ff - lag(tot_ff) OVER (
      PARTITION BY gid ORDER BY EVENTNUM), 0)             AS pts
  FROM ff
)
SELECT gid, q, STARTTIME, ENDTIME, EVENTNUM, msg, act, team, descr, pts,
       sum(pts) OVER (PARTITION BY gid, q, STARTTIME, ENDTIME
                      ORDER BY EVENTNUM
                      ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
                                                          AS cum_pts,
       sum(pts) OVER (PARTITION BY gid, q, STARTTIME, ENDTIME)
                                                          AS poss_pts
FROM p
"""


def main():
    e = duckdb.connect().execute(SQL).fetchdf()
    e["gid"] = e["gid"].astype(str)
    print(f"  {len(e):,} event rows")

    f = e[(e["msg"] == 6) & e["team"].notna()].copy()
    f["counts"] = ~f["descr"].str.contains("TECHNICAL", regex=False)
    f = f.sort_values(["gid", "q", "team", "EVENTNUM"])
    f["team_foul_no"] = f.groupby(["gid", "q", "team"])["counts"].cumsum()
    f["in_bonus"] = f["counts"] & (f["team_foul_no"] >= 6)
    # points scored in the REMAINDER of this possession, after the foul
    f["pts_after"] = f["poss_pts"] - f["cum_pts"]

    sub = f[f["act"].isin(BONUS_SUBJECT) & f["counts"]].copy()
    yr = pd.to_datetime(
        e.groupby("gid")["EVENTNUM"].size().index.to_series().map(
            lambda x: x), errors="coerce")
    # season from the master, to respect the development boundary
    from prepare_data import CSV, season_label
    raw = pd.read_csv(CSV, low_memory=False)
    raw["lbl"] = season_label(raw).astype(str)
    raw = raw[raw["lbl"].str.contains("Regular Season", na=False)]
    ymap = pd.Series(
        raw["lbl"].str.extract(r"(\d{4})")[0].astype(int).values,
        index=raw["GAME-ID"].astype(str).str.strip().str.zfill(10))
    sub["yr"] = sub["gid"].map(ymap)
    dev = sub[sub["yr"] <= DEV_MAX]
    print(f"  bonus-subject non-shooting defensive fouls: {len(sub):,} "
          f"({len(dev):,} on development)")

    pre = dev[~dev["in_bonus"]]
    bon = dev[dev["in_bonus"]]
    v_pre = pre["pts_after"].mean()
    v_bon = bon["pts_after"].mean()
    dv = v_bon - v_pre
    print("\n" + "=" * 88)
    print("VALUE OF A NON-SHOOTING DEFENSIVE FOUL BY RULES STATE (development)")
    print("=" * 88)
    print(f"  pre-bonus  n={len(pre):,}   points in remainder of possession "
          f"{v_pre:.4f}")
    print(f"  in bonus   n={len(bon):,}   points generated "
          f"{v_bon:.4f}")
    print(f"  incremental value of bonus conversion   dV = {dv:+.4f}")
    print(f"\n  sanity: bonus value should sit near 2 x league FT% "
          f"(~1.54) plus rebound continuation")

    # CrewShock-induced increase in bonus fouls, from bonus_analysis
    d_bonus_fouls_per_team = 0.1631
    per_game = 2 * d_bonus_fouls_per_team
    inc = per_game * dv
    c_true = 0.9231          # pooled c_true on the actual total, per unit
    print("\n" + "=" * 88)
    print("CREWSHOCK BONUS-CONVERSION ACCOUNTING")
    print("=" * 88)
    print(f"  Expected points after ordinary non-shooting side-out foul:"
          f"   {v_pre:8.4f}")
    print(f"  Expected points from bonus non-shooting foul:              "
          f"   {v_bon:8.4f}")
    print(f"  Incremental value of bonus conversion:                     "
          f"   {dv:+8.4f}")
    print(f"  CrewShock additional bonus fouls per unit, per team:       "
          f"   {d_bonus_fouls_per_team:8.4f}")
    print(f"  ... per game (both teams):                                 "
          f"   {per_game:8.4f}")
    print(f"  Expected incremental bonus points per unit CrewShock:      "
          f"   {inc:8.4f}")
    print(f"  Observed total-point effect per unit CrewShock:             "
          f"   {c_true:8.4f}")
    print(f"  Share of CrewShock scoring effect explained by bonus"
          f" conversion: {100*inc/c_true:6.1f}%")

    print("\n" + "=" * 88)
    print("THE TWO CHANNELS, SIDE BY SIDE")
    print("=" * 88)
    sh = dev[dev["act"].isin((2, 29))] if len(dev) else dev
    allf = e[(e["msg"] == 6)].copy()
    print(f"  bonus non-shooting foul: offense was NOT shooting, so the two")
    print(f"    free throws are added to a possession that would otherwise")
    print(f"    have continued and produced {v_pre:.3f} points on average.")
    print(f"    net addition {dv:+.3f}, replacement offset "
          f"{100*v_pre/v_bon:.0f}%")
    lam = 0.5489
    print(f"  shooting foul: replaces a field-goal attempt outright;")
    print(f"    previously estimated replacement fraction lambda = {lam:.4f}")
    print(f"\n  -> the bonus channel carries roughly "
          f"{100*(1-v_pre/v_bon):.0f}% of its gross value through to the total,")
    print(f"     against {100*(1-lam):.0f}% for the average foul event.")


if __name__ == "__main__":
    main()
