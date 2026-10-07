"""Automatic daily trader for the three frozen 2026-27 strategies.

    python nba_auto_trader.py preflight            # check every dependency, trade nothing
    python nba_auto_trader.py early   [--arm]      # 09:00 ET  PaceGap + MOVE_COMBINED
    python nba_auto_trader.py late    [--arm]      # ~2h pre-tip  CrewShock
    python nba_auto_trader.py dashboard            # build + publish s3://kalshi-strat/nba.html

Governing documents: AMENDMENT_live_trading.md (the reversal of "no capital"),
LIVE_TRADING_OPS.md (runbook), PREREG_2026_27_PROSPECTIVE.md (the frozen rules).
PROJECT_CLOSED.md closed the RESEARCH on 2026-09-14; it explicitly did NOT cancel
this frozen evaluation.

=============================================================================
WHY THERE ARE TWO RUNS AND NOT ONE
=============================================================================
09:00 ET is the right time for two of the three strategies and the wrong time
for the third, for two independent reasons:

  PaceGap, MOVE_COMBINED   settle against the OPENER      -> fill EARLY. 09:00 is correct.
  CrewShock                settles against the CLOSE      -> fill LATE.

  and separately: REFEREE ASSIGNMENTS DO NOT EXIST AT 09:00 ET. official.nba.com
  publishes them around or after 9am. A 09:00 CrewShock run usually scores an
  EMPTY SLATE and logs nothing -- it does not error, it just silently does
  nothing, which is the worst of the three outcomes.

`late` exists for CrewShock alone. Running CrewShock in `early` is possible
(--force-crewshock) and is a DIFFERENT BET than the one that was backtested:
its edge is measured against the closing total, and at 09:00 the close does not
exist. The open->close move is roughly unbiased (mean -0.032 pts) but carries
sd 3.175 pts against a 1.925-pt edge, so it is noise added for nothing.

=============================================================================
THE OPENING-TOTAL DEPENDENCY -- this gates two of the three strategies
=============================================================================
PaceGap needs `open_total` and MOVE_COMBINED needs `ot_open` as BOTH a model
input AND the settlement reference. Neither can be synthesised.

This module will NOT substitute Kalshi's own ladder centre for the sportsbook
opener. It is tempting (Kalshi is right there, and at 09:00 its centre is near
the opener) but the backtests were struck on the sportsbook opening number, and
swapping the reference changes what is being traded. Sources, in order:

  1. openers_YYYY-MM-DD.csv in the project dir  (team_h,team_r,open_total,open_spread)
  2. The Odds API, if ODDS_API_KEY is set       (paper_trade.py already speaks it)

With neither, the early phase SKIPS both strategies and says so. CrewShock is
unaffected and still runs in `late`.
"""
import os, sys, csv, json, subprocess, argparse, datetime as dt

ROOT     = os.environ.get("NBA_PROJECT_DIR", "/home/dpope/projects/nba_entropy_replication")
HERE     = os.path.dirname(os.path.abspath(__file__))
PY       = os.environ.get("NBA_PY", "/home/dpope/nba_env/bin/python")
STATE    = os.path.expanduser("~/data/nba_auto_trader.jsonl")
KILL     = os.path.expanduser("~/data/NBA_TRADING_HALT")
S3_BUCKET = os.environ.get("NBA_S3_BUCKET", "kalshi-strat")
S3_KEY    = os.environ.get("NBA_S3_KEY", "nba.html")

# Reuse the WINDOWS AWS profile that the earnings-mention publisher already uses
# for s3://kalshi-strat/dashboard.html. Referenced, never copied: one source of
# truth, rotation on the Windows side propagates with no edit here, and no
# second copy of a secret exists. run_nba_trader.sh exports these too; this
# fallback keeps a direct `python nba_auto_trader.py` working identically.
for _var, _default in (("AWS_SHARED_CREDENTIALS_FILE", "/mnt/c/Users/rando/.aws/credentials"),
                       ("AWS_CONFIG_FILE", "/mnt/c/Users/rando/.aws/config"),
                       ("AWS_DEFAULT_REGION", "us-east-1")):
    if not os.environ.get(_var) and (_default.startswith("us-") or os.path.exists(_default)):
        os.environ[_var] = _default
# ORDER MATTERS AND IS EASY TO GET BACKWARDS. insert(0, ...) in a loop REVERSES
# the argument order, so iterating (HERE, ROOT) leaves ROOT first and the repo
# copy of every module shadows the installed one. That is not academic: a copy
# of this stack is committed to the project for version control AND installed
# here, so the wrong one silently wins and then looks for its config next to
# itself. Iterate (ROOT, HERE) so HERE ends up at position 0.
for p in (ROOT, HERE):
    if p in sys.path:
        sys.path.remove(p)
    sys.path.insert(0, p)


def _log(step, ok, detail=""):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with open(STATE, "a") as f:
        f.write(json.dumps({"utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                            "step": step, "ok": bool(ok), "detail": str(detail)[:400]}) + "\n")
    print(f"  [{'OK  ' if ok else 'FAIL'}] {step}" + (f"  {detail}" if detail else ""))
    return ok


def _run(step, cmd, cwd=ROOT, required=True):
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=1800)
        ok = p.returncode == 0
        tail = ((p.stdout or "") + (p.stderr or "")).strip().splitlines()
        detail = tail[-1] if tail else ""
        if not ok and tail:
            print("      " + "\n      ".join(tail[-6:]))
    except Exception as e:
        ok, detail = False, f"{type(e).__name__}: {e}"
    _log(step, ok, detail)
    return ok or not required


def openers_path(day):
    return os.path.join(ROOT, f"openers_{day}.csv")


def have_openers(day):
    """Is there a usable sportsbook opener source for `day`?  (path, how) or (None, why)."""
    p = openers_path(day)
    if os.path.exists(p):
        try:
            with open(p) as f:
                rows = list(csv.DictReader(f))
            need = {"team_h", "team_r", "open_total", "open_spread"}
            if rows and need.issubset(rows[0]):
                return p, f"csv ({len(rows)} games)"
            return None, f"{os.path.basename(p)} missing columns {sorted(need - set(rows[0] if rows else []))}"
        except Exception as e:
            return None, f"unreadable: {e}"
    try:
        import nba_openers as O
        k, src = O.api_key()
        return None, f"no CSV yet; Odds API key available ({src}) -- will fetch at run time"
    except Exception:
        pass
    return None, "no openers CSV, and no Odds API key in env or odds_config.json"


# --------------------------------------------------------------------- phases
def phase_feed(day, strict=True):
    """Refresh the BigDataBall season-to-date feed. CrewShock depends on it."""
    print(f"\n[1] BigDataBall feed  {day}")
    import nba_bdb_feed as F
    try:
        rc = F.convert(asof=day, strict_age=strict)
    except Exception as e:
        return _log("bdb_feed", False, f"{type(e).__name__}: {e}")
    return _log("bdb_feed", rc == 0, f"rc={rc}")


def phase_early(day, arm=False, take=True, force_crewshock=False):
    """09:00 ET. Opener-settled strategies: PaceGap and MOVE_COMBINED."""
    if os.path.exists(KILL):
        return _log("early", False, f"kill switch present: {KILL}")
    print(f"\n=== EARLY  {day}  {'ARMED' if arm else 'DRY RUN'} ===")
    phase_feed(day, strict=False)          # not fatal here; CrewShock runs in `late`

    print(f"\n[2] opening totals")
    path, how = have_openers(day)
    if path is None:
        # Try the Odds API. It refuses to overwrite an existing capture, so a
        # re-run never replaces an opener that was already observed.
        _run("fetch_openers", [PY, os.path.join(HERE, "nba_openers.py"), "--date", day],
             cwd=HERE, required=False)
        path, how = have_openers(day)
    if path is None:
        _log("openers", False, how)
        print("      SKIPPING PaceGap and MOVE_COMBINED -- both settle against the")
        print("      sportsbook opener and it is not available. Kalshi's own centre is")
        print("      deliberately NOT substituted. CrewShock is unaffected (run `late`).")
        return False
    _log("openers", True, how)

    print(f"\n[3] capture openers -> immutable prospective row")
    # LOOK-AHEAD GUARD. capture_openers writes the IMMUTABLE prospective row and
    # refuses duplicates, so a row written for a future date permanently blocks
    # the real capture on that day ("already logged -- rows are immutable").
    # A rehearsal run on a far-future slate did exactly that and had to be
    # unwound by hand. Capture is for today, or yesterday at the latest.
    ahead = (dt.date.fromisoformat(day) - dt.date.today()).days
    if ahead > 1:
        _log("capture_openers", False,
             f"REFUSED: {day} is {ahead} days ahead; capture writes an immutable row")
        print("      Use --date only for today or a completed day. Everything else in")
        print("      this phase still ran; only the immutable write was skipped.")
    else:
        _run("capture_openers", [PY, "capture_openers.py", day, path])

    print(f"\n[4] MOVE_COMBINED recommendation")
    # NOT `path`: that file is the capture_openers schema (full team names).
    # move_combined_live wants game_date,away_abbr,home_abbr,open_total.
    lines = os.path.join(ROOT, f"lines_{day}.csv")
    if not os.path.exists(lines):
        _log("move_combined", False, f"{os.path.basename(lines)} missing "
             f"(nba_openers writes it alongside the openers CSV)")
    else:
        _run("move_combined", [PY, "move_combined_live.py", "--date", day,
                               "--lines", lines], required=False)

    print(f"\n[5] Kalshi orders  (resting bids; see AMENDMENT §3 for why not taking)")
    strats = ["pacegap", "move"] + (["crewshock"] if force_crewshock else [])
    if force_crewshock:
        print("      !! --force-crewshock: CrewShock settles at the CLOSE. At 09:00 the")
        print("         close does not exist. This is not the backtested bet.")
    ok = True
    for s in strats:
        cmd = [PY, os.path.join(HERE, "nba_live_trader.py"), "--date", day, "--strategy", s]
        if arm:  cmd.append("--arm")
        if not take: cmd.append("--make")   # TAKER is the default
        ok &= _run(f"trade_{s}", cmd, cwd=HERE, required=False)
    return ok


def phase_late(day, arm=False, take=True):
    """~2h before first tip. CrewShock only: it is graded at the close."""
    if os.path.exists(KILL):
        return _log("late", False, f"kill switch present: {KILL}")
    print(f"\n=== LATE  {day}  {'ARMED' if arm else 'DRY RUN'} ===")
    if not phase_feed(day, strict=True):
        print("      HARD STOP: CrewShock will not be scored on a stale foul history.")
        return False
    print(f"\n[2] referee assignments -> crewshock_live_log.csv")
    if not _run("crewshock_daily", [PY, "crewshock_live.py", "daily", "--date", day]):
        return False
    print(f"\n[3] Kalshi orders  (close-settled, OVER-only -> proven YES path only)")
    # Both close-settled strategies run here. final7 only produces signals
    # inside the last 7 days of the regular season; on every other date it
    # returns nothing, so this line is a no-op for ~96% of the season.
    sys.path.insert(0, HERE)
    import nba_live_trader as LT
    strats = ["crewshock"] + (["final7"] if LT.in_final7_window(day) else [])
    if len(strats) > 1:
        print(f"      final7 ACTIVE: {day} is inside the last {LT.FINAL7_DAYS} days "
              f"(season ends {LT.FINAL7_LAST_REGULAR}).")
        print(f"      It is DISCRETIONARY, not preregistered -- CrewShock claims any")
        print(f"      game they both want. See AUTO_TRADER_OPS.md.")
    ok = True
    for s in strats:
        cmd = [PY, os.path.join(HERE, "nba_live_trader.py"), "--date", day, "--strategy", s]
        if arm:  cmd.append("--arm")
        if not take: cmd.append("--make")   # TAKER is the default
        ok &= _run(f"trade_{s}", cmd, cwd=HERE, required=False)
    return ok


def phase_cancel(arm=False):
    """Pull resting orders on games near tip. NBA totals trade IN-PLAY."""
    print(f"\n=== CANCEL ===")
    cmd = [PY, os.path.join(HERE, "nba_live_trader.py"), "--cancel"]
    if arm: cmd.append("--arm")
    return _run("cancel", cmd, cwd=HERE, required=False)


def phase_dashboard(publish=True):
    print(f"\n=== DASHBOARD -> s3://{S3_BUCKET}/{S3_KEY} ===")
    env = dict(os.environ, NBA_S3_BUCKET=S3_BUCKET, NBA_S3_KEY=S3_KEY)
    cmd = [PY, os.path.join(HERE, "nba_dashboard.py"), "--build"] + (["--publish"] if publish else [])
    try:
        p = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True, timeout=600, env=env)
        tail = ((p.stdout or "") + (p.stderr or "")).strip().splitlines()
        if tail: print("      " + "\n      ".join(tail[-4:]))
        return _log("dashboard", p.returncode == 0, tail[-1] if tail else "")
    except Exception as e:
        return _log("dashboard", False, f"{type(e).__name__}: {e}")


# ------------------------------------------------------------------ preflight
def preflight(day):
    """Check every dependency. Trades nothing. Run this before opening night."""
    print(f"PREFLIGHT  {day}\n" + "=" * 68)
    rows = []
    def chk(name, ok, detail):
        rows.append((name, ok, detail)); return ok

    chk("python", os.path.exists(PY), PY)
    chk("project dir", os.path.isdir(ROOT), ROOT)
    for f in ("crewshock_live.py", "capture_openers.py", "move_combined_live.py",
              "frozen_models.py", "prospective_log.py", "team_mapping.csv"):
        chk(f"  {f}", os.path.exists(os.path.join(ROOT, f)), "")
    for f in ("nba_kalshi.py", "nba_live_trader.py", "nba_dashboard.py", "nba_bdb_feed.py"):
        chk(f"  {f}", os.path.exists(os.path.join(HERE, f)), "")

    try:
        import nba_bdb_feed as F
        try:
            p, fd = F.find_feed(day)
            age = (dt.date.fromisoformat(day) - fd).days
            chk("BigDataBall feed", age <= F.MAX_AGE_DAYS,
                f"{os.path.basename(p)} dated {fd} (age {age}d)")
        except Exception as e:
            chk("BigDataBall feed", False, str(e))
    except Exception as e:
        chk("BigDataBall feed", False, f"import failed: {e}")

    # Openers pass if the CSV exists OR the Odds API can actually serve it.
    # A key that is present but deactivated must not read as PASS.
    path, how = have_openers(day)
    if path is None:
        try:
            import nba_openers as O
            ev, quota, src = O.fetch()
            n = sum(1 for e in ev
                    if (dt.datetime.fromisoformat(e["commence_time"].replace("Z", "+00:00"))
                        - dt.timedelta(hours=5)).date().isoformat() == day)
            chk("opening totals", True,
                f"Odds API live (key from {src}); {n} games on {day}; "
                f"quota {quota['used']}/{int(quota['used'] or 0) + int(quota['remaining'] or 0)}")
        except Exception as e:
            chk("opening totals", False, f"{how} | {str(e)[:110]}")
    else:
        chk("opening totals", True, how)

    chk("frozen history", os.path.exists("/mnt/c/NBA2/dfMaster_OT_2017-2026.csv"),
        "dfMaster_OT_2017-2026.csv")

    # Referee names: an unresolved official contributes 0 to the crew sum and
    # biases CrewShock toward zero. resolve_officials() catches it at run time
    # and refuses the game; this catches it while there is still time to fix.
    try:
        import io, contextlib
        import nba_ref_check as RC
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = RC.check(dfrom=day, quiet=True)
        out = buf.getvalue()
        line = next((l for l in out.splitlines() if "distinct officials assigned" in l), "")
        if "no assignments published" in out:
            chk("referee names", True, f"none published for {day} yet (expected pre-season)")
        else:
            chk("referee names", rc == 0, line.strip() or "see nba_ref_check.py")
    except Exception as e:
        chk("referee names", False, f"{type(e).__name__}: {str(e)[:70]}")

    try:
        sys.path.insert(0, HERE)
        import nba_kalshi as NK
        k = NK.NBAKalshi()
        code, who = k.whoami()
        chk("Kalshi auth", code == 200,
            f"balance ${(who.get('balance') or 0)/100:,.2f}" if code == 200 else str(who)[:80])
        chk("Kalshi NBA events", True, f"{len(k.open_events())} open KXNBATOTAL events")
    except Exception as e:
        chk("Kalshi auth", False, f"{type(e).__name__}: {e}")

    # SHARD FUNDING. Kalshi shards its exchange and funds do not cross between
    # shards. Every NBA series is on exchange_index 3 (Tennis/Baseball/
    # Basketball); this account's balance has been on 0 (Default), where the
    # mention markets live. An order sent with $0 on the NBA shard returns
    # 404 insufficient_shard_balance -- so WITHOUT THIS CHECK the trader places
    # nothing all season and every rejection looks like a bad order. Found
    # 2026-10-07 by a 1-contract probe, not by reading the docs.
    try:
        import nba_kalshi as NKQ
        _k = NKQ.NBAKalshi()
        _bal, _idx = _k.shard_balance(), _k.series_shard()
        if _idx is None:
            chk("NBA shard funded", None,
                "no open NBA event to read exchange_index from -- recheck in season")
        else:
            _have = _bal.get(int(_idx), 0.0)
            chk("NBA shard funded", _have > 0.0,
                f"${_have:.2f} on exchange_index {_idx} ("
                + ", ".join(f"{i}=${v:.2f}" for i, v in sorted(_bal.items()))
                + (")" if _have > 0 else ") -- TRANSFER FUNDS TO SHARD "
                   f"{_idx}; every NBA order will 404 until then"))
    except Exception as e:
        chk("NBA shard funded", False, f"{type(e).__name__}: {e}")

    try:
        import nba_live_trader as LT
        chk("NO-side verified", LT.NO_SIDE_VERIFIED,
            "UNDER enabled" if LT.NO_SIDE_VERIFIED
            else "UNDER refused -- run nba_live_trader.py --verify-no-side; CrewShock unaffected")
    except Exception as e:
        chk("NO-side verified", False, str(e))

    try:
        import boto3
        s = boto3.client("s3")
        s.head_bucket(Bucket=S3_BUCKET)
        chk("S3 bucket", True, f"s3://{S3_BUCKET}/{S3_KEY}")
    except Exception as e:
        chk("S3 bucket", False, f"{type(e).__name__}: {str(e)[:70]}")

    chk("kill switch clear", not os.path.exists(KILL), KILL)

    print(f"\n{'check':<26}{'':<6}detail")
    for n, ok, d in rows:
        print(f"{n:<26}{'PASS' if ok else 'FAIL':<6}{d}")
    hard = [n for n, ok, d in rows if not ok]
    print("\n" + ("ALL CHECKS PASS" if not hard else f"{len(hard)} FAILING: {', '.join(hard)}"))
    return 0 if not hard else 1


def _take(a):
    """Taker unless --make is given. --make --arm is refused outright: we are
    not approved for market making on Kalshi, so the maker path may be measured
    but must never be armed."""
    if getattr(a, "make", False) and a.arm:
        sys.exit("REFUSED: --make --arm is market making, which is not approved.")
    return not getattr(a, "make", False)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("phase", choices=["preflight", "feed", "early", "late",
                                      "cancel", "dashboard", "all"])
    ap.add_argument("--date", default=dt.date.today().isoformat())
    ap.add_argument("--arm", action="store_true", help="place real orders")
    ap.add_argument("--take", action="store_true",
                    help="(default, kept for compatibility) cross the spread")
    ap.add_argument("--make", action="store_true",
                    help="NOT APPROVED -- rest at the bid. Analysis only, never arm.")
    ap.add_argument("--force-crewshock", action="store_true",
                    help="run CrewShock in the early phase (NOT the backtested bet)")
    ap.add_argument("--no-publish", action="store_true")
    a = ap.parse_args()
    d = a.date
    if a.phase == "preflight":  sys.exit(preflight(d))
    if a.phase == "feed":       sys.exit(0 if phase_feed(d) else 1)
    if a.phase == "early":      sys.exit(0 if phase_early(d, a.arm, _take(a), a.force_crewshock) else 1)
    if a.phase == "late":       sys.exit(0 if phase_late(d, a.arm, _take(a)) else 1)
    if a.phase == "cancel":     sys.exit(0 if phase_cancel(a.arm) else 1)
    if a.phase == "dashboard":  sys.exit(0 if phase_dashboard(not a.no_publish) else 1)
    ok = phase_early(d, a.arm, _take(a), a.force_crewshock)
    ok &= phase_late(d, a.arm, _take(a))
    phase_dashboard(not a.no_publish)
    sys.exit(0 if ok else 1)
