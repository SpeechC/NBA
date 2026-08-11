"""Is game-to-game scoring VARIANCE predictable, and is it worth anything?

The idea: if some games are reliably higher-variance than others, and the book
prices its alternate-total ladder off a single sigma, then extremes are mispriced
in the predictable direction.

Note what this can and cannot pay off in. A straight over/under at the closing
number is, to first order, a coin flip whose value does NOT depend on variance --
getting sigma right changes nothing about a bet at the median. Variance only pays
in markets that price the shape of the distribution:

    alternate totals · middles across books · teasers · live totals

We hold historical prices for none of those. So this is a *feasibility* test: if
variance turns out not to be predictable, that closes the whole family cheaply and
there is no reason to go buy derivative price history. If it is predictable, the
size of the effect tells you whether that purchase is worth making.

Mechanisms worth testing, rather than a blind feature dump:
  * three-point rate  — a 3PA-heavy game has higher scoring variance per
    possession, mechanically (bigger payoff per make, similar make rate)
  * pace              — more possessions, more total variance in absolute points
  * team scoring SD   — teams that swing between hot and cold nights
  * total level       — the heteroskedasticity already measured (+0.016 sigma/pt)
"""

import numpy as np
import pandas as pd
from scipy import stats
from xgboost import XGBRegressor

from movement_full import wf_xgb

ODDS = "/home/dpope/data/dfMaster_OT.parquet"
LAG = 10          # longer window than usual: estimating a variance needs more games
SEED = 42


def build():
    o = pd.read_parquet(ODDS)
    o["season"] = o["DATASET_H"].fillna(o["BIGDATABALL\nDATASET_H"])
    r = o[o["season"].str.contains("Regular Season|In-Season", na=False)].copy()
    r["date"] = pd.to_datetime(r["DATE"])
    q = [f"{i}Q_{s}" for i in (1, 2, 3, 4) for s in ("H", "R")]
    for c in q:
        r[c] = pd.to_numeric(r[c], errors="coerce")
    ot = [f"OT{i}_{s}" for i in range(1, 6) for s in ("H", "R")]
    r["ot"] = sum(pd.to_numeric(r[c], errors="coerce").fillna(0) for c in ot)
    r["total"] = r[q].sum(axis=1) + r["ot"]
    r["close"] = pd.to_numeric(r["CLOSING TOTAL_H"], errors="coerce")
    r = r[r["close"].between(150, 300)].dropna(subset=["total", "close"])
    r["resid"] = r["total"] - r["close"]
    r["absres"] = r["resid"].abs()

    from team_mapping import NAME_TO_ID
    sides = []
    for suf in ("H", "R"):
        sides.append(pd.DataFrame({
            "gid": r["GAME-ID"].astype(str), "date": r["date"], "season": r["season"],
            "team": r[f"TEAM_{suf}"].map(NAME_TO_ID),
            "pts": pd.to_numeric(r[f"PTS_{suf}"], errors="coerce"),
            "p3a": pd.to_numeric(r[f"3PA_{suf}"], errors="coerce"),
            "fga": pd.to_numeric(r[f"FGA_{suf}"], errors="coerce"),
            "pace": pd.to_numeric(r[f"PACE_{suf}"], errors="coerce"),
            "game_total": r["total"]}))
    p = pd.concat(sides, ignore_index=True).dropna(subset=["team"])
    p["p3_rate"] = p["p3a"] / p["fga"]
    p = p.sort_values(["season", "team", "date"]).reset_index(drop=True)

    g = p.groupby(["season", "team"])
    # lagged team-level MEANS (level features)
    for c in ("pace", "p3_rate", "pts"):
        p[f"m_{c}"] = g[c].transform(lambda s: s.shift(1).rolling(LAG).mean())
    # lagged team-level SDs (the actual variance features)
    for c in ("pts", "pace", "game_total"):
        p[f"sd_{c}"] = g[c].transform(lambda s: s.shift(1).rolling(LAG).std())

    feat = [c for c in p.columns if c.startswith(("m_", "sd_"))]
    h = p[p["gid"].isin(r["GAME-ID"].astype(str))].copy()
    home = h.merge(r[["GAME-ID", "TEAM_H"]].assign(
        gid=r["GAME-ID"].astype(str), th=r["TEAM_H"].map(NAME_TO_ID))[["gid", "th"]],
        on="gid", how="left")
    home["is_home"] = home["team"] == home["th"]

    a = home[home["is_home"]].set_index("gid")[feat].add_prefix("h_")
    b = home[~home["is_home"]].set_index("gid")[feat].add_prefix("a_")
    G = (r.assign(gid=r["GAME-ID"].astype(str))
           .set_index("gid")[["date", "season", "close", "total", "resid", "absres"]]
           .join(a).join(b).dropna())
    return G.sort_values("date").reset_index(drop=True), \
        [f"h_{c}" for c in feat] + [f"a_{c}" for c in feat] + ["close"]


def main():
    G, feats = build()
    print(f"games with lagged variance features: {len(G):,}  "
          f"{G['date'].min().date()} .. {G['date'].max().date()}\n")

    # walk-forward prediction of |residual|; E|resid| = sigma*sqrt(2/pi) for a normal
    G["pred_abs"] = wf_xgb(G[feats].values, G["absres"].values.astype(float),
                           G["date"].values, 1500, depth=3, n_est=200, lr=0.03)
    d = G.dropna(subset=["pred_abs"]).copy()
    d["pred_sigma"] = d["pred_abs"] * np.sqrt(np.pi / 2)

    const = d["absres"].expanding().mean().shift(1)
    base_rmse = float(np.sqrt(np.nanmean((d["absres"] - const) ** 2)))
    mod_rmse = float(np.sqrt(np.mean((d["absres"] - d["pred_abs"]) ** 2)))
    corr = float(np.corrcoef(d["pred_abs"], d["absres"])[0, 1])

    print("=== can we predict |residual| out of sample? ===")
    print(f"  n = {len(d):,}")
    print(f"  RMSE, constant (expanding mean) : {base_rmse:.4f}")
    print(f"  RMSE, model                     : {mod_rmse:.4f}")
    print(f"  improvement                     : {100 * (1 - mod_rmse / base_rmse):+.2f}%")
    print(f"  corr(predicted, realised |resid|): {corr:+.4f}")

    print("\n=== how much does predicted sigma actually vary? ===")
    print(f"  predicted sigma: mean {d['pred_sigma'].mean():.2f}  "
          f"sd {d['pred_sigma'].std():.2f}  "
          f"p10 {d['pred_sigma'].quantile(.1):.2f}  p90 {d['pred_sigma'].quantile(.9):.2f}")

    print("\n=== do high-predicted-sigma games actually deviate more? (quintiles) ===")
    d["q"] = pd.qcut(d["pred_sigma"], 5, labels=[1, 2, 3, 4, 5])
    t = d.groupby("q", observed=True).agg(
        n=("absres", "size"), pred_sigma=("pred_sigma", "mean"),
        realised_sd=("resid", "std"), mean_abs=("absres", "mean"))
    t["over20 %"] = 100 * d.groupby("q", observed=True)["absres"].apply(lambda s: (s > 20).mean())
    print(t.round(3).to_string())

    lo, hi = t["realised_sd"].iloc[0], t["realised_sd"].iloc[-1]
    print(f"\n  realised SD, lowest vs highest quintile: {lo:.2f} vs {hi:.2f}  "
          f"({100 * (hi / lo - 1):+.1f}%)")

    print("\n=== what would that be worth on an alternate total? ===")
    print("P(|resid| > d) priced off the pooled sigma vs the quintile's own sigma:")
    pooled = d["resid"].std()
    rows = []
    for dist in (15, 20, 25):
        p_pool = 2 * (1 - stats.norm.cdf(dist / pooled))
        p_lo = 2 * (1 - stats.norm.cdf(dist / lo))
        p_hi = 2 * (1 - stats.norm.cdf(dist / hi))
        rows.append({"distance": dist, "pooled %": 100 * p_pool,
                     "low-sigma quintile %": 100 * p_lo,
                     "high-sigma quintile %": 100 * p_hi,
                     "edge if book uses pooled (pp)": 100 * (p_hi - p_pool)})
    print(pd.DataFrame(rows).round(2).to_string(index=False))


if __name__ == "__main__":
    main()
