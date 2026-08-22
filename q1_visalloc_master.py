"""Rebuild the visitor-allocation quarter effect from the MASTER quarter columns
(1Q_H..4Q_H, 1Q_R..4Q_R) rather than the play-by-play.

WHY. q1_visalloc.py used halves.period_scores(), which reads the PBP parquet --
and the PBP ends 2024-25. The master CSV carries every quarter for both sides
through 2026-06-15, so the state needs no PBP at all. Two consequences:

  1. the state is OPERABLE for 2026-27 (B computed from seasons through 2025-26)
  2. 2025-26 is a genuinely FRESH out-of-sample season for this hypothesis,
     never examined, and it is checked here BEFORE any pre-registration is
     written around the effect

This is a mechanism-persistence gate, exactly analogous to the CrewTilt/CrewPace
Stage-1 gates: if the state stopped predicting quarter relocation in 2025-26,
there is nothing to pre-register and the branch closes.

State, benchmark and predictions are unchanged from q1_visalloc.py. The PBP-based
development numbers are reproduced first as a cross-check on the data source.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import refs
from data_split import SPLIT_DATE
from dispersion_priced import ols

MIN_PRIOR = 60


def build():
    m = refs.build()
    n = lambda c: pd.to_numeric(m[c], errors="coerce")
    d = pd.DataFrame({
        "gid": m["GAME-ID"].astype(str).str.strip(), "yr": m["yr"],
        "date": m["date"], "TEAM_R": m["TEAM_R"], "TEAM_H": m["TEAM_H"],
        "total": m["total"], "actual": m["actual"], "e": m["e"]})
    for p in (1, 2, 3, 4):
        d[f"vis_p{p}"] = n(f"{p}Q_R")
        d[f"hom_p{p}"] = n(f"{p}Q_H")
        d[f"q{p}"] = d[f"vis_p{p}"] + d[f"hom_p{p}"]
    d = d.dropna(subset=[f"q{p}" for p in (1, 2, 3, 4)] + ["total"])

    # B: visitor's own (Q3 - Q1) on the ROAD, seasons strictly prior, n >= 60
    road = d[["yr", "TEAM_R", "vis_p1", "vis_p3"]].copy()
    road["q31"] = road["vis_p3"] - road["vis_p1"]
    h = road.groupby(["TEAM_R", "yr"], as_index=False).agg(
        s=("q31", "sum"), n=("q31", "size"))
    rows = []
    for t, g in h.groupby("TEAM_R"):
        g = g.sort_values("yr")
        cs, cn = g["s"].cumsum().shift(1), g["n"].cumsum().shift(1)
        for yr, s_, n_ in zip(g["yr"], cs, cn):
            if pd.notna(n_) and n_ >= MIN_PRIOR:
                rows.append({"TEAM_R": t, "yr": yr, "B": s_ / n_})
    return d.merge(pd.DataFrame(rows), on=["TEAM_R", "yr"], how="inner")


def main():
    d = build()
    dev = d[d["date"] < SPLIT_DATE]
    print(f"  {len(d):,} games with the state   "
          f"seasons {sorted(d['yr'].unique())}")
    print(f"  development {len(dev):,}   2024-25 {(d['yr']==2024).sum():,}   "
          f"2025-26 {(d['yr']==2025).sum():,}")

    shares = {p: dev[f"q{p}"].sum() / dev["total"].sum() for p in (1, 2, 3, 4)}
    mu, sd = dev["B"].mean(), dev["B"].std()
    d["Bz"] = (d["B"] - mu) / sd
    for p in (1, 2, 3, 4):
        d[f"d_q{p}"] = d[f"q{p}"] - shares[p] * d["total"]
    d["d_h1"] = d["d_q1"] + d["d_q2"]
    d["d_h2"] = d["d_q3"] + d["d_q4"]
    d["d_q31"] = d["q3"] - d["q1"]

    dev = d[d["date"] < SPLIT_DATE]          # re-slice: d_q* added above
    print(f"\n  FROZEN CONSTANTS (development 2017-18..2023-24)")
    print(f"    quarter shares of the closing total: "
          + "  ".join(f"q{p} {shares[p]:.4f}" for p in (1, 2, 3, 4)))
    print(f"    B mean {mu:+.4f}   B sd {sd:.4f}")
    qs = np.quantile(dev["B"], [0.2, 0.4, 0.6, 0.8])
    print(f"    B quintile cuts: " + "  ".join(f"{q:+.4f}" for q in qs))
    print(f"    Q1 residual sd {dev['d_q1'].std():.4f}   "
          f"Q3 residual sd {dev['d_q3'].std():.4f}")

    W = [("development", d[d["date"] < SPLIT_DATE]),
         ("2024-25", d[d["yr"] == 2024]),
         ("2025-26 FRESH", d[d["yr"] == 2025])]
    print("\n" + "=" * 96)
    print("EFFECT PER +1 DEVELOPMENT SD OF B  (points vs the formula price)")
    print("=" * 96)
    hdr = "".join(f"{w[0]:>17}" for w in W)
    print(f"  {'outcome':12}{'pred':>6}{hdr}")
    for col, pred in (("d_q1", "NEG"), ("d_q3", "POS"), ("d_q31", "POS"),
                      ("d_h1", "NEG"), ("d_h2", "POS"), ("e", "~0")):
        cells = ""
        for _, x in W:
            s = x.dropna(subset=[col, "Bz"])
            b, se, t = ols(s[col].values, np.column_stack([s["Bz"].values]))
            cells += f"{b[1]:>+10.3f}({t[1]:>+.2f})".rjust(17)
        print(f"  {col:12}{pred:>6}{cells}")

    print("\n" + "=" * 96)
    print("QUINTILES OF B — d_q3 (the strongest leg)")
    print("=" * 96)
    d["quint"] = np.searchsorted(qs, d["B"]) + 1
    W = [("development", d[d["date"] < SPLIT_DATE]),
         ("2024-25", d[d["yr"] == 2024]), ("2025-26 FRESH", d[d["yr"] == 2025])]
    print(f"  {'quint':>6}" + "".join(f"{w[0]:>20}" for w in W))
    for q in (1, 2, 3, 4, 5):
        cells = ""
        for _, x in W:
            s = x[x["quint"] == q]
            cells += f"n={len(s):<5} {s['d_q3'].mean():>+7.3f}".rjust(20)
        print(f"  {q:>6}{cells}")

    print("\n" + "=" * 96)
    print("GATE — did the state survive into 2025-26?")
    print("=" * 96)
    s = d[d["yr"] == 2025].dropna(subset=["d_q3", "Bz"])
    b, se, t = ols(s["d_q3"].values, np.column_stack([s["Bz"].values]))
    s1 = d[d["yr"] == 2025].dropna(subset=["d_q1", "Bz"])
    b1, _, t1 = ols(s1["d_q1"].values, np.column_stack([s1["Bz"].values]))
    ok = (b[1] > 0 and t[1] > 2) and (b1[1] < 0)
    print(f"  2025-26  d_q3 {b[1]:+.3f} (t={t[1]:+.2f})   "
          f"d_q1 {b1[1]:+.3f} (t={t1[1]:+.2f})   n={len(s)}")
    print(f"  GATE (d_q3 slope>0 with t>2, and d_q1 slope<0): "
          f"{'PASS' if ok else 'FAIL'}")


if __name__ == "__main__":
    main()
