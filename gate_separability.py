"""G4c — Conditional separability.

Unconditional bias and conditional separability are DIFFERENT ways through the
gate. A market can price correctly on average and still misprice systematically
in the cross-section. G2/G2' only see the first.

Question: does a small, economically motivated, WALK-FORWARD model create
stable dispersion in realised win rate when games are sorted by predicted edge?

    want:  lowest 20% -> 46%,  ...,  highest 20% -> 56%     (separable)
    null:  lowest 20% -> 49.7%, ..., highest 20% -> 50.3%    (nothing there)

⚠ WHY THIS MUST BE WALK-FORWARD, AND WHY THE NULL MATTERS
The prior project produced exactly the attractive table above IN DEVELOPMENT --
win rate rose monotonically 50.0% -> 55.4% with model confidence -- and in
holdout it peaked early and REVERSED, 54.4% -> 50.1%. Direction generalised;
the ranking did not. An in-sample bucket table is worthless here.

Two further controls:
  * The statistic is the SPREAD (top bucket - bottom bucket), not any single
    bucket. The top bucket is an extreme order statistic and will look good by
    construction.
  * The permutation preserves SEASON and MARKET-PRICE strata. A naive shuffle
    breaks the price structure and inflates apparent separability, because
    predicted edge correlates with the line itself.

Passing G4c requires all three:
  1. spread > 95th percentile of the stratified permutation null
  2. the top bucket clears break-even at an obtainable price
  3. the top bucket's edge clears the G6 minimum-viable-edge floor
"""
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline

N_BUCKETS = 5
MIN_TRAIN = 1200
REFIT_EVERY = 250
N_PERM = 2000


def walk_forward(g, feats, target, min_train=MIN_TRAIN, refit=REFIT_EVERY):
    """Expanding-window walk-forward probabilities. No future information."""
    g = g.sort_values("date").reset_index(drop=True)
    X = g[feats].values
    y = g[target].values.astype(int)
    out = np.full(len(g), np.nan)
    i = min_train
    while i < len(g):
        j = min(i + refit, len(g))
        m = make_pipeline(StandardScaler(),
                          LogisticRegression(C=0.1, max_iter=2000))
        m.fit(X[:i], y[:i])
        out[i:j] = m.predict_proba(X[i:j])[:, 1]
        i = j
    g["p_hat"] = out
    return g.dropna(subset=["p_hat"])


def bucket_table(d, p_col="p_hat", y_col="won", n=N_BUCKETS):
    d = d.copy()
    d["bucket"] = pd.qcut(d[p_col], n, labels=[f"Q{i+1}" for i in range(n)],
                          duplicates="drop")
    t = d.groupby("bucket", observed=True).agg(
        games=(y_col, "size"),
        pred=(p_col, "mean"),
        actual=(y_col, "mean"),
    )
    t["pred %"] = (100 * t.pred).round(2)
    t["actual %"] = (100 * t.actual).round(2)
    t["se pp"] = (100 * np.sqrt(t.actual * (1 - t.actual) / t.games)).round(2)
    return t[["games", "pred %", "actual %", "se pp"]]


def spread_stat(d, p_col="p_hat", y_col="won", n=N_BUCKETS, fair_col=None):
    """Top-bucket minus bottom-bucket.

    On a fixed-price market (totals, spreads) the raw realised rate is the
    right quantity. On a MONEYLINE it is not: sorting by predicted edge is
    confounded with the price level, because a large predicted edge tends to
    sit on longshots. Measured on NCAAB, sorting by `ehat` put fair-34% road
    favourites in the top bucket and produced a raw spread of -34.83pp that
    says nothing about skill. Pass `fair_col` for moneylines and the statistic
    becomes the CALIBRATION DEVIATION (realised - fair), which is price-neutral.
    """
    b = pd.qcut(d[p_col], n, labels=False, duplicates="drop")
    if fair_col is None:
        hi = d.loc[b == b.max(), y_col].mean()
        lo = d.loc[b == b.min(), y_col].mean()
    else:
        hi = (d.loc[b == b.max(), y_col] - d.loc[b == b.max(), fair_col]).mean()
        lo = (d.loc[b == b.min(), y_col] - d.loc[b == b.min(), fair_col]).mean()
    return hi - lo


def stratified_perm(d, strata_cols, p_col="p_hat", y_col="won",
                    n=N_BUCKETS, n_perm=N_PERM, seed=0):
    """Null: shuffle outcomes WITHIN season x price strata."""
    rng = np.random.default_rng(seed)
    obs = spread_stat(d, p_col, y_col, n)
    key = d[strata_cols].astype(str).agg("|".join, axis=1).values
    y = d[y_col].values.copy()
    idx_by = {k: np.where(key == k)[0] for k in np.unique(key)}
    null = np.empty(n_perm)
    tmp = d.copy()
    for t in range(n_perm):
        ysh = y.copy()
        for k, idx in idx_by.items():
            ysh[idx] = y[rng.permutation(idx)]
        tmp[y_col] = ysh
        null[t] = spread_stat(tmp, p_col, y_col, n)
    return obs, null


def report(d, label, break_even, floor_pp, strata_cols, seed=0):
    print("\n" + "=" * 78)
    print(f"G4c — CONDITIONAL SEPARABILITY: {label}")
    print("=" * 78)
    t = bucket_table(d)
    print(t.to_string())

    obs, null = stratified_perm(d, strata_cols, seed=seed)
    pct = 100 * (null < obs).mean()
    print(f"\n  spread (top - bottom) = {100*obs:+.2f}pp")
    print(f"  stratified permutation null: mean {100*null.mean():+.2f}pp, "
          f"95th pct {100*np.quantile(null,0.95):+.2f}pp")
    print(f"  observed sits at the {pct:.1f}th percentile   "
          f"[{'PASS' if pct > 95 else 'FAIL'}]")

    top = t.iloc[-1]
    edge = top["actual %"] - 100 * break_even
    print(f"\n  top bucket: {top['actual %']:.2f}% on {int(top['games'])} games "
          f"(se {top['se pp']:.2f}pp)")
    print(f"    vs break-even {100*break_even:.2f}%  ->  edge {edge:+.2f}pp   "
          f"[{'PASS' if edge > 0 else 'FAIL'}]")
    print(f"    vs G6 floor {floor_pp:.2f}pp                 "
          f"[{'PASS' if edge > floor_pp else 'FAIL'}]")

    monot = t["actual %"].is_monotonic_increasing
    print(f"\n  monotone across buckets: {monot}")
    ok = pct > 95 and edge > floor_pp
    print(f"\n  G4c VERDICT: {'PASS' if ok else 'FAIL'}")
    return ok
