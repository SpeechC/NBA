"""
===============================================================================
 TARGET 3 (deep) — TEAM-TOTAL ADDITIVITY across the whole quote history
===============================================================================
 The first pass used ONE snapshot per market and found dispersion (|gap|>3pts
 in 16% of 25 events). Team totals only exist from 2026-08-10 (41 events; the
 /historical/markets endpoint returns nothing for this series), so there is no
 more HISTORY to fetch -- but there are 731,901 candles, and the first pass
 threw almost all of them away.

 This walks the full minute-by-minute quote history and asks the questions a
 snapshot cannot:

   A. How large is the gap, minute by minute, and does it persist?
      A transient gap is noise. A gap that survives for many minutes is a
      standing invitation.
   B. What do the three legs actually COST? Team-total spreads were never
      measured, and this is a THREE-LEG trade: two team legs plus the full
      game. That is the gate everything else has died at.
   C. Does the gap MEAN-REVERT, and which side moves? If the team pair
      converges to the full-game line, the full board is the anchor and the
      team legs are the mispriced ones (and vice versa).
   D. Is the gap directional -- does the team pair systematically sit above
      or below, which is the signature of one-sided public buying?

 Read-only.
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

HALVES = "/mnt/c/NBA2/Kalshi/data/kalshi_wnba_halves.sqlite"
FULLDB = "/mnt/c/NBA2/Kalshi/data/kalshi_wnba_candles.sqlite"
FEE = 1.75          # cents at p=.5; conservative for a mid-ladder leg
CPP = 2.59          # cents per point on a full-game ladder


def ladder(g):
    """-> (implied line, mean spread cents) from one snapshot of one board."""
    g = g.sort_values("k")
    if len(g) < 3:
        return None, np.nan
    L = A.median_cross(g.k.values.astype(float), g.mid.values)
    m = g[(g.mid > 0.2) & (g.mid < 0.8)]
    return L, (float((m.a - m.b).mean()) if len(m) else np.nan)


def load_team():
    con = sqlite3.connect(HALVES)
    mk = pd.read_sql(
        "select ticker, event_ticker, floor_strike, yes_sub_title from markets "
        "where ticker like 'KXWNBATEAMTOTAL%'", con)
    cd = pd.read_sql(
        "select ticker, end_period_ts ts, yes_bid_close b, yes_ask_close a "
        "from candles where period_interval=1 and ticker like "
        "'KXWNBATEAMTOTAL%'", con)
    con.close()
    d = cd.dropna(subset=["b", "a"]).merge(mk, on="ticker")
    d["mid"] = (d.b + d.a) / 200.0
    d["k"] = d.floor_strike.astype(float)
    d["team"] = (d.yes_sub_title.astype(str)
                 .str.extract(r'^(.*?)\s+over\s', expand=False).str.strip())
    d["ev"] = d.event_ticker.str.split("-").str[1]
    return d.dropna(subset=["team"])


def load_full():
    con = sqlite3.connect(FULLDB)
    mk = pd.read_sql("select ticker, event_ticker, floor_strike from markets "
                     "where ticker like 'KXWNBATOTAL%'", con)
    cd = pd.read_sql("select ticker, end_period_ts ts, yes_bid_close b, "
                     "yes_ask_close a from candles where period_interval=1 "
                     "and ticker like 'KXWNBATOTAL%'", con)
    con.close()
    d = cd.dropna(subset=["b", "a"]).merge(mk, on="ticker")
    d["mid"] = (d.b + d.a) / 200.0
    d["k"] = d.floor_strike.astype(float)
    d["ev"] = d.event_ticker.str.split("-").str[1]
    return d


def main():
    tt, fu = load_team(), load_full()
    evs = sorted(set(tt.ev) & set(fu.ev))
    print(f"team-total events {tt.ev.nunique()}, overlapping the full board "
          f"on {len(evs)}\n")
    rows = []
    for ev in evs:
        t, f = tt[tt.ev == ev], fu[fu.ev == ev]
        teams = sorted(t.team.unique())
        if len(teams) != 2:
            continue
        fmap = {ts: g for ts, g in f.groupby("ts")}
        amap = {ts: g for ts, g in t[t.team == teams[0]].groupby("ts")}
        bmap = {ts: g for ts, g in t[t.team == teams[1]].groupby("ts")}
        for ts in sorted(set(fmap) & set(amap) & set(bmap)):
            Lf, sf = ladder(fmap[ts])
            La, sa = ladder(amap[ts])
            Lb, sb = ladder(bmap[ts])
            if any(x is None or not np.isfinite(x) for x in (Lf, La, Lb)):
                continue
            rows.append({"ev": ev, "ts": ts, "Lf": Lf, "sum": La + Lb,
                         "gap": (La + Lb) - Lf, "sp_f": sf,
                         "sp_t": np.nanmean([sa, sb])})
    d = pd.DataFrame(rows)
    if not len(d):
        print("no simultaneous three-board snapshots")
        return
    d = d.sort_values(["ev", "ts"])
    print(f"A. SIMULTANEOUS THREE-BOARD SNAPSHOTS: {len(d):,} minutes across "
          f"{d.ev.nunique()} events  (median {d.groupby('ev').size().median():.0f}/event)")
    print(f"   gap = (TT_a + TT_b) - full :  mean {d.gap.mean():+.2f}  "
          f"median {d.gap.median():+.2f}  sd {d.gap.std():.2f}")
    print(f"   |gap|>2pts {(d.gap.abs()>2).mean():.0%}   >3 "
          f"{(d.gap.abs()>3).mean():.0%}   >5 {(d.gap.abs()>5).mean():.0%}")
    rng = np.random.default_rng(4)
    ev_a = d.ev.unique()
    by = {e: d.loc[d.ev == e, "gap"].values for e in ev_a}
    bs = [np.concatenate([by[x] for x in rng.choice(ev_a, len(ev_a), True)]).mean()
          for _ in range(3000)]
    lo, hi = np.percentile(bs, [2.5, 97.5])
    print(f"   mean gap 95% CI (clustered by event) [{lo:+.2f},{hi:+.2f}]"
          f"  -> {'DIRECTIONAL' if (lo>0 or hi<0) else 'no systematic side'}")

    print(f"\nB. WHAT THE THREE LEGS COST")
    print(f"   full-board spread   median {d.sp_f.median():.1f}c")
    print(f"   team-leg spread     median {d.sp_t.median():.1f}c  (each of two legs)")
    cost_c = d.sp_f.median() / 2 + d.sp_t.median() + 3 * FEE
    print(f"   three-leg round trip ~ {cost_c:.1f}c = {cost_c/CPP:.1f} points of total")
    print(f"   share of minutes where |gap| clears that bar: "
          f"{(d.gap.abs()*CPP > cost_c).mean():.1%}")

    print(f"\nC. DOES A GAP PERSIST, OR BLINK?")
    runs = []
    for e, g in d.groupby("ev"):
        big = (g.gap.abs() * CPP > cost_c).values
        c = 0
        for v in big:
            if v:
                c += 1
            elif c:
                runs.append(c)
                c = 0
        if c:
            runs.append(c)
    if runs:
        r = np.array(runs)
        print(f"   {len(r)} episodes above cost; median length {np.median(r):.0f} min, "
              f"max {r.max()} min, >=5min in {(r>=5).mean():.0%}")
    else:
        print("   no episode ever cleared the cost bar")

    print(f"\nD. WHICH SIDE CORRECTS?  (gap_t+5 regressed on gap_t)")
    d["gap_next"] = d.groupby("ev").gap.shift(-5)
    d["df"] = d.groupby("ev").Lf.shift(-5) - d.Lf
    d["dt"] = d.groupby("ev")["sum"].shift(-5) - d["sum"]
    s = d.dropna(subset=["gap_next"])
    if len(s) > 50:
        b, se = A.ols(s.gap_next.values, [s.gap.values], ["gap"])
        print(f"   persistence coef {b['gap']:+.3f} (se {se['gap']:.3f})  "
              f"[1 = never corrects, 0 = corrects fully in 5 min]")
        bf, sef = A.ols(s.df.values, [s.gap.values], ["gap"])
        bt, set_ = A.ols(s.dt.values, [s.gap.values], ["gap"])
        print(f"   full board moves {bf['gap']:+.3f} per pt of gap (se {sef['gap']:.3f})")
        print(f"   team pair moves  {bt['gap']:+.3f} per pt of gap (se {set_['gap']:.3f})")
        print("   the leg with the LARGER |coef| is the one doing the correcting,")
        print("   i.e. the mispriced side.")


if __name__ == "__main__":
    main()
