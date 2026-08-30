"""PBP transition/live-turnover states for m(X). Feeds PHASE 4 settle.

The parquet's STARTTIME comes from a lineup-reconstruction pipeline that does not
exist for a live feed, so possession starts are reconstructed from raw PBP.

RECONSTRUCTION, VALIDATED against STARTTIME on 3,609,007 regular-season events:
  a possession ends on: made FG (1), turnover (5), made FT (3 w/o MISS),
                        DEFENSIVE rebound (4, rebounding team != prior event team)
  exact 88.44%  |  transition share 18.67% vs 18.88%  |  event agreement 99.43%
  TEAM-GAME (what the profile consumes): corr 0.9854, bias -0.21pp, sd 0.84pp

An earlier version treating ALL rebounds as possession-ending gave 27.36% vs
18.88% -- a 45% overstatement. Offensive rebounds do not end a possession.
"""
import os, sys, warnings
import pandas as pd, numpy as np
warnings.filterwarnings("ignore")

STORE  = os.path.expanduser("~/data/pbp_transition_store.csv")
PARQ   = "/mnt/c/NBA2/out/pbp_lineups_all.parquet"
TRANS_MAX_SEC = 7          # frozen: early-clock threshold
COLS = ["date","team","trans_share","live_to","fga"]

def _reconstruct(p):
    """Add `recon` (possession start, elapsed sec) to a sorted PBP frame."""
    for c in ("PERIOD","EVENTNUM","PCTIMESTRING","EVENTMSGTYPE","EVENTMSGACTIONTYPE"):
        p[c] = pd.to_numeric(p[c], errors="coerce")
    p = p.drop_duplicates(["GAME_ID","EVENTNUM"]).sort_values(["GAME_ID","PERIOD","EVENTNUM"])
    desc = p.get("HOMEDESCRIPTION", pd.Series("", index=p.index)).fillna("") + " " + \
           p.get("VISITORDESCRIPTION", pd.Series("", index=p.index)).fillna("")
    tm = p["PLAYER1_TEAM_ABBREVIATION"]
    prev_team = p.groupby(["GAME_ID","PERIOD"], sort=False)["PLAYER1_TEAM_ABBREVIATION"].shift(1)
    def_reb = (p.EVENTMSGTYPE == 4) & tm.notna() & prev_team.notna() & (tm != prev_team)
    made_ft = (p.EVENTMSGTYPE == 3) & ~desc.str.contains("MISS", na=False)
    p["ends"] = (p.EVENTMSGTYPE == 1) | (p.EVENTMSGTYPE == 5) | def_reb | made_ft
    g = p.groupby(["GAME_ID","PERIOD"], sort=False)
    prev_end = g.apply(lambda x: x.PCTIMESTRING.where(x.ends).shift(1).ffill(),
                       include_groups=False).reset_index(level=[0,1], drop=True)
    p["recon"] = prev_end.fillna(g.PCTIMESTRING.transform("min"))
    return p

def _aggregate(p, dates):
    """Team-game transition share and live-ball turnover count."""
    p = _reconstruct(p)
    sc = p.PCTIMESTRING - p.recon
    p["fga"]   = p.EVENTMSGTYPE.isin([1,2])
    p["trans"] = (p.fga & (sc >= 0) & (sc <= TRANS_MAX_SEC)).astype(int)
    p["live"]  = ((p.EVENTMSGTYPE == 5) & p.EVENTMSGACTIONTYPE.isin([1,2])).astype(int)
    p = p[p.PLAYER1_TEAM_ABBREVIATION.notna()]
    a = p.groupby(["GAME_ID","PLAYER1_TEAM_ABBREVIATION"]).agg(
            fga=("fga","sum"), trans=("trans","sum"), live=("live","sum")).reset_index()
    a = a[a.fga >= 40]
    a["trans_share"] = a.trans / a.fga
    a["date"] = a.GAME_ID.map(dates)
    a = a.rename(columns={"PLAYER1_TEAM_ABBREVIATION":"abbr"})
    return a.dropna(subset=["date"])[["date","abbr","trans_share","live","fga"]]

def _to_names(a):
    m = pd.read_csv("/home/dpope/projects/nba_entropy_replication/team_mapping.csv")
    a = a.copy(); a["team"] = a.abbr.map(dict(zip(m.abbr, m.bigdataball_name)))
    return a.dropna(subset=["team"]).rename(columns={"live":"live_to"})[COLS]

def backfill():
    """Build the store from the historical parquet. Run once."""
    p = pd.read_parquet(PARQ, columns=["GAME_ID","PERIOD","EVENTNUM","PCTIMESTRING",
        "EVENTMSGTYPE","EVENTMSGACTIONTYPE","PLAYER1_TEAM_ABBREVIATION",
        "HOMEDESCRIPTION","VISITORDESCRIPTION","SEASON_TYPE","GAMEDATE"])
    p = p[p.SEASON_TYPE.astype(str).str.contains("Regular", na=False)]
    dates = p.groupby("GAME_ID").GAMEDATE.first()
    out = _to_names(_aggregate(p, dates))
    out["date"] = pd.to_datetime(out.date).dt.strftime("%Y-%m-%d")
    os.makedirs(os.path.dirname(STORE), exist_ok=True)
    out.drop_duplicates(["date","team"]).to_csv(STORE, index=False)
    _invalidate_caches()
    return len(out)

def update(day, pbp_frame=None):
    """Append one day. `pbp_frame` lets a live feed inject raw PBP directly.

    Without a frame this looks in the parquet, which covers history only -- for
    2026-27 the caller must supply the frame from a live source.
    """
    if pbp_frame is None:
        try:
            p = pd.read_parquet(PARQ, columns=["GAME_ID","PERIOD","EVENTNUM","PCTIMESTRING",
                "EVENTMSGTYPE","EVENTMSGACTIONTYPE","PLAYER1_TEAM_ABBREVIATION",
                "HOMEDESCRIPTION","VISITORDESCRIPTION","SEASON_TYPE","GAMEDATE"])
            p = p[(p.SEASON_TYPE.astype(str).str.contains("Regular", na=False)) &
                  (pd.to_datetime(p.GAMEDATE, errors="coerce").dt.strftime("%Y-%m-%d") == day)]
        except Exception:
            return 0
    else:
        p = pbp_frame
    if not len(p): return 0
    dates = pd.Series(day, index=p.GAME_ID.unique())
    out = _to_names(_aggregate(p, dates))
    if not len(out): return 0
    out["date"] = day
    prev = pd.read_csv(STORE) if os.path.exists(STORE) else pd.DataFrame(columns=COLS)
    both = pd.concat([prev, out], ignore_index=True).drop_duplicates(["date","team"], keep="last")
    both.to_csv(STORE, index=False)
    _invalidate_caches()
    return len(out)

def _invalidate_caches():
    """frozen_models caches this store per process and never re-reads it.

    nba_daily.py runs all four phases in ONE process, so a settle that appends to
    the store would otherwise leave any later state rebuild reading the pre-update
    snapshot -- silently, with no error. Uses sys.modules so it clears the cache
    only if frozen_models is already loaded; it must never pull it in.
    """
    m = sys.modules.get("frozen_models")
    if m is not None and hasattr(m, "_TRC"):
        m._TRC.clear()


def load():
    if not os.path.exists(STORE): return pd.DataFrame(columns=COLS)
    d = pd.read_csv(STORE); d["date"] = pd.to_datetime(d.date); return d

def staleness(as_of):
    """Days between the store's last game and `as_of`.

    HARD STOP if large. _mean() skips NaN, so a stale store does not error -- the
    transition state silently freezes at its last observed value and m(X) drifts
    without any visible failure. Same class as the BigDataBall stale-history stop
    in CREWSHOCK_LIVE_OPS.
    """
    d = load()
    if not len(d): return {"ok": False, "reason": "store empty", "days": None}
    last = d.date.max(); days = (pd.Timestamp(as_of) - last).days
    return {"ok": days <= 7, "days": int(days),
            "last_game": last.strftime("%Y-%m-%d"),
            "reason": "" if days <= 7 else f"transition store {days}d stale -- m(X) unreliable"}

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "backfill":
        print(f"backfilled {backfill():,} team-games -> {STORE}")
    elif len(sys.argv) > 2 and sys.argv[1] == "update":
        print(f"appended {update(sys.argv[2])} team-games for {sys.argv[2]}")
    else:
        d = load(); print(f"store: {len(d):,} team-games"
              + (f"  {d.date.min().date()}..{d.date.max().date()}" if len(d) else ""))
