"""Fetch regulation-end and game-end wallclocks for every game already in
espn_clocks_{league}.csv (which stored only tip and halftime). Needed for the
endgame-pinning and OT-optionality tests. Appends espn_end_clocks_{lg}.csv.
"""
import os
import sys
import time

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from espn_true_clock import BASE, get                        # noqa: E402

REPO = os.path.dirname(os.path.abspath(__file__))


def ends(espn_id, league):
    js = get(f"{BASE}/{league}/summary", {"event": espn_id})
    if not js:
        return None, None, None
    plays = js.get("plays") or []
    if not plays:
        return None, None, None
    p4 = [p["wallclock"] for p in plays
          if (p.get("period") or {}).get("number") == 4 and p.get("wallclock")]
    allw = [p["wallclock"] for p in plays if p.get("wallclock")]
    nper = max((p.get("period") or {}).get("number", 0) for p in plays)
    return (max(p4) if p4 else None), (max(allw) if allw else None), nper


def run(league):
    src = os.path.join(REPO, f"espn_clocks_{league}.csv")
    out = os.path.join(REPO, f"espn_end_clocks_{league}.csv")
    d = pd.read_csv(src).dropna(subset=["tip_utc"])
    have = set()
    rows = []
    if os.path.exists(out):
        prev = pd.read_csv(out)
        have = set(prev.espn_id.astype(str))
        rows = prev.to_dict("records")
    todo = d[~d.espn_id.astype(str).isin(have)]
    print(f"[{league}] {len(todo)} games to fetch (of {len(d)})")
    for i, (_, r) in enumerate(todo.iterrows(), 1):
        reg, fin, nper = ends(r.espn_id, league)
        rows.append({"espn_id": r.espn_id, "date": r.date, "away": r.away,
                     "home": r.home, "reg_end_utc": reg, "game_end_utc": fin,
                     "n_periods": nper})
        if i % 40 == 0:
            print(f"[{league}] {i}/{len(todo)}", flush=True)
            pd.DataFrame(rows).to_csv(out, index=False)
        time.sleep(0.2)
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"[{league}] wrote {out}: {len(rows)} rows")


if __name__ == "__main__":
    for lg in (sys.argv[1:] or ["wnba", "nba"]):
        run(lg)
    print("### ENDCLOCKS DONE")
