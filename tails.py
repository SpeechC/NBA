"""Are game totals fat-tailed relative to what the closing line implies?

Hypothesis: very low and very high scoring games occur more often than the totals
market prices, which would make alternate totals (and extreme over/unders)
mispriced.

The quantity to test is the RESIDUAL, actual total minus closing total -- not the
raw total. The market's job is to centre each game; whether the *level* is right
is a different question from whether the *spread of outcomes* around it is right.

Three decompositions, because "fat tails" has three possible causes and only one
of them is exploitable:

  1. OVERTIME. Mechanically fat on the right: an overtime adds ~24 points. This is
     real but fully known to the market, so it is separated out by measuring
     regulation-only totals alongside full-game totals.

  2. MIXTURE. If different games have genuinely different variances (a fast
     shootout is more variable in absolute points than a slow grind), then pooling
     them produces excess kurtosis even when every individual game is perfectly
     normal. A single-sigma pricing ladder would then be wrong -- but the fix is
     conditional variance, not a fat-tailed distribution. Tested by modelling
     sigma as a function of the closing total and re-checking kurtosis after
     standardising.

  3. GENUINELY FAT CONDITIONAL TAILS. What is left after 1 and 2. This is the only
     version that implies the market's *shape* is wrong.

Note on the benchmark: we have no alternate-total prices, so "what the market
predicts" is proxied by a normal distribution with the empirically observed sigma.
That is the standard first approximation and roughly what a linear alternate-total
ladder assumes, but it is an assumption, not an observation of book pricing.
"""

import numpy as np
import pandas as pd
from scipy import stats

ODDS = "/home/dpope/data/dfMaster_OT.parquet"


def load():
    o = pd.read_parquet(ODDS)
    o["season"] = o["DATASET_H"].fillna(o["BIGDATABALL\nDATASET_H"])
    r = o[o["season"].str.contains("Regular Season|In-Season", na=False)].copy()

    q = [f"{i}Q_{s}" for i in (1, 2, 3, 4) for s in ("H", "R")]
    for c in q:
        r[c] = pd.to_numeric(r[c], errors="coerce")
    r["reg_total"] = r[q].sum(axis=1)

    ot_cols = [f"OT{i}_{s}" for i in range(1, 6) for s in ("H", "R")]
    r["ot_pts"] = sum(pd.to_numeric(r[c], errors="coerce").fillna(0) for c in ot_cols)
    r["full_total"] = r["reg_total"] + r["ot_pts"]
    r["is_ot"] = r["OT1_H"].notna()
    r["close"] = pd.to_numeric(r["CLOSING TOTAL_H"], errors="coerce")
    r = r[r["close"].between(150, 300)]
    return r.dropna(subset=["reg_total", "close"])


def moments(x, label):
    x = np.asarray(x, dtype=float)
    n = len(x)
    return {
        "series": label, "n": n, "mean": x.mean(), "sd": x.std(ddof=1),
        "skew": stats.skew(x), "excess kurtosis": stats.kurtosis(x),
        "JB p": stats.jarque_bera(x).pvalue,
    }


def tail_table(x, label):
    """Empirical vs normal tail frequencies, both directions."""
    x = np.asarray(x, dtype=float)
    z = (x - x.mean()) / x.std(ddof=1)
    rows = []
    for k in (1.0, 1.5, 2.0, 2.5, 3.0):
        emp_hi = float((z > k).mean())
        emp_lo = float((z < -k).mean())
        nrm = float(1 - stats.norm.cdf(k))
        rows.append({"series": label, "z": k,
                     "empirical over %": 100 * emp_hi,
                     "empirical under %": 100 * emp_lo,
                     "normal %": 100 * nrm,
                     "over ratio": emp_hi / nrm if nrm else np.nan,
                     "under ratio": emp_lo / nrm if nrm else np.nan})
    return pd.DataFrame(rows)


def main():
    r = load()
    r["resid_full"] = r["full_total"] - r["close"]
    r["resid_reg"] = r["reg_total"] - r["close"]
    reg_only = r[~r["is_ot"]]

    print(f"games {len(r):,}   overtime {r['is_ot'].sum():,} ({100 * r['is_ot'].mean():.2f}%)\n")

    print("=== 1. MOMENTS OF THE RESIDUAL ===")
    m = pd.DataFrame([
        moments(r["resid_full"], "full total (incl OT) - close"),
        moments(r["resid_reg"], "regulation total - close"),
        moments(reg_only["resid_full"], "non-OT games only"),
    ])
    print(m.round(4).to_string(index=False))
    print("\n(excess kurtosis 0 = normal; >0 = fat tails; JB p < 0.05 rejects normality)\n")

    print("=== 2. TAIL FREQUENCIES vs NORMAL ===")
    t = pd.concat([
        tail_table(r["resid_full"], "full (incl OT)"),
        tail_table(reg_only["resid_full"], "non-OT games"),
    ])
    print(t.round(3).to_string(index=False))
    print("\n(ratio > 1 means the tail is fatter than normal at that distance)\n")

    print("=== 3. IS IT A MIXTURE? does sigma depend on the total? ===")
    r2 = r.copy()
    r2["bucket"] = pd.qcut(r2["close"], 5)
    b = r2.groupby("bucket", observed=True)["resid_full"].agg(["size", "mean", "std"])
    b["excess kurt"] = r2.groupby("bucket", observed=True)["resid_full"].apply(stats.kurtosis)
    print(b.round(3).to_string())

    # standardise by a fitted sigma(close) and re-test
    fit = np.polyfit(r2["close"], r2["resid_full"].abs(), 1)
    sigma_hat = np.polyval(fit, r2["close"]) * np.sqrt(np.pi / 2)
    z = r2["resid_full"] / sigma_hat
    print(f"\n  sigma modelled as linear in the closing total: "
          f"slope {fit[0]:+.4f} pts of sigma per point of total")
    print(f"  excess kurtosis BEFORE standardising: "
          f"{stats.kurtosis(r2['resid_full']):+.4f}")
    print(f"  excess kurtosis AFTER  standardising: {stats.kurtosis(z):+.4f}")

    print("\n=== 4. WHAT IT WOULD BE WORTH ===")
    print("Fair odds for an alternate total d points from the close, empirical vs normal:")
    x = r["resid_full"].to_numpy()
    sd = x.std(ddof=1)
    rows = []
    for d in (5, 10, 15, 20, 25):
        eo, eu = float((x > d).mean()), float((x < -d).mean())
        no = float(1 - stats.norm.cdf(d / sd))
        rows.append({"points from close": d,
                     "emp over %": 100 * eo, "normal over %": 100 * no,
                     "emp under %": 100 * eu,
                     "over edge pp": 100 * (eo - no),
                     "under edge pp": 100 * (eu - no)})
    print(pd.DataFrame(rows).round(3).to_string(index=False))
    print("\n(edge in percentage points; a book pricing off a normal would be wrong by this much)")


if __name__ == "__main__":
    main()
