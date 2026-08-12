"""Can we detect a missing priced variable without being able to name it?

If the closing line is optimal, its residual must be unpredictable from ANY
function of information available before tip-off. That converts an unbounded
search ("what variable is the market missing?") into a set of bounded tests for
STRUCTURE, each of which can fire without identifying the cause.

Six tests, each sensitive to a different signature of an omitted variable:

  1 MINCER-ZARNOWITZ   actual ~ a + b*line. Optimality requires (a,b)=(0,1).
                       b<1 means the line is too dispersed -- it overreacts to
                       its own inputs; b>1 means too compressed. Detects
                       miscalibrated USE of information already held.

  2 SERIAL CORRELATION Residuals for the same team in consecutive games. A
                       persistent unobserved team attribute -- a systematic
                       misvaluation the market has not learned -- induces
                       positive autocorrelation. Detects PERSISTENT omissions.

  3 VARIANCE COMPONENTS Between-group vs within-group residual variance, over
                       several groupings. Any grouping where between exceeds
                       permutation indicates information shared within the group
                       and absent from the line. Detects CLUSTERED omissions.

  4 MIXTURE STRUCTURE  If an unobserved BINARY state shifts scoring in some
                       games, residuals are a two-component mixture rather than
                       one distribution. Compared by BIC, plus excess kurtosis.
                       Detects STATE-DEPENDENT omissions the other tests miss,
                       because a mixture with equal weights has zero mean shift.

  5 CONDITIONAL VARIANCE Is |residual| predictable from the line? Optimality
                       does not require homoskedasticity, but predictable
                       variance is exploitable in derivative markets and
                       indicates the line does not carry its own uncertainty.

  6 SIGN RUNS          Wald-Wolfowitz runs test on the residual sign sequence
                       within team. Detects regime structure invisible to
                       correlation.

⚠ POWER IS THE LIMIT. Each test states the smallest effect it could have found.
A null here means "no structure above this size", never "the line is optimal".
"""
import warnings

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")
RNG = np.random.default_rng(0)


def load():
    from prepare_data import CSV, season_label
    raw = pd.read_csv(CSV, low_memory=False)
    raw["season"] = season_label(raw).astype(str)
    d = raw[raw["season"].str.contains("Regular Season", na=False)].copy()
    d["date"] = pd.to_datetime(d["DATE"], errors="coerce")
    d["close_total"] = pd.to_numeric(d["CLOSING TOTAL_H"], errors="coerce")
    d["close_spread"] = pd.to_numeric(d["CLOSING SPREAD_H"], errors="coerce")
    d["actual_total"] = d["PTS_H"] + d["PTS_R"]
    d["actual_margin"] = d["PTS_H"] - d["PTS_R"]
    d = d.dropna(subset=["close_total", "close_spread", "date", "actual_total"])
    d = d[d["close_total"].between(150, 300)]
    d["r_total"] = d["actual_total"] - d["close_total"]
    d["r_spread"] = d["actual_margin"] + d["close_spread"]
    return d.sort_values("date").reset_index(drop=True)


def mincer_zarnowitz(y, x, label):
    X = np.c_[np.ones(len(x)), x]
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    s2 = (resid ** 2).sum() / (len(y) - 2)
    cov = s2 * np.linalg.pinv(X.T @ X)
    se = np.sqrt(np.diag(cov))
    # joint Wald test of (a,b) = (0,1)
    diff = beta - np.array([0.0, 1.0])
    W = diff @ np.linalg.pinv(cov) @ diff
    p = 1 - stats.chi2.cdf(W, 2)
    print(f"  {label}")
    print(f"    intercept {beta[0]:+.4f} (se {se[0]:.4f})   "
          f"slope {beta[1]:+.5f} (se {se[1]:.5f})")
    print(f"    joint Wald vs (0,1): chi2={W:.2f}  p={p:.4f}"
          f"   {'<-- REJECTS optimality' if p < 0.05 else 'consistent with optimality'}")
    print(f"    smallest detectable slope deviation (80% power): "
          f"{2.8*se[1]:.5f}")
    return beta, se


def main():
    d = load()
    print(f"{len(d):,} games  {d['date'].min().date()} .. {d['date'].max().date()}\n")

    print("=" * 92)
    print("1. MINCER-ZARNOWITZ — is the line's own use of information calibrated?")
    print("=" * 92)
    mincer_zarnowitz(d["actual_total"].values, d["close_total"].values,
                     "TOTALS: actual_total ~ a + b*close_total")
    print()
    mincer_zarnowitz(d["actual_margin"].values, -d["close_spread"].values,
                     "SIDES: actual_margin ~ a + b*(-close_spread)")

    # long format: one row per team-game
    h = d[["date", "season", "TEAM_H", "r_total", "r_spread"]].copy()
    h.columns = ["date", "season", "team", "r_total", "r_spread"]
    a = d[["date", "season", "TEAM_R", "r_total", "r_spread"]].copy()
    a.columns = ["date", "season", "team", "r_total", "r_spread"]
    a["r_spread"] = -a["r_spread"]
    L = pd.concat([h, a]).sort_values(["season", "team", "date"])

    print("\n" + "=" * 92)
    print("2. SERIAL CORRELATION — persistent team-level misvaluation")
    print("=" * 92)
    for col in ("r_total", "r_spread"):
        L["lag"] = L.groupby(["season", "team"])[col].shift(1)
        s = L.dropna(subset=["lag"])
        r = np.corrcoef(s[col], s["lag"])[0, 1]
        se = 1 / np.sqrt(len(s))
        print(f"  {col}: lag-1 corr {r:+.4f}  (n={len(s):,}, se {se:.4f}, "
              f"t={r/se:+.2f})   detectable at |r| > {2.8*se:.4f}")

    print("\n" + "=" * 92)
    print("3. VARIANCE COMPONENTS — information shared within a group")
    print("=" * 92)
    for col in ("r_total", "r_spread"):
        for gname, keys in (("team", ["team"]), ("team-season", ["season", "team"]),
                            ("month", [L["date"].dt.to_period("M")])):
            g = L.groupby(keys)[col]
            obs = g.mean().std()
            sizes = g.size().values
            vals = L[col].values
            null = []
            for _ in range(600):
                p = RNG.permutation(vals)
                idx, m = 0, []
                for n in sizes:
                    m.append(p[idx:idx + n].mean())
                    idx += n
                null.append(np.std(m))
            null = np.array(null)
            gl = gname if isinstance(gname, str) else "month"
            flag = "<-- above null" if obs > np.percentile(null, 95) else ""
            print(f"  {col:9} by {gl:12} sd of group means {obs:.4f}   "
                  f"null {null.mean():.4f}±{null.std():.4f}   "
                  f"pct {100*np.mean(null < obs):5.1f}  {flag}")

    print("\n" + "=" * 92)
    print("4. MIXTURE STRUCTURE — an unobserved binary state")
    print("=" * 92)
    from sklearn.mixture import GaussianMixture
    for col in ("r_total", "r_spread"):
        x = d[col].values.reshape(-1, 1)
        b1 = GaussianMixture(1, random_state=0).fit(x).bic(x)
        b2 = GaussianMixture(2, random_state=0).fit(x).bic(x)
        k = stats.kurtosis(x.ravel())
        z, pk = stats.kurtosistest(x.ravel())
        print(f"  {col}: BIC 1-comp {b1:,.0f}  2-comp {b2:,.0f}  "
              f"delta {b2-b1:+,.0f} {'<-- mixture preferred' if b2 < b1 else ''}")
        print(f"           excess kurtosis {k:+.4f}  (test z={z:+.2f}, p={pk:.4f})")

    print("\n" + "=" * 92)
    print("5. CONDITIONAL VARIANCE — is |residual| predictable?")
    print("=" * 92)
    for col, pred in (("r_total", "close_total"), ("r_spread", "close_spread")):
        y = d[col].abs().values
        x = d[pred].abs().values if col == "r_spread" else d[pred].values
        X = np.c_[np.ones(len(x)), x]
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        r = np.corrcoef(x, y)[0, 1]
        print(f"  |{col}| ~ {pred}: slope {beta[1]:+.5f}  corr {r:+.4f}  "
              f"t={r*np.sqrt(len(y)-2)/np.sqrt(1-r*r):+.2f}")

    print("\n" + "=" * 92)
    print("6. SIGN RUNS — regime structure within team sequences")
    print("=" * 92)
    for col in ("r_total", "r_spread"):
        zs = []
        for _, g in L.groupby(["season", "team"]):
            s = np.sign(g[col].values)
            s = s[s != 0]
            if len(s) < 20:
                continue
            runs = 1 + (s[1:] != s[:-1]).sum()
            n1, n2 = (s > 0).sum(), (s < 0).sum()
            if n1 == 0 or n2 == 0:
                continue
            mu = 2 * n1 * n2 / (n1 + n2) + 1
            var = (mu - 1) * (mu - 2) / (n1 + n2 - 1)
            zs.append((runs - mu) / np.sqrt(var))
        zs = np.array(zs)
        print(f"  {col}: mean runs z {zs.mean():+.4f} over {len(zs)} team-seasons "
              f"(se {zs.std()/np.sqrt(len(zs)):.4f}, "
              f"t={zs.mean()/(zs.std()/np.sqrt(len(zs))):+.2f})")


if __name__ == "__main__":
    main()
