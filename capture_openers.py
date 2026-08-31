"""PHASE 1 -- capture openers and write the immutable prospective row.

Runs as early as openers exist, BEFORE the injury report and before any line
movement. Writes:
  * one immutable row per game via prospective_log.log_game()
  * lines_today.csv for nba_monitor's MOVE_COMBINED leg

INPUT  openers_YYYY-MM-DD.csv with columns:
         team_h,team_r,open_total,open_spread[,open_ml_h,open_ml_r][,game_id][,obtained_at_utc]
       team names must match the master (e.g. "Boston","Indiana").
       obtained_at_utc: when the opener was OBSERVED. If absent, now() is used
       and the row is marked source='capture-time' -- less trustworthy, because
       PREREG D2 requires knowing the opener preceded our information.

USAGE  python capture_openers.py 2026-10-20 [openers.csv]
"""
import sys, os, csv, datetime as dt
import pandas as pd, numpy as np
sys.path.insert(0, "/home/dpope/projects/nba_entropy_replication")
import frozen_models as FM
import prospective_log as PL
import pbp_transition as PT

LINES_OUT = "lines_today.csv"

def _abbr_map():
    t = pd.read_csv("team_mapping.csv")
    return dict(zip(t.bigdataball_name, t.abbr))

def main(day, path=None):
    path = path or f"openers_{day}.csv"
    if not os.path.exists(path):
        print(f"FAIL no opener file: {path}"); return 1
    sl = pd.read_csv(path)
    need = {"team_h","team_r","open_total","open_spread"}
    if not need.issubset(sl.columns):
        print(f"FAIL {path} needs {sorted(need)}"); return 1

    g  = FM.load_history()
    st = FM.build_states(g, day)          # strictly < day, so same-day safe
    pr = FM.team_profiles(g, day)
    if st["ab"] is None:
        print("FAIL no a,b fit -- need >=400 completed prior-season games"); return 1
    print(f"states as of {day}: {st['n_games']:,} prior games, a,b={tuple(round(v,4) for v in st['ab'])}")
    stale = PT.staleness(day)
    if not stale["ok"]:
        # Log m_X EMPTY rather than from a frozen transition state. An empty field
        # is auditable; a silently-stale one is not.
        print(f"  WARN {stale['reason']} (last {stale.get('last_game')}) -- m_X will be logged EMPTY")
        st["mx"] = None

    ab = _abbr_map(); rows = []; n_ok = n_skip = 0
    for r in sl.itertuples():
        gid = getattr(r, "game_id", None) or f"{day}-{ab.get(r.team_r,r.team_r)}-{ab.get(r.team_h,r.team_h)}"
        obtained = getattr(r, "obtained_at_utc", None)
        if not obtained or (isinstance(obtained, float) and np.isnan(obtained)):
            obtained = dt.datetime.utcnow().isoformat(timespec="seconds")+"Z"
            src = "capture-time"
        else:
            src = "observed"
        try:
            q = FM.predict_game(st, pr, r.team_h, r.team_r,
                                float(r.open_total), float(r.open_spread))
        except KeyError as e:
            print(f"  SKIP {gid}: {e}"); n_skip += 1; continue
        if not np.isfinite(q["P_book"]):
            print(f"  SKIP {gid}: P_book not computable"); n_skip += 1; continue
        try:
            row = PL.log_game(gid, day, r.team_h, r.team_r,
                              float(r.open_total), float(r.open_spread),
                              f"openers_csv:{src}", obtained,
                              q["P_hat"], q["P_book"], q["EffSum"],
                              q["mu5"], q["m_X"],
                              getattr(r, "open_ml_h", None), getattr(r, "open_ml_r", None))
        except ValueError as e:
            print(f"  SKIP {gid}: {e}"); n_skip += 1; continue
        n_ok += 1
        print(f"  {gid:<28} E_pace {float(row['E_pace']):+7.2f}  bet={row['bet_flag']}  side={row['side']}")
        rows.append({"game_date": day, "away_abbr": ab.get(r.team_r, r.team_r),
                     "home_abbr": ab.get(r.team_h, r.team_h),
                     "open_total": r.open_total})
    if rows:
        pd.DataFrame(rows).to_csv(LINES_OUT, index=False)
        print(f"wrote {LINES_OUT} ({len(rows)} games) for MOVE_COMBINED")
    print(f"logged {n_ok}, skipped {n_skip}")
    return 0 if n_ok else 1

if __name__ == "__main__":
    if len(sys.argv) < 2: print(__doc__); sys.exit(1)
    sys.exit(main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None))
