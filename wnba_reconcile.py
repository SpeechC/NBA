"""
===============================================================================
 WNBA HALFTIME MONITOR — OUTCOME RECONCILIATION                SINGLE-FILE / F5
===============================================================================
 Reads the append-only monitor logs, attaches each game's realized total, and
 grades the logged would-trades. Read-only: it never writes into the JSONL.

 Two outcome sources, in order of preference:
   1. `settlement` rows the monitor wrote in-session (score feed, same night)
   2. basketball-reference finals (wnba_2026_halves.csv) — the fallback that
      covers games the monitor never saw finalize (restart, crash, early exit)
 A game with neither is reported UNRESOLVED, never silently dropped.

 CANONICAL GRADING RULE (fixed here, one place, so it cannot drift):
   For each threshold, take the FIRST poll at or after halftime that produced
   would-trade rows, and within that poll the single best-edge rung — "best
   rung per game", matching the backtest's economic tail. No lookahead: the
   trade is decided from the earliest actionable moment only.
   YES pays iff realized_total > floor_strike (verified on 1,345 settled 2026
   markets, 100% agreement; every strike is .5, so ties cannot occur).

 Outputs outputs/wnba_live_panel.csv plus a printed M3 ladder comparable to
 PREREG_wnba_halftime.md s"Economic tail", and the M1 depth summary F1 needs.

 The panel columns (pre_L, h1, realized_total) are also exactly the training
 triple an adaptive refit would consume — see WNBA_PROTOTYPE_SPEC.md s14 on
 why that stays a season-end shadow comparison, not a live refit.
===============================================================================
"""
import datetime as dt
import glob
import json
import os
import sys

import pandas as pd

OUT_DIR = (r"D:\Kalshi\wnba_monitor" if os.name == "nt"
           else "/mnt/d/Kalshi/wnba_monitor")
HERE = os.path.dirname(os.path.abspath(__file__))
# The script is deployed to D:\Kalshi\code while the scraped finals live in
# the repo, so resolve the CSV across both homes rather than silently finding
# nothing (an absent file would zero the fallback with no visible error).
BREF_CANDIDATES = [
    os.path.join(HERE, "wnba_2026_halves.csv"),
    os.path.join(HERE, os.pardir, "wnba_2026_halves.csv"),
    (r"D:\Kalshi\wnba_2026_halves.csv" if os.name == "nt"
     else "/mnt/d/Kalshi/wnba_2026_halves.csv"),
    ("/home/dpope/projects/nba_entropy_replication/wnba_2026_halves.csv"
     if os.name != "nt" else
     r"\\wsl.localhost\Ubuntu\home\dpope\projects\nba_entropy_replication"
     r"\wnba_2026_halves.csv"),
]
BREF = next((p for p in BREF_CANDIDATES if os.path.exists(p)),
            BREF_CANDIDATES[0])
PANEL = os.path.join(HERE, "outputs", "wnba_live_panel.csv")
THRESHOLDS = (0.03, 0.05, 0.08)

# Duplicated from wnba_monitor.py deliberately: importing that module would
# chdir into the Kalshi directory and require credentials this script does not.
CITY_CODES = {
    "Atlanta": ("ATL",), "Chicago": ("CHI",), "Connecticut": ("CONN",),
    "Dallas": ("DAL",), "Golden State": ("GSV", "GS"), "Indiana": ("IND",),
    "Las Vegas": ("LVA", "LV"), "Los Angeles": ("LAS", "LA"),
    "Minnesota": ("MIN",), "New York": ("NYL", "NY"), "Phoenix": ("PHX",),
    "Portland": ("PDX", "POR"), "Seattle": ("SEA",), "Toronto": ("TOR",),
    "Washington": ("WSH", "WAS")}


def read_logs(out_dir):
    """-> (rows, files, phase_a_files). Tolerates partial trailing lines."""
    rows, files = [], sorted(glob.glob(os.path.join(out_dir, "monitor2_*.jsonl")))
    for p in files:
        with open(p, "r", encoding="utf-8") as fh:
            for ln, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    print(f"  [warn] {os.path.basename(p)}:{ln} unparseable "
                          f"(truncated write?) — skipped")
                    continue
                r["_file"] = os.path.basename(p)
                rows.append(r)
    phase_a = sorted(glob.glob(os.path.join(out_dir, "monitor_*.jsonl")))
    return rows, files, phase_a


def event_date(evt):
    tail = evt.rsplit("-", 1)[-1]
    try:
        return dt.datetime.strptime(tail[:7], "%y%b%d").date()
    except ValueError:
        return None


def bref_totals(path, with_count=False):
    """-> {(date, "AWAYHOME"): (total, h1, n_ot)}, optionally with game count

    Keyed by the CONCATENATED code pair exactly as the Kalshi ticker tail
    spells it, with one key per code variant: Kalshi writes Las Vegas as LV,
    New York NY, Los Angeles LA and Golden State GS, while the fuller LVA /
    NYL / LAS / GSV forms also appear. Emitting every variant makes the
    lookup a direct hit instead of a guess.
    """
    if not os.path.exists(path):
        return ({}, 0) if with_count else {}
    df = pd.read_csv(path)
    out, n = {}, 0
    for _, r in df.iterrows():
        def codes(name):
            for city, cs in CITY_CODES.items():
                if str(name).startswith(city):
                    return cs
            return ()
        acs, hcs = codes(r["away"]), codes(r["home"])
        if not acs or not hcs:
            continue
        d = dt.datetime.strptime(str(r["date"]), "%Y%m%d").date()
        h1 = r["a_q1"] + r["a_q2"] + r["h_q1"] + r["h_q2"]
        val = (int(r["a_final"] + r["h_final"]), int(h1), int(r["n_ot"]))
        n += 1
        for a in acs:
            for h in hcs:
                out[(d, a + h)] = val
    return (out, n) if with_count else out


def bref_lookup(evt, table):
    d = event_date(evt)
    if d is None:
        return None
    return table.get((d, evt.rsplit("-", 1)[-1][7:]))


def collect(rows):
    """-> {event: {pre_L, h1, polls[], settlement, dates}}"""
    ev = {}
    for r in rows:
        e = r.get("event")
        if not e:
            continue
        d = ev.setdefault(e, {"pre_L": None, "h1": None, "polls": [],
                              "settlement": None, "first_ts": r.get("ts_utc"),
                              "last_ts": r.get("ts_utc")})
        d["last_ts"] = r.get("ts_utc") or d["last_ts"]
        if r.get("type") == "settlement":
            d["settlement"] = r
        elif r.get("type") == "ladder":
            if r.get("pre_L") is not None and d["pre_L"] is None:
                d["pre_L"] = r["pre_L"]
            st = r.get("game_state") or {}
            if st.get("h1"):
                d["h1"] = st["h1"]
            if r.get("would_trade"):
                d["polls"].append({"ts": r["ts_utc"],
                                   "would": r["would_trade"],
                                   "period": st.get("period"),
                                   "status": st.get("status")})
    return ev


def canonical_trade(polls, th):
    """First poll at/after halftime with rows at this threshold -> best edge."""
    for p in sorted(polls, key=lambda x: x["ts"]):
        cands = [w for w in p["would"] if w["threshold"] == th]
        if cands:
            best = max(cands, key=lambda w: w["edge"])
            return {**best, "entry_ts": p["ts"], "entry_period": p["period"]}
    return None


def main(out_dir=OUT_DIR):
    print(f"[reconcile] reading {out_dir}")
    rows, files, phase_a = read_logs(out_dir)
    if not files:
        print("  no monitor2_*.jsonl found — nothing to reconcile.")
        return
    print(f"  {len(files)} log file(s), {len(rows)} row(s)"
          + (f"; {len(phase_a)} Phase-A file(s) ignored (no would-trade rows)"
             if phase_a else ""))
    feed_err = sum(1 for r in rows if r.get("type") == "feed_err")
    if feed_err:
        print(f"  {feed_err} feed_err row(s) logged — see M2/uptime notes")

    ev = collect(rows)
    table, n_bref = bref_totals(BREF, with_count=True)
    if not table:
        print(f"  [WARN] no basketball-reference finals found "
              f"(looked for {os.path.basename(BREF)} in "
              f"{len(BREF_CANDIDATES)} locations) — the fallback outcome "
              f"source is OFF; only monitor settlement rows will resolve.")
    else:
        print(f"  bref finals: {os.path.basename(BREF)} ({n_bref} game(s), "
              f"latest {max(d for d, _ in table)})")
    print(f"  {len(ev)} event(s) seen")

    recs, unresolved = [], []
    for e, d in sorted(ev.items()):
        total = h1 = n_ot = None
        src = None
        if d["settlement"]:
            total = d["settlement"]["realized_total"]
            h1 = d["settlement"].get("h1") or d["h1"]
            n_ot = d["settlement"].get("n_ot")
            src = "monitor"
        else:
            hit = bref_lookup(e, table)
            if hit:
                total, h1b, n_ot = hit
                h1 = d["h1"] or h1b
                src = "bref"
        base = {"event": e, "date": event_date(e), "pre_L": d["pre_L"],
                "h1": h1, "realized_total": total, "n_ot": n_ot,
                "outcome_src": src, "n_would_polls": len(d["polls"]),
                "first_ts": d["first_ts"], "last_ts": d["last_ts"]}
        if total is None:
            unresolved.append(base)
            if d["polls"]:
                print(f"  [UNRESOLVED] {e}: {len(d['polls'])} would-trade "
                      f"poll(s) but no outcome — rerun wnba_bref_scrape.py")
            continue
        for th in THRESHOLDS:
            t = canonical_trade(d["polls"], th)
            if not t:
                recs.append({**base, "threshold": th, "traded": False})
                continue
            win = (total > t["strike"]) if t["side"] == "YES" else \
                  (total <= t["strike"])
            recs.append({**base, "threshold": th, "traded": True,
                         "side": t["side"], "strike": t["strike"],
                         "edge": t["edge"], "cost": t["cost"],
                         "E": t["E"], "entry_ts": t["entry_ts"],
                         "entry_period": t.get("entry_period"),
                         "at_halftime": t.get("at_halftime"),
                         "depth_dollars": t.get("depth_dollars"),
                         "depth_contracts_est": t.get("depth_contracts_est"),
                         "win": win,
                         "pnl": round((1.0 - t["cost"]) if win else -t["cost"], 4)})

    df = pd.DataFrame(recs)
    os.makedirs(os.path.dirname(PANEL), exist_ok=True)
    df.to_csv(PANEL, index=False)
    print(f"[reconcile] panel -> {PANEL}  ({len(df)} row(s))")

    games = df["event"].nunique() if len(df) else 0
    resolved = df[df.realized_total.notna()]["event"].nunique() if len(df) else 0
    print(f"\n  games resolved {resolved}/{games + len(unresolved)}"
          f"   unresolved {len(unresolved)}")
    if len(df) and df.get("traded") is not None and df["traded"].any():
        print("\n  M3 — would-trade ladder (canonical: first armed poll, "
              "best rung)\n")
        print(f"  {'min edge':>9} {'games':>6} {'hit':>7} {'P&L (1ct)':>10} "
              f"{'ROI':>8}")
        for th in THRESHOLDS:
            s = df[(df.threshold == th) & (df.traded)]
            if not len(s):
                print(f"  {th:>8.0%} {0:>6}       —          —        —")
                continue
            pnl, cost = s.pnl.sum(), s.cost.sum()
            print(f"  {th:>8.0%} {len(s):>6} {s.win.mean():>6.0%} "
                  f"{pnl:>+10.2f} {pnl / cost if cost else 0:>+8.1%}")
        d8 = df[(df.threshold == 0.08) & (df.traded) &
                (df.depth_contracts_est.notna())]
        if len(d8):
            ok = (d8.depth_contracts_est >= 5).mean()
            print(f"\n  M1/F1 — depth at the >=8c would-trade price: "
                  f"median {d8.depth_contracts_est.median():,.0f} contracts est"
                  f" ({d8.depth_dollars.median():,.0f} dollars), "
                  f">=5 in {ok:.0%} of {len(d8)} halftime(s)")
    else:
        print("\n  no would-trade rows logged yet — the model arms only at "
              "halftime, so this stays empty until a monitored game reaches "
              "the break.")
    if unresolved:
        print(f"\n  UNRESOLVED events ({len(unresolved)}): "
              + ", ".join(u["event"] for u in unresolved[:6])
              + (" ..." if len(unresolved) > 6 else ""))
    print("\n[reconcile] done. Panel is read-only output; logs untouched.")
    return df


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else OUT_DIR)
