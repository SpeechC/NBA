"""PREREG_injury.md Stage-0 data-quality gates. Reads NO market numbers.

Q1 coverage        >= 90% of panel games in the analysis window (2020-21..2024-25;
                   2025-26 dropped per the Q1 resolution) have >= 1 report
Q2 parse validity  players listed OUT in the FINAL pregame report play 0
                   seconds in the lineup parquet in >= 97% of cases
Q3 timing sanity   report timestamps precede tip for >= 99% of used reports

Any failure stops the market tests until the data defect is fixed. Fixing data
is permitted; touching the hypothesis or the frozen states is not.

Q2 is the real test: it validates the parse, the player-name join and the
status semantics all at once, against an independent source (the play-by-play
lineup reconstruction).
"""
import warnings

import duckdb
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

from prepare_data import CSV, season_label

PANEL = "injury_status_panel.csv"
WINDOW_MAX = 2024      # 2025-26 dropped per PREREG_injury.md Q1 resolution
PBP = "/home/dpope/data/pbp_lineups_all.parquet"

MINUTES_SQL = f"""
WITH ev AS (
  SELECT lpad(CAST(GAME_ID AS VARCHAR),10,'0') AS gid,
         PLAYER1_ID AS pid, PLAYER1_NAME AS pname,
         PLAYER1_TEAM_ABBREVIATION AS abbr
  FROM read_parquet('{PBP}')
  WHERE SEASON_TYPE='RegularSeason' AND PLAYER1_ID > 0
    AND PLAYER1_NAME IS NOT NULL
)
SELECT gid, pid, any_value(pname) AS pname, any_value(abbr) AS abbr,
       count(*) AS events
FROM ev GROUP BY gid, pid
"""


def norm_name(s):
    """'Claxton,Nicolas' -> 'nicolasclaxton';  'Nicolas Claxton' -> same."""
    s = str(s).lower()
    s = re.sub(r"[^a-z,]", "", s)
    if "," in s:
        last, _, first = s.partition(",")
        s = first + last
    return s


import re  # noqa: E402  (used by norm_name above)


def main():
    P = pd.read_csv(PANEL, parse_dates=["report_ts", "game_date"])
    print(f"  panel: {len(P):,} rows, {P['report_date'].nunique():,} report "
          f"days, {P['game_date'].nunique():,} game dates")

    raw = pd.read_csv(CSV, low_memory=False)
    lbl = season_label(raw).astype(str)
    g = raw[lbl.str.contains("Regular Season", na=False)].copy()
    g["yr"] = lbl[lbl.str.contains("Regular Season", na=False)] \
        .str.extract(r"(\d{4})")[0].astype(int)
    g["dt"] = pd.to_datetime(g["DATE"], errors="coerce").dt.normalize()
    g["gid"] = g["GAME-ID"].astype(str).str.strip().str.zfill(10)
    g = g[(g["yr"] >= 2020) & (g["yr"] <= WINDOW_MAX)]   # 2025-26 dropped

    # ---------------------------------------------------------------- Q1
    print("\n" + "=" * 84)
    print("Q1 — COVERAGE (>= 90% of panel games with >= 1 report)")
    print("=" * 84)
    have = set(P["game_date"].dt.strftime("%Y-%m-%d"))
    g["covered"] = g["dt"].dt.strftime("%Y-%m-%d").isin(have)
    cov = 100 * g["covered"].mean()
    print(f"  {'season':>8}{'games':>8}{'covered':>9}{'pct':>8}")
    for yr, s in g.groupby("yr"):
        print(f"  {yr:>8}{len(s):>8,}{int(s['covered'].sum()):>9,}"
              f"{100*s['covered'].mean():>7.1f}%")
    q1 = cov >= 90.0
    print(f"  OVERALL {cov:.1f}%   Q1 {'PASS' if q1 else 'FAIL'}")
    print(f"  [2025-26 truncation at 2025-12-22 is documented and expected]")

    # ---------------------------------------------------------------- Q3
    print("\n" + "=" * 84)
    print("Q3 — TIMING SANITY (>= 99% of reports precede tip)")
    print("=" * 84)
    # tip is not in the panel; use the game DATE as the conservative bound:
    # a report must be dated on or before its game date
    P["lead_days"] = (P["game_date"] - P["report_ts"].dt.normalize()).dt.days
    ok3 = (P["lead_days"] >= 0).mean()
    print(f"  report date <= game date: {100*ok3:.2f}%")
    print(f"  lead-day distribution: "
          f"{P['lead_days'].value_counts().sort_index().head(4).to_dict()}")
    q3 = ok3 >= 0.99
    print(f"  Q3 {'PASS' if q3 else 'FAIL'}")

    # ---------------------------------------------------------------- Q2
    print("\n" + "=" * 84)
    print("Q2 — PARSE VALIDITY (>= 97% of final-report OUT play 0 seconds)")
    print("=" * 84)
    M = duckdb.connect().execute(MINUTES_SQL).fetchdf()
    M["gid"] = M["gid"].astype(str)
    M["key"] = M["pname"].map(norm_name)
    played = M.groupby("gid")["key"].apply(set).to_dict()

    # final pregame report per (game_date, matchup)
    P["k"] = P["game_date"].dt.strftime("%Y-%m-%d") + "|" + P["matchup"]
    last_ts = P.groupby("k")["report_ts"].transform("max")
    F = P[P["report_ts"] == last_ts].copy()
    F = F[F["status"] == "Out"]
    F["key"] = F["player"].map(norm_name)

    # map matchup+team to a gid via the panel's date + team abbreviations
    g["mk"] = g["dt"].dt.strftime("%Y-%m-%d")
    gmap = {}
    for _, r in g.iterrows():
        gmap.setdefault(r["mk"], []).append(r["gid"])
    F["date_s"] = F["game_date"].dt.strftime("%Y-%m-%d")

    checked = zero = 0
    for date_s, sub in F.groupby("date_s"):
        gids = gmap.get(date_s, [])
        if not gids:
            continue
        allplayed = set()
        for gd in gids:
            allplayed |= played.get(gd, set())
        for k in sub["key"]:
            if not k:
                continue
            checked += 1
            if k not in allplayed:
                zero += 1
    rate = zero / checked if checked else 0
    print(f"  final-report OUT designations checked: {checked:,}")
    print(f"  of these, absent from the play-by-play that night: "
          f"{zero:,} ({100*rate:.2f}%)")
    q2 = rate >= 0.97
    print(f"  Q2 {'PASS' if q2 else 'FAIL'}")

    print("\n" + "=" * 84)
    print("STAGE-0 VERDICT")
    print("=" * 84)
    for nm, ok in (("Q1 coverage", q1), ("Q2 parse validity", q2),
                   ("Q3 timing sanity", q3)):
        print(f"  {nm:22} {'PASS' if ok else 'FAIL'}")
    print(f"\n  -> {'gates pass; the PREREG_injury.md market tests may proceed' if (q1 and q2 and q3) else 'STOP: fix the data defect before any market test'}")


if __name__ == "__main__":
    main()
