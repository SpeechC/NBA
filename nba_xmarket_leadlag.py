"""Which leg is the laggard -- with legs defined economically and honest se.

nba_xmarket_coherence.py found an asymmetry, but it labelled the legs by SORTED
TICKER, which is alphabetical and carries no economic meaning (it put BOS, NYK
and OKC in "leg 0" -- one home team and two away). An asymmetry across an
arbitrary labelling is not a mechanism, so the legs are redefined here by things
a trader can see in advance:

    favourite / underdog     by mid price
    liquid / illiquid        by traded volume over the window
    tight / wide             by quoted spread

and the question is which of those, if any, predicts who does the correcting.

INFERENCE. The naive regression above reported t = -108. That is nonsense: the
sample is 3 events observed every minute, so the observations are enormously
autocorrelated and the effective n is nearer 3 than 43,000. Everything here is
bootstrapped over contiguous BLOCKS within event, and the event count is printed
next to every number so it cannot be read as more than it is.
"""
import os, sqlite3, argparse
import numpy as np, pandas as pd

DB = os.environ.get("NBA_XMARKET_DB",
                    os.path.expanduser("~/data/kalshi_local/kalshi_nba_xmarket.sqlite"))
RNG = np.random.default_rng(20260924)
BLOCK_MIN = 360           # 6h blocks -- longer than any decay horizon tested


def build(con, interval=1):
    d = pd.read_sql(
        "SELECT event_ticker,ticker,end_period_ts ts,yes_bid_close b,yes_ask_close a,"
        "volume v FROM candles WHERE series_ticker='KXNBAGAME' AND period_interval=?",
        con, params=(interval,))
    out = []
    for ev, g in d.groupby('event_ticker'):
        tk = sorted(g.ticker.unique())
        if len(tk) != 2:
            continue
        idx = np.arange(g.ts.min(), g.ts.max() + 1, 60)
        cols = {'ts': idx}
        for i, t in enumerate(tk):
            s = (g[g.ticker == t].sort_values('ts')
                 .drop_duplicates('ts', keep='last').set_index('ts').reindex(idx).ffill())
            cols[f'b{i}'], cols[f'a{i}'] = s.b.values, s.a.values
            cols[f'cv{i}'] = s.v.fillna(0).cumsum().values
        f = pd.DataFrame(cols).dropna()
        f['event'] = ev
        f['name0'], f['name1'] = tk[0].split('-')[-1], tk[1].split('-')[-1]
        out.append(f)
    f = pd.concat(out, ignore_index=True)
    f['m0'] = (f.b0 + f.a0) / 2
    f['m1'] = (f.b1 + f.a1) / 2
    f['inc'] = f.m0 + f.m1 - 1.0
    f['s0'], f['s1'] = f.a0 - f.b0, f.a1 - f.b1
    return f


def boot_beta(x, y, blocks, nboot=2000):
    """Slope with a block bootstrap se. blocks is an integer block id per row."""
    b = np.polyfit(x, y, 1)[0]
    ub = np.unique(blocks)
    if len(ub) < 4:
        return b, np.nan, np.nan, len(ub)
    draws = []
    idx_by_block = {k: np.where(blocks == k)[0] for k in ub}
    for _ in range(nboot):
        pick = RNG.choice(ub, len(ub), replace=True)
        ii = np.concatenate([idx_by_block[k] for k in pick])
        if len(ii) > 5 and np.ptp(x[ii]) > 1e-9:
            draws.append(np.polyfit(x[ii], y[ii], 1)[0])
    lo, hi = np.percentile(draws, [2.5, 97.5])
    return b, lo, hi, len(ub)


def main(horizons):
    con = sqlite3.connect(DB)
    f = build(con)
    con.close()
    f = f.sort_values(['event', 'ts']).reset_index(drop=True)
    f['block'] = (f.groupby('event').cumcount() // BLOCK_MIN)
    f['block'] = (f.event.astype('category').cat.codes.astype('int64') * 10000
                  + f.block.astype('int64'))

    print(f"events {f.event.nunique()}   minutes {len(f):,}   "
          f"blocks {f.block.nunique()} of {BLOCK_MIN}m")
    print(f"incoherence sd {f.inc.std()*100:.3f}c   "
          f"|inc|>2c on {100*(f.inc.abs()>.02).mean():.1f}% of minutes")

    # ---- economic leg labels, recomputed per row -----------------------------
    fav_is0 = (f.m0 >= f.m1).values
    liq_is0 = (f.cv0 >= f.cv1).values
    tight_is0 = (f.s0 <= f.s1).values

    print("\nhow often each label picks leg 0 (1.00 or 0.00 => the label is "
          "constant within the sample and cannot be tested):")
    for nm, v in (('favourite', fav_is0), ('more liquid', liq_is0), ('tighter', tight_is0)):
        print(f"  {nm:12s} {v.mean():.2f}")

    for h in horizons:
        g = f.copy()
        for c in ('m0', 'm1'):
            g[f'd{c}'] = g.groupby('event')[c].shift(-h) - g[c]
        g = g.dropna(subset=['dm0', 'dm1'])
        if len(g) < 500:
            continue
        fav = (g.m0 >= g.m1).values
        print(f"\n--- horizon {h}m   n={len(g):,} ---")
        for nm, sel in (('FAVOURITE', fav), ('MORE LIQUID', (g.cv0 >= g.cv1).values),
                        ('TIGHTER BOOK', (g.s0 <= g.s1).values)):
            if sel.mean() in (0.0, 1.0):
                print(f"  {nm:13s} label constant -- not testable here")
                continue
            # move of the labelled leg, and of its complement
            dsel = np.where(sel, g.dm0, g.dm1)
            doth = np.where(sel, g.dm1, g.dm0)
            x = g.inc.values
            bs, lo_s, hi_s, nb = boot_beta(x, dsel, g.block.values)
            bo, lo_o, hi_o, _ = boot_beta(x, doth, g.block.values)
            print(f"  {nm:13s} beta(labelled) {bs:+.4f} [{lo_s:+.4f},{hi_s:+.4f}]   "
                  f"beta(other) {bo:+.4f} [{lo_o:+.4f},{hi_o:+.4f}]   blocks={nb}")

    print("\nA mechanism requires the two intervals NOT to overlap. With this")
    print("many events they almost certainly will, which is the point: this is")
    print("a pilot that sizes the effect and proves the pipeline, not a result.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--horizons", default="15,60,240")
    a = ap.parse_args()
    main([int(x) for x in a.horizons.split(",")])
