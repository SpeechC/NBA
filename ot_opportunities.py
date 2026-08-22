"""OVERTIME: what else is in it beyond the flat shape correction?

kalshi_shape.py modelled the total as a mixture with a CONSTANT p_OT = 5.24%.
That is a misspecification: overtime requires a regulation TIE, and tie
probability must fall as the expected margin grows. Three consequences, tested
here:

  1  IS P(OT) PREDICTABLE?  Fit P(OT) on |spread| (and check whether the total
     level adds anything) on development; validate on holdout. The mechanical
     prediction is a Gaussian tie density scaled by the end-game attractor
     (margin_shape.py measured ties at 1.78x the Gaussian rate).

  2  DOES THE SHAPE CORRECTION SCALE?  The Gaussian-vs-mixture gap is
     proportional to p_OT, so the ATM mispricing should be materially larger on
     close games than on blowouts. If so, the correction should be
     game-specific, not the flat ~0.75pp currently specified.

  3  KXNBAOVERTIME — Kalshi lists a DIRECT market on whether a game goes to
     overtime (2 settled markets, June 2026, zero volume). If P(OT) is
     predictable and the market quotes a flat rate, that is a clean trade on a
     cheap contract, with no shape modelling required. Sized here against a
     hypothetical flat quote.

All estimation on development 2017-18..2023-24; holdout 2024-25 + 2025-26.
"""
import warnings

import numpy as np
import pandas as pd
from scipy.stats import norm

warnings.filterwarnings("ignore")

import refs
from data_split import SPLIT_DATE
from dispersion_priced import ols

FEE_K = 0.07


def build():
    m = refs.build()
    n = lambda c: pd.to_numeric(m[c], errors="coerce")
    J = sum(n(f"OT{i}_{s}").fillna(0.0) for i in range(1, 6)
            for s in ("H", "R"))
    d = pd.DataFrame({
        "date": m["date"], "yr": m["yr"],
        "spread": n("CLOSING SPREAD_H"), "total": m["total"],
        "actual": m["actual"], "e": m["e"], "J": J,
        "margin": n("PTS_H") - n("PTS_R")})
    d = d.dropna(subset=["spread", "total", "actual"])
    d["ot"] = (d["J"] > 0).astype(float)
    d["asp"] = d["spread"].abs()
    return d


def main():
    d = build()
    dev, hold = d[d["date"] < SPLIT_DATE], d[d["date"] >= SPLIT_DATE]
    print(f"  {len(d):,} games   OT rate {100*d['ot'].mean():.2f}%   "
          f"development {len(dev):,}  holdout {len(hold):,}")

    print("\n" + "=" * 92)
    print("1 — IS P(OT) PREDICTABLE FROM THE SPREAD?")
    print("=" * 92)
    print(f"  {'|spread|':>12}{'n dev':>8}{'OT % dev':>10}{'n hold':>8}"
          f"{'OT % hold':>11}{'mechanical':>12}")
    sd_reg = 13.48          # regulation-residual sd, margin_shape.py
    att = 1.78              # end-game tie attractor, margin_shape.py
    for lo, hi in ((0, 2), (2, 4), (4, 6), (6, 8), (8, 11), (11, 99)):
        a = dev[(dev["asp"] >= lo) & (dev["asp"] < hi)]
        b = hold[(hold["asp"] >= lo) & (hold["asp"] < hi)]
        mid = np.clip((lo + min(hi, 20)) / 2, 0, None)
        mech = att * (norm.cdf((0.5 - mid) / sd_reg)
                      - norm.cdf((-0.5 - mid) / sd_reg))
        print(f"  {f'{lo}-{hi}':>12}{len(a):>8,}{100*a['ot'].mean():>10.2f}"
              f"{len(b):>8,}{100*b['ot'].mean():>11.2f}{100*mech:>12.2f}")

    X = np.column_stack([dev["asp"].values, dev["total"].values])
    b, se, t = ols(dev["ot"].values, X)
    print(f"\n  P(OT) ~ |spread| + total (development, linear):")
    print(f"    |spread| {b[1]:+.5f} (t={t[1]:+.2f})   "
          f"total {b[2]:+.6f} (t={t[2]:+.2f})")
    d["p_ot"] = np.clip(b[0] + b[1] * d["asp"] + b[2] * d["total"],
                        0.005, 0.20)
    for lab, x in (("development", d[d["date"] < SPLIT_DATE]),
                   ("holdout", d[d["date"] >= SPLIT_DATE])):
        q = pd.qcut(x["p_ot"], 4, labels=False, duplicates="drop")
        rates = [100 * x[q == k]["ot"].mean() for k in sorted(set(q))]
        pred = [100 * x[q == k]["p_ot"].mean() for k in sorted(set(q))]
        print(f"  {lab:12} predicted " +
              " ".join(f"{p:5.2f}" for p in pred) +
              "   realized " + " ".join(f"{r:5.2f}" for r in rates))

    print("\n" + "=" * 92)
    print("2 — DOES THE SHAPE CORRECTION SCALE WITH P(OT)?")
    print("=" * 92)
    Js = dev.loc[dev["ot"] == 1, "J"].values
    EJ, VJ = Js.mean(), Js.var(ddof=1)
    sd_tot = dev["e"].std()
    print(f"  OT points added: mean {EJ:.2f}  sd {np.sqrt(VJ):.2f}   "
          f"total residual sd {sd_tot:.2f}")

    def atm_gap(p):
        """Gaussian-minus-mixture probability at the money, same mean/variance."""
        m0 = -p * EJ
        s2 = sd_tot ** 2 - p * (1 - p) * EJ ** 2 - p * VJ
        s0 = np.sqrt(max(s2, 1.0))
        mix = (1 - p) * (1 - norm.cdf((0 - m0) / s0)) \
            + p * np.mean(1 - norm.cdf((0 - m0 - Js) / s0))
        return (1 - norm.cdf(0.0)) - mix          # gauss - mixture

    print(f"\n  {'p_OT':>8}{'ATM Yes overpricing (pp)':>28}")
    for p in (0.02, 0.035, 0.0524, 0.07, 0.09):
        print(f"  {100*p:>7.2f}%{100*atm_gap(p):>28.2f}")
    print("\n  by |spread| bucket, using the fitted p_OT:")
    print(f"  {'|spread|':>12}{'n':>8}{'mean p_OT':>11}"
          f"{'ATM tilt (pp)':>15}")
    for lo, hi in ((0, 3), (3, 6), (6, 9), (9, 99)):
        s = d[(d["asp"] >= lo) & (d["asp"] < hi)]
        pm = s["p_ot"].mean()
        print(f"  {f'{lo}-{hi}':>12}{len(s):>8,}{100*pm:>10.2f}%"
              f"{100*atm_gap(pm):>15.2f}")

    print("\n" + "=" * 92)
    print("3 — KXNBAOVERTIME: sizing a direct OT market against a flat quote")
    print("=" * 92)
    flat = d["ot"].mean()
    print(f"  a flat quote would sit near the base rate: {100*flat:.2f}%")
    print(f"  {'|spread|':>12}{'n':>8}{'true OT %':>11}{'edge vs flat':>14}"
          f"{'side':>7}{'ROI/fill %':>12}")
    for lo, hi in ((0, 3), (3, 6), (6, 9), (9, 99)):
        s = hold[(hold["asp"] >= lo) & (hold["asp"] < hi)]
        if len(s) < 30:
            continue
        true = s["ot"].mean()
        edge = true - flat
        # buy Yes at flat+1c ask if true > flat; else sell Yes at flat-1c bid
        if edge > 0:
            cost = flat + 0.01 + 0.25 * FEE_K * flat * (1 - flat)
            roi = (true - cost) / cost
            side = "BUY"
        else:
            coll = flat - 0.01 - 0.25 * FEE_K * flat * (1 - flat)
            roi = (coll - true) / (1 - coll)
            side = "SELL"
        print(f"  {f'{lo}-{hi}':>12}{len(s):>8,}{100*true:>10.2f}%"
              f"{100*edge:>+13.2f}pp{side:>7}{100*roi:>12.1f}")
    print("\n  [holdout rates, 1c spread assumed, maker fee. A flat-quoted OT")
    print("   market is the assumption being sized -- it has never been")
    print("   observed, since KXNBAOVERTIME has zero volume.]")


if __name__ == "__main__":
    main()
