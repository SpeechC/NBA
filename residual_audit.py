"""Audit of NBA market residuals. Characterisation, not a strategy search.

    e_i = actual - closing line, for the full-game total, the spread, and H1.

Unconditional mean accuracy is already established (FG total: -0.17, t = -0.28).
That is not conditional unbiasedness, and says nothing about the second moment.

  1 SERIAL INDEPENDENCE   ACF and Ljung-Box on e, |e| and e^2, at day level and
                          within-team. Corr(e_t, e_{t-1}) ~ 0 with
                          Corr(e_t^2, e_{t-1}^2) > 0 would mean hard-to-price
                          periods cluster.
  2 TEAM ERROR VARIANCE   is SD(e | team) persistent across an early/late split?
                          Are some teams intrinsically harder to price?
  3 PROCESS VOLATILITY    persistence of sigma(possessions), sigma(eFG),
                          sigma(3PA rate), sigma(FTA rate), sigma(PPP). This is
                          a GATE -- do not assume any variance estimate is
                          stable because one looked interesting.
  4 DOES IT PREDICT       for characteristics passing 3: e^2 ~ sigma_char.
                          beta = 0 means DK's pricing already handles the state.
  5 gated on 4.
  6 CONDITIONAL MEAN      cross-fitted e ~ f(X) using only prior games, on
                          economically motivated states. Modelling
                          actual-minus-market directly, not the outcome.
"""
import warnings

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")
RNG = np.random.default_rng(0)

EARLY = [2017, 2018, 2020]
LATE = [2021, 2022, 2023, 2024]


def build():
    from halves import period_scores
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
    d["margin"] = d["PTS_H"] - d["PTS_R"]
    d = d.dropna(subset=["total", "spread", "actual"])
    d = d[d["total"].between(150, 300)].copy()
    d["e_tot"] = d["actual"] - d["total"]
    d["e_ats"] = d["margin"] + d["spread"]
    for s in ("H", "R"):
        d[f"efg_{s}"] = n(f"TEAM_eFGP_{s}")
        d[f"fga_{s}"], d[f"tpa_{s}"] = n(f"TEAM_FGA_{s}"), n(f"TEAM_3PA_{s}")
        d[f"fta_{s}"] = n(f"TEAM_FTA_{s}")
    d["efg"] = (d["efg_H"] + d["efg_R"]) / 2
    d["tpa_rate"] = (d["tpa_H"] + d["tpa_R"]) / (d["fga_H"] + d["fga_R"])
    d["fta_rate"] = (d["fta_H"] + d["fta_R"]) / (d["fga_H"] + d["fga_R"])
    qp = quarter_poss().groupby("gid")["poss"].sum().rename("poss").reset_index()
    d = d.merge(qp, on="gid", how="left")
    d["ppp"] = d["actual"] / d["poss"]
    ps = period_scores("RegularSeason")
    d = d.merge(ps[["gid", "q1", "q2"]], on="gid", how="left")
    d["h1"] = d["q1"] + d["q2"]
    return d.sort_values("date").reset_index(drop=True)


def acf(x, lags=8):
    x = np.asarray(x, dtype=float)
    x = x - x.mean()
    n = len(x)
    den = (x ** 2).sum()
    return [float((x[k:] * x[:-k]).sum() / den) for k in range(1, lags + 1)]


def ljung(r, n, m):
    q = n * (n + 2) * sum(rk ** 2 / (n - k - 1) for k, rk in enumerate(r[:m]))
    return q, 1 - stats.chi2.cdf(q, m)


def test1(d):
    print("=" * 96)
    print("1 — SERIAL INDEPENDENCE")
    print("=" * 96)
    day = d.groupby("date").agg(e=("e_tot", "mean"), n=("e_tot", "size"))
    day = day[day["n"] >= 4]
    print(f"  day-level series: {len(day)} days with >=4 games")
    for lab, x in (("e", day["e"]), ("|e|", day["e"].abs()),
                   ("e^2", day["e"] ** 2)):
        r = acf(x, 5)
        q, p = ljung(r, len(x), 5)
        print(f"    {lab:4} acf(1..5) " + " ".join(f"{v:+.3f}" for v in r)
              + f"   Ljung-Box Q={q:.1f}  p={p:.4f}")

    rows = []
    for side in ("H", "R"):
        rows.append(pd.DataFrame({"team": d[f"TEAM_{side}"], "yr": d["yr"],
                                  "date": d["date"], "e": d["e_tot"]}))
    L = pd.concat(rows).sort_values("date")
    print("\n  within-team sequence (lag 1, pooled across teams):")
    for lab, f in (("e", lambda s: s), ("|e|", np.abs),
                   ("e^2", lambda s: s ** 2)):
        a, b = [], []
        for (t, y), s in L.groupby(["team", "yr"]):
            v = f(s["e"]).values
            if len(v) > 20:
                a.extend(v[1:]); b.extend(v[:-1])
        r = np.corrcoef(a, b)[0, 1]
        tt = r * np.sqrt(len(a) - 2) / np.sqrt(1 - r * r)
        print(f"    {lab:4} corr {r:+.4f}  t={tt:+.2f}  n={len(a):,}")


def persist(df, key, val, agg, lab, early=EARLY, late=LATE, minn=80):
    rows = []
    for t, s in df.groupby(key):
        a, b = s[s["yr"].isin(early)][val], s[s["yr"].isin(late)][val]
        a, b = a.dropna(), b.dropna()
        if len(a) < minn or len(b) < minn:
            continue
        rows.append({key: t, "x": agg(a), "y": agg(b)})
    t = pd.DataFrame(rows)
    if len(t) < 10:
        print(f"  {lab:26} too few groups")
        return np.nan
    r = np.corrcoef(t["x"], t["y"])[0, 1]
    tt = r * np.sqrt(len(t) - 2) / np.sqrt(1 - r * r)
    print(f"  {lab:26} corr {r:+.3f}  t={tt:+5.2f}  n={len(t)}  "
          f"range {t['x'].min():.3f}..{t['x'].max():.3f}")
    return r


def test23(d):
    print("\n" + "=" * 96)
    print("2 — TEAM MARKET-ERROR VARIANCE: persistent?")
    print("=" * 96)
    rows = []
    for side in ("H", "R"):
        rows.append(pd.DataFrame({"team": d[f"TEAM_{side}"], "yr": d["yr"],
                                  "e": d["e_tot"], "ats": d["e_ats"],
                                  "poss": d["poss"], "efg": d["efg"],
                                  "tpa": d["tpa_rate"], "fta": d["fta_rate"],
                                  "ppp": d["ppp"]}))
    L = pd.concat(rows)
    persist(L, "team", "e", lambda s: s.std(ddof=1), "SD(total residual)")
    persist(L, "team", "ats", lambda s: s.std(ddof=1), "SD(ATS residual)")
    persist(L, "team", "e", lambda s: s.mean(), "MEAN(total residual)")

    print("\n" + "=" * 96)
    print("3 — PROCESS VOLATILITY: which team variances persist at all? (GATE)")
    print("=" * 96)
    out = {}
    for c, lab in (("poss", "SD(possessions)"), ("efg", "SD(eFG%)"),
                   ("tpa", "SD(3PA rate)"), ("fta", "SD(FTA rate)"),
                   ("ppp", "SD(points per poss)")):
        out[c] = persist(L, "team", c, lambda s: s.std(ddof=1), lab)
    print("\n  for reference, the MEANS of the same processes:")
    for c, lab in (("poss", "MEAN(possessions)"), ("efg", "MEAN(eFG%)"),
                   ("tpa", "MEAN(3PA rate)")):
        persist(L, "team", c, lambda s: s.mean(), lab)
    return L, out


def test4(d, L, gates):
    print("\n" + "=" * 96)
    print("4 — does persistent process volatility predict |market error|?")
    print("=" * 96)
    good = [c for c, r in gates.items() if np.isfinite(r) and r > 0.3]
    if not good:
        print("  no process volatility passed the persistence gate (r > 0.30).")
        print("  Test 4 is not run.")
        return
    early = L[L["yr"].isin(EARLY)]
    sig = early.groupby("team").agg(**{f"s_{c}": (c, lambda s: s.std(ddof=1))
                                       for c in good}).reset_index()
    te = d[d["yr"].isin(LATE)].copy()
    for suf, col in (("_h", "TEAM_H"), ("_a", "TEAM_R")):
        te = te.merge(sig.add_suffix(suf).rename(columns={f"team{suf}": col}),
                      on=col, how="inner")
    for c in good:
        te[f"S_{c}"] = (te[f"s_{c}_h"] + te[f"s_{c}_a"]) / 2
        y = (te["e_tot"] ** 2).values
        x = te[f"S_{c}"].values
        ok = np.isfinite(x) & np.isfinite(y)
        r = np.corrcoef(x[ok], y[ok])[0, 1]
        tt = r * np.sqrt(ok.sum() - 2) / np.sqrt(1 - r * r)
        print(f"  e^2 ~ frozen {c:5} volatility   corr {r:+.4f}  t={tt:+.2f}  "
              f"n={ok.sum():,}")


def test6(d):
    print("\n" + "=" * 96)
    print("6 — CONDITIONAL MEAN BIAS, cross-fitted (expanding window)")
    print("=" * 96)
    from sklearn.linear_model import Ridge
    from sklearn.preprocessing import StandardScaler
    d = d.copy()
    d["abs_spread"] = d["spread"].abs()
    feats = ["total", "abs_spread", "spread"]
    for c in ("poss", "efg", "tpa_rate", "fta_rate"):
        rows = []
        for side in ("H", "R"):
            rows.append(pd.DataFrame({"gid": d["gid"], "yr": d["yr"],
                                      "date": d["date"],
                                      "team": d[f"TEAM_{side}"], "v": d[c]}))
        P = pd.concat(rows).sort_values("date")
        P[f"r10_{c}"] = (P.groupby(["yr", "team"])["v"]
                         .transform(lambda s: s.shift(1)
                                    .rolling(10, min_periods=5).mean()))
        agg = P.groupby("gid")[f"r10_{c}"].mean().reset_index()
        d = d.merge(agg, on="gid", how="left")
        feats.append(f"r10_{c}")
    d = d.dropna(subset=feats + ["e_tot"]).reset_index(drop=True)
    print(f"  {len(d):,} games with complete lagged states, "
          f"{len(feats)} features")
    yrs = sorted(d["yr"].unique())
    out = []
    for i in range(2, len(yrs)):
        tr = d[d["yr"].isin(yrs[:i])]
        te = d[d["yr"] == yrs[i]].copy()
        sc = StandardScaler().fit(tr[feats])
        m = Ridge(alpha=100.0).fit(sc.transform(tr[feats]), tr["e_tot"])
        te["pred"] = m.predict(sc.transform(te[feats]))
        out.append(te)
    P = pd.concat(out)
    r = np.corrcoef(P["pred"], P["e_tot"])[0, 1]
    tt = r * np.sqrt(len(P) - 2) / np.sqrt(1 - r * r)
    print(f"  out-of-sample corr(predicted error, actual error) = {r:+.4f}"
          f"  t={tt:+.2f}  n={len(P):,}")
    P["q"] = pd.qcut(P["pred"], 5, labels=[1, 2, 3, 4, 5])
    t = P.groupby("q", observed=True).apply(lambda s: pd.Series({
        "n": len(s), "pred": round(s["pred"].mean(), 2),
        "actual e": round(s["e_tot"].mean(), 2),
        "over %": round(100 * (s["e_tot"] > 0).mean(), 2)}),
        include_groups=False)
    print(t.to_string())
    print(f"\n  monotone in actual e: {t['actual e'].is_monotonic_increasing}"
          f"   over% spread {t['over %'].iloc[-1]-t['over %'].iloc[0]:+.2f}pp")


def main():
    d = build()
    print(f"{len(d):,} games  {d['date'].min().date()} .. {d['date'].max().date()}")
    print(f"  e_tot mean {d['e_tot'].mean():+.3f}  sd {d['e_tot'].std():.2f}")
    print(f"  e_ats mean {d['e_ats'].mean():+.3f}  sd {d['e_ats'].std():.2f}\n")
    test1(d)
    L, gates = test23(d)
    test4(d, L, gates)
    test6(d)


if __name__ == "__main__":
    main()
