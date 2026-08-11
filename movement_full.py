"""Line-movement strategy over the full sample, with burn-in accounted for once.

The earlier version stacked four nested burn-in periods -- score model (2000
team-games), calibration (800), movement model (2000), then a second movement
model (1200) fitted on the already-burned-in output. Roughly 4700 of 7200 games
were consumed before the first bet, which is why the strategy appeared to span
only 2023-01 to 2024-04 rather than the full 2017-2024 data.

Here the whole chain runs in one pass and each stage uses the minimum burn-in it
actually needs. Everything remains strictly walk-forward: no stage ever sees a
game that had not finished at the time of the bet.

Note 2019-20 is absent from the source file entirely, so there is an unavoidable
gap between the 2018-19 and 2020-21 seasons.
"""

import numpy as np
import pandas as pd
from scipy import stats
from xgboost import XGBRegressor

from prepare_data import CSV, season_label
from rest_travel import FEATURES as RT
from walkforward_pace import ALLV, EXT
from walkforward_totals import build

SEED = 42

# Burn-in, reduced 2026-08-11 so the panel starts inside the 2017-18 season.
#
# The lagged box-score features need 6 games per team, so no game before
# 2017-10-25 can ever carry features -- that date is a hard floor. Only 481
# games exist in calendar 2017 after it. The previous settings (1500 team-games
# + 300 games = ~1050 games of burn-in) overshot that by more than double and
# put the panel's first game at 2018-04-03, discarding the whole 2017-18 season.
#
# These values cost ~250 games instead, starting the panel in early December
# 2017. The trade is real and one-directional: the score model's first
# predictions are now trained on ~150 games rather than ~750, so `dis_open` is
# noisier early in the sample. It is not leaky -- the walk-forward is intact and
# no game ever sees a later one. Later games are unaffected in what they train
# on; only the refit grid shifts.
SCORE_MIN = 300       # team-games (~150 games) before the score model predicts
CAL_MIN = 100         # games before calibration is available
MOVE_MIN = 500        # games before the movement model predicts (pred_move only,
                      # which specs A and D do not use -- see the write at the end)
REFIT_DAYS = 7


def clean_market(raw):
    cs = pd.to_numeric(raw["CLOSING SPREAD_H"], errors="coerce")
    os_ = pd.to_numeric(raw["OPENING SPREAD_H"], errors="coerce")
    ct = pd.to_numeric(raw["CLOSING TOTAL_H"], errors="coerce")
    ot = pd.to_numeric(raw["OPENING TOTAL_H"], errors="coerce")
    ok = (cs.abs() <= 25) & (os_.abs() <= 25) & ct.between(150, 300) & ot.between(150, 300)
    return pd.DataFrame({"game_id": raw["GAME-ID"], "close_total": ct, "open_total": ot,
                         "close_margin": -cs, "open_margin": -os_, "clean": ok})


def wf_xgb(X, y, dates, min_train, depth=3, n_est=150, lr=0.05):
    pred = np.full(len(y), np.nan)
    uniq = np.unique(dates)
    counts = np.cumsum([np.sum(dates == d) for d in uniq])
    idx = np.searchsorted(counts, min_train)
    if idx >= len(uniq):
        return pred
    cuts = pd.date_range(pd.Timestamp(uniq[idx]),
                         pd.Timestamp(uniq.max()) + pd.Timedelta(days=1), freq=f"{REFIT_DAYS}D")
    m = XGBRegressor(max_depth=depth, n_estimators=n_est, learning_rate=lr, subsample=0.8,
                     colsample_bytree=0.8, random_state=SEED, n_jobs=4, verbosity=0)
    for i, cut in enumerate(cuts):
        nxt = cuts[i + 1] if i + 1 < len(cuts) else pd.Timestamp(uniq.max()) + pd.Timedelta(days=1)
        tr = dates < np.datetime64(cut)
        te = (dates >= np.datetime64(cut)) & (dates < np.datetime64(nxt))
        if te.sum() == 0 or tr.sum() < min_train:
            continue
        m.fit(X[tr], y[tr])
        pred[te] = m.predict(X[te])
    return pred


def wf_calibrate(model, actual, min_train, step=25):
    out = np.full(len(model), np.nan)
    coef = None
    for i in range(min_train, len(model)):
        if coef is None or (i - min_train) % step == 0:
            A = np.column_stack([np.ones(i), model[:i]])
            coef, *_ = np.linalg.lstsq(A, actual[:i], rcond=None)
        out[i] = coef[0] + coef[1] * model[i]
    return out


def main():
    panel, _ = build()
    raw = pd.read_csv(CSV, low_memory=False)
    raw["season"] = season_label(raw)
    raw = raw[raw["season"].str.contains("Regular Season|In-Season", na=False)]
    mk = clean_market(raw)

    # ---- stage 1: team score model, walk-forward ---------------------------
    cols = ([f"f_{v}" for v in ALLV] + [f"f_{v}_opp" for v in EXT]
            + RT + [c + "_opp" for c in RT])
    panel = panel.sort_values("date").reset_index(drop=True)
    panel["pred"] = wf_xgb(panel[cols].values, panel["Y"].values.astype(float),
                           panel["date"].values, SCORE_MIN, depth=2, n_est=100, lr=0.3)
    sc = panel.dropna(subset=["pred"])
    print(f"stage 1 score preds: {len(sc)} team-games from {sc.date.min().date()}", flush=True)

    h = sc[sc.home == 1].set_index("game_id")
    a = sc[sc.home == 0].set_index("game_id")
    g = pd.DataFrame({"season": h["season"], "date": h["date"],
                      "actual_total": h["Y"] + a["Y"], "actual_margin": h["Y"] - a["Y"],
                      "model_total": h["pred"] + a["pred"],
                      "model_margin": h["pred"] - a["pred"]}).dropna().reset_index()
    g = g.merge(mk, on="game_id", how="inner")
    g = g[g["clean"]].sort_values("date").reset_index(drop=True)

    # ---- stage 2: calibrate the model's total to actual totals -------------
    g["cal_total"] = wf_calibrate(g["model_total"].values, g["actual_total"].values, CAL_MIN)
    g = g.dropna(subset=["cal_total"]).reset_index(drop=True)
    g["dis_open"] = g["cal_total"] - g["open_total"]
    g["move_total"] = g["close_total"] - g["open_total"]
    print(f"stage 2 calibrated: {len(g)} games from {g.date.min().date()}", flush=True)

    # ---- stage 3: model the move ------------------------------------------
    feats = ["open_total", "dis_open"]
    fm = panel[panel.home == 1][["game_id"] + [f"f_{v}" for v in ALLV]
                                + [f"f_{v}_opp" for v in EXT]]
    g = g.merge(fm, on="game_id", how="left")
    feats += [f"f_{v}" for v in ALLV] + [f"f_{v}_opp" for v in EXT]
    g = g.dropna(subset=feats).reset_index(drop=True)
    g["pred_move"] = wf_xgb(g[feats].values, g["move_total"].values.astype(float),
                            g["date"].values, MOVE_MIN)
    d = g.dropna(subset=["pred_move"]).reset_index(drop=True)
    print(f"stage 3 movement preds: {len(d)} games from {d.date.min().date()}", flush=True)

    # ---- evaluate ----------------------------------------------------------
    L = ["# Line-movement strategy over the full sample\n",
         "Burn-in is now applied once across the whole chain instead of four times "
         "in sequence. 2019-20 is absent from the source data, so there is a gap "
         "between 2018-19 and 2020-21.\n",
         f"\nBets graded from **{d.date.min().date()}** to **{d.date.max().date()}** "
         f"({len(d)} games with a prediction).\n"]

    L.append("\n## Coverage by season\n")
    cov = d.groupby("season").agg(games=("pred_move", "size"),
                                  first=("date", "min"), last=("date", "max"))
    L.append(cov.to_markdown() + "\n")

    rows = {}
    rng = np.random.default_rng(0)
    for lab, sub in [("all", d), ("|pred|>0.5", d[d.pred_move.abs() > 0.5]),
                     ("|pred|>1", d[d.pred_move.abs() > 1]),
                     ("|pred|>1.5", d[d.pred_move.abs() > 1.5])]:
        s = sub[sub.actual_total != sub.open_total]
        if len(s) < 100:
            continue
        over = (s.actual_total > s.open_total).values
        bet = (s.pred_move > 0).values
        win = np.where(bet, over, ~over).astype(float)
        n, w = len(win), win.mean()
        lo, hi = stats.beta.ppf([.025, .975], win.sum() + .5, n - win.sum() + .5)
        clv = np.where(sub.pred_move > 0, sub.move_total, -sub.move_total)
        se = clv.std() / np.sqrt(len(clv))
        bs = np.array([rng.choice(win, n, replace=True).mean() for _ in range(8000)])
        roi_bs = bs * (100 / 110) - (1 - bs)
        rows[lab] = {"n": n, "CLV": clv.mean(), "CLV lo": clv.mean() - 1.96 * se,
                     "CLV hi": clv.mean() + 1.96 * se,
                     "beat close %": 100 * (clv > 0).mean(),
                     "win %": 100 * w, "win lo": 100 * lo, "win hi": 100 * hi,
                     "ROI %": 100 * (w * (100 / 110) - (1 - w)),
                     "P(ROI>0) %": 100 * (roi_bs > 0).mean()}
    tab = pd.DataFrame(rows).T
    L.append("\n## Strategy performance\n")
    L.append(tab.round(3).to_markdown() + "\n")

    # per season, at the |pred|>1 threshold
    s = d[(d.pred_move.abs() > 1) & (d.actual_total != d.open_total)].copy()
    over = (s.actual_total > s.open_total).values
    s["win"] = np.where((s.pred_move > 0).values, over, ~over).astype(float)
    s["clv"] = np.where(s.pred_move > 0, s.move_total, -s.move_total)
    ps = s.groupby("season").agg(bets=("win", "size"),
                                 win_pct=("win", lambda x: 100 * x.mean()),
                                 clv=("clv", "mean"))
    ps["ROI %"] = (ps["win_pct"] / 100) * (100 / 110) - (1 - ps["win_pct"] / 100)
    ps["ROI %"] *= 100
    L.append("\n## Season by season at |pred| > 1\n")
    L.append(ps.round(2).to_markdown() + "\n")
    L.append(f"\nSeasons with a winning record: "
             f"**{int((ps['win_pct'] > 52.38).sum())} of {len(ps)}**. "
             f"Seasons with positive CLV: **{int((ps['clv'] > 0).sum())} of {len(ps)}**.\n")

    open("MOVEMENT_FULL.md", "w").write("\n".join(L))

    # Write `g`, not `d`. `d` has additionally dropped the MOVE_MIN=500 burn-in
    # games needed by the XGBoost `pred_move` column -- but the frozen ridge
    # specs A and D never use pred_move; they run their own walk-forward. Making
    # them pay that burn-in cost 500 games off the front of the panel and pushed
    # the development era's start from 2018-03 to 2019-01, losing all of 2017-18
    # and half of 2018-19 for no reason.
    #
    # pred_move is retained as a column and is NaN for those 500 games; anything
    # that consumes it must dropna, as the evaluation above already does.
    g.to_csv("movement_full_games.csv", index=False)
    print(f"\nwrote movement_full_games.csv: {len(g)} games from "
          f"{g.date.min().date()} ({len(d)} of them carry pred_move)")
    print("\n" + tab.round(3).to_string())
    print("\n" + ps.round(2).to_string())


if __name__ == "__main__":
    main()
