"""PHASE 4 -- append prior-day outcomes to the prospective log.

Must not run before BigDataBall lands, or the box scores are absent and the run
silently settles nothing. Appends close/actual only; pre-game fields are never
touched (prospective_log.settle refuses to overwrite).

Computes NO wagering performance -- PREREG D3 forbids interim looks.

USAGE  python settle_day.py 2026-10-20
"""
import sys, warnings
import pandas as pd, numpy as np
warnings.filterwarnings("ignore")
sys.path.insert(0, "/home/dpope/projects/nba_entropy_replication")
import frozen_models as FM
import prospective_log as PL
import pbp_transition as PT
import pbp_feed as PF

def main(day):
    # PBP transition/live-TO must land BEFORE the next capture, or m(X) is stale.
    # A live 2026-27 feed must pass its raw PBP frame: PT.update(day, frame).
    try:
        # Live CDN feed is primary; PT.update falls back to the historical parquet
        # when the feed yields nothing (backtests, pre-2026-27 dates).
        frame = None
        try:
            f = PF.fetch_day(day)
            frame = f if len(f) else None
        except Exception as fe:
            print(f"  pbp_feed unavailable ({fe}); falling back to parquet")
        n_tr = PT.update(day, pbp_frame=frame)
        src = "cdn" if frame is not None else "parquet"
        print(f"pbp transition: appended {n_tr} team-games ({src})")
    except Exception as e:
        print(f"pbp transition FAILED ({e}) -- m(X) will go stale; fix before next capture")
    g = FM.load_history()
    d = g[(g.date == pd.Timestamp(day)) & g.played]
    if not len(d):
        print(f"no played games found for {day} -- has BigDataBall landed?"); return 1
    with open(PL.LOG) as f:
        import csv as _c
        logged = {r["game_id"]: r for r in _c.DictReader(f)}
    n_ok = n_miss = n_already = 0
    for r in d.itertuples():
        cand = [k for k, v in logged.items()
                if v["date"] == day and v["TEAM_H"] == r.TEAM_H and v["TEAM_R"] == r.TEAM_R]
        if not cand:
            print(f"  NOT LOGGED {r.TEAM_R} @ {r.TEAM_H} -- capture phase missed it"); n_miss += 1; continue
        gid = cand[0]
        if logged[gid]["actual_total"]:
            n_already += 1; continue
        try:
            PL.settle(gid, r.close if np.isfinite(r.close) else "",
                      r.pH + r.pR, round(r.gpace, 3))
            n_ok += 1
        except ValueError as e:
            print(f"  SKIP {gid}: {e}"); n_miss += 1
    print(f"settled {n_ok}, already-settled {n_already}, unmatched {n_miss}")
    h = PL.health()
    print(f"log health: rows={h['rows']} settled={h['settled']} "
          f"incomplete_pregame={h['incomplete_pregame_fields']}")
    return 0 if n_miss == 0 else 1

if __name__ == "__main__":
    if len(sys.argv) < 2: print(__doc__); sys.exit(1)
    sys.exit(main(sys.argv[1]))
