"""Season-by-season P&L for the four monitor signals. Read-only, nothing refit.

$100 flat at -110 (win +$90.91, loss -$100, push $0). Break-even 52.381%.
ROI = 1.90909*hit - 1  (NOT 2.1*hit - 1; that slip is on record in
MOVEMENT_FULL.md). Entry points differ by signal and are labelled: CrewShock
and the two calendar windows grade at the CLOSE, MOVE_COMBINED bets AT THE
OPENER by construction.
"""
import math, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
from prepare_data import read_master, season_label

STAKE, WIN = 100.0, 100.0/1.1
MULT, BE = 1 + WIN/STAKE, 1.1/2.1


def pnl(res):
    """res: +1 win, -1 loss, 0 push."""
    res = np.asarray(res); live = res != 0
    w = int((res[live] > 0).sum()); l = int((res[live] < 0).sum()); n = w+l
    if not n: return None
    hit = w/n; se = math.sqrt(0.25/n)
    return dict(n=n, hit=hit, prof=w*WIN - l*STAKE, roi=MULT*hit-1,
                z=(hit-BE)/se, lo=MULT*(hit-1.96*se)-1, hi=MULT*(hit+1.96*se)-1,
                push=int((~live).sum()))


def table(name, entry, by_season, total):
    print(f"\n{'='*82}\n {name}   (graded at the {entry})\n{'='*82}")
    print(f"  {'season':<10}{'bets':>7}{'hit':>9}{'profit $':>12}{'ROI':>9}{'vs BE':>10}")
    for s, r in by_season:
        if r is None: continue
        print(f"  {s:<10}{r['n']:>7,}{100*r['hit']:>8.2f}%{r['prof']:>+12,.0f}"
              f"{100*r['roi']:>+9.2f}%{100*(r['hit']-BE):>+9.2f}pp")
    r = total
    print(f"  {'-'*72}")
    print(f"  {'TOTAL':<10}{r['n']:>7,}{100*r['hit']:>8.2f}%{r['prof']:>+12,.0f}"
          f"{100*r['roi']:>+9.2f}%{100*(r['hit']-BE):>+9.2f}pp")
    print(f"  z vs break-even {r['z']:+.2f}    ROI 95% CI "
          f"[{100*r['lo']:+.2f}%, {100*r['hi']:+.2f}%]  "
          f"{'EXCLUDES 0' if r['lo']>0 else 'includes 0'}")


# ---------------- master: calendar windows (frozen defs from pre_asb.py) -----
raw = read_master(verbose=False)
raw["lbl"] = season_label(raw).astype(str)
d = raw[raw["lbl"].str.contains("Regular Season", na=False)].copy()
d["date"] = pd.to_datetime(d["DATE"], errors="coerce")
d["close"] = pd.to_numeric(d["CLOSING TOTAL_H"], errors="coerce")
d["actual"] = pd.to_numeric(d["PTS_H"], errors="coerce") + pd.to_numeric(d["PTS_R"], errors="coerce")
d = d.dropna(subset=["date", "close", "actual"])
d = d[d["close"].between(150, 300)].copy()
d["yr"] = d["lbl"].str.extract(r"(\d{4})")[0].astype(int)
d["days_left"] = (d.groupby("lbl")["date"].transform("max") - d["date"]).dt.days
brk = {}
for lbl, g in d.groupby("lbl"):
    dts = np.sort(g["date"].unique())
    if len(dts) < 3: continue
    gaps = np.diff(dts).astype("timedelta64[D]").astype(int)
    brk[lbl] = pd.Timestamp(dts[int(np.argmax(gaps))])
d["days_to_break"] = d["lbl"].map(brk) - d["date"]
d["days_to_break"] = d["days_to_break"].dt.days
d["final7"] = d["days_left"] <= 7
d["pre_asb3"] = d["days_to_break"].between(0, 2)
d["res_over"] = np.sign(d["actual"] - d["close"])      # OVER bet

for name, flag in (("final7  — VALIDATED (55.29% OOS)", "final7"),
                   ("pre_asb3 — NOT VALIDATED, family-wise p=0.0712", "pre_asb3")):
    sub = d[d[flag]]
    bys = [(str(y), pnl(g.res_over.values)) for y, g in sub.groupby("yr")]
    table(name, "CLOSE, bet OVER", bys, pnl(sub.res_over.values))

# ---------------- CrewShock --------------------------------------------------
rf = pd.read_csv("ref_features.csv"); rf["gid"] = rf.gid.astype(str).str.strip()
d["gid"] = d["GAME-ID"].astype(str).str.strip()
cs = rf[["gid", "CrewShock", "yr"]].merge(
    d[["gid", "close", "actual", "res_over"]], on="gid", how="inner")
f = cs[cs.CrewShock >= 0.8682]
bys = [(str(y), pnl(g.res_over.values)) for y, g in f.groupby("yr")]
table("CrewShock — FROZEN, threshold 0.8682", "CLOSE, bet OVER",
      bys, pnl(f.res_over.values))

# ---------------- MOVE_COMBINED ---------------------------------------------
s = pd.read_csv("/mnt/c/NBA2/move_signal_states.csv")
s["gid"] = s["GAME-ID"].astype(str).str.strip()
g2 = pd.read_csv("movement_full_games.csv"); g2["gid"] = g2.game_id.astype(str).str.strip()
m = s.merge(g2[["gid", "actual_total", "open_total"]], on="gid").dropna(
    subset=["MOVE_COMBINED_OOS", "actual_total", "open_total"])
m = m[m.MOVE_COMBINED_OOS.abs() >= 1.0].copy()
m["res"] = np.sign(m.MOVE_COMBINED_OOS) * np.sign(m.actual_total - m.open_total)
bys = [(str(y), pnl(x.res.values)) for y, x in m.groupby("SEASON")]
table("MOVE_COMBINED — FROZEN, |m| >= 1.0", "OPENER, side = sign(m)",
      bys, pnl(m.res.values))

print(f"\n{'='*82}\n NOTE: only CrewShock and MOVE_COMBINED are game-selective. The two")
print(" calendar windows bet EVERY game in the window, so their bet counts are")
print(" set by the schedule, not by a signal strength.")
