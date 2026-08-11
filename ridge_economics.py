"""Ridge on both movement markets: full decision metrics, not just CLV.

CLV is the leading indicator; ROI is the payoff. This reports both, plus the
binomial and bootstrap intervals that say whether the payoff is distinguishable
from zero, and a per-season breakdown so a single lucky year cannot carry it.

Bets are struck at the OPENING number and graded against it. Thresholds are all
reported, not just the flattering one -- threshold-shopping is the specific error
this project has criticised elsewhere.
"""

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import RidgeCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

RNG = np.random.default_rng(0)
BREAKEVEN = 110 / 210


def walk(X, y, dates, step=7, min_train=500):
    pred = np.full(len(y), np.nan)
    uniq = np.unique(dates)
    cnt = np.cumsum([np.sum(dates == u) for u in uniq])
    cuts = pd.date_range(pd.Timestamp(uniq[np.searchsorted(cnt, min_train)]),
                         pd.Timestamp(uniq.max()) + pd.Timedelta(days=1), freq=f"{step}D")
    for i, c in enumerate(cuts):
        nxt = cuts[i + 1] if i + 1 < len(cuts) else pd.Timestamp(uniq.max()) + pd.Timedelta(days=1)
        tr = dates < np.datetime64(c)
        te = (dates >= np.datetime64(c)) & (dates < np.datetime64(nxt))
        if te.sum() == 0 or tr.sum() < min_train:
            continue
        m = make_pipeline(StandardScaler(), RidgeCV(alphas=np.logspace(-2, 3, 20)))
        m.fit(X[tr], y[tr])
        pred[te] = m.predict(X[te])
    return pred


def economics(pred, move, actual, open_line, label, thresholds=(0, 0.5, 1, 1.5, 2)):
    rows = []
    keep = ~np.isnan(pred)
    pred, move, actual, open_line = pred[keep], move[keep], actual[keep], open_line[keep]
    for thr in thresholds:
        sel = np.abs(pred) > thr
        if sel.sum() < 100:
            continue
        p, mv, ac, ol = pred[sel], move[sel], actual[sel], open_line[sel]
        push = ac == ol
        p, mv, ac, ol = p[~push], mv[~push], ac[~push], ol[~push]
        over = ac > ol
        win = np.where(p > 0, over, ~over).astype(float)
        n, w = len(win), win.mean()
        lo, hi = stats.beta.ppf([.025, .975], win.sum() + .5, n - win.sum() + .5)
        bs = np.array([RNG.choice(win, n, replace=True).mean() for _ in range(8000)])
        roi_bs = bs * (100 / 110) - (1 - bs)
        clv = np.where(p > 0, mv, -mv)
        se = clv.std() / np.sqrt(len(clv))
        rows.append({
            "market": label, "threshold": thr, "n": n,
            "CLV": clv.mean(), "CLV lo": clv.mean() - 1.96 * se,
            "beat close %": 100 * (clv > 0).mean(),
            "win %": 100 * w, "win lo": 100 * lo, "win hi": 100 * hi,
            "ROI %": 100 * (w * (100 / 110) - (1 - w)),
            "ROI lo": 100 * np.percentile(roi_bs, 2.5),
            "ROI hi": 100 * np.percentile(roi_bs, 97.5),
            "P(ROI>0) %": 100 * (roi_bs > 0).mean()})
    return pd.DataFrame(rows)


def main():
    out = []

    # ---------- TOTALS ----------
    d = pd.read_csv("movement_full_games.csv", parse_dates=["date"]).sort_values("date")
    d = d.reset_index(drop=True)
    FE = ["open_total", "dis_open"] + [c for c in d.columns if c.startswith("f_")]
    d = d.dropna(subset=FE + ["move_total", "actual_total", "open_total"]).reset_index(drop=True)
    d["pm"] = walk(d[FE].values, d["move_total"].values.astype(float), d["date"].values)
    t = economics(d["pm"].values, d["move_total"].values, d["actual_total"].values,
                  d["open_total"].values, "TOTALS")
    out.append(t)
    print("=== TOTALS (ridge) ===")
    print(t.round(3).to_string(index=False))

    dd = d.dropna(subset=["pm"])
    sel = dd[dd["pm"].abs() > 1].copy()
    push = sel["actual_total"] == sel["open_total"]
    s = sel[~push]
    over = (s["actual_total"] > s["open_total"]).values
    s = s.assign(win=np.where((s["pm"] > 0).values, over, ~over).astype(float),
                 clv=np.where(s["pm"] > 0, s["move_total"], -s["move_total"]))
    ps = s.groupby("season").agg(n=("win", "size"), win_pct=("win", lambda x: 100 * x.mean()),
                                 clv=("clv", "mean"))
    ps["ROI %"] = 100 * ((ps["win_pct"] / 100) * (100 / 110) - (1 - ps["win_pct"] / 100))
    print("\nby season at |pred|>1:")
    print(ps.round(2).to_string())

    # ---------- SPREADS ----------
    sp = pd.read_parquet("/home/dpope/data/spread_movement.parquet").sort_values("date")
    sp = sp.reset_index(drop=True)
    FE2 = ["open_margin", "dis_open"] + [c for c in sp.columns if c.startswith("f_")]
    sp = sp.dropna(subset=FE2 + ["move", "actual_margin", "open_margin"]).reset_index(drop=True)
    sp["pm"] = walk(sp[FE2].values, sp["move"].values.astype(float), sp["date"].values)
    t2 = economics(sp["pm"].values, sp["move"].values, sp["actual_margin"].values,
                   sp["open_margin"].values, "SPREADS")
    out.append(t2)
    print("\n=== SPREADS / MONEYLINE (ridge) ===")
    print(t2.round(3).to_string(index=False))
    print("\n  (XGBoost gave CLV +0.155 all / +0.317 selective; break-even needs ~0.70)")

    print(f"\nbreak-even win rate at -110: {100 * BREAKEVEN:.2f}%")
    pd.concat(out).to_csv("ridge_economics.csv", index=False)


if __name__ == "__main__":
    main()
