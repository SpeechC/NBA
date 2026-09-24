"""The exception the mechanism predicts, traded directly.

Section A of screen_cross_market_exceptions.py measured that the book scales
sigma with the expected total at +0.01436 per point while reality scales at
+0.03523 -- 41% of the true rate. If that is real, then in a HIGH-TOTAL game
true dispersion exceeds the dispersion implied by the price, the favourite's win
probability is overstated, and the correction is to back the UNDERDOG.

Section B never tested this. It tested whether the spread/moneyline RESIDUAL
predicts the winner inside total buckets, which is a different question. The
mechanism does not predict a residual; it predicts a DIRECTIONAL error in both
markets at once, because both are built off the same understated sigma.

The trade: back the moneyline underdog, conditioned on the expected total.
Everything is priced at the real American moneyline, vig included.

Note the effect must scale with |spread| as well -- at a pick'em there is no
favourite to overprice -- so the two are crossed.
"""
import numpy as np, pandas as pd
from scipy.stats import norm

RNG = np.random.default_rng(20260924)
df = pd.read_csv('/mnt/c/NBA2/dfMaster_OT_2017-2026.csv', low_memory=False)
d = pd.DataFrame({
    'date':   pd.to_datetime(df['DATE'], errors='coerce'),
    'spread': pd.to_numeric(df['CLOSING SPREAD_H'], errors='coerce'),
    'total':  pd.to_numeric(df['CLOSING TOTAL_H'], errors='coerce'),
    'ml_h':   pd.to_numeric(df['MONEYLINE_H'], errors='coerce'),
    'ml_r':   pd.to_numeric(df['MONEYLINE_R'], errors='coerce'),
    'f_h':    pd.to_numeric(df['F_H'], errors='coerce'),
    'f_r':    pd.to_numeric(df['F_R'], errors='coerce')}).dropna()
d['margin'] = d.f_h - d.f_r
d = d[(d.ml_h.abs() >= 100) & (d.ml_r.abs() >= 100) & (d.margin != 0)]
d['home_win'] = (d.margin > 0).astype(float)
d['season'] = np.where(d.date.dt.month >= 8, d.date.dt.year, d.date.dt.year - 1)
d = d.reset_index(drop=True)

# The dog is whoever the SPREAD makes the dog; spread 0 games are dropped.
d = d[d.spread != 0].copy()
d['dog_is_home'] = d.spread > 0
d['ml_dog'] = np.where(d.dog_is_home, d.ml_h, d.ml_r)
d['dog_won'] = np.where(d.dog_is_home, d.home_win, 1 - d.home_win)
d['pay_dog'] = np.where(d.ml_dog < 0, 100.0 / -d.ml_dog, d.ml_dog / 100.0)
d['pnl_dog'] = np.where(d.dog_won == 1, d.pay_dog, -1.0)
d['absspr'] = d.spread.abs()
nsz = d.season.nunique()
print(f"n = {len(d)}   seasons {nsz}   overall dog ROI "
      f"{d.pnl_dog.mean()*100:+.2f}%   dog win rate {d.dog_won.mean():.4f}")


def blk(s, label):
    """Season-block bootstrap: the honest se when a season is the unit."""
    if len(s) < 100:
        return None
    m = s.pnl_dog.mean() * 100
    per = s.groupby('season').pnl_dog.mean().values
    boot = [RNG.choice(per, len(per), replace=True).mean() * 100 for _ in range(2000)]
    lo, hi = np.percentile(boot, [2.5, 97.5])
    zz = m / (s.pnl_dog.std() / np.sqrt(len(s))) / 100
    return dict(label=label, n=len(s), per_szn=len(s) / nsz, wr=s.dog_won.mean(),
                roi=m, lo=lo, hi=hi, z=zz, pos=(np.array(per) > 0).sum(), nsz=len(per))


print("\n" + "=" * 78)
print("BACK THE UNDERDOG, BY EXPECTED TOTAL   (all prices are the real moneyline)")
print("=" * 78)
print(f"  {'total bucket':>18s} {'n':>5s} {'win%':>7s} {'ROI%':>8s} {'95% CI (season blk)':>22s} {'+szn':>6s}")
d['tb'] = pd.qcut(d.total, 6, duplicates='drop')
for b, g in d.groupby('tb', observed=True):
    r = blk(g, str(b))
    if r:
        print(f"  {r['label']:>18s} {r['n']:5d} {r['wr']*100:7.2f} {r['roi']:+8.2f} "
              f"  [{r['lo']:+6.2f},{r['hi']:+6.2f}]   {r['pos']}/{r['nsz']}")

print("\n" + "=" * 78)
print("CROSSED WITH |SPREAD|   (the mechanism needs a favourite to overprice)")
print("=" * 78)
d['sb'] = pd.cut(d.absspr, [0, 4, 7, 11, 40], right=False)
hdr = sorted(d.sb.dropna().unique().tolist(), key=lambda x: x.left)
print(f"  {'total':>18s} " + " ".join(f"{str(h):>14s}" for h in hdr))
for b, g in d.groupby('tb', observed=True):
    cells = []
    for h in hdr:
        s = g[g.sb == h]
        cells.append(f"{s.pnl_dog.mean()*100:+7.2f}%({len(s):4d})" if len(s) >= 100 else "       --     ")
    print(f"  {str(b):>18s} " + " ".join(cells))

print("\n" + "=" * 78)
print("THE RULE AS THE MECHANISM WOULD STATE IT")
print("=" * 78)
for thr in [224, 226.5, 228.5, 230, 232.5, 235]:
    s = d[(d.total >= thr) & (d.absspr >= 4)]
    r = blk(s, f"total>={thr}, |spr|>=4")
    if r:
        print(f"  {r['label']:>24s} n={r['n']:5d} ({r['per_szn']:4.0f}/szn) "
              f"win {r['wr']*100:5.2f}%  ROI {r['roi']:+6.2f}%  "
              f"CI [{r['lo']:+6.2f},{r['hi']:+6.2f}]  seasons+ {r['pos']}/{r['nsz']}")

print("\n  CONTROL -- the same bet where the mechanism says there is nothing:")
for thr in [215, 213.5]:
    s = d[(d.total <= thr) & (d.absspr >= 4)]
    r = blk(s, f"total<={thr}, |spr|>=4")
    if r:
        print(f"  {r['label']:>24s} n={r['n']:5d} ({r['per_szn']:4.0f}/szn) "
              f"win {r['wr']*100:5.2f}%  ROI {r['roi']:+6.2f}%  "
              f"CI [{r['lo']:+6.2f},{r['hi']:+6.2f}]  seasons+ {r['pos']}/{r['nsz']}")
