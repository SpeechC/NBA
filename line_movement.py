"""Can we predict where the line closes?

Different target, different economics. Instead of forecasting a 12.7-point-SD game
outcome, forecast a 2.0-point-SD human process: the drift from the opening number
to the closing number. If that is predictable, you bet the opening price and
capture closing line value directly.

Data cleaning: the CLOSING SPREAD column contains 4 contaminated rows (values of
-110, 110, 112, 243 -- juice and totals leaking into the spread field). They are
dropped. Uncleaned, they inflate the market's margin RMSE from 13.06 to 13.46 and
make the opening line look more accurate than the closing line, which is backwards.

Two things are tested:
  1. Diagnostic -- does our score model's disagreement with the OPENING line
     predict the subsequent move? Our beat-the-close rate has been 42-44% across
     every configuration, which implies the signal anti-predicts movement. If that
     is stable, fading it produces positive CLV.
  2. A model of the move itself, from information available at open.

Note the economics: a bet placed at the open is graded against the OPENING number,
so CLV is a leading indicator, not the payoff. Both are reported.
"""

import numpy as np
import pandas as pd
from scipy import stats
from xgboost import XGBRegressor

from prepare_data import CSV, VARS, season_label
from rest_travel import FEATURES as RT
from walkforward import MIN_TRAIN, REFIT_DAYS, SEED, VIG_BREAKEVEN
from walkforward_pace import ALLV, EXT, walk_forward
from walkforward_totals import build, to_games
from scoreboard import wf_calibrate


def clean_market(raw):
    cs = pd.to_numeric(raw["CLOSING SPREAD_H"], errors="coerce")
    os_ = pd.to_numeric(raw["OPENING SPREAD_H"], errors="coerce")
    ct = pd.to_numeric(raw["CLOSING TOTAL_H"], errors="coerce")
    ot = pd.to_numeric(raw["OPENING TOTAL_H"], errors="coerce")
    ok = (cs.abs() <= 25) & (os_.abs() <= 25) & ct.between(150, 300) & ot.between(150, 300)
    return pd.DataFrame({
        "game_id": raw["GAME-ID"],
        "close_margin": -cs, "open_margin": -os_,
        "close_total": ct, "open_total": ot, "clean": ok,
    })


def wf_predict(df, cols, target, dates, min_train=MIN_TRAIN, step=REFIT_DAYS):
    """Expanding-window XGBoost, refit every `step` days."""
    X, y = df[cols].values, df[target].values.astype(float)
    pred = np.full(len(df), np.nan)
    uniq = np.unique(dates)
    counts = np.cumsum([np.sum(dates == d) for d in uniq])
    start = uniq[np.searchsorted(counts, min_train)]
    cuts = pd.date_range(pd.Timestamp(start), pd.Timestamp(uniq.max()) + pd.Timedelta(days=1),
                         freq=f"{step}D")
    model = XGBRegressor(max_depth=3, n_estimators=150, learning_rate=0.05,
                         subsample=0.8, colsample_bytree=0.8, random_state=SEED,
                         n_jobs=4, verbosity=0)
    for i, cut in enumerate(cuts):
        nxt = cuts[i + 1] if i + 1 < len(cuts) else pd.Timestamp(uniq.max()) + pd.Timedelta(days=1)
        tr = dates < np.datetime64(cut)
        te = (dates >= np.datetime64(cut)) & (dates < np.datetime64(nxt))
        if te.sum() == 0 or tr.sum() < min_train:
            continue
        model.fit(X[tr], y[tr])
        pred[te] = model.predict(X[te])
    return pred


def main():
    panel, _ = build()
    raw = pd.read_csv(CSV, low_memory=False)
    raw["season"] = season_label(raw)
    raw = raw[raw["season"].str.contains("Regular Season|In-Season", na=False)]
    mk = clean_market(raw)

    # score model (best variant) -> its opinion, calibrated to actual margins
    cols = ([f"f_{v}" for v in ALLV] + [f"f_{v}_opp" for v in EXT]
            + RT + [c + "_opp" for c in RT])
    scores = walk_forward(panel, cols)
    h = scores[scores["home"] == 1].set_index("game_id")
    a = scores[scores["home"] == 0].set_index("game_id")
    g = pd.DataFrame({
        "season": h["season"], "date": h["date"],
        "actual_margin": h["Y"] - a["Y"], "actual_total": h["Y"] + a["Y"],
        "model_margin": h["pred"] - a["pred"], "model_total": h["pred"] + a["pred"],
    }).dropna().reset_index()
    g = g.merge(mk, on="game_id", how="inner")
    g = g[g["clean"]].sort_values("date").reset_index(drop=True)
    g["cal_margin"] = wf_calibrate(g["model_margin"].values, g["actual_margin"].values)
    g["cal_total"] = wf_calibrate(g["model_total"].values, g["actual_total"].values)
    g = g.dropna(subset=["cal_margin", "open_margin", "close_margin"]).reset_index(drop=True)

    g["move"] = g["close_margin"] - g["open_margin"]
    g["move_total"] = g["close_total"] - g["open_total"]
    g["dis_open"] = g["cal_margin"] - g["open_margin"]
    g["dis_open_total"] = g["cal_total"] - g["open_total"]

    L = ["# Modelling the closing line move\n",
         f"Cleaned sample: **{len(g)}** games. Spread move SD "
         f"**{g['move'].std():.2f}**, total move SD **{g['move_total'].std():.2f}** — "
         f"far smaller targets than a game outcome (margin SD ~13).\n"]

    # ---- 1. diagnostic: does our score signal predict the move? -----------
    L.append("\n## 1. Does the score model's disagreement predict the move?\n")
    rows = {}
    for lab, dis, mv in [("spread", g["dis_open"], g["move"]),
                         ("total", g["dis_open_total"], g["move_total"])]:
        X = np.column_stack([np.ones(len(g)), dis])
        c, *_ = np.linalg.lstsq(X, mv, rcond=None)
        r = mv - X @ c
        se = np.sqrt(np.diag(float(r @ r) / (len(g) - 2) * np.linalg.inv(X.T @ X)))
        agree = float(np.mean(np.sign(dis) == np.sign(mv)))
        rows[lab] = {"slope": c[1], "t": c[1] / se[1],
                     "corr": float(np.corrcoef(dis, mv)[0, 1]),
                     "move agrees with model %": 100 * agree}
    L.append(pd.DataFrame(rows).T.round(4).to_markdown() + "\n")
    L.append("\nA positive slope means the line moves *toward* the model's opinion "
             "(the model anticipates the market). Negative means the line moves away "
             "— the model is on the wrong side of the flow, which is what a "
             "42-44% beat-the-close rate implied.\n")

    # ---- 2. model the move directly ---------------------------------------
    feat = (["open_margin", "dis_open"]
            + [f"f_{v}" for v in ALLV] + [f"f_{v}_opp" for v in EXT])
    gm = g.merge(panel[panel.home == 1][["game_id"] + [f"f_{v}" for v in ALLV]
                                        + [f"f_{v}_opp" for v in EXT]],
                 on="game_id", how="left").dropna(subset=feat).reset_index(drop=True)
    dates = gm["date"].values
    gm["pred_move"] = wf_predict(gm, feat, "move", dates)
    gm = gm.dropna(subset=["pred_move"])

    L.append(f"\n## 2. Predicting the spread move directly ({len(gm)} games)\n")
    base = float(np.sqrt(np.mean(gm["move"] ** 2)))
    mod = float(np.sqrt(np.mean((gm["move"] - gm["pred_move"]) ** 2)))
    corr = float(np.corrcoef(gm["pred_move"], gm["move"])[0, 1])
    sign = float(np.mean(np.sign(gm["pred_move"]) == np.sign(gm["move"])))
    L.append(pd.DataFrame({"value": {
        "RMSE predicting no move (baseline)": base,
        "RMSE of the model": mod,
        "R2 vs baseline %": 100 * (1 - (mod / base) ** 2),
        "corr(predicted, actual move)": corr,
        "direction called correctly %": 100 * sign,
    }}).round(4).to_markdown() + "\n")

    # ---- 3. economics: bet the open on the predicted direction ------------
    d = gm[gm["actual_margin"] != gm["open_margin"]].copy()
    bet_home = d["pred_move"] > 0
    clv = np.where(bet_home, d["move"], -d["move"])
    cover_open = d["actual_margin"] > d["open_margin"]
    win = np.where(bet_home, cover_open, ~cover_open).astype(float)
    wr = win.mean()
    se = clv.std() / np.sqrt(len(clv))
    L.append("\n## 3. Economics of betting the opening number\n")
    L.append(pd.DataFrame({"value": {
        "n bets": len(d),
        "CLV pts": clv.mean(),
        "CLV 95% lo": clv.mean() - 1.96 * se,
        "CLV 95% hi": clv.mean() + 1.96 * se,
        "beat the close %": 100 * (clv > 0).mean(),
        "win rate vs opening number %": 100 * wr,
        "ROI at -110 %": 100 * (wr * (100 / 110) - (1 - wr)),
        "break-even %": 100 * VIG_BREAKEVEN,
    }}).round(4).to_markdown() + "\n")
    L.append("\nA bet struck at the open is graded against the **opening** number, so "
             "CLV is the leading indicator and the win rate is the payoff. Positive CLV "
             "with a break-even win rate still means the signal is finding real "
             "information — it just has not converted yet.\n")

    open("LINE_MOVEMENT.md", "w").write("\n".join(L))
    gm.to_csv("line_movement_games.csv", index=False)
    print("\n".join(L))


if __name__ == "__main__":
    main()
