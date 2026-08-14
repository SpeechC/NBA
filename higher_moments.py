"""Higher moments: variance, skew, tails and cross-outcome correlation.

Generic variance modelling failed and conditional variance around three discrete
states failed. This tests the moments we have NOT examined, each with a market
test attached where one exists.

M1 VARIANCE ~ TOTAL LEVEL.  Untested. We showed margin variance rises with
   |spread| (t = 5.59) and that the moneyline prices it. But a high-total game
   has more possessions, so it should also carry more margin variance. If the
   book maps spread -> moneyline without conditioning on the TOTAL, that is a
   distributional error in an observable transformation.
     Stage 1: (margin+spread)^2 ~ total
     Stage 2: moneyline error ~ total, and ~ total controlling for |spread|

M2 SKEW.  Is the margin residual skewed, and does the skew vary with the spread?
   A normal-based spread->moneyline map assumes symmetry; if big favourites have
   an asymmetric margin distribution, their moneyline is systematically off even
   with the right variance.

M3 CORRELATED OUTCOMES.  corr(total residual, |margin| residual). Same-game
   parlays and derived markets price these jointly; if high-scoring games are
   systematically also blowouts (or the reverse), any product treating them as
   independent is mispriced. No SGP data here, so this is measurement only.

M4 TAILS.  Compare realised tail frequencies against the normal implied by each
   game's own moments. Fat tails in the margin mean big favourites lose outright
   more often than a Gaussian map implies -- directly a moneyline question.

Stage 1 requires a coefficient AND monotone buckets. Stage 2 is the moneyline,
the only distributional instrument in this dataset.
"""
import warnings

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")


def load():
    from prepare_data import CSV, season_label
    raw = pd.read_csv(CSV, low_memory=False)
    raw["lbl"] = season_label(raw).astype(str)
    d = raw[raw["lbl"].str.contains("Regular Season", na=False)].copy()
    n = lambda c: pd.to_numeric(d[c], errors="coerce")
    d["spread"] = n("CLOSING SPREAD_H")
    d["total"] = n("CLOSING TOTAL_H")
    d["mlh"], d["mla"] = n("MONEYLINE_H"), n("MONEYLINE_R")
    d["margin"] = d["PTS_H"] - d["PTS_R"]
    d["actual"] = d["PTS_H"] + d["PTS_R"]
    d = d.dropna(subset=["spread", "total", "mlh", "mla"])
    d = d[d["total"].between(150, 300)].copy()
    d["ats"] = d["margin"] + d["spread"]
    d["tot_r"] = d["actual"] - d["total"]
    d["abs_spread"] = d["spread"].abs()
    ph = np.where(d["mlh"] < 0, -d["mlh"] / (-d["mlh"] + 100),
                  100 / (d["mlh"] + 100))
    pa = np.where(d["mla"] < 0, -d["mla"] / (-d["mla"] + 100),
                  100 / (d["mla"] + 100))
    d["p_home"] = ph / (ph + pa)
    d = d[(d["p_home"] > 0.03) & (d["p_home"] < 0.97)].copy()
    d["p_fav"] = np.where(d["spread"] < 0, d["p_home"], 1 - d["p_home"])
    d["fav_won"] = np.where(d["spread"] < 0, d["margin"] > 0, d["margin"] < 0)
    d["ml_err"] = d["fav_won"].astype(float) - d["p_fav"]
    return d


def tstat(x, y):
    r = np.corrcoef(x, y)[0, 1]
    return r, r * np.sqrt(len(x) - 2) / np.sqrt(1 - r * r)


def main():
    d = load()
    print(f"{len(d):,} games\n")

    print("=" * 96)
    print("M1 — does the TOTAL predict margin variance, and is it priced?")
    print("=" * 96)
    r, t = tstat(d["total"], d["ats"] ** 2)
    print(f"  STAGE 1  (margin+spread)^2 ~ total     corr {r:+.4f}  t={t:+.2f}")
    d["tq"] = pd.qcut(d["total"], 5, labels=[1, 2, 3, 4, 5])
    print("    quintiles of total: " + "  ".join(
        f"Q{i} tot {g['total'].mean():.0f} sd(ats) {g['ats'].std():5.2f}"
        for i, g in d.groupby("tq", observed=True)))
    r2, t2 = tstat(d["total"], d["ml_err"])
    print(f"\n  STAGE 2  moneyline error ~ total       corr {r2:+.4f}  t={t2:+.2f}")
    print("    quintiles: " + "  ".join(
        f"Q{i} MLerr {100*g['ml_err'].mean():+5.2f}pp"
        for i, g in d.groupby("tq", observed=True)))
    # does total add anything beyond |spread|?
    X = np.column_stack([np.ones(len(d)), d["abs_spread"], d["total"]])
    beta, *_ = np.linalg.lstsq(X, (d["ats"] ** 2).values, rcond=None)
    res = (d["ats"] ** 2).values - X @ beta
    s2 = (res ** 2).sum() / (len(d) - 3)
    se = np.sqrt(np.diag(np.linalg.pinv(X.T @ X)) * s2)
    print(f"\n  variance regression: |spread| {beta[1]:+.3f} (t={beta[1]/se[1]:+.2f})"
          f"   total {beta[2]:+.3f} (t={beta[2]/se[2]:+.2f})")

    print("\n" + "=" * 96)
    print("M2 — skew of the margin, and does it vary with the spread?")
    print("=" * 96)
    print(f"  overall skew: ATS residual {stats.skew(d['ats']):+.4f}   "
          f"total residual {stats.skew(d['tot_r']):+.4f}")
    z, p = stats.skewtest(d["ats"])
    print(f"  skewtest on ATS: z={z:+.2f}  p={p:.4f}")
    d["sq"] = pd.qcut(d["abs_spread"], 5, labels=[1, 2, 3, 4, 5])
    print("    by |spread| quintile: " + "  ".join(
        f"Q{i} skew {stats.skew(g['ats']):+.3f}"
        for i, g in d.groupby("sq", observed=True)))

    print("\n" + "=" * 96)
    print("M3 — are total and margin outcomes correlated?")
    print("=" * 96)
    for a, b, lab in ((d["tot_r"], d["ats"].abs(), "total residual vs |ATS|"),
                      (d["tot_r"], d["margin"].abs(), "total residual vs |margin|"),
                      (d["tot_r"], d["ats"], "total residual vs signed ATS")):
        r, t = tstat(a, b)
        print(f"  {lab:32} corr {r:+.4f}  t={t:+.2f}")
    print("\n  a positive first row means high-scoring games are also blowouts;")
    print("  any product pricing total and margin independently would be wrong")

    print("\n" + "=" * 96)
    print("M4 — tails: does the favourite lose outright more than Gaussian?")
    print("=" * 96)
    sd = d["ats"].std()
    for k in (1.0, 1.5, 2.0, 2.5):
        emp = (d["ats"].abs() > k * sd).mean()
        theo = 2 * (1 - stats.norm.cdf(k))
        print(f"  |ATS| > {k}sd : empirical {100*emp:5.2f}%   normal "
              f"{100*theo:5.2f}%   ratio {emp/theo:.3f}")
    print(f"\n  excess kurtosis of ATS residual: {stats.kurtosis(d['ats']):+.4f}")
    # tail test where it matters: big favourites losing outright
    big = d[d["abs_spread"] >= 10]
    print(f"\n  |spread| >= 10 ({len(big):,} games): favourite implied "
          f"{100*big['p_fav'].mean():.2f}%  actual {100*big['fav_won'].mean():.2f}%"
          f"   gap {100*(big['fav_won'].mean()-big['p_fav'].mean()):+.2f}pp")
    big2 = d[d["abs_spread"] >= 14]
    print(f"  |spread| >= 14 ({len(big2):,} games): implied "
          f"{100*big2['p_fav'].mean():.2f}%  actual {100*big2['fav_won'].mean():.2f}%"
          f"   gap {100*(big2['fav_won'].mean()-big2['p_fav'].mean()):+.2f}pp")


if __name__ == "__main__":
    main()
