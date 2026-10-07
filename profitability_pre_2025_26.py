"""Per-strategy profitability for seasons BEFORE 2025-26.

*** BASIS: SPORTSBOOK AT -110. NOT TAKER, NOT MAKER. ***
Kalshi books exist only for 2025-26, so no taker replay is possible for any
earlier season -- a taker figure needs an executable ask and there isn't one.
This is the -110 flat-stake basis the original backtests used, stated on its
face per the standing labelling rule.

Two reasons to read it as an upper bound even on its own terms:
  * 53% of totals are NOT at -110 and the juice skews AGAINST the bettor; the
    measured hurdle is 1.12 pts of line error, not the 1.089 that -110 implies.
  * A -110 wager settles against the LINE. Kalshi settles a RUNG, and the
    2025-26 replay showed the rung hit rate runs 5-10pp BELOW the line hit rate
    because the max-edge rung sits above the line for an OVER.

Seasons: 2017-18 .. 2024-25 (the file has no 2019-20). 2025-26 excluded.
final7 uses the window reconciled against monitor_season_pnl.py: days_left <= 7
on the Regular Season label, eight calendar days.
"""
import sys, re
import numpy as np, pandas as pd
sys.path.insert(0, '.')
from prepare_data import read_master, season_label

WIN, LOSE = 100.0 / 1.1, -100.0        # $100 flat at -110
CUT = 2025                             # exclude season 2025 (= 2025-26)

raw = read_master(verbose=False)
raw['lbl'] = season_label(raw).astype(str)
d = raw[raw['lbl'].str.contains('Regular Season', na=False)].copy()
d['date'] = pd.to_datetime(d['DATE'], errors='coerce')
d['close'] = pd.to_numeric(d['CLOSING TOTAL_H'], errors='coerce')
d['open'] = pd.to_numeric(d['OPENING TOTAL_H'], errors='coerce')
d['actual'] = pd.to_numeric(d['PTS_H'], errors='coerce') + pd.to_numeric(d['PTS_R'], errors='coerce')
d['gid'] = d['GAME-ID'].astype(str).str.replace(r'\.0$', '', regex=True)
d = d.dropna(subset=['date', 'close', 'actual'])
d = d[d['close'].between(150, 300)].copy()
d['season'] = d['lbl'].str.extract(r'(\d{4})')[0].astype(int)
d['days_left'] = (d.groupby('lbl')['date'].transform('max') - d['date']).dt.days


def report(name, bets, basis):
    """bets: DataFrame with season, won (bool), pushed (bool)."""
    b = bets[~bets.pushed].copy()
    b['pnl'] = np.where(b.won, WIN, LOSE)
    print(f"\n{'='*74}\n{name}   [{basis}]\n{'='*74}")
    print(f"  {'season':>8s} {'bets':>6s} {'hit%':>8s} {'P&L':>10s} {'ROI':>8s}")
    for s, g in b.groupby('season'):
        print(f"  {s:>8d} {len(g):6d} {100*g.won.mean():7.2f}% "
              f"{g.pnl.sum():+10.0f} {100*g.pnl.sum()/(100*len(g)):+7.2f}%")
    n, h = len(b), b.won.mean()
    roi = b.pnl.sum() / (100 * n)
    se = np.sqrt(h * (1 - h) / n)
    z = (h - 1 / 1.909090909 * 0 - 0.5238095) / se      # break-even at -110
    boot = [np.random.default_rng(i).choice(b.pnl.values, n, replace=True).mean() / 100
            for i in range(2000)]
    lo, hi = np.percentile(boot, [2.5, 97.5])
    print(f"  {'TOTAL':>8s} {n:6d} {100*h:7.2f}% {b.pnl.sum():+10.0f} {100*roi:+7.2f}%")
    print(f"           break-even 52.381%   z = {z:+.2f}   "
          f"ROI 95% CI [{100*lo:+.2f}%, {100*hi:+.2f}%]"
          f"  {'EXCLUDES 0' if lo > 0 else 'includes 0'}")
    pos = sum(1 for _, g in b.groupby('season') if g.pnl.sum() > 0)
    print(f"           seasons positive: {pos}/{b.season.nunique()}")
    return n, h, b.pnl.sum(), roi


# ------------------------------------------------------------ crewshock
cw = pd.read_csv('crewshock_walkforward_bets.csv')
cw = cw[cw.season < CUT].copy()
cw['won'] = cw.result.astype(str).str.upper().eq('W')
cw['pushed'] = cw.result.astype(str).str.upper().eq('P')
r_cw = report('CREWSHOCK  (bet OVER at the close, threshold 0.8682)',
              cw[['season', 'won', 'pushed']], 'sportsbook -110, $100 flat')

# ------------------------------------------------------------ final7
f7 = d[(d.days_left <= 7) & (d.season < CUT)].copy()
f7['won'] = f7.actual > f7.close
f7['pushed'] = f7.actual == f7.close
r_f7 = report('FINAL7  (bet OVER every game, days_left <= 7, 8 calendar days)',
              f7[['season', 'won', 'pushed']], 'sportsbook -110, $100 flat')

# ------------------------------------------------------------ move
mv = pd.read_csv('/mnt/c/NBA2/move_signal_states.csv')
mv = mv[mv.MOVE_COMBINED_OOS.notna()].copy()
mv['gid'] = mv['GAME-ID'].astype(str).str.replace(r'\.0$', '', regex=True)
mv = mv.merge(d[['gid', 'season', 'open', 'actual']], on='gid', how='inner')
mv = mv.dropna(subset=['open'])
mv = mv[(mv.MOVE_COMBINED_OOS.abs() >= 1.0) & (mv.season < CUT)].copy()
mv['over'] = mv.MOVE_COMBINED_OOS > 0
mv['won'] = np.where(mv.over, mv.actual > mv.open, mv.actual < mv.open)
mv['pushed'] = mv.actual == mv.open
r_mv = report('MOVE_COMBINED  (|m| >= 1.0, bet the sign, settles vs the OPENER)',
              mv[['season', 'won', 'pushed']], 'sportsbook -110, $100 flat')

print(f"\n{'='*74}\nPACEGAP\n{'='*74}")
print("  NOT RECONSTRUCTED. Its signal is E_pace from the frozen engine and no")
print("  per-game historical export exists; rebuilding it means running")
print("  frozen_models walk-forward. The published figure is pooled over")
print("  2023-2025 and so CANNOT be split to exclude 2025-26:")
print("      n = 3,480   hit 52.59%   ROI +0.39%   CI [50.93%, 54.25%]")
print("  (PREREG_2026_27_PROSPECTIVE.md). The |E_pace| >= 4.77 rule's discovery")
print("  behaviour was n = 1,056, 30.3% of the slate, hit 53.31%.")

print(f"\n{'='*74}\nWHAT EXCLUDING 2025-26 DOES\n{'='*74}")
print(f"  {'strategy':>12s} {'pre-26 bets':>12s} {'pre-26 hit%':>12s} {'pre-26 ROI':>11s}"
      f" {'8-szn hit%':>11s} {'8-szn ROI':>10s}")
pub = {'crewshock': (1390, 54.82, 4.66), 'final7': (527, 56.93, 8.68)}
for nm, r in (('crewshock', r_cw), ('final7', r_f7)):
    p = pub[nm]
    print(f"  {nm:>12s} {r[0]:12d} {100*r[1]:11.2f}% {100*r[3]:+10.2f}% "
          f"{p[1]:10.2f}% {p[2]:+9.2f}%")
print(f"  {'move':>12s} {r_mv[0]:12d} {100*r_mv[1]:11.2f}% {100*r_mv[3]:+10.2f}% "
      f"{'53.44':>10}% {'n/a':>9}")
print("\n  '8-szn' columns are the published all-seasons figures including 2025-26.")
