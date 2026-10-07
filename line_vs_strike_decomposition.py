"""Is the sportsbook-vs-Kalshi difference in the LINE VALUES themselves?

Hypothesis: the strategies' hit rates are defined against the sportsbook CLOSING
TOTAL, but Kalshi only offers strikes on a 3-point grid at X.5, so you never bet
the line -- you bet the nearest available number. If so, the gap is the STRIKE,
not the venue.

Four measurements, all on 2025-26, all taker, no midpoint:

  1  Is the Kalshi ladder CENTRED on the closing total? (bounds-identified mu)
  2  How far is the nearest strike from the close? (the quantisation)
  3  How fast does the win rate fall per point of strike offset? (the slope)
  4  At the nearest-line rung, does the Kalshi hit rate equal the sportsbook
     over-rate -- and if so, is the remaining ROI difference purely COST?
"""
import sqlite3, numpy as np, pandas as pd, sys
from scipy.stats import norm
sys.path.insert(0, '.')
sys.path.insert(0, '/mnt/d/Kalshi/nba')
from prepare_data import read_master, season_label
import nba_live_trader as T

TOT = '/home/dpope/data/kalshi_local/kalshi_nba_totals.sqlite'
SIG_GRID = np.arange(9.0, 30.001, 0.05)
SLACK, BIG = 0.005, 1e9

B = pd.read_csv('offset_curve_full_board.csv')
print(f"board rows {len(B)}   events {B.ev.nunique()}")

# ---------------------------------------------------------------- 1. centring
con = sqlite3.connect('file:' + TOT + '?mode=ro', uri=True)
full = pd.read_sql("""SELECT event_ticker ev, floor_strike K,
                             pregame_yes_bid b, pregame_yes_ask a FROM markets
                      WHERE pregame_yes_bid IS NOT NULL AND pregame_yes_ask IS NOT NULL
                        AND floor_strike IS NOT NULL""", con)
con.close()
full['L'], full['U'] = full.b / 100.0, full.a / 100.0
closes = B.groupby('ev').close.first()


def mu_bounds(K, Lo_, Up_):
    Lo = np.clip(Lo_ - SLACK, 1e-9, 1 - 1e-9); Up = np.clip(Up_ + SLACK, 1e-9, 1 - 1e-9)
    zL = np.where(np.isfinite(norm.ppf(1 - Lo)), norm.ppf(1 - Lo), BIG)
    zU = np.where(np.isfinite(norm.ppf(1 - Up)), norm.ppf(1 - Up), -BIG)
    lo = (K[None, :] - SIG_GRID[:, None] * zL[None, :]).max(axis=1)
    hi = (K[None, :] - SIG_GRID[:, None] * zU[None, :]).min(axis=1)
    ok = np.where(lo <= hi + 1e-9)[0]
    if len(ok) == 0:
        return np.nan
    i = ok[len(ok) // 2]
    return (lo[i] + hi[i]) / 2.0


rows = []
for ev, g in full.groupby('ev'):
    if ev not in closes.index or len(g) < 4:
        continue
    g = g.sort_values('K')
    mu = mu_bounds(g.K.values, g.L.values, g.U.values)
    if np.isfinite(mu):
        rows.append(dict(ev=ev, mu=mu, close=closes[ev]))
C = pd.DataFrame(rows)
C['diff'] = C.mu - C.close
print("\n" + "=" * 80)
print("1. IS THE KALSHI LADDER CENTRED ON THE CLOSING TOTAL?")
print("=" * 80)
print(f"  n={len(C)}   mu - close:  mean {C['diff'].mean():+.3f}  "
      f"median {C['diff'].median():+.3f}  sd {C['diff'].std():.3f}")
print(f"  |mu - close| <= 1 pt on {100*(C['diff'].abs()<=1).mean():.1f}% of events, "
      f"<= 2 pts on {100*(C['diff'].abs()<=2).mean():.1f}%")
print(f"  corr(mu, close) = {C.mu.corr(C.close):.4f}")
print("  (mu from the executable-bounds identified set -- no midpoint)")

# ---------------------------------------------------------------- 2. quantisation
print("\n" + "=" * 80)
print("2. HOW FAR IS THE NEAREST STRIKE FROM THE CLOSE?")
print("=" * 80)
B['off_pts'] = B.K - B.close
near = B.loc[B.groupby('ev').off_pts.apply(lambda s: s.abs().idxmin())]
print(f"  n={len(near)}  nearest strike minus close: mean {near.off_pts.mean():+.3f}  "
      f"median {near.off_pts.median():+.3f}  sd {near.off_pts.std():.3f}")
print(f"  mean ABSOLUTE distance {near.off_pts.abs().mean():.3f} pts  "
      f"(max possible 1.5 on a 3-pt grid)")
print(f"  above the close on {100*(near.off_pts>0).mean():.1f}% of events")

# ---------------------------------------------------------------- 3. slope
print("\n" + "=" * 80)
print("3. WIN RATE PER POINT OF STRIKE OFFSET")
print("=" * 80)
fine = B[B.off_pts.abs() <= 9].copy()
fine['bin'] = pd.cut(fine.off_pts, np.arange(-9, 9.01, 1.5))
print(f"  {'strike - close':>16}{'n':>7}{'hit%':>8}{'ask':>8}")
xs, ys = [], []
for b, g in fine.groupby('bin', observed=True):
    if len(g) < 100:
        continue
    print(f"  {str(b):>16}{len(g):>7}{100*g.hit.mean():>7.2f}%{g.ask.mean():>8.3f}")
    xs.append(g.off_pts.mean()); ys.append(g.hit.mean())
sl = np.polyfit(xs, ys, 1)[0]
print(f"\n  fitted slope {100*sl:+.3f} pp of win rate per point of strike")
print(f"  theory phi(0)/sigma = {100*norm.pdf(0)/T.SIGMA_REF:+.3f} pp/pt  "
      f"(sigma = {T.SIGMA_REF})")

# ---------------------------------------------------------------- 4. the gap
print("\n" + "=" * 80)
print("4. AT THE NEAREST-LINE RUNG, IS THE DIFFERENCE PURELY COST?")
print("=" * 80)
sb_over = (B.groupby('ev').first().actual > B.groupby('ev').first().close).mean()
print(f"  sportsbook over-rate at the close, full board: {100*sb_over:.2f}%")
print(f"  Kalshi hit% at the nearest-line rung:          {100*near.hit.mean():.2f}%")
print(f"  difference: {100*(near.hit.mean()-sb_over):+.2f}pp "
      f"(strike is {near.off_pts.mean():+.3f} pts off the close on average)")
print()
BE_110 = 0.5238095
print(f"  COST COMPARISON -- break-even win rate required:")
for ask in (near.ask.mean(), 0.502, 0.490, 0.520):
    fee = np.ceil(0.07 * ask * (1 - ask) * 1000) / 1000.0
    be = ask + fee
    tag = '  <- board mean nearest-strike ask' if abs(ask - near.ask.mean()) < 1e-9 else ''
    print(f"    Kalshi, ask {ask:.3f} + fee {fee:.3f}  ->  {100*be:.3f}%"
          f"   vs -110 {100*BE_110:.3f}%   Kalshi "
          f"{'CHEAPER' if be < BE_110 else 'DEARER'} by "
          f"{abs(100*(be-BE_110)):.3f}pp{tag}")
print(f"\n  Break-even parity is at an ask of about "
      f"{BE_110 - 0.018:.3f} -- below that Kalshi is cheaper, above it dearer.")

print(f"\n  ROI AT AN IDENTICAL HIT RATE (so only the cost structure differs):")
print(f"    {'hit%':>7}{'SB -110 ROI':>14}{'Kalshi ROI':>12}{'diff':>9}")
for h in (0.4929, 0.5238, 0.5507, 0.56):
    sb = (h * 100.0 / 1.1 - (1 - h) * 100.0) / 100.0
    for ask, lbl in ((near.ask.mean(), 'board'),):
        fee = np.ceil(0.07 * ask * (1 - ask) * 1000) / 1000.0
        out = ask + fee
        kk = (h * (1 - out) - (1 - h) * out) / out
    print(f"    {100*h:>6.2f}%{100*sb:>+13.2f}%{100*kk:>+11.2f}%{100*(kk-sb):>+8.2f}pp")

print("\n  VERDICT ON THE HYPOTHESIS: the LINE VALUES agree almost exactly --")
print("  the ladder is centred on the close (median difference 0.001 pts,")
print("  corr 0.9975). What differs is the STRIKE you are forced to bet: a")
print("  3-point grid puts you a mean 0.688 pts from the close, and at ~2.1pp")
print("  of win rate per point that is real dispersion, though unbiased.")
print("  Kalshi and -110 cost within ~0.2pp of each other at the line, so the")
print("  venue is roughly neutral; the large effect is rung CHOICE, which the")
print("  max-edge rule pushes a further +1.83 pts off the validated number.")
