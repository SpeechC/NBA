"""CALIBRATION vs ACCURACY on this program's two frozen signals.

DESCRIPTIVE. This can only DOWNGRADE confidence in signal magnitude; no new
signal, threshold or strategy may come out of it. Motivated by Walsh & Joshi
(papers/ssrn_4705918.pdf): model selection on calibration beats accuracy, and
Kelly sizing only works on a calibrated model.

A signal is CALIBRATED in magnitude if a bucket whose points-of-edge implies
54% actually wins 54%. If the reliability curve flattens or reverses, the sign
is informative and the MAGNITUDE IS NOT -- which forbids Kelly sizing on it.
"""
import math, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
from prepare_data import read_master, season_label

BE = 1.1 / 2.1


def emp_gain(dev, e):
    """EXACT empirical win-probability gain from e points of edge."""
    return np.mean(dev > -e) - np.mean(dev > 0)


def table(name, val, res, dev_pool, edges):
    """val = |signal| in points of edge; res = +1 win / -1 loss / 0 push."""
    print(f"\n=== {name} ===")
    print(f"  {'bucket':<14}{'n':>6}{'mean |edge|':>13}{'IMPLIED':>10}"
          f"{'ACTUAL':>9}{'gap':>9}")
    rows = []
    for lo, hi in edges:
        m = (val >= lo) & (val < hi)
        r = res[m]
        live = r != 0
        if live.sum() < 60:
            continue
        act = (r[live] > 0).mean()
        e = val[m].mean()
        imp = 0.5 + emp_gain(dev_pool, e)
        rows.append((lo, hi, int(live.sum()), e, imp, act))
        print(f"  {f'{lo:.1f}-{hi:.1f}':<14}{int(live.sum()):>6,}{e:>13.3f}"
              f"{100*imp:>9.2f}%{100*act:>8.2f}%{100*(act-imp):>+8.2f}pp")
    return rows


# ---------------- MOVE_COMBINED ---------------------------------------------
s = pd.read_csv("/mnt/c/NBA2/move_signal_states.csv")
s["gid"] = s["GAME-ID"].astype(str).str.strip()
g = pd.read_csv("movement_full_games.csv"); g["gid"] = g.game_id.astype(str).str.strip()
d = s.merge(g[["gid", "actual_total", "open_total", "close_total"]], on="gid").dropna(
    subset=["MOVE_COMBINED_OOS", "actual_total", "open_total"])
d["res"] = np.sign(d.MOVE_COMBINED_OOS) * np.sign(d.actual_total - d.open_total)
dev_open = (d.actual_total - d.open_total).values
rows_m = table("MOVE_COMBINED — is |m| calibrated as points of edge?",
               d.MOVE_COMBINED_OOS.abs().values, d.res.values, dev_open,
               [(0,.5),(.5,1),(1,1.5),(1.5,2),(2,2.5),(2.5,3),(3,9)])

# ---------------- CrewShock --------------------------------------------------
raw = read_master(verbose=False); raw["season"] = season_label(raw).astype(str)
raw = raw[raw.season.str.contains("Regular Season", na=False)].copy()
n = lambda c: pd.to_numeric(raw[c], errors="coerce")
m = pd.DataFrame({"gid": raw["GAME-ID"].astype(str).str.strip(),
                  "close": n("CLOSING TOTAL_H"),
                  "actual": n("PTS_H") + n("PTS_R")}).dropna()
m = m[m.close.between(150, 300)]
rf = pd.read_csv("ref_features.csv"); rf["gid"] = rf.gid.astype(str).str.strip()
c = rf[["gid", "CrewShock"]].merge(m, on="gid").dropna()
c["res"] = np.sign(c.actual - c.close)          # always bet OVER
dev_close = (c.actual - c.close).values
# CrewShock -> points: the frozen mechanism is +0.813 pts per 1 unit (CLOSING_REFEREE)
c["edge_pts"] = c.CrewShock * 0.813
rows_c = table("CrewShock — is the CrewShock VALUE calibrated as points?",
               c.edge_pts.clip(lower=0).values, c.res.values, dev_close,
               [(0,.3),(.3,.6),(.6,.9),(.9,1.2),(1.2,1.6),(1.6,9)])

# ---------------- monotonicity ----------------------------------------------
print("\n=== MONOTONICITY — does a bigger signal actually win more? ===")
for nm, rows in (("MOVE_COMBINED", rows_m), ("CrewShock", rows_c)):
    act = [r[5] for r in rows]
    inc = sum(act[i+1] > act[i] for i in range(len(act)-1))
    rho = np.corrcoef([r[3] for r in rows], act)[0, 1]
    print(f"  {nm:<16} buckets {len(rows)}  rising steps {inc}/{len(act)-1}  "
          f"corr(edge, actual win%) = {rho:+.3f}")
    print(f"     actual by bucket: {' '.join(f'{100*a:.1f}' for a in act)}")

print("\n=== THE OPERATIONAL QUESTION ===")
print("  If the magnitude is calibrated -> size by edge (Kelly).")
print("  If only the SIGN is informative -> FLAT BET; Kelly on an uncalibrated")
print("  magnitude allocates most capital to the least reliable cells.")
