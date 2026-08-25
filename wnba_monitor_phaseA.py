"""
===============================================================================
 WNBA HALFTIME MONITOR — PHASE A (Kalshi-only logger)        SINGLE-FILE / F5
===============================================================================
 COMPONENT_ROLE = OBSERVER. Contains no order-placement code; GET-only.
 Governed by WNBA_PROTOTYPE_SPEC.md (sections 5, 6, 12).

 Polls every open KXWNBATOTAL market: full ladder quotes + orderbook depth,
 every POLL_S seconds, until no open markets remain or MAX_HOURS elapses.
 Append-only JSONL, one file per UTC date, in OUT_DIR.

 Run from Spyder (F5) on a game evening, or via nohup. Needs kalshi_client.py
 (KALSHI_DIR) and its credentials.
===============================================================================
"""
import datetime as dt
import json
import os
import sys
import time

COMPONENT_ROLE = "OBSERVER"
KALSHI_DIR = r"C:\NBA2\Kalshi" if os.name == "nt" else "/mnt/c/NBA2/Kalshi"
OUT_DIR = r"C:\NBA2\wnba_monitor" if os.name == "nt" else "/mnt/c/NBA2/wnba_monitor"
SERIES = "KXWNBATOTAL"
POLL_S = 30
MAX_HOURS = 9
IDLE_STOP_MIN = 90          # stop after this long with zero open markets

sys.path.insert(0, KALSHI_DIR)
os.chdir(KALSHI_DIR)        # client reads credentials relative to its dir
from kalshi_client import KalshiClient          # noqa: E402

RULE = {"a": -3.165, "b": 0.5573, "c": 0.9404,  # frozen (spec s11) — logged,
        "note": "E=a+b*pre+c*H1; H1 joins post-hoc"}  # not acted on in Phase A


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    c = KalshiClient()
    c.probe_base_urls()
    t0 = time.time()
    idle_since = None
    print(f"[monitor] Phase A start, series={SERIES}, poll={POLL_S}s, "
          f"role={COMPONENT_ROLE}")
    header = {"ts_utc": dt.datetime.utcnow().isoformat(), "type": "header",
              "component_role": COMPONENT_ROLE, "series": SERIES,
              "frozen_rule": RULE, "poll_s": POLL_S}
    while time.time() - t0 < MAX_HOURS * 3600:
        day = dt.datetime.utcnow().strftime("%Y%m%d")
        path = os.path.join(OUT_DIR, f"monitor_{day}.jsonl")
        if not os.path.exists(path):
            with open(path, "a") as f:
                f.write(json.dumps(header) + "\n")
        try:
            r = c.get("/markets", {"series_ticker": SERIES, "status": "open",
                                   "limit": 200}) or {}
            ms = r.get("markets", [])
        except Exception as ex:                       # noqa: BLE001
            print(f"[monitor] markets ERR {type(ex).__name__}: {ex}")
            time.sleep(POLL_S)
            continue
        if not ms:
            idle_since = idle_since or time.time()
            if time.time() - idle_since > IDLE_STOP_MIN * 60:
                print("[monitor] no open markets for a while — stopping.")
                break
            time.sleep(POLL_S)
            continue
        idle_since = None
        by_event = {}
        for m in ms:
            by_event.setdefault(m["event_ticker"], []).append(m)
        rows = 0
        with open(path, "a") as f:
            for evt, rungs in by_event.items():
                ladder = []
                for m in sorted(rungs, key=lambda x: float(x.get("floor_strike") or 0)):
                    try:
                        ob = (c.get(f"/markets/{m['ticker']}/orderbook", {})
                              or {}).get("orderbook", {}) or {}
                    except Exception:                 # noqa: BLE001
                        ob = {}
                    ladder.append({
                        "strike": m.get("floor_strike"),
                        "bid": m.get("yes_bid"), "ask": m.get("yes_ask"),
                        "last": m.get("last_price"), "vol": m.get("volume"),
                        "book_yes": (ob.get("yes") or [])[:6],
                        "book_no": (ob.get("no") or [])[:6]})
                f.write(json.dumps({
                    "ts_utc": dt.datetime.utcnow().isoformat(),
                    "type": "ladder", "event": evt,
                    "component_role": COMPONENT_ROLE,
                    "ladder": ladder}) + "\n")
                rows += 1
        depth = sum(l0[1] for e in by_event.values() for m0 in [None]
                    for l0 in [])
        print(f"[monitor] {dt.datetime.utcnow().strftime('%H:%M:%S')}Z  "
              f"{len(by_event)} event(s), {len(ms)} rungs logged")
        time.sleep(POLL_S)
    print("[monitor] done.")


if __name__ == "__main__":
    main()
