"""P&L for the cohesion signal, at the UNCONDITIONAL rule the prereg implies.

Rule: bet the side with the higher cohesion. No threshold, no sizing, no
selection -- PREREG_cohesion Section 4 forbids concentrating the edge by a
post-hoc threshold search, so none is applied.

-110 both ways: a $100 win returns $90.91, a loss costs $100.
"""
import math, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
from cohesion import build, CTRL, ols_t

STAKE, WIN = 100.0, 100.0 / 1.1        # $90.91 at -110
BE = 1.1 / 2.1                          # 52.381% break-even


def pnl(g):
    """Bet home if C_diff>0 else away. Push when the game lands on the number."""
    side = np.sign(g.C_diff.values)                 # +1 home, -1 away
    res = np.sign(g.dev_s.values)                   # +1 home covered
    live = (side != 0) & (res != 0)
    w = int(((side == res) & live).sum())
    l = int(((side != res) & live).sum())
    p = int(len(g) - w - l)
    profit = w * WIN - l * STAKE
    staked = (w + l) * STAKE
    hit = w / (w + l) if (w + l) else np.nan
    return dict(n=len(g), bets=w + l, w=w, l=l, push=p, hit=hit,
                profit=profit, staked=staked,
                roi=profit / staked if staked else np.nan)


def line(lab, r):
    print(f"  {lab:<24}{r['bets']:>7,}{100*r['hit']:>8.2f}%"
          f"{r['profit']:>+12,.0f}{100*r['roi']:>+9.2f}%"
          f"{100*(r['hit']-BE):>+9.2f}pp")


d = build()
dev, ho = d[d.is_dev], d[~d.is_dev]

print("Rule: bet the side with higher prior-only lineup cohesion. $100/game, -110.")
print(f"Break-even {100*BE:.3f}%\n")
print(f"  {'period':<24}{'bets':>7}{'hit':>9}{'profit $':>12}{'ROI':>9}{'vs BE':>11}")
print("  " + "-" * 70)
line("DEVELOPMENT (5 seas)", pnl(dev))
print("  " + "-" * 70)
for s, g in ho.groupby("season"):
    line(f"holdout {s}", pnl(g))
r = pnl(ho)
line("HOLDOUT pooled", r)
print("  " + "-" * 70)
line("FULL SAMPLE", pnl(d))

# ---- the uncertainty that decides whether any of this means anything --------
n = r["bets"]
se = np.sqrt(0.25 / n)
print(f"\nIs the holdout result distinguishable from break-even?")
print(f"  holdout hit {100*r['hit']:.2f}%  n={n:,}  se={100*se:.2f}pp")
lo, hi = r["hit"] - 1.96 * se, r["hit"] + 1.96 * se
print(f"  95% CI  [{100*lo:.2f}%, {100*hi:.2f}%]   break-even {100*BE:.2f}%"
      f"   -> {'EXCLUDES' if lo > BE else 'INCLUDES'} break-even")
z = (r["hit"] - BE) / se
print(f"  z vs break-even = {z:+.2f}   one-sided p = "
      f"{1 - 0.5*(1+math.erf(z/np.sqrt(2))):.4f}")
print(f"  ROI 95% CI roughly [{100*((lo*(1+WIN/STAKE))-1):+.2f}%, "
      f"{100*((hi*(1+WIN/STAKE))-1):+.2f}%]")

# ---- the RESIDUALISED signal: what the regression coefficient actually says --
print("\n" + "="*72)
print("The naive sign rule is NOT what the finding claims. The coefficient is")
print("CONDITIONAL on controls, and corr(C_diff, sp_close) = -0.40, so betting")
print("the higher-cohesion side is largely betting favourites. The tradeable")
print("object is C_diff RESIDUALISED on the controls, fitted on development")
print("and applied to the holdout.")
print("="*72)
Ztr = np.column_stack([np.ones(len(dev))] + [dev[c].values for c in CTRL])
ok = np.all(np.isfinite(Ztr), axis=1) & np.isfinite(dev.C_diff.values)
g, *_ = np.linalg.lstsq(Ztr[ok], dev.C_diff.values[ok], rcond=None)
for lab, sub in (("DEVELOPMENT", dev), ("HOLDOUT", ho)):
    Z = np.column_stack([np.ones(len(sub))] + [sub[c].values for c in CTRL])
    r = sub.copy()
    r["C_diff"] = sub.C_diff.values - Z @ g          # residualised signal
    print(f"  {lab:<24}{'bets':>7}{'hit':>9}{'profit $':>12}{'ROI':>9}{'vs BE':>11}")
    line(f"  resid rule {lab}", pnl(r))
    if lab == "HOLDOUT":
        rr = pnl(r); nn = rr["bets"]; sse = np.sqrt(0.25/nn)
        zz = (rr["hit"] - BE)/sse
        print(f"    95% CI [{100*(rr['hit']-1.96*sse):.2f}%, "
              f"{100*(rr['hit']+1.96*sse):.2f}%]  vs BE {100*BE:.2f}%  z={zz:+.2f}")

# ---- dose-response: DIAGNOSTIC ONLY, explicitly not a strategy --------------
print("\nDose-response by |C_diff| quintile — DIAGNOSTIC, NOT A STRATEGY.")
print("Section 4 forbids threshold selection; the best cell here is an")
print("upper-biased estimate and must not be read as an achievable edge.")
q = pd.qcut(ho.C_diff.abs(), 5, labels=False)
print(f"  {'quintile':<24}{'bets':>7}{'hit':>9}{'profit $':>12}{'ROI':>9}{'vs BE':>11}")
for k in range(5):
    line(f"  Q{k+1} |C_diff|", pnl(ho[q == k]))
