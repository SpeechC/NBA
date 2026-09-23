"""Fetch today's NBA totals/spreads from The Odds API -> openers_YYYY-MM-DD.csv.

    python nba_openers.py --probe            # connectivity + mapping check, writes nothing
    python nba_openers.py --date 2026-10-21  # write the openers CSV

Unblocks PaceGap and MOVE_COMBINED, which both settle against the sportsbook
opening total and cannot be run without it.

=============================================================================
THIS IS "THE LINE AT CAPTURE TIME", NOT LITERALLY THE OPENER
=============================================================================
The Odds API serves CURRENT odds; it does not serve opening numbers. A 09:00 ET
capture is the earliest practical observation and is what
PREREG_2026_27_PROSPECTIVE D2 anticipates -- which is exactly why it requires
`open_obtained_at_utc`: the prereg needs to know the number preceded our
information, and INJURY_TIMING_AUDIT found 42% of injury reports arrive on game
day. Every row is stamped with the real observation time and
`open_line_source`. Do not backfill this file later in the day and call it an
opener.

=============================================================================
TEAM NAMING IS THE SILENT FAILURE MODE
=============================================================================
The Odds API says "Los Angeles Clippers"; dfMaster says "LA Clippers".
"Portland Trail Blazers" is two nickname words, not one. A strip-the-last-word
heuristic silently drops those games -- and a dropped game is indistinguishable
from a game with no line.

So the map below is EXPLICIT and all 30 entries are validated against
team_mapping.csv at import. An unmapped team is a hard error, never a skip.
This is the same failure class as the `JT Orr` / `J.T. Orr` bug that mis-scored
a real CrewShock slate.
"""
import os, sys, csv, json, argparse, datetime as dt
import statistics as stats

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get("NBA_PROJECT_DIR", "/home/dpope/projects/nba_entropy_replication")
CONFIG = os.path.join(HERE, "odds_config.json")
API = "https://api.the-odds-api.com/v4/sports/basketball_nba/odds/"

# The Odds API full name -> dfMaster / team_mapping.csv bigdataball_name
ODDS_TO_BDB = {
    "Atlanta Hawks": "Atlanta",            "Boston Celtics": "Boston",
    "Brooklyn Nets": "Brooklyn",           "Charlotte Hornets": "Charlotte",
    "Chicago Bulls": "Chicago",            "Cleveland Cavaliers": "Cleveland",
    "Dallas Mavericks": "Dallas",          "Denver Nuggets": "Denver",
    "Detroit Pistons": "Detroit",          "Golden State Warriors": "Golden State",
    "Houston Rockets": "Houston",          "Indiana Pacers": "Indiana",
    "Los Angeles Clippers": "LA Clippers", "Los Angeles Lakers": "LA Lakers",
    "Memphis Grizzlies": "Memphis",        "Miami Heat": "Miami",
    "Milwaukee Bucks": "Milwaukee",        "Minnesota Timberwolves": "Minnesota",
    "New Orleans Pelicans": "New Orleans", "New York Knicks": "New York",
    "Oklahoma City Thunder": "Oklahoma City", "Orlando Magic": "Orlando",
    "Philadelphia 76ers": "Philadelphia",  "Phoenix Suns": "Phoenix",
    "Portland Trail Blazers": "Portland",  "Sacramento Kings": "Sacramento",
    "San Antonio Spurs": "San Antonio",    "Toronto Raptors": "Toronto",
    "Utah Jazz": "Utah",                   "Washington Wizards": "Washington",
}


def api_key():
    k = os.environ.get("ODDS_API_KEY")
    if k:
        return k, "env"
    if os.path.exists(CONFIG):
        try:
            k = json.load(open(CONFIG)).get("odds_api_key")
            if k:
                return k, os.path.basename(CONFIG)
        except Exception as e:
            raise RuntimeError(f"{CONFIG} unreadable: {e}")
    raise RuntimeError(f"no ODDS_API_KEY in env and no key in {CONFIG}")


def validate_mapping():
    """Every dfMaster team must be reachable. Offline; runs without the API."""
    p = os.path.join(ROOT, "team_mapping.csv")
    with open(p) as f:
        bdb = {r["bigdataball_name"].strip() for r in csv.DictReader(f)}
    mapped = set(ODDS_TO_BDB.values())
    missing = sorted(bdb - mapped)
    extra = sorted(mapped - bdb)
    dupes = [v for v in mapped if list(ODDS_TO_BDB.values()).count(v) > 1]
    return {"bdb_teams": len(bdb), "mapped": len(mapped),
            "unreachable": missing, "not_in_dfmaster": extra, "duplicates": sorted(set(dupes))}


def fetch(regions="us", books=None, timeout=25):
    import requests
    k, src = api_key()
    r = requests.get(API, params={"apiKey": k, "regions": regions,
                                  "markets": "totals,spreads",
                                  "oddsFormat": "american"}, timeout=timeout)
    quota = {"used": r.headers.get("x-requests-used"),
             "remaining": r.headers.get("x-requests-remaining")}
    if r.status_code != 200:
        try:
            msg = r.json()
        except Exception:
            msg = r.text[:300]
        raise RuntimeError(f"HTTP {r.status_code} (key from {src}): {msg}")
    return r.json(), quota, src


def _consensus(event, books=None):
    """Median total and median home spread across books.

    Median, not a single book: one book posting a stale or outlying number
    moves a single-book capture by a full point, and the strategies' whole
    margins are 0.06-0.8 points. The contributing book count is recorded so a
    thin consensus is visible rather than silent.
    """
    tot, spr, used = [], [], []
    home = event.get("home_team")
    for b in event.get("bookmakers", []):
        if books and b.get("key") not in books:
            continue
        got = False
        for m in b.get("markets", []):
            if m.get("key") == "totals":
                pts = [o.get("point") for o in m.get("outcomes", []) if o.get("point") is not None]
                if pts:
                    tot.append(float(pts[0])); got = True
            elif m.get("key") == "spreads":
                for o in m.get("outcomes", []):
                    if o.get("name") == home and o.get("point") is not None:
                        spr.append(float(o["point"])); got = True
        if got:
            used.append(b.get("key"))
    return (stats.median(tot) if tot else None,
            stats.median(spr) if spr else None,
            len(tot), len(spr), used)


def build(day=None, out=None, regions="us", books=None, probe=False):
    day = day or dt.date.today().isoformat()
    v = validate_mapping()
    print(f"team mapping: {v['mapped']}/{v['bdb_teams']} dfMaster teams reachable")
    for k_, lbl in (("unreachable", "NOT REACHABLE FROM THE ODDS API"),
                    ("not_in_dfmaster", "mapped to a name dfMaster does not use"),
                    ("duplicates", "duplicate targets")):
        if v[k_]:
            print(f"  *** {lbl}: {v[k_]}")
    if v["unreachable"] or v["not_in_dfmaster"] or v["duplicates"]:
        print("HARD STOP: fix ODDS_TO_BDB before fetching.")
        return 2

    try:
        events, quota, src = fetch(regions, books)
    except Exception as e:
        print(f"FAIL {e}")
        if "DEACTIVATED" in str(e).upper():
            print("  The key is recognised but the subscription is inactive.")
            print("  Reactivate at the-odds-api.com, or drop an openers CSV manually.")
        return 2
    print(f"API ok (key from {src})   quota used {quota['used']} remaining {quota['remaining']}")
    print(f"events returned: {len(events)}")

    now = dt.datetime.now(dt.timezone.utc)
    rows, skipped = [], []
    for e in events:
        ct = e.get("commence_time", "")
        try:
            tip = dt.datetime.fromisoformat(ct.replace("Z", "+00:00"))
        except Exception:
            skipped.append((e.get("id"), f"bad commence_time {ct!r}")); continue
        # bucket by US Eastern game date, which is how dfMaster dates a game
        gday = (tip - dt.timedelta(hours=5)).date().isoformat()
        if gday != day:
            continue
        h, a = e.get("home_team"), e.get("away_team")
        if h not in ODDS_TO_BDB or a not in ODDS_TO_BDB:
            skipped.append((f"{a} @ {h}", "UNMAPPED TEAM NAME")); continue
        total, spread, nt, ns, used = _consensus(e, books)
        if total is None or spread is None:
            skipped.append((f"{a} @ {h}", f"no {'total' if total is None else 'spread'} quoted"))
            continue
        rows.append({"team_h": ODDS_TO_BDB[h], "team_r": ODDS_TO_BDB[a],
                     "open_total": total, "open_spread": spread,
                     "obtained_at_utc": now.isoformat(timespec="seconds"),
                     "open_line_source": f"oddsapi-median-{nt}books",
                     "n_books_total": nt, "n_books_spread": ns,
                     "commence_time": ct})

    print(f"games on {day}: {len(rows)}   skipped: {len(skipped)}")
    for k_, why in skipped[:8]:
        print(f"  SKIP {k_}: {why}")
    if any(w == "UNMAPPED TEAM NAME" for _, w in skipped):
        print("HARD STOP: an unmapped team name is a dropped game, and a dropped")
        print("  game is indistinguishable from a game with no line. Fix ODDS_TO_BDB.")
        return 2
    if not rows:
        print("no games -- nothing written (this is normal on a dark day)")
        return 0
    thin = [r for r in rows if r["n_books_total"] < 3]
    if thin:
        print(f"  note: {len(thin)} game(s) priced by fewer than 3 books")
    if probe:
        print("\n--probe: writing nothing. Sample:")
        for r in rows[:5]:
            print(f"  {r['team_r']:<14} @ {r['team_h']:<14} total {r['open_total']:>6.1f}"
                  f"  spread {r['open_spread']:>+6.1f}  ({r['n_books_total']} books)")
        return 0

    out = out or os.path.join(ROOT, f"openers_{day}.csv")
    cols = ["team_h", "team_r", "open_total", "open_spread", "obtained_at_utc",
            "open_line_source", "n_books_total", "n_books_spread", "commence_time"]
    if os.path.exists(out):
        print(f"REFUSING to overwrite {out} -- an opener is an immutable observation.")
        print(f"  Delete it deliberately if the first capture was wrong.")
        return 2
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, cols); w.writeheader(); w.writerows(rows)
    print(f"wrote {out}  ({len(rows)} games)")

    # SECOND FORMAT, deliberately not the same file. capture_openers.py wants
    # team_h,team_r,open_total,open_spread with dfMaster FULL NAMES;
    # move_combined_live.py --lines wants game_date,away_abbr,home_abbr,open_total
    # with ABBREVIATIONS. Feeding one the other's file fails with KeyError:
    # 'game_date' -- which is a loud failure, but only after the phase has
    # already run, so both are written up front.
    try:
        with open(os.path.join(ROOT, "team_mapping.csv")) as f:
            abbr = {r["bigdataball_name"].strip(): r["abbr"].strip()
                    for r in csv.DictReader(f)}
        lines_out = os.path.join(ROOT, f"lines_{day}.csv")
        miss = sorted({t for r in rows for t in (r["team_h"], r["team_r"])} - set(abbr))
        if miss:
            print(f"  WARN no abbreviation for {miss}; MOVE_COMBINED lines not written")
        else:
            with open(lines_out, "w", newline="") as f:
                w = csv.DictWriter(f, ["game_date", "away_abbr", "home_abbr", "open_total"])
                w.writeheader()
                for r in rows:
                    w.writerow({"game_date": day, "away_abbr": abbr[r["team_r"]],
                                "home_abbr": abbr[r["team_h"]],
                                "open_total": r["open_total"]})
            print(f"wrote {lines_out}  ({len(rows)} games, MOVE_COMBINED format)")
    except Exception as e:
        print(f"  WARN could not write MOVE_COMBINED lines: {e}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--date", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--regions", default="us")
    ap.add_argument("--books", default=None, help="comma-separated book keys; default all")
    ap.add_argument("--probe", action="store_true")
    a = ap.parse_args()
    sys.exit(build(a.date, a.out, a.regions,
                   set(a.books.split(",")) if a.books else None, a.probe))
