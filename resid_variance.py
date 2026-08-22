"""Three follow-ups to opening_line_error_decomposition.py, per spec:

PART 1 — INCREMENTAL: is the error-only latent movement signal the SAME
  information as the frozen ridge move prediction (movement_full_games.csv,
  walk-forward pred_move), or incremental?
      Move = a + b1*ridge + b2*latent      on common OOS games.

PART 2 — CONDITIONAL VARIANCE: do residual-state histories predict the
  MAGNITUDE of the opening error?  Targets |e_open| and log(1+e^2), same
  error-only matrix, same season folds, PCA-OLS. Baselines: (a) constant,
  (b) LEVEL (open total + |open spread|) -- any residual-state claim must beat
  the trivial level predictor, which is already known to price dispersion.
  Deliverable: predicted-variance deciles vs realized dispersion, OOS.
  Context of record: this is the NINTH dispersion test in this project; the
  eighth (matchup_dist.py, which included scoring volatility) gave R^2=0.0007.

PART 3 — FROZEN KALSHI APPLICATION: the variance model is trained on the
  sportsbook 8 seasons only; 2025-26 Kalshi ladders are an untouched
  application sample. Does predicted dispersion identify ladders whose implied
  sd is too narrow / too wide?  Metric: sd(z), z=(actual-mu)/sd_implied, by
  predicted-dispersion decile; calibrated pricing => sd(z)=1 in every decile.
"""
import warnings

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")

from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

import opening_line_error_decomposition as OLE

EV_THRESH = 0.80
RNG = 20260827


def folds(X):
    seasons = sorted(X["season"].unique())
    for i in range(2, len(seasons)):
        yield (X["season"] < seasons[i]).values, \
              (X["season"] == seasons[i]).values


def pca_oos(X, featcols, targets):
    preds = {t: np.full(len(X), np.nan) for t in targets}
    for tr, te in folds(X):
        sc = StandardScaler().fit(X.loc[tr, featcols])
        Ztr, Zte = sc.transform(X.loc[tr, featcols]), \
            sc.transform(X.loc[te, featcols])
        p = PCA(n_components=min(30, Ztr.shape[1])).fit(Ztr)
        K = int(np.searchsorted(np.cumsum(p.explained_variance_ratio_),
                                EV_THRESH) + 1)
        Str, Ste = p.transform(Ztr)[:, :K], p.transform(Zte)[:, :K]
        for t in targets:
            A = np.column_stack([np.ones(Str.shape[0]), Str])
            b, *_ = np.linalg.lstsq(A, X.loc[tr, t].values, rcond=None)
            preds[t][te] = np.column_stack(
                [np.ones(Ste.shape[0]), Ste]) @ b
    return preds


def lin_oos(X, cols, targets):
    preds = {t: np.full(len(X), np.nan) for t in targets}
    for tr, te in folds(X):
        for t in targets:
            A = np.column_stack([np.ones(tr.sum())] +
                                [X.loc[tr, c] for c in cols])
            b, *_ = np.linalg.lstsq(A, X.loc[tr, t].values, rcond=None)
            preds[t][te] = np.column_stack(
                [np.ones(te.sum())] + [X.loc[te, c] for c in cols]) @ b
    return preds


def main():
    g = OLE.load()
    X, featcols = OLE.design_matrix(g)
    X["abs_e"] = X["te_open"].abs()
    X["loge2"] = np.log1p(X["te_open"] ** 2)
    X["abs_sp"] = X["om_open"].abs()
    print(f"\n  {len(X):,} games, {len(featcols)} error-state features")

    # ---------------------------------------------------------- PART 1
    print("\n" + "=" * 92)
    print("PART 1 — RIDGE vs LATENT on open->close TOTAL movement")
    print("=" * 92)
    mv = pd.read_csv("movement_full_games.csv",
                     usecols=["game_id", "pred_move", "move_total", "clean"])
    mv["gid"] = mv["game_id"].astype(str).str.strip()
    mv = mv[mv["clean"] == True]
    lat = pca_oos(X, featcols, ["tmove"])["tmove"]
    ok = ~np.isnan(lat)
    D = X.loc[ok, ["gid", "tmove"]].copy()
    D["latent"] = lat[ok]
    D = D.merge(mv[["gid", "pred_move"]], on="gid", how="inner").dropna()
    print(f"  common OOS games: {len(D):,}   "
          f"(ridge folds: 7-day refits; latent folds: seasons -- both OOS)")
    for nm, cols in (("ridge alone", ["pred_move"]),
                     ("latent alone", ["latent"]),
                     ("BOTH", ["pred_move", "latent"])):
        A = np.column_stack([np.ones(len(D))] + [D[c] for c in cols])
        b, *_ = np.linalg.lstsq(A, D["tmove"], rcond=None)
        r = D["tmove"] - A @ b
        se = np.sqrt(np.diag(np.linalg.pinv(A.T @ A)) * (r @ r)
                     / (len(D) - A.shape[1]))
        r2 = 1 - r.var() / D["tmove"].var()
        s = "   ".join(f"{c} {b[i+1]:+.4f} (t={b[i+1]/se[i+1]:+.2f})"
                       for i, c in enumerate(cols))
        print(f"  {nm:14} R2 {r2:.4f}   {s}")
    print(f"  corr(ridge, latent predictions) = "
          f"{np.corrcoef(D['pred_move'], D['latent'])[0, 1]:+.4f}")

    # ---------------------------------------------------------- PART 2
    print("\n" + "=" * 92)
    print("PART 2 — CONDITIONAL VARIANCE of the opening error (9th "
          "dispersion test)")
    print("=" * 92)
    lat_v = pca_oos(X, featcols, ["abs_e", "loge2"])
    lvl_v = lin_oos(X, ["ot_open", "abs_sp"], ["abs_e"])
    ok = ~np.isnan(lat_v["abs_e"])
    y = X.loc[ok, "abs_e"].values
    for nm, p in (("latent |e|", lat_v["abs_e"][ok]),
                  ("latent log(1+e2)", lat_v["loge2"][ok]),
                  ("LEVEL baseline", lvl_v["abs_e"][ok])):
        yy = X.loc[ok, "loge2"].values if "log" in nm else y
        r2 = 1 - np.sum((yy - p) ** 2) / np.sum((yy - yy.mean()) ** 2)
        cr = np.corrcoef(yy, p)[0, 1]
        t = cr * np.sqrt(ok.sum() - 2) / np.sqrt(1 - cr ** 2)
        print(f"  {nm:18} OOS R2 {r2:+.5f}   corr {cr:+.4f} (t={t:+.2f})")
    A = np.column_stack([np.ones(ok.sum()), lat_v["abs_e"][ok],
                         lvl_v["abs_e"][ok]])
    b, *_ = np.linalg.lstsq(A, y, rcond=None)
    r = y - A @ b
    se = np.sqrt(np.diag(np.linalg.pinv(A.T @ A)) * (r @ r) / (ok.sum() - 3))
    print(f"  |e| ~ latent + level:  latent {b[1]:+.4f} (t={b[1]/se[1]:+.2f})"
          f"   level {b[2]:+.4f} (t={b[2]/se[2]:+.2f})")

    print("\n  predicted-dispersion deciles (latent |e| model, pooled OOS):")
    S = X[ok].copy()
    S["pred"] = lat_v["abs_e"][ok]
    S["dec"] = pd.qcut(S["pred"], 10, labels=False) + 1
    t = S.groupby("dec").agg(n=("pred", "size"), pred=("pred", "mean"),
                             mean_abs_e=("abs_e", "mean"),
                             sd_e=("te_open", lambda v: v.std(ddof=1)))
    print(t.round(3).to_string())
    sp, pv = stats.spearmanr(t.index, t["mean_abs_e"])
    print(f"  Spearman(decile, realized |e|) = {sp:+.3f} (p={pv:.3f})   "
          f"D10-D1 = {t['mean_abs_e'].iloc[-1]-t['mean_abs_e'].iloc[0]:+.3f} "
          f"points")

    # ---------------------------------------------------------- PART 3
    print("\n" + "=" * 92)
    print("PART 3 — FROZEN KALSHI APPLICATION (2025-26, untouched by "
          "training)")
    print("=" * 92)
    import kalshi_calib as KC
    u = KC.load()
    u = u[~((u["bid"] <= 0) & (u["ask"] >= 1.0))]
    u = u[u["bucket"] == "regular"]
    rows = []
    for ev, gg in u.groupby("event_ticker"):
        f = KC.fit_ladder(gg)
        if f:
            rows.append({"k": gg["k"].iloc[0], "mu": f[0], "sd_imp": f[1],
                         "actual": gg["actual"].iloc[0]})
    K = pd.DataFrame(rows)
    mp = pd.read_csv("team_mapping.csv").set_index(
        "bigdataball_name")["abbr"].to_dict()
    m2 = g[g["season"] == 2025].copy()
    m2["H"], m2["A"] = m2["home"].map(mp), m2["away"].map(mp)
    mk = lambda d, a, b: (d.dt.strftime("%Y-%m-%d") + "|"
                          + np.where(a < b, a, b) + "-"
                          + np.where(a < b, b, a))
    m2["k"] = mk(m2["date"], m2["H"].values, m2["A"].values)
    S25 = S[S["season"] == 2025].merge(m2[["gid", "k"]], on="gid") \
        .merge(K, on="k").dropna(subset=["pred", "sd_imp"])
    S25["z"] = (S25["actual"] - S25["mu"]) / S25["sd_imp"]
    print(f"  {len(S25):,} games with a variance prediction and a fitted "
          f"ladder")
    print(f"  corr(predicted |e|, Kalshi implied sd) = "
          f"{np.corrcoef(S25['pred'], S25['sd_imp'])[0, 1]:+.4f}")
    S25["q"] = pd.qcut(S25["pred"], 5, labels=False) + 1
    print(f"  {'quintile':>9}{'n':>6}{'pred |e|':>10}{'implied sd':>12}"
          f"{'realized |a-mu|':>17}{'sd(z)':>8}")
    from scipy.stats import chi2
    for q, s in S25.groupby("q"):
        sz = s["z"].std(ddof=1)
        print(f"  {q:>9}{len(s):>6}{s['pred'].mean():>10.3f}"
              f"{s['sd_imp'].mean():>12.2f}"
              f"{(s['actual']-s['mu']).abs().mean():>17.3f}{sz:>8.3f}")
    n = len(S25)
    lo = np.sqrt(chi2.ppf(0.025, n // 5 - 1) / (n // 5 - 1))
    hi = np.sqrt(chi2.ppf(0.975, n // 5 - 1) / (n // 5 - 1))
    print(f"  per-quintile 95% band for sd(z) under calibrated pricing: "
          f"[{lo:.3f}, {hi:.3f}]")


if __name__ == "__main__":
    main()
