"""Putting CrewShock into the right units.

CrewShock is a foul RATE deviation (+1.09 fouls per 100 possessions per unit).
The extra fouls it actually produces are mechanically

    ExpectedExtraFouls = CrewShock * ExpectedPossessions / 100

so the economically correct variable is

    RefExposure = CrewShock * ExpectedPossessions / 100

This is an accounting identity, not an interaction search.

EXPECTED POSSESSIONS — recovered, window unaltered:
    walkforward.py LAG = 4
    walkforward_pace.build_panel_ext: f_PACE = shift(1).rolling(LAG).mean()
    models_frozen.add_pace_terms:     pace_sum = h_f_PACE + a_f_PACE
    models_frozen line 123:           implied_total = (pace_sum/2) * oeff_sum/100
so pace_sum / 2 is the frozen PER-TEAM expected possession count.

CrewShock and LeagueFoulState are LOADED from ref_features.csv, never rebuilt.
The +0.8682 threshold is unchanged.

Unlike the play-by-play tests this uses the FULL split including 2025-26,
because every input is available in every season.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import ref_shock as rsk
import refs
from data_split import SPLIT_DATE
from dispersion_priced import ols
from models_frozen import add_pace_terms
from symmetric_features import build as sym_build

CTRL = rsk.CTRL
THR = 0.8682
STAKE, WIN, BE = 100.0, 100.0 * 100.0 / 110.0, 110 / 210


def build():
    G = add_pace_terms(sym_build())
    G["gid"] = G["gid"].astype(str).str.strip()
    G = G[["gid", "pace_sum"]].dropna().drop_duplicates("gid")

    m = refs.build()
    m["gid"] = m["GAME-ID"].astype(str).str.strip()
    n = lambda c: pd.to_numeric(m[c], errors="coerce")
    m["fouls"] = n("PF_H") + n("PF_R")
    m["fta"] = n("FTA_H") + n("FTA_R")
    n0 = len(m)
    m = m.merge(G, on="gid", how="left")
    assert len(m) == n0
    print(f"  frozen pace state merged: {m['pace_sum'].notna().sum():,} of {n0:,}")

    f = pd.read_csv("ref_features.csv")
    f["gid"] = f["gid"].astype(str).str.strip()
    m = m.merge(f[["gid", "CrewShock", "LeagueFoulState"]], on="gid", how="left")
    print(f"  frozen ref_features merged: {m['CrewShock'].notna().sum():,}")
    ctl = rsk.build()[["gid"] + CTRL]
    ctl["gid"] = ctl["gid"].astype(str).str.strip()
    m = m.merge(ctl, on="gid", how="left")

    m["ExpPoss"] = m["pace_sum"] / 2.0
    m["RefExposure"] = m["CrewShock"] * m["ExpPoss"] / 100.0
    return m


def main():
    d = build()
    core = ["CrewShock", "RefExposure", "ExpPoss", "LeagueFoulState",
            "e", "total", "actual", "fouls", "fta"]
    s = d.dropna(subset=core).copy()
    sc = s.dropna(subset=CTRL).copy()
    dev, hold = s[s["date"] < SPLIT_DATE], s[s["date"] >= SPLIT_DATE]

    print("\n" + "=" * 100)
    print("HOW MUCH DOES THE SCALING ACTUALLY CHANGE?")
    print("=" * 100)
    print(f"  {len(s):,} games (full split, 2025-26 included)   "
          f"develop {len(dev):,}   holdout {len(hold):,}")
    f_ = s["ExpPoss"] / 100.0
    print(f"  ExpPoss per team: mean {s['ExpPoss'].mean():.2f}  "
          f"sd {s['ExpPoss'].std():.2f}  "
          f"p1 {s['ExpPoss'].quantile(.01):.1f}  p99 {s['ExpPoss'].quantile(.99):.1f}")
    print(f"  scaling factor ExpPoss/100: mean {f_.mean():.4f}  sd {f_.std():.4f}"
          f"  -> it rescales CrewShock by only +/-{100*f_.std():.1f}%")
    r = np.corrcoef(s["CrewShock"], s["RefExposure"])[0, 1]
    print(f"  corr(CrewShock, RefExposure) = {r:.6f}")
    print(f"  POWER NOTE: with the two variables correlated at {r:.4f}, no")
    print(f"  sample can meaningfully prefer one over the other statistically.")
    print(f"  The case for RefExposure is that it is the correct unit, not that")
    print(f"  it fits better.")

    print("\n" + "=" * 100)
    print("HEAD TO HEAD on identical rows — Residual ~ X (no controls)")
    print("=" * 100)
    print(f"  {'window':9} {'variable':14} {'coef':>9} {'t':>7} {'R^2 %':>9}")
    for lab, x in (("develop", dev), ("holdout", hold), ("all", s)):
        for nm in ("CrewShock", "RefExposure"):
            b, se, t = ols(x["e"].values, x[nm].values.reshape(-1, 1))
            pred = b[0] + b[1] * x[nm].values
            r2 = 1 - ((x["e"] - pred) ** 2).sum() / (
                (x["e"] - x["e"].mean()) ** 2).sum()
            print(f"  {lab:9} {nm:14} {b[1]:9.4f} {t[1]:7.2f} {100*r2:9.4f}")
        print()

    print("=" * 100)
    print("NESTED — Residual ~ CrewShock + ExpPoss + CrewShock*ExpPoss + controls")
    print("  delta != 0 would say the referee omission scales with pace")
    print("=" * 100)
    for lab, x in (("develop", sc[sc["date"] < SPLIT_DATE]),
                   ("holdout", sc[sc["date"] >= SPLIT_DATE]), ("all", sc)):
        X = np.column_stack([x["CrewShock"], x["ExpPoss"],
                             x["CrewShock"] * x["ExpPoss"],
                             x["LeagueFoulState"]] + [x[c] for c in CTRL])
        b, se, t = ols(x["e"].values, X)
        print(f"  {lab:9} n={len(x):5,}  bR {b[1]:+8.4f} (t={t[1]:+5.2f})   "
              f"bP {b[2]:+7.4f} (t={t[2]:+5.2f})   "
              f"delta {b[3]:+8.5f} (t={t[3]:+5.2f})")

    print("\n" + "=" * 100)
    print("THE CHAIN on RefExposure   Y ~ RefExposure + League + controls")
    print("=" * 100)
    print(f"  {'link':22} {'develop':>22} {'holdout':>22}")
    for col, name in (("fouls", "raw fouls"), ("fta", "FTA"),
                      ("actual", "ACTUAL TOTAL"), ("total", "CLOSING TOTAL"),
                      ("e", "closing residual")):
        cells = []
        for x in (sc[sc["date"] < SPLIT_DATE], sc[sc["date"] >= SPLIT_DATE]):
            X = np.column_stack([x["RefExposure"], x["LeagueFoulState"]]
                                + [x[c] for c in CTRL])
            b, se, t = ols(x[col].values, X)
            cells.append(f"{b[1]:+9.4f} (t={t[1]:+5.2f})")
        print(f"  {name:22} {cells[0]:>22} {cells[1]:>22}")

    print("\n  c_market vs c_true for RefExposure")
    for lab, x in (("develop", sc[sc["date"] < SPLIT_DATE]),
                   ("holdout", sc[sc["date"] >= SPLIT_DATE]), ("all", sc)):
        X = np.column_stack([x["RefExposure"], x["LeagueFoulState"]]
                            + [x[c] for c in CTRL])
        bm, _, tm = ols(x["total"].values, X)
        bt, _, tt = ols(x["actual"].values, X)
        print(f"    {lab:9} c_market {bm[1]:+.4f} (t={tm[1]:+5.2f})   "
              f"c_true {bt[1]:+.4f} (t={tt[1]:+5.2f})   "
              f"gap {bt[1]-bm[1]:+.4f}")

    print("\n" + "=" * 100)
    print("ECONOMIC — equal selectivity, develop Q85 of each signal")
    print("=" * 100)
    qe = dev["RefExposure"].quantile(0.85)
    print(f"  frozen CrewShock threshold {THR:+.4f}   "
          f"develop Q85 of RefExposure {qe:+.4f}")
    rows = []
    for nm, thr in (("CrewShock", THR), ("RefExposure", qe)):
        print(f"\n  BET OVER when {nm} >= {thr:+.4f}")
        print(f"    {'window':10} {'bets':>6} {'W':>5} {'L':>5} {'win %':>7} "
              f"{'$ won':>9} {'ROI %':>7} {'mean e':>8}")
        for lab, x in (("develop", dev), ("holdout", hold), ("all", s)):
            b = x[x[nm] >= thr]
            w = int((b["e"] > 0).sum())
            l = int((b["e"] < 0).sum())
            pnl = w * WIN - l * STAKE
            wp = 100 * w / (w + l) if w + l else np.nan
            roi = 100 * pnl / (STAKE * (w + l)) if w + l else np.nan
            print(f"    {lab:10} {len(b):6,} {w:5} {l:5} {wp:7.2f} "
                  f"{pnl:9,.0f} {roi:7.2f} {b['e'].mean():8.3f}")
            rows.append({"signal": nm, "window": lab, "bets": len(b),
                         "win_pct": round(wp, 2), "roi": round(roi, 2),
                         "mean_e": round(b["e"].mean(), 3), "dollars": round(pnl)})
        for y in sorted(hold["yr"].unique()):
            b = hold[(hold["yr"] == y) & (hold[nm] >= thr)]
            w = int((b["e"] > 0).sum())
            l = int((b["e"] < 0).sum())
            wp = 100 * w / (w + l) if w + l else np.nan
            print(f"      {y:<8} {len(b):6,} {w:5} {l:5} {wp:7.2f} "
                  f"{w*WIN-l*STAKE:9,.0f}")
    pd.DataFrame(rows).to_csv("ref_exposure_pnl.csv", index=False)
    ov = s[s["CrewShock"] >= THR].index
    oe = s[s["RefExposure"] >= qe].index
    print(f"\n  overlap of the two selections: {len(set(ov)&set(oe)):,} of "
          f"{len(ov):,} / {len(oe):,} "
          f"({100*len(set(ov)&set(oe))/max(len(ov),1):.1f}%)")


if __name__ == "__main__":
    main()
