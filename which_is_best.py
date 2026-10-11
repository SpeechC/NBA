"""Is any strategy identifiably the best? Night-level cluster bootstrap.

WHY THIS FILE EXISTS. "CrewShock is our best strategy" is in the project's
working memory, and tracing it finds two sources, neither of which is a
performance ranking:

  MONITOR_SEASON_PNL.md    lists CrewShock as section 1 of 4
  AMENDMENT_live_trading.md:188  "CrewShock is OVER-only and is unaffected
                                  -- it can arm first"

The second is an OPERATIONAL fact: CrewShock never takes the UNDER, so it did
not need the NO-side path proven before it could trade. That made it first to
arm, not best. Ordering in a document is not evidence either. And the same
doc already records that every interval except final7's includes zero.

So the ranking question has never actually been tested. A point estimate does
not answer it: four ROIs computed on overlapping games with wide CIs can be
ordered any number of ways, and reading off the largest is how a project
acquires a favourite. This asks the question directly.

METHOD. Resample NIGHTS with replacement -- the same clustering the t-stats
use, since bets on one night are one draw -- recompute all four ROIs on each
resample, and count how often each rule comes out on top. That yields
P(best), P(beats the others pairwise) and the rank distribution, all of which
account for the fact that the four rules bet overlapping games and their
errors are therefore correlated.

WHAT WOULD MAKE A RANKING REAL. P(best) near 1 for one rule. What follows
is nothing like that.

Prices are the recorded sportsbook juice, 2020-21 onward, per
taker_tstats_realprice.py. Resampling is on the UNION of nights, so a drawn
night contributes to whichever strategies actually bet it; final7 is thin by
construction (42 nights) and its interval is correspondingly wide, which is
information, not a defect.
"""
import sys
import numpy as np, pandas as pd
sys.path.insert(0, '.')
sys.path.insert(0, '/mnt/d/Kalshi/nba')
import taker_tstats_realprice as R

STRATS = ('crewshock', 'final7', 'move', 'pacegap')
B = 20000
rng = np.random.default_rng(20261011)

# pnl per $1 staked, keyed by night
D = {}
for s in STRATS:
    g = R.priced(s)
    D[s] = g.groupby('ds').pnl.agg(['sum', 'count'])

nights = sorted(set().union(*(set(v.index) for v in D.values())))
idx = {n: i for i, n in enumerate(nights)}
SUM = np.zeros((len(STRATS), len(nights)))
CNT = np.zeros((len(STRATS), len(nights)))
for a, s in enumerate(STRATS):
    for n, row in D[s].iterrows():
        SUM[a, idx[n]] = row['sum']
        CNT[a, idx[n]] = row['count']

obs = SUM.sum(1) / CNT.sum(1)

print("=" * 100)
print("IS ANY STRATEGY IDENTIFIABLY THE BEST?")
print("=" * 100)
print(f"  sportsbook recorded price, 2020-21 onward; {len(nights)} distinct nights; "
      f"{B:,} bootstrap resamples")
print(f"  resampling unit: the NIGHT (same clustering as the t-stats)")
print()
print(f"  {'strategy':>10}{'bets':>7}{'nights':>8}{'observed ROI':>14}")
for a, s in enumerate(STRATS):
    print(f"  {s:>10}{int(CNT[a].sum()):>7}{int((CNT[a]>0).sum()):>8}"
          f"{100*obs[a]:>13.2f}%")

draws = rng.integers(0, len(nights), size=(B, len(nights)))
ROI = np.empty((B, len(STRATS)))
for b in range(B):
    d = draws[b]
    num = SUM[:, d].sum(1)
    den = CNT[:, d].sum(1)
    ROI[b] = np.where(den > 0, num / np.maximum(den, 1), np.nan)

best = np.nanargmax(ROI, axis=1)
ranks = np.argsort(np.argsort(-ROI, axis=1), axis=1)      # 0 = best

print()
print("=" * 100)
print("P(this strategy has the highest TRUE ROI)")
print("=" * 100)
print(f"  {'strategy':>10}{'P(best)':>10}{'P(worst)':>10}{'P(ROI>0)':>11}"
      f"{'mean rank':>11}{'2.5%':>9}{'97.5%':>9}")
for a, s in enumerate(STRATS):
    lo, hi = np.nanpercentile(ROI[:, a], [2.5, 97.5])
    print(f"  {s:>10}{(best==a).mean():>10.3f}"
          f"{(ranks[:,a]==len(STRATS)-1).mean():>10.3f}"
          f"{(ROI[:,a]>0).mean():>11.3f}{ranks[:,a].mean()+1:>11.2f}"
          f"{100*lo:>8.2f}%{100*hi:>8.2f}%")

print()
print("=" * 100)
print("PAIRWISE  P(row's true ROI > column's)")
print("=" * 100)
print(f"  {'':>10}" + ''.join(f"{s:>12}" for s in STRATS))
for a, s in enumerate(STRATS):
    line = f"  {s:>10}"
    for b2, s2 in enumerate(STRATS):
        line += f"{'--':>12}" if a == b2 else f"{(ROI[:,a]>ROI[:,b2]).mean():>12.3f}"
    print(line)

print()
print("=" * 100)
print("THE DIFFERENCES THEMSELVES, with intervals")
print("=" * 100)
print(f"  {'pair':>24}{'observed diff':>15}{'2.5%':>10}{'97.5%':>10}  excludes 0?")
for a in range(len(STRATS)):
    for b2 in range(a + 1, len(STRATS)):
        d = ROI[:, a] - ROI[:, b2]
        lo, hi = np.nanpercentile(d, [2.5, 97.5])
        nm = f"{STRATS[a]} - {STRATS[b2]}"
        print(f"  {nm:>24}{100*(obs[a]-obs[b2]):>14.2f}%{100*lo:>9.2f}%"
              f"{100*hi:>9.2f}%  {'YES' if lo>0 or hi<0 else 'no'}")

print()
print("=" * 100)
print("VERDICT")
print("=" * 100)
pb = {s: (best == a).mean() for a, s in enumerate(STRATS)}
top = max(pb, key=pb.get)
nsig = sum(1 for a in range(len(STRATS)) for b2 in range(a+1, len(STRATS))
           if (lambda d: d[0] > 0 or d[1] < 0)(
               np.nanpercentile(ROI[:, a] - ROI[:, b2], [2.5, 97.5])))
print(f"  highest P(best) is {top} at {pb[top]:.3f}.")
print(f"  pairwise differences whose 95% interval excludes zero: {nsig} of 6.")
print()
print("  With four strategies P(best) = 0.25 is indifference, so final7's 0.64 is")
print("  NOT indifference -- the data do lean its way, and it would be wrong to")
print("  wave that off. But two things sit against reading it as the answer:")
print()
print("    1. NO pair separates. All 6 differences straddle zero, final7 - pacegap")
print("       at [-6.06%, +12.80%] and final7 - crewshock at [-7.48%, +12.41%]")
print("       reversed. P(best) ranks point estimates; it does not establish that")
print("       the gaps are real, and the gaps are not.")
print("    2. final7 is the rule LEAST entitled to the lead. It is the only")
print("       DISCRETIONARY one, its window was chosen by LOSO on these same")
print("       seasons, and it has 42 nights against 629-690 for the others -- the")
print("       widest interval in the table. The apparent leader is the one with")
print("       the weakest provenance, which is the signature of selection, not")
print("       of an edge.")
print()
print(f"  ON CREWSHOCK SPECIFICALLY: P(best) = {pb['crewshock']:.3f}, just BELOW the")
print("  0.25 indifference line, and P(crewshock > final7) = 0.29. So it is not")
print("  identifiably the best and never was tested to be. Its standing came from")
print("  AMENDMENT_live_trading.md:188 -- 'CrewShock is OVER-only ... it can arm")
print("  first' -- which is about which EXECUTION PATH was proven, not which rule")
print("  earns most, plus being section 1 of 4 in MONITOR_SEASON_PNL.md.")
print("  That operational fact is still true and still useful.")
print()
print("  THE DEFENSIBLE STATEMENT: all four have P(ROI>0) of 0.83-0.97 and none")
print("  is separable from the others. Treat them as one undifferentiated basket")
print("  of thin edges, not a ranked list with a favourite at the top.")
