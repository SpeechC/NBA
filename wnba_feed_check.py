"""
===============================================================================
 WNBA SCORE-FEED VALIDATION                                  SINGLE-FILE / SPYDER
===============================================================================
 Run with F5. No arguments. Read the PASS/FAIL lines at the end.

 Purpose: the log-only halftime monitor needs a live score feed. The WNBA CDN
 endpoints are blocked from the development sandbox, so whether they work from
 YOUR machine/network decides the monitor's primary input. This script tests
 every candidate endpoint and, if a game is live while you run it, measures
 feed freshness.

 What it checks
   1  season schedule JSON        (game list + tip times -> the daily slate)
   2  today's scoreboard JSON     (live period/clock/score -> halftime trigger)
   3  one boxscore JSON           (per-period scores -> H1 construction)
   4  feed freshness              (only meaningful during a live game)
   5  fallbacks                   (stats.wnba.com variants)

 Interpreting results
   - Checks 1-3 PASS  -> the monitor can run as specced; send me the output.
   - Scoreboard FAILS but schedule PASSES -> monitor can run with degraded
     halftime detection (poll boxscores); send output, I will adjust the spec.
   - Everything FAILS -> your network is walled like the sandbox; we fall back
     to a paid/alternate feed decision before building.
===============================================================================
"""
import datetime as dt
import json
import time

import requests

HDR = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36"),
       "Referer": "https://www.wnba.com/",
       "Origin": "https://www.wnba.com",
       "Accept": "application/json, text/plain, */*",
       "Accept-Language": "en-US,en;q=0.9"}

results = []


def check(name, url, probe):
    """probe(json_dict) -> summary string, or raise."""
    try:
        r = requests.get(url, headers=HDR, timeout=25)
        body = r.text.strip()
        if r.status_code != 200:
            results.append((name, False, f"HTTP {r.status_code}"))
            return None
        if not body.startswith("{") and not body.startswith("["):
            results.append((name, False,
                            f"200 but NOT JSON ({len(body)}b — likely a WAF page)"))
            return None
        js = r.json()
        summary = probe(js)
        results.append((name, True, summary))
        return js
    except Exception as ex:                                   # noqa: BLE001
        results.append((name, False, f"{type(ex).__name__}: {ex}"))
        return None


# ---- 1. season schedule ------------------------------------------------------
def probe_sched(js):
    gd = js["leagueSchedule"]["gameDates"]
    n = sum(len(x["games"]) for x in gd)
    g = next(g for x in gd for g in x["games"])
    tip = g.get("gameDateTimeEst") or g.get("gameDateTimeUTC") or "??"
    return (f"{len(gd)} dates, {n} games; sample "
            f"{g['awayTeam']['teamTricode']}@{g['homeTeam']['teamTricode']} "
            f"tip={tip}")


sched = check("1 schedule",
              "https://cdn.wnba.com/static/json/staticData/scheduleLeagueV2_1.json",
              probe_sched)

# ---- 2. today's scoreboard ---------------------------------------------------
def probe_board(js):
    sb = js.get("scoreboard", {})
    games = sb.get("games", [])
    if not games:
        return f"reachable; no games listed today ({sb.get('gameDate','?')})"
    g = games[0]
    return (f"{len(games)} game(s); sample status='{g.get('gameStatusText')}' "
            f"period={g.get('period')} clock='{g.get('gameClock')}' "
            f"{g['awayTeam']['teamTricode']} {g['awayTeam'].get('score')} @ "
            f"{g['homeTeam']['teamTricode']} {g['homeTeam'].get('score')}")


board = check("2 scoreboard",
              "https://cdn.wnba.com/static/json/liveData/scoreboard/todaysScoreboard_10.json",
              probe_board)

# ---- 3. one boxscore (needs a gameId; take today's or a recent one) ----------
gid = None
if board:
    gs = board.get("scoreboard", {}).get("games", [])
    if gs:
        gid = gs[0].get("gameId")
if not gid and sched:
    # most recent past game from the schedule
    today = dt.date.today().isoformat()
    past = [g for x in sched["leagueSchedule"]["gameDates"] for g in x["games"]
            if str(g.get("gameDateTimeEst", ""))[:10] <= today]
    if past:
        gid = past[-1].get("gameId")

if gid:
    def probe_box(js):
        game = js["game"]
        hp = game["homeTeam"].get("periods", [])
        per = [(p.get("period"), p.get("score")) for p in hp]
        return f"gameId {gid}; home periods {per}"
    check("3 boxscore",
          f"https://cdn.wnba.com/static/json/liveData/boxscore/boxscore_{gid}.json",
          probe_box)
else:
    results.append(("3 boxscore", False, "no gameId available to test"))

# ---- 4. freshness (only if a game is LIVE right now) -------------------------
live = []
if board:
    live = [g for g in board.get("scoreboard", {}).get("games", [])
            if g.get("gameStatus") == 2]           # 2 = in progress
if live:
    g0 = live[0]["gameId"]
    print(f"\nlive game detected ({g0}) — sampling clock twice, 30s apart ...")
    t1 = check("4 freshness poll A",
               f"https://cdn.wnba.com/static/json/liveData/boxscore/boxscore_{g0}.json",
               lambda js: f"clock {js['game'].get('gameClock')} period {js['game'].get('period')}")
    time.sleep(30)
    t2 = check("4 freshness poll B",
               f"https://cdn.wnba.com/static/json/liveData/boxscore/boxscore_{g0}.json",
               lambda js: f"clock {js['game'].get('gameClock')} period {js['game'].get('period')}")
    if t1 and t2:
        moved = t1["game"].get("gameClock") != t2["game"].get("gameClock")
        results.append(("4 freshness verdict", moved,
                        "clock ADVANCED between polls (feed is live)" if moved
                        else "clock did NOT move in 30s (feed may be delayed)"))
else:
    results.append(("4 freshness", None,
                    "no game live right now — rerun during a game window"))

# ---- 5. fallbacks ------------------------------------------------------------
check("5 fallback stats.wnba",
      "https://stats.wnba.com/stats/scoreboardv3?GameDate="
      + dt.date.today().isoformat() + "&LeagueID=10",
      lambda js: "reachable, keys: " + ",".join(list(js.keys())[:4]))

# ---- report ------------------------------------------------------------------
print("\n" + "=" * 74)
print(" RESULTS — copy this whole block back to the chat")
print("=" * 74)
for name, ok, msg in results:
    flag = "PASS" if ok else ("SKIP" if ok is None else "FAIL")
    print(f"  [{flag}] {name}: {msg}")
need = {n: ok for n, ok, _ in results}
core = [need.get("1 schedule"), need.get("2 scoreboard"), need.get("3 boxscore")]
print("-" * 74)
if all(core):
    print("  VERDICT: core feed WORKS — the monitor can be built as specced.")
elif need.get("1 schedule"):
    print("  VERDICT: partial — schedule OK, live path degraded. Send output.")
else:
    print("  VERDICT: walled from this network too. Send output; we choose a"
          " fallback feed before building.")
