"""BigDataBall season-to-date team feed -> the game-wide CSV CrewShock reads.

    SOURCE  C:\\Users\\rando\\Dropbox\\26-27-nba-team\\MM-DD-YYYY-nba-season-team-feed.xlsx
    TARGET  C:\\NBA2\\dfMaster_2027.csv          (crewshock_live.CURRENT)

A NEW DATED FILE ARRIVES EACH DAY. This picks the newest one at or before the
as-of date, converts it, and refuses rather than guesses.

=============================================================================
WHY THIS IS A PIVOT, NOT A COPY
=============================================================================
The BigDataBall feed is TEAM-LEVEL: one row per team per game, with a VENUE
column saying which side the row is. `crewshock_live.load_history()` reads
GAME-LEVEL WIDE columns -- PF_H/PF_R, POSS_H/POSS_R, MAIN REF_R, CREW_R,
CREW_H, "REFEREE\\n&\\nUMPIRE_H". So every game's two rows must be folded into
one, with _H and _R suffixes, exactly as dfMaster_OT_2017-2026.csv is shaped.

Getting the fold backwards silently swaps home and road fouls, which flips the
sign of every CrewShock input without erroring.

=============================================================================
THIS FILE FAILS LOUDLY. THAT IS THE POINT.
=============================================================================
CrewShock's recorded failure mode is a SILENT one: `official.nba.com` writes
`JT Orr`, BigDataBall writes `J.T. Orr`, and unmatched that zeroes an
official's entire 60-game history and biases CrewShock toward zero. It
mis-scored a real slate before canonical matching was added.

So this module validates the schema, the pivot, and the staleness, and exits
non-zero on any of them. A missing column is never filled with a default, and
a stale file is never used. Run `--probe` on opening day BEFORE arming
anything: it reports what it found and writes nothing.
"""
import os, re, sys, glob, argparse, datetime as dt
import numpy as np, pandas as pd

FEED_DIR = os.environ.get("NBA_BDB_DIR", "/mnt/c/Users/rando/Dropbox/26-27-nba-team")
TARGET   = os.environ.get("NBA_BDB_TARGET", "/mnt/c/NBA2/dfMaster_2027.csv")
PATTERN  = "*-nba-season-team-feed.xlsx"
MAX_AGE_DAYS = 1          # CREWSHOCK_LIVE_OPS: stale history is a HARD STOP

# team-feed column -> what dfMaster calls it. Values are matched case- and
# whitespace-insensitively; the feed's exact spelling is reported by --probe.
NEED_TEAM = {
    "GAME-ID": ["GAME-ID", "GAME ID", "GAMEID"],
    "DATE":    ["DATE"],
    "TEAM":    ["TEAM"],
    "VENUE":   ["VENUE", "VENUE (R/H)", "H/A", "HOME/AWAY"],
    "PF":      ["PF", "F", "FOULS", "TEAM FOULS"],
    "POSS":    ["POSS", "POSSESSIONS"],
    "PTS":     ["PTS", "POINTS", "FINAL"],
    "CLOSING TOTAL": ["CLOSING TOTAL", "CLOSING_TOTAL", "TOTAL CLOSE"],
    "DATASET": ["DATASET", "BIGDATABALL DATASET"],
}
# referee columns -- BOTH layout eras, because load_history() reads either
NEED_REF = {
    "MAIN REF":   ["MAIN REF", "CREW CHIEF", "REFEREE"],
    "CREW":       ["CREW", "REFEREE & UMPIRE", "UMPIRE"],
    "CREW CHIEF": ["CREW CHIEF", "MAIN REF"],
}
OPTIONAL = {"OPENING TOTAL": ["OPENING TOTAL", "OPENING_TOTAL"],
            "OPPONENT": ["OPPONENT", "OPP"]}


def _norm(s):
    return re.sub(r"\s+", " ", str(s)).strip().upper()


def find_feed(asof=None, feed_dir=None):
    """Newest dated feed at or before `asof`. Returns (path, file_date)."""
    feed_dir = feed_dir or FEED_DIR
    if not os.path.isdir(feed_dir):
        raise FileNotFoundError(f"feed directory not found: {feed_dir}")
    asof = dt.date.fromisoformat(asof) if isinstance(asof, str) else (asof or dt.date.today())
    best = None
    for p in glob.glob(os.path.join(feed_dir, PATTERN)):
        m = re.match(r"^(\d{2})-(\d{2})-(\d{4})-", os.path.basename(p))
        if not m:
            continue
        mm, dd, yyyy = (int(x) for x in m.groups())
        try:
            fd = dt.date(yyyy, mm, dd)
        except ValueError:
            continue
        if fd <= asof and (best is None or fd > best[1]):
            best = (p, fd)
    if best is None:
        raise FileNotFoundError(
            f"no {PATTERN} dated on/before {asof} in {feed_dir}")
    return best


def _resolve(cols, wanted):
    """Map our canonical name -> the feed's actual column, or None."""
    idx = {_norm(c): c for c in cols}
    out = {}
    for canon, aliases in wanted.items():
        hit = next((idx[_norm(a)] for a in aliases if _norm(a) in idx), None)
        out[canon] = hit
    return out


def probe(asof=None, feed_dir=None):
    """Report what the feed contains. WRITES NOTHING. Run this on day one."""
    path, fd = find_feed(asof, feed_dir)
    raw = pd.read_excel(path, engine="openpyxl")
    print(f"file    {path}")
    print(f"dated   {fd}   rows {len(raw):,}   columns {len(raw.columns)}")
    print(f"\ncolumns as the feed spells them:\n  {list(raw.columns)}\n")
    for label, wanted in (("REQUIRED", NEED_TEAM), ("REFEREE", NEED_REF),
                          ("OPTIONAL", OPTIONAL)):
        res = _resolve(raw.columns, wanted)
        print(f"{label}:")
        for k, v in res.items():
            print(f"  {k:<16} -> {v if v else '*** NOT FOUND ***'}")
    res = _resolve(raw.columns, NEED_TEAM)
    if res.get("VENUE"):
        print(f"\nVENUE values: {sorted(raw[res['VENUE']].dropna().astype(str).unique())[:8]}")
    if res.get("DATASET"):
        print(f"DATASET values: {sorted(raw[res['DATASET']].dropna().astype(str).unique())[:4]}")
    if res.get("GAME-ID"):
        per = raw.groupby(res["GAME-ID"]).size()
        print(f"rows per GAME-ID: min {per.min()} median {per.median():.0f} max {per.max()}"
              f"   (MUST be exactly 2 -- one per team)")
    return 0


def convert(asof=None, feed_dir=None, target=None, strict_age=True):
    """Pivot the team feed to game-wide and write the CrewShock CSV."""
    target = target or TARGET
    path, fd = find_feed(asof, feed_dir)
    asof_d = dt.date.fromisoformat(asof) if isinstance(asof, str) else (asof or dt.date.today())
    age = (asof_d - fd).days
    print(f"feed    {os.path.basename(path)}   dated {fd}   age {age}d")
    if strict_age and age > MAX_AGE_DAYS:
        print(f"HARD STOP: feed is {age} days old (max {MAX_AGE_DAYS}).\n"
              f"  A stale history does not error -- CrewShock silently freezes at its last\n"
              f"  observed value and drifts. Skip the slate; do not score on stale data.")
        return 2

    raw = pd.read_excel(path, engine="openpyxl")
    tcol = _resolve(raw.columns, NEED_TEAM)
    rcol = _resolve(raw.columns, NEED_REF)
    missing = [k for k, v in tcol.items() if v is None]
    if missing:
        print(f"HARD STOP: required column(s) not found: {missing}")
        print(f"  feed columns: {list(raw.columns)}")
        print(f"  run --probe and add the real spelling to NEED_TEAM.")
        return 2
    if rcol["MAIN REF"] is None or rcol["CREW"] is None:
        print(f"HARD STOP: referee columns not found -> {rcol}")
        print(f"  CrewShock cannot be scored without officials.")
        return 2

    d = pd.DataFrame({
        "gid":   raw[tcol["GAME-ID"]].astype(str).str.strip(),
        "date":  pd.to_datetime(raw[tcol["DATE"]], errors="coerce"),
        "team":  raw[tcol["TEAM"]].astype(str).str.strip(),
        "venue": raw[tcol["VENUE"]].astype(str).str.strip().str.upper().str[0],
        "PF":    pd.to_numeric(raw[tcol["PF"]], errors="coerce"),
        "POSS":  pd.to_numeric(raw[tcol["POSS"]], errors="coerce"),
        "PTS":   pd.to_numeric(raw[tcol["PTS"]], errors="coerce"),
        "CLOSING TOTAL": pd.to_numeric(raw[tcol["CLOSING TOTAL"]], errors="coerce"),
        "DATASET": raw[tcol["DATASET"]].astype(str),
        "MAIN REF": raw[rcol["MAIN REF"]].astype(str).str.strip(),
        "CREW":     raw[rcol["CREW"]].astype(str).str.strip(),
    })
    if rcol.get("CREW CHIEF") and rcol["CREW CHIEF"] != rcol["MAIN REF"]:
        d["CREW CHIEF"] = raw[rcol["CREW CHIEF"]].astype(str).str.strip()
    if tcol.get("OPENING TOTAL") is None:
        o = _resolve(raw.columns, OPTIONAL)
        if o.get("OPENING TOTAL"):
            d["OPENING TOTAL"] = pd.to_numeric(raw[o["OPENING TOTAL"]], errors="coerce")

    # --- the pivot. VENUE must partition each game into exactly one H and one R.
    bad_v = sorted(set(d.venue.dropna()) - {"H", "R", "A"})
    if bad_v:
        print(f"HARD STOP: unrecognised VENUE values {bad_v}; expected H and R/A")
        return 2
    d["venue"] = d.venue.replace({"A": "R"})
    counts = d.groupby("gid").venue.agg(lambda s: tuple(sorted(s)))
    ok = counts == ("H", "R")
    if not ok.all():
        bad = counts[~ok]
        print(f"HARD STOP: {len(bad)} game(s) are not exactly one H + one R row.")
        print(f"  A game with two H rows folds one team's fouls onto itself.")
        for g, v in bad.head(5).items():
            print(f"    {g}: {v}")
        return 2

    H = d[d.venue == "H"].drop(columns="venue").set_index("gid")
    R = d[d.venue == "R"].drop(columns="venue").set_index("gid")
    keep_common = ["date", "DATASET"]
    W = pd.DataFrame(index=H.index)
    W["GAME-ID"] = H.index
    W["DATE"] = H["date"].dt.strftime("%m/%d/%Y")
    for side, src in (("H", H), ("R", R)):
        W[f"TEAM_{side}"] = src["team"]
        W[f"PF_{side}"] = src["PF"]
        W[f"POSS_{side}"] = src["POSS"]
        W[f"PTS_{side}"] = src["PTS"]
        W[f"CLOSING TOTAL_{side}"] = src["CLOSING TOTAL"]
        W[f"DATASET_{side}"] = src["DATASET"]
        W[f"MAIN REF_{side}"] = src["MAIN REF"]
        W[f"CREW_{side}"] = src["CREW"]
        if "CREW CHIEF" in src:
            W[f"CREW CHIEF_{side}"] = src["CREW CHIEF"]
        if "OPENING TOTAL" in src:
            W[f"OPENING TOTAL_{side}"] = src["OPENING TOTAL"]
    W["VENUE_H"] = "H"

    # --- validate the result the way load_history() will consume it
    if not W["DATASET_H"].astype(str).str.contains("Regular Season", na=False).any():
        print(f"HARD STOP: no row has 'Regular Season' in DATASET_H.")
        print(f"  load_history() filters on it; every row would be dropped.")
        print(f"  observed: {sorted(W['DATASET_H'].astype(str).unique())[:5]}")
        return 2
    tot = W["CLOSING TOTAL_H"]
    act = W["PTS_H"] + W["PTS_R"]
    usable = tot.between(150, 300) & act.notna()
    pf_ok = W[["PF_H", "PF_R", "POSS_H", "POSS_R"]].notna().all(axis=1)

    os.makedirs(os.path.dirname(target), exist_ok=True)
    W.to_csv(target, index=False)
    print(f"wrote   {target}   {len(W):,} games")
    print(f"  usable by load_history (Regular Season, total 150-300, final present): "
          f"{int(usable.sum()):,}")
    print(f"  complete foul/possession rows: {int(pf_ok.sum()):,}")
    print(f"  date range {W['DATE'].min()} .. {W['DATE'].max()}")
    if usable.sum() == 0:
        print("  *** zero usable games -- CrewShock will score nothing ***")
        return 2
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--probe", action="store_true", help="report columns, write nothing")
    p.add_argument("--date", default=None, help="as-of date YYYY-MM-DD (default today)")
    p.add_argument("--dir", default=None)
    p.add_argument("--target", default=None)
    p.add_argument("--allow-stale", action="store_true",
                   help="bypass the age stop; records that you did")
    a = p.parse_args()
    try:
        if a.probe:
            sys.exit(probe(a.date, a.dir))
        sys.exit(convert(a.date, a.dir, a.target, strict_age=not a.allow_stale))
    except Exception as e:
        print(f"FAIL {type(e).__name__}: {e}")
        sys.exit(2)
