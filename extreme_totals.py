"""Do extreme totals pay off? Testing the "3 SD" claim.

Claim: when a total sits far from the season's typical total, neither side pays.

Two readings, both testable and distinguishable:

  A. EFFICIENCY  -- at extremes the market is well priced, over% sits near 50%,
                    and both sides therefore lose to the vig. "Neither pays"
                    is literally true only in this sense, since over% and under%
                    must sum to 100.
  B. REVERSION   -- extremes do not persist: very high totals come in UNDER,
                    very low totals come in OVER. Here one side DOES pay, and
                    the claim would mean "do not bet the extreme to continue".

Both are reported. They imply opposite trades, so separating them matters.

The season mean and sd are computed WALK-FORWARD (season-to-date, expanding,
minimum 100 games) rather than from the full season. Using the finished season's
statistics would leak: you cannot know in November what November's total looks
like relative to a season that has not happened yet.
"""
import warnings

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")

import data_split as ds
from prepare_data import CSV, season_label

MIN_N = 100


def build():
    raw = pd.read_csv(CSV, low_memory=False)
    raw["season"] = season_label(raw).astype(str)
    d = raw[raw["season"].str.contains("Regular Season", na=False)].copy()
    d["date"] = pd.to_datetime(d["DATE"], errors="coerce")
    d["close"] = pd.to_numeric(d["CLOSING TOTAL_H"], errors="coerce")
    d["open"] = pd.to_numeric(d["OPENING TOTAL_H"], errors="coerce")
    d["actual"] = d["PTS_H"] + d["PTS_R"]
    d = d.dropna(subset=["close", "actual", "date"]).sort_values("date")
    d = d[d["close"].between(150, 300)].reset_index(drop=True)

    # season-to-date mean and sd of the CLOSING total, strictly prior games
    out = []
    for s, sub in d.groupby("season", sort=False):
        sub = sub.sort_values("date").copy()
        mu = sub["close"].expanding().mean().shift(1)
        sd = sub["close"].expanding().std().shift(1)
        cnt = np.arange(len(sub))
        sub["mu"], sub["sd"], sub["prior_n"] = mu.values, sd.values, cnt
        out.append(sub)
    d = pd.concat(out, ignore_index=True)
    d = d[d["prior_n"] >= MIN_N].copy()
    d["z"] = (d["close"] - d["mu"]) / d["sd"]
    d["resid"] = d["actual"] - d["close"]
    d = d[d["actual"] != d["close"]]        # drop exact pushes
    return ds.tag(d)


def metrics(sub):
    ov = (sub["resid"] > 0).mean()
    n = len(sub)
    se = np.sqrt(ov * (1 - ov) / n) if n else np.nan
    return {"n": n, "mean z": round(sub["z"].mean(), 2),
            "actual-close": round(sub["resid"].mean(), 3),
            "over %": round(100 * ov, 2),
            "over lo": round(100 * (ov - 1.96 * se), 2),
            "over hi": round(100 * (ov + 1.96 * se), 2),
            "ROI over %": round(100 * (ov * (100 / 110) - (1 - ov)), 2),
            "ROI under %": round(100 * ((1 - ov) * (100 / 110) - ov), 2)}


def main():
    d = build()
    print(f"{len(d):,} games with a season-to-date baseline "
          f"({d['date'].min().date()} .. {d['date'].max().date()})")
    print(f"z: mean {d['z'].mean():+.3f}  sd {d['z'].std():.3f}\n")

    print("=" * 108)
    print("How rare are extremes? (walk-forward z)")
    print("=" * 108)
    for t in (1.0, 1.5, 2.0, 2.5, 3.0):
        n = int((d["z"].abs() >= t).sum())
        print(f"  |z| >= {t:<4}  n = {n:5,}  ({100*n/len(d):5.2f}% of games, "
              f"~{n/8:.0f} per season)")

    print("\n" + "=" * 108)
    print("Signed z bands — is it EFFICIENCY (over% ~50) or REVERSION?")
    print("=" * 108)
    bins = [-np.inf, -2, -1.5, -1, -0.5, 0.5, 1, 1.5, 2, np.inf]
    lab = ["z<-2", "-2..-1.5", "-1.5..-1", "-1..-0.5", "-0.5..0.5",
           "0.5..1", "1..1.5", "1.5..2", "z>2"]
    d["band"] = pd.cut(d["z"], bins, labels=lab)
    rows = []
    for g, sub in d.groupby("band", observed=True):
        rows.append({"band": g, **metrics(sub)})
    print(pd.DataFrame(rows).to_string(index=False))

    print("\n" + "=" * 108)
    print("Absolute extremes, and split by development / holdout")
    print("=" * 108)
    for t in (2.0, 2.5, 3.0):
        sub = d[d["z"].abs() >= t]
        rows = []
        for lbl, s in (("DEV", sub[~sub["is_holdout"]]),
                       ("HOLDOUT", sub[sub["is_holdout"]]),
                       ("pooled", sub)):
            if len(s) >= 25:
                rows.append({"set": lbl, **metrics(s)})
        print(f"\n--- |z| >= {t} ---")
        print(pd.DataFrame(rows).to_string(index=False) if rows
              else "  too few games to say anything")

    print("\n" + "=" * 108)
    print("The two tails separately, |z| >= 2 (reversion would make these differ)")
    print("=" * 108)
    rows = []
    for lbl, s in (("HIGH totals  z >= +2", d[d["z"] >= 2]),
                   ("LOW  totals  z <= -2", d[d["z"] <= -2]),
                   ("HIGH  z >= +1.5", d[d["z"] >= 1.5]),
                   ("LOW   z <= -1.5", d[d["z"] <= -1.5])):
        if len(s) >= 25:
            t, p = stats.ttest_1samp(s["resid"], 0.0)
            rows.append({"tail": lbl, **metrics(s), "t": round(t, 2),
                         "p": round(p, 3)})
    print(pd.DataFrame(rows).to_string(index=False))

    print("\n" + "=" * 108)
    print("Does |z| predict anything at all? (regression on the residual)")
    print("=" * 108)
    X = np.c_[np.ones(len(d)), d["z"], d["z"].abs()]
    beta, *_ = np.linalg.lstsq(X, d["resid"].values, rcond=None)
    yhat = X @ beta
    r = np.corrcoef(yhat, d["resid"])[0, 1]
    print(f"  resid ~ 1 + z + |z|   coefficients: intercept {beta[0]:+.3f}, "
          f"z {beta[1]:+.3f}, |z| {beta[2]:+.3f}")
    print(f"  multiple correlation with the outcome: {r:.4f}  (R^2 {r*r:.5f})")


if __name__ == "__main__":
    main()
