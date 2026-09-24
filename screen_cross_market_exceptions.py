"""Exceptions to the rule, not the rule.

CROSS_MARKET_SIGMA_SCAN.md established a POOLED result: when the spread and the
moneyline disagree, the moneyline is right. That is a central tendency. It says
nothing about whether the relationship is uniform, and this programme's own
finding is that market errors are EPISODIC rather than evenly spread.

Two separate questions here.

A. MECHANISM. Margin dispersion should scale with possessions. If the book
   scales sigma with the expected total more slowly than reality does, then in
   high-total games true sigma exceeds implied sigma, the favourite is
   overpriced, and the exception is directional and pregame-observable. This is
   OUR mechanism -- the pace channel -- pointed at the sides market.

B. CONDITIONING. Where, if anywhere, does the residual change sign? Tested
   across 8 pregame-observable dimensions, with a permutation calibration so
   that "the best cell" is judged against how good a best cell gets by chance.

BASELINE. A cell's ROI is not judged against zero. Betting the residual-favoured
side is compared with betting the OPPOSITE side at the same moneylines: the mean
of the two is that cell's pure vig drag, and the SPREAD between them is the
signal. This keeps a cell of heavy favourites from looking skilful.
"""
import numpy as np, pandas as pd
from scipy.stats import norm

RNG = np.random.default_rng(20260924)
df = pd.read_csv('/mnt/c/NBA2/dfMaster_OT_2017-2026.csv', low_memory=False)

d = pd.DataFrame({
    'date':    pd.to_datetime(df['DATE'], errors='coerce'),
    'spread':  pd.to_numeric(df['CLOSING SPREAD_H'], errors='coerce'),
    'ospread': pd.to_numeric(df['OPENING SPREAD_H'], errors='coerce'),
    'total':   pd.to_numeric(df['CLOSING TOTAL_H'], errors='coerce'),
    'ototal':  pd.to_numeric(df['OPENING TOTAL_H'], errors='coerce'),
    'ml_h':    pd.to_numeric(df['MONEYLINE_H'], errors='coerce'),
    'ml_r':    pd.to_numeric(df['MONEYLINE_R'], errors='coerce'),
    'f_h':     pd.to_numeric(df['F_H'], errors='coerce'),
    'f_r':     pd.to_numeric(df['F_R'], errors='coerce'),
    'rest_h':  df['TEAM\nREST DAYS_H'].astype(str),
    'rest_r':  df['TEAM\nREST DAYS_R'].astype(str),
    'dataset': df['DATASET_H'].astype(str),
})
d['margin'] = d.f_h - d.f_r
d = d.dropna(subset=['spread', 'total', 'ml_h', 'ml_r', 'margin'])
d = d[(d.ml_h.abs() >= 100) & (d.ml_r.abs() >= 100) & (d.margin != 0)]
d['home_win'] = (d.margin > 0).astype(float)

a2p = lambda m: np.where(m < 0, -m / (-m + 100.0), 100.0 / (m + 100.0))
d['raw_h'], d['raw_r'] = a2p(d.ml_h), a2p(d.ml_r)
d['overround'] = d.raw_h + d.raw_r
d['p_ml'] = d.raw_h / d.overround
d['season'] = np.where(d.date.dt.month >= 8, d.date.dt.year, d.date.dt.year - 1)
d['playoff'] = d.dataset.str.contains('Playoff', case=False)
d = d.reset_index(drop=True)

print(f"n = {len(d)}   seasons {d.season.min()}-{d.season.max()}")

# =====================================================================  A
print("\n" + "=" * 72)
print("A.  DOES THE BOOK SCALE SIGMA WITH THE EXPECTED TOTAL?")
print("=" * 72)
z = norm.ppf(d.p_ml.clip(1e-6, 1 - 1e-6))
d['sig_imp'] = np.where(np.abs(z) > 1e-9, -d.spread / z, np.nan)

d['tot_bkt'] = pd.qcut(d.total, 6, duplicates='drop')
print(f"  {'closing total':>16s} {'n':>5s} {'sd(margin+spr)':>15s} {'implied sigma':>14s} {'gap':>7s}")
rows = []
for b, g in d.groupby('tot_bkt', observed=True):
    gg = g[g.spread.abs() >= 3]
    real = (g.margin + g.spread).std()
    imp = gg.sig_imp.median()
    rows.append((g.total.mean(), real, imp, len(g)))
    print(f"  {str(b):>16s} {len(g):5d} {real:15.3f} {imp:14.3f} {real-imp:+7.3f}")

arr = np.array([(t, r, i) for t, r, i, _ in rows])
sr = np.polyfit(arr[:, 0], arr[:, 1], 1)[0]
si = np.polyfit(arr[:, 0], arr[:, 2], 1)[0]
print(f"\n  slope of REALISED sigma vs total : {sr:+.5f} pts of sigma per pt of total")
print(f"  slope of IMPLIED  sigma vs total : {si:+.5f}")
print(f"  under-scaling gap                : {sr-si:+.5f}")
print("  (positive gap => book under-scales dispersion => favourites overpriced")
print("   in high-total games.  Traded directly in B as 'total' below.)")

# =====================================================================  prep
# Flexible OOS spread->P map removes MY misspecification from the residual.
d['p_flex'] = np.nan
for s in d.season.unique():
    tr = d[d.season != s]
    m = tr.groupby('spread').p_ml.mean()
    m = m[tr.groupby('spread').size() >= 20]
    d.loc[d.season == s, 'p_flex'] = d.loc[d.season == s, 'spread'].map(m).values
d = d.dropna(subset=['p_flex']).reset_index(drop=True)
d['resid'] = d.p_ml - d.p_flex

d['payout_h'] = np.where(d.ml_h < 0, 100.0 / -d.ml_h, d.ml_h / 100.0)
d['payout_r'] = np.where(d.ml_r < 0, 100.0 / -d.ml_r, d.ml_r / 100.0)


def roi(sub, back_home):
    """ROI of backing `back_home` at the real moneyline."""
    pay = np.where(back_home, sub.payout_h, sub.payout_r)
    won = np.where(back_home, sub.home_win, 1 - sub.home_win)
    return np.where(won == 1, pay, -1.0)


def cell_stat(sub):
    """(signal spread, its z, n). Signal = residual-side ROI minus anti-side ROI."""
    if len(sub) < 120:
        return None
    bh = (sub.resid < 0).values          # ML dear on home => value on the road
    a, b = roi(sub, bh), roi(sub, ~bh)
    diff = a - b                          # paired: same games, opposite sides
    if diff.std() == 0:
        return None
    return diff.mean() * 100, diff.mean() / (diff.std() / np.sqrt(len(diff))), len(sub)


# =====================================================================  B
print("\n" + "=" * 72)
print("B.  WHERE DOES THE RULE BEND?   signal = ROI(residual side) - ROI(other side)")
print("    positive => the RESIDUAL is right there (an exception)")
print("    negative => the MONEYLINE is right there (the pooled rule)")
print("=" * 72)

d['absres'] = d.resid.abs()
d['move'] = d.spread - d.ospread
d['tmove'] = d.total - d.ototal
d['b2b_h'] = d.rest_h.str.contains('B2B')
d['b2b_r'] = d.rest_r.str.contains('B2B')

DIMS = {
    'total (closing)':  pd.qcut(d.total, 5, duplicates='drop'),
    '|spread|':         pd.cut(d.spread.abs(), [0, 2, 4, 7, 10, 40], right=False),
    'overround':        pd.qcut(d.overround, 4, duplicates='drop'),
    '|residual|':       pd.qcut(d.absres, 4, duplicates='drop'),
    'spread move':      pd.cut(d.move, [-20, -1.01, -0.01, 0.99, 20], right=False),
    'season':           d.season,
    'rest spot':        np.select([d.b2b_h & ~d.b2b_r, ~d.b2b_h & d.b2b_r,
                                   d.b2b_h & d.b2b_r], ['home B2B', 'road B2B', 'both B2B'],
                                  'neither'),
    'playoff':          d.playoff,
}

best = None
allcells = []
for name, key in DIMS.items():
    print(f"\n  -- {name}")
    for b, g in d.groupby(key, observed=True):
        r = cell_stat(g)
        if r is None:
            continue
        sig, zz, n = r
        allcells.append((name, str(b), sig, zz, n))
        flag = '  <<<' if zz > 1.96 else ''
        print(f"     {str(b):>18s} n={n:5d}   signal {sig:+7.2f}%   z {zz:+6.2f}{flag}")
        if best is None or zz > best[3]:
            best = (name, str(b), sig, zz, n)

print("\n" + "=" * 72)
print(f"BEST CELL: {best[0]} = {best[1]}   signal {best[2]:+.2f}%  z {best[3]:+.2f}  n={best[4]}")

# Permutation: how good does the best cell get when the residual carries no
# information?  Shuffle the SIGN of the residual within season, keep everything
# else -- this destroys the signal while preserving prices, cells and n.
print("Permutation calibration (500 draws, residual sign shuffled within season)")
nulls = []
for it in range(500):
    dd = d.copy()
    flip = RNG.choice([-1, 1], size=len(dd))
    dd['resid'] = dd.resid.values * flip
    bz = -9
    for name, key in DIMS.items():
        for b, g in dd.groupby(key, observed=True):
            r = cell_stat(g)
            if r and r[1] > bz:
                bz = r[1]
    nulls.append(bz)
nulls = np.array(nulls)
print(f"  null best-cell z: median {np.median(nulls):+.2f}  95th {np.percentile(nulls,95):+.2f}"
      f"  max {nulls.max():+.2f}")
print(f"  observed best-cell z {best[3]:+.2f}  ->  p = {(nulls >= best[3]).mean():.4f}")
