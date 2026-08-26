"""P&L check on injury Hypothesis B — read-only, nothing refitted.

PREREG_injury already states B "is NOT a tradable edge as it stands": the final
pregame report precedes tip by ~30 minutes and the close is AT tip, so the
signal is near-contemporaneous with the market's own reaction. This quantifies
what that costs, by separating two questions that must not be conflated:

  UPPER BOUND (unattainable) -- bet at the OPENER on late-out news. This uses
      information that DOES NOT EXIST at the opener. It is leakage by
      construction and is reported only to bound the value of a latency edge.

  ACTIONABLE -- bet at the CLOSE, after the final report is public. This is
      the only version you could really place, and it asks whether the closing
      total OVER- or UNDER-reacts to late outs.
"""
import math, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
import injury_market as IM

STAKE, WIN = 100.0, 100.0 / 1.1
MULT, BE = 1 + WIN / STAKE, 1.1 / 2.1

d = IM.build()
d["late_signed"] = (d["OUT_late_DEF"] + d["OUT_late_OFF"]
                    - d.get("UPGRADE_late_DEF", 0) - d.get("UPGRADE_late_OFF", 0))
print(f"panel {len(d):,} games   late_signed nonzero on "
      f"{int((d.late_signed != 0).sum()):,}")
cols = [c for c in ("total", "ot_open", "ot_close", "open_total", "close_total",
                    "actual_total") if c in d.columns]
print("available market cols:", cols)


def pnl(x, line_col, sign):
    """sign = direction bet, +1 over / -1 under. Push when it lands exactly."""
    res = np.sign(x["total"].values - x[line_col].values)
    live = (sign != 0) & (res != 0)
    w = int(((sign == res) & live).sum())
    l = int(((sign != res) & live).sum())
    n = w + l
    if n == 0:
        return None
    hit = w / n
    se = math.sqrt(0.25 / n)
    return dict(n=n, hit=hit, roi=MULT * hit - 1, prof=w * WIN - l * STAKE,
                se=se, z=(hit - BE) / se,
                lo=MULT * (hit - 1.96 * se) - 1, hi=MULT * (hit + 1.96 * se) - 1)


def line(lab, r):
    if r is None:
        print(f"  {lab:<34} no live bets"); return
    print(f"  {lab:<34}{r['n']:>7,}{100*r['hit']:>8.2f}%{r['prof']:>+11,.0f}"
          f"{100*r['roi']:>+9.2f}%{r['z']:>+7.2f}   "
          f"[{100*r['lo']:+.2f}%, {100*r['hi']:+.2f}%]")


# B's sign is NEGATIVE: net late absences move the total DOWN -> bet UNDER
f = d[d.late_signed != 0].dropna(subset=["total", "ot_open", "ot_close"])
side = -np.sign(f.late_signed.values)
print(f"\nB fires on {len(f):,} games with both lines present. "
      f"Sign convention: net late OUTs -> bet UNDER.")
print(f"Break-even {100*BE:.3f}%. $100/bet at -110.")
print(f"  {'variant':<34}{'bets':>7}{'hit':>9}{'profit':>11}{'ROI':>9}{'z':>7}"
      f"   ROI 95% CI")
print("  " + "-" * 96)
line("UPPER BOUND @ opener (LEAKAGE)", pnl(f, "ot_open", side))
line("ACTIONABLE @ close", pnl(f, "ot_close", side))

print("\n=== Is the movement B predicts already IN the close? (CLV) ===")
clv = side * (f.ot_close.values - f.ot_open.values)
se = clv.std() / np.sqrt(len(clv))
print(f"  mean CLV {clv.mean():+.4f} pts   t = {clv.mean()/se:+.2f}   "
      f"beat the close {100*(clv > 0).mean():.1f}%")
print(f"  -> the line ALREADY moves {clv.mean():+.3f} pts toward B's direction")
print(f"     between open and close. That movement IS Hypothesis B; it is the")
print(f"     finding, and capturing it requires beating the market to it.")

print("\n=== What the two variants mean ===")
ub, ac = pnl(f, "ot_open", side), pnl(f, "ot_close", side)
if ub and ac:
    print(f"  upper bound ROI {100*ub['roi']:+.2f}%  minus  actionable ROI "
          f"{100*ac['roi']:+.2f}%  =  {100*(ub['roi']-ac['roi']):+.2f}pp")
    print(f"  That difference is the ENTIRE value of the latency race, and it is")
    print(f"  only available to someone who acts before the line moves.")
