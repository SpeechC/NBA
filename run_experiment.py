"""Replication of Chen, Jhou, Lee & Lu (2021), Entropy 23(4), 477.

Reproduces the paper's scheme end to end:
  Table 3  single-stage models (ELM, MARS, XGBoost, SGB, KNN) x game-lags 1-6
  Table 2  ensemble feature ranking from MARS / XGBoost / SGB
  Table 4  two-stage models on the top-6 ranked features x game-lags 1-6
  Table 5  T-XGBoost vs linear / M5P-style tree / SVR, single and two-stage
  Table 6/7 Wilcoxon signed-rank tests on fold-level errors
  Figure 3 sensitivity to the number of selected features (4-8)
"""

import json
import sys
import warnings

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import GridSearchCV, KFold
from sklearn.neighbors import KNeighborsRegressor
from sklearn.svm import SVR
from sklearn.tree import DecisionTreeRegressor
from xgboost import XGBRegressor

from mars_elm import ELM, Earth
from prepare_data import VARS, designed_features, load_panel

warnings.filterwarnings("ignore")
SEED = 42
FOLDS = 10
INNER = 3
NJOBS = 1  # BLAS+grid threads are pinned to 1; parallelism comes from running seasons side by side


def mape(y_true, y_pred):
    return float(np.mean(np.abs((y_true - y_pred) / y_true)))


# --- model factories -------------------------------------------------------
# Hyperparameters mirror the R packages the paper used: caret-tuned grids for
# XGBoost / ELM / KNN, package defaults for MARS (earth) and SGB (gbm).
def make_model(name):
    if name == "MARS":
        return Earth(), None
    if name == "SGB":
        return GradientBoostingRegressor(
            n_estimators=100, max_depth=1, learning_rate=0.1,
            subsample=0.5, random_state=SEED), None
    if name == "XGBoost":
        grid = {"max_depth": [1, 2, 3], "n_estimators": [50, 100, 150],
                "learning_rate": [0.3, 0.4]}
        return XGBRegressor(subsample=1.0, colsample_bytree=0.8,
                            min_child_weight=1, gamma=0, random_state=SEED,
                            n_jobs=1, verbosity=0), grid
    if name == "ELM":
        return ELM(random_state=SEED), {"n_hidden": [5, 10, 20, 50, 100]}
    if name == "KNN":
        return KNeighborsRegressor(weights="distance"), {"n_neighbors": [3, 5, 7, 9, 11, 15]}
    if name == "Linear":
        return LinearRegression(), None
    if name == "M5P":
        # sklearn has no M5P; a pruned regression tree is the closest analogue
        return DecisionTreeRegressor(random_state=SEED), {"min_samples_leaf": [5, 10, 20, 40]}
    if name == "SVR":
        return SVR(kernel="rbf"), {"C": [1, 10, 100], "gamma": ["scale", 0.1]}
    raise ValueError(name)


def fit_predict(name, Xtr, ytr, Xte):
    est, grid = make_model(name)
    if grid:
        gs = GridSearchCV(est, grid, cv=INNER, scoring="neg_mean_absolute_error", n_jobs=NJOBS)
        gs.fit(Xtr, ytr)
        est = gs.best_estimator_
    else:
        est.fit(Xtr, ytr)
    return est.predict(Xte)


def cv_evaluate(name, X, y):
    """10-fold CV; returns overall MAPE/RMSE/SSE plus per-fold MAPEs."""
    kf = KFold(n_splits=FOLDS, shuffle=True, random_state=SEED)
    preds = np.zeros(len(y))
    fold_mapes = []
    for tr, te in kf.split(X):
        p = fit_predict(name, X[tr], y[tr], X[te])
        preds[te] = p
        fold_mapes.append(mape(y[te], p))
    err = y - preds
    return {
        "mape": mape(y, preds),
        "rmse": float(np.sqrt(np.mean(err ** 2))),
        "sse": float(np.sum(err ** 2)),
        "fold_mapes": fold_mapes,
        "abs_pct_err": np.abs(err / y),
    }


# --- feature ranking (paper Table 2) ---------------------------------------
def rank_features(X, y):
    ranks = {}
    for name in ["MARS", "XGBoost", "SGB"]:
        est, grid = make_model(name)
        if grid:
            est = GridSearchCV(est, grid, cv=INNER,
                               scoring="neg_mean_absolute_error", n_jobs=NJOBS).fit(X, y).best_estimator_
        else:
            est.fit(X, y)
        imp = np.asarray(est.feature_importances_, dtype=float)
        # rank 1 = most important; unselected features share the worst rank (13),
        # matching how earth/gbm report zero-importance variables in the paper
        order = pd.Series(-imp).rank(method="min")
        order[imp <= 0] = len(imp)
        ranks[name] = order.values
    tab = pd.DataFrame(ranks, index=VARS)
    tab["Average Rank"] = tab.mean(axis=1)
    return tab.sort_values("Average Rank")


def main():
    season = sys.argv[1] if len(sys.argv) > 1 else "NBA 2018-2019 Regular Season"
    if season.upper() == "ALL":
        season = None
    panel = load_panel(season)
    data = designed_features(panel)
    print(f"season={season}  team-games={len(panel)}  modelled samples={len(data[4])}\n",
          flush=True)

    results = {"season": str(season), "n_samples": int(len(data[4]))}
    single_models = ["ELM", "MARS", "XGBoost", "SGB", "KNN"]

    # ---- Table 3: single-stage models -------------------------------------
    table3 = pd.DataFrame(index=[f"S-{m}" for m in single_models],
                          columns=[f"l={l}" for l in range(1, 7)], dtype=float)
    detail = {}
    for l in range(1, 7):
        d = data[l]
        X, y = d[VARS].values, d["Y"].values.astype(float)
        for m in single_models:
            r = cv_evaluate(m, X, y)
            table3.loc[f"S-{m}", f"l={l}"] = r["mape"]
            detail[(f"S-{m}", l)] = r
            print(f"  S-{m:<8} lag={l}  MAPE={r['mape']:.4f}", flush=True)
    print("\nTable 3 (single models):\n", table3.round(4).to_string(), "\n", flush=True)

    # ---- Table 2: ensemble feature ranking --------------------------------
    rank_tables = {}
    selected = {}
    for l in range(1, 7):
        d = data[l]
        rt = rank_features(d[VARS].values, d["Y"].values.astype(float))
        rank_tables[l] = rt
        selected[l] = list(rt.index[:6])
    print("Table 2 (feature ranking, lag=4):\n", rank_tables[4].round(2).to_string(), flush=True)
    print("\nSelected top-6 features by lag:")
    for l in range(1, 7):
        print(f"  l={l}: {selected[l]}", flush=True)

    # ---- Table 4: two-stage models ----------------------------------------
    table4 = pd.DataFrame(index=[f"T-{m}" for m in single_models],
                          columns=[f"l={l}" for l in range(1, 7)], dtype=float)
    for l in range(1, 7):
        d = data[l]
        feats = selected[l]
        X, y = d[feats].values, d["Y"].values.astype(float)
        for m in single_models:
            r = cv_evaluate(m, X, y)
            table4.loc[f"T-{m}", f"l={l}"] = r["mape"]
            detail[(f"T-{m}", l)] = r
            print(f"  T-{m:<8} lag={l}  MAPE={r['mape']:.4f}", flush=True)
    print("\nTable 4 (two-stage models):\n", table4.round(4).to_string(), "\n", flush=True)

    # ---- Table 5: comparison with linear / M5P / SVR at lag=4 -------------
    d4 = data[4]
    y4 = d4["Y"].values.astype(float)
    table5 = {}
    for m in ["Linear", "M5P", "SVR"]:
        rs = cv_evaluate(m, d4[VARS].values, y4)
        rt = cv_evaluate(m, d4[selected[4]].values, y4)
        detail[(f"S-{m}", 4)] = rs
        detail[(f"T-{m}", 4)] = rt
        table5[f"S-{m}"] = rs
        table5[f"T-{m}"] = rt
        print(f"  S-{m:<7} MAPE={rs['mape']:.4f}   T-{m:<7} MAPE={rt['mape']:.4f}", flush=True)
    table5["T-XGBoost"] = detail[("T-XGBoost", 4)]
    t5 = pd.DataFrame({k: {"MAPE": v["mape"], "RMSE": v["rmse"], "SSE": v["sse"]}
                       for k, v in table5.items()}).T
    print("\nTable 5 (model comparison, lag=4):\n", t5.round(4).to_string(), "\n", flush=True)

    # ---- Tables 6 & 7: Wilcoxon signed-rank on per-sample absolute % errors -
    base = detail[("T-XGBoost", 4)]["abs_pct_err"]
    table6 = {}
    for l in [1, 2, 3, 5, 6]:
        s, p = wilcoxon(base, detail[("T-XGBoost", l)]["abs_pct_err"])
        table6[f"lag={l}"] = {"statistic": float(s), "p_value": float(p)}
    table7 = {}
    for m in ["Linear", "MARS", "SVR", "SGB", "KNN", "ELM", "M5P"]:
        s, p = wilcoxon(base, detail[(f"T-{m}", 4)]["abs_pct_err"])
        table7[f"T-{m}"] = {"statistic": float(s), "p_value": float(p)}
    print("Table 6 (T-XGBoost lag=4 vs other lags):\n",
          pd.DataFrame(table6).T.to_string(), flush=True)
    print("\nTable 7 (T-XGBoost lag=4 vs competitors):\n",
          pd.DataFrame(table7).T.to_string(), "\n", flush=True)

    # ---- Figure 3: sensitivity to number of selected features -------------
    fig3 = pd.DataFrame(index=[f"T-{m}" for m in single_models],
                        columns=[4, 5, 6, 7, 8], dtype=float)
    for k in [4, 5, 6, 7, 8]:
        feats = list(rank_tables[4].index[:k])
        X = d4[feats].values
        for m in single_models:
            fig3.loc[f"T-{m}", k] = cv_evaluate(m, X, y4)["mape"]
        print(f"  n_features={k} done", flush=True)
    print("\nFigure 3 (MAPE by number of selected features, lag=4):\n",
          fig3.round(4).to_string(), flush=True)

    results.update({
        "table3": table3.round(4).to_dict(),
        "table2_lag4": rank_tables[4].round(3).to_dict(),
        "selected_features": selected,
        "table4": table4.round(4).to_dict(),
        "table5": t5.round(4).to_dict(),
        "table6": table6,
        "table7": table7,
        "figure3": fig3.round(4).to_dict(),
    })
    tag = "ALL_SEASONS" if season is None else season.replace(" ", "_")
    out = f"results_{tag}.json"
    with open(out, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
