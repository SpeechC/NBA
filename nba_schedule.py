"""NBA schedule fetcher for the 2026-27 live pipeline.

Tries several public endpoints in order and returns a normalised frame:

    game_date (datetime64)  away_abbr  home_abbr  game_id  tipoff_et

ENDPOINT FRAGILITY IS THE POINT OF THE FALLBACK CHAIN. The NBA moved the
injury-report CDN mid-2025-26 and a WAF now blocks several hosts from some
networks; this module therefore (a) tries multiple sources, (b) caches every
successful pull to disk, and (c) can serve entirely from a local CSV so a
blocked endpoint never stops the day's recommendations.

VERIFY ON YOUR MACHINE before the season: `python nba_schedule.py --check`.
From the development sandbox cdn.nba.com and stats.nba.com are both blocked,
so the live paths in here are written from their documented shapes and are
NOT sandbox-verified.
"""
import argparse
import json
import os
import sys
import time

import pandas as pd

CACHE_DIR = os.environ.get("NBA_SCHED_CACHE", "schedule_cache")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
HDRS = {"User-Agent": UA, "Referer": "https://www.nba.com/",
        "Origin": "https://www.nba.com", "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9", "x-nba-stats-origin": "stats",
        "x-nba-stats-token": "true", "Connection": "keep-alive"}

# 2026-27 season string used by the stats.nba.com endpoint
SEASON = os.environ.get("NBA_SEASON", "2026-27")


def _get(url, timeout=30):
    import requests
    r = requests.get(url, headers=HDRS, timeout=timeout)
    r.raise_for_status()
    return r.json()


def _from_cdn():
    """Static league schedule JSON. One file, whole season."""
    data = _get("https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json")
    rows = []
    for gd in data["leagueSchedule"]["gameDates"]:
        for g in gd["games"]:
            rows.append({"game_id": g["gameId"],
                         "game_date": pd.to_datetime(gd["gameDate"]).normalize(),
                         "tipoff_et": g.get("gameDateTimeEst"),
                         "away_abbr": g["awayTeam"]["teamTricode"],
                         "home_abbr": g["homeTeam"]["teamTricode"],
                         "label": g.get("gameLabel", "")})
    return pd.DataFrame(rows)


def _from_stats():
    """stats.nba.com scheduleleaguev2 — resultSets shape."""
    data = _get(f"https://stats.nba.com/stats/scheduleleaguev2?LeagueID=00&Season={SEASON}")
    tbl = data.get("resultSets", data.get("resultSet"))
    if isinstance(tbl, dict):
        tbl = [tbl]
    blk = next(t for t in tbl if "Game" in t.get("name", "") or t.get("headers"))
    cols = [c.upper() for c in blk["headers"]]
    df = pd.DataFrame(blk["rowSet"], columns=cols)
    pick = lambda *names: next((c for c in names if c in df.columns), None)
    return pd.DataFrame({
        "game_id": df[pick("GAME_ID", "GAMEID")],
        "game_date": pd.to_datetime(df[pick("GAME_DATE", "GAMEDATE")]).dt.normalize(),
        "tipoff_et": df.get(pick("GAME_TIME_EST", "GAMEDATETIMEEST")),
        "away_abbr": df[pick("AWAY_TEAM_ABBREVIATION", "AWAYTEAMTRICODE", "VISITOR_TEAM_ABBREVIATION")],
        "home_abbr": df[pick("HOME_TEAM_ABBREVIATION", "HOMETEAMTRICODE")],
        "label": ""})


def _from_local(path):
    """Last-resort local CSV: game_date, away_abbr, home_abbr [, game_id]."""
    df = pd.read_csv(path)
    df["game_date"] = pd.to_datetime(df["game_date"]).dt.normalize()
    for c in ("game_id", "tipoff_et", "label"):
        if c not in df.columns:
            df[c] = ""
    return df[["game_id", "game_date", "tipoff_et", "away_abbr", "home_abbr", "label"]]


SOURCES = [("cdn", _from_cdn), ("stats", _from_stats)]


def fetch(local_csv=None, use_cache_on_fail=True, verbose=True,
          prefer_local=True):
    """Return the full-season schedule frame.

    An explicitly supplied local_csv is treated as an OVERRIDE (prefer_local),
    so a hand-maintained schedule always wins over the live endpoints.
    """
    os.makedirs(CACHE_DIR, exist_ok=True)
    if prefer_local and local_csv and os.path.exists(local_csv):
        df = _from_local(local_csv)
        if verbose:
            print(f"  schedule: {len(df):,} games from LOCAL OVERRIDE {local_csv}")
        return df
    cache = os.path.join(CACHE_DIR, f"schedule_{SEASON.replace('-', '_')}.csv")
    errs = []
    for name, fn in SOURCES:
        try:
            df = fn()
            if len(df):
                df.to_csv(cache, index=False)
                if verbose:
                    print(f"  schedule: {len(df):,} games from '{name}' "
                          f"(cached -> {cache})")
                return df
        except Exception as ex:                       # noqa: BLE001
            errs.append(f"{name}: {type(ex).__name__}: {ex}")
    if local_csv and os.path.exists(local_csv):
        df = _from_local(local_csv)
        if verbose:
            print(f"  schedule: {len(df):,} games from LOCAL {local_csv}")
        return df
    if use_cache_on_fail and os.path.exists(cache):
        df = pd.read_csv(cache, parse_dates=["game_date"])
        age_h = (time.time() - os.path.getmtime(cache)) / 3600
        print(f"  !! all live sources failed; using CACHE ({age_h:.1f}h old)")
        for e in errs:
            print(f"     {e}")
        return df
    raise RuntimeError("no schedule source available:\n  " + "\n  ".join(errs))


def games_on(date, **kw):
    d = pd.to_datetime(date).normalize()
    s = fetch(**kw)
    return s[s.game_date == d].reset_index(drop=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="probe every source")
    ap.add_argument("--date", help="list games on YYYY-MM-DD")
    ap.add_argument("--local", help="fallback CSV path")
    a = ap.parse_args()
    if a.check:
        for name, fn in SOURCES:
            try:
                df = fn()
                print(f"  {name:6} OK  {len(df):,} games  "
                      f"{df.game_date.min().date()} .. {df.game_date.max().date()}")
            except Exception as ex:                   # noqa: BLE001
                print(f"  {name:6} FAIL  {type(ex).__name__}: {ex}")
        sys.exit(0)
    g = games_on(a.date, local_csv=a.local) if a.date else fetch(local_csv=a.local)
    print(g.to_string(index=False))
