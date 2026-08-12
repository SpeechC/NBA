"""Does training on the BETTING OUTCOME beat training on the line move?

Every model in this project predicts `move_total` under squared loss, then gets
thresholded on |pred| and bet by sign. Three layers sit between the objective and
the payoff, and squared loss on the move treats a 6-point move exactly 36x more
seriously than a 1-point move — when both pay identically if the sign is right.

The aligned alternative: train directly on whether the bet won, under logistic
loss. Every game then contributes according to whether we won it. A blowout and a
one-point game carry the same weight, which is correct, because they pay the same.

    baseline   ridge on move_total          -> bet sign(pred)
    reframed   logistic on (over hit @open) -> bet sign(p - 0.5)

The two produce differently scaled confidence — points versus probability — so
comparing them at a shared numeric threshold is meaningless. They are compared at
MATCHED BET COUNTS instead: top k% of games by each model's own confidence.

DEVELOPMENT ONLY. Choosing a target is model selection.

⚠ Expect tension, not a free win. The move is predictable (corr ~0.29) but
front-runs a correction the market makes anyway. The outcome pays but is close to
unpredictable — the market is unbiased against it and a permutation-controlled
blind search found nothing. This test prices that trade-off explicitly.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

from sklearn.linear_model import LogisticRegressionCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

import data_split as ds
from models_frozen import SPECS, add_pace_terms, walk_forward
from symmetric_features import build

CS = np.logspace(-3, 1, 5)


def walk_logistic(X, y, dates, step=7, min_train=500):
    """Same protocol as models_frozen.walk_forward, logistic instead of ridge."""
    pred = np.full(len(y), np.nan)
    uniq = np.unique(dates)
    cnt = np.cumsum([np.sum(dates == u) for u in uniq])
    start = pd.Timestamp(uniq[np.searchsorted(cnt, min_train)])
    cuts = pd.date_range(start, pd.Timestamp(uniq.max()) + pd.Timedelta(days=1),
                         freq=f"{step}D")
    for i, c in enumerate(cuts):
        nxt = (cuts[i + 1] if i + 1 < len(cuts)
               else pd.Timestamp(uniq.max()) + pd.Timedelta(days=1))
        tr = dates < np.datetime64(c)
        te = (dates >= np.datetime64(c)) & (dates < np.datetime64(nxt))
        if te.sum() == 0 or tr.sum() < min_train or len(np.unique(y[tr])) < 2:
            continue
        m = make_pipeline(StandardScaler(),
                          LogisticRegressionCV(Cs=CS, cv=3, max_iter=300,
                                               scoring="neg_log_loss", n_jobs=1))
        m.fit(X[tr], y[tr])
        pred[te] = m.predict_proba(X[te])[:, 1]
    return pred


def metrics(s, side, label, k):
    over = (s["actual_total"] > s["open_total"]).values
    win = np.where(side > 0, over, ~over).astype(float)
    clv = np.where(side > 0, s["move_total"], -s["move_total"])
    w = win.mean()
    return {"model": label, "top %": k, "bets": len(s),
            "CLV": round(clv.mean(), 3),
            "win %": round(100 * w, 2),
            "ROI110 %": round(100 * (w * (100 / 110) - (1 - w)), 2),
            "ROI105 %": round(100 * (w * (100 / 105) - (1 - w)), 2)}


def main():
    G = add_pace_terms(build()).sort_values("date").reset_index(drop=True)
    for spec in ("A", "D"):
        feats = SPECS[spec]
        d = G.dropna(subset=feats + ["move_total", "actual_total", "open_total"])
        d = d.sort_values("date").reset_index(drop=True)
        X, dates = d[feats].values, d["date"].values

        d["pm"] = walk_forward(X, d["move_total"].values.astype(float), dates)
        y_bet = (d["actual_total"] > d["open_total"]).astype(int).values
        print(f"spec {spec}: fitting logistic on the betting outcome "
              f"(base rate {100*y_bet.mean():.2f}% over)...", flush=True)
        d["p_over"] = walk_logistic(X, y_bet, dates)

        d = d.dropna(subset=["pm", "p_over"]).copy()
        dev = ds.dev(d)
        dev = dev[dev["actual_total"] != dev["open_total"]]
        ds.assert_no_holdout(dev, what=f"target reframe, spec {spec}")

        rows = []
        for k in (100, 50, 30, 20, 10):
            n = int(len(dev) * k / 100)
            b = dev.reindex(dev["pm"].abs().sort_values(ascending=False).index[:n])
            rows.append(metrics(b, np.sign(b["pm"]).values,
                                "ridge on MOVE", k))
            conf = (dev["p_over"] - 0.5).abs()
            b2 = dev.reindex(conf.sort_values(ascending=False).index[:n])
            rows.append(metrics(b2, np.where(b2["p_over"] > 0.5, 1, -1),
                                "logistic on OUTCOME", k))
        t = pd.DataFrame(rows).sort_values(["top %", "model"],
                                           ascending=[False, True])
        print("\n" + "=" * 92)
        print(f"SPEC {spec} — development only, matched bet counts")
        print("=" * 92)
        print(t.to_string(index=False))

        agree = (np.sign(dev["pm"]) == np.where(dev["p_over"] > 0.5, 1, -1)).mean()
        r = np.corrcoef(dev["pm"], dev["p_over"])[0, 1]
        print(f"\n  the two models agree on side {100*agree:.1f}% of the time")
        print(f"  corr(move prediction, p_over) = {r:+.4f}")
        print(f"  logistic p_over range: {dev['p_over'].min():.3f} .. "
              f"{dev['p_over'].max():.3f}  (sd {dev['p_over'].std():.4f})\n")


if __name__ == "__main__":
    main()
