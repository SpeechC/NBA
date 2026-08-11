"""Does garbage-time adjustment improve the market-facing model?

Pre-registered comparison, three feature sets, one primary metric. Deliberately
narrow: ~15 strategy variants have already been evaluated on this sample, so this
runs three and reports all three regardless of which wins.

  A  odds-file lagged OEFF/DEFF/PACE          (the established baseline, 19.31)
  B  pbp-derived, ALL possessions             (isolates pbp vs BigDataBall)
  C  pbp-derived, COMPETITIVE possessions     (isolates the garbage-time effect)

B vs A tells you whether the pbp reconstruction is at least as good as the vendor
box score. C vs B is the actual question: does removing decided possessions make
a team rating more predictive?

Primary metric: walk-forward RMSE predicting the game total, against the closing
line's 18.09 on the same games. Secondary: CLV in the line-movement model.
"""

import numpy as np
import pandas as pd
from xgboost import XGBRegressor

from movement_full import wf_xgb, wf_calibrate, SCORE_MIN, CAL_MIN, MOVE_MIN
from prepare_data import CSV, season_label

RATINGS = "/home/dpope/data/team_game_ratings.parquet"
LAG = 4


def build_panel():
    r = pd.read_parquet(RATINGS)
    r = r[r["season_type"] == "RegularSeason"].copy()
    r["team"] = r["team"].astype("int64")

    odds = pd.read_parquet("/home/dpope/data/dfMaster_OT.parquet")
    odds["season_lbl"] = odds["DATASET_H"].fillna(odds["BIGDATABALL\nDATASET_H"])
    odds = odds[odds["season_lbl"].str.contains("Regular Season|In-Season", na=False)]
    odds["gid"] = (odds["GAME-ID"].astype(str)
                   .str.replace(r"\.0$", "", regex=True).str.zfill(10))
    odds["date"] = pd.to_datetime(odds["DATE"])
    from team_mapping import NAME_TO_ID

    # per-team odds-side ratings, for feature set A
    side = []
    for suf, other in (("H", "R"), ("R", "H")):
        side.append(pd.DataFrame({
            "gid": odds["gid"], "date": odds["date"],
            "team": odds[f"TEAM_{suf}"].map(NAME_TO_ID),
            "is_home": 1 if suf == "H" else 0,
            "pts": pd.to_numeric(odds[f"PTS_{suf}"], errors="coerce"),
            "oeff_odds": pd.to_numeric(odds[f"OEFF_{suf}"], errors="coerce"),
            "deff_odds": pd.to_numeric(odds[f"DEFF_{suf}"], errors="coerce"),
            "pace_odds": pd.to_numeric(odds[f"PACE_{suf}"], errors="coerce"),
        }))
    o = pd.concat(side, ignore_index=True).dropna(subset=["team"])
    o["team"] = o["team"].astype("int64")

    p = o.merge(r[["gid", "team", "season", "oeff_all", "deff_all", "oeff_comp",
                   "deff_comp", "poss_all", "poss_comp", "gt_share"]],
                on=["gid", "team"], how="inner")
    p = p.sort_values(["season", "team", "date"]).reset_index(drop=True)

    market = pd.DataFrame({
        "gid": odds["gid"],
        "close_total": pd.to_numeric(odds["CLOSING TOTAL_H"], errors="coerce"),
        "open_total": pd.to_numeric(odds["OPENING TOTAL_H"], errors="coerce"),
    })
    market = market[market["close_total"].between(150, 300)
                    & market["open_total"].between(150, 300)]
    return p, market


FEATS = {
    "A odds-file": ["oeff_odds", "deff_odds", "pace_odds"],
    "B pbp all": ["oeff_all", "deff_all", "poss_all"],
    "C pbp competitive": ["oeff_comp", "deff_comp", "poss_all"],
}


def lagged(p, cols):
    f = (p.groupby(["season", "team"])[cols]
           .apply(lambda g: g.shift(1).rolling(LAG).mean())
           .reset_index(level=[0, 1], drop=True).sort_index())
    return f.add_prefix("L_")


def run(p, market, name, cols):
    d = pd.concat([p, lagged(p, cols)], axis=1).dropna(
        subset=[f"L_{c}" for c in cols]).copy()
    h = d[d.is_home == 1].set_index("gid")
    a = d[d.is_home == 0].set_index("gid")
    g = pd.DataFrame({"date": h["date"], "season": h["season"],
                      "actual_total": h["pts"] + a["pts"]}).dropna()
    for c in cols:
        g[f"h_{c}"] = h[f"L_{c}"]
        g[f"a_{c}"] = a[f"L_{c}"]
    g = g.reset_index().merge(market, on="gid", how="inner")
    g = g.dropna().sort_values("date").reset_index(drop=True)

    fcols = [f"h_{c}" for c in cols] + [f"a_{c}" for c in cols]
    g["pred"] = wf_xgb(g[fcols].values, g["actual_total"].values.astype(float),
                       g["date"].values, SCORE_MIN, depth=3, n_est=150, lr=0.05)
    d2 = g.dropna(subset=["pred"]).reset_index(drop=True)
    d2["cal"] = wf_calibrate(d2["pred"].values, d2["actual_total"].values, CAL_MIN)
    d2 = d2.dropna(subset=["cal"])

    rmse = float(np.sqrt(np.mean((d2["cal"] - d2["actual_total"]) ** 2)))
    line = float(np.sqrt(np.mean((d2["close_total"] - d2["actual_total"]) ** 2)))

    # secondary: CLV from the movement model on this disagreement
    d2["dis"] = d2["cal"] - d2["open_total"]
    d2["move"] = d2["close_total"] - d2["open_total"]
    d2["pm"] = wf_xgb(d2[["open_total", "dis"] + fcols].values,
                      d2["move"].values.astype(float), d2["date"].values, MOVE_MIN)
    m = d2.dropna(subset=["pm"])
    sel = m[m["pm"].abs() > 1]
    clv_all = np.where(m["pm"] > 0, m["move"], -m["move"]).mean()
    clv_sel = np.where(sel["pm"] > 0, sel["move"], -sel["move"]).mean() if len(sel) else np.nan
    return {"set": name, "n": len(d2), "total RMSE": rmse, "line RMSE": line,
            "gap": rmse - line, "n move": len(m), "CLV all": clv_all,
            "n>1": len(sel), "CLV>1": clv_sel}


def main():
    p, market = build_panel()
    print(f"panel: {len(p):,} team-games, {p['season'].nunique()} seasons", flush=True)
    print("sanity — our OEFF vs the odds file's, same team-games:")
    print(f"  corr(all, odds)  = {p['oeff_all'].corr(p['oeff_odds']):.4f}   "
          f"mean diff {(p['oeff_all'] - p['oeff_odds']).mean():+.3f}")
    print(f"  corr(comp, odds) = {p['oeff_comp'].corr(p['oeff_odds']):.4f}")
    print(f"  mean garbage share {100 * p['gt_share'].mean():.2f}%\n", flush=True)

    rows = [run(p, market, k, v) for k, v in FEATS.items()]
    for r in rows:
        print(f"{r['set']:20} RMSE {r['total RMSE']:.3f} (line {r['line RMSE']:.3f}, "
              f"gap {r['gap']:+.3f})  CLV all {r['CLV all']:+.3f}  "
              f"CLV>1 {r['CLV>1']:+.3f} on n={r['n>1']}", flush=True)
    print()
    print(pd.DataFrame(rows).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
