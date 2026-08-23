"""PREREG_ladder_consistency.md -- the single descriptive pass.

Hard cross: same event, same minute, K2>K1, bid(K2) > ask(K1)  (dominance arb)
Net cross:  gross - taker fees both legs (0.07*p*(1-p) each, at own price)
Soft:       mid(K2) > mid(K1), reported as coherence only.

All counts are UPPER BOUNDS (bars are not synchronous snapshots); persistence
>= 3 consecutive minutes is the interesting class. 1 contract per instance.
"""
import sqlite3
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

CAND = "/mnt/c/NBA2/Kalshi/data/kalshi_nba_candles.sqlite"
CURATED = "file:/mnt/c/NBA2/Kalshi/data/kalshi_nba_totals.sqlite?mode=ro"


def fee(p):
    """taker fee per contract, dollars, at price p (dollars)."""
    return 0.07 * p * (1 - p)


def main():
    cc = sqlite3.connect(CAND)
    k = pd.read_sql("SELECT ticker,event_ticker,end_period_ts,"
                    "yes_bid_close,yes_ask_close FROM candles", cc)
    ct = sqlite3.connect(CURATED, uri=True)
    mk = pd.read_sql("SELECT ticker,floor_strike,tipoff_ts FROM markets", ct)
    k = k.merge(mk, on="ticker", how="left")
    for c in ("end_period_ts", "yes_bid_close", "yes_ask_close",
              "floor_strike", "tipoff_ts"):
        k[c] = pd.to_numeric(k[c], errors="coerce")

    # same-rung sanity first (data errors, never arbitrage)
    both = k[(k.yes_bid_close > 0) & (k.yes_ask_close > 0)].copy()
    inv = both[both.yes_bid_close > both.yes_ask_close]
    print(f"  bars scanned {len(k):,}   two-sided {len(both):,}")
    print(f"  SAME-RUNG bid>ask data errors: {len(inv):,}")

    both = both[both.yes_bid_close <= both.yes_ask_close]
    both = both.dropna(subset=["floor_strike"])
    both["bid"] = both.yes_bid_close / 100.0
    both["ask"] = both.yes_ask_close / 100.0
    both["mid"] = (both.bid + both.ask) / 2
    both = both.sort_values(["event_ticker", "end_period_ts", "floor_strike"])

    g = both.groupby(["event_ticker", "end_period_ts"], sort=False)
    both["n_rungs"] = g["bid"].transform("size")
    m = both[both.n_rungs >= 2].copy()
    grp = m.groupby(["event_ticker", "end_period_ts"], sort=False)

    # suffix max of bid over HIGHER strikes (reverse cummax within group,
    # shifted so a rung is never compared with itself)
    rev = m.iloc[::-1]
    m["suf_bid"] = rev.groupby(["event_ticker", "end_period_ts"],
                               sort=False)["bid"].transform(
        lambda s: s.shift(1).cummax()).iloc[::-1]
    m["suf_mid"] = rev.groupby(["event_ticker", "end_period_ts"],
                               sort=False)["mid"].transform(
        lambda s: s.shift(1).cummax()).iloc[::-1]
    # adjacent versions: next-higher strike only
    m["nxt_bid"] = grp["bid"].shift(-1)
    m["nxt_mid"] = grp["mid"].shift(-1)

    minutes = m.groupby(["event_ticker", "end_period_ts"]).ngroups
    print(f"  (event,minute) ladders with >=2 quoted rungs: {minutes:,}")

    # ---- hard crosses (any pair) -------------------------------------------
    m["gross"] = m.suf_bid - m.ask
    hard = m[m.gross > 0].copy()
    hard["net"] = hard.gross - fee(hard.ask) - fee(hard.suf_bid)
    hard_adj = m[(m.nxt_bid - m.ask) > 0]
    softv = m[m.suf_mid > m.mid]
    soft_adj = m[m.nxt_mid > m.mid]

    print("\n" + "=" * 80)
    print("HARD CROSSES  bid(K2) > ask(K1)  [UPPER BOUNDS -- see prereg s3]")
    print("=" * 80)
    hmin = hard.groupby(["event_ticker", "end_period_ts"]).ngroups
    print(f"  low-leg instances: {len(hard):,}   minutes with any cross: "
          f"{hmin:,} ({100*hmin/minutes:.3f}% of ladder-minutes)")
    print(f"  adjacent-pair instances: {len(hard_adj):,}")
    if len(hard):
        print(f"  gross cents: mean {100*hard.gross.mean():.2f}  "
              f"median {100*hard.gross.median():.2f}  "
              f"max {100*hard.gross.max():.0f}")
        print(f"  NET of taker fees both legs: positive on {int((hard.net>0).sum()):,} "
              f"instances; net cents mean {100*hard.net.mean():.2f}")
        print(f"  sum of positive net at 1 contract each: "
              f"${hard.loc[hard.net>0,'net'].sum():.2f} over the whole window")

    # ---- persistence -------------------------------------------------------
    print("\n" + "=" * 80)
    print("PERSISTENCE of crossed low-legs (consecutive minutes)")
    print("=" * 80)
    if len(hard):
        hard = hard.sort_values(["event_ticker", "floor_strike",
                                 "end_period_ts"])
        gap = hard.groupby(["event_ticker", "floor_strike"])[
            "end_period_ts"].diff()
        hard["run_id"] = (gap != 60).cumsum()
        runs = hard.groupby("run_id").agg(
            L=("end_period_ts", "size"), ev=("event_ticker", "first"),
            K=("floor_strike", "first"), net=("net", "max"),
            t0=("end_period_ts", "min"))
        vc = runs.L.clip(upper=10).value_counts().sort_index()
        print(f"  runs: {len(runs):,}   length distribution "
              f"{vc.to_dict()}  (10 = '>=10')")
        long = runs[runs.L >= 3].sort_values("L", ascending=False)
        print(f"  runs >= 3 minutes: {len(long):,}"
              + (f"   of which net>0: {int((long.net>0).sum()):,}" if len(long) else ""))
        for _, r in long.head(10).iterrows():
            print(f"    {r.ev}  K={r.K:.1f}  {int(r.L)} min  "
                  f"best net {100*r.net:+.2f}c")

    # ---- timing ------------------------------------------------------------
    if len(hard):
        hard["h_to_tip"] = (hard.tipoff_ts - hard.end_period_ts) / 3600
        bins = pd.cut(hard.h_to_tip, [0, 1, 2, 4, 8, 24])
        print("\n  crosses by hours-to-tip: "
              f"{hard.groupby(bins).size().to_dict()}")

    # ---- soft violations ---------------------------------------------------
    print("\n" + "=" * 80)
    print("SOFT (mid) INVERSIONS -- coherence only, never money")
    print("=" * 80)
    print(f"  any-pair: {len(softv):,} low-legs "
          f"({100*len(softv)/len(m):.2f}% of rung-minutes)   "
          f"adjacent: {len(soft_adj):,}")
    if len(soft_adj):
        amt = (soft_adj.nxt_mid - soft_adj.mid) * 100
        print(f"  adjacent inversion size, cents: mean {amt.mean():.2f}  "
              f"median {amt.median():.2f}  p95 {amt.quantile(.95):.2f}")


if __name__ == "__main__":
    main()
