"""Does a strategy's edge TRAVEL along the ladder, or sit only at the line?

The venues are dual parameterisations of one distribution:
  sportsbook   fixes the PRICE (-110) and solves for the LINE   -> you buy the median
  Kalshi       fixes the LINES (a 3-pt strike grid) and solves for PRICES -> you buy
               any point on the CDF you like
Measured: the ladder's mu IS the close (median difference 0.001 pts, corr
0.9975). So there is no information difference, and the user's objection is
right as far as it goes.

But a strategy's edge is not a distribution -- it is ONE NUMBER about ONE event:
P(total > close) = 54.21% for crewshock. It says nothing about
P(total > close + 6). Translating a hit rate from one strike to another REQUIRES
A MODEL of how the signal moves the distribution, and the trader assumes a pure
location shift of a normal, mu -> mu + delta. Under that assumption the edge at
strike K is Phi((K-mu)/sigma) - Phi((K-mu-delta)/sigma): maximal at the line and
decaying slowly outward.

This tests the assumption directly, using BOXSCORES ONLY -- no Kalshi data, so
all eight seasons are available and the test is properly powered:

    edge(x) = P(actual > close + x | signal) - P(actual > close + x | all games)

If edge(x) is flat in x, the location-shift model is right and the rung choice
should not matter. If edge(x) peaks at x = 0 and decays faster than the model
says, then the extra rungs Kalshi offers are bets the backtest never made.
"""
import sys
import numpy as np, pandas as pd
from scipy.stats import norm
sys.path.insert(0, '.')
sys.path.insert(0, '/mnt/d/Kalshi/nba')
from prepare_data import read_master, season_label
import nba_live_trader as T

raw = read_master(verbose=False)
raw['lbl'] = season_label(raw).astype(str)
d = raw[raw['lbl'].str.contains('Regular Season', na=False)].copy()
d['date'] = pd.to_datetime(d['DATE'], errors='coerce')
d['close'] = pd.to_numeric(d['CLOSING TOTAL_H'], errors='coerce')
d['actual'] = pd.to_numeric(d['PTS_H'], errors='coerce') + pd.to_numeric(d['PTS_R'], errors='coerce')
d = d.dropna(subset=['date', 'close', 'actual'])
d = d[d['close'].between(150, 300)].copy()
d['season'] = d['lbl'].str.extract(r'(\d{4})')[0].astype(int)
d['days_left'] = (d.groupby('lbl')['date'].transform('max') - d['date']).dt.days
d['ds'] = d.date.dt.strftime('%Y-%m-%d')
d['h'], d['r'] = d['TEAM_H'].astype(str), d['TEAM_R'].astype(str)
d['dev'] = d.actual - d.close
print(f"all regular-season games with a close and a result: {len(d)}")

cw = pd.read_csv('crewshock_walkforward_bets.csv')
cw['ds'] = pd.to_datetime(cw.date).dt.strftime('%Y-%m-%d')
cwk = set(zip(cw.ds, cw.TEAM_H.astype(str), cw.TEAM_R.astype(str)))
d['is_cw'] = [tuple(x) in cwk for x in zip(d.ds, d.h, d.r)]
d['is_f7'] = d.days_left <= 7
print(f"  crewshock games matched: {int(d.is_cw.sum())} (csv has {len(cw)})")
print(f"  final7 games:            {int(d.is_f7.sum())}")

XS = np.arange(-12, 12.1, 1.5)
SIG = T.SIGMA_REF


def curve(mask, name, delta):
    sub = d[mask]
    base = d
    print(f"\n{'='*86}\n{name}   n={len(sub)}   (delta assumed {delta:+.3f} pts)\n{'='*86}")
    print(f"  {'x = strike-close':>17}{'P(>x|sig)':>11}{'P(>x|all)':>11}"
          f"{'EDGE pp':>9}{'se':>7}{'model pp':>10}{'edge/model':>11}")
    rows = []
    for x in XS:
        hs = (sub.dev > x).mean()
        ha = (base.dev > x).mean()
        se = np.sqrt(hs * (1 - hs) / len(sub) + ha * (1 - ha) / len(base))
        # location-shift model: Phi((x-delta)/sig) differenced against Phi(x/sig)
        mdl = (1 - norm.cdf((x - delta) / SIG)) - (1 - norm.cdf(x / SIG))
        rows.append(dict(x=x, edge=hs - ha, se=se, model=mdl))
        rat = (hs - ha) / mdl if abs(mdl) > 1e-6 else np.nan
        print(f"  {x:>+17.1f}{100*hs:>10.2f}%{100*ha:>10.2f}%"
              f"{100*(hs-ha):>+8.2f}{100*se:>7.2f}{100*mdl:>+9.2f}{rat:>11.2f}")
    R = pd.DataFrame(rows)
    core = R[R.x.abs() <= 1.5]
    far = R[R.x.abs() >= 6]
    print(f"\n  mean EDGE   |x| <= 1.5 : {100*core.edge.mean():+.2f}pp   "
          f"(model says {100*core.model.mean():+.2f}pp)")
    print(f"  mean EDGE   |x| >= 6   : {100*far.edge.mean():+.2f}pp   "
          f"(model says {100*far.model.mean():+.2f}pp)")
    print(f"  edge RETENTION at |x|>=6: "
          f"{100*far.edge.mean()/core.edge.mean() if core.edge.mean() else float('nan'):.0f}% "
          f"of its at-the-line value;  model predicts "
          f"{100*far.model.mean()/core.model.mean():.0f}%")
    return R


r_cw = curve(d.is_cw, 'CREWSHOCK  (all 8 seasons)', T.delta_points(0.5421))
r_f7 = curve(d.is_f7, 'FINAL7  (all 8 seasons)', T.delta_points(0.5529))

print(f"\n{'='*86}\nWHAT THIS MEANS\n{'='*86}")
print("  If EDGE is flat in x, the venues really are interchangeable and rung")
print("  choice is free. If EDGE peaks near x=0 and decays faster than the")
print("  location-shift model, then the sportsbook sells the ONE bet the")
print("  backtest measured, and Kalshi's extra rungs are bets nobody tested.")
