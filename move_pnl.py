"""P&L check on the FROZEN MOVE_COMBINED signal — read-only.

Nothing here modifies the estimator, weights, thresholds or trading rule. The
DECISION cells are the frozen |m| >= 1.0 (primary) and >= 1.5 (confirmatory);
the full grid is reported because the prereg already fixes it as the report
grid, not because any cell is being selected.

Adds the two checks the cohesion branch showed were missing:
  1 the CORRECTED break-even arithmetic (shift from 50%, COMPARED to 52.381%)
  2 the TAIL diagnostic: does the edge sit near the total line or in blowouts?
"""
import math, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")

STAKE, WIN = 100.0, 100.0 / 1.1
BE = 1.1 / 2.1

s = pd.read_csv("/mnt/c/NBA2/move_signal_states.csv")
s["gid"] = s["GAME-ID"].astype(str).str.strip()
g = pd.read_csv("movement_full_games.csv")
g["gid"] = g.game_id.astype(str).str.strip()
d = s.merge(g[["gid", "actual_total", "close_total", "open_total", "season"]],
            on="gid", how="inner")
d = d.dropna(subset=["MOVE_COMBINED_OOS", "actual_total", "open_total"])
d["m"] = d.MOVE_COMBINED_OOS
# prereg: "simulated bet placed AT the recorded opener; pushes void"
d["res"] = np.sign(d.actual_total - d.open_total)     # +1 over, -1 under
d["side"] = np.sign(d.m)                              # bet over if m>0
print(f"games with a frozen OOS signal: {len(d):,}   "
      f"seasons {sorted(d.SEASON.unique())}")


def pnl(x):
    live = (x.side != 0) & (x.res != 0)
    w = int(((x.side == x.res) & live).sum())
    l = int(((x.side != x.res) & live).sum())
    n = w + l
    prof = w * WIN - l * STAKE
    hit = w / n if n else np.nan
    se = math.sqrt(0.25 / n) if n else np.nan
    z = (hit - BE) / se if n else np.nan
    return dict(bets=n, hit=hit, prof=prof, roi=prof / (n * STAKE) if n else np.nan,
                se=se, z=z)


def line(lab, r):
    print(f"  {lab:<22}{r['bets']:>7,}{100*r['hit']:>8.2f}%{r['prof']:>+12,.0f}"
          f"{100*r['roi']:>+9.2f}%{100*(r['hit']-BE):>+9.2f}pp{r['z']:>+7.2f}")


print(f"\nBet at the OPENER, -110, $100/game. Break-even {100*BE:.3f}%.")
print(f"  {'threshold':<22}{'bets':>7}{'hit':>9}{'profit $':>12}{'ROI':>9}"
      f"{'vs BE':>11}{'z':>7}")
print("  " + "-" * 77)
for th in (0.0, 0.5, 1.0, 1.5, 2.0, 2.5):
    tag = " *DECISION*" if th in (1.0, 1.5) else ""
    line(f"|m| >= {th}{tag}", pnl(d[d.m.abs() >= th]))

print("\nSeason by season at the primary threshold |m| >= 1.0")
print(f"  {'season':<22}{'bets':>7}{'hit':>9}{'profit $':>12}{'ROI':>9}"
      f"{'vs BE':>11}{'z':>7}")
for ss, x in d[d.m.abs() >= 1.0].groupby("SEASON"):
    line(str(ss), pnl(x))

print("\n=== CORRECTED ARITHMETIC (the step I got wrong on cohesion) ===")
dev = (d.actual_total - d.close_total)
sd = float(dev.std())
dens = 0.3989 / sd
print(f"  sd(actual_total - close_total) = {sd:.2f}  ->  density "
      f"{100*dens:.2f}pp per point")
print(f"  -110 requires a shift from 50% of {100*(BE-0.5):.3f}pp "
      f"= {(BE-0.5)/dens:.3f} POINTS of edge")
for th in (1.0, 1.5):
    x = d[d.m.abs() >= th]
    mp = x.m.abs().mean()
    imp = 0.5 + mp * dens
    print(f"  |m| >= {th}: mean |m| {mp:.3f} pts -> implied {100*imp:.2f}%  "
          f"vs BE {100*BE:.2f}%  -> net {100*(imp-BE):+.2f}pp   "
          f"(realised {100*pnl(x)['hit']:.2f}%)")

print("\n=== TAIL DIAGNOSTIC — where does the edge sit? ===")
print("  (outcome-conditioned, DIAGNOSTIC only, not a predictive claim)")
x = d[d.m.abs() >= 1.0].copy()
x["miss"] = (x.actual_total - x.open_total).abs()
q = pd.qcut(x.miss, 3, labels=["near the number", "middle", "blowout tail"])
print(f"  {'|actual-open|':<22}{'bets':>7}{'hit':>9}{'profit $':>12}{'ROI':>9}"
      f"{'vs BE':>11}{'z':>7}")
for k, gg in x.groupby(q):
    line(str(k), pnl(gg))
print("\n  NOTE: for a totals bet the cover IS the sign of (actual - line), so")
print("  unlike cohesion this signal was ALWAYS evaluated on the tradeable")
print("  quantity. The split above cannot be gamed into a strategy: you cannot")
print("  know |actual - open| before the game.")
