"""Within-KXNBAGAME coherence and lead-lag: the purest cross-market test.

The two markets in a KXNBAGAME event are COMPLEMENTS -- exactly one settles at
$1. So mid_A + mid_B must equal 1, with no model, no sigma, no link function and
no outcome data. Any deviation is arithmetic, not forecasting.

This runs the ordering the programme agreed on:

  STAGE 1 (price discovery)  Does incoherence at time t predict which leg moves
                             next?  A market that corrects toward its complement
                             is the LAGGING leg, and that is a mechanism.
  STAGE 2 (execution)        Only if Stage 1 passes: is the implied trade
                             executable after fees and depth?

Stage 2 is NOT run on a Stage 1 failure. A structural inconsistency is not
automatically tradable -- that was the error this ordering exists to prevent.

FORWARD-FILL IS MANDATORY. Candles emit only on book change, so a raw join
drops every quiet minute and fabricates illiquidity.
"""
import os, sqlite3, argparse
import numpy as np, pandas as pd

DB = os.environ.get("NBA_XMARKET_DB",
                    os.path.expanduser("~/data/kalshi_local/kalshi_nba_xmarket.sqlite"))
FEE_RATE = 0.07


def fee(p, n=1):
    import math
    return math.ceil(FEE_RATE * p * (1.0 - p) * n * 1000) / 1000.0


def load(con, interval=1):
    d = pd.read_sql(
        "SELECT event_ticker,ticker,end_period_ts ts,yes_bid_close b,yes_ask_close a,"
        "volume v FROM candles WHERE series_ticker='KXNBAGAME' AND period_interval=?",
        con, params=(interval,))
    return d


def grid(d):
    """Forward-fill each ticker onto the event's common minute grid."""
    out = []
    for ev, g in d.groupby('event_ticker'):
        tk = sorted(g.ticker.unique())
        if len(tk) != 2:
            continue
        lo, hi = g.ts.min(), g.ts.max()
        idx = np.arange(lo, hi + 1, 60)
        f = pd.DataFrame({'ts': idx})
        for i, t in enumerate(tk):
            s = (g[g.ticker == t].sort_values('ts')
                 .drop_duplicates('ts', keep='last').set_index('ts'))
            r = s.reindex(idx).ffill()
            f[f'b{i}'], f[f'a{i}'] = r.b.values, r.a.values
            f[f'v{i}'] = r.v.fillna(0).values
        f['event'] = ev
        f['t0'], f['t1'] = tk[0], tk[1]
        out.append(f.dropna())
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def main(interval, horizons):
    con = sqlite3.connect(DB)
    d = load(con, interval)
    if d.empty:
        print("no KXNBAGAME candles in the DB yet -- run nba_xmarket_collect.py")
        return
    f = grid(d)
    f['m0'] = (f.b0 + f.a0) / 2
    f['m1'] = (f.b1 + f.a1) / 2
    f['inc'] = f.m0 + f.m1 - 1.0                      # mid incoherence
    f['buy_both'] = f.a0 + f.a1 - 1.0                 # <0 (net of fee) = arb
    f['sell_both'] = 1.0 - (f.b0 + f.b1)              # <0 (net of fee) = arb
    f['spr'] = (f.a0 - f.b0) + (f.a1 - f.b1)

    print(f"events {f.event.nunique()}   aligned minutes {len(f):,}   "
          f"interval {interval}m")
    print(f"\nMID INCOHERENCE  (m0 + m1 - 1)")
    print(f"  mean {f.inc.mean()*100:+.3f}c   median {f.inc.median()*100:+.3f}c   "
          f"sd {f.inc.std()*100:.3f}c")
    print(f"  |inc| > 1c on {100*(f.inc.abs()>.01).mean():5.1f}% of minutes, "
          f"> 2c on {100*(f.inc.abs()>.02).mean():.1f}%")
    print(f"  summed quoted spread: median {f.spr.median()*100:.2f}c")

    print(f"\nARBITRAGE (the only model-free trade), fees included")
    n = len(f)
    for lbl, col, px in (("buy both legs at ask", 'buy_both', (f.a0, f.a1)),
                         ("sell both legs at bid", 'sell_both', (f.b0, f.b1))):
        cost = f[col] + np.array([fee(x) for x in px[0]]) + np.array([fee(x) for x in px[1]])
        k = (cost < 0).sum()
        print(f"  {lbl:24s} profitable on {k:6d} / {n:,} minutes ({100*k/n:.3f}%)"
              + (f"   best {-cost.min()*100:+.2f}c" if k else f"   best {-cost.max()*100:+.2f}c"))

    # ---------------- STAGE 1: does incoherence predict WHICH LEG moves? -------
    print(f"\n{'='*74}\nSTAGE 1 -- PRICE DISCOVERY: does incoherence predict the next move?\n{'='*74}")
    print("  If leg k is the laggard, d(m_k) regresses NEGATIVELY on its own")
    print("  contribution to the incoherence: it moves to close the gap.")
    print(f"  {'horizon':>8s} {'n':>7s} {'beta_leg0':>11s} {'t':>7s} "
          f"{'beta_leg1':>11s} {'t':>7s} {'beta_inc_decay':>15s} {'t':>7s}")
    res = {}
    for h in horizons:
        g = f.sort_values(['event', 'ts']).copy()
        for c in ('m0', 'm1', 'inc'):
            g[f'd{c}'] = g.groupby('event')[c].shift(-h) - g[c]
        g = g.dropna(subset=['dm0', 'dm1', 'dinc'])
        if len(g) < 100:
            continue
        row = []
        for c in ('dm0', 'dm1', 'dinc'):
            y, x = g[c].values, g.inc.values
            b = np.polyfit(x, y, 1)[0]
            yh = np.polyval(np.polyfit(x, y, 1), x)
            se = np.sqrt(((y - yh) ** 2).sum() / (len(y) - 2) / ((x - x.mean()) ** 2).sum())
            row += [b, b / se if se else np.nan]
        res[h] = row
        print(f"  {h:6d}m {len(g):7d} {row[0]:+11.4f} {row[1]:+7.2f} "
              f"{row[2]:+11.4f} {row[3]:+7.2f} {row[4]:+15.4f} {row[5]:+7.2f}")

    print("\n  READING IT: beta_inc_decay is the half-life term. A coefficient of")
    print("  -1 means the incoherence is fully gone by that horizon; 0 means it")
    print("  persists. Leg betas near -0.5/-0.5 mean BOTH legs share the")
    print("  correction (no lead-lag). One near -1 and one near 0 means the")
    print("  first leg is the laggard -- that is the tradable asymmetry.")
    con.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=int, default=1)
    ap.add_argument("--horizons", default="1,5,15,60,240")
    a = ap.parse_args()
    main(a.interval, [int(x) for x in a.horizons.split(",")])
