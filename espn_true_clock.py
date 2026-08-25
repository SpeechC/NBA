"""
===============================================================================
 GROUND-TRUTH GAME CLOCKS FROM ESPN PLAY-BY-PLAY
===============================================================================
 Both halftime audits rest on INFERRED clocks: the WNBA on a settled-price
 anchor, the NBA on a scheduled tipoff plus a swept offset. Neither is truth,
 and the corrected WNBA anchor was partly chosen because it produced
 theoretically tidy coefficients — which is close to fitting the answer.

 ESPN's summary endpoint carries a `wallclock` UTC stamp on every play, so the
 real tipoff (first period-1 play) and the real halftime buzzer (last period-2
 play) are directly observable. This fetches them so the audits can be checked
 against fact instead of inference.

 Caches to espn_clocks_{league}.csv; re-running only fetches what is missing.
===============================================================================
"""
import os
import sys
import time

import pandas as pd
from curl_cffi import requests as cr

BASE = "https://site.api.espn.com/apis/site/v2/sports/basketball"
REPO = os.path.dirname(os.path.abspath(__file__))


def get(url, params, tries=3):
    for i in range(tries):
        try:
            r = cr.get(url, params=params, impersonate="chrome", timeout=30)
            if r.status_code == 200 and r.text.strip().startswith("{"):
                return r.json()
        except Exception:                                   # noqa: BLE001
            pass
        time.sleep(1.5 * (i + 1))
    return None


def scoreboard_ids(league, dates):
    """-> DataFrame[espn_id, date, away, home, sched_utc]"""
    rows = []
    for d in dates:
        js = get(f"{BASE}/{league}/scoreboard", {"dates": d, "limit": 100})
        if not js:
            print(f"  [warn] scoreboard {d} failed")
            continue
        for e in js.get("events", []):
            c = e["competitions"][0]
            t = {x["homeAway"]: x["team"] for x in c["competitors"]}
            rows.append({"espn_id": e["id"], "date": d,
                         "away": t["away"].get("abbreviation"),
                         "home": t["home"].get("abbreviation"),
                         "sched_utc": e.get("date")})
        time.sleep(0.3)
    return pd.DataFrame(rows)


def game_clock(espn_id, league):
    """-> (tip_utc, half_utc) from play wallclocks, or (None, None)."""
    js = get(f"{BASE}/{league}/summary", {"event": espn_id})
    if not js:
        return None, None
    plays = js.get("plays") or []
    p1 = [p for p in plays if (p.get("period") or {}).get("number") == 1
          and p.get("wallclock")]
    p2 = [p for p in plays if (p.get("period") or {}).get("number") == 2
          and p.get("wallclock")]
    if not p1 or not p2:
        return None, None
    return min(p["wallclock"] for p in p1), max(p["wallclock"] for p in p2)


def harvest(league, dates, out):
    path = os.path.join(REPO, out)
    have = pd.read_csv(path) if os.path.exists(path) else pd.DataFrame()
    ids = scoreboard_ids(league, dates)
    print(f"[{league}] {len(ids)} games listed across {len(dates)} dates")
    done = set(have.espn_id.astype(str)) if len(have) else set()
    rows = have.to_dict("records") if len(have) else []
    todo = [r for _, r in ids.iterrows() if str(r.espn_id) not in done]
    print(f"[{league}] fetching play-by-play for {len(todo)} new game(s)")
    for i, r in enumerate(todo, 1):
        tip, half = game_clock(r.espn_id, league)
        rows.append({**r.to_dict(), "tip_utc": tip, "half_utc": half})
        if i % 25 == 0:
            print(f"[{league}] {i}/{len(todo)}", flush=True)
            pd.DataFrame(rows).to_csv(path, index=False)
        time.sleep(0.25)
    d = pd.DataFrame(rows)
    d.to_csv(path, index=False)
    ok = d.tip_utc.notna().sum() if len(d) else 0
    print(f"[{league}] wrote {path}: {len(d)} rows, {ok} with a real clock")
    return d


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "both"
    if which in ("nba", "both"):
        dts = pd.date_range("2025-10-20", "2025-12-23").strftime("%Y%m%d")
        harvest("nba", list(dts), "espn_clocks_nba.csv")
    if which in ("wnba", "both"):
        dts = pd.date_range("2026-04-29", "2026-08-25").strftime("%Y%m%d")
        harvest("wnba", list(dts), "espn_clocks_wnba.csv")
