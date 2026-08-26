"""NATIONAL-TV STRUCTURE CHECKS — run BEFORE the prereg is finalised.
Broadcast/schedule data only. No score, no total, no dev."""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
from prepare_data import read_master, season_label
from tip_time_structure import ABBR, local_hour

tv = pd.read_csv("tipoffs_espn_tv.csv")
tv["utc_ts"] = pd.to_datetime(tv.utc, utc=True, format="mixed")
tv["home_city"] = tv.home_abbr.map(ABBR)
tv["away_city"] = tv.away_abbr.map(ABBR)
tv = tv.dropna(subset=["home_city", "away_city"]).copy()
lt = [local_hour(t, c) for t, c in zip(tv.utc_ts, tv.home_city)]
tv["tip_hour"] = [x[1] for x in lt]
tv["local_date"] = pd.Series([x[0] for x in lt]).dt.normalize().values
tv["bc_names"] = tv.bc_names.fillna("")

raw = read_master(verbose=False)
raw["season"] = season_label(raw)
raw = raw[raw["season"].astype(str).str.contains(
    "Regular Season|In-Season", na=False)].copy()
m = pd.DataFrame({"gid": raw["GAME-ID"].astype(str).str.strip().values,
                  "season": raw["season"].astype(str).values,
                  "date": pd.to_datetime(raw["DATE"]).values,
                  "home": raw["TEAM_H"].astype(str).str.strip().values,
                  "away": raw["TEAM_R"].astype(str).str.strip().values,
                  "to_close": pd.to_numeric(raw["CLOSING TOTAL_H"],
                                            errors="coerce").values,
                  "sp_close": pd.to_numeric(raw["CLOSING SPREAD_H"],
                                            errors="coerce").values})
j = m.merge(tv[["local_date", "home_city", "away_city", "bc_national",
                "bc_names", "tip_hour"]],
            left_on=["date", "home", "away"],
            right_on=["local_date", "home_city", "away_city"], how="left")

print(f"=== GATE 1 CONTENT — join {j.bc_national.notna().sum():,}/{len(j):,} "
      f"({100*j.bc_national.notna().mean():.2f}%) ===")

print("\n=== network composition of NATIONAL games ===")
net = (j[j.bc_national == 1].bc_names.str.split("|").explode()
       .str.strip().value_counts())
print(net.head(14).to_string())

print("\n=== GATE 3 ERA STABILITY — national share by season ===")
print(f"  {'season':<28}{'games':>7}{'nat%':>7}{'NBATV%':>8}{'ABC%':>7}"
      f"{'ESPN%':>7}{'TNT%':>7}{'other%':>8}")
rows = []
for s, g in j.groupby("season"):
    nm = g.bc_names.fillna("")
    def sh(pat):
        return 100 * nm.str.contains(pat, case=False, regex=True).mean()
    r = (len(g), 100*g.bc_national.mean(), sh(r"NBA ?TV"), sh(r"\bABC\b"),
         sh(r"ESPN"), sh(r"\bTNT\b"),
         100*g.bc_national.mean() - sh(r"NBA ?TV|\bABC\b|ESPN|\bTNT\b"))
    rows.append(r)
    print(f"  {s[:28]:<28}{r[0]:>7,}{r[1]:>7.1f}{r[2]:>8.1f}{r[3]:>7.1f}"
          f"{r[4]:>7.1f}{r[5]:>7.1f}{r[6]:>8.1f}")
a = np.array([r[1] for r in rows])
full = [r for r in rows if r[0] > 200]
af = np.array([r[1] for r in full])
print(f"  national share across FULL seasons: {af.min():.1f}%-{af.max():.1f}% "
      f"(ratio {af.max()/af.min():.2f}x)")

print("\n=== CONFOUNDING CHECK — national games are marquee games ===")
for lab, col in (("closing total", "to_close"), ("|closing spread|", "sp_close")):
    v = j[col].abs() if "spread" in lab else j[col]
    n1, n0 = v[j.bc_national == 1], v[j.bc_national == 0]
    print(f"  {lab:18} national {n1.mean():7.2f}   local {n0.mean():7.2f}"
          f"   diff {n1.mean()-n0.mean():+.2f}")
t1 = j[j.bc_national == 1].tip_hour
t0 = j[j.bc_national == 0].tip_hour
print(f"  {'tip hour (local)':18} national {t1.mean():7.2f}   local {t0.mean():7.2f}"
      f"   diff {t1.mean()-t0.mean():+.2f}")
print(f"  {'weekend share':18} national "
      f"{j[j.bc_national==1].date.dt.dayofweek.isin([5,6]).mean():7.3f}   local "
      f"{j[j.bc_national==0].date.dt.dayofweek.isin([5,6]).mean():7.3f}")

print("\n=== teams most often national (top 6) vs least (bottom 4) ===")
tm = pd.concat([j[["home", "bc_national"]].rename(columns={"home": "t"}),
                j[["away", "bc_national"]].rename(columns={"away": "t"})])
s = tm.groupby("t").bc_national.mean().sort_values(ascending=False)
print("  ", ", ".join(f"{k} {100*v:.0f}%" for k, v in s.head(6).items()))
print("  ", ", ".join(f"{k} {100*v:.0f}%" for k, v in s.tail(4).items()))

j.to_csv("tv_panel.csv", index=False)
print(f"\nwrote tv_panel.csv ({len(j):,} games)")
