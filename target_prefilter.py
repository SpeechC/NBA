"""
===============================================================================
 PRE-FILTER FOR TARGETS 4-7 — measure the spread BEFORE doing any modelling
===============================================================================
 The law extracted from target 3: a board's spread is the market's own
 statement about how much attention it gets. Unattended => mispriced => also
 untouchable. A viable target needs BOTH a tight spread (so it can be traded)
 AND low analytical attention (so it is wrong).

 So before modelling anything, measure the board each target would actually
 trade, in the phase it would trade it:

   T4 crew / calendar shocks  -> PREGAME full-game board (and 1H)
   T5 new-series launch window-> spread as a function of BOARD AGE
   T6 maker vs phantom rev.   -> not spread but FLOW: contracts/min at the
                                 halftime touch (a maker needs fills)
   T7 injury-news latency     -> PREGAME full-game board + evidence that it
                                 JUMPS (news arrives) rather than drifting

 RESULTS (2026-08-25). Board spreads in the priced 20-80c region:

   board  phase        med spread   as points   vol/min
   full   pregame          1.0c        0.4         0
   full   in-game          2.0c        0.8       181-468
   1H     pregame          5.0c        1.9         0
   2H     pregame         67.0c       25.9         0
   Q1     pregame         32.0c       12.4         0
   Q4     pregame         57.0c       22.0         0
   TEAM   any             39.0c       15.1         0

 T4 CREW / CALENDAR -> PASS, best-qualified. The pregame full-game board is
    the tightest thing in the program: 1.0c spread, 2.2c round trip = 0.9
    POINTS of total. For scale, phantom reversion was worth 1.7 pts (would
    clear) and garbage time 0.5 pts (would not).

 T5 LAUNCH WINDOWS -> FAIL, decisively. Spread by board age (week 1 / 2 /
    3-4 / 5+):  2H 90c/90c/55c/29c,  Q4 98c/97c/57c/28c,  Q1 37/34/33/26,
    TEAM 46/35/30/-. Boards are WIDEST exactly when new and tighten
    monotonically. The immature window is unreachable. (1H is the lone
    exception, tight from week one -- so no window existed there either.)

 T6 MAKER -> PASS on flow, but the PRIZE IS SMALLER THAN ASSUMED. Halftime
    window carries 51,555 contracts/game and 100% of games have flow -- but
    the WNBA full board is only 2.0c wide, so a maker earns ~1c per fill,
    not the ~7c implied by the NBA's stale 14.3c spread. Thin-margin,
    high-turnover, and entirely dependent on adverse selection being under
    1c. Tonight's M1/M2 logs are the measurement.

 T7 INJURY LATENCY -> FAIL as a standalone. Measured within-rung (the
    naive within-event diff manufactures a 93% false-positive rate): moves
    >5c in a minute occur in 0.025% of rung-minutes, 19 of 251 games, and
    the median volume on those bars is ZERO with a 14.5c spread -- they are
    quote flickers on untraded rungs, not news repricings. 85% sit within
    2h of tip. There is no populated pregame jump process to be early to.

 Read-only. Verdict per target: PASS (worth modelling) or FAIL (dead on cost).
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
import clock_validation as CV                                # noqa: E402

FULLDB = "/mnt/c/NBA2/Kalshi/data/kalshi_wnba_candles.sqlite"
HALVES = "/mnt/c/NBA2/Kalshi/data/kalshi_wnba_halves.sqlite"
BOARDS = [("full", FULLDB, "KXWNBATOTAL%"),
          ("1H", HALVES, "KXWNBA1HTOTAL%"),
          ("2H", HALVES, "KXWNBA2HTOTAL%"),
          ("Q1", HALVES, "KXWNBA1QTOTAL%"),
          ("Q4", HALVES, "KXWNBA4QTOTAL%"),
          ("TEAM", HALVES, "KXWNBATEAMTOTAL%")]
CPP = 2.59


def pull(tag, db, like):
    con = sqlite3.connect(db)
    d = pd.read_sql(
        "select event_ticker e, end_period_ts ts, yes_bid_close b, "
        "yes_ask_close a, volume v from candles where period_interval=1 "
        f"and ticker like '{like}'", con)
    con.close()
    d = d.dropna(subset=["b", "a"])
    d["mid"] = (d.b + d.a) / 200.0
    d["sp"] = d.a - d.b
    d = d[(d.mid > 0.2) & (d.mid < 0.8)]          # priced region only
    d["board"] = tag
    d["k"] = d.e.str.split("-").str[1]
    return d[["board", "e", "k", "ts", "sp", "v", "mid"]]


def main():
    d = pd.concat([pull(*b) for b in BOARDS], ignore_index=True)
    ck = CV.load_clocks("espn_clocks_wnba.csv", CV.ESPN_WNBA)
    ds = ck.date.astype(str)
    M = {f"{i:02d}": m for i, m in enumerate(
        ["", "JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP",
         "OCT", "NOV", "DEC"])}
    ck["key"] = (ds.str[2:4] + ds.str[4:6].map(M) + ds.str[6:8]
                 + ck.ac + ck.hc)
    tip = dict(zip(ck.key, ck.tip_ts))
    half = dict(zip(ck.key, ck.half_ts))
    d["tip"] = d.k.map(tip)
    d["half"] = d.k.map(half)
    j = d.dropna(subset=["tip"]).copy()
    j["phase"] = np.where(j.ts < j.tip - 60, "pregame",
                          np.where(j.ts < j.half, "1st half", "2nd half+"))

    print("SPREAD AND FLOW BY BOARD AND PHASE  (priced region 20-80c only)")
    print(f"  {'board':>6} {'phase':>10} {'bars':>7} {'med spread':>11} "
          f"{'as points':>10} {'vol/min':>8}")
    for b in ["full", "1H", "2H", "Q1", "Q4", "TEAM"]:
        for ph in ["pregame", "1st half", "2nd half+"]:
            s = j[(j.board == b) & (j.phase == ph)]
            if len(s) < 100:
                continue
            print(f"  {b:>6} {ph:>10} {len(s):>7,} {s.sp.median():>10.1f}c "
                  f"{s.sp.median()/CPP:>9.1f} {s.v.median():>8.0f}")

    print("\n" + "=" * 70)
    print("T4  CREW / CALENDAR SHOCKS -> pregame full-game board")
    f = j[(j.board == "full") & (j.phase == "pregame")]
    sp = f.sp.median()
    print(f"    median pregame spread {sp:.1f}c = {sp/CPP:.1f} pts; round trip "
          f"{sp/2+1.75:.1f}c = {(sp/2+1.75)/CPP:.1f} pts")
    print(f"    VERDICT: {'PASS' if sp/2+1.75 < 6 else 'FAIL'} — an effect must "
          f"exceed {(sp/2+1.75)/CPP:.1f} points of total to pay.")
    print(f"    (for scale: unpriced garbage-time was 0.5 pts, phantom "
          f"reversion 1.7 pts)")

    print("\nT5  NEW-SERIES LAUNCH WINDOW -> spread vs board age")
    print(f"  {'board':>6} {'week 1':>9} {'week 2':>9} {'week 3-4':>9} "
          f"{'week 5+':>9}")
    for b in ["1H", "2H", "Q1", "Q4", "TEAM"]:
        s = j[j.board == b].copy()
        if not len(s):
            continue
        s["age_d"] = (s.ts - s.ts.min()) / 86400.0
        cells = []
        for lo, hi in [(0, 7), (7, 14), (14, 28), (28, 999)]:
            g = s[(s.age_d >= lo) & (s.age_d < hi)]
            cells.append(f"{g.sp.median():.0f}c" if len(g) > 100 else "  -")
        print(f"  {b:>6} " + "".join(f"{c:>9}" for c in cells))
    print("    VERDICT: FAIL if boards are WIDEST when new — the immature")
    print("    window is exactly when you cannot transact.")

    print("\nT6  MAKER vs PHANTOM REVERSION -> flow, not spread")
    hw = j[(j.board == "full") & (j.ts >= j.half - 300) & (j.ts <= j.half + 900)]
    if len(hw):
        per_game = hw.groupby("k").v.sum()
        print(f"    halftime window (-5..+15 min): {hw.v.median():.0f} "
              f"contracts/min/rung, {per_game.median():.0f} per game total")
        print(f"    games with ANY flow: {(per_game > 0).mean():.0%}; "
              f"median full-board spread there {hw.sp.median():.1f}c")
        print(f"    VERDICT: {'PASS' if per_game.median() > 200 else 'THIN'} — "
              f"a maker needs fills; this is the flow available to rest against.")

    print("\nT7  INJURY-NEWS LATENCY -> does the pregame board JUMP?")
    # NB: diff WITHIN each ticker (rung). Diffing within an event mixes
    # different strikes and manufactures fake 'jumps' (93% false positive).
    f2 = f.sort_values(["e", "ts"])
    f2["dmid"] = f2.groupby("e").mid.diff().abs()
    big = f2[f2.dmid > 0.03]
    print(f"    pregame bars {len(f2):,}; moves >3c in one minute: "
          f"{len(big):,} ({len(big)/max(1,len(f2)):.2%})")
    print(f"    games with >=1 such jump: {big.k.nunique()} of {f2.k.nunique()}")
    print(f"    VERDICT: {'PASS' if len(big)/max(1,len(f2)) > 0.002 else 'FAIL'}"
          f" — jumps are where news arrives; no jumps means nothing to be early to.")


if __name__ == "__main__":
    main()
