"""The min-GP split applied to ALL FOUR strategies, not just PaceGap.

WHY. pacegap_early_season.py tested min GP < 20 vs >= 20 on PaceGap alone and
the result (p 0.015) was then used to suggest holding off at the start of the
season. That is one strategy's result standing in for a four-strategy
decision, and the other three were never tested.

THE MECHANISM DOES NOT PREDICT THE SAME THING FOR ALL FOUR, and this matters
more than the p-values, because it decides which cells are a TEST and which
are a fishing expedition:

  pacegap   PREDICTED. build_states() carries prior-season pace/efficiency at
            CARRY = 0.42 and updates it from current-season games. Its state
            is literally a function of GP.
  move      PREDICTED. f_pace/f_oeff/f_deff are rolling windows grouped by
            ["season","team"], so they RESET each season. It already carries its
            own scope rule, MIN_PRIOR = 10, so its early cell can only ever
            be GP 10-19 -- the first 10 are gated out by construction.
  crewshock NOT PREDICTED. Its input is officials' foul-rate history pooled
            across 8 seasons and 9,489 games. An official's profile barely
            moves over 20 games of one season, so there is no mechanical
            reason for a GP effect. Any result here is a post-hoc subgroup.
  final7    STRUCTURALLY IMMUNE. It bets the last 8 days of a season, so
            every bet has min GP in the high 70s. The split cannot apply.

So this is ONE mechanism-motivated test (pacegap), one weaker version of the
same test (move, already partly gated), one post-hoc look (crewshock), and
one cell that does not exist (final7). Reported that way rather than as four
equal tests, and Bonferroni/BH over the ones actually run.
"""
import sys
import numpy as np, pandas as pd
from scipy import stats
sys.path.insert(0, '.')
sys.path.insert(0, '/mnt/d/Kalshi/nba')
import taker_by_season as B
import taker_tstats_realprice as R
import nba_live_trader as T

C = B.C
CUT = 20

# ------------------------------------------------- point-in-time games played
d = B.d.copy().sort_values('date')
first = d.groupby('season')['date'].transform('min')
d['day_in_season'] = (d.date - first).dt.days
cur, nh, na = {}, [], []
for r in d.itertuples():
    c = cur.setdefault(r.season, {})
    nh.append(c.get(r.h, 0)); na.append(c.get(r.r, 0))
    c[r.h] = c.get(r.h, 0) + 1
    c[r.r] = c.get(r.r, 0) + 1
d['h_gp'], d['a_gp'] = nh, na
d['min_gp'] = np.minimum(d.h_gp, d.a_gp)
GP = d[['ds', 'h', 'r', 'min_gp', 'day_in_season']]

MECH = {'pacegap':   ('PREDICTED',  'build_states carries prior season at CARRY=0.42'),
        'move':       ('PREDICTED',  'rolling windows groupby(season,team); MIN_PRIOR=10 already gates GP<10'),
        'crewshock':  ('not predicted', 'officials pooled over 8 seasons; profile barely moves in 20 games'),
        'final7':     ('N/A',        'last 8 days of the season -> every bet has min GP ~75+')}

print("=" * 108)
print(f"THE min-GP SPLIT ON ALL FOUR STRATEGIES   (cut at min GP = {CUT})")
print("=" * 108)
print("  min GP = the FEWER of the two teams' games already played that season,")
print("           counted strictly before the game. 0 = a season opener.")
print()
print(f"  {'strategy':>10}{'mechanism':>16}   why")
for s in ('pacegap', 'move', 'crewshock', 'final7'):
    print(f"  {s:>10}{MECH[s][0]:>16}   {MECH[s][1]}")

print()
print("=" * 108)
print("WHAT min-GP RANGE EACH STRATEGY EVEN OCCUPIES")
print("=" * 108)
print(f"  {'strategy':>10}{'bets':>7}{'min':>6}{'p05':>6}{'median':>8}{'p95':>6}{'max':>6}"
      f"{'% below 20':>12}{'% at GP=0':>11}")
FR = {}
for s in ('crewshock', 'final7', 'move', 'pacegap'):
    g = R.priced(s).merge(GP, on=['ds', 'h', 'r'], how='left')
    FR[s] = g
    q = g.min_gp.quantile([.05, .5, .95])
    print(f"  {s:>10}{len(g):>7}{int(g.min_gp.min()):>6}{int(q[.05]):>6}"
          f"{int(q[.5]):>8}{int(q[.95]):>6}{int(g.min_gp.max()):>6}"
          f"{100*(g.min_gp < CUT).mean():>11.1f}%{100*(g.min_gp == 0).mean():>10.1f}%")

print()
print("=" * 108)
print(f"EARLY (min GP < {CUT}) vs LATE (min GP >= {CUT})   -- recorded price, 2020-21+")
print("=" * 108)
print(f"  {'strategy':>10}{'':>4}{'n':>6}{'nights':>8}{'hit%':>8}{'ROI':>9}{'t':>7}"
      f"    LATE-EARLY diff      t       p")
RES = {}
for s in ('crewshock', 'final7', 'move', 'pacegap'):
    g = FR[s]
    early, late = g[g.min_gp < CUT], g[g.min_gp >= CUT]
    if len(early) < 30 or len(late) < 30:
        print(f"  {s:>10}    SPLIT DOES NOT APPLY -- early n={len(early)}, late n={len(late)}")
        RES[s] = None
        continue
    out = []
    for lab, x in (('E', early), ('L', late)):
        se, G = R.cluster_se(x.pnl, x.ds)
        out.append((lab, len(x), G, x.won.mean(), x.pnl.mean(), x.pnl.mean()/se))
    see, _ = R.cluster_se(early.pnl, early.ds)
    sel, _ = R.cluster_se(late.pnl, late.ds)
    diff = late.pnl.mean() - early.pnl.mean()
    sed = np.sqrt(see**2 + sel**2)
    tt = diff / sed
    pp = 2*stats.norm.sf(abs(tt))
    RES[s] = dict(diff=diff, t=tt, p=pp, ne=len(early), nl=len(late))
    for i, (lab, n, G, h, m, t) in enumerate(out):
        tail = (f"    {100*diff:>+13.2f}%{tt:>+8.2f}{pp:>8.3f}" if i == 0 else "")
        print(f"  {s:>10}{lab:>4}{n:>6}{G:>8}{100*h:>7.2f}%{100*m:>+8.2f}%{t:>+7.2f}{tail}")

print()
print("=" * 108)
print("MULTIPLE TESTING over the splits actually run")
print("=" * 108)
run = {k: v for k, v in RES.items() if v}
ps = sorted((v['p'], k) for k, v in run.items())
m = len(ps)
print(f"  {m} splits applicable (final7 excluded: the cell does not exist)")
print(f"      {'strategy':>10}{'p':>9}{'Bonferroni':>12}{'BH q':>9}  survives BH 5%?")
for i, (p, s) in enumerate(ps, 1):
    bh = p * m / i
    print(f"      {s:>10}{p:>9.3f}{min(1, p*m):>12.3f}{min(1, bh):>9.3f}"
          f"  {'yes' if bh < 0.05 else 'no'}")

print()
print("=" * 108)
print("VERDICT -- which strategies a GP gate would apply to")
print("=" * 108)
for s in ('pacegap', 'move', 'crewshock', 'final7'):
    v = RES.get(s)
    mech = MECH[s][0]
    if v is None:
        print(f"  {s:>10}  NO GATE. {MECH[s][1]}.")
        continue
    sig = 'significant' if v['p'] < 0.05 else 'not significant'
    print(f"  {s:>10}  mechanism {mech}; diff {100*v['diff']:+.2f}% "
          f"p {v['p']:.3f} ({sig}); early n={v['ne']}")
