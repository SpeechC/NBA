"""
===============================================================================
 NBA HALFTIME SLOPE — FULL 2025-26 SEASON, PROBIT ESTIMATOR
===============================================================================
 Every previous NBA slope estimate ran on the Oct-Dec candle capture (429
 games) with median-crossing, which needs the ladder to bracket 0.5 and so
 dropped ~20% of games -- the extreme ones. Two things have changed:

   - `kalshi_nba_triangle.sqlite` now holds KXNBATOTAL for the WHOLE season
     (1,324 events, 2025-10-21 .. 2026-06-13), harvested via
     /historical/markets
   - `implied_line.probit_line` prices a ladder without a crossing

 So the slope can finally be measured on the full season with no bracketing
 selection. The question it settles: is the NBA halftime under-reaction real,
 or was it -- as the Aug-26 diagnostic suggested -- an attenuation artefact
 living in badly-determined ladders?

 Benchmarks: efficient s = 1 + gamma, and gamma is ~0 on 9,489 master games,
 so the bar is 1.0. The realized regression on the same sample is reported
 alongside every estimate as an internal control.
===============================================================================
"""
import os
import sqlite3
import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wnba_anchor_audit as A                                # noqa: E402
import clock_validation as CV                                # noqa: E402
from prepare_data import CSV, season_label                   # noqa: E402
from implied_line import probit_line, median_cross           # noqa: E402

DB = "/mnt/c/NBA2/Kalshi/data/kalshi_nba_triangle.sqlite"
CODE = {"Atlanta": "ATL", "Boston": "BOS", "Brooklyn": "BKN",
        "Charlotte": "CHA", "Chicago": "CHI", "Cleveland": "CLE",
        "Dallas": "DAL", "Denver": "DEN", "Detroit": "DET",
        "Golden State": "GSW", "Houston": "HOU", "Indiana": "IND",
        "LA Clippers": "LAC", "Los Angeles Clippers": "LAC",
        "LA Lakers": "LAL", "Los Angeles Lakers": "LAL",
        "Los Angeles": "LAL", "Memphis": "MEM", "Miami": "MIA",
        "Milwaukee": "MIL", "Minnesota": "MIN", "New Orleans": "NOP",
        "New York": "NYK", "Oklahoma City": "OKC", "Orlando": "ORL",
        "Philadelphia": "PHI", "Phoenix": "PHX", "Portland": "POR",
        "Sacramento": "SAC", "San Antonio": "SAS", "Toronto": "TOR",
        "Utah": "UTA", "Washington": "WAS"}


def master():
    raw = pd.read_csv(CSV, low_memory=False)
    raw["season"] = season_label(raw).astype(str)
    d = raw[raw["season"].str.contains("Regular Season", na=False)].copy()
    d["date"] = pd.to_datetime(d["DATE"], errors="coerce")
    d = d[d.date >= "2025-10-01"].copy()
    for c in ("1Q_H", "2Q_H", "1Q_R", "2Q_R", "PTS_H", "PTS_R",
              "CLOSING TOTAL_H"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["h1"] = d["1Q_H"] + d["2Q_H"] + d["1Q_R"] + d["2Q_R"]
    d["total"] = d["PTS_H"] + d["PTS_R"]
    d["pre"] = d["CLOSING TOTAL_H"]
    d["ac"], d["hc"] = d["TEAM_R"].map(CODE), d["TEAM_H"].map(CODE)
    d["ekey"] = (d.date.dt.strftime("%y") + d.date.dt.strftime("%b").str.upper()
                 + d.date.dt.strftime("%d") + d.ac + d.hc)
    return d.dropna(subset=["h1", "total", "pre", "ac", "hc"])


def halftimes():
    ck = CV.load_clocks("espn_clocks_nba.csv", CV.ESPN_NBA)
    ds = ck.date.astype(str)
    ck["ekey"] = (ds.str[2:4] + pd.to_datetime(ds, format="%Y%m%d")
                  .dt.strftime("%b").str.upper() + ds.str[6:8]
                  + ck.ac + ck.hc)
    return dict(zip(ck.ekey, ck.half_ts))


def snapshots(stamps, offset_min=3, tol=300):
    con = sqlite3.connect(DB)
    cd = pd.read_sql("select ticker, event_ticker e, end_period_ts ts, "
                     "yes_bid_close b, yes_ask_close a from candles where "
                     "period_interval=1 and ticker like 'KXNBATOTAL-%'", con)
    mk = pd.read_sql("select ticker, floor_strike k from markets where ticker "
                     "like 'KXNBATOTAL-%'", con)
    con.close()
    d = cd.dropna(subset=["b", "a"]).merge(mk, on="ticker")
    d["ekey"] = d.e.str.split("-").str[1]
    d = d[d.ekey.isin(stamps)]
    d["tgt"] = d.ekey.map(stamps) + offset_min * 60
    d = d[(d.ts - d.tgt).abs() <= tol]
    rows = []
    for key, g in d.groupby("ekey"):
        t = g.ts.iloc[(g.ts - g.tgt).abs().values.argmin()]
        s = g[g.ts == t]
        if len(s) < 3:
            continue
        mid = ((s.b + s.a) / 200.0).values
        kk = s.k.values.astype(float)
        p = probit_line(kk, mid, weighted=True)
        rows.append({"ekey": key, "mu": p["mu"], "sigma": p["sigma"],
                     "r2": p["r2"], "extrap": p["extrap"], "n_rungs": p["n"],
                     "mc": median_cross(kk, mid),
                     "spread": float((s.a - s.b).median())})
    return pd.DataFrame(rows)


def fit(d, col, lab):
    s = d.dropna(subset=[col, "pre", "h1"])
    if len(s) < 30:
        print(f"   {lab:<38} n={len(s):>4}  too few")
        return
    b, se = A.ols(s[col].values, [s.pre.values, s.h1.values], ["pre", "h1"])
    br, ser = A.ols(s.total.values, [s.pre.values, s.h1.values], ["pre", "h1"])
    gap = b["h1"] - br["h1"]
    print(f"   {lab:<38} n={len(s):>4}  s={b['h1']:.3f} ({se['h1']:.3f})  "
          f"bench={br['h1']:.3f}  gap={gap:+.3f}  "
          f"t={(b['h1']-1.0)/se['h1']:+.1f} vs 1.0")


def main():
    m = master()
    st = halftimes()
    print(f"master 2025-26 games {len(m)}; ESPN halftimes {len(st)}")
    snap = snapshots(st)
    d = m.merge(snap, on="ekey", how="inner")
    print(f"joined with a halftime ladder: {len(d)} games "
          f"(prior NBA estimates used 220-324)\n")
    print(f"  date span {d.date.min().date()} .. {d.date.max().date()}")
    print(f"  median ladder spread {d.spread.median():.1f}c, "
          f"median rungs used {d.n_rungs.median():.0f}\n")
    print("FULL-SEASON SLOPE  (efficient bar = 1.0; gamma ~ 0 on 9,489 games)")
    fit(d, "mc", "median-crossing (bracketed only)")
    fit(d, "mu", "probit, ALL games")
    print("\n by ladder fit quality — where the Aug-26 diagnostic said it lived:")
    fit(d[d.r2 >= 0.95], "mu", "   r2 >= 0.95 (well determined)")
    fit(d[d.r2 < 0.95], "mu", "   r2 < 0.95")
    print("\n by extrapolation:")
    fit(d[d.extrap <= 0.001], "mu", "   interpolated")
    fit(d[d.extrap > 0.001], "mu", "   extrapolated")
    print("\n by half of season (is it stable?):")
    mid = d.date.median()
    fit(d[d.date <= mid], "mu", f"   first half (to {str(mid.date())})")
    fit(d[d.date > mid], "mu", "   second half")
    print("\n by ladder spread (quote quality):")
    q = d.spread.median()
    fit(d[d.spread <= q], "mu", f"   tight ladders (<= {q:.0f}c)")
    fit(d[d.spread > q], "mu", f"   wide ladders (> {q:.0f}c)")


if __name__ == "__main__":
    main()
