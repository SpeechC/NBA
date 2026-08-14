"""Moneyline residual audit — the probability-market analogue of the totals audit.

    p_i = devigged fair home win probability from the book's two moneylines
    e_i = y_i - p_i            y = 1 if the home team wins
    z_i = (y_i - p_i) / sqrt(p_i (1-p_i))     standardised

The raw ML residual is mechanically heteroskedastic, Var(e|p) = p(1-p), so the
variance tests must use z, not e. Under a correctly priced market z is unit
variance and serially independent.

  1 CALIBRATION      Brier, log loss, calibration by implied decile,
                     favourite/underdog and home/away splits
  2 NOISE AUDIT      ACF and Ljung-Box on z, |z|, z^2; team-level persistence of
                     E[z|team] (systematically over/underpriced teams) and
                     SD(z|team) (teams the market finds harder to price)
  3 CONDITIONAL      logit(P) = logit(p) + f(X), the market entering as an
                     OFFSET so that f(X)=0 IS the efficient-market benchmark.
                     Walk-forward. This asks directly whether pregame
                     information can correct the book's own probability, which
                     is a stronger test than building a win model from scratch.
  4 RANKABILITY      Delta = p* - p. Rank games by Delta and require monotone
                     calibration error, then ROI at the actual moneyline price.

STOPPING RULE, fixed in advance: if the offset model cannot improve OOS log loss
AND Brier over the devigged market, and the Delta buckets are non-monotone, then
neither the conditional-mean market (totals) nor the probability market contains
accessible residual structure in our information set.
"""
import warnings

import numpy as np
import pandas as pd
from scipy import optimize, stats

warnings.filterwarnings("ignore")

from sklearn.preprocessing import StandardScaler

ROLL = 15


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
    d["mlh"], d["mla"] = n("MONEYLINE_H"), n("MONEYLINE_R")
    d["margin"] = d["PTS_H"] - d["PTS_R"]
    d["actual"] = d["PTS_H"] + d["PTS_R"]
    d = d.dropna(subset=["total", "spread", "mlh", "mla", "margin"])
    d = d[d["margin"] != 0]
    ph = np.where(d["mlh"] < 0, -d["mlh"] / (-d["mlh"] + 100),
                  100 / (d["mlh"] + 100))
    pa = np.where(d["mla"] < 0, -d["mla"] / (-d["mla"] + 100),
                  100 / (d["mla"] + 100))
    d["p"] = ph / (ph + pa)
    d["hold"] = ph + pa - 1
    d = d[(d["p"] > 0.02) & (d["p"] < 0.98)].copy()
    d["y"] = (d["margin"] > 0).astype(float)
    d["e"] = d["y"] - d["p"]
    d["z"] = d["e"] / np.sqrt(d["p"] * (1 - d["p"]))
    d["logit_p"] = np.log(d["p"] / (1 - d["p"]))
    d["abs_spread"] = d["spread"].abs()

    qp = quarter_poss().groupby("gid")["poss"].sum().rename("poss").reset_index()
    d = d.merge(qp, on="gid", how="left")
    d["ppp"] = d["actual"] / d["poss"]
    for s in ("H", "R"):
        d[f"efg_{s}"] = n(f"TEAM_eFGP_{s}")
    d = d.sort_values("date").reset_index(drop=True)

    rows = []
    for s, o in (("H", "R"), ("R", "H")):
        rows.append(pd.DataFrame({
            "gid": d["gid"], "yr": d["yr"], "date": d["date"],
            "team": d[f"TEAM_{s}"], "side": s,
            "poss": d["poss"], "ppp": d["ppp"], "efg": d[f"efg_{s}"],
            "pd": d[f"PTS_{s}"] - d[f"PTS_{o}"],
            "win": (d[f"PTS_{s}"] > d[f"PTS_{o}"]).astype(float)}))
    P = pd.concat(rows).sort_values("date")
    g = P.groupby(["yr", "team"])
    P["prev"] = g["date"].shift(1)
    P["rest"] = ((P["date"] - P["prev"]).dt.days - 1).clip(0, 6).fillna(3)
    for c in ("poss", "ppp", "efg", "pd"):
        P[f"m_{c}"] = g[c].transform(
            lambda s: s.shift(1).rolling(ROLL, min_periods=8).mean())
        P[f"v_{c}"] = g[c].transform(
            lambda s: s.shift(1).rolling(ROLL, min_periods=8).std(ddof=1))
    P["wpct"] = g["win"].transform(lambda s: s.shift(1).expanding().mean())
    keep = (["gid", "side", "rest", "wpct"]
            + [f"{p}_{c}" for p in ("m", "v") for c in ("poss", "ppp", "efg", "pd")])
    W = P[keep]
    h = W[W["side"] == "H"].drop(columns="side").add_suffix("_h").rename(
        columns={"gid_h": "gid"})
    a = W[W["side"] == "R"].drop(columns="side").add_suffix("_a").rename(
        columns={"gid_a": "gid"})
    d = d.merge(h, on="gid").merge(a, on="gid")
    d["str_diff"] = d["m_pd_h"] - d["m_pd_a"]
    d["wpct_diff"] = d["wpct_h"] - d["wpct_a"]
    d["pace_sum"] = d["m_poss_h"] + d["m_poss_a"]
    d["pace_diff"] = (d["m_poss_h"] - d["m_poss_a"]).abs()
    d["vol_sum"] = d["v_pd_h"] + d["v_pd_a"]
    d["rest_diff"] = d["rest_h"] - d["rest_a"]
    return d


FEATS = ["spread", "abs_spread", "total", "str_diff", "wpct_diff",
         "pace_sum", "pace_diff", "vol_sum", "rest_diff",
         "v_poss_h", "v_poss_a", "v_efg_h", "v_efg_a"]


def fit_offset(X, y, off, alpha=10.0):
    """logit(P) = off + X @ b, minimising penalised log loss."""
    def nll(b):
        eta = off + X @ b
        p = 1 / (1 + np.exp(-eta))
        p = np.clip(p, 1e-9, 1 - 1e-9)
        return (-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))
                + alpha * (b @ b) / len(y))
    r = optimize.minimize(nll, np.zeros(X.shape[1]), method="L-BFGS-B")
    return r.x


def acf(x, lags=5):
    x = np.asarray(x, float) - np.mean(x)
    den = (x ** 2).sum()
    return [float((x[k:] * x[:-k]).sum() / den) for k in range(1, lags + 1)]


def main():
    d = build()
    dc = d.dropna(subset=FEATS).reset_index(drop=True)
    print(f"{len(d):,} games with moneylines; {len(dc):,} with complete states")
    print(f"  mean hold {100*d['hold'].mean():.2f}%   "
          f"home win rate {d['y'].mean():.4f}   mean p {d['p'].mean():.4f}")

    print("\n" + "=" * 92)
    print("1 — CALIBRATION")
    print("=" * 92)
    print(f"  Brier {np.mean((d['p']-d['y'])**2):.5f}   "
          f"log loss {-np.mean(d['y']*np.log(d['p'])+(1-d['y'])*np.log(1-d['p'])):.5f}")
    d["dec"] = pd.cut(d["p"], np.arange(0, 1.01, 0.1))
    t = d.groupby("dec", observed=True).apply(lambda s: pd.Series({
        "n": len(s), "implied": round(s["p"].mean(), 4),
        "actual": round(s["y"].mean(), 4),
        "gap pp": round(100 * (s["y"].mean() - s["p"].mean()), 2),
        "se pp": round(100 * np.sqrt(s["y"].mean()*(1-s["y"].mean())/len(s)), 2)}),
        include_groups=False)
    print(t.to_string())
    fav = d[d["spread"] < 0]
    dog = d[d["spread"] > 0]
    print(f"\n  home favourites n={len(fav):,} gap "
          f"{100*(fav['y'].mean()-fav['p'].mean()):+.2f}pp")
    print(f"  home dogs       n={len(dog):,} gap "
          f"{100*(dog['y'].mean()-dog['p'].mean()):+.2f}pp")

    print("\n" + "=" * 92)
    print("2 — NOISE AUDIT on the standardised residual z")
    print("=" * 92)
    print(f"  z: mean {d['z'].mean():+.4f}  sd {d['z'].std():.4f} "
          f"(unit variance expected)")
    day = d.groupby("date")["z"].agg(["mean", "size"])
    day = day[day["size"] >= 4]
    for lab, x in (("z", day["mean"]), ("|z|", day["mean"].abs()),
                   ("z^2", day["mean"] ** 2)):
        r = acf(x, 5)
        q = len(x) * (len(x) + 2) * sum(v**2 / (len(x)-k-1)
                                        for k, v in enumerate(r))
        print(f"    day-level {lab:4} acf " + " ".join(f"{v:+.3f}" for v in r)
              + f"   LB p={1-stats.chi2.cdf(q,5):.4f}")
    rows = []
    for s, o in (("H", "R"), ("R", "H")):
        rows.append(pd.DataFrame({"team": d[f"TEAM_{s}"], "yr": d["yr"],
                                  "z": d["z"] * (1 if s == "H" else -1)}))
    Z = pd.concat(rows)
    E, L = [2017, 2018, 2020], [2021, 2022, 2023, 2024]
    r = []
    for t_, s in Z.groupby("team"):
        a, b = s[s["yr"].isin(E)]["z"], s[s["yr"].isin(L)]["z"]
        if len(a) > 80 and len(b) > 80:
            r.append({"m1": a.mean(), "m2": b.mean(),
                      "s1": a.std(ddof=1), "s2": b.std(ddof=1)})
    r = pd.DataFrame(r)
    print(f"\n  team persistence, {len(r)} teams:")
    print(f"    E[z|team]  corr {np.corrcoef(r['m1'], r['m2'])[0,1]:+.3f}   "
          f"(systematically over/underpriced teams)")
    print(f"    SD(z|team) corr {np.corrcoef(r['s1'], r['s2'])[0,1]:+.3f}   "
          f"(teams the market finds harder to price)")

    print("\n" + "=" * 92)
    print("3 — CONDITIONAL: logit(P) = logit(p) + f(X), market as OFFSET")
    print("=" * 92)
    yrs = sorted(dc["yr"].unique())
    out = []
    for i in range(2, len(yrs)):
        tr = dc[dc["yr"].isin(yrs[:i])]
        te = dc[dc["yr"] == yrs[i]].copy()
        if len(te) < 100:
            continue
        sc = StandardScaler().fit(tr[FEATS])
        b = fit_offset(sc.transform(tr[FEATS]), tr["y"].values,
                       tr["logit_p"].values)
        eta = te["logit_p"].values + sc.transform(te[FEATS]) @ b
        te["pstar"] = 1 / (1 + np.exp(-eta))
        out.append(te)
    R = pd.concat(out)
    y = R["y"].values
    for lab, p in (("market p", R["p"].values), ("corrected p*", R["pstar"].values)):
        p = np.clip(p, 1e-9, 1 - 1e-9)
        print(f"  {lab:14} log loss {-np.mean(y*np.log(p)+(1-y)*np.log(1-p)):.5f}"
              f"   Brier {np.mean((p-y)**2):.5f}")
    print(f"  n={len(R):,} out-of-sample games")

    print("\n" + "=" * 92)
    print("4 — RANKABILITY of Delta = p* - p")
    print("=" * 92)
    R["delta"] = R["pstar"] - R["p"]
    print(f"  Delta: mean {R['delta'].mean():+.4f}  sd {R['delta'].std():.4f}  "
          f"range [{R['delta'].min():+.3f}, {R['delta'].max():+.3f}]")
    R["q"] = pd.qcut(R["delta"], 5, labels=[1, 2, 3, 4, 5])
    rows = []
    for q, s in R.groupby("q", observed=True):
        gap = s["y"].mean() - s["p"].mean()
        se = np.sqrt(s["y"].mean() * (1 - s["y"].mean()) / len(s))
        rows.append({"Q": q, "n": len(s), "Delta": round(s["delta"].mean(), 4),
                     "implied": round(s["p"].mean(), 4),
                     "actual": round(s["y"].mean(), 4),
                     "gap pp": round(100 * gap, 2),
                     "±1.96se": round(100 * 1.96 * se, 2)})
    t = pd.DataFrame(rows)
    print(t.to_string(index=False))
    print(f"\n  monotone in gap: {t['gap pp'].is_monotonic_increasing}"
          f"   Q5-Q1 swing {t['gap pp'].iloc[-1]-t['gap pp'].iloc[0]:+.2f}pp")


if __name__ == "__main__":
    main()
