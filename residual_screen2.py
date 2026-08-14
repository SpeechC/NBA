"""Residual-predictability screen, rebuilt on TRUE per-game inputs.

The original residual_screen.py drew its shooting features from the master's
TEAM_-prefixed columns, which the audit showed are pre-smoothed level series.
A rolling SD of an already-smoothed series is severely attenuated, so the
"no persistent process volatility" conclusion was not a fair test.

Everything here is per-game and unsmoothed:

  master, 100% coverage, spans the full split
      PACE, OEFF, DEFF          (OEFF is identical to ADV_OFF_RTG)
      bare box vars 3PA, FTA, TOV, ORB, ...
  advanced ADV_ box, 100% both sides of the split
      ADV_EFG, ADV_TS, ADV_FTA_RATE, ADV_3PA_RATE, ADV_TOV_PER100,
      ADV_OREB_PCT, ADV_PF_PER100_OPP_POSS
  advanced PBP, develop + 2024-25 ONLY
      PBP_PTS_POSS_SD      within-game SD of points per possession
      PBP_POS_DUR_SD       within-game SD of possession length
      PBP_ZERO_PTS_SHARE   share of possessions scoring nothing
      PBP_3PLUS_PTS_SHARE  share of possessions scoring 3+

Two questions, in order:

  PART 1  Does true process volatility persist at all? This is the finding the
          smoothing made unreliable. Tested three ways: season-to-season,
          within-season split-half, and against the persistence of the MEANS
          measured identically, so the comparison is like for like.

  PART 2  The three-target screen, unchanged in design from the original so the
          numbers are comparable:
              Y1 = e         signed residual   benchmark e_hat = 0
              Y2 = |e|       magnitude         benchmark training mean |e|
              Y3 = 1(e > 0)  direction         benchmark p = 0.5
          Walk-forward by season, expanding window, no tuning in the test year.

THE POINT IS NOT R^2. Against an 18-point residual SD a 1% R^2 is a useless
forecast and could still be a business if the extreme buckets separate by
1.5-2 points, so the quintile table is the primary output.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.preprocessing import StandardScaler

ROLL = 15
BE = 110 / 210
ADVF = "/mnt/c/NBA2/advanced_stats/game_advanced_stats.csv"

RAW = ["PACE", "OEFF", "DEFF", "POSS", "3PA", "FTA", "TO", "OR", "PF"]
ADVV = ["ADV_EFG", "ADV_TS", "ADV_FTA_RATE", "ADV_3PA_RATE",
        "ADV_TOV_PER100", "ADV_OREB_PCT", "ADV_PF_PER100_OPP_POSS"]
PBPV = ["PBP_PTS_POSS_SD", "PBP_POS_DUR_SD", "PBP_ZERO_PTS_SHARE",
        "PBP_3PLUS_PTS_SHARE"]


def build():
    from prepare_data import CSV, season_label
    raw = pd.read_csv(CSV, low_memory=False)
    raw["lbl"] = season_label(raw).astype(str)
    d = raw[raw["lbl"].str.contains("Regular Season", na=False)].copy()
    n = lambda c: pd.to_numeric(d[c], errors="coerce")
    d["date"] = pd.to_datetime(d["DATE"], errors="coerce")
    d["yr"] = d["lbl"].str.extract(r"(\d{4})")[0].astype(int)
    d["gid"] = d["GAME-ID"].astype(str).str.strip()
    d["total"], d["spread"] = n("CLOSING TOTAL_H"), n("CLOSING SPREAD_H")
    d["actual"] = d["PTS_H"] + d["PTS_R"]
    d = d.dropna(subset=["total", "spread", "actual", "date"])
    d = d[d["total"].between(150, 300)].copy()
    d["e"] = d["actual"] - d["total"]
    d["abs_spread"] = d["spread"].abs()

    adv = pd.read_csv(ADVF, low_memory=False)
    adv["gid"] = adv["GAME-ID"].astype(str).str.strip()
    keep = ["gid"] + [f"{v}_{s}" for v in ADVV + PBPV for s in ("H", "R")]
    adv = adv[[c for c in keep if c in adv.columns]]
    clash = (set(adv.columns) & set(d.columns)) - {"gid"}
    assert not clash, f"column collision: {clash}"
    n0 = len(d)
    d = d.merge(adv, on="gid", how="left")
    assert len(d) == n0, "merge changed row count"

    # per-team panel of TRUE per-game process values
    rows = []
    for s in ("H", "R"):
        r = {"gid": d["gid"], "yr": d["yr"], "date": d["date"],
             "team": d[f"TEAM_{s}"], "side": s,
             "pts": pd.to_numeric(d[f"PTS_{s}"], errors="coerce")}
        for v in RAW:
            r[v] = pd.to_numeric(d[f"{v}_{s}"], errors="coerce")
        for v in ADVV + PBPV:
            if f"{v}_{s}" in d:
                r[v] = d[f"{v}_{s}"]
        rows.append(pd.DataFrame(r))
    P = pd.concat(rows).sort_values("date")
    return d, P


VOLV = ["OEFF", "PACE", "pts"]


def part1(P):
    print("=" * 96)
    print("PART 1 — DOES TRUE PROCESS VOLATILITY PERSIST?")
    print("=" * 96)
    print("  Measured on unsmoothed per-game values. The MEANS are measured the")
    print("  same way so the comparison is like for like.\n")

    ts = P.groupby(["yr", "team"])[VOLV].agg(["mean", "std", "size"])
    ts = ts[ts[(VOLV[0], "size")] >= 40]

    print("  (a) SEASON TO SEASON  corr(stat in season t, same stat in t+1)")
    print(f"      {'variable':10} {'MEAN persists':>16} {'SD persists':>16}   n pairs")
    for v in VOLV:
        t = ts[v].reset_index()
        t["nxt"] = t["yr"] + 1
        j = t.merge(t, left_on=["team", "nxt"], right_on=["team", "yr"],
                    suffixes=("_t", "_n"))
        rm = np.corrcoef(j["mean_t"], j["mean_n"])[0, 1]
        rs = np.corrcoef(j["std_t"], j["std_n"])[0, 1]
        tm = rm * np.sqrt(len(j) - 2) / np.sqrt(1 - rm ** 2)
        tsd = rs * np.sqrt(len(j) - 2) / np.sqrt(1 - rs ** 2)
        print(f"      {v:10} {rm:+.4f} (t={tm:+5.2f}) {rs:+.4f} (t={tsd:+5.2f})   "
              f"{len(j)}")

    print("\n  (b) WITHIN SEASON SPLIT-HALF  odd-numbered games vs even-numbered")
    print("      Removes any season-level confound. Corrected for the fact that")
    print("      each half estimates the SD from only ~41 games.")
    Q = P.sort_values("date").copy()
    Q["gnum"] = Q.groupby(["yr", "team"]).cumcount()
    print(f"      {'variable':10} {'MEAN':>18} {'SD':>18}   n team-seasons")
    for v in VOLV:
        a = Q[Q["gnum"] % 2 == 0].groupby(["yr", "team"])[v].agg(["mean", "std",
                                                                 "size"])
        b = Q[Q["gnum"] % 2 == 1].groupby(["yr", "team"])[v].agg(["mean", "std",
                                                                 "size"])
        j = a.join(b, lsuffix="_a", rsuffix="_b").dropna()
        j = j[(j["size_a"] >= 20) & (j["size_b"] >= 20)]
        rm = np.corrcoef(j["mean_a"], j["mean_b"])[0, 1]
        rs = np.corrcoef(j["std_a"], j["std_b"])[0, 1]
        tm = rm * np.sqrt(len(j) - 2) / np.sqrt(1 - rm ** 2)
        tsd = rs * np.sqrt(len(j) - 2) / np.sqrt(1 - rs ** 2)
        print(f"      {v:10} {rm:+.4f} (t={tm:+5.2f}) {rs:+.4f} (t={tsd:+5.2f})"
              f"   {len(j)}")

    print("\n  (c) WITHIN-GAME dispersion, which needs no estimation window at")
    print("      all: PBP_PTS_POSS_SD is measured from ~100 possessions in a")
    print("      single game, so it is far less noisy than any rolling SD.")
    if "PBP_PTS_POSS_SD" in P.columns:
        s = P.dropna(subset=["PBP_PTS_POSS_SD"])
        g = s.groupby(["yr", "team"])["PBP_PTS_POSS_SD"].agg(["mean", "size"])
        g = g[g["size"] >= 40].reset_index()
        g["nxt"] = g["yr"] + 1
        j = g.merge(g, left_on=["team", "nxt"], right_on=["team", "yr"],
                    suffixes=("_t", "_n"))
        r = np.corrcoef(j["mean_t"], j["mean_n"])[0, 1]
        t = r * np.sqrt(len(j) - 2) / np.sqrt(1 - r ** 2)
        print(f"      team mean of within-game PPP dispersion, season t -> t+1:"
              f"  {r:+.4f}  t={t:+.2f}  n={len(j)}")
        sh = s.groupby(["yr", "team"])["PBP_PTS_POSS_SD"].std().median()
        print(f"      median within-team-season SD of that measure: {sh:.4f}")


def features(d, P, use_pbp):
    vs = RAW + ADVV + (PBPV if use_pbp else [])
    vs = [v for v in vs if v in P.columns]
    g = P.groupby(["yr", "team"])
    out = P[["gid", "side"]].copy()
    for c in vs:
        out[f"m_{c}"] = g[c].transform(
            lambda s: s.shift(1).rolling(ROLL, min_periods=8).mean())
        out[f"v_{c}"] = g[c].transform(
            lambda s: s.shift(1).rolling(ROLL, min_periods=8).std(ddof=1))
    h = out[out["side"] == "H"].drop(columns="side").add_suffix("_h").rename(
        columns={"gid_h": "gid"})
    a = out[out["side"] == "R"].drop(columns="side").add_suffix("_a").rename(
        columns={"gid_a": "gid"})
    clash = (set(h.columns) | set(a.columns)) & set(d.columns) - {"gid"}
    assert not clash, f"column collision: {clash}"
    z = d.merge(h, on="gid").merge(a, on="gid")
    feats = ["total", "spread", "abs_spread"]
    for c in vs:
        z[f"M_{c}"] = z[f"m_{c}_h"] + z[f"m_{c}_a"]
        z[f"V_{c}"] = z[f"v_{c}_h"] + z[f"v_{c}_a"]
        feats += [f"M_{c}", f"V_{c}"]
    z["pace_diff"] = (z["m_PACE_h"] - z["m_PACE_a"]).abs()
    z["pace_prod"] = z["m_PACE_h"] * z["m_PACE_a"] / 100.0
    feats += ["pace_diff", "pace_prod"]
    return z, feats


def walk(d, feats, target, kind, maxyr=None):
    if maxyr is not None:
        d = d[d["yr"] <= maxyr]
    yrs = sorted(d["yr"].unique())
    out = []
    for i in range(2, len(yrs)):
        tr, te = d[d["yr"].isin(yrs[:i])], d[d["yr"] == yrs[i]].copy()
        if len(te) < 100:
            continue
        sc = StandardScaler().fit(tr[feats])
        X, Xt = sc.transform(tr[feats]), sc.transform(te[feats])
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
    print("\n" + "-" * 92)
    print(lab)
    print("-" * 92)
    y, p, b = P[target].values, P["pred"].values, P["bench"].values
    if kind == "ridge":
        r = np.corrcoef(p, y)[0, 1]
        t = r * np.sqrt(len(y) - 2) / np.sqrt(1 - r * r)
        r2 = 1 - ((y - p) ** 2).sum() / ((y - b) ** 2).sum()
        print(f"  n={len(y):,}  corr {r:+.4f}  t={t:+.2f}   "
              f"OOS R^2 vs benchmark {100*r2:+.3f}%   pred sd {p.std():.3f} "
              f"(actual sd {y.std():.2f})")
    else:
        ll = -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))
        llb = np.log(2)
        print(f"  n={len(y):,}  log-loss {ll:.5f} vs benchmark {llb:.5f}  "
              f"gain {llb-ll:+.5f}   pred sd {p.std():.4f}")
    P = P.copy()
    P["q"] = pd.qcut(P["pred"], 5, labels=[1, 2, 3, 4, 5], duplicates="drop")
    rows = []
    for q, s in P.groupby("q", observed=True):
        ov = (s["e"] > 0).mean()
        rows.append({"Q": q, "n": len(s), "pred": round(s["pred"].mean(), 3),
                     "actual e": round(s["e"].mean(), 3),
                     "|e|": round(s["e"].abs().mean(), 2),
                     "over %": round(100 * ov, 2),
                     "1.96se": round(100 * 1.96 * np.sqrt(ov * (1 - ov) / len(s)), 2)})
    T = pd.DataFrame(rows)
    print(T.to_string(index=False))
    print(f"  actual-e Q5-Q1 {T['actual e'].iloc[-1]-T['actual e'].iloc[0]:+.3f} pts"
          f"   |e| Q5-Q1 {T['|e|'].iloc[-1]-T['|e|'].iloc[0]:+.2f}"
          f"   over% Q5-Q1 {T['over %'].iloc[-1]-T['over %'].iloc[0]:+.2f}pp"
          f"   (need {100*BE-50:+.2f}pp from 50 to clear the vig)")


def main():
    d, P = build()
    print(f"{len(d):,} regular-season games, seasons {sorted(d['yr'].unique())}")
    print(f"  e: mean {d['e'].mean():+.3f}  sd {d['e'].std():.2f}  "
          f"MAE {d['e'].abs().mean():.2f}\n")
    part1(P)

    for use_pbp, maxyr, tag in ((False, None, "FULL SPLIT — master + ADV box, "
                                 "true per-game, validates through 2025-26"),
                                (True, 2024, "PBP BLOCK — adds within-game "
                                 "dispersion, validates on 2024-25 only")):
        z, feats = features(d, P, use_pbp)
        z = z.dropna(subset=feats + ["e"])
        if maxyr is not None:
            z = z[z["yr"] <= maxyr]
        print("\n\n" + "=" * 96)
        print(f"PART 2 — {tag}")
        print("=" * 96)
        print(f"  {len(z):,} games with complete lagged states, "
              f"{len(feats)} features, seasons {sorted(z['yr'].unique())}")
        z["abs_e"] = z["e"].abs()
        z["dir"] = (z["e"] > 0).astype(int)
        report(walk(z, feats, "e", "ridge"), "e", "ridge",
               "Y1 — SIGNED RESIDUAL   (benchmark: predict 0)")
        report(walk(z, feats, "abs_e", "ridge"), "abs_e", "ridge",
               "Y2 — MAGNITUDE |e|     (benchmark: training mean |e|)")
        report(walk(z, feats, "dir", "logit"), "dir", "logit",
               "Y3 — DIRECTION 1(e>0)  (benchmark: p = 0.5)")


if __name__ == "__main__":
    main()
