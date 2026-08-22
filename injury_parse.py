"""Parse the official NBA injury-report PDF archive into a game-team-player
status panel, and run the PREREG_injury.md Stage-0 data-quality gates.

READS NO MARKET NUMBERS. Nothing here touches a line, a total, or a game
outcome other than minutes played (used solely for gate Q2). The market tests
in PREREG_injury.md are downstream and may only run if Q1-Q3 pass.

PARSING. Reports have a fixed column geometry:
    GameDate | GameTime | Matchup | Team | PlayerName | CurrentStatus | Reason
Words are assigned to columns by x0 with forward-fill down the page (date,
matchup and team appear only on the first row of each group). The REASON
column is DISCARDED: PREREG_injury.md prohibits injury-type/severity/body-part
conditioning, and reason text wraps across lines, so dropping it removes the
only real parsing hazard.

Report timestamp comes from the FILENAME (date + hour stamp), which the header
line corroborates.

OUTPUT  injury_status_panel.csv  (one row per report x game x player)
    report_date, report_stamp, report_ts, game_date, matchup, team_raw,
    player, status
"""
import glob
import os
import re
import warnings

import pandas as pd

warnings.filterwarnings("ignore")

import pdfplumber

PDFS = "/home/dpope/data/injury_reports"
OUT = "injury_status_panel.csv"
STATUSES = {"Out", "Doubtful", "Questionable", "Probable", "Available"}
# column boundaries (x0 midpoints from the fixed layout)
BOUNDS = [(0, 110, "game_date"), (110, 190, "game_time"),
          (190, 255, "matchup"), (255, 415, "team"),
          (415, 575, "player"), (575, 655, "status")]
FN = re.compile(r"Injury-Report_(\d{4}-\d{2}-\d{2})_(\d{2}[AP]M)\.pdf$")


def col_of(x0):
    for lo, hi, name in BOUNDS:
        if lo <= x0 < hi:
            return name
    return None


def parse_pdf(path):
    rows = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            words = page.extract_words()
            lines = {}
            for w in words:
                c = col_of(w["x0"])
                if c is None:
                    continue
                key = round(w["top"] / 3)          # cluster words into lines
                lines.setdefault(key, {}).setdefault(c, []).append(w["text"])
            for key in sorted(lines):
                d = {c: "".join(v) for c, v in lines[key].items()}
                st = d.get("status", "")
                if st not in STATUSES:
                    continue                       # header/wrap/footer lines
                rows.append({
                    "game_date": d.get("game_date", ""),
                    "matchup": d.get("matchup", ""),
                    "team": d.get("team", ""),
                    "player": d.get("player", ""),
                    "status": st})
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    for c in ("game_date", "matchup", "team"):     # forward-fill group columns
        df[c] = df[c].replace("", pd.NA).ffill()
    return df


def main():
    files = sorted(glob.glob(os.path.join(PDFS, "*.pdf")))
    print(f"parsing {len(files):,} PDFs ...")
    out, bad = [], 0
    for i, f in enumerate(files, 1):
        m = FN.search(os.path.basename(f))
        if not m:
            continue
        try:
            df = parse_pdf(f)
        except Exception:
            bad += 1
            continue
        if df.empty:
            continue
        df["report_date"], df["report_stamp"] = m.group(1), m.group(2)
        out.append(df)
        if i % 1000 == 0:
            print(f"  {i:,}/{len(files):,}  rows so far "
                  f"{sum(len(x) for x in out):,}", flush=True)
    P = pd.concat(out, ignore_index=True)
    P["report_ts"] = pd.to_datetime(
        P["report_date"] + " " + P["report_stamp"], format="%Y-%m-%d %I%p")
    P["game_date"] = pd.to_datetime(P["game_date"], errors="coerce")
    P = P.dropna(subset=["game_date", "player"])
    P = P[["report_date", "report_stamp", "report_ts", "game_date", "matchup",
           "team", "player", "status"]].rename(columns={"team": "team_raw"})
    P.to_csv(OUT, index=False)
    print(f"\nwrote {OUT}: {len(P):,} rows, {bad} unreadable PDFs")
    print(f"  reports {P.groupby(['report_date','report_stamp']).ngroups:,}   "
          f"game-dates {P['game_date'].nunique():,}   "
          f"players {P['player'].nunique():,}")
    print(f"  status mix: "
          f"{P['status'].value_counts(normalize=True).round(3).to_dict()}")
    return P


if __name__ == "__main__":
    main()
