"""t-stats on the taker P&L and hit rate, with the SE that the design requires.

THE P&L t-STAT AND THE HIT-RATE z-STAT ARE THE SAME NUMBER. This is not a
shortcut, it is algebra, and it is worth stating because printing them as two
columns would imply two tests where there is one.

At flat stake and a constant price c, one contract pays (1-c) on a win and -c
on a loss. So per-bet P&L is a two-point variable whose outcomes differ by
exactly 1:

    mean = h(1-c) - (1-h)c = h - c
    var  = h(1-h)(1-c+c)^2 = h(1-h)
    t    = (h - c) / sqrt(h(1-h)/n)

which is exactly the one-sample proportion statistic for H0: h = c. The same
holds for the -110 book with the null at 0.5238 -- the 190.91 scale factor
cancels out of the ratio. The two tests differ ONLY if the stake or the price
varies bet to bet, and MAX_CONTRACTS_GAME = 1 with a constant c, so here they
do not.

WHICH NULL. H0: h = c is the economic null -- zero profit after cost. H0:
h = 0.5 is a different and much weaker question (is there any directional
signal at all), and a rule can pass it while losing money. Both are shown;
only the first one pays.

=============================================================================
THE SE IS DATE-CLUSTERED, AND THAT IS THE POINT OF THIS FILE
=============================================================================
The iid binomial SE is WRONG HERE, and wrong in the optimistic direction.
These rules bet OVER on many games on the SAME NIGHT, and the thing that
makes a total go over -- pace, officiating, shooting variance league-wide --
is partly common to every game played that night. Those bets are not n
independent draws.

final7 is the extreme case: it bets EVERY game in the window, so a 14-game
April slate is 14 bets on one night sharing one league-wide shock.

So the standard error is clustered on GAME DATE (CR1):

    se = sqrt( G/(G-1) * sum_g S_g^2 ) / n,     S_g = sum of demeaned pnl in g

and the design effect (se_clustered/se_iid)^2 is reported, which converts
directly into an effective sample size n/deff. This follows the standing
position from the SCA work that daily-HAC/daily-clustered is the right SE
when observations share a day.

NOTHING HERE FIXES SELECTION. Every rule was found in this data. CrewShock's
0.5421 is a holdout, final7's window was chosen by LOSO on the same seasons
it is scored on. A t-stat computed on discovery data is an upper bound on the
evidence, not a test, and the efficiency-simulation result in this repo is the
reason to say so out loud: an efficient market throws off a "significant"
season-level finding in more than 75% of seasons.
"""
import sys
import numpy as np, pandas as pd
from scipy import stats
sys.path.insert(0, '.')
sys.path.insert(0, '/mnt/d/Kalshi/nba')
import taker_by_season as B          # reuses its data, signals and graded()
import nba_live_trader as T

C = B.C


def cluster_se(pnl, groups):
    """CR1 cluster-robust SE of a mean, clustered on `groups`."""
    x = np.asarray(pnl, float)
    n = len(x)
    dm = x - x.mean()
    S = pd.Series(dm).groupby(np.asarray(groups)).sum().values
    G = len(S)
    if G < 2:
        return np.nan, G
    return np.sqrt(G / (G - 1.0) * np.sum(S ** 2)) / n, G


def block(strat):
    g = B.graded(strat).copy()
    g['pnl'] = np.where(g.won, 1.0 - C, -C)
    return g


print("=" * 104)
print("t-STATS ON THE TAKER RECORD")
print("=" * 104)
print(f"  c = {C:.4f}   per-bet P&L = (1-c) on a win, -c on a loss")
print("  H0(economic): h = c, i.e. zero P&L.   H0(signal): h = 0.50.")
print("  The P&L t-stat EQUALS the hit-rate z-stat at flat stake and constant c")
print("  -- verified numerically below, not asserted.")
print()

rows = []
for strat in ('crewshock', 'final7', 'move', 'pacegap'):
    g = block(strat)
    n, h = len(g), g.won.mean()
    mean = g.pnl.mean()

    # --- the two statistics, computed INDEPENDENTLY to show they coincide
    se_iid_p = g.pnl.std(ddof=1) / np.sqrt(n)        # from the P&L series
    t_pnl = mean / se_iid_p
    se_hit = np.sqrt(h * (1 - h) / n)                # from the proportion
    z_hit = (h - C) / se_hit

    se_cl, G = cluster_se(g.pnl, g.ds)
    t_cl = mean / se_cl
    deff = (se_cl / se_iid_p) ** 2
    p_cl = 2 * stats.t.sf(abs(t_cl), G - 1)
    z50 = (h - 0.50) / np.sqrt(0.25 / n)

    rows.append(dict(strat=strat, n=n, G=G, h=h, mean=mean, t_pnl=t_pnl,
                     z_hit=z_hit, t_cl=t_cl, p_cl=p_cl, deff=deff, z50=z50,
                     prereg=T.STRATS[strat].get('prereg', False)))

print(f"  {'strategy':>10}{'bets':>6}{'nights':>8}{'hit%':>8}"
      f"{'P&L/ct':>9}{'t (iid)':>9}{'z hit':>8}{'t (clust)':>11}"
      f"{'p':>9}{'deff':>7}{'n_eff':>8}")
for r in rows:
    print(f"  {r['strat']:>10}{r['n']:>6}{r['G']:>8}{100*r['h']:>7.2f}%"
          f"{r['mean']:>+9.4f}{r['t_pnl']:>+9.2f}{r['z_hit']:>+8.2f}"
          f"{r['t_cl']:>+11.2f}{r['p_cl']:>9.3f}{r['deff']:>7.2f}"
          f"{r['n']/r['deff']:>8.0f}")

print()
print("  IDENTITY CHECK  max |t_pnl - z_hit| = "
      f"{max(abs(r['t_pnl']-r['z_hit']) for r in rows):.2e}   "
      "(same test, as derived above)")
print()
print(f"  {'strategy':>10}{'z vs 0.50':>12}{'p':>9}   interpretation")
for r in rows:
    p50 = 2 * stats.norm.sf(abs(r['z50']))
    both = ("beats cost" if r['p_cl'] < 0.05 else
            "signal but not cost" if p50 < 0.05 else "neither")
    print(f"  {r['strat']:>10}{r['z50']:>+12.2f}{p50:>9.3f}   {both}")

print()
print("=" * 104)
print("BY SEASON -- date-clustered t on the P&L")
print("=" * 104)
print(f"  {'strategy':>10}" + ''.join(f"{s:>9}" for s in range(2017, 2026))
      + f"{'ALL':>9}")
for strat in ('crewshock', 'final7', 'move', 'pacegap'):
    g = block(strat)
    line = f"  {strat:>10}"
    for s in range(2017, 2026):
        x = g[g.season == s]
        if len(x) < 2:
            line += f"{'--':>9}"; continue
        se, G = cluster_se(x.pnl, x.ds)
        line += f"{x.pnl.mean()/se:>+9.2f}" if se and np.isfinite(se) else f"{'--':>9}"
    se, G = cluster_se(g.pnl, g.ds)
    line += f"{g.pnl.mean()/se:>+9.2f}"
    print(line)
nsig = 0; ntot = 0
for strat in ('crewshock', 'final7', 'move', 'pacegap'):
    g = block(strat)
    for s in g.season.unique():
        x = g[g.season == s]
        se, G = cluster_se(x.pnl, x.ds)
        if se and np.isfinite(se) and G > 2:
            ntot += 1
            nsig += abs(x.pnl.mean() / se) > stats.t.isf(0.025, G - 1)
print(f"\n  season-strategy cells significant at 5%: {nsig} of {ntot} "
      f"({100*nsig/ntot:.0f}%) -- expected 5% under the null")

print()
print("=" * 104)
print("MULTIPLE TESTING on the four headline tests")
print("=" * 104)
ps = sorted((r['p_cl'], r['strat']) for r in rows)
m = len(ps)
print(f"  {'strategy':>10}{'p':>9}{'Bonferroni':>12}{'BH q':>9}  survives BH 5%?")
for i, (p, s) in enumerate(ps, 1):
    bh = p * m / i
    print(f"  {s:>10}{p:>9.3f}{min(1,p*m):>12.3f}{min(1,bh):>9.3f}"
          f"  {'yes' if bh < 0.05 else 'no'}")
print()
print("  REGISTERED vs DISCRETIONARY: " + ", ".join(
    f"{r['strat']}={'prereg' if r['prereg'] else 'DISCRETIONARY'}" for r in rows))
print("  final7 is the only one that was not preregistered, and its window was")
print("  selected by LOSO on these same seasons -- so its t is the one least")
print("  entitled to be read as a test.")
