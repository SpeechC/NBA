"""P&L check on the FROZEN CrewShock signal — read-only.

Nothing modified: estimator, shrinkage, threshold (>= 0.8682), windows and the
trading rule (bet OVER) are all frozen. Reproduces CLOSING_REFEREE.md first,
then adds the four checks this series developed:
  1 corrected break-even arithmetic (points required vs available)
  2 ROI confidence interval with the correct 1.90909 multiplier
  3 tail diagnostic -- near the number or in blowouts?
  4 CLV -- which should be ~ZERO here, because non-pricing IS the finding
"""
import math, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
from prepare_data import read_master, season_label, _side

STAKE, WIN = 100.0, 100.0 / 1.1
MULT, BE = 1 + WIN / STAKE, 1.1 / 2.1
THR = 0.8682                      # FROZEN development Q85

rf = pd.read_csv("ref_features.csv")
rf["gid"] = rf.gid.astype(str).str.strip()
raw = read_master(verbose=False)
raw["season"] = season_label(raw)
raw = raw[raw["season"].astype(str).str.contains(
    "Regular Season|In-Season", na=False)].copy()
gid = raw["GAME-ID"].astype(str).str.strip()
hp = _side(raw, "H")["Y"].values.astype(float)
ap = _side(raw, "R")["Y"].values.astype(float)
m = pd.DataFrame({"gid": gid.values, "season": raw["season"].astype(str).values,
                  "close_total": pd.to_numeric(raw["CLOSING TOTAL_H"], errors="coerce").values,
                  "open_total": pd.to_numeric(raw["OPENING TOTAL_H"], errors="coerce").values,
                  "actual_total": hp + ap})
d = rf[["gid", "CrewShock", "yr"]].merge(m, on="gid", how="inner").dropna(
    subset=["CrewShock", "close_total", "actual_total"])
d["is_dev"] = d.yr <= 2023        # frozen: development through 2023-24
f = d[d.CrewShock >= THR].copy()
print(f"joined {len(d):,} games;  CrewShock >= {THR} fires on {len(f):,}")


def pnl(x, col="close_total"):
    res = np.sign(x.actual_total.values - x[col].values)   # +1 over
    live = res != 0
    w = int((res[live] > 0).sum()); l = int((res[live] < 0).sum())
    n = w + l
    if not n: return None
    hit = w / n; se = math.sqrt(0.25 / n)
    return dict(n=n, hit=hit, prof=w * WIN - l * STAKE, roi=MULT * hit - 1,
                z=(hit - BE) / se, lo=MULT * (hit - 1.96 * se) - 1,
                hi=MULT * (hit + 1.96 * se) - 1, push=int((~live).sum()))


def line(lab, r):
    if r is None: print(f"  {lab:<26} none"); return
    print(f"  {lab:<26}{r['n']:>6,}{100*r['hit']:>8.2f}%{r['prof']:>+10,.0f}"
          f"{100*r['roi']:>+8.2f}%{r['z']:>+7.2f}   [{100*r['lo']:+.2f}%, {100*r['hi']:+.2f}%]")


print(f"\nBet OVER when CrewShock >= {THR}. $100 at -110, break-even {100*BE:.3f}%.")
print(f"  {'window':<26}{'bets':>6}{'hit':>9}{'profit':>10}{'ROI':>8}{'z':>7}   ROI 95% CI")
print("  " + "-" * 90)
line("DEVELOPMENT", pnl(f[f.is_dev]))
line("HOLDOUT", pnl(f[~f.is_dev]))
line("POOLED", pnl(f))
line("POOLED graded at OPEN", pnl(f, "open_total"))

print("\nSeason by season")
for ss, x in f.groupby("yr"):
    r = pnl(x)
    if r: line(str(ss), r)

print("\n=== 1. CORRECTED ARITHMETIC ===")
dev_sd = float((d.actual_total - d.close_total).std())
dens = 0.3989 / dev_sd
print(f"  sd(actual - close) {dev_sd:.2f} -> density {100*dens:.2f}pp per point")
print(f"  -110 requires {100*(BE-0.5):.3f}pp = {(BE-0.5)/dens:.3f} POINTS of edge")
edge_pts = (f.actual_total - f.close_total).mean()
print(f"  realised mean (actual - close) in the firing tail = {edge_pts:+.3f} pts")
print(f"  implied hit from {edge_pts:+.3f} pts: {100*(0.5+edge_pts*dens):.2f}%"
      f"   realised {100*pnl(f)['hit']:.2f}%")

print("\n=== 4. CLV — expected to be ~ZERO, because NON-PRICING is the finding ===")
c = (f.close_total - f.open_total).dropna()
se = c.std() / np.sqrt(len(c))
print(f"  mean close-open on firing games {c.mean():+.4f} pts  t={c.mean()/se:+.2f}"
      f"  (n={len(c):,})")
cn = (d[d.CrewShock < THR].close_total - d[d.CrewShock < THR].open_total).dropna()
print(f"  non-firing games                {cn.mean():+.4f} pts   "
      f"difference {c.mean()-cn.mean():+.4f}")
print("  -> if the market priced CrewShock, the line would drift UP on these")
print("     games. CLOSING_REFEREE reports c_market statistically zero; a null")
print("     here is the CONFIRMATION, not a failure.")

print("\n=== 3. TAIL DIAGNOSTIC (outcome-conditioned, diagnostic only) ===")
x = f.copy(); x["miss"] = (x.actual_total - x.close_total).abs()
q = pd.qcut(x.miss, 3, labels=["near the number", "middle", "blowout tail"])
print(f"  {'|actual-close|':<26}{'bets':>6}{'hit':>9}{'profit':>10}{'ROI':>8}{'z':>7}")
for k, gg in x.groupby(q):
    r = pnl(gg)
    if r: print(f"  {str(k):<26}{r['n']:>6,}{100*r['hit']:>8.2f}%{r['prof']:>+10,.0f}"
                f"{100*r['roi']:>+8.2f}%{r['z']:>+7.2f}")

pl = np.where(np.sign(f.actual_total.values - f.close_total.values) > 0, WIN,
              np.where(np.sign(f.actual_total.values - f.close_total.values) < 0, -STAKE, 0))
cum = np.cumsum(pl); dd = (cum - np.maximum.accumulate(cum)).min()
print(f"\n=== EQUITY PATH === final {cum[-1]:+,.0f}   max drawdown {dd:+,.0f} "
      f"({dd/STAKE:.0f}u)   share below zero {100*(cum < 0).mean():.0f}%")
