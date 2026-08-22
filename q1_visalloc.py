"""What is the visitor-allocation state worth on a Q1 TOTAL market?

CONTEXT. poss_vs_eff.py established that the VISITOR's prior-season road
Q3-Q1 orientation predicts BOTH teams' quarter splits out of sample (home
t=+5.38, away t=+5.06, 5/5 seasons). The effect RELOCATES points between
quarters and adds none to the full game, which is why it has been untradeable:
no quarter-total market existed in our data. Kalshi listed KXNBA1QTOTAL /
KXNBA3QTOTAL in June 2026. A first-season derivative market prices by formula
from the full-game ladder -- share x total -- which is exactly the benchmark a
relocation effect beats.

STATE, recovered from poss_vs_eff.py, not redefined:
    B(team, season) = mean of that team's OWN (Q3 pts - Q1 pts) over its ROAD
                      games in seasons STRICTLY BEFORE, requiring n >= 60
    attached to the game by its VISITOR. Standardised on development.
    High B = possessions/scoring shifted LATER (Q3-heavy).

BENCHMARK: the formula price  share_q * closing_total, shares frozen on
development (QUARTERS.md: q1 0.2525, q3 0.2502 -- NOT total/4).

    d_q = (Q_home + Q_vis) - share_q * closing_total

PREDICTIONS, stated before results:
    d_q1 on B:  NEGATIVE      d_q3 on B:  POSITIVE
    (q3-q1 total) on B: POSITIVE  -- the sharpest contrast
    d_q2, d_q4 on B: ~0           -- falsification
    full-game residual on B: ~0   -- known (relocation, not addition)

Development 2017-18..2023-24; SEALED 2024-25 (PBP ends there).
Economics at the end: points per SD of B against the Kalshi hurdle at a
quarter-total scale.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import refs
from data_split import SPLIT_DATE
from dispersion_priced import ols
from halves import period_scores

MIN_PRIOR = 60
SEALED = 2024


def build():
    w = period_scores().reset_index()
    w.columns = ["_".join(str(x) for x in c if x != "") if isinstance(c, tuple)
                 else c for c in w.columns]
    # columns like vis_1, home_1 ... after pivot; normalise
    ren = {}
    for p in (1, 2, 3, 4):
        for s in ("vis", "home"):
            for cand in (f"{s}_{p}", f"{s}_{p}.0", f"('{s}', {p})"):
                if cand in w.columns:
                    ren[cand] = f"{s}_p{p}"
    w = w.rename(columns=ren)
    need = [f"{s}_p{p}" for s in ("vis", "home") for p in (1, 2, 3, 4)]
    if not all(c in w.columns for c in need):
        raise SystemExit(f"column mismatch: {list(w.columns)}")
    w["gid"] = w["gid"].astype(str).str.zfill(10)
    for p in (1, 2, 3, 4):
        w[f"q{p}"] = w[f"vis_p{p}"] + w[f"home_p{p}"]

    m = refs.build()
    m["gidz"] = m["GAME-ID"].astype(str).str.strip().str.zfill(10)
    m = m[["gidz", "yr", "date", "TEAM_R", "TEAM_H", "total", "actual", "e"]]
    d = w.merge(m, left_on="gid", right_on="gidz", how="inner")

    # B: visitor's own Q3-Q1 on the road, prior seasons only, pooled
    road = d[["yr", "TEAM_R", "vis_p1", "vis_p3"]].copy()
    road["q31"] = road["vis_p3"] - road["vis_p1"]
    hist = road.groupby(["TEAM_R", "yr"], as_index=False).agg(
        s=("q31", "sum"), n=("q31", "size"))
    rows = []
    for (t,), g in hist.groupby(["TEAM_R"]):
        g = g.sort_values("yr")
        cs, cn = g["s"].cumsum().shift(1), g["n"].cumsum().shift(1)
        for yr, s_, n_ in zip(g["yr"], cs, cn):
            if pd.notna(n_) and n_ >= MIN_PRIOR:
                rows.append({"TEAM_R": t, "yr": yr, "B": s_ / n_})
    Bt = pd.DataFrame(rows)
    d = d.merge(Bt, on=["TEAM_R", "yr"], how="inner")
    return d.dropna(subset=["B", "total", "q1", "q3"])


def main():
    d = build()
    dev = d[d["date"] < SPLIT_DATE]
    print(f"  {len(d):,} games with the visitor state   development "
          f"{len(dev):,}   sealed 2024-25 {len(d)-len(dev):,}")

    shares = {p: (dev[f"q{p}"].sum() / dev["total"].sum()) for p in (1, 2, 3, 4)}
    print("  development quarter shares of the closing total: "
          + "  ".join(f"q{p} {shares[p]:.4f}" for p in (1, 2, 3, 4)))
    mu, sd = dev["B"].mean(), dev["B"].std()
    d["Bz"] = (d["B"] - mu) / sd
    print(f"  B: development mean {mu:+.3f} sd {sd:.3f}   "
          f"(points of own Q3-Q1 on the road)")

    for p in (1, 2, 3, 4):
        d[f"d_q{p}"] = d[f"q{p}"] - shares[p] * d["total"]
    d["d_q31"] = d["q3"] - d["q1"]

    print("\n" + "=" * 96)
    print("EFFECT OF THE VISITOR STATE ON FORMULA-PRICED QUARTER TOTALS")
    print("  coefficient = points per +1 development SD of B")
    print("=" * 96)
    print(f"  {'outcome':22}{'prediction':>12}{'development':>011}{'t':>7}"
          f"{'sealed':>11}{'t':>7}")
    dv, sl = d[d["date"] < SPLIT_DATE], d[d["yr"] == SEALED]
    keep = {}
    for col, pred in (("d_q1", "NEG"), ("d_q3", "POS"), ("d_q31", "POS"),
                      ("d_q2", "~0"), ("d_q4", "~0"), ("e", "~0")):
        cells = []
        for x in (dv, sl):
            s = x.dropna(subset=[col, "Bz"])
            b, se, t = ols(s[col].values, np.column_stack([s["Bz"].values]))
            cells.append((b[1], t[1]))
        keep[col] = cells
        print(f"  {col:22}{pred:>12}{cells[0][0]:>+11.4f}{cells[0][1]:>7.2f}"
              f"{cells[1][0]:>+11.4f}{cells[1][1]:>7.2f}")

    print("\n" + "=" * 96)
    print("QUINTILES OF B — the tradeable statement (development / sealed)")
    print("=" * 96)
    qs = np.quantile(dev["B"], [0.2, 0.4, 0.6, 0.8])
    d["quint"] = np.searchsorted(qs, d["B"]) + 1
    print(f"  {'quint':>6}{'n dev':>8}{'d_q1 dev':>10}{'d_q3 dev':>10}"
          f"{'n seal':>8}{'d_q1 seal':>11}{'d_q3 seal':>11}")
    for q in (1, 2, 3, 4, 5):
        a = dv[dv['quint'] == q] if 'quint' in dv else None
        a = d[(d["quint"] == q) & (d["date"] < SPLIT_DATE)]
        b_ = d[(d["quint"] == q) & (d["yr"] == SEALED)]
        print(f"  {q:>6}{len(a):>8}{a['d_q1'].mean():>+10.3f}"
              f"{a['d_q3'].mean():>+10.3f}{len(b_):>8}"
              f"{b_['d_q1'].mean():>+11.3f}{b_['d_q3'].mean():>+11.3f}")

    print("\n" + "=" * 96)
    print("ECONOMICS AT A QUARTER-TOTAL RUNG")
    print("=" * 96)
    resid_sd = dv["d_q1"].std()
    dens = 1.0 / (resid_sd * np.sqrt(2 * np.pi))
    b1 = abs(keep["d_q1"][0][0])
    q15 = abs(d[(d["quint"] == 5) & (d["date"] < SPLIT_DATE)]["d_q1"].mean()
              - d[(d["quint"] == 1) & (d["date"] < SPLIT_DATE)]["d_q1"].mean())
    print(f"  Q1-total residual sd (dev): {resid_sd:.2f} points   "
          f"ATM density {dens:.4f}/pt -> 1 point = {100*dens:.2f}pp")
    print(f"  effect per 1 SD of B:      {b1:.3f} pts = {100*b1*dens:.2f}pp")
    print(f"  Q5-Q1 quintile contrast:   {q15:.3f} pts = {100*q15*dens:.2f}pp")
    print(f"\n  {'venue':16}{'hurdle pp':>10}{'hurdle pts':>12}")
    for lab, h in (("-110 book", 2.38), ("Kalshi taker (2c)", 2.75),
                   ("Kalshi maker", -0.56)):
        print(f"  {lab:16}{h:>10.2f}{h/(100*dens):>12.2f}")
    print(f"\n  NOTE the maker hurdle is negative; the taker hurdle at a "
          f"quarter scale is only {2.75/(100*dens):.2f} points because the "
          f"residual sd is ~{resid_sd:.0f}, not ~18.")


if __name__ == "__main__":
    main()
