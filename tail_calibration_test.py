"""
===============================================================================
 TEST 1 — LADDER-TAIL CALIBRATION (favorite-longshot bias)
===============================================================================
 The market concentrates on the crossing rung; the wings are priced by nobody.
 Favorite-longshot bias predicts LONGSHOTS (cheap YES) resolve LESS often than
 priced and FAVOURITES (dear YES) resolve MORE often. Kalshi's fee is
 0.07*p*(1-p), which is near-zero at the extremes -- the one part of the
 ladder where the toll booth is almost free.

 Method: every settled rung across all six harvested board families. For each,
 take the price at a fixed pregame anchor (last bracketed bar before tip is not
 required here -- we use each market's own last quote at or before the anchor),
 bucket by price, and compare mean price to realized YES rate. Fees applied at
 the bucket's own price. Buying YES pays (1 - cost) on a win; buying NO pays
 (1 - (1-p) - fee) analogously, so both directions are reported.

 Bias direction is stated BEFORE looking: longshot buckets should UNDER-resolve
 (so the edge is selling them / buying NO), favourite buckets should
 OVER-resolve (edge is buying YES).

 Read-only. Uses the candle stores plus each market's settlement `result`.
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

DBS = [("full", "/mnt/c/NBA2/Kalshi/data/kalshi_wnba_candles.sqlite", "KXWNBATOTAL%"),
       ("1H", "/mnt/c/NBA2/Kalshi/data/kalshi_wnba_halves.sqlite", "KXWNBA1HTOTAL%"),
       ("2H", "/mnt/c/NBA2/Kalshi/data/kalshi_wnba_halves.sqlite", "KXWNBA2HTOTAL%"),
       ("Q1", "/mnt/c/NBA2/Kalshi/data/kalshi_wnba_halves.sqlite", "KXWNBA1QTOTAL%"),
       ("Q2", "/mnt/c/NBA2/Kalshi/data/kalshi_wnba_halves.sqlite", "KXWNBA2QTOTAL%"),
       ("Q3", "/mnt/c/NBA2/Kalshi/data/kalshi_wnba_halves.sqlite", "KXWNBA3QTOTAL%"),
       ("Q4", "/mnt/c/NBA2/Kalshi/data/kalshi_wnba_halves.sqlite", "KXWNBA4QTOTAL%")]
BUCKETS = [(0.01, 0.05), (0.05, 0.10), (0.10, 0.20), (0.20, 0.35),
           (0.35, 0.65), (0.65, 0.80), (0.80, 0.90), (0.90, 0.95),
           (0.95, 0.99)]


def fee(p):
    return 0.07 * p * (1 - p)


def pull(tag, db, like):
    con = sqlite3.connect(db)
    mk = pd.read_sql(
        "select ticker, event_ticker, result, close_ts from markets "
        f"where result in ('yes','no') and ticker like '{like}'", con)
    if not len(mk):
        con.close()
        return pd.DataFrame()
    cd = pd.read_sql(
        "select ticker, end_period_ts ts, yes_bid_close b, yes_ask_close a "
        f"from candles where period_interval=1 and ticker like '{like}'", con)
    con.close()
    cd = cd.dropna(subset=["b", "a"])
    if not len(cd):
        return pd.DataFrame()
    cd["mid"] = (cd.b + cd.a) / 200.0
    cd["spread"] = (cd.a - cd.b)
    m = cd.merge(mk[["ticker", "result", "close_ts"]], on="ticker", how="inner")
    # PREGAME anchor: the market's earliest quoted bar is deep pregame; take
    # the bar nearest (close - 4h) which precedes tip for these boards.
    m["delta"] = (m.ts - (m.close_ts - 4 * 3600)).abs()
    idx = m.groupby("ticker").delta.idxmin()
    s = m.loc[idx].copy()
    s["board"] = tag
    s["win"] = (s.result == "yes").astype(int)
    return s[["board", "ticker", "mid", "spread", "win"]]


def main():
    parts = [pull(t, d, l) for t, d, l in DBS]
    d = pd.concat([p for p in parts if len(p)], ignore_index=True)
    d = d[(d.mid > 0) & (d.mid < 1)]
    print(f"settled rungs with a pregame quote: {len(d):,} across "
          f"{d.board.nunique()} board families\n")
    print("TAIL CALIBRATION — priced vs realized")
    print(f"  {'price band':>12} {'n':>6} {'mean price':>11} {'realized':>10} "
          f"{'diff':>8} {'spread':>8}  {'YES edge':>9} {'NO edge':>8}")
    rows = []
    for lo, hi in BUCKETS:
        s = d[(d.mid >= lo) & (d.mid < hi)]
        if len(s) < 30:
            continue
        p, r = s.mid.mean(), s.win.mean()
        se = np.sqrt(r * (1 - r) / len(s))
        ey = r - p - fee(p)
        en = (1 - r) - (1 - p) - fee(p)
        rows.append((lo, hi, len(s), p, r, se, ey, en, s.spread.median()))
        star = "  <--" if abs(r - p) > 2 * se else ""
        print(f"  {f'{lo:.2f}-{hi:.2f}':>12} {len(s):>6} {p:>11.3f} "
              f"{r:>10.3f} {r - p:>+8.3f} {s.spread.median():>7.1f}c "
              f"{ey:>+9.3f} {en:>+8.3f}{star}")
    print("\n  diff = realized - priced. Favorite-longshot predicts NEGATIVE")
    print("  diff in cheap bands and POSITIVE in dear bands.  '<--' = the gap")
    print("  exceeds 2 standard errors.")
    print("\n  edges are net of the 0.07*p*(1-p) fee but NOT of the spread;")
    print("  the spread column is the bar an edge must clear to be real.")
    e = pd.DataFrame(rows, columns=["lo", "hi", "n", "p", "r", "se", "ey",
                                    "en", "sp"])
    tail = e[(e.hi <= 0.20) | (e.lo >= 0.80)]
    if len(tail):
        print(f"\n  TAILS ONLY (<=20c or >=80c): n={int(tail.n.sum()):,}, "
              f"mean |diff| {np.average(np.abs(tail.r - tail.p), weights=tail.n):.4f}, "
              f"median spread {tail.sp.median():.1f}c")
    return e


if __name__ == "__main__":
    main()
