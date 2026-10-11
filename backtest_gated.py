"""The GATED configuration backtested: PaceGap and MOVE at min GP >= 20.

THE CONFIGURATION THIS PRICES is what nba_live_trader now does:
    crewshock   every signal          (NOT gated -- its early cell pays +7.10%)
    final7      every signal          (NOT gated -- min GP is already ~75)
    pacegap     min GP >= 20 only     (GP_GATE_MIN = 20)
    move        min GP >= 20 only
min GP = the FEWER of the two teams' completed regular-season games this
season, strictly before the game. "After 20 games played" = GP >= 20, which is
what the code implements and what is priced here.

=============================================================================
READ THE GATED NUMBERS AS IN-SAMPLE. THEY ARE NOT A FORECAST.
=============================================================================
The GP >= 20 cut was chosen by inspecting THIS data. Of the two rules, the
threshold sweep showed the gap widening monotonically out to cut 35, so 20 was
picked as the least restrictive end of a supported range rather than as an
estimated cliff -- but it was still picked here. Correcting PaceGap's p 0.015
for the 8 cuts searched gives 0.12.

So the gated ROI is an upper bound on what the gate buys, and the UNGATED
column is the honest prior for 2026-27. Both are printed side by side, and the
difference between them is the quantity that has not been validated out of
sample. Nothing below is a reason to expect +8.69% next season.

What the gate IS defensible on: the excluded cell is not profitable at any cut
>= 20 (-4.4% to -2.2%) and only break-even below 15, so declining it forgoes
nothing demonstrable. That is an argument for the gate costing little, not for
the gated figure being achievable.

Priced on the recorded sportsbook juice 2020-21 onward (taker: a book quote is
take-it-or-leave-it). Flat-c on the full 2017-18 sample shown alongside.
"""
import sys
import numpy as np, pandas as pd
from scipy import stats
sys.path.insert(0, '.')
sys.path.insert(0, '/mnt/d/Kalshi/nba')
import taker_by_season as B
import taker_tstats_realprice as R
import gp_gate_all_strategies as G
import nba_live_trader as T

C = B.C
STAKE = 100.0
CUT = T.GP_GATE_MIN
GATED = set(T.GP_GATED)


def stats_for(x, div):
    if len(x) == 0:
        return None
    n, h = len(x), x.won.mean()
    se, Gn = R.cluster_se(x.pnl, x.ds)
    t = x.pnl.mean() / se if se and np.isfinite(se) else np.nan
    p = 2 * stats.t.sf(abs(t), Gn - 1) if np.isfinite(t) else np.nan
    lo, hi = stats.beta.interval(0.95, x.won.sum() + .5, n - x.won.sum() + .5)
    return dict(n=n, G=Gn, h=h, hlo=lo, hhi=hi, roi=x.pnl.mean() / div,
                pnl=STAKE * x.pnl.sum() / div, t=t, p=p,
                ds0=x.ds.min(), ds1=x.ds.max(), nsea=x.season.nunique())


def frames(div_priced=True):
    out = {}
    for s in ('crewshock', 'final7', 'move', 'pacegap'):
        g = G.FR[s] if div_priced else None
        if not div_priced:
            g = B.graded(s).copy()
            g['pnl'] = np.where(g.won, 1.0 - C, -C)
            g = g.merge(G.GP, on=['ds', 'h', 'r'], how='left')
        out[s] = g
    return out


def report(title, div_priced):
    div = 1.0 if div_priced else C
    F = frames(div_priced)
    print()
    print("=" * 122)
    print(title)
    print("=" * 122)
    print(f"  {'strategy':>10}{'gate':>10}{'sea':>5}{'from':>12}{'to':>12}"
          f"{'bets':>6}{'hit%':>8}{'95% CI on hit':>18}{'ROI':>9}"
          f"{'P&L $':>10}{'t':>7}{'p':>8}")
    tot_pnl = tot_n = 0
    res = {}
    for s in ('crewshock', 'final7', 'move', 'pacegap'):
        g = F[s]
        gated = s in GATED
        x = g[g.min_gp >= CUT] if gated else g
        c = stats_for(x, div)
        if c is None:
            print(f"  {s:>10}  no bets"); continue
        res[s] = c
        tot_pnl += c['pnl']; tot_n += c['n']
        lbl = f">=GP{CUT}" if gated else "none"
        print(f"  {s:>10}{lbl:>10}{c['nsea']:>5}{c['ds0']:>12}{c['ds1']:>12}"
              f"{c['n']:>6}{100*c['h']:>7.2f}%"
              f"{('[%.1f%%, %.1f%%]' % (100*c['hlo'], 100*c['hhi'])):>18}"
              f"{100*c['roi']:>+8.2f}%{c['pnl']:>+10,.0f}{c['t']:>+7.2f}"
              f"{c['p']:>8.3f}")
    print(f"  {'PORTFOLIO':>10}{'':>10}{'':>5}{'':>12}{'':>12}{tot_n:>6}{'':>8}"
          f"{'':>18}{100*tot_pnl/(STAKE*tot_n):>+8.2f}%{tot_pnl:>+10,.0f}")
    print(f"  PORTFOLIO pools overlapping rules on the same games -- not an extra test.")
    return res


PR = report("GATED CONFIGURATION -- recorded sportsbook price, 2020-21 onward", True)
FL = report("GATED CONFIGURATION -- flat c = %.4f, full sample 2017-18 onward" % C, False)

# ------------------------------------------------------- what the gate changed
print()
print("=" * 122)
print("WHAT THE GATE CHANGED  (recorded price) -- gated vs ungated, same rules")
print("=" * 122)
F = frames(True)
print(f"  {'strategy':>10}{'':>3}{'bets':>6}{'hit%':>8}{'ROI':>9}{'P&L $':>10}"
      f"{'t':>7}{'p':>8}   {'bets dropped':>13}{'their ROI':>11}{'their P&L':>11}")
for s in ('pacegap', 'move'):
    g = F[s]
    on, off = g[g.min_gp >= CUT], g[g.min_gp < CUT]
    a, b = stats_for(on, 1.0), stats_for(g, 1.0)
    d = stats_for(off, 1.0)
    for lab, c in (("ON ", a), ("OFF", b)):
        print(f"  {s:>10}{lab:>3}{c['n']:>6}{100*c['h']:>7.2f}%"
              f"{100*c['roi']:>+8.2f}%{c['pnl']:>+10,.0f}{c['t']:>+7.2f}{c['p']:>8.3f}"
              + (f"   {d['n']:>13}{100*d['roi']:>+10.2f}%{d['pnl']:>+11,.0f}"
                 if lab == "ON " else ""))
for s in ('crewshock', 'final7'):
    c = stats_for(F[s], 1.0)
    print(f"  {s:>10}{'--':>3}{c['n']:>6}{100*c['h']:>7.2f}%{100*c['roi']:>+8.2f}%"
          f"{c['pnl']:>+10,.0f}{c['t']:>+7.2f}{c['p']:>8.3f}   {'not gated':>13}")

# ------------------------------------------------------------------ by season
print()
print("=" * 122)
print("BY SEASON, GATED  (recorded price; pacegap/move restricted to min GP >= %d)" % CUT)
print("=" * 122)
for s in ('crewshock', 'final7', 'move', 'pacegap'):
    g = F[s]
    if s in GATED:
        g = g[g.min_gp >= CUT]
    print(f"\n  {s.upper()}   {'GATED' if s in GATED else 'ungated'}")
    print(f"      {'season':>9}{'from':>12}{'to':>12}{'bets':>6}{'hit%':>8}"
          f"{'ROI':>9}{'P&L $':>10}{'t':>7}{'p':>8}")
    for ss in sorted(g.season.unique()):
        x = g[g.season == ss]
        c = stats_for(x, 1.0)
        if c is None or c['n'] < 2:
            continue
        print(f"      {('%d-%s' % (ss, str(ss+1)[2:])):>9}{c['ds0']:>12}{c['ds1']:>12}"
              f"{c['n']:>6}{100*c['h']:>7.2f}%{100*c['roi']:>+8.2f}%"
              f"{c['pnl']:>+10,.0f}{c['t']:>+7.2f}{c['p']:>8.3f}")
    c = stats_for(g, 1.0)
    print(f"      {'ALL':>9}{c['ds0']:>12}{c['ds1']:>12}{c['n']:>6}"
          f"{100*c['h']:>7.2f}%{100*c['roi']:>+8.2f}%{c['pnl']:>+10,.0f}"
          f"{c['t']:>+7.2f}{c['p']:>8.3f}")

# ------------------------------------------------------- multiple testing
print()
print("=" * 122)
print("MULTIPLE TESTING on the four gated headline tests")
print("=" * 122)
ps = sorted((v['p'], k) for k, v in PR.items())
m = len(ps)
print(f"      {'strategy':>10}{'p':>9}{'Bonferroni':>12}{'BH q':>9}  survives BH 5%?")
for i, (p, s) in enumerate(ps, 1):
    bh = p * m / i
    print(f"      {s:>10}{p:>9.3f}{min(1, p*m):>12.3f}{min(1, bh):>9.3f}"
          f"  {'yes' if bh < 0.05 else 'no'}")
print()
print("  THE TWO SEARCHES MUST BE COUNTED TOGETHER, NOT SEPARATELY.")
print("  The table above corrects for testing 4 strategies. On top of that the GP")
print("  cut was swept over 8 values before 20 was chosen. Correcting for one and")
print("  then the other and calling each a pass is double-counting the budget:")
pg = PR['pacegap']['p']
for mm, lab in ((4,  "the 4 gated headline tests only"),
                (8,  "the 8 GP cuts for pacegap only"),
                (16, "2 mechanism-named strategies x 8 cuts"),
                (24, "3 applicable strategies x 8 cuts"),
                (32, "4 strategies x 8 cuts")):
    print(f"      m={mm:>2}  {lab:<42} -> {min(1, pg*mm):.3f}  "
          f"{'significant' if pg*mm < 0.05 else 'NOT significant'}")
print()
print("  PaceGap's gated p survives EITHER search alone and NEITHER jointly. The")
print("  honest reading is BORDERLINE, not significant: m=16 is the smallest")
print("  defensible joint space (the mechanism named pacegap and move in advance,")
print("  but the cut was searched in both) and it gives 0.058.")
print()
print("  An earlier version of this file printed the 8-cut correction on its own")
print("  and concluded 'significant'. That was wrong -- it spent the 4-test and")
print("  the 8-cut budget twice over.")
print()
print("  The gate is justified by the excluded cell being unprofitable, not by")
print("  any of these p-values. Treat the UNGATED column as the forecast for")
print("  2026-27.")
