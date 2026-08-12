"""Two more ranking experiments, then stop.

EXPERIMENT 1 — specification check. Same features, same folds, but target
    P(Over) via ridge-logistic instead of E[R] via ridge. The payoff is
    I(R>0), and if conditional VARIANCE differs across late games then E[R|X]
    need not rank P(R>0|X). No new features, no model shopping.

EXPERIMENT 2 — regime-state variables. The previous failure asked ordinary
    basketball-history variables to identify which games experience an unusual
    behavioural regime. These describe WHY a game is abnormal:

      schedule    rest days, back-to-backs, games in last 7 -- RECONSTRUCTED from
                  the schedule, not taken from the vendor's 62%-populated column
      incentive   conference standings before the game: distance from the play-in
                  cutoff, elimination and clinch state, and the gap between the
                  two teams' stakes
      market      open-to-close line move, which says whether the market is
                  receiving information about the regime before tip-off

Conference assignments are hard-coded; there was no realignment in 2017-2026.

Same expanding-window OOS, same quintile/top-x% evaluation, same monotonicity
criterion. If both fail, the conclusion is that late-season TIMING carries the
information and conditional selection does not -- which is itself a market
result, not a modelling shortfall.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.preprocessing import StandardScaler

BE = 110 / 210
RAMP = 21.0
ALPHAS = [10.0, 30.0, 100.0, 300.0, 1000.0]
CS = [0.001, 0.003, 0.01, 0.03, 0.1]

EAST = {"Atlanta", "Boston", "Brooklyn", "Charlotte", "Chicago", "Cleveland",
        "Detroit", "Indiana", "Miami", "Milwaukee", "New York", "Orlando",
        "Philadelphia", "Toronto", "Washington"}


def build():
    from eos_rank import build as base_build
    d = base_build()
    d = d.sort_values("date").reset_index(drop=True)
    # base_build() already defines rest_h/rest_a from the vendor's 62%-populated
    # column; drop them, since the reconstructed versions replace them and the
    # merge below would otherwise silently produce rest_h_x / rest_h_y.
    d = d.drop(columns=[c for c in ("rest_h", "rest_a") if c in d.columns])
    d["conf_H"] = np.where(d["TEAM_H"].isin(EAST), "E", "W")
    d["conf_R"] = np.where(d["TEAM_R"].isin(EAST), "E", "W")
    # base_build() keeps every raw column, so the opening total is already here
    d["line_move"] = d["close_total"] - pd.to_numeric(d["OPENING TOTAL_H"],
                                                      errors="coerce")

    # ---- long panel: schedule + standings, all strictly prior ---------------
    rows = []
    for side, opp in (("H", "R"), ("R", "H")):
        rows.append(pd.DataFrame({
            "gid": d.index, "date": d["date"], "season": d["season"],
            "team": d[f"TEAM_{side}"], "conf": d[f"conf_{side}"],
            "win": (d[f"PTS_{side}"] > d[f"PTS_{opp}"]).astype(float)}))
    L = pd.concat(rows).sort_values(["season", "team", "date"])
    g = L.groupby(["season", "team"])
    L["prev_date"] = g["date"].shift(1)
    L["rest"] = (L["date"] - L["prev_date"]).dt.days - 1
    L["rest"] = L["rest"].clip(0, 7).fillna(3)
    L["b2b"] = (L["rest"] == 0).astype(float)
    L["cum_w"] = g["win"].transform(lambda s: s.shift(1).cumsum())
    L["gp"] = g.cumcount()
    L["wpct_b"] = L["cum_w"] / L["gp"].replace(0, np.nan)
    L["games_left"] = 82 - L["gp"]

    # conference standings as of each date: the play-in cutoff is the 10th wpct
    cut = (L.dropna(subset=["wpct_b"])
             .sort_values("date")
             .groupby(["season", "conf", "date"])["wpct_b"]
             .apply(lambda s: s.nlargest(10).min())
             .rename("cutoff").reset_index())
    cut["cutoff"] = (cut.groupby(["season", "conf"])["cutoff"]
                     .transform(lambda s: s.expanding().mean()))
    L = L.merge(cut, on=["season", "conf", "date"], how="left")
    L["gb_cutoff"] = (L["wpct_b"] - L["cutoff"]) * L["gp"]
    L["max_wpct"] = (L["cum_w"] + L["games_left"]) / 82.0
    L["eliminated"] = (L["max_wpct"] < L["cutoff"]).astype(float)
    L["clinched"] = (L["wpct_b"] * L["gp"] / 82.0 > L["cutoff"]).astype(float)
    # leverage: high when close to the cutoff with games left to matter
    L["leverage"] = np.exp(-np.abs(L["gb_cutoff"]) / 4.0)

    keep = ["date", "season", "team", "rest", "b2b", "gb_cutoff",
            "eliminated", "clinched", "leverage"]
    S = L[keep].drop_duplicates(["season", "team", "date"])

    clash = [f"{k}_{sfx}" for k in keep for sfx in ("h", "a")
             if f"{k}_{sfx}" in d.columns]
    assert not clash, f"merge would collide on {clash}"
    d = d.merge(S.add_suffix("_h").rename(columns={"date_h": "date",
                "season_h": "season", "team_h": "TEAM_H"}),
                on=["date", "season", "TEAM_H"], how="left")
    d = d.merge(S.add_suffix("_a").rename(columns={"date_a": "date",
                "season_a": "season", "team_a": "TEAM_R"}),
                on=["date", "season", "TEAM_R"], how="left")
    hf = d["spread"] < 0
    for stem in ("rest", "b2b", "gb_cutoff", "eliminated", "clinched", "leverage"):
        d[f"fav_{stem}"] = np.where(hf, d[f"{stem}_h"], d[f"{stem}_a"])
        d[f"dog_{stem}"] = np.where(hf, d[f"{stem}_a"], d[f"{stem}_h"])
    d["incentive_gap"] = d["fav_leverage"] - d["dog_leverage"]
    d["min_leverage"] = d[["fav_leverage", "dog_leverage"]].min(axis=1)
    d["both_out"] = d["fav_eliminated"] * d["dog_eliminated"]
    return d


BASE = ["close_total", "abs_spread", "fav_wpct", "dog_wpct", "wpct_gap",
        "dog_futility", "fav_locked", "fav_r5_pts", "dog_r5_pts",
        "fav_pts_surprise", "dog_pts_surprise", "fav_r5_g_resid",
        "dog_r5_g_resid", "fav_r20_g_resid", "dog_r20_g_resid"]
REGIME = ["fav_rest", "dog_rest", "fav_b2b", "dog_b2b", "fav_gb_cutoff",
          "dog_gb_cutoff", "fav_eliminated", "dog_eliminated", "fav_clinched",
          "dog_clinched", "incentive_gap", "min_leverage", "both_out",
          "line_move"]


def design(x, feats):
    X = x[feats].values
    w = x["late_w"].values.reshape(-1, 1)
    return np.hstack([X, w, X * w])


def run(d, feats, kind, label):
    seasons = sorted(d["season"].unique())
    out = []
    for i in range(2, len(seasons)):
        tr = d[d["season"].isin(seasons[:i])]
        te = d[(d["season"] == seasons[i]) & (d["days_left"] <= 7)].copy()
        if len(te) < 20:
            continue
        sc = StandardScaler().fit(design(tr, feats))
        Xtr, Xte = sc.transform(design(tr, feats)), sc.transform(design(te, feats))
        if kind == "ridge":
            m = Ridge(alpha=300.0).fit(Xtr, tr["resid"].values)
            te["pred"] = m.predict(Xte)
        else:
            y = (tr["resid"] > 0).astype(int).values
            m = LogisticRegression(C=0.01, max_iter=1000).fit(Xtr, y)
            te["pred"] = m.predict_proba(Xte)[:, 1]
        out.append(te)
    P = pd.concat(out).sort_values("pred", ascending=False).reset_index(drop=True)
    print(f"\n{'='*92}\n{label}   (n={len(P)}, "
          f"corr(pred,resid)={np.corrcoef(P['pred'], P['resid'])[0,1]:+.4f})\n{'='*92}")
    rows = []
    for frac in (0.2, 0.4, 0.6, 1.0):
        k = int(len(P) * frac)
        s = P.head(k)
        ov = (s["resid"] > 0).mean()
        rows.append({"top": f"{int(100*frac)}%", "bets": k,
                     "over %": round(100 * ov, 2),
                     "ROI110": round(100 * (ov * (100 / 110) - (1 - ov)), 2)})
    print(pd.DataFrame(rows).to_string(index=False))
    P["q"] = pd.qcut(P["pred"], 5, labels=[1, 2, 3, 4, 5], duplicates="drop")
    t = P.groupby("q", observed=True).apply(lambda s: pd.Series({
        "n": len(s), "over %": round(100 * (s["resid"] > 0).mean(), 2)}),
        include_groups=False)
    print("\n  quintiles (1=lowest pred):  " +
          "  ".join(f"Q{i}={v:.1f}%" for i, v in zip(t.index, t["over %"])))
    rc = np.corrcoef(np.arange(len(t)), t["over %"].values)[0, 1]
    print(f"  monotone: {t['over %'].is_monotonic_increasing}   "
          f"rank corr {rc:+.3f}")
    return P


def main():
    d = build()
    db = d.dropna(subset=BASE)
    dr = d.dropna(subset=BASE + REGIME)
    print(f"base features complete:   {len(db):,} games")
    print(f"+regime features complete: {len(dr):,} games "
          f"({int((dr['days_left']<=7).sum())} final-7)")
    print(f"  rest reconstructed: {100*d['fav_rest'].notna().mean():.1f}% "
          f"(vendor column was 62%)")
    print(f"  line_move available: {100*d['line_move'].notna().mean():.1f}%")

    run(dr, BASE, "ridge", "EXP 0 — base features, ridge on residual (reference)")
    run(dr, BASE, "logit", "EXP 1 — base features, LOGISTIC on Over/Under")
    run(dr, BASE + REGIME, "ridge", "EXP 2a — +regime state, ridge on residual")
    run(dr, BASE + REGIME, "logit", "EXP 2b — +regime state, LOGISTIC on Over")


if __name__ == "__main__":
    main()
