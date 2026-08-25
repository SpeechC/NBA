"""ESPN WNBA live-score feed check — run in Spyder (F5), paste output back.
Best run during a live game; off-hours still answers the access question."""
import datetime as dt
import time

import requests

HDR = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36"),
       "Accept": "application/json"}
URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard"

try:
    r = requests.get(URL, headers=HDR, timeout=25)
    body = r.text.strip()
    if r.status_code != 200 or not body.startswith("{"):
        print(f"[FAIL] HTTP {r.status_code}, {len(body)}b"
              + (" — non-JSON (WAF page?)" if body else ""))
    else:
        js = r.json()
        evs = js.get("events", [])
        print(f"[PASS] scoreboard reachable — {len(evs)} game(s) listed "
              f"({js.get('day', {}).get('date', '?')})")
        for e in evs:
            comp = e["competitions"][0]
            st = comp["status"]
            teams = {c["homeAway"]: c for c in comp["competitors"]}
            def half(c):
                ls = c.get("linescores", [])
                return sum(int(float(x.get("value", 0))) for x in ls[:2]) if ls else None
            print(f"   {teams['away']['team']['abbreviation']} "
                  f"{teams['away'].get('score')} @ "
                  f"{teams['home']['team']['abbreviation']} "
                  f"{teams['home'].get('score')}  | "
                  f"period {st.get('period')} clock '{st.get('displayClock')}' "
                  f"state {st['type'].get('state')}  | "
                  f"H1(away/home) {half(teams['away'])}/{half(teams['home'])}")
        live = [e for e in evs
                if e["competitions"][0]["status"]["type"].get("state") == "in"]
        if live:
            print("\nlive game found — freshness check, 30s apart:")
            c1 = live[0]["competitions"][0]["status"].get("displayClock")
            time.sleep(30)
            r2 = requests.get(URL, headers=HDR, timeout=25).json()
            e2 = next(e for e in r2["events"] if e["id"] == live[0]["id"])
            c2 = e2["competitions"][0]["status"].get("displayClock")
            print(f"   clock {c1} -> {c2}  "
                  f"{'[PASS] LIVE' if c1 != c2 else '[WARN] unchanged in 30s'}")
        else:
            print("\n(no game live now — rerun during a game for freshness)")
except Exception as ex:                                    # noqa: BLE001
    print(f"[FAIL] {type(ex).__name__}: {ex}")
