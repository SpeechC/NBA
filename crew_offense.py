"""Does CrewShock scale with offensive strength? Pre-registered in
PREREG_crew_offense.md.

Team-game panel, two rows per game, inference clustered at the game level.
CrewShock and LeagueFoulState are loaded from ref_features.csv, never rebuilt.
Efficiency states are the frozen LAG=4 models_frozen features; the W=20 states
from the referee identification are reported as robustness.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import refs
from data_split import SPLIT_DATE
from models_frozen import add_pace_terms
from symmetric_features import build as sym_build

DEV_MAX = 2023


def cluster_ols(y, X, groups):
    """OLS with cluster-robust standard errors at the game level."""
    X = np.column_stack([np.ones(len(X)), X])
    XtX_inv = np.linalg.pinv(X.T @ X)
    b = XtX_inv @ X.T @ y
    r = y - X @ b
    meat = np.zeros((X.shape[1], X.shape[1]))
    order = np.argsort(groups, kind="stable")
    gs = groups[order]
    Xs, rs = X[order], r[order]
    bounds = np.flatnonzero(np.r_[True, gs[1:] != gs[:-1], True])
    for i in range(len(bounds) - 1):
        sl = slice(bounds[i], bounds[i + 1])
        u = Xs[sl].T @ rs[sl]
        meat += np.outer(u, u)
    G = len(bounds) - 1
    n, k = X.shape
    adj = (G / (G - 1)) * ((n - 1) / (n - k))
    V = XtX_inv @ meat @ XtX_inv * adj
    se = np.sqrt(np.diag(V))
    return b, se, b / se


def build():
    m = refs.build()
    m["gid"] = m["GAME-ID"].astype(str).str.strip()
    n = lambda c: pd.to_numeric(m[c], errors="coerce")
    m["spread"] = n("CLOSING SPREAD_H")
    m["pf_h"], m["pf_a"] = n("PF_H"), n("PF_R")
    m["fta_h"], m["fta_a"] = n("FTA_H"), n("FTA_R")
    m["ftm_h"], m["ftm_a"] = n("FT_H"), n("FT_R")
    m["pts_h"], m["pts_a"] = n("PTS_H"), n("PTS_R")

    G = add_pace_terms(sym_build())
    G["gid"] = G["gid"].astype(str).str.strip()
    keep = ["gid", "h_f_OEFF", "a_f_OEFF", "h_f_DEFF", "a_f_DEFF",
            "h_f_PACE", "a_f_PACE", "pace_sum"]
    G = G[keep].dropna().drop_duplicates("gid")
    n0 = len(m)
    m = m.merge(G, on="gid", how="left")
    assert len(m) == n0

    f = pd.read_csv("ref_features.csv")
    f["gid"] = f["gid"].astype(str).str.strip()
    m = m.merge(f[["gid", "CrewShock", "LeagueFoulState"]], on="gid", how="left")

    m["imp_h"] = (m["total"] - m["spread"]) / 2.0
    m["imp_a"] = (m["total"] + m["spread"]) / 2.0

    rows = []
    for s, o, hm in (("h", "a", 1), ("a", "h", 0)):
        rows.append(pd.DataFrame({
            "gid": m["gid"], "yr": m["yr"], "date": m["date"], "home": hm,
            "CrewShock": m["CrewShock"], "LeagueFoulState": m["LeagueFoulState"],
            "pace_sum": m["pace_sum"],
            "own_off": m[f"{s}_f_OEFF"], "opp_def": m[f"{o}_f_DEFF"],
            "pts": m[f"pts_{s}"], "imp": m[f"imp_{s}"],
            "fta": m[f"fta_{s}"], "ftm": m[f"ftm_{s}"],
            "fouls_drawn": m[f"pf_{o}"]}))
    P = pd.concat(rows, ignore_index=True)
    P["TeamResidual"] = P["pts"] - P["imp"]
    return P


TARGETS = [("fouls_drawn", "fouls drawn (opp committed)"),
           ("fta", "team FTA"), ("ftm", "team FTM"),
           ("pts", "ACTUAL team points"),
           ("imp", "IMPLIED closing team points"),
           ("TeamResidual", "team CLOSING RESIDUAL")]


def design(x):
    return np.column_stack([
        x["CrewShock"], x["CrewShock"] * x["zOff"], x["CrewShock"] * x["zDef"],
        x["zOff"], x["zDef"], x["home"], x["LeagueFoulState"], x["pace_sum"]])


def main():
    P = build()
    P = P.dropna(subset=["CrewShock", "LeagueFoulState", "own_off", "opp_def",
                         "pace_sum", "pts", "imp", "fta", "ftm",
                         "fouls_drawn"]).reset_index(drop=True)
    dev = P[P["yr"] <= DEV_MAX]
    mo, so = dev["own_off"].mean(), dev["own_off"].std()
    md, sd_ = dev["opp_def"].mean(), dev["opp_def"].std()
    P["zOff"] = (P["own_off"] - mo) / so
    P["zDef"] = (P["opp_def"] - md) / sd_
    dev = P[P["date"] < SPLIT_DATE]
    hold = P[P["date"] >= SPLIT_DATE]

    print("=" * 104)
    print("CrewShock x OFFENSIVE STRENGTH — team-game panel, game-clustered")
    print("=" * 104)
    print(f"  {len(P):,} team-games ({P['gid'].nunique():,} games)   "
          f"development {len(dev):,}   holdout {len(hold):,}")
    print(f"  FROZEN develop standardisation: own_off mu {mo:.3f} sd {so:.3f}   "
          f"opp_def mu {md:.3f} sd {sd_:.3f}")
    print("  orientation: zOff higher = better offense;  zDef higher = opponent")
    print("  ALLOWS more (weaker defense). Both point toward more team points,")
    print("  which is what makes bO and bD comparable.")
    print(f"  corr(zOff, zDef) = {np.corrcoef(P['zOff'], P['zDef'])[0,1]:+.4f}")
    print(f"  TeamResidual: mean {P['TeamResidual'].mean():+.3f}  "
          f"sd {P['TeamResidual'].std():.2f}")

    print("\n" + "=" * 104)
    print("PRIMARY — TeamResidual, and the full chain")
    print("  bR = CrewShock   bO = CrewShock x zOff   bD = CrewShock x zDef")
    print("=" * 104)
    for wlab, x in (("DEVELOPMENT", dev), ("HOLDOUT", hold)):
        print(f"\n  [{wlab}]  n={len(x):,} team-games, "
              f"{x['gid'].nunique():,} clusters")
        print(f"    {'target':30} {'bR':>18} {'bO':>18} {'bD':>18}")
        for col, name in TARGETS:
            b, se, t = cluster_ols(x[col].values, design(x), x["gid"].values)
            print(f"    {name:30} {b[1]:+9.4f}(t={t[1]:+5.2f})"
                  f" {b[2]:+9.4f}(t={t[2]:+5.2f})"
                  f" {b[3]:+9.4f}(t={t[3]:+5.2f})")

    print("\n  holdout by season")
    for y in sorted(hold["yr"].unique()):
        x = hold[hold["yr"] == y]
        b, se, t = cluster_ols(x["TeamResidual"].values, design(x),
                               x["gid"].values)
        print(f"    {y:<8} n={len(x):5,}  bR {b[1]:+7.4f}(t={t[1]:+5.2f})  "
              f"bO {b[2]:+7.4f}(t={t[2]:+5.2f})  "
              f"bD {b[3]:+7.4f}(t={t[3]:+5.2f})")
    b, se, t = cluster_ols(P["TeamResidual"].values, design(P), P["gid"].values)
    print(f"    {'POOLED':8} n={len(P):5,}  bR {b[1]:+7.4f}(t={t[1]:+5.2f})  "
          f"bO {b[2]:+7.4f}(t={t[2]:+5.2f})  "
          f"bD {b[3]:+7.4f}(t={t[3]:+5.2f})")

    print("\n" + "=" * 104)
    print("DESCRIPTIVE MONOTONICITY — CrewShock slope within frozen buckets")
    print("  development-defined cut points, applied unchanged to holdout")
    print("=" * 104)
    for var, lab, ks in (("zOff", "OFFENSE", (3, 5)), ("zDef", "OPP DEFENSE",
                                                       (3, 5))):
        for k in ks:
            cuts = np.asarray(dev[var].quantile(np.linspace(0, 1, k + 1)).values,
                              dtype=float).copy()
            cuts[0], cuts[-1] = -np.inf, np.inf
            print(f"\n  {lab} — {k} frozen buckets")
            print(f"    {'bucket':8} {'dev n':>7} {'dev slope':>12} "
                  f"{'hold n':>7} {'hold slope':>12}")
            for i in range(k):
                cells = []
                for x in (dev, hold):
                    g = x[(x[var] >= cuts[i]) & (x[var] < cuts[i + 1])]
                    if len(g) < 200:
                        cells.append((len(g), np.nan, np.nan))
                        continue
                    X = np.column_stack([g["CrewShock"], g["zOff"], g["zDef"],
                                         g["home"], g["LeagueFoulState"],
                                         g["pace_sum"]])
                    b, se, t = cluster_ols(g["TeamResidual"].values, X,
                                           g["gid"].values)
                    cells.append((len(g), b[1], t[1]))
                print(f"    {i+1:<8} {cells[0][0]:7,} "
                      f"{cells[0][1]:+8.4f}({cells[0][2]:+5.2f}) "
                      f"{cells[1][0]:7,} {cells[1][1]:+8.4f}({cells[1][2]:+5.2f})")

    print("\n" + "=" * 104)
    print("ROBUSTNESS — same model on the W=20 referee-control efficiency states")
    print("=" * 104)
    import ref_shock as rsk
    c = rsk.build()[["gid", "m_oeff_h", "m_oeff_a", "m_deff_h", "m_deff_a"]]
    c["gid"] = c["gid"].astype(str).str.strip()
    rows = []
    for s, o, hm in (("h", "a", 1), ("a", "h", 0)):
        rows.append(c[["gid"]].assign(home=hm, own_off2=c[f"m_oeff_{s}"],
                                      opp_def2=c[f"m_deff_{o}"]))
    C = pd.concat(rows, ignore_index=True)
    Q = P.merge(C, on=["gid", "home"], how="inner").dropna(
        subset=["own_off2", "opp_def2"])
    qd = Q[Q["date"] < SPLIT_DATE]
    Q["zOff"] = (Q["own_off2"] - qd["own_off2"].mean()) / qd["own_off2"].std()
    Q["zDef"] = (Q["opp_def2"] - qd["opp_def2"].mean()) / qd["opp_def2"].std()
    for wlab, x in (("development", Q[Q["date"] < SPLIT_DATE]),
                    ("holdout", Q[Q["date"] >= SPLIT_DATE])):
        b, se, t = cluster_ols(x["TeamResidual"].values, design(x),
                               x["gid"].values)
        print(f"  {wlab:12} n={len(x):5,}  bR {b[1]:+7.4f}(t={t[1]:+5.2f})  "
              f"bO {b[2]:+7.4f}(t={t[2]:+5.2f})  "
              f"bD {b[3]:+7.4f}(t={t[3]:+5.2f})")


if __name__ == "__main__":
    main()
