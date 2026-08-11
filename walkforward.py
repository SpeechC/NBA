"""Walk-forward test of the paper's score model against the closing spread.

Takes the paper's best configuration -- 4 game-lags, the six selected features,
XGBoost -- and produces strictly out-of-sample predictions of each team's score,
then asks a single question: does the model's disagreement with the market
contain information the closing line has not already priced?

Totals are deliberately excluded. Overtime games are absent from dfMaster.csv, so
grading totals on this file is ex-post selection (closing totals go over only
47.95% of the time here, an artifact of the missing games). Spreads are unaffected
-- dropping overtime removes near-zero margins symmetrically -- so sides and
moneylines are testable today and totals are not.

Two leaks in the replication pipeline are removed here:
  * min-max normalisation over the whole season -> dropped entirely. It is an
    affine per-feature rescaling, and XGBoost's threshold splits are invariant to
    it, so removing it changes nothing about the model while removing the leak.
  * random 10-fold CV -> expanding-window refits, training only on games that
    finished before the game being predicted.
"""

import numpy as np
import pandas as pd
from scipy import stats
from xgboost import XGBRegressor

from prepare_data import VARS, CSV, season_label, _side

SEED = 42
LAG = 4
# the paper's six selected features (our ranking picked 3P% over ORB; see RESULTS.md)
FEATURES = ["DRB", "2P%", "FT%", "ORB", "AST", "3PA"]
REFIT_DAYS = 7
MIN_TRAIN = 2000
VIG_BREAKEVEN = 110 / 210  # risk 110 to win 100 => 52.38%


def build_panel():
    raw = pd.read_csv(CSV, low_memory=False)
    raw["season"] = season_label(raw)
    # In-Season Tournament games are regular-season games with their own label
    keep = raw["season"].str.contains("Regular Season|In-Season", na=False)
    raw = raw[keep].copy()

    panel = pd.concat([_side(raw, "H"), _side(raw, "R")], ignore_index=True)
    panel = panel.sort_values(["season", "team", "date", "game_id"]).reset_index(drop=True)
    panel[VARS] = panel[VARS].astype(float)
    panel["game_no"] = panel.groupby(["season", "team"]).cumcount() + 1

    # lag-4 means of the team's own previous games, raw scale (no normalisation)
    feats = (panel.groupby(["season", "team"])[VARS]
                  .apply(lambda g: g.shift(1).rolling(LAG).mean())
                  .reset_index(level=[0, 1], drop=True).sort_index())
    feats.columns = [f"f_{c}" for c in feats.columns]
    panel = pd.concat([panel, feats], axis=1)

    # season-to-date mean score, the naive benchmark the ML model has to beat
    panel["f_naive"] = (panel.groupby(["season", "team"])["Y"]
                             .transform(lambda s: s.shift(1).rolling(LAG).mean()))

    market = pd.DataFrame({
        "game_id": raw["GAME-ID"],
        "close_spread_h": pd.to_numeric(raw["CLOSING SPREAD_H"], errors="coerce"),
        "open_spread_h": pd.to_numeric(raw["OPENING SPREAD_H"], errors="coerce"),
        "ml_h": pd.to_numeric(raw["MONEYLINE_H"], errors="coerce"),
        "ml_r": pd.to_numeric(raw["MONEYLINE_R"], errors="coerce"),
    })
    return panel.dropna(subset=[f"f_{c}" for c in VARS]).reset_index(drop=True), market


def walk_forward_scores(panel):
    """Expanding-window refits; predict each team-game from games already played."""
    cols = [f"f_{c}" for c in FEATURES]
    X, y, dates = panel[cols].values, panel["Y"].values.astype(float), panel["date"].values
    pred = np.full(len(panel), np.nan)
    naive = np.full(len(panel), np.nan)

    order = np.argsort(dates)
    uniq = np.unique(dates)
    start = uniq[np.searchsorted(np.cumsum([np.sum(dates == d) for d in uniq]), MIN_TRAIN)]
    cuts = pd.date_range(pd.Timestamp(start), pd.Timestamp(uniq.max()) + pd.Timedelta(days=1),
                         freq=f"{REFIT_DAYS}D")

    model = XGBRegressor(max_depth=2, n_estimators=100, learning_rate=0.3,
                         subsample=1.0, colsample_bytree=0.8, random_state=SEED,
                         n_jobs=4, verbosity=0)
    for i, cut in enumerate(cuts):
        nxt = cuts[i + 1] if i + 1 < len(cuts) else pd.Timestamp(uniq.max()) + pd.Timedelta(days=1)
        tr = dates < np.datetime64(cut)
        te = (dates >= np.datetime64(cut)) & (dates < np.datetime64(nxt))
        if te.sum() == 0 or tr.sum() < MIN_TRAIN:
            continue
        model.fit(X[tr], y[tr])
        pred[te] = model.predict(X[te])
        naive[te] = panel["f_naive"].values[te]
    out = panel[["game_id", "team", "home", "season", "date", "Y"]].copy()
    out["pred"] = pred
    out["naive"] = naive
    return out.dropna(subset=["pred"])


def to_games(scores, market):
    h = scores[scores["home"] == 1].set_index("game_id")
    a = scores[scores["home"] == 0].set_index("game_id")
    g = pd.DataFrame({
        "season": h["season"], "date": h["date"],
        "actual_margin": h["Y"] - a["Y"],
        "model_margin": h["pred"] - a["pred"],
        "naive_margin": h["naive"] - a["naive"],
    }).dropna()
    g = g.join(market.set_index("game_id"), how="inner")
    # a spread of -4.5 for the home team means the market expects home to win by 4.5
    g["market_margin"] = -g["close_spread_h"]
    g["open_margin"] = -g["open_spread_h"]
    return g.dropna(subset=["market_margin"]).sort_values("date")


def calibrate(g):
    """Walk-forward affine calibration of model margin onto actual margin.

    The paper's model has no venue term, so its raw margin carries no home-court
    advantage and is on the wrong scale. Calibration coefficients are fit only on
    games that finished before the game being calibrated.
    """
    cal = np.full(len(g), np.nan)
    mm, am = g["model_margin"].values, g["actual_margin"].values
    seasons = g["season"].values
    for i in range(len(g)):
        if i < 500:
            continue
        A = np.column_stack([np.ones(i), mm[:i]])
        coef, *_ = np.linalg.lstsq(A, am[:i], rcond=None)
        cal[i] = coef[0] + coef[1] * mm[i]
    g = g.copy()
    g["cal_margin"] = cal
    return g.dropna(subset=["cal_margin"])


def american_to_prob(o):
    return np.where(o < 0, -o / (-o + 100), 100 / (o + 100))


def report(g):
    L = []
    L.append(f"Walk-forward games graded: **{len(g)}** "
             f"({g['date'].min().date()} to {g['date'].max().date()})\n")

    # --- 1. accuracy vs the market ---------------------------------------
    def rmse(a, b):
        return float(np.sqrt(np.mean((a - b) ** 2)))
    acc = pd.DataFrame({
        "RMSE": {
            "closing line": rmse(g["market_margin"], g["actual_margin"]),
            "model (calibrated)": rmse(g["cal_margin"], g["actual_margin"]),
            "naive 4-game scoring avg": rmse(g["naive_margin"], g["actual_margin"]),
        },
        "MAE": {
            "closing line": float(np.mean(np.abs(g["market_margin"] - g["actual_margin"]))),
            "model (calibrated)": float(np.mean(np.abs(g["cal_margin"] - g["actual_margin"]))),
            "naive 4-game scoring avg": float(np.mean(np.abs(g["naive_margin"] - g["actual_margin"]))),
        }})
    L.append("## 1. Margin accuracy, out of sample\n")
    L.append(acc.round(3).to_markdown() + "\n")

    # --- 2. incremental information over the line -------------------------
    # actual ~ market + model : does the model add anything the line lacks?
    Xf = np.column_stack([np.ones(len(g)), g["market_margin"], g["cal_margin"]])
    coef, *_ = np.linalg.lstsq(Xf, g["actual_margin"], rcond=None)
    resid = g["actual_margin"] - Xf @ coef
    dof = len(g) - Xf.shape[1]
    s2 = float(resid @ resid) / dof
    se = np.sqrt(np.diag(s2 * np.linalg.inv(Xf.T @ Xf)))
    tvals = coef / se
    inc = pd.DataFrame({"coef": coef, "std err": se, "t": tvals,
                        "p": 2 * (1 - stats.t.cdf(np.abs(tvals), dof))},
                       index=["intercept", "market margin", "model margin"])
    L.append("## 2. Does the model add information the closing line lacks?\n")
    L.append("Regression of actual margin on the closing line and the model:\n")
    L.append(inc.round(4).to_markdown() + "\n")
    L.append(f"\nIf the market has already priced everything the model knows, the "
             f"**model margin** coefficient is 0 and the **market margin** coefficient is 1. "
             f"Observed: model {coef[2]:+.4f} (t = {tvals[2]:.2f}, p = {inc['p'].iloc[2]:.3f}), "
             f"market {coef[1]:+.4f}.\n")

    # --- 3. the edge signal ----------------------------------------------
    g = g.copy()
    g["signal"] = g["cal_margin"] - g["market_margin"]
    g["home_cover"] = g["actual_margin"] > g["market_margin"]
    push = g["actual_margin"] == g["market_margin"]
    gg = g[~push]
    # bet the side the model favours
    gg = gg.assign(bet_home=gg["signal"] > 0)
    gg = gg.assign(win=np.where(gg["bet_home"], gg["home_cover"], ~gg["home_cover"]))

    bins = [-np.inf, -6, -3, 3, 6, np.inf]
    labels = ["< -6", "-6 to -3", "-3 to +3", "+3 to +6", "> +6"]
    gg = gg.assign(bucket=pd.cut(gg["signal"], bins, labels=labels))
    tab = gg.groupby("bucket", observed=True).agg(
        n=("home_cover", "size"), home_cover_pct=("home_cover", lambda s: 100 * s.mean()))
    tab["se"] = (np.sqrt(0.25 / tab["n"]) * 100).round(2)
    L.append("## 3. Model-market disagreement vs outcome\n")
    L.append("Signal = calibrated model margin − closing market margin. "
             "Positive means the model likes the home team more than the market does.\n")
    L.append(tab.round(2).to_markdown() + "\n")
    L.append("\nA monotone rise in home cover % across buckets is what a real edge looks like.\n")

    # --- 3b. is the "disagreement" really disagreement? -------------------
    sd_cal, sd_mkt = g["cal_margin"].std(), g["market_margin"].std()
    r_sig_mkt = np.corrcoef(g["signal"], g["market_margin"])[0, 1]
    r_cal_mkt = np.corrcoef(g["cal_margin"], g["market_margin"])[0, 1]
    L.append("\n**Diagnostic — what the signal actually measures**\n")
    L.append(pd.DataFrame({"value": {
        "SD of calibrated model margin": sd_cal,
        "SD of closing market margin": sd_mkt,
        "corr(model margin, market margin)": r_cal_mkt,
        "corr(signal, market margin)": r_sig_mkt,
    }}).round(3).to_markdown() + "\n")
    L.append(f"\nThe model's margin varies over a range only {sd_cal / sd_mkt:.0%} as wide as the "
             f"market's, so the difference between them is dominated by the market number: "
             f"corr(signal, market margin) = {r_sig_mkt:.2f}. Bucketing on the signal therefore "
             f"sorts games mostly by *how big a favourite the home team is*, not by how much the "
             f"model disagrees. That is why the bucket table trends opposite to the regression "
             f"coefficient in section 2 — the buckets are picking up favourite/underdog effects. "
             f"Section 2 is the trustworthy test, because it holds the market line fixed.\n")

    # --- 3c. the corrected bucket test -----------------------------------
    # residualise the model margin against the market line so the signal carries
    # only what the model says *beyond* the line
    A = np.column_stack([np.ones(len(gg)), gg["market_margin"]])
    b, *_ = np.linalg.lstsq(A, gg["cal_margin"], rcond=None)
    gg = gg.assign(ortho=gg["cal_margin"] - A @ b)
    obins = gg["ortho"].quantile([0, .2, .4, .6, .8, 1.0]).values.copy()
    obins[0], obins[-1] = -np.inf, np.inf
    gg = gg.assign(obucket=pd.cut(gg["ortho"], obins,
                                  labels=["most anti-home", "2", "3", "4", "most pro-home"]))
    otab = gg.groupby("obucket", observed=True).agg(
        n=("home_cover", "size"), home_cover_pct=("home_cover", lambda s: 100 * s.mean()))
    otab["se"] = (np.sqrt(0.25 / otab["n"]) * 100).round(2)
    L.append("\n**Corrected test — disagreement orthogonal to the line, quintiles**\n")
    L.append(otab.round(2).to_markdown() + "\n")
    L.append("\nThis is the version of the bucket test worth reading: it asks whether the part "
             "of the model's opinion that the line does *not* already contain predicts covers.\n")

    wr = gg["win"].mean()
    n = len(gg)
    z = (wr - VIG_BREAKEVEN) / np.sqrt(0.25 / n)
    roi = wr * (100 / 110) - (1 - wr)
    L.append("## 4. Betting the model's side, flat stakes at -110\n")
    rows = {"all games": gg}
    for lab in labels[::-1][:2] + labels[:2]:
        sub = gg[gg["bucket"] == lab]
        if len(sub):
            rows[f"signal bucket {lab}"] = sub
    rows["|signal| > 3"] = gg[gg["signal"].abs() > 3]
    rows["|signal| > 6"] = gg[gg["signal"].abs() > 6]
    bt = pd.DataFrame({k: {
        "n": len(v), "win %": 100 * v["win"].mean(),
        "ROI %": 100 * (v["win"].mean() * (100 / 110) - (1 - v["win"].mean())),
    } for k, v in rows.items()}).T
    L.append(bt.round(2).to_markdown() + "\n")
    L.append(f"\nBreak-even at -110 is **{100 * VIG_BREAKEVEN:.2f}%**. Overall "
             f"{100 * wr:.2f}% on n = {n} (z = {z:+.2f} vs break-even), ROI {100 * roi:+.2f}%.\n")

    # --- 5. per season ----------------------------------------------------
    ps = gg.groupby("season").agg(n=("win", "size"), win_pct=("win", lambda s: 100 * s.mean()))
    ps["ROI %"] = ps["win_pct"] / 100 * (100 / 110) - (1 - ps["win_pct"] / 100)
    ps["ROI %"] *= 100
    L.append("## 5. By season\n")
    L.append(ps.round(2).to_markdown() + "\n")

    # --- 6. closing line value -------------------------------------------
    cl = gg.dropna(subset=["open_margin"]).copy()
    # did the line move toward the side we bet, between open and close?
    cl["move"] = cl["market_margin"] - cl["open_margin"]
    cl["clv"] = np.where(cl["bet_home"], cl["move"], -cl["move"])
    L.append("## 6. Closing line value\n")
    L.append(f"Betting the model's side at the **opening** number, the line then moved "
             f"in our favour by **{cl['clv'].mean():+.3f}** points on average "
             f"(n = {len(cl)}, {100 * (cl['clv'] > 0).mean():.1f}% of bets got positive CLV). "
             f"Sustained positive CLV is the strongest single sign of a real edge.\n")

    # --- 7. moneyline -----------------------------------------------------
    ml = gg.dropna(subset=["ml_h", "ml_r"]).copy()
    sd = float(np.std(ml["actual_margin"] - ml["cal_margin"]))
    ml["p_home"] = stats.norm.cdf(ml["cal_margin"] / sd)
    ph = american_to_prob(ml["ml_h"].values)
    pa = american_to_prob(ml["ml_r"].values)
    ml["mkt_p_home"] = ph / (ph + pa)  # de-vigged
    ml["edge"] = ml["p_home"] - ml["mkt_p_home"]
    ml["home_win"] = ml["actual_margin"] > 0
    ml["bet_home"] = ml["edge"] > 0
    ml["win"] = np.where(ml["bet_home"], ml["home_win"], ~ml["home_win"])
    odds = np.where(ml["bet_home"], ml["ml_h"], ml["ml_r"])
    payout = np.where(odds > 0, odds / 100, 100 / -odds)
    ml["profit"] = np.where(ml["win"], payout, -1.0)
    mrow = {}
    for thr in [0.0, 0.02, 0.05]:
        sub = ml[ml["edge"].abs() > thr]
        mrow[f"|edge| > {thr:.0%}"] = {"n": len(sub), "win %": 100 * sub["win"].mean(),
                                       "ROI %": 100 * sub["profit"].mean()}
    L.append("## 7. Moneyline\n")
    L.append(f"Model win probability from the calibrated margin with sigma = {sd:.2f} points, "
             f"against the de-vigged market probability.\n")
    L.append(pd.DataFrame(mrow).T.round(2).to_markdown() + "\n")

    # calibration check
    ml["decile"] = pd.qcut(ml["p_home"], 10, duplicates="drop")
    calib = ml.groupby("decile", observed=True).agg(
        n=("home_win", "size"), predicted=("p_home", "mean"), actual=("home_win", "mean"))
    L.append("\n**Calibration of the model's home-win probability**\n")
    L.append((calib.assign(predicted=lambda d: (100 * d["predicted"]).round(1),
                           actual=lambda d: (100 * d["actual"]).round(1))).to_markdown() + "\n")
    return "\n".join(L), gg


def main():
    panel, market = build_panel()
    print(f"team-games with lag-{LAG} features: {len(panel)}", flush=True)
    scores = walk_forward_scores(panel)
    print(f"walk-forward team-game predictions: {len(scores)}", flush=True)
    g = to_games(scores, market)
    print(f"games with a closing spread: {len(g)}", flush=True)
    g = calibrate(g)
    text, gg = report(g)
    header = ("# Walk-forward test: the paper's score model vs the closing spread\n\n"
              "Totals are excluded because overtime games are missing from the source "
              "file; see README. Spreads and moneylines are unaffected.\n\n")
    open("BETTING.md", "w").write(header + text)
    gg.to_csv("walkforward_games.csv", index=False)
    print(text)


if __name__ == "__main__":
    main()
