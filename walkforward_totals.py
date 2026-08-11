"""Totals and spreads against the market, on the complete file (overtime included).

This is the test that was held back. With overtime games restored, closing totals
go over 50.08% of the time (they went over only 47.95% on the overtime-free file),
so grading totals is finally legitimate.

Both markets are graded with the same harness and the same variant ladder, so the
totals result can be read against the spread result directly:

    Total signal  = predicted (home + away) - closing total
    Margin signal = predicted (home - away) - closing market margin

Each is tested for (a) raw accuracy vs the line, (b) incremental information over
the line, (c) monotonicity of disagreement orthogonal to the line, (d) flat-stake
ROI at -110, and (e) closing line value from the opening number.
"""

import math

import numpy as np
import pandas as pd
from scipy import stats

from prepare_data import CSV, VARS, season_label, _side
from rest_travel import FEATURES as RT, add_rest_travel
from walkforward import VIG_BREAKEVEN
from walkforward_pace import ALLV, EXT, build_panel_ext, walk_forward


def build():
    raw = pd.read_csv(CSV, low_memory=False)
    raw["season"] = season_label(raw)
    raw = raw[raw["season"].str.contains("Regular Season|In-Season", na=False)].copy()

    panel, _ = build_panel_ext()
    rt = add_rest_travel(panel[["game_id", "season", "team", "date", "home"]], raw)
    panel = panel.merge(rt[["game_id", "team"] + RT + ["itinerary_gap"]],
                        on=["game_id", "team"], how="left")
    opp = panel[["game_id", "home"] + RT].copy()
    opp["home"] = 1 - opp["home"]
    opp = opp.rename(columns={c: c + "_opp" for c in RT})
    panel = panel.merge(opp, on=["game_id", "home"], how="inner")

    market = pd.DataFrame({
        "game_id": raw["GAME-ID"],
        "close_total": pd.to_numeric(raw["CLOSING TOTAL_H"], errors="coerce"),
        "open_total": pd.to_numeric(raw["OPENING TOTAL_H"], errors="coerce"),
        "close_spread_h": pd.to_numeric(raw["CLOSING SPREAD_H"], errors="coerce"),
        "open_spread_h": pd.to_numeric(raw["OPENING SPREAD_H"], errors="coerce"),
    })
    return panel, market


def to_games(scores, market):
    h = scores[scores["home"] == 1].set_index("game_id")
    a = scores[scores["home"] == 0].set_index("game_id")
    g = pd.DataFrame({
        "season": h["season"], "date": h["date"],
        "actual_margin": h["Y"] - a["Y"], "actual_total": h["Y"] + a["Y"],
        "model_margin": h["pred"] - a["pred"], "model_total": h["pred"] + a["pred"],
    }).dropna()
    g = g.join(market.set_index("game_id"), how="inner")
    g["market_margin"] = -g["close_spread_h"]
    g["open_margin"] = -g["open_spread_h"]
    return g.sort_values("date")


def calibrate(g, model_col, actual_col, out_col, min_train=500):
    """Expanding-window affine calibration, fit only on already-finished games."""
    mv, av = g[model_col].values, g[actual_col].values
    cal = np.full(len(g), np.nan)
    for i in range(min_train, len(g)):
        A = np.column_stack([np.ones(i), mv[:i]])
        coef, *_ = np.linalg.lstsq(A, av[:i], rcond=None)
        cal[i] = coef[0] + coef[1] * mv[i]
    g = g.copy()
    g[out_col] = cal
    return g


def assess(g, cal_col, actual_col, line_col, open_col, over_is_positive=True):
    """One market, one variant: accuracy, incremental info, buckets, ROI, CLV."""
    d = g.dropna(subset=[cal_col, line_col]).copy()
    n = len(d)
    res = {"n": n, "model SD": float(d[cal_col].std()),
           "RMSE": float(np.sqrt(np.mean((d[cal_col] - d[actual_col]) ** 2))),
           "line RMSE": float(np.sqrt(np.mean((d[line_col] - d[actual_col]) ** 2)))}

    X = np.column_stack([np.ones(n), d[line_col], d[cal_col]])
    coef, *_ = np.linalg.lstsq(X, d[actual_col], rcond=None)
    r = d[actual_col] - X @ coef
    s2 = float(r @ r) / (n - 3)
    se = np.sqrt(np.diag(s2 * np.linalg.inv(X.T @ X)))
    res["incr coef"] = float(coef[2])
    res["incr t"] = float(coef[2] / se[2])
    res["incr p"] = float(2 * (1 - stats.t.cdf(abs(coef[2] / se[2]), n - 3)))

    # bet the side the model prefers; pushes excluded
    d["signal"] = d[cal_col] - d[line_col]
    d = d[d[actual_col] != d[line_col]]
    over = d[actual_col] > d[line_col]
    win = np.where(d["signal"] > 0, over, ~over)
    wr = float(np.mean(win))
    res["win %"] = 100 * wr
    res["ROI %"] = 100 * (wr * (100 / 110) - (1 - wr))
    res["z vs BE"] = (wr - VIG_BREAKEVEN) / math.sqrt(0.25 / len(d))

    # disagreement orthogonal to the line
    A = np.column_stack([np.ones(len(d)), d[line_col]])
    b, *_ = np.linalg.lstsq(A, d[cal_col], rcond=None)
    d["ortho"] = d[cal_col] - A @ b
    q = pd.qcut(d["ortho"], 5, labels=[1, 2, 3, 4, 5])
    rates = d.assign(q=q, over=over[d.index]).groupby("q", observed=True)["over"].mean() * 100
    res["bucket 1"], res["bucket 5"] = float(rates.iloc[0]), float(rates.iloc[-1])
    res["bucket spread"] = res["bucket 5"] - res["bucket 1"]

    cl = d.dropna(subset=[open_col])
    move = cl[line_col] - cl[open_col]
    res["CLV pts"] = float(np.mean(np.where(cl["signal"] > 0, move, -move)))
    return res, d


def main():
    panel, market = build()
    print(f"team-games: {len(panel)}  itinerary holes: {panel['itinerary_gap'].mean():.2%}",
          flush=True)

    base = [f"f_{v}" for v in ALLV] + [f"f_{v}_opp" for v in EXT]
    variants = {
        "paper6": [f"f_{v}" for v in ["DRB", "2P%", "FT%", "ORB", "AST", "3PA"]],
        "paper13": [f"f_{v}" for v in VARS],
        "pace16": [f"f_{v}" for v in ALLV],
        "matchup": base,
        "matchup+rest+travel": base + RT + [c + "_opp" for c in RT],
    }

    tot_rows, mar_rows, keep = {}, {}, {}
    for name, cols in variants.items():
        g = to_games(walk_forward(panel, cols), market)
        g = calibrate(g, "model_total", "actual_total", "cal_total")
        g = calibrate(g, "model_margin", "actual_margin", "cal_margin")
        tot_rows[name], dt = assess(g, "cal_total", "actual_total", "close_total", "open_total")
        mar_rows[name], _ = assess(g, "cal_margin", "actual_margin", "market_margin", "open_margin")
        keep[name] = dt
        print(f"{name:22} TOTAL t={tot_rows[name]['incr t']:+.2f} ROI={tot_rows[name]['ROI %']:+.2f}%"
              f" | MARGIN t={mar_rows[name]['incr t']:+.2f} ROI={mar_rows[name]['ROI %']:+.2f}%",
              flush=True)

    tot = pd.DataFrame(tot_rows).T
    mar = pd.DataFrame(mar_rows).T
    out = ["# Totals and spreads on the complete file (overtime restored)\n",
           "Closing totals now go over 50.08% of the time (47.95% on the overtime-free "
           "file), so totals are legitimately gradable for the first time. Same harness, "
           "same variants, both markets.\n",
           "## Totals\n", tot.round(3).to_markdown() + "\n",
           "\n## Spreads\n", mar.round(3).to_markdown() + "\n",
           f"\nBreak-even at -110 is {100 * VIG_BREAKEVEN:.2f}%. `incr t` is the t-statistic "
           "on the model when actual is regressed on the closing line plus the model; "
           "|t| > 2 indicates information the line has not priced. `bucket 1/5` are over "
           "rates in the extreme quintiles of disagreement orthogonal to the line — a real "
           "edge shows a wide, monotone spread.\n"]
    open("BETTING_TOTALS.md", "w").write("\n".join(out))
    best = max(tot_rows, key=lambda k: abs(tot_rows[k]["incr t"]))
    keep[best].to_csv("totals_games.csv", index=False)
    print("\nTOTALS\n" + tot.round(3).to_string())
    print("\nSPREADS\n" + mar.round(3).to_string())


if __name__ == "__main__":
    main()
