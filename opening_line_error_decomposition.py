"""NBA opening-line error decomposition and latent error-state analysis.

Spec: discovery/diagnostic experiment on whether the bookmaker's own historical
errors contain stable latent structure, identified strictly pregame, that
predicts (A) opening total error, (B) opening spread error, (C) open->close
total movement, (D) open->close spread movement.

Design highlights (full spec in the conversation record):
  - error-ONLY feature matrix: nothing but prior bookmaker residuals
  - strictly prior-only, within-season team histories
  - walk-forward by season: train seasons <= N, test season N+1
  - scaler, PCA, ICA and OLS all fit inside each training fold
  - deciles, betting sim at the opener, CLV, execution sensitivity
  - verdict from the fixed taxonomy

Outputs: opening_line_error_decomposition_results.xlsx (tabbed),
         opening_line_error_oos_predictions.csv, console summary.
"""
import warnings

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")

from sklearn.decomposition import PCA, FastICA
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler

from prepare_data import CSV, season_label as _season_label  # handles both
# vendor layouts: DATASET_H (2017-2022) and BIGDATABALL\nDATASET_H (2022-26)
XLSX = "opening_line_error_decomposition_results.xlsx"
PREDS = "opening_line_error_oos_predictions.csv"
RNG = 20260826
EV_THRESH = 0.80          # training-only PC count rule: cumEV >= 80%
MIN_PRIOR = 10            # both teams need >= 10 prior games this season

TABS = {}


def season_label(raw):
    return _season_label(raw)


# ----------------------------------------------------------------- load
def load():
    from prepare_data import read_master
    raw = read_master(CSV, verbose=False)   # market range gates
    lbl = season_label(raw).astype(str)
    d = raw[lbl.str.contains("Regular Season", na=False)].copy()
    d["season"] = lbl[lbl.str.contains("Regular Season", na=False)]
    cols = {
        "game id": "GAME-ID", "date": "DATE",
        "season": "season_label(raw)",
        "home team": "TEAM_H", "away team": "TEAM_R",
        # season mapping is via prepare_data.season_label (dual layouts)
        "home points": "PTS_H", "away points": "PTS_R",
        "opening total": "OPENING TOTAL_H", "closing total":
        "CLOSING TOTAL_H", "opening spread": "OPENING SPREAD_H",
        "closing spread": "CLOSING SPREAD_H"}
    print("COLUMN MAPPINGS USED")
    for k, v in cols.items():
        ok = (v in raw.columns) or ("season_label" in v)
        print(f"  {k:16} -> {v:20} {'OK' if ok else 'MISSING'}")
        if not ok:
            raise SystemExit(f"required column missing: {v}")
    n = lambda c: pd.to_numeric(d[c], errors="coerce")
    g = pd.DataFrame({
        "gid": d["GAME-ID"].astype(str).str.strip(),
        "date": pd.to_datetime(d["DATE"], errors="coerce"),
        "season": d["season"].str.extract(r"(\d{4})")[0].astype(int),
        "home": d["TEAM_H"], "away": d["TEAM_R"],
        "hpts": n("PTS_H"), "apts": n("PTS_R"),
        "ot_open": n("OPENING TOTAL_H"), "ot_close": n("CLOSING TOTAL_H"),
        "sp_open": n("OPENING SPREAD_H"), "sp_close": n("CLOSING SPREAD_H")})
    g = g.dropna().sort_values(["date", "gid"]).reset_index(drop=True)

    # spread convention check: in this file spread_H = -(implied home margin)
    g["margin"] = g["hpts"] - g["apts"]
    c_neg = np.corrcoef(g["margin"], -g["sp_open"])[0, 1]
    c_pos = np.corrcoef(g["margin"], g["sp_open"])[0, 1]
    conv = -1.0 if c_neg > c_pos else 1.0
    print(f"\nSPREAD CONVENTION: corr(margin, -spread_H)={c_neg:+.3f}  "
          f"corr(margin, +spread_H)={c_pos:+.3f}")
    print(f"  -> OpenMargin = {'-' if conv < 0 else '+'}OPENING SPREAD_H  "
          f"(home favourite has a NEGATIVE raw spread)" if conv < 0 else "")
    g["om_open"] = conv * g["sp_open"]
    g["om_close"] = conv * g["sp_close"]

    g["total"] = g["hpts"] + g["apts"]
    g["te_open"] = g["total"] - g["ot_open"]
    g["te_close"] = g["total"] - g["ot_close"]
    g["se_open"] = g["margin"] - g["om_open"]
    g["se_close"] = g["margin"] - g["om_close"]
    g["tmove"] = g["ot_close"] - g["ot_open"]
    g["smove"] = g["om_close"] - g["om_open"]
    g["ihs"] = (g["ot_open"] + g["om_open"]) / 2.0
    g["ias"] = (g["ot_open"] - g["om_open"]) / 2.0
    g["hse"] = g["hpts"] - g["ihs"]
    g["ase"] = g["apts"] - g["ias"]
    a1 = np.abs(g["hse"] + g["ase"] - g["te_open"]).max()
    a2 = np.abs(g["hse"] - g["ase"] - g["se_open"]).max()
    print(f"IDENTITY CHECK: max|hse+ase-te_open|={a1:.2e}  "
          f"max|hse-ase-se_open|={a2:.2e}  "
          f"{'PASS' if max(a1, a2) < 1e-9 else 'FAIL'}")
    return g


# -------------------------------------------------- 3: distributions
def distributions(g):
    def row(e):
        e = e.dropna()
        return dict(N=len(e), mean=e.mean(), median=e.median(),
                    MAE=e.abs().mean(), RMSE=np.sqrt((e**2).mean()),
                    sd=e.std(), skew=stats.skew(e),
                    exkurt=stats.kurtosis(e),
                    p5=e.quantile(.05), p10=e.quantile(.10),
                    p25=e.quantile(.25), p75=e.quantile(.75),
                    p90=e.quantile(.90), p95=e.quantile(.95))
    series = {"total_open": "te_open", "total_close": "te_close",
              "spread_open": "se_open", "spread_close": "se_close",
              "home_score": "hse", "away_score": "ase"}
    t = pd.DataFrame({k: row(g[v]) for k, v in series.items()}).T
    TABS["Distribution"] = t.reset_index().rename(columns={"index": "error"})
    bys = []
    for yr, s in g.groupby("season"):
        for k, v in series.items():
            r = row(s[v]); r.update(error=k, season=yr)
            bys.append(r)
    TABS["Distribution_by_season"] = pd.DataFrame(bys)
    print("\n" + "=" * 96)
    print("3 — UNCONDITIONAL ERROR DISTRIBUTIONS (pooled; per-season in xlsx)")
    print("=" * 96)
    print(t[["N", "mean", "median", "MAE", "RMSE", "sd", "skew",
             "exkurt"]].round(3).to_string())


# ------------------------------------------------------ 4: mixtures
def mixtures(g):
    print("\n" + "=" * 96)
    print("4 — GAUSSIAN MIXTURES on opening errors (BIC primary)")
    print("=" * 96)
    rows = []
    for nm, col in (("total_open", "te_open"), ("spread_open", "se_open")):
        x = g[col].dropna().values.reshape(-1, 1)
        print(f"  {nm}  (n={len(x):,})")
        best = None
        for k in (1, 2, 3, 4):
            gm = GaussianMixture(k, random_state=RNG, n_init=3).fit(x)
            aic, bic = gm.aic(x), gm.bic(x)
            for j in range(k):
                rows.append(dict(target=nm, k=k, comp=j,
                                 weight=gm.weights_[j],
                                 mean=gm.means_[j, 0],
                                 sd=np.sqrt(gm.covariances_[j, 0, 0]),
                                 AIC=aic, BIC=bic, scope="pooled"))
            tag = ""
            if best is None or bic < best[1]:
                best = (k, bic)
            print(f"    k={k}  AIC {aic:12.1f}  BIC {bic:12.1f}")
        print(f"    BIC-selected k = {best[0]}")
        for yr, s in g.groupby("season"):
            x = s[col].dropna().values.reshape(-1, 1)
            if len(x) < 400:
                continue
            bics = {k: GaussianMixture(k, random_state=RNG,
                                       n_init=2).fit(x).bic(x)
                    for k in (1, 2, 3)}
            ksel = min(bics, key=bics.get)
            rows.append(dict(target=nm, k=ksel, comp=-1, weight=np.nan,
                             mean=np.nan, sd=np.nan, AIC=np.nan,
                             BIC=bics[ksel], scope=f"season {yr} selected"))
        sel = [r for r in rows if r["target"] == nm and "season" in
               str(r["scope"])]
        ks = [r["k"] for r in sel]
        print(f"    by season, BIC-selected k: {ks}")
    TABS["Mixture_Models"] = pd.DataFrame(rows)


# -------------------------------------------- 5/6: error-state features
LAGS = (1, 2, 3)
RMS = ((3, 3), (5, 3), (10, 5), (20, 10))
SDS = ((5, 3), (10, 5), (20, 10))
STATES = ("scoreerr", "allowerr", "toterr", "sprerr")


def team_panel(g):
    rows = []
    for side in ("home", "away"):
        opp = "away" if side == "home" else "home"
        sgn = 1.0 if side == "home" else -1.0
        rows.append(pd.DataFrame({
            "gid": g["gid"], "date": g["date"], "season": g["season"],
            "team": g[side],
            "scoreerr": g["hse"] if side == "home" else g["ase"],
            "allowerr": g["ase"] if side == "home" else g["hse"],
            "toterr": g["te_open"], "sprerr": sgn * g["se_open"]}))
    p = pd.concat(rows).sort_values(["date", "gid"]).reset_index(drop=True)
    grp = p.groupby(["season", "team"])
    feats = {}
    for st in STATES:
        s = grp[st]
        for L in LAGS:
            feats[f"{st}_lag{L}"] = s.shift(L)
        for w, mp in RMS:
            feats[f"{st}_rm{w}"] = s.transform(
                lambda x, w=w, mp=mp: x.shift(1).rolling(w, min_periods=mp)
                .mean())
        for w, mp in SDS:
            feats[f"{st}_sd{w}"] = s.transform(
                lambda x, w=w, mp=mp: x.shift(1).rolling(w, min_periods=mp)
                .std())
        feats[f"{st}_ewm"] = s.transform(
            lambda x: x.shift(1).ewm(halflife=5, min_periods=3).mean())
    F = pd.concat(feats, axis=1)
    F[["gid", "team"]] = p[["gid", "team"]]
    F["nprior"] = grp.cumcount()
    return F


def design_matrix(g):
    F = team_panel(g)
    fcols = [c for c in F.columns if c not in ("gid", "team", "nprior")]
    h = g[["gid", "home"]].merge(
        F.rename(columns={"team": "home"}), on=["gid", "home"])
    a = g[["gid", "away"]].merge(
        F.rename(columns={"team": "away"}), on=["gid", "away"])
    X = g[["gid", "date", "season", "home", "away", "te_open", "se_open",
           "te_close", "se_close", "tmove", "smove", "ot_open", "ot_close",
           "total", "margin", "om_open", "om_close"]].copy()
    for c in fcols:
        X[f"h_{c}"] = h[c].values
        X[f"a_{c}"] = a[c].values
    X["h_nprior"], X["a_nprior"] = h["nprior"].values, a["nprior"].values
    # matchup combinations on the canonical rm10 state
    for st in STATES:
        X[f"sum_{st}"] = X[f"h_{st}_rm10"] + X[f"a_{st}_rm10"]
        X[f"dif_{st}"] = X[f"h_{st}_rm10"] - X[f"a_{st}_rm10"]
    X = X[(X["h_nprior"] >= MIN_PRIOR) & (X["a_nprior"] >= MIN_PRIOR)]
    featcols = [c for c in X.columns if c.startswith(("h_", "a_", "sum_",
                                                      "dif_"))
                and not c.endswith("nprior")]
    X = X.dropna(subset=featcols).reset_index(drop=True)
    return X, featcols


# --------------------------------------------------- 5: persistence gate
def persistence(X):
    print("\n" + "=" * 96)
    print("5 — PERSISTENCE GATE: simple 4-state models (rm10 states)")
    print("=" * 96)
    specs = {
        "te_open": ["h_scoreerr_rm10", "a_scoreerr_rm10",
                    "h_allowerr_rm10", "a_allowerr_rm10"],
        "se_open": ["h_sprerr_rm10", "a_sprerr_rm10",
                    "h_scoreerr_rm10", "a_scoreerr_rm10"],
        "tmove": ["h_scoreerr_rm10", "a_scoreerr_rm10",
                  "h_allowerr_rm10", "a_allowerr_rm10"],
        "smove": ["h_sprerr_rm10", "a_sprerr_rm10",
                  "h_scoreerr_rm10", "a_scoreerr_rm10"]}
    rows = []
    seasons = sorted(X["season"].unique())
    for tgt, fx in specs.items():
        # in-sample
        A = np.column_stack([np.ones(len(X))] + [X[c] for c in fx])
        b, *_ = np.linalg.lstsq(A, X[tgt], rcond=None)
        r = X[tgt] - A @ b
        r2 = 1 - r.var() / X[tgt].var()
        # walk-forward
        preds = np.full(len(X), np.nan)
        for i in range(2, len(seasons)):
            tr = X["season"] < seasons[i]
            te = X["season"] == seasons[i]
            At = np.column_stack([np.ones(tr.sum())] +
                                 [X.loc[tr, c] for c in fx])
            bt, *_ = np.linalg.lstsq(At, X.loc[tr, tgt], rcond=None)
            Ae = np.column_stack([np.ones(te.sum())] +
                                 [X.loc[te, c] for c in fx])
            preds[te.values] = Ae @ bt
        ok = ~np.isnan(preds)
        y, p = X.loc[ok, tgt].values, preds[ok]
        oos_r2 = 1 - np.sum((y - p) ** 2) / np.sum((y - y.mean()) ** 2)
        cr = np.corrcoef(y, p)[0, 1]
        tstat = cr * np.sqrt(ok.sum() - 2) / np.sqrt(1 - cr ** 2)
        rows.append(dict(target=tgt, IS_R2=r2, OOS_R2=oos_r2, OOS_corr=cr,
                         OOS_t=tstat, n_oos=int(ok.sum())))
        print(f"  {tgt:8}  IS R2 {r2:+.5f}   OOS R2 {oos_r2:+.5f}   "
              f"OOS corr {cr:+.4f} (t={tstat:+.2f})   n={ok.sum():,}")
    TABS["Persistence"] = pd.DataFrame(rows)


# ----------------------------------------- 7/8/9: PCA / ICA walk-forward
def latent_oos(X, featcols):
    print("\n" + "=" * 96)
    print("7/8/9 — WALK-FORWARD LATENT MODELS (PCA and ICA, per-fold fits)")
    print("=" * 96)
    seasons = sorted(X["season"].unique())
    targets = ("te_open", "se_open", "tmove", "smove")
    preds = {(m, t): np.full(len(X), np.nan)
             for m in ("pca", "ica") for t in targets}
    ev_rows, load_prev, stab = [], None, []
    Ks = []
    for i in range(2, len(seasons)):
        tr = (X["season"] < seasons[i]).values
        te = (X["season"] == seasons[i]).values
        sc = StandardScaler().fit(X.loc[tr, featcols])
        Ztr = sc.transform(X.loc[tr, featcols])
        Zte = sc.transform(X.loc[te, featcols])
        pca = PCA(n_components=min(30, Ztr.shape[1])).fit(Ztr)
        cum = np.cumsum(pca.explained_variance_ratio_)
        K = int(np.searchsorted(cum, EV_THRESH) + 1)
        Ks.append(K)
        ev_rows.append(dict(test_season=seasons[i], K=K,
                            **{f"PC{j+1}": pca.explained_variance_ratio_[j]
                               for j in range(20)}))
        L = pca.components_[:5]
        if load_prev is not None:
            for j in range(5):
                c = np.corrcoef(L[j], load_prev[j])[0, 1]
                stab.append(dict(test_season=seasons[i], PC=j + 1,
                                 corr_with_prev_fold=abs(c)))
        load_prev = L
        Str, Ste = pca.transform(Ztr)[:, :K], pca.transform(Zte)[:, :K]
        ica = FastICA(n_components=K, random_state=RNG, max_iter=1000,
                      whiten="unit-variance").fit(Ztr)
        Itr, Ite = ica.transform(Ztr), ica.transform(Zte)
        for t in targets:
            ytr = X.loc[tr, t].values
            for m, Ftr, Fte in (("pca", Str, Ste), ("ica", Itr, Ite)):
                A = np.column_stack([np.ones(len(Ftr)), Ftr])
                b, *_ = np.linalg.lstsq(A, ytr, rcond=None)
                preds[(m, t)][te] = np.column_stack(
                    [np.ones(len(Fte)), Fte]) @ b
    TABS["PCA"] = pd.DataFrame(ev_rows)
    TABS["PCA_Loadings"] = pd.DataFrame(
        {"feature": featcols,
         **{f"PC{j+1}_lastfold": load_prev[j] for j in range(5)}})
    st = pd.DataFrame(stab)
    TABS["PC_Stability"] = st
    print(f"  folds: train<=season N, test N+1; test seasons "
          f"{seasons[2:]}   K by cumEV>={EV_THRESH:.0%}: {Ks}")
    e1 = TABS["PCA"].iloc[-1]
    print(f"  last fold: PC1 {e1['PC1']:.1%}  PC2 {e1['PC2']:.1%}  "
          f"PC3 {e1['PC3']:.1%}  (cum20 "
          f"{sum(e1[f'PC{j+1}'] for j in range(20)):.1%})")
    piv = st.groupby("PC")["corr_with_prev_fold"].mean()
    print("  PC loading stability across adjacent folds (mean |corr|): "
          + "  ".join(f"PC{k} {v:.3f}" for k, v in piv.items()))
    return preds


# --------------------------------------- 11..15: evaluation and betting
def evaluate(X, preds):
    print("\n" + "=" * 96)
    print("11 — OOS METRICS (pooled over genuinely out-of-sample seasons)")
    print("=" * 96)
    names = {"te_open": "A total_open", "se_open": "B spread_open",
             "tmove": "C total_move", "smove": "D spread_move"}
    rows = []
    for t, nm in names.items():
        y_all = X[t].values
        line = f"  {nm:14}"
        for m in ("pca", "ica"):
            p = preds[(m, t)]
            ok = ~np.isnan(p)
            y = y_all[ok]
            r2 = 1 - np.sum((y - p[ok])**2) / np.sum((y - y.mean())**2)
            cr = np.corrcoef(y, p[ok])[0, 1]
            ts = cr * np.sqrt(ok.sum() - 2) / np.sqrt(1 - cr**2)
            rows.append(dict(target=nm, model=m, OOS_R2=r2, corr=cr, t=ts,
                             RMSE=np.sqrt(np.mean((y - p[ok])**2)),
                             MAE=np.mean(np.abs(y - p[ok])),
                             n=int(ok.sum())))
            line += f"  {m}: R2 {r2:+.5f} corr {cr:+.4f} (t {ts:+.2f})"
        print(line)
    TABS["OOS_Predictions_summary"] = pd.DataFrame(rows)

    # the MARKET-CORRECTS pattern, primary latent model = pca
    print("\n  THE §10 PATTERN (pca model):")
    for t, mv, cl in (("te_open", "tmove", "te_close"),
                      ("se_open", "smove", "se_close")):
        p = preds[("pca", t)]
        ok = ~np.isnan(p)
        c1 = np.corrcoef(X.loc[ok, t], p[ok])[0, 1]
        c2 = np.corrcoef(X.loc[ok, mv], p[ok])[0, 1]
        c3 = np.corrcoef(X.loc[ok, cl], p[ok])[0, 1]
        n = ok.sum()
        tt = lambda c: c * np.sqrt(n - 2) / np.sqrt(1 - c**2)
        print(f"    {t}: corr(pred, open err) {c1:+.4f} (t {tt(c1):+.2f})   "
              f"corr(pred, MOVE) {c2:+.4f} (t {tt(c2):+.2f})   "
              f"corr(pred, close err) {c3:+.4f} (t {tt(c3):+.2f})")

    # by season
    bys = []
    for t in names:
        p = preds[("pca", t)]
        ok = ~np.isnan(p)
        for yr, s in X[ok].groupby("season"):
            pp = p[ok][X[ok]["season"].values == yr]
            cr = np.corrcoef(s[t], pp)[0, 1]
            bys.append(dict(target=t, season=yr, corr=cr, n=len(s)))
    TABS["OOS_By_Season"] = pd.DataFrame(bys)

    # capturable fraction
    print("\n15 — CAPTURABLE FRACTION (pca):")
    for t in ("te_open", "se_open"):
        p = preds[("pca", t)]
        ok = ~np.isnan(p)
        cf = np.var(p[ok]) / np.var(X.loc[ok, t])
        r2 = 1 - np.sum((X.loc[ok, t] - p[ok])**2) / \
            np.sum((X.loc[ok, t] - X.loc[ok, t].mean())**2)
        print(f"    {t}: Var(pred)/Var(e) = {cf:.4f}   OOS R2 = {r2:+.5f}")


def deciles_and_betting(X, preds):
    print("\n" + "=" * 96)
    print("12 — DECILES of predicted OPENING error (pca, pooled OOS)")
    print("=" * 96)
    out = {}
    for t, mv, lab in (("te_open", "tmove", "Buckets_Total"),
                       ("se_open", "smove", "Buckets_Spread")):
        p = preds[("pca", t)]
        ok = ~np.isnan(p)
        s = X[ok].copy()
        s["pred"] = p[ok]
        s["dec"] = pd.qcut(s["pred"], 10, labels=False) + 1
        tt = s.groupby("dec").agg(
            n=("pred", "size"), pred=("pred", "mean"),
            open_err=(t, "mean"), move=(mv, "mean"),
            close_err=(t.replace("open", "close"), "mean"))
        tt["over_rate_at_open"] = s.groupby("dec")[t].apply(
            lambda e: (e > 0).mean())
        out[lab] = tt.reset_index()
        TABS[lab] = out[lab]
        print(f"\n  {t}:")
        print(tt.round(3).to_string())
        mono = tt["open_err"].is_monotonic_increasing
        sp, pv = stats.spearmanr(tt.index, tt["open_err"])
        print(f"  strictly monotonic: {mono}   Spearman(dec, open_err) "
              f"{sp:+.3f} (p={pv:.3f})")

    print("\n" + "=" * 96)
    print("13/14/17 — BETTING AT THE OPENER (totals, pca), CLV, execution")
    print("=" * 96)
    p = preds[("pca", "te_open")]
    ok = ~np.isnan(p)
    s = X[ok].copy()
    s["pred"] = p[ok]
    rows = []
    print(f"  {'threshold':>10}{'n':>7}{'win %':>8}{'ROI %':>8}{'t':>7}"
          f"{'mean CLV':>10}{'beat close %':>13}")
    for thr in (0.0, 0.5, 1.0, 1.5, 2.0, 2.5):
        b = s[s["pred"].abs() >= thr].copy()
        if len(b) < 30:
            continue
        over = b["pred"] > 0
        win = np.where(over, b["total"] > b["ot_open"],
                       b["total"] < b["ot_open"])
        push = b["total"] == b["ot_open"]
        live = ~push
        wr = win[live].mean()
        roi = (wr * 100 / 110 - (1 - wr))
        se = np.sqrt(wr * (1 - wr) / live.sum())
        clv = np.where(over, b["tmove"], -b["tmove"])
        rows.append(dict(threshold=thr, n=int(live.sum()),
                         win_pct=100 * wr, roi_pct=100 * roi,
                         t_vs_BE=(wr - 110 / 210) / se,
                         mean_CLV=clv.mean(),
                         beat_close_pct=100 * (clv > 0).mean(),
                         mean_pred=b["pred"].abs().mean(),
                         mean_realized=np.where(over, b["te_open"],
                                                -b["te_open"]).mean()))
        print(f"  {thr:>10.1f}{live.sum():>7,}{100*wr:>8.2f}"
              f"{100*roi:>8.2f}{(wr-110/210)/se:>7.2f}{clv.mean():>10.3f}"
              f"{100*(clv>0).mean():>13.1f}")
    TABS["Betting"] = pd.DataFrame(rows)

    seas = []
    b = s[s["pred"].abs() >= 1.0]
    for yr, x in b.groupby("season"):
        over = x["pred"] > 0
        live = x["total"] != x["ot_open"]
        win = np.where(over, x["total"] > x["ot_open"],
                       x["total"] < x["ot_open"])[live]
        clv = np.where(over, x["tmove"], -x["tmove"])
        seas.append(dict(season=yr, n=int(live.sum()),
                         win_pct=100 * win.mean(), CLV=clv.mean()))
    TABS["Betting_by_season"] = pd.DataFrame(seas)
    print("  by season (|pred|>=1.0): " + "  ".join(
        f"{r['season']}: {r['win_pct']:.1f}%/{r['CLV']:+.2f}"
        for r in seas))
    TABS["CLV"] = pd.DataFrame(
        [dict(bucket=f">={thr}", **{k: v for k, v in r.items()
                                    if "CLV" in k or k in ("n",)})
         for thr, r in zip([r["threshold"] for r in rows], rows)])

    ex = []
    print(f"\n  execution sensitivity (|pred|>=1.0 totals):")
    for adv in (0.0, 0.5, 1.0):
        bb = s[s["pred"].abs() >= 1.0]
        over = bb["pred"] > 0
        line = np.where(over, bb["ot_open"] + adv, bb["ot_open"] - adv)
        win = np.where(over, bb["total"] > line, bb["total"] < line)
        push = bb["total"] == line
        live = ~push
        wr = win[live].mean()
        roi = wr * 100 / 110 - (1 - wr)
        ex.append(dict(adverse=adv, n=int(live.sum()), win_pct=100 * wr,
                       roi_pct=100 * roi))
        print(f"    adverse {adv:.1f} pts: win {100*wr:.2f}%  "
              f"ROI {100*roi:+.2f}%")
    TABS["Execution_Sensitivity"] = pd.DataFrame(ex)
    return s


def save(X, preds):
    p = preds[("pca", "te_open")]
    ok = ~np.isnan(p)
    s = X[ok].copy()
    s["pred_total_err"] = p[ok]
    s["pred_spread_err"] = preds[("pca", "se_open")][ok]
    s["pred_dir"] = np.sign(s["pred_total_err"])
    s["clv_total"] = np.where(s["pred_total_err"] > 0, s["tmove"],
                              -s["tmove"])
    live = s["total"] != s["ot_open"]
    s["bet_result"] = np.where(~live, "push",
                               np.where((s["pred_total_err"] > 0)
                                        == (s["te_open"] > 0), "win",
                                        "loss"))
    s["model"] = "pca_cumEV80_ols"
    cols = ["gid", "date", "season", "home", "away", "ot_open", "ot_close",
            "total", "te_open", "te_close", "pred_total_err",
            "pred_spread_err", "model", "pred_dir", "tmove", "clv_total",
            "bet_result"]
    s[cols].to_csv(PREDS, index=False)
    try:
        with pd.ExcelWriter(XLSX) as w:
            summary = pd.DataFrame([{"note": k, "rows": len(v)}
                                    for k, v in TABS.items()])
            summary.to_excel(w, sheet_name="Summary", index=False)
            for k, v in TABS.items():
                v.to_excel(w, sheet_name=k[:31], index=False)
        print(f"\n  wrote {XLSX} ({len(TABS)} tabs) and {PREDS} "
              f"({ok.sum():,} OOS rows)")
    except Exception as e:
        for k, v in TABS.items():
            v.to_csv(f"oled_{k}.csv", index=False)
        print(f"\n  xlsx failed ({e}); wrote oled_*.csv instead, plus {PREDS}")


def main():
    g = load()
    print(f"\n  {len(g):,} regular-season games, seasons "
          f"{sorted(g['season'].unique())}")
    distributions(g)
    mixtures(g)
    X, featcols = design_matrix(g)
    print(f"\n6 — ERROR-ONLY STATE MATRIX: {len(X):,} games with "
          f"{len(featcols)} features (both teams >= {MIN_PRIOR} prior games)")
    persistence(X)
    preds = latent_oos(X, featcols)
    evaluate(X, preds)
    deciles_and_betting(X, preds)
    save(X, preds)


if __name__ == "__main__":
    main()
