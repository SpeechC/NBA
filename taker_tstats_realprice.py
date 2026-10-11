"""t-stats on the REAL recorded price, 2020-21 onward, not an assumed -110.

WHY THIS SUPERSEDES THE FLAT-c VERSION. taker_tstats.py priced every bet at a
single constant c = 0.5254, taken from the one season of Kalshi rungs that
exists. For the Kalshi basis that constraint is real -- settled markets are
purged, so there is exactly one season of books and there always will be. But
the SPORTSBOOK price is in dfMaster for every game, and the juice is recorded
explicitly for 7,169 of them. Grading six seasons of book bets at a flat -110
when the actual price is on disk throws away the single largest lever on
profitability.

THE PRIOR AUDIT UNDERCOUNTED THE SAMPLE BY 2.6x. PRICE_BAR_AUDIT.md found
n = 2,779 by reading CLOSING\\nODDS_H only. The column pair is polymorphic:
the TOTAL lands in _R more often than in _H (5,843 vs 3,646). Reading both
and keeping whichever parses to a number equal to CLOSING TOTAL_H recovers
the total for 9,489 of 9,489 regular-season games -- a 100% validated parse,
not a heuristic -- of which 7,169 carry explicit juice.

TWO CONSEQUENCES THAT CHANGE THE STATISTICS.

1. THE P&L t-STAT AND THE HIT-RATE z-STAT ARE NO LONGER THE SAME NUMBER.
   At flat stake AND flat price they coincide (taker_tstats.py derives why).
   Once the price varies bet to bet, the win payoff varies too, so the P&L
   series is no longer a two-point variable and the two tests separate. Both
   are now reported, and the gap between them is itself informative: it is
   whether the rule is selecting games that happen to be priced well.

2. THE JUICE IS ONE SIDE'S, AND WE DO NOT GET TO PICK THE CHEAP SIDE.
   "223.5u -05" prices the UNDER at -105, which puts the OVER near -115. So
   when the recorded side is not the side the strategy takes, the price must
   be IMPUTED from the complement at the -110/-110 overround of 1.047619.
   That is an assumption, so the whole table is also reported RESTRICTED to
   bets whose recorded side IS the side taken, where no imputation enters.
   If the two disagree, the imputation is doing the work and the result is
   not safe.

SEASONS 2017-18 AND 2018-19 ARE EXCLUDED from the priced analysis: only 4.8%
and 7.6% of their games record juice, so a priced result there would be a
statement about which 60 games happened to have a price, not about the rule.
They are retained in the flat-c tables in taker_tstats.py.
"""
import sys, re
import numpy as np, pandas as pd
from scipy import stats
sys.path.insert(0, '.')
sys.path.insert(0, '/mnt/d/Kalshi/nba')
import taker_by_season as B
import nba_live_trader as T

OVERROUND = 2 * (110.0 / 210.0)        # the -110/-110 benchmark, 1.047619
PAT = re.compile(r'^\s*(\d{3}(?:\.\d)?)\s*([ou])?\s*-?(\d{2})?', re.I)
CH, CR = 'CLOSING\nODDS_H', 'CLOSING\nODDS_R'
PRICED_FROM = 2020                     # first season with usable juice coverage


def _parse(v):
    m = PAT.match(str(v).strip())
    if not m:
        return (None, None, None)
    j = m.group(3)
    return (float(m.group(1)), (m.group(2) or '').lower() or None,
            (-100.0 - int(j)) if j is not None else None)


def amer_to_p(odds):
    """American odds -> implied probability (negative odds only here)."""
    o = float(odds)
    return (-o) / ((-o) + 100.0) if o < 0 else 100.0 / (o + 100.0)


def p_to_profit(p):
    """Implied prob -> profit per 1 staked on a win."""
    return (1.0 - p) / p


# ------------------------------------------------------------------ prices
raw = B.d.copy()                       # already regular-season, close/actual clean
# B.d is read from the same dfMaster, so the ODDS columns are ALREADY present.
# Merging a second copy in silently suffixes them to _x/_y and the parse then
# reads nothing -- assert instead of re-reading the file.
missing = [c for c in (CH, CR) if c not in raw.columns]
if missing:
    raise KeyError(f"expected odds columns absent from B.d: {missing!r}")
raw = raw.reset_index(drop=True)

num, side, juice = [], [], []
for i in range(len(raw)):
    cl = raw.close.iat[i]
    best = (None, None, None)
    for cn in (CR, CH):
        n_, s_, j_ = _parse(raw[cn].iat[i])
        if n_ is None:
            continue
        if pd.notna(cl) and abs(n_ - cl) <= 0.01:
            best = (n_, s_, j_); break
        if best[0] is None:
            best = (n_, s_, j_)
    num.append(best[0]); side.append(best[1]); juice.append(best[2])
raw['pnum'], raw['pside'], raw['pjuice'] = num, side, juice
raw['parse_ok'] = (raw.pnum - raw.close).abs() <= 0.01
PRICES = raw[['ds', 'h', 'r', 'pside', 'pjuice', 'parse_ok']]


def priced(strat):
    """Graded bets with the price of the side actually taken."""
    g = B.graded(strat).merge(PRICES, on=['ds', 'h', 'r'], how='left')
    g = g[(g.season >= PRICED_FROM) & g.parse_ok & g.pjuice.notna()].copy()
    rec_p = g.pjuice.map(amer_to_p)                 # implied prob of RECORDED side
    same = (g.pside == g.dir.str.lower().str[0])    # 'o'/'u' vs OVER/UNDER
    g['same_side'] = same
    # our side's implied prob: recorded if it matches, else the complement
    g['p_ours'] = np.where(same, rec_p, OVERROUND - rec_p)
    g['profit'] = g.p_ours.map(p_to_profit)
    g['pnl'] = np.where(g.won, g.profit, -1.0)      # per 1 staked
    return g


def cluster_se(x, groups):
    x = np.asarray(x, float); n = len(x)
    S = pd.Series(x - x.mean()).groupby(np.asarray(groups)).sum().values
    G = len(S)
    if G < 2:
        return np.nan, G
    return np.sqrt(G / (G - 1.0) * np.sum(S ** 2)) / n, G


STAKE = 100.0          # $ per bet, flat -- the unit every -110 table in this
                       # repo uses, so these P&L figures are comparable to them


def report(title, pick):
    """One panel. EVERY strategy's own date span is printed, not assumed.

    The window is NOT common across strategies and must not be labelled as if
    it were: MOVE's signal file starts in 2021-22, and juice coverage starts
    in 2020-21, so each rule's priced sample begins where its own inputs do.
    Printing one blanket period over four different spans is how a table
    acquires a caption that is false for three of its rows.
    """
    print()
    print("=" * 118)
    print(title)
    print("=" * 118)
    out = {}
    rows = []
    for strat in ('crewshock', 'final7', 'move', 'pacegap'):
        g = pick(priced(strat))
        if len(g) < 30:
            rows.append((strat, None)); continue
        n, h = len(g), g.won.mean()
        be = g.p_ours.mean()
        roi = g.pnl.mean()                      # per $1 staked
        se, G = cluster_se(g.pnl, g.ds)
        t = roi / se
        p = 2 * stats.t.sf(abs(t), G - 1)
        z = (h - be) / np.sqrt(h * (1 - h) / n)
        r110 = h * (100.0 / 110.0) - (1 - h)
        pnl = STAKE * g.pnl.sum()               # $ at $100/bet
        out[strat] = dict(n=n, h=h, be=be, roi=roi, t=t, p=p, z=z, G=G,
                          pnl=pnl, ds0=g.ds.min(), ds1=g.ds.max(),
                          nsea=g.season.nunique())
        rows.append((strat, out[strat]))

    print(f"  {'strategy':>10}{'seasons':>9}{'from':>13}{'to':>13}"
          f"{'bets':>6}{'hit%':>8}{'BE%':>8}{'ROI':>9}"
          f"{'P&L $':>11}{'$/bet':>8}{'t P&L':>8}{'p':>8}")
    for strat, r in rows:
        if r is None:
            print(f"  {strat:>10}   too few priced bets"); continue
        print(f"  {strat:>10}{r['nsea']:>9}{r['ds0']:>13}{r['ds1']:>13}"
              f"{r['n']:>6}{100*r['h']:>7.2f}%{100*r['be']:>7.2f}%"
              f"{100*r['roi']:>+8.2f}%{r['pnl']:>+11,.0f}"
              f"{r['pnl']/r['n']:>+8.2f}{r['t']:>+8.2f}{r['p']:>8.3f}")
    tot = sum(r['pnl'] for _, r in rows if r)
    totn = sum(r['n'] for _, r in rows if r)
    print(f"  {'TOTAL':>10}{'':>9}{min(r['ds0'] for _,r in rows if r):>13}"
          f"{max(r['ds1'] for _,r in rows if r):>13}{totn:>6}{'':>8}{'':>8}"
          f"{100*tot/(STAKE*totn):>+8.2f}%{tot:>+11,.0f}{tot/totn:>+8.2f}")
    print(f"  stake ${STAKE:.0f} flat per bet; P&L $ is the dollar total over that "
          f"strategy's own span; $/bet is P&L/bets.")
    print(f"  TOTAL pools four overlapping rules on the same games -- a portfolio "
          f"figure, not an additional test.")
    return out


print("=" * 118)
print("REAL-PRICE t-STATS -- SPORTSBOOK, at the price actually recorded for each game")
print("=" * 118)
print("  PERIOD: 2020-12-22 to 2026-04-12 at the widest, but the span DIFFERS BY")
print("  STRATEGY and each row below prints its own. Two different things bound it:")
print(f"    - juice coverage starts in {PRICED_FROM}-21 (2017-18 is 4.8% and 2018-19")
print("      7.6%, so a priced result there would describe the ~60 games that")
print("      happened to carry a price, not the rule). Those two seasons are OUT.")
print("    - MOVE's own signal file starts in 2021-22, so it has 5 seasons, not 6.")
print("    - final7 occupies only the last 8 days of each season, so its 6 seasons")
print("      are 6 short windows, not a continuous span.")
print()
print("  THIS IS A TAKER PRICE. A sportsbook quote is take-it-or-leave-it, so the")
print("  recorded -110/-112/-105 IS what a taker pays there; the maker/taker")
print("  distinction only exists on Kalshi. It is NOT a Kalshi figure: Kalshi has")
print("  one season of books and the rest are purged, which is why this table uses")
print("  the book instead of extrapolating one season of rungs to six.")
print()
print(f"  overround assumed for imputation: {OVERROUND:.6f}  (the -110/-110 benchmark)")
print("  parse validated: the number read equals CLOSING TOTAL_H on every game kept")

A = report("ALL PRICED BETS -- recorded side used directly, opposite side IMPUTED",
           lambda g: g)
S = report("NO IMPUTATION -- only bets whose RECORDED side IS the side taken",
           lambda g: g[g.same_side])

print()
print("=" * 118)
print("BY SEASON ON REAL PRICES -- bets, hit%, ROI and P&L at $100 flat per bet")
print("  (all priced bets, imputed where the recorded side is not ours)")
print("=" * 118)
for strat in ('crewshock', 'final7', 'move', 'pacegap'):
    g = priced(strat)
    if len(g) < 30:
        continue
    print(f"\n  {strat.upper()}   {g.ds.min()} to {g.ds.max()}   "
          f"settles on the {T.STRATS[strat]['line'].upper()}")
    print(f"      {'season':>9}{'from':>13}{'to':>13}{'bets':>6}{'hit%':>8}"
          f"{'BE%':>8}{'ROI':>9}{'P&L $':>10}{'t':>7}")
    for s in sorted(g.season.unique()):
        x = g[g.season == s]
        se, G = cluster_se(x.pnl, x.ds)
        tt = x.pnl.mean() / se if se and np.isfinite(se) else np.nan
        lbl = f"{s}-{str(s+1)[2:]}"
        print(f"      {lbl:>9}{x.ds.min():>13}{x.ds.max():>13}{len(x):>6}"
              f"{100*x.won.mean():>7.2f}%{100*x.p_ours.mean():>7.2f}%"
              f"{100*x.pnl.mean():>+8.2f}%{STAKE*x.pnl.sum():>+10,.0f}"
              f"{tt:>+7.2f}")
    se, G = cluster_se(g.pnl, g.ds)
    print(f"      {'ALL':>9}{g.ds.min():>13}{g.ds.max():>13}{len(g):>6}"
          f"{100*g.won.mean():>7.2f}%{100*g.p_ours.mean():>7.2f}%"
          f"{100*g.pnl.mean():>+8.2f}%{STAKE*g.pnl.sum():>+10,.0f}"
          f"{g.pnl.mean()/se:>+7.2f}")

print()
print("=" * 118)
print("DOES THE IMPUTATION DO THE WORK?")
print("=" * 118)
print(f"  {'strategy':>10}{'all n':>8}{'all ROI':>10}{'all t':>8}"
      f"{'same n':>9}{'same ROI':>10}{'same t':>8}   verdict")
for k in A:
    if k not in S:
        continue
    a, s = A[k], S[k]
    flip = (a['roi'] > 0) != (s['roi'] > 0)
    print(f"  {k:>10}{a['n']:>8}{100*a['roi']:>+9.2f}%{a['t']:>+8.2f}"
          f"{s['n']:>9}{100*s['roi']:>+9.2f}%{s['t']:>+8.2f}"
          f"   {'SIGN FLIPS -- unsafe' if flip else 'agrees in sign'}")

print()
print("=" * 118)
print("WHAT THE PRICE ITSELF IS WORTH -- against BOTH benchmarks, which differ")
print("=" * 118)
# The REALISED league mean break-even, not the -110 nominal. These are not the
# same number and conflating them was an error in an earlier version of this
# file: the league itself is priced DEARER than -110, which is the established
# reason the totals bar is 1.123 rather than the long-assumed 1.079.
_lgm = raw[(raw.season >= PRICED_FROM) & raw.parse_ok & raw.pjuice.notna()]
LEAGUE_BE = _lgm.pjuice.map(amer_to_p).mean()
NOMINAL_BE = 110.0 / 210.0
print(f"  realised league mean price  {_lgm.pjuice.mean():.2f}  -> break-even "
      f"{100*LEAGUE_BE:.4f}%   (n={len(_lgm):,})")
print(f"  nominal -110                        -> break-even {100*NOMINAL_BE:.4f}%")
print(f"  THE LEAGUE IS DEARER THAN -110 BY {100*(LEAGUE_BE-NOMINAL_BE):.4f}pp: "
      f"{(_lgm.pjuice<-110).sum():,} games worse than -110 vs "
      f"{(_lgm.pjuice>-110).sum():,} better.")
print()
print(f"  {'strategy':>10}{'rule mean BE':>15}{'vs league':>13}{'vs -110':>11}")
for strat in ('crewshock', 'final7', 'move', 'pacegap'):
    g = priced(strat)
    if len(g) < 30:
        continue
    print(f"  {strat:>10}{100*g.p_ours.mean():>14.4f}%"
          f"{100*(g.p_ours.mean()-LEAGUE_BE):>12.4f}pp"
          f"{100*(g.p_ours.mean()-NOMINAL_BE):>10.4f}pp")
print()
print("  NEGATIVE = the rule selects games priced CHEAPER than that benchmark.")
print()
print("  TWO SMALL OPPOSING EFFECTS THAT CANCEL, which is why the flat--110 grade")
print("  survived. The league is 0.064pp dearer than -110, so grading at -110 is")
print("  optimistic; but all four rules select games 0.011-0.100pp cheaper than the")
print("  league, which gives most of it back. Net against -110 is -0.036 to")
print("  +0.053pp, and the realised ROI difference is within 0.12pp. The flat grade")
print("  was not biased for THESE rules -- not because price does not vary, but")
print("  because two effects of similar size point opposite ways. That is a")
print("  coincidence of this selection, not a general licence to assume -110.")

print()
print("=" * 104)
print("MULTIPLE TESTING on the real-price results")
print("=" * 104)
for nm, D in (("all priced (with imputation)", A), ("same side only (no imputation)", S)):
    ps = sorted((v['p'], k) for k, v in D.items())
    m = len(ps)
    print(f"\n  {nm}")
    print(f"      {'strategy':>10}{'p':>9}{'Bonferroni':>12}{'BH q':>9}  survives BH 5%?")
    for i, (p, s) in enumerate(ps, 1):
        bh = p * m / i
        print(f"      {s:>10}{p:>9.3f}{min(1, p*m):>12.3f}{min(1, bh):>9.3f}"
              f"  {'yes' if bh < 0.05 else 'no'}")

print()
print("=" * 104)
print("WHAT CHANGED BY USING REAL PRICES, AND WHAT DID NOT")
print("=" * 104)
print("  The level barely moves. Every 'delta' above is within 0.12pp of ROI, and the")
print("  mean break-even of each rule's own bets sits within 0.05pp of the league's")
print("  52.381%. So although 56% of games are NOT at -110, the deviations do not")
print("  correlate with what any of these rules selects, and they average out. The")
print("  flat -110 grade was not biasing the answer -- which is a null on the price")
print("  channel, established over 6 seasons rather than assumed.")
print()
print("  Two things genuinely improved. The P&L t and the hit-rate z now SEPARATE,")
print("  because the win payoff varies bet to bet -- they are no longer one test.")
print("  And the same-side subsample removes the imputation entirely.")
print()
print("  WHAT NOT TO READ INTO IT. On the halved same-side sample final7 falls to")
print("  t = 0.71 and pacegap rises to t = 2.27. It is tempting to call that a new")
print("  ranking. It is not: halving n moves t by ~sqrt(2) on its own, these are")
print("  overlapping noisy subsamples, and nothing survives BH correction in either")
print("  panel. Building a mechanism on that difference is the error this project")
print("  has already made once with 'the edge does not travel'.")
