"""Unified daily runner for the 2026-27 season. THIS MODULE PLACES NO BETS.

Execution lives in `nba_live_trader.py`, which reads the logs written here. The
split is deliberate and load-bearing: a module that computes a signal cannot
place an order, and a module that places orders cannot compute a signal. See
AMENDMENT_live_trading.md and LIVE_TRADING_OPS.md.


Consolidates four independently-built loggers into one dependency-ordered run:

  PHASE 1  capture   openers + timestamp -> prospective_log        (as early as available)
  PHASE 2  assign    referee slate -> crewshock_live, nba_monitor  (after 9am ET)
  PHASE 3  snapshot  Kalshi totals ladders                         (pregame)
  PHASE 4  settle    prior day's results into every log            (next morning)

Ordering is not cosmetic:
  * PHASE 1 must precede the injury report and any line movement. The opener
    timestamp is the field INJURY_TIMING_AUDIT showed we lacked in 2025-26.
  * PHASE 2 cannot run before ~9am ET; referee assignments do not exist yet.
  * PHASE 4 must not run before BigDataBall lands, or histories are a day stale.

DELIBERATELY ABSENT: any computation of hit rate, ROI or P/L.
PREREG_2026_27_PROSPECTIVE D3 forbids interim wagering looks. `status()` reports
pipeline health only.
"""
import subprocess, sys, os, datetime as dt, json

ROOT = "/home/dpope/projects/nba_entropy_replication"
PY   = "/home/dpope/nba_env/bin/python"
KAL  = "/mnt/c/NBA2/Kalshi/download_nba_totals.py"
STATE= os.path.expanduser("~/data/nba_daily_state.jsonl")

SEASON = {
    "preseason_start": "2026-10-03",   # plumbing test only, NOT scored
    "opening_day":     "2026-10-20",
    "move_live":       "2026-11-15",   # MOVE_COMBINED needs ~10 games/team
    "asb_break":       "2027-02-18",
    "last_regular":    "2027-04-11",
}

def _run(label, cmd, required=True):
    t0 = dt.datetime.utcnow()
    try:
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=1800)
        ok = p.returncode == 0
        out = (p.stdout or "")[-400:]
    except Exception as e:
        ok, out = False, str(e)[:400]
    rec = {"utc": t0.isoformat(timespec="seconds")+"Z", "step": label,
           "ok": ok, "required": required, "tail": out}
    with open(STATE, "a") as f: f.write(json.dumps(rec)+"\n")
    print(f"  [{'OK ' if ok else 'FAIL'}] {label}")
    if not ok and required: print(f"        {out.strip()[:300]}")
    return ok

def phase1_capture(day):
    """Openers + timestamp. Feeds prospective_log AND MOVE_COMBINED."""
    print(f"PHASE 1 capture  {day}")
    return _run("openers", [PY, "capture_openers.py", day])

def phase2_assignments(day):
    """After 9am ET. Referee-dependent signals."""
    print(f"PHASE 2 assignments  {day}")
    a = _run("crewshock_live", [PY, "crewshock_live.py", "daily", day])
    b = _run("nba_monitor",    [PY, "nba_monitor.py", day])
    return a and b

def phase3_ladders(day):
    """Pregame Kalshi snapshot. Feeds the ladder archive, not any live decision."""
    print(f"PHASE 3 ladders  {day}")
    return _run("kalshi_ladders", [PY, KAL, "--date", day], required=False)

def phase4_settle(day):
    """Prior day's outcomes. Requires BigDataBall to have landed."""
    print(f"PHASE 4 settle  {day}")
    return _run("settle", [PY, "settle_day.py", day])

def status():
    """Pipeline health ONLY. Computes no wagering performance -- see D3."""
    import prospective_log as PL
    out = {"season": SEASON, "prospective_log": PL.health()}
    if os.path.exists(STATE):
        with open(STATE) as f: rows = [json.loads(l) for l in f]
        recent = rows[-40:]
        out["recent_failures"] = [r["step"] for r in recent if not r["ok"] and r["required"]]
        out["runs_logged"] = len(rows)
    return out

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__); print("usage: nba_daily.py {capture|assignments|ladders|settle|status} [YYYY-MM-DD]")
        sys.exit(1)
    cmd = sys.argv[1]
    day = sys.argv[2] if len(sys.argv) > 2 else dt.date.today().isoformat()
    if cmd == "status":
        print(json.dumps(status(), indent=2)); sys.exit(0)
    fn = {"capture": phase1_capture, "assignments": phase2_assignments,
          "ladders": phase3_ladders, "settle": phase4_settle}.get(cmd)
    if fn is None: print(f"unknown phase {cmd}"); sys.exit(1)
    sys.exit(0 if fn(day) else 1)
