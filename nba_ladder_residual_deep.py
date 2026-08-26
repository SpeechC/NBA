"""
===============================================================================
 NBA LADDER RESIDUALS — deep test of the last surviving edge
===============================================================================
 `ladder_residual_maker.py` found NBA rungs quoted away from their own
 ladder's probit fit are directionally informative, worth +1.24c gross to a
 maker (CI [-0.04,+2.51]); `adverse_selection.py` then showed the
 adverse-selection charge is ~0.02c, so the threat that was supposed to kill
 it does not. What remains unanswered is whether the edge is REAL and
 PERSISTENT, and this asks the four questions that decide it.

  1. MEAN REVERSION. A maker's actual mechanism is not settlement -- it is
     that the quote returns to fair. Does resid(t+h) shrink toward zero when
     resid(t) is large? A coefficient near 1 means the residual is a
     persistent feature of the board (nothing to harvest); near 0 means it
     reverts (harvestable).
  2. SPREAD REGIME. NBA half-spreads compressed 3-4c -> 1-2c across the
     season. If the edge shrinks with them, it is disappearing as the venue
     matures and the measured value is a historical artefact.
  3. PHASE. Pregame vs in-game are different books with different flow.
  4. CAPACITY. An edge of a cent is only a business at size; volume at the
     rung bounds it.

 Net economics apply the MEASURED adverse-selection charge rather than a
 hypothetical one, and the fee, which `adverse_selection.py` showed is the
 binding cost.
===============================================================================
"""
import os
import sqlite3
import sys
import warnings

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from implied_line import probit_line                         # noqa: E402

DB = "/mnt/c/NBA2/Kalshi/data/kalshi_nba_triangle.sqlite"
RNG = np.random.default_rng(53)
ADV = 0.0002      # measured adverse selection, 5-min horizon (0.02c)


def fee(p):
    return 0.07 * p * (1 - p)


def build(snaps_per_game=8):
    con = sqlite3.connect(DB)
    mk = pd.read_sql("select ticker, event_ticker e, floor_strike k, result, "
                     "game_date, close_ts from markets where result in "
                     "('yes','no') and ticker like 'KXNBATOTAL-%'", con)
    cd = pd.read_sql("select ticker, end_period_ts ts, yes_bid_close b, "
                     "yes_ask_close a, volume v from candles where "
                     "period_interval=1 and ticker like 'KXNBATOTAL-%'", con)
    con.close()
    d = cd.dropna(subset=["b", "a"]).merge(mk, on="ticker")
    d["mid"] = (d.b + d.a) / 200.0
    d["sp"] = d.a - d.b
    d["win"] = (d.result == "yes").astype(float)
    d["key"] = d.e.str.split("-").str[1]
    d["mo"] = pd.to_datetime(d.game_date).dt.strftime("%Y-%m")
    d["phase"] = np.where(d.ts < d.close_ts - 3 * 3600, "pregame", "in-game")
    keep = []
    for key, g in d.groupby("key"):
        ts = np.sort(g.ts.unique())
        pick = ts[np.linspace(0, len(ts) - 1,
                              min(snaps_per_game, len(ts))).round().astype(int)]
        keep.append(g[g.ts.isin(pick)])
    d = pd.concat(keep, ignore_index=True)
    # LOO residual per rung
    rows = []
    for (key, ts), g in d.groupby(["key", "ts"]):
        if len(g) < 5:
            continue
        kk = g.k.values.astype(float)
        mid = g.mid.values
        for i in range(len(g)):
            m = np.ones(len(g), bool)
            m[i] = False
            p = probit_line(kk[m], mid[m], weighted=True)
            if not np.isfinite(p["mu"]) or not (p["sigma"] > 0) or p["r2"] < 0.9:
                continue
            phat = 1 - stats.norm.cdf((kk[i] - p["mu"]) / p["sigma"])
            r = g.iloc[i]
            rows.append({"key": key, "ticker": r.ticker, "ts": ts, "mo": r.mo,
                         "phase": r.phase, "mid": mid[i], "phat": phat,
                         "resid": mid[i] - phat, "sp": r.sp, "win": r.win,
                         "v": r.v})
    return pd.DataFrame(rows)


def ci(v, keys, B=3000):
    ev = np.unique(keys)
    by = {k: v[keys == k] for k in ev}
    o = [np.nanmean(np.concatenate([by[x] for x in RNG.choice(ev, len(ev), True)]))
         for _ in range(B)]
    return np.nanpercentile(o, [2.5, 97.5])


def maker_edge(s):
    """Edge to a maker resting toward the fit, net of measured adv sel + fee."""
    buy, sell = s[s.resid < 0], s[s.resid > 0]
    e = np.concatenate([
        (buy.win - buy.mid - fee(buy.mid) - ADV).values,
        ((1 - sell.win) - (1 - sell.mid) - fee(sell.mid) - ADV).values])
    k = np.concatenate([buy.key.values, sell.key.values])
    return e, k


def row(lab, s, thresh=0.02):
    s = s[s.resid.abs() > thresh]
    if len(s) < 100:
        print(f"  {lab:<30} n={len(s):>6}  too few")
        return
    e, k = maker_edge(s)
    lo, hi = ci(e, k)
    print(f"  {lab:<30} n={len(s):>6} edge {np.nanmean(e)*100:>+6.2f}c "
          f"CI [{lo*100:+.2f},{hi*100:+.2f}]  sp {s.sp.median():.1f}c")


def main():
    d = build()
    print(f"NBA rung-snapshots {len(d):,}, games {d.key.nunique()}\n")

    print("1. MEAN REVERSION — does the residual return to fair?")
    d = d.sort_values(["ticker", "ts"])
    for h in (1, 3, 5, 10):
        g = d.copy()
        g["fut"] = g.groupby("ticker").resid.shift(-1)
        g["gap"] = g.groupby("ticker").ts.diff().shift(-1)
        s = g[(g.gap.between(30, h * 60 + 60)) & g.fut.notna()]
        if len(s) < 200:
            continue
        b, se = np.polyfit(s.resid, s.fut, 1), None
        keep = s.resid.abs() > 0.02
        print(f"   ~{h:>2}m ahead: persistence coef {b[0]:+.3f}  "
              f"(1=never reverts, 0=fully reverts)   n={len(s):,}"
              f"   |resid|>2c subset mean {s[keep].resid.mean()*100:+.2f}c -> "
              f"{s[keep].fut.mean()*100:+.2f}c")

    print("\n2. BY SPREAD REGIME (the venue is compressing)")
    for lab, sub in (("2025-10..12 (3-4c)", d[d.mo < "2026-01"]),
                     ("2026-01+ (2c)", d[(d.mo >= "2026-01") & (d.mo < "2026-03")]),
                     ("2026-03+ (1-2c)", d[d.mo >= "2026-03"])):
        row(lab, sub)

    print("\n3. BY PHASE")
    for ph in ("pregame", "in-game"):
        row(ph, d[d.phase == ph])

    print("\n4. BY RESIDUAL SIZE")
    for lo_ in (0.01, 0.02, 0.03, 0.05):
        row(f"|resid| > {lo_*100:.0f}c", d, thresh=lo_)

    print("\n5. CAPACITY at |resid| > 2c")
    s = d[d.resid.abs() > 0.02]
    print(f"   opportunities {len(s):,} over {s.key.nunique()} games "
          f"= {len(s)/max(1,s.key.nunique()):.1f} per game")
    print(f"   volume on those rung-minutes: median {s.v.median():.0f}, "
          f"mean {s.v.mean():.0f} contracts")
    e, k = maker_edge(s)
    print(f"   edge {np.nanmean(e)*100:+.2f}c/contract -> at 100 contracts per "
          f"opportunity, {np.nanmean(e)*100*100*len(s)/max(1,s.key.nunique())/100:.2f} "
          f"dollars per game")


if __name__ == "__main__":
    main()
