"""
===============================================================================
 CLOCK ALIGNMENT CHECK — is the ESPN game clock really lined up with Kalshi?
===============================================================================
 clock_validation.py assumes the ESPN wallclock and the Kalshi candle
 timestamps refer to the same instants. That assumption is exactly the kind
 that produced the original anchor bug, so it gets tested rather than trusted.

 The test uses a PHYSICAL feature of the game that involves no prices, no
 outcomes and no anchor: the NBA halftime break is ~15 minutes during which no
 basketball is played. If our alignment is correct, Kalshi trading volume must
 show a trough in [buzzer, buzzer+15] and recover exactly at +15. A clock off
 by even five minutes would visibly shift that trough.

 Read-only; prints a volume profile.
===============================================================================
"""
import os
import sqlite3
import sys
import warnings

import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import clock_validation as CV                                # noqa: E402
import nba_anchor_audit as N                                 # noqa: E402


def main():
    ck = CV.load_clocks("espn_clocks_nba.csv", CV.ESPN_NBA)
    con = sqlite3.connect(N.CANDLES)
    v = pd.read_sql("select event_ticker e, end_period_ts t, sum(volume) v "
                    "from candles where period_interval=1 group by 1,2", con)
    meta = pd.read_sql("select distinct event_ticker e, away_team, home_team, "
                       "game_date from markets", con)
    con.close()
    meta["key"] = (meta.game_date.astype(str) + "|" + meta.away_team + "@"
                   + meta.home_team)
    ds = ck.date.astype(str)
    ck["key"] = (ds.str[:4] + "-" + ds.str[4:6] + "-" + ds.str[6:8] + "|"
                 + ck.ac + "@" + ck.hc)
    j = ck.merge(meta, on="key", how="inner")
    halfm = dict(zip(j.e, j.half_ts))
    print(f"games with both a real clock and candle volume: {len(j)}\n")

    v = v[v.e.isin(halfm)].copy()
    v["rel"] = (v.t - v.e.map(halfm)) / 60.0
    p = v[v.rel.between(-40, 45)].copy()
    p["bin"] = (p.rel // 5 * 5).astype(int)
    g = p.groupby("bin").v.median()
    mx = g.max()
    print("median Kalshi volume per minute, relative to the REAL halftime buzzer")
    for b in sorted(g.index):
        tag = "  <-- the 15-min break" if 0 <= b < 15 else ""
        print(f"   buzzer{b:+4d}..{b + 5:+4d}  {g[b]:>7.0f}  "
              f"{'#' * int(min(60, g[b] / mx * 60))}{tag}")
    brk = g[(g.index >= 0) & (g.index < 15)].mean()
    play = g[((g.index >= -20) & (g.index < 0))
             | ((g.index >= 15) & (g.index < 35))].mean()
    print(f"\n   break window mean   {brk:,.0f}/min")
    print(f"   surrounding play    {play:,.0f}/min")
    print(f"   ratio {brk / play:.2f} — a correctly aligned clock puts the "
          f"trough exactly here and the recovery exactly at +15.")


if __name__ == "__main__":
    main()
