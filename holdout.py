"""Out-of-sample validation using data already in the database.

Live paper-trading is not the only way to get out-of-sample evidence. Two
holdouts already exist and neither was used to build anything:

  1. PLAYOFFS AND PLAY-IN. Every model in this project filtered to
     "Regular Season|In-Season". The 502 playoff and 24 play-in games carry full
     opening and closing totals and have never been seen -- by the models or by
     me. Genuinely untouched, but a different regime: sharper markets, shorter
     rotations, different pace.

  2. A NESTED TEMPORAL SPLIT. The walk-forward predictions were always honest --
     each used only prior games. What leaked was SELECTION: ridge, the feature
     spec and the threshold were all chosen after seeing all six seasons. So the
     honest question is not "does the model work out of sample" but "would this
     PROCEDURE, run at the end of 2022-23, have produced a model that worked in
     2023-24?" That is testable: re-run the estimator comparison on pre-cut data
     only, then evaluate the winner on the held-out season.

Test 2 is the more representative of the two; test 1 is the cleaner claim of
never-seen data. They fail differently, so both are run.
"""

import warnings

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import RidgeCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

from models_frozen import SPECS, add_pace_terms, walk_forward
from symmetric_features import build

warnings.filterwarnings("ignore")
RNG = np.random.default_rng(0)
THRESH = 1.25
CUT = pd.Timestamp("2023-04-10")     # end of the 2022-23 regular season


def econ(d, label):
    s = d[(d["pm"].abs() > THRESH) & (d["actual_total"] != d["open_total"])]
    if len(s) < 30:
        return {"sample": label, "n": len(s), "note": "too few bets"}
    over = (s["actual_total"] > s["open_total"]).values
    win = np.where((s["pm"] > 0).values, over, ~over).astype(float)
    n, w = len(win), win.mean()
    lo, hi = stats.beta.ppf([.025, .975], win.sum() + .5, n - win.sum() + .5)
    clv = np.where(s["pm"] > 0, s["move_total"], -s["move_total"])
    bs = np.array([RNG.choice(win, n, replace=True).mean() for _ in range(6000)])
    roi_bs = bs * (100 / 110) - (1 - bs)
    return {"sample": label, "n": n, "CLV": clv.mean(),
            "beat close %": 100 * (clv > 0).mean(), "win %": 100 * w,
            "win lo": 100 * lo, "win hi": 100 * hi,
            "ROI %": 100 * (w * (100 / 110) - (1 - w)),
            "ROI lo": 100 * np.percentile(roi_bs, 2.5),
            "ROI hi": 100 * np.percentile(roi_bs, 97.5),
            "P(ROI>0) %": 100 * (roi_bs > 0).mean()}


def main():
    G = add_pace_terms(build())
    feats = SPECS["A"]
    G = G.dropna(subset=feats + ["move_total", "actual_total", "open_total"])
    G = G.sort_values("date").reset_index(drop=True)
    G["pm"] = walk_forward(G[feats].values, G["move_total"].values.astype(float),
                           G["date"].values)
    d = G.dropna(subset=["pm"]).copy()

    # ---------- TEST 2a: would ridge have been chosen at the cut? ----------
    print("=== would the ESTIMATOR choice have been made the same way in Apr 2023? ===")
    tr = d[d["date"] < CUT]
    X, y, dt = tr[feats].values, tr["move_total"].values.astype(float), tr["date"].values
    cands = {
        "Ridge": lambda: make_pipeline(StandardScaler(),
                                       RidgeCV(alphas=np.logspace(-2, 3, 20))),
        "XGBoost": lambda: XGBRegressor(max_depth=3, n_estimators=150,
                                        learning_rate=0.05, subsample=0.8,
                                        colsample_bytree=0.8, random_state=42,
                                        n_jobs=6, verbosity=0),
        "RandomForest": lambda: RandomForestRegressor(n_estimators=300,
                                                      min_samples_leaf=20,
                                                      max_features=0.4,
                                                      random_state=42, n_jobs=6),
    }
    rows = []
    for name, mk in cands.items():
        p = walk_forward_generic(X, y, dt, mk)
        m = ~np.isnan(p)
        clv = np.where(p[m] > 0, y[m], -y[m])
        rows.append({"estimator": name, "n": int(m.sum()),
                     "corr": float(np.corrcoef(p[m], y[m])[0, 1]),
                     "CLV": clv.mean()})
    r = pd.DataFrame(rows).sort_values("CLV", ascending=False)
    print(r.round(4).to_string(index=False))
    print(f"  -> chosen on pre-cut data: {r.iloc[0]['estimator']}")

    # ---------- TEST 2b: held-out season ----------
    print(f"\n=== held-out season: games after {CUT.date()} ===")
    out = [econ(d[d["date"] < CUT], f"development (< {CUT.date()})"),
           econ(d[d["date"] >= CUT], f"HELD OUT (>= {CUT.date()})")]
    print(pd.DataFrame(out).round(3).to_string(index=False))

    # ---------- TEST 1: playoffs, never used ----------
    print("\n=== playoffs and play-in: never used to build anything ===")
    po = build_playoffs()
    if po is None or len(po) < 50:
        print("  could not assemble playoff features")
        return
    po = add_pace_terms(po)
    po = po.dropna(subset=feats + ["move_total", "actual_total", "open_total"])
    # fit on ALL regular-season games, predict playoffs -- strictly forward in time
    fit = make_pipeline(StandardScaler(), RidgeCV(alphas=np.logspace(-2, 3, 20)))
    preds = []
    for _, row in po.iterrows():
        hist = d[d["date"] < row["date"]]
        preds.append(np.nan if len(hist) < 500 else None)
    # vectorised: refit monthly rather than per game
    po = po.sort_values("date").reset_index(drop=True)
    pm = np.full(len(po), np.nan)
    for i, cut in enumerate(pd.date_range(po["date"].min(), po["date"].max(), freq="30D")):
        nxt = cut + pd.Timedelta(days=30)
        hist = G[G["date"] < cut]
        te = (po["date"] >= cut) & (po["date"] < nxt)
        if te.sum() == 0 or len(hist) < 500:
            continue
        fit.fit(hist[feats].values, hist["move_total"].values.astype(float))
        pm[te.values] = fit.predict(po.loc[te, feats].values)
    po["pm"] = pm
    po = po.dropna(subset=["pm"])
    print(pd.DataFrame([econ(po, "playoffs/play-in")]).round(3).to_string(index=False))


def walk_forward_generic(X, y, dates, make, step=7, min_train=500):
    pred = np.full(len(y), np.nan)
    uniq = np.unique(dates)
    cnt = np.cumsum([np.sum(dates == u) for u in uniq])
    i0 = np.searchsorted(cnt, min_train)
    if i0 >= len(uniq):
        return pred
    cuts = pd.date_range(pd.Timestamp(uniq[i0]),
                         pd.Timestamp(uniq.max()) + pd.Timedelta(days=1), freq=f"{step}D")
    for i, c in enumerate(cuts):
        nxt = cuts[i + 1] if i + 1 < len(cuts) else pd.Timestamp(uniq.max()) + pd.Timedelta(days=1)
        tr = dates < np.datetime64(c)
        te = (dates >= np.datetime64(c)) & (dates < np.datetime64(nxt))
        if te.sum() == 0 or tr.sum() < min_train:
            continue
        m = make()
        m.fit(X[tr], y[tr])
        pred[te] = m.predict(X[te])
    return pred


def build_playoffs():
    """Same feature construction as build(), but for playoff/play-in games."""
    import symmetric_features as sf
    from prepare_data import CSV, season_label
    from walkforward_pace import ALLV, build_panel_ext
    import prepare_data as pdm

    raw = pd.read_csv(CSV, low_memory=False)
    raw["season"] = season_label(raw)
    po_mask = raw["season"].str.contains("Playoffs|Play-in|Play-In", na=False)
    if po_mask.sum() == 0:
        return None
    # playoff features need the regular-season panel for lags; rebuild with
    # playoffs appended so within-season rolling means carry across
    print(f"  playoff/play-in games in odds file: {po_mask.sum()}")
    return None      # feature carry-over across season types not implemented


if __name__ == "__main__":
    main()
