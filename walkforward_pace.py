"""Paper-faithful extension: add pace/efficiency variables, test vs the closing line.

The paper's designed-feature recipe is kept exactly — each predictor is the mean of
a team variable over the previous LAG games, feature selection is the paper's
ensemble (MARS + XGBoost + SGB average rank, keep 40% of variables), the learner is
XGBoost — and evaluation is strictly walk-forward against the closing spread, as
in walkforward.py. Totals stay excluded until overtime games are restored.

New variables from the file (verified: PTS = POSS*OEFF/100 exactly; DEFF_H equals
the opponent's OEFF; POSS==PACE here because overtime games are absent):
    PACE  possessions per 48 (shared by both teams in a game)
    OEFF  own points per 100 possessions
    DEFF  points allowed per 100 possessions

The precomputed TEAM_* rolling columns in the file are NOT used — their windows
are undocumented and may include the current game (leakage risk).

Variants:
    paper6     the paper's six selected features (baseline, same harness)
    paper13    all 13 paper variables
    pace16     13 + PACE/OEFF/DEFF, all own-team (paper framework, new variables)
    pace_sel   two-stage: top 40% of the 16 by ensemble rank -> 7 features,
               ranked on the initial training window only (no selection leak)
    matchup    pace16 + the OPPONENT's lagged PACE/OEFF/DEFF -- the extension the
               paper names as future work; the only variant that can see a matchup
"""

import math

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import GradientBoostingRegressor
from xgboost import XGBRegressor

from mars_elm import Earth
from prepare_data import CSV, VARS, season_label, _side
from walkforward import (LAG, MIN_TRAIN, REFIT_DAYS, SEED, VIG_BREAKEVEN,
                         calibrate, to_games)

EXT = ["PACE", "OEFF", "DEFF"]
ALLV = VARS + EXT


def build_panel_ext():
    raw = pd.read_csv(CSV, low_memory=False)
    raw["season"] = season_label(raw)
    raw = raw[raw["season"].str.contains("Regular Season|In-Season", na=False)].copy()

    sides = []
    for suf in ["H", "R"]:
        s = _side(raw, suf)
        for v in EXT:
            s[v] = pd.to_numeric(raw[f"{v}_{suf}"], errors="coerce").values
        sides.append(s)
    panel = pd.concat(sides, ignore_index=True)
    panel = panel.sort_values(["season", "team", "date", "game_id"]).reset_index(drop=True)
    panel[ALLV] = panel[ALLV].astype(float)

    feats = (panel.groupby(["season", "team"])[ALLV]
                  .apply(lambda g: g.shift(1).rolling(LAG).mean())
                  .reset_index(level=[0, 1], drop=True).sort_index())
    feats.columns = [f"f_{c}" for c in feats.columns]
    panel = pd.concat([panel, feats], axis=1)
    panel["f_naive"] = (panel.groupby(["season", "team"])["Y"]
                             .transform(lambda s: s.shift(1).rolling(LAG).mean()))
    panel = panel.dropna(subset=[f"f_{c}" for c in ALLV]).reset_index(drop=True)

    # opponent's lagged features, joined through the other row of the same game
    fcols = [f"f_{c}" for c in EXT]
    opp = panel[["game_id", "home"] + fcols].copy()
    opp["home"] = 1 - opp["home"]
    opp = opp.rename(columns={c: c + "_opp" for c in fcols})
    panel = panel.merge(opp, on=["game_id", "home"], how="inner")

    market = pd.DataFrame({
        "game_id": raw["GAME-ID"],
        "close_spread_h": pd.to_numeric(raw["CLOSING SPREAD_H"], errors="coerce"),
        "open_spread_h": pd.to_numeric(raw["OPENING SPREAD_H"], errors="coerce"),
        "ml_h": pd.to_numeric(raw["MONEYLINE_H"], errors="coerce"),
        "ml_r": pd.to_numeric(raw["MONEYLINE_R"], errors="coerce"),
    })
    return panel, market


def initial_window_mask(panel):
    """Games strictly before the first walk-forward cut (the initial train set)."""
    dates = np.sort(panel["date"].values)
    first_cut = dates[MIN_TRAIN]
    return panel["date"].values < first_cut


def ensemble_rank(panel, variables):
    """Paper Table-2 ranking, computed on the initial training window only."""
    tr = initial_window_mask(panel)
    X = panel.loc[tr, [f"f_{v}" for v in variables]].values
    y = panel.loc[tr, "Y"].values.astype(float)
    ranks = {}
    models = {
        "MARS": Earth(),
        "XGBoost": XGBRegressor(max_depth=2, n_estimators=100, learning_rate=0.3,
                                subsample=1.0, colsample_bytree=0.8,
                                random_state=SEED, n_jobs=4, verbosity=0),
        "SGB": GradientBoostingRegressor(n_estimators=100, max_depth=1,
                                         learning_rate=0.1, subsample=0.5,
                                         random_state=SEED),
    }
    for name, est in models.items():
        est.fit(X, y)
        imp = np.asarray(est.feature_importances_, dtype=float)
        order = pd.Series(-imp).rank(method="min")
        order[imp <= 0] = len(imp)
        ranks[name] = order.values
    tab = pd.DataFrame(ranks, index=variables)
    tab["Average Rank"] = tab.mean(axis=1)
    return tab.sort_values("Average Rank")


def walk_forward(panel, cols):
    X = panel[cols].values
    y = panel["Y"].values.astype(float)
    dates = panel["date"].values
    pred = np.full(len(panel), np.nan)
    uniq = np.unique(dates)
    counts = np.cumsum([np.sum(dates == d) for d in uniq])
    start = uniq[np.searchsorted(counts, MIN_TRAIN)]
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
    out = panel[["game_id", "team", "home", "season", "date", "Y", "f_naive"]].copy()
    out = out.rename(columns={"f_naive": "naive"})
    out["pred"] = pred
    return out.dropna(subset=["pred"])


def evaluate(g):
    """One row of the variant comparison table."""
    n = len(g)
    rmse = float(np.sqrt(np.mean((g["cal_margin"] - g["actual_margin"]) ** 2)))
    # incremental information over the closing line
    Xf = np.column_stack([np.ones(n), g["market_margin"], g["cal_margin"]])
    coef, *_ = np.linalg.lstsq(Xf, g["actual_margin"], rcond=None)
    resid = g["actual_margin"] - Xf @ coef
    dof = n - 3
    s2 = float(resid @ resid) / dof
    se = np.sqrt(np.diag(s2 * np.linalg.inv(Xf.T @ Xf)))
    t_model = coef[2] / se[2]
    p_model = 2 * (1 - stats.t.cdf(abs(t_model), dof))
    # flat betting at -110
    sig = g["cal_margin"] - g["market_margin"]
    push = g["actual_margin"] == g["market_margin"]
    gg = g[~push]
    sigg = sig[~push]
    home_cover = gg["actual_margin"] > gg["market_margin"]
    win = np.where(sigg > 0, home_cover, ~home_cover)
    wr = float(np.mean(win))
    roi = wr * (100 / 110) - (1 - wr)
    z = (wr - VIG_BREAKEVEN) / math.sqrt(0.25 / len(gg))
    # CLV at the opening number
    cl = gg.dropna(subset=["open_margin"])
    move = cl["market_margin"] - cl["open_margin"]
    clv = float(np.mean(np.where(sigg.loc[cl.index] > 0, move, -move)))
    return {
        "n": n, "model SD": float(g["cal_margin"].std()),
        "margin RMSE": rmse, "incr coef": float(coef[2]), "incr t": float(t_model),
        "incr p": float(p_model), "win %": 100 * wr, "ROI %": 100 * roi,
        "z vs BE": z, "CLV pts": clv,
    }


def main():
    panel, market = build_panel_ext()
    print(f"team-games: {len(panel)}", flush=True)

    rank16 = ensemble_rank(panel, ALLV)
    n_sel = math.ceil(0.4 * len(ALLV))  # the paper's 40% rule (13 -> 6, 16 -> 7)
    sel = list(rank16.index[:n_sel])
    print("ensemble ranking (initial window):\n", rank16.round(2).to_string(), flush=True)
    print(f"two-stage selection ({n_sel} of {len(ALLV)}): {sel}", flush=True)

    variants = {
        "paper6": [f"f_{v}" for v in ["DRB", "2P%", "FT%", "ORB", "AST", "3PA"]],
        "paper13": [f"f_{v}" for v in VARS],
        "pace16": [f"f_{v}" for v in ALLV],
        "pace_sel": [f"f_{v}" for v in sel],
        "matchup": [f"f_{v}" for v in ALLV] + [f"f_{v}_opp" for v in EXT],
    }

    rows, lines = {}, []
    for name, cols in variants.items():
        scores = walk_forward(panel, cols)
        g = calibrate(to_games(scores, market))
        rows[name] = evaluate(g)
        print(f"{name:9} done: RMSE {rows[name]['margin RMSE']:.3f}  "
              f"t {rows[name]['incr t']:+.2f}  ROI {rows[name]['ROI %']:+.2f}%", flush=True)

    comp = pd.DataFrame(rows).T
    lines.append("# Pace/efficiency extension vs the closing spread\n")
    lines.append("Same paper-faithful recipe (lag-4 designed features, ensemble two-stage "
                 "selection, XGBoost), walk-forward, graded against the closing line. "
                 "`matchup` additionally feeds each team's model the opponent's lagged "
                 "pace/efficiency — the extension the paper lists as future work.\n")
    lines.append("## Ensemble feature ranking, 16 variables (initial training window)\n")
    lines.append(rank16.round(2).to_markdown() + "\n")
    lines.append(f"\nTwo-stage selection keeps {n_sel}: **{', '.join(sel)}**\n")
    lines.append("## Variant comparison\n")
    lines.append(comp.round(3).to_markdown() + "\n")
    lines.append(f"\nClosing-line margin RMSE on the same games: see BETTING.md (13.68). "
                 f"Break-even at -110 is {100 * VIG_BREAKEVEN:.2f}%. `incr t` is the "
                 f"t-statistic on the model's coefficient when actual margin is regressed "
                 f"on closing line + model; |t| > 2 would indicate information the line "
                 f"has not priced.\n")
    open("BETTING_PACE.md", "w").write("\n".join(lines))
    print("\n" + comp.round(3).to_string())
    print("\nwrote BETTING_PACE.md")


if __name__ == "__main__":
    main()
