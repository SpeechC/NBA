"""Fetch NBA tip-off times 2017-2026 from ESPN's dated scoreboard.

The vendor master file has no time-of-day column. ESPN returns event `date` in
UTC; local arena time is derived later. Monthly ranges (~70 requests total).
Writes tipoffs_espn_tv.csv. Reference data acquisition only - no outcome is used.
"""
import sys
import time

import pandas as pd
from curl_cffi import requests as rq

URL = ("https://site.api.espn.com/apis/site/v2/sports/basketball/nba/"
       "scoreboard?dates={a}-{b}&limit=1000")

months = []
for y in range(2017, 2027):
    for m in range(1, 13):
        if m in (7, 8, 9):            # no NBA games
            continue
        if (y, m) < (2017, 10) or (y, m) > (2026, 6):
            continue
        last = pd.Timestamp(year=y, month=m, day=1) + pd.offsets.MonthEnd(0)
        months.append((f"{y}{m:02d}01", last.strftime("%Y%m%d")))

rows, seen = [], set()
for i, (a, b) in enumerate(months, 1):
    for attempt in range(4):
        try:
            js = rq.get(URL.format(a=a, b=b), impersonate="chrome", timeout=45).json()
            break
        except Exception as ex:                                   # noqa: BLE001
            if attempt == 3:
                print(f"  [ERR] {a} {type(ex).__name__}", flush=True)
                js = {}
            time.sleep(2 * (attempt + 1))
    for e in js.get("events", []):
        if e["id"] in seen:
            continue
        seen.add(e["id"])
        c = e["competitions"][0]
        tm = {t["homeAway"]: t for t in c["competitors"]}
        if "home" not in tm or "away" not in tm:
            continue
        rows.append({
            "espn_id": e["id"], "utc": e["date"],
            "home_abbr": tm["home"]["team"].get("abbreviation"),
            "away_abbr": tm["away"]["team"].get("abbreviation"),
            "home_loc": tm["home"]["team"].get("location"),
            "away_loc": tm["away"]["team"].get("location"),
            "home_score": tm["home"].get("score"),
            "away_score": tm["away"].get("score"),
            "type": c.get("type", {}).get("abbreviation"),
            "bc_national": int(any(b.get("market") == "national"
                                   for b in (c.get("broadcasts") or []))),
            "bc_names": "|".join(
                n for b in (c.get("broadcasts") or [])
                if b.get("market") == "national" for n in (b.get("names") or [])),
            "bc_all": "|".join(
                f"{b.get('market')}:{','.join(b.get('names') or [])}"
                for b in (c.get("broadcasts") or [])),
            "season_type": e.get("season", {}).get("type"),
        })
    print(f"  {i:>2}/{len(months)} {a[:6]}  cum {len(rows):,}", flush=True)

d = pd.DataFrame(rows)
d.to_csv("tipoffs_espn_tv.csv", index=False)
print(f"\nwrote tipoffs_espn_tv.csv  {len(d):,} games")
print(d.groupby(d.utc.str[:4]).bc_national.agg(["size","mean"]).to_string())
