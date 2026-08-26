"""
===============================================================================
 MODEL-FREE HALFTIME-OVER CONTROL, RERUN ON THE PROBIT ESTIMATOR
===============================================================================
 The first control (halftime_over_control.py) priced the line by
 median-crossing, so it ran on 186 bracketed games whose mean total was 177.9
 against a league 174.7 -- and the +3.2-pt selection was roughly the whole
 claimed bias. `implied_line.probit_line` removes the bracketing requirement,
 which brings 238 games and cuts the selection to +1.4 pts. This asks the same
 question on the better sample:

   does a blind "buy the over at the halftime line" rule actually pay?

 Same deliberately stupid rule: at the true halftime buzzer, buy YES at the
 ask of the rung nearest the implied line. No E, no CDF, no thresholds.
 Cost = ask + 0.07*ask*(1-ask), held to settlement. CIs cluster-bootstrapped.

 Same controls as before, plus the two new diagnostics the probit fit provides
 (extrapolation distance and ladder fit quality), since the NBA under-reaction
 turned out to live entirely in the low-r2 subset.
===============================================================================
"""
import os
import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wnba_reconcile as R                                   # noqa: E402
import clock_validation as CV                                # noqa: E402
import implied_line_validate as V                            # noqa: E402
import wnba_anchor_audit as A                                # noqa: E402
from implied_line import probit_line, median_cross           # noqa: E402

RNG = np.random.default_rng(23)
DB = "/mnt/c/NBA2/Kalshi/data/kalshi_wnba_candles.sqlite"


def fee(p):
    return 0.07 * p * (1 - p)


def build(offset_min=3):
    """One snapshot per game at buzzer+offset: strikes, bids, asks together.

    NB: mu and the traded quotes MUST come from the SAME timestamp. An earlier
    version derived mu from one snapshot and priced the fill from whichever
    timestamp happened to be most common in the candle rows, which silently
    mixed moments.
    """
    ck = CV.load_clocks("espn_clocks_wnba.csv", CV.ESPN_WNBA)
    ds = ck.date.astype(str)
    M = {f"{i:02d}": m for i, m in enumerate(
        ["", "JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP",
         "OCT", "NOV", "DEC"])}
    ck["key"] = ds.str[2:4] + ds.str[4:6].map(M) + ds.str[6:8] + ck.ac + ck.hc
    ck["mo"] = ds.str[4:6]
    stamps = dict(zip(ck.key, ck.half_ts + offset_min * 60))
    mo = dict(zip(ck.key, ck.mo))
    con = __import__("sqlite3").connect(DB)
    cd = pd.read_sql("select ticker, event_ticker e, end_period_ts ts, "
                     "yes_bid_close b, yes_ask_close a from candles where "
                     "period_interval=1 and ticker like 'KXWNBATOTAL%'", con)
    mk = pd.read_sql("select ticker, floor_strike k from markets where ticker "
                     "like 'KXWNBATOTAL%'", con)
    con.close()
    cd = cd.dropna(subset=["b", "a"]).merge(mk, on="ticker")
    cd["key"] = cd.e.str.split("-").str[1]
    cd = cd[cd.key.isin(stamps)]
    cd["tgt"] = cd.key.map(stamps)
    cd = cd[(cd.ts - cd.tgt).abs() <= 300]
    bref = R.bref_totals(R.BREF)
    rows = []
    for key, g in cd.groupby("key"):
        t = g.ts.iloc[(g.ts - g.tgt).abs().values.argmin()]
        snap = g[g.ts == t]                      # ONE timestamp, all rungs
        if len(snap) < 3:
            continue
        hit = R.bref_lookup("KXWNBATOTAL-" + key, bref)
        if not hit:
            continue
        total, h1, n_ot = hit
        mid = ((snap.b + snap.a) / 200.0).values
        kk = snap.k.values.astype(float)
        p = probit_line(kk, mid, weighted=True)
        if not np.isfinite(p["mu"]):
            continue
        i = np.abs(kk - p["mu"]).argmin()        # rung nearest the line
        r = snap.iloc[i]
        rows.append({"key": key, "mo": mo.get(key), "mu": p["mu"],
                     "sigma": p["sigma"], "r2": p["r2"], "extrap": p["extrap"],
                     "mc": median_cross(kk, mid), "total": total, "h1": h1,
                     "n_ot": n_ot, "K": float(r.k), "ask": r.a / 100.0,
                     "bid": r.b / 100.0})
    d = pd.DataFrame(rows)
    d["cost"] = d.ask + fee(d.ask)
    d["win"] = (d.total > d.K).astype(float)
    d["pnl"] = np.where(d.win > 0, 1 - d.cost, -d.cost)
    return d


def line(lab, d):
    if len(d) < 10:
        print(f"  {lab:<36} n={len(d):>3}   too few")
        return
    ev = d.key.unique()
    by = {k: d.loc[d.key == k, "pnl"].values for k in ev}
    bs = [np.concatenate([by[x] for x in RNG.choice(ev, len(ev), True)]).mean()
          for _ in range(4000)]
    lo, hi = np.percentile(bs, [2.5, 97.5])
    c = d.cost.mean()
    print(f"  {lab:<36} n={len(d):>3} hit {d.win.mean():>4.0%} "
          f"ROI {d.pnl.sum()/d.cost.sum():>+6.1%} "
          f"CI [{lo/c:+.1%},{hi/c:+.1%}]")


def main():
    d = build(3)
    allg = pd.read_csv(R.BREF)
    allg["tot"] = allg.a_final + allg.h_final
    print("BLIND OVER AT THE HALFTIME LINE — probit estimator\n")
    print(f"  games {len(d)} (median-crossing managed 186)")
    print(f"  sample mean total {d.total.mean():.1f} vs league "
          f"{allg.tot.mean():.1f}  -> residual selection "
          f"+{d.total.mean()-allg.tot.mean():.1f} pts (was +3.2)")
    print(f"  raw bias mean(total - mu) = {(d.total-d.mu).mean():+.2f} pts, "
          f"over-rate {(d.total>d.mu).mean():.1%}\n")
    line("ALL GAMES (the control)", d)
    print("\n 1. BY MONTH")
    for m, g in d.groupby("mo"):
        line(f"    month {m}", g)
    print("\n 2. OVERTIME")
    line("    OT excluded", d[d.n_ot == 0])
    print("\n 3. LADDER QUALITY (new diagnostic)")
    line("    r2 >= 0.95 (well determined)", d[d.r2 >= 0.95])
    line("    r2 < 0.95", d[d.r2 < 0.95])
    line("    interpolated (extrap=0)", d[d.extrap <= 0.001])
    line("    extrapolated", d[d.extrap > 0.001])
    print("\n 4. RECOVERED vs INCUMBENT SAMPLE")
    line("    games median-crossing could price", d[d.mc.notna()])
    line("    games ONLY probit can price", d[d.mc.isna()])
    print("\n 5. ENTRY TIMING")
    for off in (0, 6, 12):
        line(f"    buzzer +{off} min", build(off))
    print("\n 6. ENTRY PRICE BAND")
    for lo, hi in ((0.30, 0.45), (0.45, 0.55), (0.55, 0.70)):
        line(f"    ask {lo:.2f}-{hi:.2f}", d[(d.ask >= lo) & (d.ask < hi)])


if __name__ == "__main__":
    main()
