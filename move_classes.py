"""Is there a CLASS of games that drives large CLV?

A different framing from everything so far. The frozen model predicts the signed
move and we select on |prediction| -- i.e. we select on MODEL CONFIDENCE. This
asks instead whether there are identifiable GAME TYPES where the line reliably
moves a lot, and whether our direction call is any good inside them.

Two conditions must both hold for a class to be worth anything:
  1. large moves        -- otherwise there is no CLV to capture
  2. predictable direction -- a large move called wrong is large NEGATIVE CLV

Note this is NOT the variance test we already ran. That asked whether the
GAME OUTCOME's dispersion around the line was predictable (it was not).
This asks whether the LINE's own movement magnitude is predictable, which is a
different quantity and untested.

Part 1 -- descriptive: CLV within strata of pre-specified class variables.
Part 2 -- two-stage: a magnitude model x a direction model, versus the single
          regression-plus-threshold we use now.
"""

import warnings

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LogisticRegression, RidgeCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from models_frozen import SPECS, add_pace_terms, walk_forward
from symmetric_features import build

warnings.filterwarnings("ignore")
RNG = np.random.default_rng(0)
THRESH = 1.25


def clv_stats(s):
    """CLV and betting metrics for a set of games already carrying `pm`."""
    if len(s) < 40:
        return None
    over = (s["actual_total"] > s["open_total"]).values
    win = np.where((s["pm"] > 0).values, over, ~over).astype(float)
    clv = np.where(s["pm"] > 0, s["move_total"], -s["move_total"])
    w = win.mean()
    return {"n": len(s), "mean |move|": s["move_total"].abs().mean(),
            "CLV": clv.mean(), "beat close %": 100 * (clv > 0).mean(),
            "win %": 100 * w, "ROI %": 100 * (w * (100 / 110) - (1 - w))}


def main():
    G = add_pace_terms(build())
    feats = SPECS["A"]
    G = G.dropna(subset=feats + ["move_total", "actual_total", "open_total"])
    G = G.sort_values("date").reset_index(drop=True)
    G["pm"] = walk_forward(G[feats].values, G["move_total"].values.astype(float),
                           G["date"].values)
    d = G.dropna(subset=["pm"]).copy()
    d["abs_move"] = d["move_total"].abs()
    d["game_no"] = d.groupby(["season"]).cumcount()

    print(f"games {len(d):,}   mean |move| {d['abs_move'].mean():.3f}   "
          f"sd {d['move_total'].std():.3f}\n")

    # ---------- PART 1: does |move| even vary predictably by class? ----------
    classes = {
        "|implied - open|": d["implied_minus_open"].abs(),
        "|dis_open|": d["dis_open"].abs(),
        "opening total level": d["open_total"],
        "combined pace": d["pace_sum"],
        "|pace mismatch|": d["pace_absdiff"],
        "days into season": d["game_no"],
    }
    print("=" * 104)
    print("PART 1 — mean |move| and our CLV, by quintile of each candidate class")
    print("=" * 104)
    for name, v in classes.items():
        d["_q"] = pd.qcut(v, 5, labels=[1, 2, 3, 4, 5], duplicates="drop")
        rows = []
        for q, sub in d.groupby("_q", observed=True):
            bets = sub[(sub["pm"].abs() > THRESH) &
                       (sub["actual_total"] != sub["open_total"])]
            st = clv_stats(bets)
            rows.append({"quintile": q, "n games": len(sub),
                         "mean |move| (all)": sub["abs_move"].mean(),
                         "bets": st["n"] if st else 0,
                         "CLV": st["CLV"] if st else np.nan,
                         "win %": st["win %"] if st else np.nan,
                         "ROI %": st["ROI %"] if st else np.nan})
        t = pd.DataFrame(rows)
        spread = t["mean |move| (all)"].iloc[-1] - t["mean |move| (all)"].iloc[0]
        print(f"\n--- {name}   (|move| spread across quintiles: {spread:+.3f}) ---")
        print(t.round(3).to_string(index=False))

    # ---------- PART 2: two-stage, magnitude x direction ----------
    print("\n" + "=" * 104)
    print("PART 2 — two-stage (predict magnitude, then direction) vs the single model")
    print("=" * 104)

    # stage 1: predict |move| walk-forward
    d = d.reset_index(drop=True)
    d["pred_mag"] = walk_forward(d[feats].values, d["abs_move"].values.astype(float),
                                 d["date"].values)
    # stage 2: predict direction (sign) with regularised logistic, walk-forward
    y_dir = (d["move_total"] > 0).astype(int).values
    pdir = np.full(len(d), np.nan)
    dates = d["date"].values
    uniq = np.unique(dates)
    cnt = np.cumsum([np.sum(dates == u) for u in uniq])
    cuts = pd.date_range(pd.Timestamp(uniq[np.searchsorted(cnt, 500)]),
                         pd.Timestamp(uniq.max()) + pd.Timedelta(days=1), freq="7D")
    X = d[feats].values
    for i, c in enumerate(cuts):
        nxt = cuts[i + 1] if i + 1 < len(cuts) else pd.Timestamp(uniq.max()) + pd.Timedelta(days=1)
        tr = dates < np.datetime64(c)
        te = (dates >= np.datetime64(c)) & (dates < np.datetime64(nxt))
        if te.sum() == 0 or tr.sum() < 500:
            continue
        m = make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=500))
        m.fit(X[tr], y_dir[tr])
        pdir[te] = m.predict_proba(X[te])[:, 1]
    d["p_up"] = pdir
    dd = d.dropna(subset=["pred_mag", "p_up"]).copy()
    dd["pm2"] = np.where(dd["p_up"] > 0.5, 1, -1)          # direction call
    dd["conf"] = (dd["p_up"] - 0.5).abs()

    rows = [{"strategy": "single model, |pred|>1.25",
             **clv_stats(dd[(dd["pm"].abs() > THRESH) &
                            (dd["actual_total"] != dd["open_total"])])}]
    for mq, cq in ((0.6, 0.0), (0.6, 0.02), (0.75, 0.0), (0.75, 0.02), (0.9, 0.05)):
        sel = dd[(dd["pred_mag"] > dd["pred_mag"].quantile(mq)) &
                 (dd["conf"] > cq) & (dd["actual_total"] != dd["open_total"])].copy()
        sel["pm"] = sel["pm2"]
        st = clv_stats(sel)
        if st:
            rows.append({"strategy": f"two-stage: mag>q{int(mq*100)}, conf>{cq}", **st})
    print(pd.DataFrame(rows).round(3).to_string(index=False))
    print(f"\n  magnitude model: corr(pred |move|, actual |move|) = "
          f"{np.corrcoef(dd['pred_mag'], dd['abs_move'])[0, 1]:.4f}")
    print(f"  direction model: AUC-equivalent accuracy = "
          f"{100 * ((dd['p_up'] > 0.5) == (dd['move_total'] > 0)).mean():.2f}%")


if __name__ == "__main__":
    main()
