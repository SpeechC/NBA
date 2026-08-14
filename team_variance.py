"""Team-level DISPERSION as a second characteristic, and whether it is priced.

A team is (mu_j, sigma_j), not just mu_j. Two visitors with the same +4 mean are
not equally actionable if one has sigma 5 and the other 15.

PART A -- GATE. Does team-specific dispersion persist?
    sigma_j = SD of road (H2-H1) around the team's own mean
    split 2017-2020 vs 2021-2023, correlate; variance components with a
    permutation null. If dispersion does not persist it is sampling noise in a
    noisy statistic and everything downstream is meaningless.

    Note the sampling problem is worse than for means: the SE of a sample SD is
    about sigma/sqrt(2n), so even ~120 games per half gives ~1.1 points of noise
    on an estimate near 17. Teams must differ by a lot to be detectable.

PART B -- only if A passes. Is the standardised signal Z_j = |mu_j|/sigma_j a
    better predictor of DK allocation error than |mu_j| was? Both frozen pre-2023.
    Also P(H2 > H1) = Phi(mu/sigma), which converts averages into probabilities.

PART C -- independent, and where dispersion has direct economic meaning.
    Margin variance is what a moneyline prices. Using pre-2023 team ATS
    dispersion:
      C1 does DK already shift its ML away from the spread-rule for high-variance
         teams?   logit(P_DK) ~ f(spread) + variance_state
      C2 does variance still predict the OUTCOME after DK's own probability?
         outcome ~ P_DK + variance_state
    A zero coefficient in C2 means priced. A non-zero one is a distributional
    transformation error -- the closing spread can be perfectly efficient about
    E[Y] while the derived ML is wrong about P(Y>0).
"""
import warnings

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")
RNG = np.random.default_rng(0)

EARLY = [2017, 2018, 2020]
LATE = [2021, 2022, 2023]


def road_panel():
    from bench_oos import build as bench_build
    _, L = bench_build()
    return L[L["road"]].copy()


def part_a(R):
    print("=" * 96)
    print("PART A (GATE) — does team-level dispersion persist?")
    print("=" * 96)
    rows = []
    for t, s in R.groupby("team"):
        a = s[s["yr"].isin(EARLY)]["h21"]
        b = s[s["yr"].isin(LATE)]["h21"]
        if len(a) < 60 or len(b) < 60:
            continue
        rows.append({"team": t, "n1": len(a), "n2": len(b),
                     "sd1": a.std(ddof=1), "sd2": b.std(ddof=1),
                     "mu1": a.mean(), "mu2": b.mean()})
    t = pd.DataFrame(rows)
    r_sd = np.corrcoef(t["sd1"], t["sd2"])[0, 1]
    r_mu = np.corrcoef(t["mu1"], t["mu2"])[0, 1]
    tt = r_sd * np.sqrt(len(t) - 2) / np.sqrt(1 - r_sd ** 2)
    print(f"  {len(t)} teams, {t['n1'].mean():.0f} / {t['n2'].mean():.0f} "
          f"road games per half")
    print(f"  corr(sigma_early, sigma_late) = {r_sd:+.3f}  t={tt:+.2f}")
    print(f"  corr(mu_early,    mu_late)    = {r_mu:+.3f}   <- the mean, for "
          f"reference")
    print(f"  sigma range: {t['sd1'].min():.1f} .. {t['sd1'].max():.1f} "
          f"(early)   mean {t['sd1'].mean():.1f}")

    # is the observed spread in sigma beyond sampling noise?
    obs = t["sd1"].std(ddof=1)
    null = []
    for _ in range(2000):
        p = R.copy()
        p["team"] = RNG.permutation(p["team"].values)
        sds = [s[s["yr"].isin(EARLY)]["h21"].std(ddof=1)
               for _, s in p.groupby("team")
               if len(s[s["yr"].isin(EARLY)]) >= 60]
        if len(sds) > 5:
            null.append(np.std(sds, ddof=1))
    null = np.array(null)
    print(f"  sd across teams of sigma: observed {obs:.3f}   "
          f"null {null.mean():.3f} ± {null.std():.3f}   "
          f"percentile {100*np.mean(null < obs):.1f}")
    passed = (r_sd > 0.3 and tt > 2) or np.mean(null < obs) > 0.95
    print(f"\n  GATE: {'PASS' if passed else 'FAIL'}")
    return t, passed


def part_c():
    print("\n" + "=" * 96)
    print("PART C — team margin dispersion and the spread->moneyline map")
    print("=" * 96)
    from prepare_data import CSV, season_label
    raw = pd.read_csv(CSV, low_memory=False)
    raw["lbl"] = season_label(raw).astype(str)
    d = raw[raw["lbl"].str.contains("Regular Season", na=False)].copy()
    n = lambda c: pd.to_numeric(d[c], errors="coerce")
    d["spread"] = n("CLOSING SPREAD_H")
    d["mlh"], d["mla"] = n("MONEYLINE_H"), n("MONEYLINE_R")
    d["margin"] = d["PTS_H"] - d["PTS_R"]
    d["yr"] = d["lbl"].str.extract(r"(\d{4})")[0].astype(int)
    d = d.dropna(subset=["spread", "mlh", "mla", "margin"])
    d["ats"] = d["margin"] + d["spread"]
    ph = np.where(d["mlh"] < 0, -d["mlh"] / (-d["mlh"] + 100),
                  100 / (d["mlh"] + 100))
    pa = np.where(d["mla"] < 0, -d["mla"] / (-d["mla"] + 100),
                  100 / (d["mla"] + 100))
    d["p_home"] = ph / (ph + pa)
    d = d[(d["p_home"] > 0.03) & (d["p_home"] < 0.97)].copy()
    d["home_win"] = (d["margin"] > 0).astype(float)
    d["logit"] = np.log(d["p_home"] / (1 - d["p_home"]))

    # team ATS dispersion from EARLY seasons only
    rows = []
    for side in ("H", "R"):
        rows.append(pd.DataFrame({"yr": d["yr"], "team": d[f"TEAM_{side}"],
                                  "ats": d["ats"] * (1 if side == "H" else -1)}))
    A = pd.concat(rows)
    sig = (A[A["yr"].isin(EARLY)].groupby("team")["ats"]
           .agg(["std", "size"]).reset_index())
    sig = sig[sig["size"] >= 100].rename(columns={"std": "sig"})
    print(f"  team ATS sigma from {EARLY}: {len(sig)} teams, "
          f"range {sig['sig'].min():.1f} .. {sig['sig'].max():.1f}")
    # persistence of ATS dispersion
    sig2 = (A[A["yr"].isin(LATE)].groupby("team")["ats"].std().rename("sig2")
            .reset_index())
    m = sig.merge(sig2, on="team")
    r = np.corrcoef(m["sig"], m["sig2"])[0, 1]
    print(f"  corr(ATS sigma early, late) = {r:+.3f}   "
          f"<- does margin dispersion persist?")

    te = d[d["yr"].isin(LATE)].copy()
    te = te.merge(sig[["team", "sig"]].rename(
        columns={"team": "TEAM_H", "sig": "sig_h"}), on="TEAM_H", how="inner")
    te = te.merge(sig[["team", "sig"]].rename(
        columns={"team": "TEAM_R", "sig": "sig_a"}), on="TEAM_R", how="inner")
    te["vstate"] = (te["sig_h"] + te["sig_a"]) / 2
    te["vstate"] = te["vstate"] - te["vstate"].mean()
    print(f"  test window {LATE}: {len(te):,} games")

    X = np.column_stack([np.ones(len(te)), -te["spread"], te["vstate"]])
    beta, *_ = np.linalg.lstsq(X, te["logit"].values, rcond=None)
    res = te["logit"].values - X @ beta
    s2 = (res ** 2).sum() / (len(te) - 3)
    se = np.sqrt(np.diag(np.linalg.pinv(X.T @ X)) * s2)
    print(f"\n  C1  logit(P_DK) ~ spread + variance_state")
    print(f"      spread {beta[1]:+.5f} (t={beta[1]/se[1]:+.1f})   "
          f"variance {beta[2]:+.5f} (t={beta[2]/se[2]:+.2f})")
    print("      does DK already shift its ML for high-variance teams?")

    from sklearn.linear_model import LogisticRegression
    y = te["home_win"].values
    X1 = te[["logit"]].values
    X2 = np.column_stack([te["logit"].values, te["vstate"].values])
    m1 = LogisticRegression(max_iter=1000).fit(X1, y)
    m2 = LogisticRegression(max_iter=1000).fit(X2, y)
    ll = lambda m, X: -np.mean(y * np.log(m.predict_proba(X)[:, 1])
                               + (1 - y) * np.log(1 - m.predict_proba(X)[:, 1]))
    print(f"\n  C2  outcome ~ P_DK + variance_state")
    print(f"      coefficient on variance {m2.coef_[0][1]:+.4f}")
    print(f"      log-loss  P_DK only {ll(m1, X1):.5f}   "
          f"+variance {ll(m2, X2):.5f}   gain {ll(m1,X1)-ll(m2,X2):+.5f}")
    te["vq"] = pd.qcut(te["vstate"], 4, labels=[1, 2, 3, 4])
    print("\n      calibration by variance quartile:")
    for q, s in te.groupby("vq", observed=True):
        print(f"        Q{q} sigma {s['vstate'].mean()+ (sig['sig'].mean()):.1f}"
              f"  n={len(s):4d}  implied {100*s['p_home'].mean():5.2f}%  "
              f"actual {100*s['home_win'].mean():5.2f}%  "
              f"gap {100*(s['home_win'].mean()-s['p_home'].mean()):+5.2f}pp")


def main():
    R = road_panel()
    t, passed = part_a(R)
    if not passed:
        print("\n  Part B is gated on A and is not run.")
    part_c()


if __name__ == "__main__":
    main()
