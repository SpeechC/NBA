"""Cross-market sigma-consistency scan, run on the sportsbook proxy.

THE TEST (Oracle-7's edge column, with sigma estimated rather than chosen):
  A closing spread S_h (home) and a closing moneyline pair imply the SAME
  quantity -- P(home margin > 0) -- through different contracts. Under a normal
  margin distribution, P = Phi(-S_h / sigma). If the book's two markets are
  internally consistent, the sigma that reconciles them is constant across the
  board, and the residual is noise.

KILL CONDITION (user's, stated up front): if implied sigma across rungs is
tight, there is nothing here.

NOTE ON WHAT THIS IS. This is the SPORTSBOOK, not Kalshi. Kalshi's settled
NBA markets are purged from the API, so no historical Kalshi spread/moneyline
board exists to test. This answers the prior question -- does a spread<->
moneyline inconsistency exist in NBA pricing at all -- for free, on 9 seasons.
"""
import numpy as np, pandas as pd
from scipy.stats import norm

P = '/mnt/c/NBA2/dfMaster_OT_2017-2026.csv'
df = pd.read_csv(P, low_memory=False)

d = pd.DataFrame({
    'date':   pd.to_datetime(df['DATE'], errors='coerce'),
    'spread': pd.to_numeric(df['CLOSING SPREAD_H'], errors='coerce'),
    'ml_h':   pd.to_numeric(df['MONEYLINE_H'], errors='coerce'),
    'ml_r':   pd.to_numeric(df['MONEYLINE_R'], errors='coerce'),
    'f_h':    pd.to_numeric(df['F_H'], errors='coerce'),
    'f_r':    pd.to_numeric(df['F_R'], errors='coerce'),
})
d['margin'] = d['f_h'] - d['f_r']
d['home_win'] = (d['margin'] > 0).astype(float)
d = d.dropna(subset=['spread', 'ml_h', 'ml_r', 'margin'])
d = d[(d.ml_h.abs() >= 100) & (d.ml_r.abs() >= 100)]
# A tie is impossible in NBA; guard anyway.
d = d[d['margin'] != 0]


def american_to_prob(m):
    m = np.asarray(m, float)
    return np.where(m < 0, -m / (-m + 100.0), 100.0 / (m + 100.0))


d['raw_h'] = american_to_prob(d.ml_h)
d['raw_r'] = american_to_prob(d.ml_r)
d['overround'] = d.raw_h + d.raw_r
# Proportional de-vig. Sensitivity to this choice is checked below.
d['p_ml'] = d.raw_h / d.overround
d['season'] = np.where(d.date.dt.month >= 8, d.date.dt.year, d.date.dt.year - 1)

print(f"games {len(d)}  seasons {d.season.min()}-{d.season.max()}  "
      f"median overround {d.overround.median():.4f}")
print(f"margin: mean {d.margin.mean():+.3f}  sd {d.margin.std():.3f}  "
      f"home win {d.home_win.mean():.4f}")

# ---------------------------------------------------------------- 1. outcome sigma
# sigma that the ACTUAL margins imply, given the spread as the centre.
resid = d.margin + d.spread            # spread_h is negative for a favorite
sig_out = resid.std()
print(f"\n[1] sd(margin + spread) = {sig_out:.4f}   mean resid {resid.mean():+.4f}")

# ---------------------------------------------------------------- 2. implied sigma
# sigma that reconciles each game's moneyline with its own spread.
z = norm.ppf(d.p_ml.clip(1e-6, 1 - 1e-6))
with np.errstate(divide='ignore', invalid='ignore'):
    d['sig_imp'] = np.where(np.abs(z) > 1e-9, -d.spread / z, np.nan)

# Only meaningful away from spread 0, where both sides -> 0/0.
big = d[d.spread.abs() >= 3].copy()
print(f"[2] per-game implied sigma  (|spread|>=3, n={len(big)}):")
print(f"    median {big.sig_imp.median():.3f}   IQR "
      f"{big.sig_imp.quantile(.25):.3f}-{big.sig_imp.quantile(.75):.3f}")

print("\n[3] implied sigma by |spread| bucket  (is the curve FLAT?)")
print(f"    {'bucket':>10s} {'n':>6s} {'sig_imp':>9s} {'sd(marg+spr)':>13s} {'p_ml':>8s} {'winrate':>8s}")
d['absspr'] = d.spread.abs()
bins = [0, 2, 4, 6, 8, 10, 13, 40]
d['bkt'] = pd.cut(d.absspr, bins, right=False)
for b, g in d.groupby('bkt', observed=True):
    gg = g[g.absspr >= 3]
    si = gg.sig_imp.median() if len(gg) else np.nan
    fav = np.where(g.spread < 0, g.home_win, 1 - g.home_win)
    pf = np.where(g.spread < 0, g.p_ml, 1 - g.p_ml)
    print(f"    {str(b):>10s} {len(g):6d} {si:9.3f} {(g.margin+g.spread).std():13.3f} "
          f"{pf.mean():8.4f} {fav.mean():8.4f}")

# ---------------------------------------------------------------- 4. the residual
# Fit ONE sigma by matching the board, then look at what is left over.
from scipy.optimize import brentq


def board_mismatch(s):
    return float((norm.cdf(-d.spread / s) - d.p_ml).mean())


sig_fit = brentq(board_mismatch, 5.0, 30.0)
d['p_spr'] = norm.cdf(-d.spread / sig_fit)
d['resid'] = d.p_ml - d.p_spr
print(f"\n[4] single sigma reconciling the whole board: {sig_fit:.4f}")
print(f"    (outcome sigma was {sig_out:.4f})")
print(f"    residual p_ml - p_spread:  mean {d.resid.mean():+.5f}  "
      f"sd {d.resid.std():.5f}  |>2pp| {100*(d.resid.abs()>.02).mean():.1f}%  "
      f"|>5pp| {100*(d.resid.abs()>.05).mean():.1f}%")

# ---------------------------------------------------------------- 5. does it pay?
# The only question that matters: when the moneyline disagrees with the spread,
# which one is right?  Bet the SIDE THE RESIDUAL FAVOURS at the real moneyline,
# vig included -- no de-vigged fantasy price.
print("\n[5] does the residual predict the outcome?  (bet at the REAL moneyline)")
print(f"    {'|resid| >=':>11s} {'n':>6s} {'bets/szn':>9s} {'winrate':>8s} "
      f"{'exp':>8s} {'ROI%':>8s} {'z':>7s}")
nsz = d.season.nunique()
for thr in [0.00, 0.01, 0.02, 0.03, 0.05]:
    s = d[d.resid.abs() >= thr].copy()
    if len(s) < 30:
        continue
    # residual > 0  =>  moneyline says home is MORE likely than the spread does
    #                   => the ML is the dearer side; the value is on the ROAD.
    back_home = s.resid < 0
    ml = np.where(back_home, s.ml_h, s.ml_r)
    won = np.where(back_home, s.home_win, 1 - s.home_win)
    payout = np.where(ml < 0, 100.0 / -ml, ml / 100.0)
    pnl = np.where(won == 1, payout, -1.0)
    exp = np.where(back_home, s.p_spr, 1 - s.p_spr).mean()
    roi = pnl.mean() * 100
    zz = pnl.mean() / (pnl.std() / np.sqrt(len(pnl))) if pnl.std() > 0 else np.nan
    print(f"    {thr:11.2f} {len(s):6d} {len(s)/nsz:9.0f} {won.mean():8.4f} "
          f"{exp:8.4f} {roi:8.2f} {zz:7.2f}")

# ---------------------------------------------------------------- 6. de-vig sensitivity
print("\n[6] de-vig method sensitivity (residual sd)")
# Additive (equal-shares) de-vig instead of proportional.
exc = (d.overround - 1.0) / 2.0
p_add = (d.raw_h - exc).clip(1e-6, 1 - 1e-6)
for nm, p in [('proportional', d.p_ml), ('additive', p_add)]:
    r = p - d.p_spr
    print(f"    {nm:14s} mean {r.mean():+.5f}  sd {r.std():.5f}")
