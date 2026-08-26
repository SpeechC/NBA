"""
===============================================================================
 VALIDATION — does the probit line fix the attrition defect?
===============================================================================
 Four tests, in order of increasing consequence:

  A. AGREEMENT. On games the incumbent CAN price, mu must match
     median-crossing. Both estimate the p=0.5 point, so disagreement means the
     new estimator is broken rather than better.
  B. RECOVERY. How many games does it rescue, and are they the extreme ones
     the defect predicts?
  C. BIAS REMOVAL (WNBA). The +3.04-pt halftime "bias" was measured on the
     bracketed subset. Re-measure on the FULL sample. If it shrinks toward
     zero, the finding was attrition, as suspected.
  D. NBA SLOPE. s ~ 0.85 was measured on 279 of 361 games. Re-measure on all.
     If it rises, the under-reaction was partly selection too.

 A holdout-free check on A: agreement is measured on games where the incumbent
 works, so the probit fit is never tuned to match it -- there are no free
 parameters to tune.
===============================================================================
"""
import os
import pickle
import sqlite3
import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wnba_anchor_audit as A                                # noqa: E402
import wnba_reconcile as R                                   # noqa: E402
import clock_validation as CV                                # noqa: E402
import nba_anchor_audit as N                                 # noqa: E402
from implied_line import probit_line, median_cross           # noqa: E402


def ladders_at(db, like, stamps, tol=300):
    """-> {key: DataFrame[k, mid]} at each key's target timestamp."""
    con = sqlite3.connect(db)
    cd = pd.read_sql(
        "select ticker, event_ticker e, end_period_ts ts, yes_bid_close b, "
        f"yes_ask_close a from candles where period_interval=1 and ticker "
        f"like '{like}'", con)
    mk = pd.read_sql(f"select ticker, floor_strike k from markets where ticker "
                     f"like '{like}'", con)
    con.close()
    d = cd.dropna(subset=["b", "a"]).merge(mk, on="ticker")
    d["mid"] = (d.b + d.a) / 200.0
    d["key"] = d.e.str.split("-").str[1]
    d = d[d.key.isin(stamps)]
    d["tgt"] = d.key.map(stamps)
    d = d[(d.ts - d.tgt).abs() <= tol]
    out = {}
    for key, g in d.groupby("key"):
        i = (g.ts - g.tgt).abs().idxmin()
        t = g.loc[i, "ts"]
        gg = g[g.ts == t]
        if len(gg) >= 3:
            out[key] = gg[["k", "mid"]].astype(float)
    return out


def compare(lads, label):
    rows = []
    for key, g in lads.items():
        mc = median_cross(g.k.values, g.mid.values)
        pw = probit_line(g.k.values, g.mid.values, weighted=True)
        pu = probit_line(g.k.values, g.mid.values, weighted=False)
        rows.append({"key": key, "mc": mc, "pw": pw["mu"], "pu": pu["mu"],
                     "sigma": pw["sigma"], "n": pw["n"],
                     "brack": pw["bracketed"], "extrap": pw["extrap"],
                     "r2": pw["r2"]})
    d = pd.DataFrame(rows)
    both = d.dropna(subset=["mc", "pw"])
    print(f"\n{label}: {len(d)} ladders")
    print(f"  A. AGREEMENT where the incumbent works (n={len(both)})")
    for col, nm in (("pw", "weighted"), ("pu", "unweighted")):
        b2 = d.dropna(subset=["mc", col])
        diff = b2[col] - b2.mc
        print(f"     {nm:<11} corr {np.corrcoef(b2.mc, b2[col])[0,1]:.4f}  "
              f"mean diff {diff.mean():+.2f}  sd {diff.std():.2f}  "
              f"|diff|>1pt {(diff.abs()>1).mean():.1%}")
    got_mc = d.mc.notna().sum()
    got_pw = d.pw.notna().sum()
    print(f"  B. RECOVERY: median-crossing prices {got_mc}, probit prices "
          f"{got_pw}  (+{got_pw-got_mc}, {(got_pw-got_mc)/max(1,got_mc):+.0%})")
    rec = d[d.mc.isna() & d.pw.notna()]
    if len(rec):
        print(f"     rescued ladders: median extrapolation "
              f"{rec.extrap.median():.2f} sigma, median r2 {rec.r2.median():.3f}")
    return d


def main():
    # ---------- WNBA at the true halftime ----------
    ck = CV.load_clocks("espn_clocks_wnba.csv", CV.ESPN_WNBA)
    ds = ck.date.astype(str)
    M = {f"{i:02d}": m for i, m in enumerate(
        ["", "JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP",
         "OCT", "NOV", "DEC"])}
    ck["key"] = ds.str[2:4] + ds.str[4:6].map(M) + ds.str[6:8] + ck.ac + ck.hc
    stamps = dict(zip(ck.key, ck.half_ts + 180))
    lw = ladders_at("/mnt/c/NBA2/Kalshi/data/kalshi_wnba_candles.sqlite",
                    "KXWNBATOTAL%", stamps)
    dw = compare(lw, "WNBA halftime (buzzer+3)")

    bref = R.bref_totals(R.BREF)
    dw["total"] = [(R.bref_lookup("KXWNBATOTAL-" + k, bref) or (np.nan,)*3)[0]
                   for k in dw.key]
    allg = pd.read_csv(R.BREF)
    allg["tot"] = allg.a_final + allg.h_final
    print("\n  C. BIAS REMOVAL — mean(total - L) at halftime")
    for col, nm in (("mc", "median-crossing (incumbent)"),
                    ("pw", "probit (bracketing-free)")):
        s = dw.dropna(subset=[col, "total"])
        e = s.total - s[col]
        rng = np.random.default_rng(4)
        bs = [rng.choice(e.values, len(e), True).mean() for _ in range(4000)]
        lo, hi = np.percentile(bs, [2.5, 97.5])
        print(f"     {nm:<30} n={len(s):>3}  {e.mean():+.2f} pts "
              f"CI [{lo:+.2f},{hi:+.2f}]  sample mean total {s.total.mean():.1f}")
    print(f"     {'league (all bref games)':<30} n={len(allg):>3}  "
          f"{'':>14}  sample mean total {allg.tot.mean():.1f}")

    # ---------- NBA halftime slope ----------
    series, meta = N.build_series()
    m = N.load_master(meta)
    ckn = CV.load_clocks("espn_clocks_nba.csv", CV.ESPN_NBA)
    dsn = ckn.date.astype(str)
    ckn["key"] = (dsn.str[:4] + "-" + dsn.str[4:6] + "-" + dsn.str[6:8] + "|"
                  + ckn.ac + "@" + ckn.hc)
    m["key"] = m.date.dt.strftime("%Y-%m-%d") + "|" + m.ac + "@" + m.hc
    m = m.merge(ckn[["key", "half_ts"]], on="key", how="inner").dropna(
        subset=["event", "half_ts"])
    m["ekey"] = m.event.str.split("-").str[1]
    stamps_n = dict(zip(m.ekey, m.half_ts + 180))
    ln = ladders_at("/mnt/c/NBA2/Kalshi/data/kalshi_nba_candles.sqlite",
                    "KXNBATOTAL%", stamps_n)
    dn = compare(ln, "NBA halftime (buzzer+3)")
    mm = m.merge(dn, left_on="ekey", right_on="key", how="inner")
    print("\n  D. NBA SLOPE — L_half ~ pre + H1")
    for col, nm in (("mc", "median-crossing (incumbent)"),
                    ("pw", "probit (bracketing-free)")):
        s = mm.dropna(subset=[col, "pre", "h1"])
        b, se = A.ols(s[col].values, [s.pre.values, s.h1.values], ["pre", "h1"])
        print(f"     {nm:<30} n={len(s):>3}  s(H1) {b['h1']:.3f} "
              f"(se {se['h1']:.3f})  b(pre) {b['pre']:.3f}")
    s = mm.dropna(subset=["pw", "pre", "h1"])
    br, ser = A.ols(s.total.values, [s.pre.values, s.h1.values], ["pre", "h1"])
    print(f"     {'realized benchmark':<30} n={len(s):>3}  s(H1) {br['h1']:.3f} "
          f"(se {ser['h1']:.3f})")


if __name__ == "__main__":
    main()
