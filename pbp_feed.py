"""Live PBP feed for 2026-27, via cdn.nba.com. Supplies pbp_transition.update().

WHY THE CDN AND NOT stats.nba.com
  stats.nba.com/stats/playbyplayv2 returns HTTP 200 with a 2-byte empty body from
  this host -- blocked, not broken, so retries do not help. cdn.nba.com serves
  static JSON with no auth and answered in 0.2s.

THE COST OF THAT CHOICE
  The CDN serves the liveData schema (actionType strings), not the v2 schema the
  frozen reconstruction was validated on. This module maps liveData BACK ONTO v2
  so `pbp_transition._aggregate` runs unmodified.

  That mapping is deliberately faithful rather than accurate. The CDN labels each
  rebound `offensive`/`defensive` outright, which is better information than the
  frozen team-change heuristic -- and using it would compute live trans_share by a
  different rule than the 18,330 backfilled team-games. A team state that pools
  history and live across a rule change is a silent discontinuity at exactly the
  season boundary. So the label is ignored and the heuristic is re-derived.
  See VALIDATION below for what that costs.

VALIDATION -- CDN vs parquet, 40 games / 80 team-games, both through _aggregate()
  trans_share  corr 0.9868  bias +0.63pp  sd 0.83pp   (frozen STARTTIME benchmark
                                                       was corr 0.9854, sd 0.84pp)
  live_to      corr 0.9986  exact 97.5%
  fga          corr 0.9975
  event-level  parquet-only events 0 of 15,673; msgtype agreement 100.000%

  KNOWN DISCONTINUITY: the +0.63pp level shift is small in output terms (-0.068
  pts of m(X), 1.4% of the 4.77 threshold) but is 0.564 of the CROSS-TEAM sd of
  trans_share, and it is uniform -- every 2026-27 team reads ~0.6pp more
  transition-heavy than the parquet-derived history it is pooled with. It shifts
  m(X) by roughly a constant; it cannot create game-to-game differential error.
  Rebuilding the store from the CDN would remove it, but the CDN does not serve
  2017-18 (verified), so that would cost the store its first two seasons.
  See PBP_FEED_VALIDATION.md. Reproduce with validate_feed().
"""
import os, re, time, json
import pandas as pd, numpy as np
import requests

SCHEDULE = "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json"
PBP      = "https://cdn.nba.com/static/json/liveData/playbyplay/playbyplay_{gid}.json"
HDRS     = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Referer": "https://www.nba.com/", "Accept": "application/json"}
REG_PREFIX = "002"        # 001 preseason, 002 regular, 004 playoffs
PAUSE      = 0.7          # politeness between game fetches

# Row set kept, chosen by VALIDATION not by taste. The CDN is a strict SUPERSET
# of the parquet (parquet-only events: 0 of 15,673; msgtype agreement 100%), so
# the mapping is confirmed correct and the only question is what to DROP.
#   msg 8/9/10/7 (sub, timeout, jumpball, violation) -- absent from the parquet.
#   msg 12 (period) -- the CDN emits one at t=0 that the parquet lacks. This one
#     matters: `recon` falls back to the period MINIMUM for the first possession,
#     so a t=0 row moves the first shot of every period from sc=0 to sc=17.
#     That single row drove 141 of 141 trans-flag disagreements (~1 per period
#     per game) and a -1.54pp bias. Dropping it: bias -1.54pp -> +0.51pp.
KEEP_MSG = {1, 2, 3, 4, 5, 6}
_CLOCK = re.compile(r"PT(\d+)M([\d.]+)S")

# liveData actionType -> v2 EVENTMSGTYPE. Shot rows split on shotResult.
_MSG = {"freethrow": 3, "rebound": 4, "turnover": 5, "foul": 6, "violation": 7,
        "substitution": 8, "timeout": 9, "jumpball": 10, "ejection": 11, "period": 12}
# v2 EVENTMSGACTIONTYPE for turnovers: 1 bad pass, 2 lost ball = LIVE ball.
# pbp_transition counts live_to as isin([1,2]); everything else must NOT collide.
_TO_SUB = {"bad pass": 1, "lost ball": 2}


def _period_offset(p):
    """Parquet PCTIMESTRING is GAME-elapsed: offset is exactly 720*(period-1),
    then 300s per OT. Measured, not assumed (period 5 offset = 2880 = 720*4)."""
    return 720.0 * (p - 1) if p <= 4 else 2880.0 + 300.0 * (p - 5)


def _clock_elapsed(clock, period):
    """liveData gives time REMAINING ('PT10M24.00S'); the parquet stores ELAPSED.

    CEIL is not a rounding preference -- v2 renders the clock as MM:SS, truncating
    the fraction, so elapsed_v2 = plen - floor(remaining) = ceil(elapsed). Theory
    and measurement agree: ceil scores corr 0.9868 / sd 0.83pp against the parquet
    versus 0.9756 / 1.12pp raw.
    """
    m = _CLOCK.match(clock or "")
    if not m: return np.nan
    remaining = int(m.group(1)) * 60 + float(m.group(2))
    plen = 720.0 if period <= 4 else 300.0
    return float(np.ceil(plen - remaining)) + _period_offset(period)


def _get(url, tries=4):
    last = None
    for i in range(tries):
        try:
            r = requests.get(url, headers=HDRS, timeout=30)
            if r.status_code == 200 and len(r.content) > 200:
                return r.json()
            last = f"HTTP {r.status_code}, {len(r.content)}B"
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
        time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"fetch failed after {tries}: {url} ({last})")


def game_ids(day, regular_only=True):
    """Regular-season game ids for a date, from the published season schedule."""
    ls = _get(SCHEDULE)["leagueSchedule"]
    want = pd.Timestamp(day).strftime("%m/%d/%Y")
    for d in ls["gameDates"]:
        if d["gameDate"].split()[0] == want:
            return [g["gameId"] for g in d["games"]
                    if not regular_only or g["gameId"].startswith(REG_PREFIX)]
    return []


def fetch_game(gid):
    """One game as a v2-shaped frame. Empty frame if the game has no actions yet."""
    acts = _get(PBP.format(gid=gid))["game"]["actions"]
    rows = []
    for a in acts:
        at, per = a.get("actionType"), a.get("period") or 0
        if at in ("2pt", "3pt"):
            msg = 1 if a.get("shotResult") == "Made" else 2
        else:
            msg = _MSG.get(at, 0)
        sub = 0
        if at == "turnover":
            sub = _TO_SUB.get((a.get("subType") or "").lower(), 99)

        tri = a.get("teamTricode")
        # v2 leaves PLAYER1_TEAM_ABBREVIATION null on TEAM rebounds (personId 0);
        # the CDN fills the tricode in. Null it back out, or the frozen
        # `tm != prev_team` test sees possession changes v2 never saw.
        if at == "rebound" and not a.get("personId"):
            tri = None

        if msg not in KEEP_MSG:
            continue
        rows.append({
            "GAME_ID": int(gid),
            "PERIOD": per,
            "EVENTNUM": a.get("actionNumber"),
            "PCTIMESTRING": _clock_elapsed(a.get("clock"), per),
            "EVENTMSGTYPE": msg,
            "EVENTMSGACTIONTYPE": sub,
            "PLAYER1_TEAM_ABBREVIATION": tri,
            # descriptions already carry the "MISS " prefix the FT test looks for
            "HOMEDESCRIPTION": a.get("description") or "",
            "VISITORDESCRIPTION": "",
        })
    return pd.DataFrame(rows)


def fetch_day(day, gids=None, verbose=True):
    """All regular-season PBP for a date, shaped for pbp_transition.update()."""
    gids = gids if gids is not None else game_ids(day)
    if not gids:
        if verbose: print(f"  pbp_feed: no regular-season games on {day}")
        return pd.DataFrame()
    out, failed = [], []
    for i, g in enumerate(gids):
        try:
            f = fetch_game(g)
            if len(f): out.append(f)
            else: failed.append((g, "no actions"))
        except Exception as e:
            failed.append((g, str(e)[:60]))
        if i < len(gids) - 1: time.sleep(PAUSE)
    if verbose:
        print(f"  pbp_feed {day}: {len(out)}/{len(gids)} games")
        for g, why in failed: print(f"    MISSING {g}: {why}")
    # Partial days are returned, not raised: a postponed game should not block the
    # other nine. The caller sees the count and staleness() catches a real outage.
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def validate_feed(n_games=40, since="2025-01-01", seed=7):
    """Re-run the CDN-vs-parquet check. Returns the comparison frame."""
    import pbp_transition as PT
    cols = ["GAME_ID","PERIOD","EVENTNUM","PCTIMESTRING","EVENTMSGTYPE",
            "EVENTMSGACTIONTYPE","PLAYER1_TEAM_ABBREVIATION","HOMEDESCRIPTION",
            "VISITORDESCRIPTION","SEASON_TYPE","GAMEDATE"]
    p = pd.read_parquet(PT.PARQ, columns=cols)
    p = p[p.SEASON_TYPE.astype(str).str.contains("Regular", na=False)]
    p["d"] = pd.to_datetime(p.GAMEDATE, errors="coerce")
    p = p[p.d >= since]
    gids = np.random.default_rng(seed).choice(sorted(p.GAME_ID.unique()), n_games, replace=False)
    sub = p[p.GAME_ID.isin(gids)]
    dates = sub.groupby("GAME_ID").d.first()
    P = PT._to_names(PT._aggregate(sub.copy(), dates)); P["date"] = pd.to_datetime(P.date)
    C = pd.concat([fetch_game(str(g).zfill(10)) for g in gids], ignore_index=True)
    L = PT._to_names(PT._aggregate(C, dates))
    m = P.merge(L, on=["date","team"], suffixes=("_par","_cdn"))
    d = m.trans_share_cdn - m.trans_share_par
    print(f"n={len(m)}  trans corr {m.trans_share_par.corr(m.trans_share_cdn):.4f}  "
          f"bias {100*d.mean():+.2f}pp  sd {100*d.std():.2f}pp")
    return m
