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
import hashlib
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
PUBLISH_S3 = True                        # push dashboard.html to S3 each poll
S3_BUCKET = "kalshi-strat"               # PUBLIC website bucket — see spec s15
S3_KEY = "dashboard.html"

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, KALSHI_DIR)
sys.path.insert(0, _HERE)                # so wnba_reconcile imports from either home
os.chdir(KALSHI_DIR)
from kalshi_client import KalshiClient          # noqa: E402
from curl_cffi import requests as cr            # noqa: E402

try:                                     # THE canonical rule lives in one place
    from wnba_reconcile import canonical_trade  # noqa: E402
except Exception as _ex:                         # noqa: BLE001
    canonical_trade = None
    print(f"[monitor] wnba_reconcile unavailable ({type(_ex).__name__}) — "
          f"result cards will list every graded row instead of the "
          f"canonical trade. Grading of record is unaffected.")

try:
    import boto3                                # noqa: E402
except Exception:                                # noqa: BLE001
    boto3 = None

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
_S3 = {"client": None, "last_hash": None, "fails": 0, "warned": False}


def publish(html):
    """Push the dashboard to S3. NEVER raises: this component's job is
    logging, and a publish failure must not interrupt polling. Unchanged
    content is skipped, and the object is written no-cache so the hosted copy
    is not served stale."""
    if not PUBLISH_S3:
        return None
    if boto3 is None:
        if not _S3["warned"]:
            print("[monitor] boto3 missing — S3 publish OFF "
                  "(pip install boto3). Local dashboard still written.")
            _S3["warned"] = True
        return None
    h = hashlib.md5(html.encode("utf-8")).hexdigest()
    if h == _S3["last_hash"]:
        return "unchanged"
    try:
        if _S3["client"] is None:
            _S3["client"] = boto3.client("s3")
        _S3["client"].put_object(
            Bucket=S3_BUCKET, Key=S3_KEY, Body=html.encode("utf-8"),
            ContentType="text/html; charset=utf-8",
            CacheControl="no-cache, no-store, must-revalidate")
        _S3["last_hash"] = h
        if _S3["fails"]:
            print(f"[monitor] S3 publish recovered after {_S3['fails']} fail(s)")
        _S3["fails"] = 0
        return "pushed"
    except Exception as ex:                            # noqa: BLE001
        _S3["fails"] += 1
        if _S3["fails"] <= 3 or _S3["fails"] % 20 == 0:
            print(f"[monitor] S3 publish ERR #{_S3['fails']} "
                  f"{type(ex).__name__}: {ex}")
        return "error"


def render_dashboard(events, results=None):
    """events: live dicts with evt/state/pre_L/E/L_now/rows/armed/rec.
    results: settled games -> post-game WIN/LOSS cards. Returns the HTML."""
    results = results or {}
    any_rec = any(e["rec"] for e in events)
    css = ("body{font-family:Consolas,monospace;background:#111;color:#ddd;"
           "margin:20px} table{border-collapse:collapse;margin:8px 0 24px}"
           "td,th{border:1px solid #333;padding:3px 10px;text-align:right}"
           "th{background:#222} "
           ".pos{color:#4dd06a;font-weight:bold} .neg{color:#888}"
           ".hot{background:#173a17} .banner{padding:12px;background:#b3261e;"
           "color:#fff;font-size:20px;font-weight:bold} .ok{background:#1b5e20}"
           " h2{margin:18px 0 2px} .meta{color:#999;font-size:13px}"
           " .win{color:#4dd06a;font-weight:bold} .loss{color:#ff6b6b;"
           "font-weight:bold} .final{border-left:3px solid #444;"
           "padding-left:10px;margin-top:22px}"
           " .tally{padding:8px 12px;background:#1a1a1a;margin:10px 0;"
           "border:1px solid #333}")
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
    # ---- concluded games: WIN/LOSS on what was actually recommended -------
    if results:
        allt = [t for r in results.values() for t in r["trades"]]
        if allt:
            nw = sum(1 for t in allt if t["win"])
            pnl = sum(t["pnl"] for t in allt)
            cls = "win" if pnl >= 0 else "loss"
            h.append(f"<div class='tally'>settled today: <b>{nw}W / "
                     f"{len(allt) - nw}L</b> &nbsp; P&amp;L "
                     f"<span class='{cls}'>{pnl:+.2f}</span> per contract "
                     f"&nbsp;({len(results)} game(s) concluded)</div>")
        else:
            h.append(f"<div class='tally'>{len(results)} game(s) concluded — "
                     f"no wager was recommended in any of them</div>")
    for evt, r in results.items():
        label = ""
        if r["trades"]:
            nw = sum(1 for t in r["trades"] if t["win"])
            nl = len(r["trades"]) - nw
            p = sum(t["pnl"] for t in r["trades"])
            word = "WIN" if nl == 0 else ("LOSS" if nw == 0 else
                                          f"{nw}W/{nl}L")
            cls = "win" if p >= 0 else "loss"
            label = f" &nbsp;<span class='{cls}'>{word} {p:+.2f}</span>"
        ot = f" | OT x{r['n_ot']}" if r.get("n_ot") else ""
        h.append(f"<div class='final'><h2>{r['matchup']} &mdash; FINAL "
                 f"{r['away_pts']}&ndash;{r['home_pts']}{label}</h2>"
                 f"<div class='meta'>{evt} | realized total "
                 f"<b>{r['total']}</b> | H1 {r['h1']} | pre_L "
                 f"{r['pre_L'] if r['pre_L'] else '-'}{ot}</div>")
        if not r["trades"]:
            h.append("<div class='meta'>no wager was recommended — nothing "
                     "to grade</div></div>")
            continue
        h.append("<table><tr><th>min edge</th><th>side</th><th>strike</th>"
                 "<th>entry</th><th>cost</th><th>edge</th><th>result</th>"
                 "<th>P&amp;L</th></tr>")
        for t in sorted(r["trades"], key=lambda x: x["threshold"]):
            cls = "win" if t["win"] else "loss"
            word = "WIN" if t["win"] else "LOSS"
            h.append(f"<tr><td>{t['threshold']:.0%}</td><td>{t['side']}</td>"
                     f"<td>{t['strike']}</td>"
                     f"<td>{str(t.get('entry_ts', ''))[11:19]}</td>"
                     f"<td>{t['cost']:.2f}</td><td>{t['edge']:+.3f}</td>"
                     f"<td class='{cls}'>{word}</td>"
                     f"<td class='{cls}'>{t['pnl']:+.2f}</td></tr>")
        h.append("</table></div>")
    html = "".join(h)
    with open(DASH, "w", encoding="utf-8") as fh:
        fh.write(html)
    return html


def p_over(E, K):
    return 1.0 - np.searchsorted(RESID, K - E, side="right") / len(RESID)


def fee(p):
    return 0.07 * p * (1 - p)


def depth_at(rung, side):
    """Resting size a taker would lift: YES lifts the NO book, NO the YES book.

    The API serves only `orderbook_fp` (`*_dollars`), so sizes are dollar
    amounts, not contract counts — they are not integers. Both the raw figure
    and a contracts estimate are recorded; the unit ruling F1 needs is left
    open deliberately (spec s14). At F1's 5-contract bar either reading
    passes by three orders of magnitude, so it does not gate grading.
    """
    book = rung["book_no_top"] if side == "YES" else rung["book_yes_top"]
    if not book:
        return None, None
    px, sz = float(book[0][0]), float(book[0][1])
    return sz, (round(sz / px, 1) if px > 0 else None)


def grade(side, strike, cost, total):
    """Kalshi KXWNBATOTAL: YES pays iff total > floor_strike. Verified on
    1,345 settled 2026 markets, 100% agreement; all strikes are .5 (no ties).
    Returns (win, pnl_per_contract) with cost already fee-inclusive."""
    win = (total > strike) if side == "YES" else (total <= strike)
    return win, round((1.0 - cost) if win else -cost, 4)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    c = KalshiClient()
    c.probe_base_urls()
    t0 = time.time()
    idle_since = None
    pre_L = {}                 # event_ticker -> pregame L (frozen at first live)
    session = {}               # event_ticker -> {gid, would[], settled}
    results = {}               # event_ticker -> settled card (WIN/LOSS display)
    pre_missed = set()         # events seen first AFTER tip -> never armed
    pre_prov = {}              # event_ticker -> rolling pregame L (s17)

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
        # ---- settlement (spec s6) -------------------------------------------
        # Runs BEFORE the market check: a game finalizes after its market has
        # left the open list, so this is the only pass that can still see it.
        for evt, sess in session.items():
            if sess["settled"]:
                continue
            gm = games.get(sess["gid"])
            if not gm or (gm.get("away_pts") is None):
                continue
            if not str(gm.get("status", "")).lower().startswith("final"):
                continue
            total = int(gm["away_pts"]) + int(gm["home_pts"])
            graded = []
            for w in sess["would"]:
                win, pnl = grade(w["side"], w["strike"], w["cost"], total)
                graded.append({**w, "win": win, "pnl": pnl})
            loop_rows.append({
                "type": "settlement", "event": evt, "gid": sess["gid"],
                "realized_total": total, "away_pts": gm["away_pts"],
                "home_pts": gm["home_pts"], "h1": gm.get("h1"),
                "n_ot": max(0, (gm.get("period") or 4) - 4),
                "pre_L": pre_L.get(evt), "final_status": gm.get("status"),
                "n_would_trade": len(graded), "would_trade_graded": graded})
            sess["settled"] = True
            # Post-game card: the CANONICAL trade per threshold (the same rule
            # the grader of record uses), so the dashboard and the panel can
            # never disagree about what was recommended or how it did.
            cards = []
            if canonical_trade:
                for th in THRESHOLDS:
                    t = canonical_trade(sess["would"], th)
                    if not t:
                        continue
                    win, pnl = grade(t["side"], t["strike"], t["cost"], total)
                    cards.append({**t, "win": win, "pnl": pnl})
            else:
                cards = graded
            results[evt] = {
                "matchup": f"{gm.get('away_city')} @ {gm.get('home_city')}",
                "away_pts": gm["away_pts"], "home_pts": gm["home_pts"],
                "total": total, "h1": gm.get("h1"), "pre_L": pre_L.get(evt),
                "n_ot": max(0, (gm.get("period") or 4) - 4), "trades": cards}
            print(f"[monitor] SETTLED {evt}: total {total}, "
                  f"{len(graded)} would-trade row(s) graded, "
                  f"{len(cards)} canonical trade(s) on the board")
        unsettled = sum(1 for s in session.values() if not s["settled"])
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
            if loop_rows:                     # never drop a settlement row
                with open(path, "a") as f:
                    for row in loop_rows:
                        row.update({"ts_utc": dt.datetime.utcnow().isoformat(),
                                    "component_role": COMPONENT_ROLE})
                        f.write(json.dumps(row) + "\n")
            # Keep publishing once every market has closed: this is exactly
            # when the night's WIN/LOSS cards are worth looking at.
            try:
                pub = publish(render_dashboard([], results))
            except Exception as ex:                        # noqa: BLE001
                pub = None
                print(f"[monitor] dashboard ERR {type(ex).__name__}: {ex}")
            print(f"[monitor] {dt.datetime.utcnow().strftime('%H:%M:%S')}Z "
                  f"no open markets  settled {len(results)}"
                  f"{'  unsettled ' + str(unsettled) if unsettled else ''}"
                  f"{'  s3:' + pub if pub else ''}")
            idle_since = idle_since or time.time()
            if unsettled:                     # hold the loop open for finals
                idle_since = time.time()
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
                if gm and gm.get("gid"):
                    session.setdefault(evt, {"gid": gm["gid"], "would": [],
                                             "settled": False})
                if gm:
                    state = {k: gm.get(k) for k in
                             ("gid", "period", "clock", "status",
                              "away_city", "home_city",
                              "away_pts", "home_pts", "h1")}
                    live = (gm.get("period") or 0) >= 1
                    quotes = [(l["strike"], (l["bid"] + l["ask"]) / 2)
                              for l in ladder
                              if l["bid"] is not None and l["ask"] is not None]
                    # ROLLING PREGAME LINE (added 2026-08-29, spec s17).
                    # pre_L is a PREGAME quantity, so take it from the pregame
                    # board instead of waiting for tip. Every pre-tip poll
                    # overwrites a provisional line and the last one standing
                    # is frozen the moment the game goes live. The old rule
                    # froze only at period==1 with the score still 0-0, a
                    # window the 35s poll missed in 4 of the first 6 games --
                    # disqualifying two thirds of the season on poll cadence,
                    # not on any absence of data.
                    if not live and evt not in pre_L:
                        Lp = median_cross(quotes)
                        if Lp is not None:
                            pre_prov[evt] = Lp
                    # LATE-START GUARD (added 2026-08-26, spec s16), retained.
                    # pre_L is frozen once and never recomputed, so a monitor
                    # started after tip would capture a MID-GAME ladder and
                    # label it "pregame", silently poisoning E for the rest of
                    # the night. With no pregame provisional and the game
                    # already under way, mark it and stay disarmed.
                    fresh = ((gm.get("period") or 0) == 1
                             and not (gm.get("away_pts") or 0)
                             and not (gm.get("home_pts") or 0))
                    if live and evt not in pre_L:
                        src = Lp = None
                        if evt in pre_prov:
                            src, Lp = "pregame_last", pre_prov[evt]
                        elif fresh:
                            src, Lp = "tip_0_0", median_cross(quotes)
                        if Lp is not None:
                            pre_L[evt] = Lp
                            f.write(json.dumps({
                                "ts_utc": dt.datetime.utcnow().isoformat(),
                                "type": "pre_L_frozen", "event": evt,
                                "component_role": COMPONENT_ROLE,
                                "pre_L": Lp, "source": src,
                                "period": gm.get("period"),
                                "away_pts": gm.get("away_pts"),
                                "home_pts": gm.get("home_pts")}) + "\n")
                        elif not fresh and evt not in pre_missed:
                            pre_missed.add(evt)
                            # write DIRECTLY to f: loop_rows was already
                            # flushed at the top of this with-block, so an
                            # append here would be silently discarded on the
                            # next iteration (the v2.3 bug -- the guard fired
                            # correctly on 26AUG27GSNY but left no record).
                            f.write(json.dumps({
                                "ts_utc": dt.datetime.utcnow().isoformat(),
                                "type": "pre_L_missed", "event": evt,
                                "component_role": COMPONENT_ROLE,
                                "period": gm.get("period"),
                                "away_pts": gm.get("away_pts"),
                                "home_pts": gm.get("home_pts"),
                                "note": "no pregame ladder captured and game "
                                        "already under way; not armed this "
                                        "session"}) + "\n")
                would = []
                # ARM ONLY INSIDE THE HALFTIME BREAK (fixed 2026-08-26, s16).
                # E = a + b*pre + c*H1 uses the FIRST-half total and never
                # updates, so arming through Q3/Q4 compares a halftime snapshot
                # against a market that has absorbed live scoring. On night 1
                # that produced a 22c phantom edge in Q3 on CHI@CONN while a
                # time-updated version of this same model sat 0.6 pts from the
                # market, and left 733 of 874 graded rows as drift.
                halftime = bool(gm and gm.get("period") == 2 and
                                str(gm.get("status", "")).lower().startswith("half"))
                if gm and gm.get("h1") and evt in pre_L and halftime:
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
                                    d_raw, d_ct = depth_at(l, side)
                                    would.append({"threshold": th, "strike": K,
                                                  "side": side,
                                                  "edge": round(edge, 4),
                                                  "cost": round(cost, 4),
                                                  "E": round(E, 2),
                                                  "at_halftime": halftime,
                                                  "depth_dollars": d_raw,
                                                  "depth_contracts_est": d_ct,
                                                  "period": gm.get("period"),
                                                  "ts_utc": dt.datetime.utcnow()
                                                  .isoformat()})
                                    break
                f.write(json.dumps({
                    "ts_utc": dt.datetime.utcnow().isoformat(),
                    "type": "ladder", "event": evt,
                    "component_role": COMPONENT_ROLE,
                    "pre_L": pre_L.get(evt), "game_state": state,
                    "ladder": ladder, "would_trade": would}) + "\n")
                if would and evt in session:
                    session[evt]["would"].extend(would)
                # ---- dashboard rows (every touchpoint, every poll) ---------
                armed = bool(gm and gm.get("h1") and evt in pre_L and halftime)
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
            pub = publish(render_dashboard(dash_events, results))
        except Exception as ex:                                # noqa: BLE001
            pub = None
            print(f"[monitor] dashboard ERR {type(ex).__name__}: {ex}")
        print(f"[monitor] {dt.datetime.utcnow().strftime('%H:%M:%S')}Z "
              f"{len(by_event)} event(s)  joined "
              f"{sum(1 for e in dash_events if e['state'])}"
              f"{'  settled ' + str(len(results)) if results else ''}"
              f"{'  s3:' + pub if pub else ''}")
        time.sleep(POLL_S)
    print("[monitor] done.")


if __name__ == "__main__":
    main()
