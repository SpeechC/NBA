"""
===============================================================================
 MODEL-FREE CONTROL — does buying the OVER at the halftime line simply pay?
===============================================================================
 Measured claim: mean(total - L_half) = +2.98 pts (CI [+1.12,+4.92], n=188),
 while the SAME games are calibrated pregame. If that is real, a blind rule
 with NO model should capture it. If instead only the model-selected subset
 pays, the model is doing the work. If NEITHER pays after costs, the bias is
 real but sub-economic.

 The rule, deliberately stupid: at the true halftime buzzer, buy YES at the
 ask of the rung nearest the crossing. No E, no CDF, no thresholds, no rung
 selection. Held to settlement. Cost = ask + 0.07*ask*(1-ask).

 Controls run against it, each of which has killed a pattern earlier today:
   1. by MONTH        - is it one hot stretch (the August overs cell)?
   2. OT EXCLUDED     - 3.7% of games add ~15 pts; is it just overtime?
   3. ATTRITION       - are the bracketed games unrepresentative?
   4. ENTRY TIMING    - buzzer +0 / +3 / +6; a real edge should not expire
   5. RUNG CHOICE     - crossing vs every rung; is it a level or a shape?
   6. vs the MODEL    - does conditioning on the model's BUY YES add anything?
 All CIs cluster-bootstrapped by game.

 RESULTS (2026-08-25) — THE CONTROL DOES NOT CONFIRM A TRADEABLE EDGE.

 Blind rule, buy the over at the crossing rung, buzzer+3, n=186:
   raw bias +3.04 pts, over-rate 56.5%, hit 58%, ROI +8.8%
   BUT 95% CI [-5.0%, +22.3%] -- CROSSES ZERO.
 The +3-point level bias is real; the TRADE built on it is not established.

 Every control weakens it further:
  1. MONTH: +19.7 / +6.7 / +15.8 / -1.6 %. August is negative. Not persistent.
  2. OT: excluding overtime drops ROI +8.8% -> +6.6%, so ~1/4 of the raw
     figure is the 5 OT games. A 3.7%-frequency tail is doing real work.
  3. ATTRITION: the graded subset means 177.9 vs 174.7 for all bref games --
     the bracketed sample is +3.2 pts HIGHER SCORING than the league. That is
     almost exactly the size of the claimed bias, and it is selection, not
     alpha.
  4. TIMING: +4.9 / +8.8 / +5.4 / +6.2% at buzzer +0/+3/+6/+12. Stable, which
     is the one control it passes cleanly.
  5. RUNG: the entire result lives in the 0.45-0.55 entry band (+17.4%, CI
     [+1.2,+32.6], n=135). Both 0.30-0.45 (-1.8%) and 0.55-0.70 (-16.4%) are
     negative. A genuine level bias should pay across the ladder, not only at
     the money.
  6. MODEL ADDS NOTHING, and is inverted: where the model says OVER it returns
     +1.4%; where it says UNDER it returns +22.3%. The deployment rule is
     anti-correlated with what actually paid.

 VERDICT: the halftime line IS low by ~3 points, but that is substantially
 attrition (bracketed games score +3.2 above league), partly overtime, absent
 in August, confined to at-the-money rungs, and its CI crosses zero. Point 6
 also kills the reading that tonight's PDX@DAL BUY YES signals are the edge:
 the model's direction is the losing side historically.

 Read-only.
===============================================================================
"""
import json
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

RULE = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "wnba_deploy_rule.json")))
RNG = np.random.default_rng(17)


def fee(p):
    return 0.07 * p * (1 - p)


def build(offset_min=3):
    con = sqlite3.connect("/mnt/c/NBA2/Kalshi/data/kalshi_wnba_candles.sqlite")
    cd = pd.read_sql(
        "select ticker, event_ticker e, end_period_ts ts, yes_bid_close b, "
        "yes_ask_close a from candles where period_interval=1 and ticker "
        "like 'KXWNBATOTAL%'", con)
    mkm = pd.read_sql("select ticker, floor_strike k from markets where ticker "
                      "like 'KXWNBATOTAL%'", con)
    con.close()
    cd = cd.dropna(subset=["b", "a"]).merge(mkm, on="ticker")
    cd["mid"] = (cd.b + cd.a) / 200.0
    cd["key"] = cd.e.str.split("-").str[1]
    ck = CV.load_clocks("espn_clocks_wnba.csv", CV.ESPN_WNBA)
    ds = ck.date.astype(str)
    M = {f"{i:02d}": m for i, m in enumerate(
        ["", "JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP",
         "OCT", "NOV", "DEC"])}
    ck["key"] = ds.str[2:4] + ds.str[4:6].map(M) + ds.str[6:8] + ck.ac + ck.hc
    ck["mo"] = ds.str[4:6]
    cd = cd.merge(ck[["key", "half_ts", "mo"]], on="key")
    bref = R.bref_totals(R.BREF)
    ser = pickle.load(open("/tmp/claude-1000/wnba_L.pkl", "rb"))
    panel = pd.read_csv(A.PANEL)
    pre_by = dict(zip(panel.event_ticker, panel.L_pre))
    tgt = cd.half_ts + offset_min * 60
    snap = cd.loc[(cd.ts - tgt).abs().groupby(cd.ticker).idxmin()].copy()
    snap = snap[(snap.ts - snap.half_ts - offset_min * 60).abs() <= 300]
    rows = []
    for key, g in snap.groupby("key"):
        ev = "KXWNBATOTAL-" + key
        hit = R.bref_lookup(ev, bref)
        if not hit or len(g) < 4:
            continue
        total, h1, n_ot = hit
        q = g.sort_values("k")
        L = A.median_cross(q.k.values.astype(float), q.mid.values)
        if L is None or not np.isfinite(L):
            continue
        # the rung nearest the crossing -- no model input of any kind
        i = (q.mid - 0.5).abs().values.argmin()
        r = q.iloc[i]
        E = (RULE["a"] + RULE["b"] * pre_by[ev] + RULE["c"] * h1
             if ev in pre_by else np.nan)
        rows.append({"key": key, "mo": g.mo.iloc[0], "L": L, "total": total,
                     "h1": h1, "n_ot": n_ot, "K": float(r.k),
                     "ask": r.a / 100.0, "bid": r.b / 100.0, "E": E,
                     "n_rungs": len(g)})
    return pd.DataFrame(rows), snap, bref


def grade(d):
    d = d.copy()
    d["cost"] = d.ask + fee(d.ask)
    d["win"] = (d.total > d.K).astype(float)
    d["pnl"] = np.where(d.win > 0, 1 - d.cost, -d.cost)
    return d


def ci(d, col="pnl", B=4000):
    ev = d.key.unique()
    by = {k: d.loc[d.key == k, col].values for k in ev}
    out = [np.concatenate([by[x] for x in RNG.choice(ev, len(ev), True)]).mean()
           for _ in range(B)]
    return np.percentile(out, [2.5, 97.5])


def line(lab, d):
    if len(d) < 8:
        print(f"  {lab:<34} n={len(d):>3}   too few")
        return
    lo, hi = ci(d)
    roi = d.pnl.sum() / d.cost.sum()
    rl, rh = [x * len(d) / d.cost.sum() for x in (lo, hi)]
    print(f"  {lab:<34} n={len(d):>3} hit {d.win.mean():>4.0%} "
          f"cost {d.cost.mean():.2f} P&L {d.pnl.sum():>+7.2f} "
          f"ROI {roi:>+6.1%} CI [{rl:+.1%},{rh:+.1%}]")


def main():
    d, snap, bref = build(3)
    d = grade(d)
    print(f"BLIND RULE: buy the OVER at the crossing rung, halftime buzzer+3\n")
    print(f"  raw bias check: mean(total - L) = {(d.total-d.L).mean():+.2f} pts, "
          f"over-rate {(d.total>d.L).mean():.1%}, n={len(d)}\n")
    line("ALL GAMES (the control)", d)
    print("\n 1. BY MONTH — one hot stretch, or persistent?")
    for m, g in d.groupby("mo"):
        line(f"    month {m}", g)
    print("\n 2. OVERTIME — is it just OT points?")
    line("    OT games EXCLUDED", d[d.n_ot == 0])
    line("    OT games only", d[d.n_ot > 0])
    print("\n 3. ATTRITION — are bracketed games unrepresentative?")
    allg = pd.read_csv(R.BREF)
    allg["tot"] = allg.a_final + allg.h_final
    print(f"    all bref games   n={len(allg)} mean total {allg.tot.mean():.1f} "
          f"sd {allg.tot.std():.1f}")
    print(f"    graded subset    n={len(d)} mean total {d.total.mean():.1f} "
          f"sd {d.total.std():.1f}")
    print("\n 4. ENTRY TIMING — a real edge should not expire in minutes")
    for off in (0, 6, 12):
        dd, _, _ = build(off)
        line(f"    buzzer +{off} min", grade(dd))
    print("\n 5. RUNG CHOICE — level effect, or only at the money?")
    for lo, hi in ((0.30, 0.45), (0.45, 0.55), (0.55, 0.70)):
        line(f"    entry ask {lo:.2f}-{hi:.2f}",
             d[(d.ask >= lo) & (d.ask < hi)])
    print("\n 6. DOES THE MODEL ADD ANYTHING?")
    m = d.dropna(subset=["E"])
    line("    model says over (E > L)", m[m.E > m.L])
    line("    model says under (E < L)", m[m.E < m.L])
    line("    model disagrees strongly (E-L>3)", m[m.E - m.L > 3])


if __name__ == "__main__":
    main()
