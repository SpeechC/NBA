"""Systematic residual-predictability screen.

Model the closing-total residual DIRECTLY. Three targets:

    Y1 = e            signed residual        benchmark: e_hat = 0
    Y2 = |e|          magnitude              benchmark: training mean |e|
    Y3 = 1(e > 0)     direction              benchmark: p = 0.5

Features, all lagged and computed only from prior games:

  LOCATION     closing total, spread, |spread|, rolling mean possessions,
               rolling mean eFG%, rolling mean points per possession
  STABILITY    rolling SD of possessions, eFG%, PPP, 3PA rate, FTA rate --
               a team can be in a volatile STRETCH even though team-level
               volatility does not persist across seasons (already shown), so
               this is a state variable, not a team characteristic
  INTERACTION  |pace difference|, combined pace volatility, combined shooting
               volatility, pace product

Walk-forward by season, expanding window, no tuning inside the test years.

THE POINT IS NOT R^2. Against an 18-point residual SD, a 1% R^2 is a useless
forecasting model and could still be a business if the extreme buckets separate
by 1.5-2 points. So the quintile table is the primary output and R^2 is a
footnote.
"""
import warnings

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")

from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.preprocessing import StandardScaler

ROLL = 15
BE = 110 / 210


def build():
    from poss_vs_eff import quarter_poss
    from prepare_data import CSV, season_label
    raw = pd.read_csv(CSV, low_memory=False)
    raw["lbl"] = season_label(raw).astype(str)
    d = raw[raw["lbl"].str.contains("Regular Season", na=False)].copy()
    n = lambda c: pd.to_numeric(d[c], errors="coerce")
    d["gid"] = d["GAME-ID"].astype(str).str.zfill(10)
    d["date"] = pd.to_datetime(d["DATE"], errors="coerce")
    d["yr"] = d["lbl"].str.extract(r"(\d{4})")[0].astype(int)
    d["total"] = n("CLOSING TOTAL_H")
    d["spread"] = n("CLOSING SPREAD_H")
    d["actual"] = d["PTS_H"] + d["PTS_R"]
    d = d.dropna(subset=["total", "spread", "actual"])
    d = d[d["total"].between(150, 300)].copy()
    d["e"] = d["actual"] - d["total"]
    d["abs_spread"] = d["spread"].abs()
    for s in ("H", "R"):
        d[f"efg_{s}"] = n(f"TEAM_eFGP_{s}")
        d[f"fga_{s}"], d[f"tpa_{s}"] = n(f"TEAM_FGA_{s}"), n(f"TEAM_3PA_{s}")
        d[f"fta_{s}"] = n(f"TEAM_FTA_{s}")
    qp = quarter_poss().groupby("gid")["poss"].sum().rename("poss").reset_index()
    d = d.merge(qp, on="gid", how="left")
    d["ppp"] = d["actual"] / d["poss"]
    d = d.sort_values("date").reset_index(drop=True)

    # per-team panel of game-level process values
    rows = []
    for s, o in (("H", "R"), ("R", "H")):
        rows.append(pd.DataFrame({
            "gid": d["gid"], "yr": d["yr"], "date": d["date"],
            "team": d[f"TEAM_{s}"], "side": s,
            "poss": d["poss"], "ppp": d["ppp"], "efg": d[f"efg_{s}"],
            "tpa": d[f"tpa_{s}"] / d[f"fga_{s}"],
            "fta": d[f"fta_{s}"] / d[f"fga_{s}"]}))
    P = pd.concat(rows).sort_values("date")
    g = P.groupby(["yr", "team"])
    for c in ("poss", "ppp", "efg", "tpa", "fta"):
        P[f"m_{c}"] = g[c].transform(
            lambda s: s.shift(1).rolling(ROLL, min_periods=8).mean())
        P[f"v_{c}"] = g[c].transform(
            lambda s: s.shift(1).rolling(ROLL, min_periods=8).std(ddof=1))
    keep = ["gid", "side"] + [f"{p}_{c}" for p in ("m", "v")
                              for c in ("poss", "ppp", "efg", "tpa", "fta")]
    W = P[keep]
    h = W[W["side"] == "H"].drop(columns="side").add_suffix("_h").rename(
        columns={"gid_h": "gid"})
    a = W[W["side"] == "R"].drop(columns="side").add_suffix("_a").rename(
        columns={"gid_a": "gid"})
    d = d.merge(h, on="gid").merge(a, on="gid")

    # combine to game level
    for c in ("poss", "ppp", "efg", "tpa", "fta"):
        d[f"M_{c}"] = d[f"m_{c}_h"] + d[f"m_{c}_a"]
        d[f"V_{c}"] = d[f"v_{c}_h"] + d[f"v_{c}_a"]
    d["pace_diff"] = (d["m_poss_h"] - d["m_poss_a"]).abs()
    d["pace_prod"] = d["m_poss_h"] * d["m_poss_a"] / 100.0
    return d


FEATS = (["total", "spread", "abs_spread"]
         + [f"M_{c}" for c in ("poss", "ppp", "efg", "tpa", "fta")]
         + [f"V_{c}" for c in ("poss", "ppp", "efg", "tpa", "fta")]
         + ["pace_diff", "pace_prod"])


def walk(d, target, kind):
    yrs = sorted(d["yr"].unique())
    out = []
    for i in range(2, len(yrs)):
        tr = d[d["yr"].isin(yrs[:i])]
        te = d[d["yr"] == yrs[i]].copy()
        if len(te) < 100:
            continue
        sc = StandardScaler().fit(tr[FEATS])
        X, Xt = sc.transform(tr[FEATS]), sc.transform(te[FEATS])
        if kind == "ridge":
            m = Ridge(alpha=200.0).fit(X, tr[target])
            te["pred"] = m.predict(Xt)
            te["bench"] = 0.0 if target == "e" else tr[target].mean()
        else:
            m = LogisticRegression(C=0.05, max_iter=1000).fit(X, tr[target])
            te["pred"] = m.predict_proba(Xt)[:, 1]
            te["bench"] = 0.5
        out.append(te)
    return pd.concat(out)


def report(P, target, kind, lab):
    print("\n" + "=" * 92)
    print(lab)
    print("=" * 92)
    y, p, b = P[target].values, P["pred"].values, P["bench"].values
    if kind == "ridge":
        r = np.corrcoef(p, y)[0, 1]
        t = r * np.sqrt(len(y) - 2) / np.sqrt(1 - r * r)
        r2 = 1 - ((y - p) ** 2).sum() / ((y - b) ** 2).sum()
        print(f"  n={len(y):,}  corr(pred, actual) {r:+.4f}  t={t:+.2f}   "
              f"OOS R^2 vs benchmark {100*r2:+.3f}%")
        print(f"  pred range [{p.min():+.2f}, {p.max():+.2f}]  sd {p.std():.3f}"
              f"   actual sd {y.std():.2f}")
    else:
        ll = -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))
        llb = -np.mean(y * np.log(0.5) + (1 - y) * np.log(0.5))
        print(f"  n={len(y):,}  log-loss {ll:.5f}  vs benchmark {llb:.5f}  "
              f"gain {llb-ll:+.5f}")
        print(f"  pred range [{p.min():.4f}, {p.max():.4f}]  sd {p.std():.4f}")
    P = P.copy()
    P["q"] = pd.qcut(P["pred"], 5, labels=[1, 2, 3, 4, 5], duplicates="drop")
    rows = []
    for q, s in P.groupby("q", observed=True):
        ov = (s["e"] > 0).mean()
        se = np.sqrt(ov * (1 - ov) / len(s))
        rows.append({"Q": q, "n": len(s), "pred": round(s["pred"].mean(), 3),
                     "actual e": round(s["e"].mean(), 3),
                     "|e|": round(s["e"].abs().mean(), 2),
                     "over %": round(100 * ov, 2),
                     "±1.96se": round(100 * 1.96 * se, 2)})
    t = pd.DataFrame(rows)
    print(t.to_string(index=False))
    print(f"  actual-e spread Q5-Q1: {t['actual e'].iloc[-1]-t['actual e'].iloc[0]:+.3f} pts"
          f"   monotone: {t['actual e'].is_monotonic_increasing}")
    print(f"  over%   spread Q5-Q1: {t['over %'].iloc[-1]-t['over %'].iloc[0]:+.2f}pp"
          f"   (need ~{100*BE-50:.2f}pp from 50 to clear the vig)")


def main():
    d = build().dropna(subset=FEATS + ["e"])
    print(f"{len(d):,} games with complete lagged states, "
          f"{len(FEATS)} features, seasons {sorted(d['yr'].unique())}")
    print(f"  e: mean {d['e'].mean():+.3f}  sd {d['e'].std():.2f}  "
          f"MAE {d['e'].abs().mean():.2f}")
    d["abs_e"] = d["e"].abs()
    d["dir"] = (d["e"] > 0).astype(int)

    report(walk(d, "e", "ridge"), "e", "ridge",
           "Y1 — SIGNED RESIDUAL   (benchmark: predict 0)")
    report(walk(d, "abs_e", "ridge"), "abs_e", "ridge",
           "Y2 — MAGNITUDE |e|     (benchmark: training mean |e|)")
    report(walk(d, "dir", "logit"), "dir", "logit",
           "Y3 — DIRECTION 1(e>0)  (benchmark: p = 0.5)")


if __name__ == "__main__":
    main()
