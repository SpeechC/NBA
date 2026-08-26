"""TIP-TIME STRUCTURE CHECKS — run BEFORE the prereg is finalised.

Joins ESPN tip-offs to the master, derives local tip hour and hours-of-rest,
and runs the Stage-0 gates. Schedule/reference data only: no score, no total,
no dev is touched here.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
from prepare_data import read_master, season_label
from rest_travel import ARENAS, REST_MAP

# ESPN abbreviation -> the master's team naming (ARENAS keys)
ABBR = {"ATL": "Atlanta", "BOS": "Boston", "BKN": "Brooklyn", "CHA": "Charlotte",
        "CHI": "Chicago", "CLE": "Cleveland", "DAL": "Dallas", "DEN": "Denver",
        "DET": "Detroit", "GS": "Golden State", "GSW": "Golden State",
        "HOU": "Houston", "IND": "Indiana", "LAC": "LA Clippers",
        "LAL": "LA Lakers", "MEM": "Memphis", "MIA": "Miami", "MIL": "Milwaukee",
        "MIN": "Minnesota", "NO": "New Orleans", "NOP": "New Orleans",
        "NY": "New York", "NYK": "New York", "OKC": "Oklahoma City",
        "ORL": "Orlando", "PHI": "Philadelphia", "PHX": "Phoenix",
        "POR": "Portland", "SAC": "Sacramento", "SA": "San Antonio",
        "SAS": "San Antonio", "TOR": "Toronto", "UTA": "Utah", "UTAH": "Utah",
        "WSH": "Washington", "WAS": "Washington"}


def dst_active(ts):
    """US/Canada rule: 2nd Sunday March 02:00 -> 1st Sunday November 02:00."""
    y = ts.year
    mar = pd.Timestamp(year=y, month=3, day=1)
    start = mar + pd.Timedelta(days=(6 - mar.weekday()) % 7 + 7)   # 2nd Sunday
    nov = pd.Timestamp(year=y, month=11, day=1)
    end = nov + pd.Timedelta(days=(6 - nov.weekday()) % 7)         # 1st Sunday
    return start <= ts.tz_localize(None) < end


def local_hour(utc_ts, city):
    """Arena-local tip hour as a float. Arizona does not observe DST."""
    off = ARENAS[city][2]
    if city != "Phoenix" and dst_active(utc_ts):
        off += 1
    lt = utc_ts.tz_localize(None) + pd.Timedelta(hours=off)
    return lt, lt.hour + lt.minute / 60.0


tip = pd.read_csv("tipoffs_espn.csv")
tip["utc_ts"] = pd.to_datetime(tip.utc, utc=True, format="mixed")
tip["home_city"] = tip.home_abbr.map(ABBR)
tip["away_city"] = tip.away_abbr.map(ABBR)
print(f"ESPN rows {len(tip):,};  unmapped abbrs: "
      f"{sorted(set(tip.home_abbr.dropna()) - set(ABBR))}")
tip = tip.dropna(subset=["home_city", "away_city"]).copy()

lt = [local_hour(t, c) for t, c in zip(tip.utc_ts, tip.home_city)]
tip["local_ts"] = [x[0] for x in lt]
tip["tip_hour"] = [x[1] for x in lt]
tip["local_date"] = tip.local_ts.dt.normalize()

raw = read_master(verbose=False)
raw["season"] = season_label(raw)
raw = raw[raw["season"].astype(str).str.contains(
    "Regular Season|In-Season", na=False)].copy()
m = pd.DataFrame({"gid": raw["GAME-ID"].astype(str).str.strip(),
                  "season": raw["season"].astype(str),
                  "date": pd.to_datetime(raw["DATE"]),
                  "home": raw["TEAM_H"].astype(str).str.strip(),
                  "away": raw["TEAM_R"].astype(str).str.strip(),
                  "rest_lab_H": raw["TEAM\nREST DAYS_H"].astype(str).str.strip(),
                  "rest_lab_R": raw["TEAM\nREST DAYS_R"].astype(str).str.strip()})
print(f"master rows {len(m):,};  sample teams {sorted(m.home.unique())[:4]}")

j = m.merge(tip[["local_date", "home_city", "away_city", "utc_ts", "local_ts",
                 "tip_hour", "espn_id"]],
            left_on=["date", "home", "away"],
            right_on=["local_date", "home_city", "away_city"], how="left")
print(f"\n=== GATE 1 CONTENT — join rate ===")
print(f"  matched {j.utc_ts.notna().sum():,}/{len(j):,} "
      f"({100*j.utc_ts.notna().mean():.2f}%)")
un = j[j.utc_ts.isna()]
if len(un):
    print(f"  unmatched by season:\n{un.season.value_counts().head(6).to_string()}")

# hours of rest: gap between this tip and the team's previous tip
long = pd.concat([
    j.assign(team=j.home, side="H"), j.assign(team=j.away, side="R")])
long = long.sort_values(["season", "team", "utc_ts"])
long["hours_gap"] = (long.groupby(["season", "team"])["utc_ts"]
                     .diff().dt.total_seconds() / 3600.0)
long["rest_lab"] = np.where(long.side == "H", long.rest_lab_H, long.rest_lab_R)
long["rest_days"] = long.rest_lab.map(REST_MAP)

print("\n=== GATE 1 CONTENT — hours_gap must track the vendor rest label ===")
g = long.dropna(subset=["hours_gap"]).groupby("rest_days")["hours_gap"]
print(f"  {'rest_days':>10}{'n':>8}{'mean h':>9}{'sd':>8}{'p5':>8}{'p95':>8}")
for k, s in g:
    print(f"  {k:>10.0f}{len(s):>8,}{s.mean():>9.1f}{s.std():>8.1f}"
          f"{s.quantile(.05):>8.1f}{s.quantile(.95):>8.1f}")

print("\n=== GATE 2 RANGE ===")
h = j.tip_hour.dropna()
print(f"  tip_hour  n={len(h):,}  min {h.min():.2f}  max {h.max():.2f}  "
      f"outside[10,24) = {int(((h < 10) | (h >= 24)).sum())}")
hg = long.hours_gap.dropna()
print(f"  hours_gap n={len(hg):,}  min {hg.min():.1f}  max {hg.max():.1f}  "
      f"below 15h = {int((hg < 15).sum())}")

print("\n=== GATE 3 ERA STABILITY — by season ===")
print(f"  {'season':<28}{'games':>7}{'join':>7}{'tip mean':>10}{'tip sd':>8}"
      f"{'late%':>7}{'early%':>8}")
rows = []
for s, gg in j.groupby("season"):
    t = gg.tip_hour.dropna()
    r = (len(gg), gg.utc_ts.notna().mean(), t.mean(), t.std(),
         (t >= 21).mean(), (t < 17).mean())
    rows.append(r)
    print(f"  {s[:28]:<28}{r[0]:>7,}{r[1]:>7.3f}{r[2]:>10.2f}{r[3]:>8.2f}"
          f"{100*r[4]:>7.1f}{100*r[5]:>8.1f}")
a = np.array([r[1:] for r in rows], float)
print("  max/min across seasons:  join "
      f"{a[:,0].max()/a[:,0].min():.2f}x   late-share "
      f"{a[:,3].max()/max(a[:,3].min(),1e-9):.2f}x   early-share "
      f"{a[:,4].max()/max(a[:,4].min(),1e-9):.2f}x")

print("\n=== KEY QUESTION — is there hours variation WITHIN a rest-day stratum? ===")
for k in (0, 1, 2, 3):
    s = long[(long.rest_days == k)].hours_gap.dropna()
    if len(s) < 50:
        continue
    print(f"  rest_days={k}: n={len(s):,}  IQR {s.quantile(.25):.1f}-"
          f"{s.quantile(.75):.1f}h  spread p5-p95 "
          f"{s.quantile(.95)-s.quantile(.05):.1f}h  sd {s.std():.1f}h")

keep = ["gid", "season", "date", "team", "side", "utc_ts", "tip_hour",
        "hours_gap", "rest_days"]
long[keep].to_csv("tip_time_panel.csv", index=False)
print(f"\nwrote tip_time_panel.csv ({len(long):,} team-games)")
