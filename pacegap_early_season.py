"""Does PaceGap's edge exist in the FIRST DAYS of a season? The opening-night gate.

WHY THIS DECIDES IT. PaceGap is the only rule that can fire on 2026-10-20:
CrewShock and final7 are blocked by the BigDataBall hard stop in phase_late,
and MOVE is out of scope until both teams have 10 prior games (2026-11-09).
So "should we trade opening night" is entirely a question about PaceGap.

And opening night is NOT a typical PaceGap game. build_states() carries the
prior season's pace/efficiency state forward at CARRY = 0.42 and then has
ZERO current-season games to update it with. Every other night of the season
has at least some. If PaceGap's 1,452-bet record is built on games with weeks
of current-season state behind them, then opening night is out of sample on
the one dimension that matters most, and the pooled ROI does not license it.

THE TEST. Split PaceGap's own realised bets by how many games the two teams
had already played THAT SEASON, and by calendar days since each season's
first game. If the early cells look like the rest, the pooled record extends
to opening night. If they are worse, or too thin to tell, it does not.

Priced on the recorded sportsbook juice where available (2020-21 onward) and
also shown on the full 2017+ sample at flat -110, because restricting to
priced seasons costs a third of the bets and the early cells are small enough
that the extra sample matters more than the price precision here.
"""
import sys
import numpy as np, pandas as pd
from scipy import stats
sys.path.insert(0, '.')
sys.path.insert(0, '/mnt/d/Kalshi/nba')
import taker_by_season as B
import taker_tstats_realprice as R

C = B.C

# ------------------------------------------------- team games-played, PIT
d = B.d.copy()
d = d.sort_values('date')
played = {}
nh, na, dayn = [], [], []
first = d.groupby('season')['date'].transform('min')
d['day_in_season'] = (d.date - first).dt.days
cur = {}
for r in d.itertuples():
    key = r.season
    if key not in cur:
        cur[key] = {}
    c = cur[key]
    nh.append(c.get(r.h, 0)); na.append(c.get(r.r, 0))
    c[r.h] = c.get(r.h, 0) + 1
    c[r.r] = c.get(r.r, 0) + 1
d['h_gp'], d['a_gp'] = nh, na
d['min_gp'] = np.minimum(d.h_gp, d.a_gp)
GP = d[['ds', 'h', 'r', 'min_gp', 'day_in_season']]

g110 = B.graded('pacegap').merge(GP, on=['ds', 'h', 'r'], how='left')
g110['pnl'] = np.where(g110.won, 1.0 - C, -C)
gpr = R.priced('pacegap').merge(GP, on=['ds', 'h', 'r'], how='left')


def cell(x, div):
    """div = C for the flat-c frame (pnl is in contract dollars); 1.0 for the
    priced frame, whose pnl is already per $1 staked."""
    if len(x) == 0:
        return None
    se, G = R.cluster_se(x.pnl, x.ds)
    t = (x.pnl.mean() / se) if se and np.isfinite(se) else np.nan
    return dict(n=len(x), h=x.won.mean(), roi=x.pnl.mean() / div, t=t, G=G)


def panel(title, g, div, bands):
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)
    print(f"  {'window':>26}{'bets':>7}{'nights':>8}{'hit%':>8}{'ROI':>9}{'t':>8}")
    for lab, lo, hi in bands:
        x = g[(g.min_gp >= lo) & (g.min_gp <= hi)]
        c = cell(x, div)
        if c is None or c['n'] == 0:
            print(f"  {lab:>26}{0:>7}        -- no bets --")
            continue
        print(f"  {lab:>26}{c['n']:>7}{c['G']:>8}{100*c['h']:>7.2f}%"
              f"{100*c['roi']:>+8.2f}%{c['t']:>+8.2f}")
    c = cell(g, div)
    print(f"  {'ALL':>26}{c['n']:>7}{c['G']:>8}{100*c['h']:>7.2f}%"
          f"{100*c['roi']:>+8.2f}%{c['t']:>+8.2f}")


BANDS = [("min team GP = 0 (openers)", 0, 0),
         ("min GP 1-2", 1, 2),
         ("min GP 3-5", 3, 5),
         ("min GP 6-9", 6, 9),
         ("min GP 10-19", 10, 19),
         ("min GP 20+", 20, 999)]

print("=" * 100)
print("PACEGAP BY HOW MUCH CURRENT-SEASON STATE EXISTED")
print("=" * 100)
print("  min team GP = the FEWER of the two teams' games already played that")
print("  season, so 0 means at least one team is playing its season opener.")
print(f"  flat-c sample: 2017-18 onward, c = {C:.4f}")
print("  priced sample: 2020-21 onward, recorded juice")

panel("FLAT c -- full sample 2017-18 onward", g110, C, BANDS)
panel("RECORDED PRICE -- 2020-21 onward", gpr, 1.0, BANDS)

# -------------------------------------------- the pre-specifiable split
print()
print("=" * 100)
print("THE SPLIT THE MECHANISM IMPLIES: does PaceGap need current-season state?")
print("=" * 100)
print("  This is NOT one of six bands chosen after looking. build_states() carries")
print("  prior-season state at CARRY = 0.42 and updates it from current-season")
print("  games, so 'has the state been updated yet' is the one split the mechanism")
print("  names in advance. GP >= 20 vs GP < 20 is the coarse version of it.")
print()
for nm, g, div in (("flat c, 2017-18+", g110, C), ("recorded price, 2020-21+", gpr, 1.0)):
    early = g[g.min_gp < 20]; late = g[g.min_gp >= 20]
    ce, cl = cell(early, div), cell(late, div)
    print(f"  {nm}")
    for lab, c in (("EARLY  min GP < 20", ce), ("LATE   min GP >= 20", cl)):
        print(f"      {lab:>22}  n={c['n']:>4}  nights={c['G']:>3}  "
              f"hit={100*c['h']:>6.2f}%  ROI={100*c['roi']:>+7.2f}%  t={c['t']:>+5.2f}")
    # difference in mean pnl, clustered on night, unpaired
    se_e, _ = R.cluster_se(early.pnl, early.ds)
    se_l, _ = R.cluster_se(late.pnl, late.ds)
    diff = late.pnl.mean() - early.pnl.mean()
    sed = np.sqrt(se_e**2 + se_l**2)
    print(f"      {'LATE - EARLY':>22}  diff={100*diff/div:>+7.2f}%  "
          f"t={diff/sed:>+5.2f}  p={2*stats.norm.sf(abs(diff/sed)):.3f}")
    print()

# ---------------------------------------------- first N days of the season
print()
print("=" * 100)
print("THE FIRST TWO WEEKS, DAY BY DAY (flat c, full sample)")
print("=" * 100)
print(f"  {'day of season':>16}{'bets':>7}{'hit%':>8}{'ROI':>9}  cumulative")
cum = []
for dd in range(0, 15):
    x = g110[g110.day_in_season == dd]
    cum.append(x)
    cc = pd.concat(cum)
    if len(x) == 0:
        print(f"  {dd:>16}{0:>7}{'--':>8}{'--':>9}  "
              f"n={len(cc)} hit={100*cc.won.mean():.2f}% "
              f"ROI={100*cc.pnl.mean()/C:+.2f}%" if len(cc) else "")
        continue
    print(f"  {dd:>16}{len(x):>7}{100*x.won.mean():>7.2f}%"
          f"{100*x.pnl.mean()/C:>+8.2f}%  "
          f"n={len(cc)} hit={100*cc.won.mean():.2f}% "
          f"ROI={100*cc.pnl.mean()/C:+.2f}%")

print()
print("=" * 100)
print("THE DECISION NUMBERS FOR 2026-10-20")
print("=" * 100)
op = g110[g110.min_gp == 0]
e2 = g110[g110.day_in_season <= 13]
rest = g110[g110.day_in_season > 13]
for lab, x in (("season openers (min GP = 0)", op),
               ("first 14 days", e2),
               ("day 15 onward", rest)):
    if len(x) == 0:
        print(f"  {lab:>30}  no bets"); continue
    se, G = R.cluster_se(x.pnl, x.ds)
    h = x.won.mean()
    lo, hi = stats.beta.interval(0.95, x.won.sum() + .5, len(x) - x.won.sum() + .5)
    print(f"  {lab:>30}  n={len(x):>4}  hit={100*h:>6.2f}% "
          f"[{100*lo:.1f}%, {100*hi:.1f}%]  ROI={100*x.pnl.mean()/C:>+7.2f}%  "
          f"t={x.pnl.mean()/se:>+5.2f}")
print()
rate = len(op) / max((d.min_gp == 0).sum(), 1)
print(f"  PaceGap fires on {100*rate:.1f}% of opener games "
      f"({len(op)} bets from {(d.min_gp==0).sum()} such games).")
print(f"  2026-10-20 has 3 games -> expected signals = {3*rate:.2f}")
print(f"  at 1 contract and ~$0.52 outlay that is about "
      f"${3*rate*0.52:.2f} of risk.")
