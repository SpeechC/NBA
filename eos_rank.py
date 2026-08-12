"""Can we RANK final-week games by expected over-edge?

Not a replacement for the validated full-game strategy -- a selector within it.

    target   R_i = actual_total - closing_total        (continuous, not binary:
             an 18-point over carries more evidence than a 0.5-point one)

    model    R = a + f(days) + bX + g[X x f(days)] + e      ridge, no trees

Fit on ALL games so thousands of normal-season observations estimate the baseline
relationships, while the late-season games estimate only the incremental regime
change through the interaction terms. That avoids re-creating the subgroup
problem: the earlier filter search split 537 games eight ways and the best filter
came in below what the best of eight RANDOM splits produces.

f(days) is a linear ramp: late_w = max(0, 1 - days_left/21), so 1.0 on the final
day, 0 more than three weeks out.

VALIDATION is expanding-window, not leave-one-out: for each held-out season,
train on PRIOR seasons only, score that season's final-7 games, rank them, and
walk down from the highest predicted residual. The result must be MONOTONE --
higher predicted residual, higher realised over rate -- to demonstrate genuine
conditional separability rather than a lucky cut.

Baseline to beat: 55.29% (the LOSO-validated unconditional figure).

⚠ All features are lagged. Anything measured on the current game is excluded.

⚠ FEATURE SET IS COVERAGE-DRIVEN. A first version included rest days and
eFG%/OEFF-based form and retained only 3,113 of 9,387 games, leaving 174
out-of-sample final-7 games -- too few to answer the question. The vendor's rest
columns are 62% populated in every season and the box-score columns ~88%. Both
are dropped in favour of features built from points and the residual itself,
which are ~100% populated. Rest is in any case a known-priced factor, and the
box-score version is retested separately at the end on its smaller sample.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

BE = 110 / 210
RAMP = 21.0
ALPHAS = [10.0, 30.0, 100.0, 300.0, 1000.0]


def build():
    from prepare_data import CSV, season_label
    raw = pd.read_csv(CSV, low_memory=False)
    raw["season"] = season_label(raw).astype(str)
    d = raw[raw["season"].str.contains("Regular Season", na=False)].copy()
    n = lambda c: pd.to_numeric(d[c], errors="coerce")
    d["date"] = pd.to_datetime(d["DATE"], errors="coerce")
    d["close_total"] = n("CLOSING TOTAL_H")
    d["spread"] = n("CLOSING SPREAD_H")
    d["actual"] = d["PTS_H"] + d["PTS_R"]
    d["rest_h"], d["rest_a"] = n("TEAM\nREST DAYS_H"), n("TEAM\nREST DAYS_R")
    for s in ("H", "R"):
        d[f"oeff_{s}"], d[f"deff_{s}"] = n(f"TEAM_OEFF_{s}"), n(f"TEAM_DEF_{s}")
        d[f"efg_{s}"] = n(f"TEAM_eFGP_{s}")
        d[f"pts_{s}"] = d[f"PTS_{'H' if s=='H' else 'R'}"]
    d = d.dropna(subset=["close_total", "spread", "date", "actual"])
    d = d[d["close_total"].between(150, 300)].sort_values("date")
    d["resid"] = d["actual"] - d["close_total"]
    d["days_left"] = (d.groupby("season")["date"].transform("max")
                      - d["date"]).dt.days
    d["late_w"] = np.maximum(0.0, 1.0 - d["days_left"] / RAMP)

    # ---- lagged team form, built from a long panel -------------------------
    rows = []
    for side, opp in (("H", "R"), ("R", "H")):
        rows.append(pd.DataFrame({
            "date": d["date"], "season": d["season"],
            "team": d[f"TEAM_{side}"],
            "oeff": d[f"oeff_{side}"], "deff": d[f"deff_{side}"],
            "efg": d[f"efg_{side}"], "pts": d[f"pts_{side}"],
            "win": (d[f"pts_{side}"] > d[f"pts_{opp}"]).astype(float),
            "g_resid": d["resid"]}))
    L = pd.concat(rows).sort_values("date")
    g = L.groupby(["season", "team"])
    # own points and points allowed -- 100% populated, unlike the box-score cols
    L["pts_allowed"] = L["pts"] - L["g_margin"] if "g_margin" in L else np.nan
    for c in ("pts", "g_resid"):
        L[f"r5_{c}"] = g[c].transform(
            lambda s: s.shift(1).rolling(5, min_periods=2).mean())
        L[f"r20_{c}"] = g[c].transform(
            lambda s: s.shift(1).rolling(20, min_periods=5).mean())
    L["pts_surprise"] = L["r5_pts"] - L["r20_pts"]
    L["wpct"] = g["win"].transform(lambda s: s.shift(1).expanding().mean())
    keep = ["date", "season", "team", "wpct", "r5_pts", "r20_pts",
            "pts_surprise", "r5_g_resid", "r20_g_resid"]
    L = L[keep]

    d = d.merge(L.add_suffix("_h").rename(columns={"date_h": "date",
                "season_h": "season", "team_h": "TEAM_H"}),
                on=["date", "season", "TEAM_H"], how="left")
    d = d.merge(L.add_suffix("_a").rename(columns={"date_a": "date",
                "season_a": "season", "team_a": "TEAM_R"}),
                on=["date", "season", "TEAM_R"], how="left")

    # orient to favourite / underdog
    hf = d["spread"] < 0
    for stem in ("wpct", "r5_pts", "r20_pts", "pts_surprise",
                 "r5_g_resid", "r20_g_resid"):
        d[f"fav_{stem}"] = np.where(hf, d[f"{stem}_h"], d[f"{stem}_a"])
        d[f"dog_{stem}"] = np.where(hf, d[f"{stem}_a"], d[f"{stem}_h"])
    d["fav_rest"] = np.where(hf, d["rest_h"], d["rest_a"])
    d["dog_rest"] = np.where(hf, d["rest_a"], d["rest_h"])
    d["abs_spread"] = d["spread"].abs()
    # incentive proxies, continuous
    d["wpct_gap"] = d["fav_wpct"] - d["dog_wpct"]
    d["dog_futility"] = np.maximum(0.0, 0.45 - d["dog_wpct"])
    d["fav_locked"] = np.maximum(0.0, d["fav_wpct"] - 0.60)
    return d[d["resid"] != 0].reset_index(drop=True)


FEATS = ["close_total", "abs_spread", "fav_wpct", "dog_wpct", "wpct_gap",
         "dog_futility", "fav_locked", "fav_r5_pts", "dog_r5_pts",
         "fav_pts_surprise", "dog_pts_surprise",
         "fav_r5_g_resid", "dog_r5_g_resid", "fav_r20_g_resid", "dog_r20_g_resid"]


def design(x):
    """[X, late_w, X*late_w]"""
    X = x[FEATS].values
    w = x["late_w"].values.reshape(-1, 1)
    return np.hstack([X, w, X * w])


def fit_predict(train, test, alpha):
    sc = StandardScaler().fit(design(train))
    m = Ridge(alpha=alpha).fit(sc.transform(design(train)),
                               train["resid"].values)
    return m.predict(sc.transform(design(test))), m


def main():
    d = build().dropna(subset=FEATS)
    print(f"{len(d):,} games with complete lagged features, "
          f"{d['season'].nunique()} seasons")
    print(f"{len(FEATS)} base features -> {2*len(FEATS)+1} columns with "
          f"interactions\n")

    seasons = sorted(d["season"].unique())
    preds = []
    for i in range(2, len(seasons)):
        tr = d[d["season"].isin(seasons[:i])]
        te = d[(d["season"] == seasons[i]) & (d["days_left"] <= 7)].copy()
        if len(te) < 20:
            continue
        # pick alpha on the training seasons' own late games, by rank corr
        best, ba = -9, ALPHAS[0]
        for a in ALPHAS:
            inner_tr = tr[tr["season"].isin(seasons[:i - 1])]
            inner_te = tr[tr["season"] == seasons[i - 1]]
            inner_te = inner_te[inner_te["days_left"] <= 7]
            if len(inner_te) < 20 or len(inner_tr) < 500:
                continue
            p, _ = fit_predict(inner_tr, inner_te, a)
            c = np.corrcoef(p, inner_te["resid"].values)[0, 1]
            if np.isfinite(c) and c > best:
                best, ba = c, a
        p, _ = fit_predict(tr, te, ba)
        te["pred"] = p
        te["alpha"] = ba
        preds.append(te)
        print(f"  {seasons[i][4:13]}  train {len(tr):,}  test {len(te)}  "
              f"alpha {ba:>6}  corr(pred,resid) "
              f"{np.corrcoef(p, te['resid'])[0,1]:+.3f}")

    P = pd.concat(preds)
    print(f"\n  pooled out-of-sample final-7 games: {len(P):,}")
    print(f"  corr(pred, resid) = {np.corrcoef(P['pred'], P['resid'])[0,1]:+.4f}")

    print("\n" + "=" * 92)
    print("RANKED BY PREDICTED RESIDUAL — walking down from the top")
    print("=" * 92)
    P = P.sort_values("pred", ascending=False).reset_index(drop=True)
    rows = []
    for frac in (0.2, 0.3, 0.4, 0.6, 0.8, 1.0):
        k = int(len(P) * frac)
        s = P.head(k)
        ov = (s["resid"] > 0).mean()
        se = np.sqrt(ov * (1 - ov) / k)
        rows.append({"top": f"{int(100*frac)}%", "bets": k,
                     "mean pred": round(s["pred"].mean(), 2),
                     "mean resid": round(s["resid"].mean(), 2),
                     "over %": round(100 * ov, 2),
                     "95% CI": f"[{100*(ov-1.96*se):.1f}, {100*(ov+1.96*se):.1f}]",
                     "ROI110": round(100 * (ov * (100 / 110) - (1 - ov)), 2)})
    print(pd.DataFrame(rows).to_string(index=False))
    print(f"\n  unconditional LOSO baseline: 55.29%   break-even {100*BE:.2f}%")

    print("\n--- quintiles of predicted residual (monotonicity test) ---")
    P["q"] = pd.qcut(P["pred"], 5, labels=[1, 2, 3, 4, 5])
    r = []
    for q, s in P.groupby("q", observed=True):
        ov = (s["resid"] > 0).mean()
        r.append({"quintile": q, "n": len(s),
                  "mean pred": round(s["pred"].mean(), 2),
                  "mean resid": round(s["resid"].mean(), 2),
                  "over %": round(100 * ov, 2),
                  "ROI110": round(100 * (ov * (100 / 110) - (1 - ov)), 2)})
    t = pd.DataFrame(r)
    print(t.to_string(index=False))
    mono = t["over %"].is_monotonic_increasing
    sr = np.corrcoef(t["quintile"].astype(float), t["over %"])[0, 1]
    print(f"\n  monotone in over %: {mono}    rank corr across quintiles "
          f"{sr:+.3f}")
    P.to_csv("eos_rank_preds.csv", index=False)


if __name__ == "__main__":
    main()
