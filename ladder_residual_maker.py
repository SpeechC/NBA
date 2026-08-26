"""
===============================================================================
 INTRA-LADDER RESIDUALS — the maker thesis, tested without any forecast
===============================================================================
 Every strategy this programme has tried needed a VIEW: our model against the
 market's line. All of them lost, because the market forecasts better than we
 do. This asks a different question, one that needs no forecast at all:

   is an individual rung priced consistently with the OTHER rungs on its own
   ladder?

 `probit_line` fits K = mu + sigma*z to a whole ladder, which gives a smooth
 fair-value curve p_hat(K) = 1 - Phi((K - mu)/sigma). A rung quoted away from
 that curve is locally mispriced RELATIVE TO ITS OWN BOARD. Resting an order
 there is a market-making trade: no opinion about the game, only that the
 ladder should be internally smooth.

 LEAVE-ONE-OUT is essential. A rung included in its own fit drags the curve
 toward itself and its residual is shrunk toward zero. Every fitted value here
 is computed from the OTHER rungs only.

 The decisive test is calibration: for a given rung, which predicts settlement
 better -- its own quoted mid, or the LOO fit from its neighbours? If the fit
 wins, the ladder carries information the individual quote does not, and the
 residual is harvestable.

 Economics are reported two ways, because they are different businesses:
   TAKER  cross the spread, pay 0.07*p*(1-p): needs residual > half-spread+fee
   MAKER  rest at the fitted value, earn the difference, pay only the fee:
          needs residual > fee, and survives only if adverse selection is
          smaller than the residual.
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

RNG = np.random.default_rng(31)
WNBA = "/mnt/c/NBA2/Kalshi/data/kalshi_wnba_candles.sqlite"
NBA = "/mnt/c/NBA2/Kalshi/data/kalshi_nba_triangle.sqlite"


def fee(p):
    return 0.07 * p * (1 - p)


def loo_residuals(db, like, snaps_per_game=6, seed=3):
    """Per-rung LOO residual: quoted mid minus the fit from its neighbours.

    SUBSAMPLED to `snaps_per_game` evenly-spaced snapshots per game. Refitting
    every rung-minute costs ~14M probit fits on the NBA store and adds almost
    no independent information -- consecutive minutes on one ladder are nearly
    the same observation. Spacing a handful of snapshots across each game keeps
    the variation that matters (different game states) and drops the
    redundancy. CIs are clustered by game either way.
    """
    con = sqlite3.connect(db)
    mk = pd.read_sql(f"select ticker, event_ticker e, floor_strike k, result "
                     f"from markets where result in ('yes','no') and ticker "
                     f"like '{like}'", con)
    cd = pd.read_sql(f"select ticker, end_period_ts ts, yes_bid_close b, "
                     f"yes_ask_close a from candles where period_interval=1 "
                     f"and ticker like '{like}'", con)
    con.close()
    d = cd.dropna(subset=["b", "a"]).merge(mk, on="ticker")
    d["mid"] = (d.b + d.a) / 200.0
    d["sp"] = d.a - d.b
    d["win"] = (d.result == "yes").astype(float)
    d["key"] = d.e.str.split("-").str[1]
    keep = []
    for key, g in d.groupby("key"):
        ts = np.sort(g.ts.unique())
        if len(ts) == 0:
            continue
        pick = ts[np.linspace(0, len(ts) - 1, min(snaps_per_game, len(ts))
                              ).round().astype(int)]
        keep.append(g[g.ts.isin(pick)])
    d = pd.concat(keep, ignore_index=True) if keep else d.iloc[:0]
    rows = []
    for (key, ts), g in d.groupby(["key", "ts"]):
        if len(g) < 5:                       # need 4 neighbours to fit
            continue
        kk = g.k.values.astype(float)
        mid = g.mid.values
        for i in range(len(g)):
            m = np.ones(len(g), bool)
            m[i] = False
            p = probit_line(kk[m], mid[m], weighted=True)
            if not np.isfinite(p["mu"]) or not (p["sigma"] > 0):
                continue
            phat = 1 - stats.norm.cdf((kk[i] - p["mu"]) / p["sigma"])
            r = g.iloc[i]
            rows.append({"key": key, "ts": ts, "k": kk[i], "mid": mid[i],
                         "phat": phat, "resid": mid[i] - phat,
                         "sp": r.sp, "win": r.win, "r2": p["r2"]})
    return pd.DataFrame(rows)


def ci(d, col, B=3000):
    ev = d.key.unique()
    by = {k: d.loc[d.key == k, col].values for k in ev}
    o = [np.concatenate([by[x] for x in RNG.choice(ev, len(ev), True)]).mean()
         for _ in range(B)]
    return np.percentile(o, [2.5, 97.5])


def report(d, tag):
    d = d[(d.mid > 0.02) & (d.mid < 0.98) & d.phat.between(0.001, 0.999)]
    d = d[d.r2 >= 0.90]
    print(f"\n{'='*70}\n{tag}: {len(d):,} rung-snapshots, {d.key.nunique()} games")
    print(f"  |residual| median {d.resid.abs().median()*100:.2f}c, "
          f"90th pct {d.resid.abs().quantile(.9)*100:.2f}c; "
          f"median spread {d.sp.median():.1f}c")

    print("\n  A. WHICH PREDICTS SETTLEMENT -- the quote, or the neighbours' fit?")
    d["e_q"] = d.win - d.mid
    d["e_f"] = d.win - d.phat
    for lab, col in (("quoted mid", "e_q"), ("LOO fit", "e_f")):
        lo, hi = ci(d, col)
        print(f"     {lab:<12} mean err {d[col].mean():+.4f} CI [{lo:+.4f},"
              f"{hi:+.4f}]  RMSE {np.sqrt((d[col]**2).mean()):.4f}")

    print("\n  B. DOES THE RESIDUAL PREDICT? (bucket by mid - fit)")
    print(f"     {'residual band':>16} {'n':>7} {'mean resid':>11} "
          f"{'realised - quoted':>18}")
    d["bkt"] = pd.cut(d.resid, [-1, -.05, -.02, -.005, .005, .02, .05, 1])
    for b, g in d.groupby("bkt"):
        if len(g) < 200:
            continue
        lo, hi = ci(g, "e_q")
        print(f"     {str(b):>16} {len(g):>7,} {g.resid.mean()*100:>+10.2f}c "
              f"{g.e_q.mean():>+9.4f} [{lo:+.3f},{hi:+.3f}]")
    print("     a rung quoted BELOW its neighbours' fit (negative residual)")
    print("     should resolve YES more often than its quote implies.")

    print("\n  C. ECONOMICS on |residual| > 2c")
    s = d[d.resid.abs() > 0.02].copy()
    if len(s) < 100:
        print("     too few")
        return
    # trade toward the fit: buy when quoted cheap, sell when quoted dear
    buy = s[s.resid < 0]
    sell = s[s.resid > 0]
    tk_buy = buy.win - (buy.mid + buy.sp / 200) - fee(buy.mid)
    tk_sell = (1 - sell.win) - (1 - sell.mid + sell.sp / 200) - fee(sell.mid)
    mk_buy = buy.win - buy.mid - fee(buy.mid)
    mk_sell = (1 - sell.win) - (1 - sell.mid) - fee(sell.mid)
    for lab, v in (("TAKER (cross the spread)",
                    np.concatenate([tk_buy.values, tk_sell.values])),
                   ("MAKER (rest at the quote)",
                    np.concatenate([mk_buy.values, mk_sell.values]))):
        t = pd.DataFrame({"key": np.concatenate([buy.key.values,
                                                 sell.key.values]), "v": v})
        lo, hi = ci(t, "v")
        print(f"     {lab:<26} n={len(t):>6,} edge {t.v.mean()*100:>+6.2f}c "
              f"CI [{lo*100:+.2f}c,{hi*100:+.2f}c]")


def main():
    report(loo_residuals(WNBA, "KXWNBATOTAL%"), "WNBA totals")
    report(loo_residuals(NBA, "KXNBATOTAL-%"), "NBA totals")


if __name__ == "__main__":
    main()
