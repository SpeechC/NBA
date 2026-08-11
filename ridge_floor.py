"""Ridge as the linear floor on the totals-movement task.

The question this settles: is the functional form the binding constraint? If a
plain penalised linear model lands within noise of CatBoost and RandomForest, the
trees are fitting the same shallow signal with better variance control, and no
amount of model sophistication was ever going to change the earlier null results.
"""

import time
import warnings

import numpy as np
import pandas as pd
from sklearn.linear_model import RidgeCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")


def walk(X, y, dates, make, step=7, min_train=500):
    pred = np.full(len(y), np.nan)
    uniq = np.unique(dates)
    cnt = np.cumsum([np.sum(dates == u) for u in uniq])
    cuts = pd.date_range(pd.Timestamp(uniq[np.searchsorted(cnt, min_train)]),
                         pd.Timestamp(uniq.max()) + pd.Timedelta(days=1),
                         freq=f"{step}D")
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


def score(pred, y, label):
    m = ~np.isnan(pred)
    p, mv = pred[m], y[m]
    clv = np.where(p > 0, mv, -mv)
    se = clv.std() / np.sqrt(len(clv))
    sel = np.abs(p) > 1
    cs = np.where(p[sel] > 0, mv[sel], -mv[sel]) if sel.sum() else np.array([np.nan])
    return {"model": label, "n": int(m.sum()),
            "corr": float(np.corrcoef(p, mv)[0, 1]),
            "CLV": float(clv.mean()), "CLV lo": float(clv.mean() - 1.96 * se),
            "CLV hi": float(clv.mean() + 1.96 * se),
            "beat close %": float(100 * (clv > 0).mean()),
            "n>1": int(sel.sum()), "CLV>1": float(np.nanmean(cs))}


def main():
    d = pd.read_csv("movement_full_games.csv", parse_dates=["date"])
    d = d.sort_values("date").reset_index(drop=True)
    FE = ["open_total", "dis_open"] + [c for c in d.columns if c.startswith("f_")]
    d = d.dropna(subset=FE + ["move_total"]).reset_index(drop=True)
    X, y, dates = d[FE].values, d["move_total"].values.astype(float), d["date"].values

    t = time.time()
    p = walk(X, y, dates,
             lambda: make_pipeline(StandardScaler(), RidgeCV(alphas=np.logspace(-2, 3, 20))))
    r = score(p, y, "Ridge (linear floor)")
    print(f"fitted in {time.time() - t:.1f}s\n")

    ref = [
        {"model": "XGB fixed (as used)", "n": 4582, "corr": 0.2361, "CLV": 0.6046,
         "CLV lo": np.nan, "CLV hi": np.nan, "beat close %": 53.25, "n>1": 1245, "CLV>1": 1.2731},
        {"model": "XGB shallow/reg", "n": 4582, "corr": 0.2466, "CLV": 0.6253,
         "CLV lo": np.nan, "CLV hi": np.nan, "beat close %": np.nan, "n>1": 1232, "CLV>1": 1.3328},
        {"model": "CatBoost", "n": 4582, "corr": 0.2516, "CLV": 0.6373,
         "CLV lo": np.nan, "CLV hi": np.nan, "beat close %": np.nan, "n>1": 1123, "CLV>1": 1.4439},
        {"model": "RandomForest", "n": 4582, "corr": 0.2492, "CLV": 0.6734,
         "CLV lo": np.nan, "CLV hi": np.nan, "beat close %": np.nan, "n>1": 804, "CLV>1": 1.6057},
    ]
    print(pd.DataFrame([r] + ref).round(4).to_string(index=False))


if __name__ == "__main__":
    main()
