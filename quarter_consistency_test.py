"""
===============================================================================
 QUARTER-LEVEL CONSISTENCY — the redundant identities on Kalshi's boards
===============================================================================
 Kalshi lists 1Q/2Q/3Q/4Q totals alongside 1H/2H and the full game. That makes
 several identities that must ALL hold simultaneously, by arithmetic:

     full  =  1H + 2H
     1H    =  Q1 + Q2
     2H    =  Q3 + Q4
     full  =  Q1 + Q2 + Q3 + Q4

 Each is a model-free, same-venue, same-fee multi-leg trade when violated.
 board_consistency_test.py already showed full vs 1H+2H agrees to sd 1.25 pts
 with no violation beyond 3 points; this asks the finer questions, where thin
 boards are likelier to drift apart.

 Tested at three moments, because a board's discipline should vary with
 attention:
   PREGAME    (tip - 20 min)  -- quarter boards are afterthoughts here
   HALFTIME   (ESPN buzzer+3) -- H1 known, Q1/Q2 settled, 2H/Q3/Q4 live
   END OF Q3  (buzzer+~35)    -- only Q4 still live

 Reports, per identity and moment: the gap distribution, the share of games
 violating by more than the round-trip cost, and the spreads on each leg --
 because a violation you cannot transact is not an opportunity. The economics
 gate is the same one that has killed everything else: edge / cost > 1.

 RESULTS (2026-08-25). Harvest: 1H 286 events (from 05-08), 2H 158 and each
 quarter 162 (from 06-17), ~600k candles.

   PREGAME (tip-20m)        n    gap mean   sd    legs cost   beats cost
     full = 1H + 2H         6     +0.34    0.64     12.1c        0%
     1H   = Q1 + Q2         6     +0.71    0.36     15.6c        0%
     2H   = Q3 + Q4         8     +0.31    0.22     16.0c        0%
     full = Q1+Q2+Q3+Q4     6     +0.68    0.98     24.5c        0%
   HALFTIME (buzzer+3)
     2H   = Q3 + Q4        14     +0.47    1.12     37.8c        0%
   END Q3 (buzzer+35)
     2H   = Q3 + Q4        30     -0.04    1.53     45.2c        0%

 EVERY IDENTITY HOLDS, and "gap beats cost" is 0% in every cell. Gaps run
 ~0.3-0.7 pts (under 2c) against multi-leg round trips of 12-45c: you would
 need a violation 5-15x larger before it was transactable.

 The n=0 cells are STRUCTURAL, not a bug: by halftime the 1H, Q1 and Q2
 boards have settled, so their ladders are all 0s and 100s and no line can be
 read. That is the correct behaviour and it is also the point -- at halftime
 only the live boards (full, 2H, Q3, Q4) carry information, which is why the
 meaningful halftime identity is the one board_consistency_test.py already
 ran: full = H1_actual + 2H (n=27, agrees, sd 1.25 pts).

 VERDICT: Kalshi's basketball board family is internally coherent, and the
 multi-leg cost structure means that even a violation twice the size of any
 observed here would not pay. This closes the internal-arbitrage line of
 enquiry.

 Read-only. Requires kalshi_wnba_halves.sqlite (1H/2H/1Q-4Q) and
 kalshi_wnba_candles.sqlite (full game), plus espn_clocks_wnba.csv.
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
import wnba_reconcile as R                                   # noqa: E402
import clock_validation as CV                                # noqa: E402

HALVES = "/mnt/c/NBA2/Kalshi/data/kalshi_wnba_halves.sqlite"
FULLDB = "/mnt/c/NBA2/Kalshi/data/kalshi_wnba_candles.sqlite"
FEE_C = 1.75          # taker fee in cents at p=0.5
CPP = 2.59            # cents per point on a full-game ladder


def load(db, like):
    con = sqlite3.connect(db)
    d = pd.read_sql(
        "select event_ticker e, end_period_ts t, strike_label k, "
        "yes_bid_close b, yes_ask_close a from candles where "
        f"period_interval=1 and strike_label is not null "
        f"and event_ticker like '{like}'", con)
    con.close()
    d = d.dropna(subset=["b", "a"])
    d["mid"] = (d.b + d.a) / 200.0          # b, a are CENTS
    return {e.split("-", 1)[1]: {t: g for t, g in gg.groupby("t")}
            for e, gg in d.groupby("e")}


def line_and_spread(bk):
    """-> (implied line, mean spread in cents) from one ladder snapshot."""
    if bk is None or len(bk) < 3:
        return None, np.nan
    g = bk.sort_values("k")
    L = A.median_cross(g.k.values.astype(float), g.mid.values)
    m = g[(g.mid > 0.2) & (g.mid < 0.8)]
    return L, (float((m.a - m.b).mean()) if len(m) else np.nan)


def at(idx, key, ts, tol=300):
    b = idx.get(key, {})
    if not b:
        return None
    ks = np.array(sorted(b))
    i = np.abs(ks - ts).argmin()
    return b[ks[i]] if abs(ks[i] - ts) <= tol else None


def main():
    boards = {"full": load(FULLDB, "KXWNBATOTAL%")}
    for tag, series in (("1H", "KXWNBA1HTOTAL"), ("2H", "KXWNBA2HTOTAL"),
                        ("Q1", "KXWNBA1QTOTAL"), ("Q2", "KXWNBA2QTOTAL"),
                        ("Q3", "KXWNBA3QTOTAL"), ("Q4", "KXWNBA4QTOTAL")):
        boards[tag] = load(HALVES, series + "%")
        print(f"  {tag:<5} {len(boards[tag]):>4} events")

    ck = CV.load_clocks("espn_clocks_wnba.csv", CV.ESPN_WNBA)
    ck["dstr"] = ck.date.astype(str)
    IDENT = [("full = 1H + 2H", "full", ["1H", "2H"]),
             ("1H   = Q1 + Q2", "1H", ["Q1", "Q2"]),
             ("2H   = Q3 + Q4", "2H", ["Q3", "Q4"]),
             ("full = Q1+Q2+Q3+Q4", "full", ["Q1", "Q2", "Q3", "Q4"])]
    MOMENTS = [("PREGAME  (tip-20m)", lambda c: float(c.tip_ts) - 20 * 60),
               ("HALFTIME (buzzer+3)", lambda c: float(c.half_ts) + 180),
               ("END Q3   (buzzer+35)", lambda c: float(c.half_ts) + 35 * 60)]

    for mlab, mfn in MOMENTS:
        print(f"\n{'=' * 72}\n{mlab}\n{'=' * 72}")
        for ilab, lhs, rhs in IDENT:
            rows = []
            for _, c in ck.iterrows():
                dt = f"{c.dstr[:4]}-{c.dstr[4:6]}-{c.dstr[6:8]}"
                keys = [k for k in boards[lhs]
                        if k[7:] == c.ac + c.hc
                        and str(R.event_date("X-" + k)) == dt]
                for kk in keys:
                    ts = mfn(c)
                    L0, s0 = line_and_spread(at(boards[lhs], kk, ts))
                    if L0 is None or not np.isfinite(L0):
                        continue
                    parts, sps, ok = [], [s0], True
                    for tag in rhs:
                        Lp, sp = line_and_spread(at(boards[tag], kk, ts))
                        if Lp is None or not np.isfinite(Lp):
                            ok = False
                            break
                        parts.append(Lp)
                        sps.append(sp)
                    if not ok:
                        continue
                    rows.append({"gap": L0 - sum(parts),
                                 "cost_c": sum(np.nan_to_num(sps)) / 2
                                 + FEE_C * (1 + len(rhs))})
            d = pd.DataFrame(rows)
            if len(d) < 5:
                print(f"  {ilab:<22} n={len(d):<4} too few to test")
                continue
            viol = (d.gap.abs() * CPP > d.cost_c).mean()
            print(f"  {ilab:<22} n={len(d):<4} gap mean {d.gap.mean():+6.2f} "
                  f"sd {d.gap.std():5.2f}  |gap|>3pts {(d.gap.abs() > 3).mean():4.0%}"
                  f"   legs cost {d.cost_c.median():5.1f}c"
                  f"   gap beats cost in {viol:4.0%}")
    print("\n  'gap beats cost' is the only column that matters: a violation")
    print("  smaller than the multi-leg round trip is not an opportunity.")


if __name__ == "__main__":
    main()
