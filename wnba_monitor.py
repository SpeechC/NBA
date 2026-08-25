"""
===============================================================================
 WNBA HALFTIME MONITOR — PHASES A+B (full spec)              SINGLE-FILE / F5
===============================================================================
 COMPONENT_ROLE = OBSERVER. No order-placement code exists here; GET-only.
 Governed by WNBA_PROTOTYPE_SPEC.md. Supersedes wnba_monitor_phaseA.py.

 Adds to Phase A: live scores via the league CDN (curl_cffi Chrome
 impersonation; ESPN fallback), halftime detection, live edge computation
 against the frozen rule, and would_trade logging at the fixed 3/5/8c grid.

 Requires: pip install curl_cffi
===============================================================================
"""
import datetime as dt
import json
import os
import sys
import time

import numpy as np

COMPONENT_ROLE = "OBSERVER"
KALSHI_DIR = r"C:\NBA2\Kalshi" if os.name == "nt" else "/mnt/c/NBA2/Kalshi"
OUT_DIR = r"C:\NBA2\wnba_monitor" if os.name == "nt" else "/mnt/c/NBA2/wnba_monitor"
REPO = (r"C:\NBA2" if os.name == "nt"
        else "/home/dpope/projects/nba_entropy_replication")
SERIES = "KXWNBATOTAL"
POLL_S = 30
MAX_HOURS = 9
IDLE_STOP_MIN = 120
THRESHOLDS = (0.03, 0.05, 0.08)          # labels, not knobs (spec s4)

sys.path.insert(0, KALSHI_DIR)
os.chdir(KALSHI_DIR)
from kalshi_client import KalshiClient          # noqa: E402
from curl_cffi import requests as cr            # noqa: E402

RULE = json.load(open(os.path.join(REPO, "wnba_deploy_rule.json")))
RESID = np.load(os.path.join(REPO, "wnba_deploy_residuals.npy"))
CDN = "https://cdn.wnba.com/static/json/liveData"
CITY2CODE = {}          # scoreboard city -> kalshi event side, learned per day


def fetch_json(url):
    r = cr.get(url, impersonate="chrome", timeout=20)
    if r.status_code != 200 or not r.text.strip().startswith("{"):
        raise RuntimeError(f"HTTP {r.status_code}")
    return r.json()


def scoreboard():
    js = fetch_json(f"{CDN}/scoreboard/todaysScoreboard_10.json")
    return js.get("scoreboard", {}).get("games", [])


def boxscore(gid):
    js = fetch_json(f"{CDN}/boxscore/boxscore_{gid}.json")
    g = js["game"]
    def half(side):
        per = g[side].get("periods", [])
        return sum(int(p.get("score") or 0) for p in per if p.get("period") in (1, 2))
    done2 = all(any(p.get("period") == q and p.get("periodType") == "REGULAR"
                    for p in g["homeTeam"].get("periods", [])) for q in (1, 2))
    return {"gid": gid, "period": g.get("period"),
            "clock": g.get("gameClock"), "status": g.get("gameStatusText"),
            "away_city": g["awayTeam"].get("teamCity"),
            "home_city": g["homeTeam"].get("teamCity"),
            "away_pts": g["awayTeam"].get("score"),
            "home_pts": g["homeTeam"].get("score"),
            "h1": (half("awayTeam") + half("homeTeam"))}


def p_over(E, K):
    return 1.0 - np.searchsorted(RESID, K - E, side="right") / len(RESID)


def fee(p):
    return 0.07 * p * (1 - p)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    c = KalshiClient()
    c.probe_base_urls()
    t0 = time.time()
    idle_since = None
    pre_L = {}                 # event_ticker -> pregame L (frozen at first live)
    ev_city = {}               # event_ticker -> (away_city, home_city)
    print(f"[monitor v2] role={COMPONENT_ROLE} poll={POLL_S}s "
          f"rule=E={RULE['a']:+.2f}+{RULE['b']:.3f}*pre+{RULE['c']:.3f}*H1")
    header = {"ts_utc": dt.datetime.utcnow().isoformat(), "type": "header",
              "component_role": COMPONENT_ROLE, "series": SERIES,
              "frozen_rule": RULE, "thresholds": THRESHOLDS, "poll_s": POLL_S}
    wrote_header = set()
    while time.time() - t0 < MAX_HOURS * 3600:
        day = dt.datetime.utcnow().strftime("%Y%m%d")
        path = os.path.join(OUT_DIR, f"monitor2_{day}.jsonl")
        if day not in wrote_header:
            with open(path, "a") as f:
                f.write(json.dumps(header) + "\n")
            wrote_header.add(day)
        loop_rows = []
        # ---- scores ---------------------------------------------------------
        games = {}
        try:
            for g in scoreboard():
                gid = g.get("gameId")
                if g.get("gameStatus") in (2, 3) and gid:      # live or final
                    try:
                        games[gid] = boxscore(gid)
                    except Exception as ex:                    # noqa: BLE001
                        loop_rows.append({"type": "feed_err", "gid": gid,
                                          "err": str(ex)})
                else:
                    games[gid] = {"gid": gid, "period": g.get("period"),
                                  "status": g.get("gameStatusText"),
                                  "away_city": (g.get("awayTeam") or {}).get("teamCity"),
                                  "home_city": (g.get("homeTeam") or {}).get("teamCity"),
                                  "h1": None}
        except Exception as ex:                                # noqa: BLE001
            loop_rows.append({"type": "feed_err", "gid": None, "err": str(ex)})
        # ---- markets --------------------------------------------------------
        try:
            r = c.get("/markets", {"series_ticker": SERIES, "status": "open",
                                   "limit": 200}) or {}
            ms = r.get("markets", [])
        except Exception as ex:                                # noqa: BLE001
            print(f"[monitor] kalshi ERR {ex}")
            time.sleep(POLL_S)
            continue
        if not ms:
            idle_since = idle_since or time.time()
            if time.time() - idle_since > IDLE_STOP_MIN * 60:
                print("[monitor] idle too long — stopping.")
                break
            time.sleep(POLL_S)
            continue
        idle_since = None
        by_event = {}
        for m in ms:
            by_event.setdefault(m["event_ticker"], []).append(m)
        with open(path, "a") as f:
            for row in loop_rows:
                row.update({"ts_utc": dt.datetime.utcnow().isoformat(),
                            "component_role": COMPONENT_ROLE})
                f.write(json.dumps(row) + "\n")
            for evt, rungs in by_event.items():
                ladder = []
                for m in sorted(rungs, key=lambda x: float(x.get("floor_strike") or 0)):
                    try:
                        resp = c.get(f"/markets/{m['ticker']}/orderbook", {}) or {}
                        ob = resp.get("orderbook_fp") or resp.get("orderbook") or {}
                    except Exception:                          # noqa: BLE001
                        ob = {}
                    yes = sorted(ob.get("yes_dollars") or ob.get("yes") or [],
                                 key=lambda x: float(x[0]), reverse=True)
                    no = sorted(ob.get("no_dollars") or ob.get("no") or [],
                                key=lambda x: float(x[0]), reverse=True)
                    ladder.append({"strike": m.get("floor_strike"),
                                   "bid": float(yes[0][0]) if yes else None,
                                   "ask": round(1 - float(no[0][0]), 4) if no else None,
                                   "book_yes_top": yes[:6], "book_no_top": no[:6]})
                # join a game by city names (learned once per event)
                gm = None
                for g in games.values():
                    ac, hc = g.get("away_city") or "", g.get("home_city") or ""
                    if ac and hc and (ac.upper()[:3] in evt or hc.upper()[:3] in evt):
                        gm = g
                        break
                state = None
                if gm:
                    state = {k: gm.get(k) for k in
                             ("gid", "period", "clock", "status",
                              "away_pts", "home_pts", "h1")}
                    live = (gm.get("period") or 0) >= 1
                    if live and evt not in pre_L:
                        # freeze pregame L: median crossing on current ladder
                        q = [(l["strike"], (l["bid"] + l["ask"]) / 2)
                             for l in ladder
                             if l["bid"] is not None and l["ask"] is not None]
                        if len(q) >= 4:
                            xs = [float(a) for a, _ in q]
                            ps = [b for _, b in q]
                            ab = [i for i, p in enumerate(ps) if p >= 0.5]
                            bl = [i for i, p in enumerate(ps) if p < 0.5]
                            if ab and bl and max(ab) < min(bl):
                                i, j = max(ab), min(bl)
                                pre_L[evt] = xs[i] + (xs[j] - xs[i]) * \
                                    (ps[i] - 0.5) / (ps[i] - ps[j]) \
                                    if ps[i] != ps[j] else xs[i]
                would = []
                halftime = bool(gm and gm.get("period") == 2 and
                                str(gm.get("status", "")).lower().startswith("half"))
                if gm and gm.get("h1") and evt in pre_L and \
                        (halftime or (gm.get("period") or 0) >= 3):
                    E = RULE["a"] + RULE["b"] * pre_L[evt] + RULE["c"] * gm["h1"]
                    for l in ladder:
                        if l["bid"] is None or l["ask"] is None:
                            continue
                        K = float(l["strike"])
                        pt = p_over(E, K)
                        eY = pt - l["ask"] - fee(l["ask"])
                        eN = l["bid"] - pt - fee(l["bid"])
                        for side, edge, cost in (("YES", eY, l["ask"] + fee(l["ask"])),
                                                 ("NO", eN, (1 - l["bid"]) + fee(l["bid"]))):
                            for th in THRESHOLDS:
                                if edge >= th:
                                    would.append({"threshold": th, "strike": K,
                                                  "side": side,
                                                  "edge": round(edge, 4),
                                                  "cost": round(cost, 4),
                                                  "E": round(E, 2),
                                                  "at_halftime": halftime})
                                    break
                f.write(json.dumps({
                    "ts_utc": dt.datetime.utcnow().isoformat(),
                    "type": "ladder", "event": evt,
                    "component_role": COMPONENT_ROLE,
                    "pre_L": pre_L.get(evt), "game_state": state,
                    "ladder": ladder, "would_trade": would}) + "\n")
                if would:
                    print(f"[monitor] {evt}: {len(would)} WOULD-TRADE row(s) "
                          f"(E={would[0]['E']}, best edge {max(w['edge'] for w in would):.3f})")
        print(f"[monitor] {dt.datetime.utcnow().strftime('%H:%M:%S')}Z "
              f"{len(by_event)} event(s)  live-joined "
              f"{sum(1 for e in by_event if any((games.get(k) or {}).get('period') for k in games))}")
        time.sleep(POLL_S)
    print("[monitor] done.")


if __name__ == "__main__":
    main()
