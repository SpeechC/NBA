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
KALSHI_DIR = r"D:\Kalshi" if os.name == "nt" else "/mnt/d/Kalshi"
OUT_DIR = r"D:\Kalshi\wnba_monitor" if os.name == "nt" else "/mnt/d/Kalshi/wnba_monitor"
REPO = r"D:\Kalshi" if os.name == "nt" else "/mnt/d/Kalshi"
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
CITY_CODES = {                   # scoreboard teamCity -> Kalshi ticker code(s)
    "Atlanta": ("ATL",), "Chicago": ("CHI",), "Connecticut": ("CONN",),
    "Dallas": ("DAL",), "Golden State": ("GSV", "GS"), "Indiana": ("IND",),
    "Las Vegas": ("LVA", "LV"), "Los Angeles": ("LAS", "LA"),
    "Minnesota": ("MIN",), "New York": ("NYL", "NY"), "Phoenix": ("PHX",),
    "Portland": ("PDX", "POR"), "Seattle": ("SEA",), "Toronto": ("TOR",),
    "Washington": ("WSH", "WAS")}


def fetch_json(url):
    r = cr.get(url, impersonate="chrome", timeout=20)
    if r.status_code != 200 or not r.text.strip().startswith("{"):
        raise RuntimeError(f"HTTP {r.status_code}")
    return r.json()


def scoreboard():
    js = fetch_json(f"{CDN}/scoreboard/todaysScoreboard_10.json")
    return js.get("scoreboard", {})


def join_game(evt, games, sb_date):
    """Kalshi event -> scoreboard game. Exact away+home code pair on the
    ticker tail (city[:3] prefix as fallback); no join across dates — the CDN
    serves yesterday's slate until it rolls over."""
    tail = evt.rsplit("-", 1)[-1]
    try:
        if sb_date and dt.datetime.strptime(tail[:7], "%y%b%d").date() != \
                dt.datetime.strptime(sb_date[:10], "%Y-%m-%d").date():
            return None
    except ValueError:
        pass
    pair = tail[7:]
    for g in games.values():
        ac, hc = g.get("away_city") or "", g.get("home_city") or ""
        if ac and hc and any(
                a + h == pair
                for a in CITY_CODES.get(ac, (ac.upper()[:3],))
                for h in CITY_CODES.get(hc, (hc.upper()[:3],))):
            return g
    for g in games.values():
        ac, hc = g.get("away_city") or "", g.get("home_city") or ""
        if ac and hc and (ac.upper()[:3] in evt or hc.upper()[:3] in evt):
            return g
    return None


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



def median_cross(pairs):
    """pairs: [(strike, prob), ...] -> implied line at the 0.5 crossing."""
    q=[(float(k),p) for k,p in pairs if p is not None]
    if len(q)<4: return None
    q.sort()
    xs=[a for a,_ in q]; ps=[b for _,b in q]
    ab=[i for i,p in enumerate(ps) if p>=0.5]; bl=[i for i,p in enumerate(ps) if p<0.5]
    if not ab or not bl or max(ab)>min(bl): return None
    i,j=max(ab),min(bl)
    return xs[i] if ps[i]==ps[j] else xs[i]+(xs[j]-xs[i])*(ps[i]-0.5)/(ps[i]-ps[j])


DASH = os.path.join(OUT_DIR, "dashboard.html")

def render_dashboard(events):
    """events: list of dicts with evt/state/pre_L/E/L_now/rows/armed/rec."""
    any_rec = any(e["rec"] for e in events)
    css = ("body{font-family:Consolas,monospace;background:#111;color:#ddd;"
           "margin:20px} table{border-collapse:collapse;margin:8px 0 24px}"
           "td,th{border:1px solid #333;padding:3px 10px;text-align:right}"
           "th{background:#222} "
           ".pos{color:#4dd06a;font-weight:bold} .neg{color:#888}"
           ".hot{background:#173a17} .banner{padding:12px;background:#b3261e;"
           "color:#fff;font-size:20px;font-weight:bold} .ok{background:#1b5e20}"
           " h2{margin:18px 0 2px} .meta{color:#999;font-size:13px}")
    h=[f"<meta charset='utf-8'><meta http-equiv='refresh' content='30'>"
       f"<style>{css}</style>"]
    h.append(f"<div class='banner {'':s}{'' if any_rec else 'ok'}'>"
             + ("&#9888; WAGER RECOMMENDED — see highlighted rows"
                if any_rec else
                "monitoring — no recommendation yet (refreshes every 30s)")
             + "</div>")
    h.append(f"<div class='meta'>updated {dt.datetime.utcnow().isoformat()}Z"
             f" &nbsp;|&nbsp; role OBSERVER (display only, no orders)"
             f" &nbsp;|&nbsp; rule E={RULE['a']:+.2f}+{RULE['b']:.3f}·pre"
             f"+{RULE['c']:.3f}·H1</div>")
    for e in events:
        st=e["state"] or {}
        title=e["evt"]
        if st.get("away_city") and st.get("home_city"):
            title=f"{st['away_city']} @ {st['home_city']}"
            if st.get("away_pts") is not None:
                title+=f" &nbsp;{st['away_pts']}&ndash;{st['home_pts']}"
        h.append(f"<h2>{title}</h2><div class='meta'>"
                 f"{e['evt']} | "
                 f"status {st.get('status') or 'pregame'} | period {st.get('period') or '-'} "
                 f"clock {st.get('clock') or '-'} | score {st.get('away_pts','-')}-"
                 f"{st.get('home_pts','-')} | H1 {st.get('h1') or '-'} | "
                 f"pre_L {e['pre_L'] if e['pre_L'] else '-'} | "
                 + (f"<b>E = {e['E']:.1f}</b> | market L = "
                    f"{e['L_now']:.1f} | <b>deviation L−E = "
                    f"{e['L_now']-e['E']:+.1f} pts</b>" if e["armed"] and e["L_now"]
                    else "model arms at halftime") + "</div>")
        h.append("<table><tr><th>strike</th><th>bid</th><th>ask</th>"
                 "<th>p_true</th><th>mkt p(mid)</th><th>dev pp</th>"
                 "<th>edge YES</th><th>edge NO</th><th>action</th></tr>")
        for r in e["rows"]:
            cls=" class='hot'" if r.get("act") else ""
            def f(v,fmt="{:+.3f}"):
                return "-" if v is None else fmt.format(v)
            h.append(f"<tr{cls}><td>{r['K']}</td><td>{f(r['bid'],'{:.2f}')}</td>"
                     f"<td>{f(r['ask'],'{:.2f}')}</td><td>{f(r['pt'],'{:.3f}')}</td>"
                     f"<td>{f(r['mid'],'{:.3f}')}</td><td>{f(r['dev'],'{:+.1f}')}</td>"
                     f"<td class='{'pos' if (r['eY'] or 0)>0 else 'neg'}'>{f(r['eY'])}</td>"
                     f"<td class='{'pos' if (r['eN'] or 0)>0 else 'neg'}'>{f(r['eN'])}</td>"
                     f"<td>{r.get('act','')}</td></tr>")
        h.append("</table>")
    with open(DASH,"w",encoding="utf-8") as fh: fh.write("".join(h))


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
        sb_date = None
        try:
            sb = scoreboard()
            sb_date = sb.get("gameDate")
            for g in sb.get("games", []):
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
        dash_events = []
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
                gm = join_game(evt, games, sb_date)
                state = None
                if gm:
                    state = {k: gm.get(k) for k in
                             ("gid", "period", "clock", "status",
                              "away_city", "home_city",
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
                # ---- dashboard rows (every touchpoint, every poll) ---------
                armed = bool(gm and gm.get("h1") and evt in pre_L and
                             (halftime or (gm.get("period") or 0) >= 3))
                E_val = (RULE["a"] + RULE["b"]*pre_L[evt] + RULE["c"]*gm["h1"]) \
                        if armed else None
                L_now = median_cross([(l["strike"],
                                       (l["bid"]+l["ask"])/2 if l["bid"] is not None
                                       and l["ask"] is not None else None)
                                      for l in ladder])
                drows=[]
                for l in ladder:
                    K=float(l["strike"]); bid,ask=l["bid"],l["ask"]
                    mid=(bid+ask)/2 if bid is not None and ask is not None else None
                    pt=p_over(E_val,K) if armed else None
                    eY=(pt-ask-fee(ask)) if (armed and ask is not None) else None
                    eN=(bid-pt-fee(bid)) if (armed and bid is not None) else None
                    act=""
                    for th in THRESHOLDS[::-1]:
                        if eY is not None and eY>=th: act=f"BUY YES @{ask:.2f} (edge {eY:.2f})"
                        elif eN is not None and eN>=th: act=f"BUY NO @{1-bid:.2f} (edge {eN:.2f})"
                        if act: break
                    drows.append({"K":K,"bid":bid,"ask":ask,"pt":pt,"mid":mid,
                                  "dev":100*(mid-pt) if (mid is not None and pt is not None) else None,
                                  "eY":eY,"eN":eN,"act":act})
                dash_events.append({"evt":evt,"state":state,"pre_L":pre_L.get(evt),
                                    "armed":armed,"E":E_val,"L_now":L_now,
                                    "rows":drows,"rec":any(r["act"] for r in drows)})
                if would:
                    print(f"[monitor] {evt}: {len(would)} WOULD-TRADE row(s) "
                          f"(E={would[0]['E']}, best edge {max(w['edge'] for w in would):.3f})")
        try:
            render_dashboard(dash_events)
        except Exception as ex:                                # noqa: BLE001
            print(f"[monitor] dashboard ERR {type(ex).__name__}: {ex}")
        print(f"[monitor] {dt.datetime.utcnow().strftime('%H:%M:%S')}Z "
              f"{len(by_event)} event(s)  joined "
              f"{sum(1 for e in dash_events if e['state'])}")
        time.sleep(POLL_S)
    print("[monitor] done.")


if __name__ == "__main__":
    main()
