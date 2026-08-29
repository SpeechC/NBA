"""NBA MONITOR 2026-27 — four signals, one slate, LOG ONLY.

=============================================================================
 THIS PROGRAM PLACES NO BETS. No order-placement code exists here and none is
 to be added. It prints a table and appends to a JSONL log. Structural.
=============================================================================

SIGNALS, and their status is NOT uniform — this is the whole point of the
layout. Three may be actioned; one may not.

  CrewShock      FROZEN / validated. OVER when CrewShock >= 0.8682.
                 CLOSING_REFEREE.md. Pooled 54.82%, ROI +4.66%,
                 CI [-0.36%, +9.67%]. Forward test: PREREG_crewshock_forward.
  final7         VALIDATED. OVER when days_left <= 7 (final week of the
                 regular season). CLOSING.md: 55.29% OOS, 454 bets, 97.2nd
                 percentile matched-window null, 7 of 8 seasons.
  pre_asb3       *** NOT VALIDATED — DISPLAY ONLY, NEVER ACTIONED ***
                 Final 3 calendar days before the All-Star break. 60.47% over
                 raw, but it was the best of seven pre-specified regimes and
                 the FAMILY-WISE max permutation gives p = 0.0712. CLOSING.md
                 calls it "the strongest untested lead, not a second
                 strategy", and explicitly forbids adopting a 7-day version
                 post hoc. PRE_DAYS is 3 and is not tunable here.
  MOVE_COMBINED  FROZEN. m = 0.0337 + 0.8402*ridge + 0.6869*latent,
                 |m| >= 1.0 primary / 1.5 confirmatory. CLV is the endpoint;
                 ROI CI includes zero (MOVEMENT_FULL.md).

CALENDAR WINDOWS COME FROM THE PUBLISHED SCHEDULE, NOT FROM PLAYED GAMES.
`days_left` was defined in backtest as max(season date) - date. Live you do
not know the season's last date from results, and the All-Star break is not
locatable from games already played. Both are knowable pregame from the
schedule, and that is where they are read from here. Deriving them from
completed games would silently mis-fire all season.

PRESEASON. Both frozen estimators are built on "Regular Season" only.
Preseason games must never enter CrewShock's official histories or
MOVE_COMBINED's rolling features. A preseason run is a PLUMBING TEST: every
signal is emitted with action INVALID_PRESEASON and nothing is actionable.
"""
import argparse
import datetime as dt
import json
import os
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ---- CONFIG -----------------------------------------------------------------
BOXSCORE_HIST = "/mnt/c/NBA2/dfMaster_OT_2017-2026.csv"   # through 2025-26
BOXSCORE_CURRENT = os.environ.get("NBA_CURRENT", "")      # daily file when live
SCHEDULE_CSV = "nba_schedule_2026_27.csv"                 # 2026-10-03 .. 2027-04-11
LOG = "nba_monitor_log.jsonl"
LINES_CSV = ""                                            # gid,total (optional)

CREW_THR = 0.8682          # FROZEN, development Q85
FINAL7_DAYS = 7            # FROZEN, CLOSING.md
PRE_ASB_DAYS = 3           # FROZEN at 3. NOT tunable. NOT a 7-day version.
MOVE_PRIMARY, MOVE_CONFIRM = 1.0, 1.5
# -----------------------------------------------------------------------------

STATUS = {
    "crewshock": ("FROZEN/validated", True),
    "final7": ("VALIDATED 55.29% OOS", True),
    "pre_asb3": ("NOT VALIDATED (family-wise p=0.0712)", False),   # never action
    "move_combined": ("FROZEN", True),
}


def load_schedule(path=SCHEDULE_CSV):
    s = pd.read_csv(path)
    s["game_date"] = pd.to_datetime(s.game_date)
    s["gid"] = s.game_id.astype(str).str.lstrip("0")
    s["is_preseason"] = s.label.astype(str).str.contains("Pre", case=False, na=False)
    # `label` is populated ONLY for special events (NBA Cup, Rivals Week,
    # international, Preseason); ordinary regular-season games are UNLABELLED.
    # So regular season is "not preseason", not "label contains Regular" --
    # that test matched nothing and silently emptied both calendar windows.
    s["is_regular"] = ~s["is_preseason"]
    return s


def calendar_windows(sched):
    """days_left and the All-Star break, from the PUBLISHED schedule.

    Backtest defined days_left as max(season date) - date. Live that maximum is
    only knowable from the schedule, and the break is the largest mid-season
    gap in SCHEDULED dates. Reading either from completed games would mis-fire.
    """
    reg = sched[sched.is_regular]
    if reg.empty:
        return {}
    last = reg.game_date.max()
    dts = np.sort(reg.game_date.unique())
    if len(dts) > 2:
        gaps = np.diff(dts).astype("timedelta64[D]").astype(int)
        break_day = pd.Timestamp(dts[int(np.argmax(gaps))])
        break_gap = int(gaps.max())
    else:
        break_day, break_gap = None, None
    return {"last_regular": last, "break_day": break_day, "break_gap": break_gap}


def calendar_flags(day, cal):
    day = pd.Timestamp(day)
    out = {"days_left": None, "final7": False,
           "days_to_break": None, "pre_asb3": False}
    if cal.get("last_regular") is not None:
        dl = (cal["last_regular"] - day).days
        out["days_left"] = dl
        out["final7"] = 0 <= dl <= FINAL7_DAYS
    if cal.get("break_day") is not None:
        dtb = (cal["break_day"] - day).days
        out["days_to_break"] = dtb
        out["pre_asb3"] = 0 <= dtb <= PRE_ASB_DAYS - 1
    return out


def panel_crewshock(day, boxscore_paths):
    import crewshock_live as CL
    try:
        slate = CL.fetch_assignments(day)
    except Exception as ex:                                   # noqa: BLE001
        return None, f"assignments ERR {type(ex).__name__}: {ex}"
    if slate.empty:
        return None, "no referee assignments published yet (posts ~9am ET)"
    h = CL.load_history(tuple(p for p in boxscore_paths if p))
    slate, gaps = CL.resolve_officials(slate, h)
    out = CL.crewshock(h, pending=slate)
    rec = out[out._pending].copy()
    rec["fires"] = (rec.CrewShock >= CREW_THR) & (~rec.data_gap.astype(bool))
    note = f"{len(h):,} completed games in history"
    if len(gaps):
        note += f"; {len(gaps)} UNRESOLVED official(s) -> DATA_GAP"
    return rec, note


def panel_move(day, lines_csv, sched_local):
    try:
        import move_combined_live as MC
    except Exception as ex:                                   # noqa: BLE001
        return None, f"module unavailable: {ex}"
    try:
        r = MC.recommend(pd.Timestamp(day), lines_csv=lines_csv or None,
                         sched_local=sched_local)
        return r, "ok"
    except Exception as ex:                                   # noqa: BLE001
        return None, f"{type(ex).__name__}: {ex}"


def run(day, preseason=False, lines_csv=LINES_CSV):
    sched = load_schedule()
    cal = calendar_windows(sched)
    flags = calendar_flags(day, cal)
    today = sched[sched.game_date == pd.Timestamp(day)]
    pre_today = bool(today.is_preseason.any()) if len(today) else False
    dry = preseason or pre_today

    print("=" * 78)
    print(f" NBA MONITOR  {day}   *** LOG ONLY - NO ORDERS ***")
    if dry:
        print(" PRESEASON DRY RUN - plumbing test. Every signal below is")
        print(" INVALID_PRESEASON: the frozen estimators are Regular-Season only.")
    print("=" * 78)
    print(f" schedule: {len(today)} game(s) listed for this date "
          f"({'preseason' if pre_today else 'regular' if len(today) else 'none'})")
    # SIGNAL AVAILABILITY. The four signals do NOT come online together, and a
    # silent "no bet" from a signal that cannot yet compute looks identical to a
    # signal that computed and declined. Say which it is.
    dl = flags["days_left"]
    print(f" availability: CrewShock ACTIVE from day one (officials carry "
          f"cross-season history) | MOVE_COMBINED needs ~10 games/team, so it "
          f"is BLIND until ~mid-Nov | final7 only fires in the final week | "
          f"pre_asb3 only near the break (and is never actioned)")
    print(f" calendar: last regular-season date "
          f"{cal.get('last_regular').date() if cal.get('last_regular') is not None else '?'}"
          f"   All-Star break "
          f"{cal.get('break_day').date() if cal.get('break_day') is not None else '?'}"
          f" (gap {cal.get('break_gap')}d)")

    rows = []

    # ---- calendar signals ---------------------------------------------------
    print(f"\n [2] final7        days_left={flags['days_left']}  "
          f"-> {'FIRES: OVER on every game' if flags['final7'] else 'no'}"
          f"   ({STATUS['final7'][0]})")
    print(f" [3] pre_asb3      days_to_break={flags['days_to_break']}  "
          f"-> {'IN WINDOW' if flags['pre_asb3'] else 'no'}")
    print(f"     *** {STATUS['pre_asb3'][0]} — DISPLAY ONLY, NEVER ACTIONED ***")

    # ---- CrewShock ----------------------------------------------------------
    print(f"\n [1] CrewShock  ({STATUS['crewshock'][0]}, threshold {CREW_THR})")
    rec, note = panel_crewshock(day, (BOXSCORE_HIST, BOXSCORE_CURRENT))
    print(f"     {note}")
    if rec is not None and len(rec):
        print(f"     {'gid':>9} {'matchup':<10} {'CrewShock':>10} {'minN':>5}  action")
        for _, r in rec.sort_values("CrewShock", ascending=False).iterrows():
            act = ("INVALID_PRESEASON" if dry else
                   "DATA_GAP" if r.data_gap else
                   "LOG_OVER" if r.fires else "no_action")
            print(f"     {r.gid:>9} {r.away}@{r.home:<6} {r.CrewShock:>10.4f} "
                  f"{r.min_prior:>5.0f}  {act}")
            rows.append({"signal": "crewshock", "gid": r.gid,
                         "value": float(r.CrewShock), "action": act})
        n_fire = int(rec.fires.sum())
        print(f"     {n_fire} of {len(rec)} fire"
              + ("  [selectivity is reported per PREREG_crewshock_forward §8]"
                 if n_fire else ""))

    # ---- MOVE_COMBINED ------------------------------------------------------
    print(f"\n [4] MOVE_COMBINED  ({STATUS['move_combined'][0]}, "
          f"|m| >= {MOVE_PRIMARY} / {MOVE_CONFIRM})")
    mv, mnote = panel_move(day, lines_csv, SCHEDULE_CSV)
    if mv is None or (hasattr(mv, "__len__") and len(mv) == 0):
        why = ("no games on the 2026-27 schedule for this date"
               if mnote == "ok" else mnote)
        print(f"     NOT SCORED — {why}")
        rows.append({"signal": "move_combined", "action": "UNAVAILABLE",
                     "note": mnote})
    else:
        try:
            print(mv.to_string(index=False)[:1500])
        except Exception:                                     # noqa: BLE001
            print(f"     {mv}")

    # ---- calendar rows into the log ----------------------------------------
    for gid in (today.gid.tolist() if len(today) else []):
        rows.append({"signal": "final7", "gid": gid, "value": flags["days_left"],
                     "action": ("INVALID_PRESEASON" if dry else
                                "LOG_OVER" if flags["final7"] else "no_action")})
        rows.append({"signal": "pre_asb3", "gid": gid,
                     "value": flags["days_to_break"],
                     "action": "DISPLAY_ONLY_NOT_VALIDATED"})

    stamp = dt.datetime.utcnow().isoformat(timespec="seconds")
    with open(LOG, "a") as f:
        for r in rows:
            r.update({"ts_utc": stamp, "date": str(day), "role": "OBSERVER",
                      "preseason_dry_run": dry})
            f.write(json.dumps(r) + "\n")
    print(f"\n appended {len(rows)} row(s) to {LOG}"
          f"   *** LOG ONLY - NO ORDER WAS PLACED ***")
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=dt.date.today().isoformat())
    ap.add_argument("--preseason", action="store_true",
                    help="force the dry-run label")
    ap.add_argument("--lines", default=LINES_CSV)
    a = ap.parse_args()
    run(a.date, preseason=a.preseason, lines_csv=a.lines)
