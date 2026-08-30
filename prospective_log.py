"""Immutable pre-game log for the frozen 2026-27 prospective test.

Writes ONE row per game BEFORE tip. Never overwrites. Post-game fields are
appended by `settle()` only. See PREREG_2026_27_PROSPECTIVE.md D2.

DO NOT add columns, change the schema, or compute wagering performance here.
"""
import csv, os, subprocess, datetime as dt

LOG = os.path.expanduser("~/data/nba_2026_27_prospective_log.csv")
PRE = ["game_id","date","TEAM_H","TEAM_R","logged_at_utc",
       "open_total","open_spread","open_line_source","open_obtained_at_utc",
       "P_hat","P_book","D","EffSum","E_pace",
       "mu5","m_X","D_star_drift","D_star_profile",
       "bet_flag","side","code_git_sha","model_version"]
POST = ["close_total","actual_total","actual_pace","settled_at_utc"]
COLS = PRE + POST
THRESHOLD = 4.77          # FROZEN. See amendment C1/C3. Never re-optimise.
MODEL_VERSION = "2026-08-30-frozen"

def _sha():
    try:
        return subprocess.check_output(["git","rev-parse","--short","HEAD"],
                                       stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return "UNKNOWN"

def _ensure():
    if not os.path.exists(LOG):
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG,"w",newline="") as f:
            csv.DictWriter(f,COLS).writeheader()

def log_game(game_id, date, team_h, team_r, open_total, open_spread,
             open_line_source, open_obtained_at_utc,
             P_hat, P_book, EffSum, mu5, m_X):
    """Write the immutable pre-game row. Refuses to duplicate a game_id."""
    _ensure()
    with open(LOG) as f:
        if any(r["game_id"]==str(game_id) for r in csv.DictReader(f)):
            raise ValueError(f"{game_id} already logged -- rows are immutable")
    D = P_hat - P_book
    E = D * EffSum / 100.0
    row = dict.fromkeys(COLS,"")
    row.update(game_id=game_id, date=date, TEAM_H=team_h, TEAM_R=team_r,
        logged_at_utc=dt.datetime.utcnow().isoformat(timespec="seconds")+"Z",
        open_total=open_total, open_spread=open_spread,
        open_line_source=open_line_source, open_obtained_at_utc=open_obtained_at_utc,
        P_hat=round(P_hat,4), P_book=round(P_book,4), D=round(D,4),
        EffSum=round(EffSum,4), E_pace=round(E,4),
        mu5=round(mu5,4), m_X=round(m_X,4),
        D_star_drift=round(D+mu5,4), D_star_profile=round(D+m_X,4),
        bet_flag=int(abs(E)>=THRESHOLD), side=(1 if E>0 else (-1 if E<0 else 0)),
        code_git_sha=_sha(), model_version=MODEL_VERSION)
    with open(LOG,"a",newline="") as f:
        csv.DictWriter(f,COLS).writerow(row)
    return row

def settle(game_id, close_total, actual_total, actual_pace):
    """Append post-game outcomes. Pre-game fields are never touched."""
    with open(LOG) as f: rows=list(csv.DictReader(f))
    hit=False
    for r in rows:
        if r["game_id"]==str(game_id):
            if r["actual_total"]: raise ValueError(f"{game_id} already settled")
            r.update(close_total=close_total, actual_total=actual_total,
                     actual_pace=actual_pace,
                     settled_at_utc=dt.datetime.utcnow().isoformat(timespec="seconds")+"Z")
            hit=True
    if not hit: raise ValueError(f"{game_id} not found -- log it before tip")
    with open(LOG,"w",newline="") as f:
        w=csv.DictWriter(f,COLS); w.writeheader(); w.writerows(rows)

def health():
    """Pipeline health ONLY. Deliberately computes no wagering performance."""
    if not os.path.exists(LOG): return {"rows":0}
    with open(LOG) as f: rows=list(csv.DictReader(f))
    miss=[c for c in PRE if any(not r[c] for r in rows)]
    return {"rows":len(rows), "settled":sum(1 for r in rows if r["actual_total"]),
            "bet_flagged":sum(1 for r in rows if r["bet_flag"]=="1"),
            "incomplete_pregame_fields":miss,
            "distinct_code_shas":sorted({r["code_git_sha"] for r in rows})}
