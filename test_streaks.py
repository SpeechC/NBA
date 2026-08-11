"""Do days off and home/road streaks contain anything the closing line misses?

Two tests, in increasing strictness:

1. Effect on scoring -- does the variable move a team's points at all? If not,
   there is nothing to price and nothing to exploit.
2. Effect on the market residual -- regress excess margin (actual margin minus
   closing line) on the home-minus-away differential of each variable. A
   significant coefficient means the line has failed to price it. This is the
   test that matters; a variable can have a large real effect and still be
   worthless if the market already knows.
"""

import numpy as np
import pandas as pd
from scipy import stats

from prepare_data import CSV, season_label, _side
from rest_travel import FEATURES, STREAK_FEATURES, add_rest_travel

ALL_SCHED = FEATURES + STREAK_FEATURES


def build():
    raw = pd.read_csv(CSV, low_memory=False)
    raw["season"] = season_label(raw)
    raw = raw[raw["season"].str.contains("Regular Season|In-Season", na=False)].copy()

    panel = pd.concat([_side(raw, "H"), _side(raw, "R")], ignore_index=True)
    panel = panel.sort_values(["season", "team", "date"]).reset_index(drop=True)
    p = add_rest_travel(panel[["game_id", "season", "team", "date", "home"]], raw)
    p["Y"] = panel.set_index(["game_id", "team"]).loc[
        pd.MultiIndex.from_frame(p[["game_id", "team"]]), "Y"].values

    market = pd.DataFrame({
        "game_id": raw["GAME-ID"],
        "close_spread_h": pd.to_numeric(raw["CLOSING SPREAD_H"], errors="coerce"),
        "close_total": pd.to_numeric(raw["CLOSING TOTAL_H"], errors="coerce"),
    })
    return p, market


def ols(y, X, names):
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = y - X @ coef
    dof = len(y) - X.shape[1]
    s2 = float(r @ r) / dof
    se = np.sqrt(np.diag(s2 * np.linalg.inv(X.T @ X)))
    t = coef / se
    return pd.DataFrame({"coef": coef, "se": se, "t": t,
                         "p": 2 * (1 - stats.t.cdf(np.abs(t), dof))}, index=names)


def main():
    p, market = build()
    L = ["# Days off and home/road streaks\n",
         f"Complete file, {len(p)} team-games. Itinerary holes: "
         f"{p['itinerary_gap'].mean():.2%}.\n"]

    # --- 1. raw effect on scoring ----------------------------------------
    L.append("## 1. Effect on a team's own scoring\n")
    L.append("Split *within venue*: `home_stand_game`, `road_trip_game`, `days_away` and "
             "`streak_signed` are zero for one venue by construction, so a naive median "
             "split on them just recovers home-court advantage (~2.0 pts). Each is "
             "therefore compared deep-in-streak vs early-in-streak among games at the "
             "relevant venue only.\n")
    rows = {}
    for f in ALL_SCHED:
        v = p[f]
        if v.nunique() <= 1:
            continue
        sub = p
        if f in ("home_stand_game", "is_return_home"):
            sub = p[p["home"] == 1]
        elif f in ("road_trip_game", "days_away"):
            sub = p[p["home"] == 0]
        elif f == "streak_signed":
            continue  # redundant with the two above
        v = sub[f]
        hi = sub.loc[v > v.median(), "Y"].mean()
        lo = sub.loc[v <= v.median(), "Y"].mean()
        rows[f] = {"n": len(sub),
                   "deep/high": hi, "shallow/low": lo, "diff": hi - lo}
    L.append(pd.DataFrame(rows).T.round(3).to_markdown() + "\n")

    # --- 2. against the closing line -------------------------------------
    h = p[p.home == 1].set_index("game_id")
    a = p[p.home == 0].set_index("game_id")
    g = pd.DataFrame({f"d_{f}": h[f] - a[f] for f in ALL_SCHED})
    g["actual_margin"] = h["Y"] - a["Y"]
    g["actual_total"] = h["Y"] + a["Y"]
    g = g.join(market.set_index("game_id")).dropna(subset=["close_spread_h"])
    g["market_margin"] = -g["close_spread_h"]
    g["excess"] = g["actual_margin"] - g["market_margin"]
    g = g.dropna()

    L.append(f"\n## 2. Against the closing spread ({len(g)} games)\n")
    L.append("Excess margin = actual margin − closing line. Each variable enters as a "
             "home-minus-away differential.\n")

    L.append("\n**Univariate**\n")
    uni = {}
    for f in ALL_SCHED:
        c = f"d_{f}"
        if g[c].nunique() <= 1:
            continue
        X = np.column_stack([np.ones(len(g)), g[c]])
        uni[f] = ols(g["excess"].values, X, ["const", f]).iloc[1]
    L.append(pd.DataFrame(uni).T.round(4).to_markdown() + "\n")

    L.append("\n**Joint**\n")
    # streak_signed is exactly home_stand_game - road_trip_game, so it is dropped
    # to avoid perfect collinearity
    cols = [f"d_{f}" for f in ALL_SCHED
            if g[f"d_{f}"].nunique() > 1 and f != "streak_signed"]
    X = np.column_stack([np.ones(len(g))] + [g[c].values for c in cols])
    joint = ols(g["excess"].values, X, ["const"] + cols)
    L.append(joint.round(4).to_markdown() + "\n")
    tsq = (joint["t"][1:] ** 2)
    L.append(f"\nMean squared t across the {len(cols)} schedule variables: {tsq.mean():.2f} "
             f"(≈1.0 is what pure noise produces; below 1.0 means less structure than "
             f"chance would generate).\n")

    # totals too, now that overtime is restored
    gt = g.dropna(subset=["close_total"]).copy()
    gt["excess_total"] = gt["actual_total"] - gt["close_total"]
    sums = {}
    for f in ALL_SCHED:
        c = f"d_{f}"
        if gt[c].nunique() <= 1:
            continue
        X = np.column_stack([np.ones(len(gt)), gt[c]])
        sums[f] = ols(gt["excess_total"].values, X, ["const", f]).iloc[1]
    L.append(f"\n## 3. Against the closing total ({len(gt)} games)\n")
    L.append(pd.DataFrame(sums).T.round(4).to_markdown() + "\n")

    open("STREAKS.md", "w").write("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
