"""Model the TRUE total-points distribution and test where the Kalshi
Gaussian ladder misprices it.

THE ONLY OPEN FLANK IS SHAPE. The mean cannot be beaten (BETTING_TOTALS.md:
every model variant has worse RMSE than the close, incremental t <= 0, except
the frozen CrewShock/final-week signals). The variance is calibrated (overall
ratio 0.990; by level, by team, by matchup component). But the SHAPE is wrong
by construction: the ladder is Gaussian (fit RMSE 0.02 z-units) while the true
total is a MIXTURE -- regulation is Gaussian (VARIANCE.md: excess kurtosis
+0.02 on non-OT games), and overtime ADDS 10-25 points to ~5-6% of games,
one-sidedly. Full-total skew +0.256.

MODEL. With OT probability p and OT-points distribution J (both estimated from
PRIOR seasons only, 2017-18..2024-25 -- master columns OT1..OT5 both sides):

    Total = R + J*1[OT],   R ~ N(m, s)

Per game, (m, s) are chosen so the mixture MATCHES the ladder's own fitted
moments -- we take the market's mean and variance as given (they are right)
and change only the shape:

    m  = mu_hat - p*E[J]
    s^2 = sd_hat^2 - p*(1-p)*E[J]^2 - p*Var[J]

    S_model(K) = (1-p)*Phibar((K-m)/s) + p * mean_j Phibar((K-m-j)/s)

PREDICTED MISPRICING per rung:  pred(K) = S_model(K) - S_gauss(K)
(positive = the Gaussian ladder UNDERPRICES the over there). The theoretical
pattern: negative at the money, positive on BOTH wings.

TEST (one degree of freedom, game-clustered):

    observed dev (win - mid)  ~  pred

slope ~ 1 -> the mixture is the truth and the ladder has the wrong shape;
slope ~ 0 -> the ladder's Gaussian is fine. This projection test is far more
powerful than the 11 unconstrained per-rung tests that individually showed
nothing.
"""
import warnings

import numpy as np
import pandas as pd
from scipy.stats import norm

warnings.filterwarnings("ignore")

import kalshi_calib as KC
import refs


def ot_history():
    """OT probability and OT-points distribution from PRIOR seasons only."""
    m = refs.build()
    n = lambda c: pd.to_numeric(m[c], errors="coerce")
    J = sum(n(f"OT{i}_{s}").fillna(0.0) for i in range(1, 6)
            for s in ("H", "R"))
    d = pd.DataFrame({"yr": m["yr"], "J": J, "actual": m["actual"],
                      "total": m["total"]}).dropna(subset=["total"])
    prior = d[d["yr"] <= 2024]
    ot = prior[prior["J"] > 0]
    p = len(ot) / len(prior)
    print(f"  prior seasons 2017-18..2024-25: {len(prior):,} games   "
          f"OT rate {100*p:.2f}%")
    print(f"  OT points added: mean {ot['J'].mean():.2f}  sd {ot['J'].std():.2f}"
          f"  median {ot['J'].median():.0f}  max {ot['J'].max():.0f}")
    # shape check: does removing OT points restore normality?
    from scipy.stats import skew, kurtosis
    e_full = prior["actual"] - prior["total"]
    e_reg = (prior["actual"] - prior["J"]) - prior["total"]
    print(f"  residual skew/kurtosis: full {skew(e_full):+.3f}/"
          f"{kurtosis(e_full):+.3f}   regulation-only {skew(e_reg):+.3f}/"
          f"{kurtosis(e_reg):+.3f}")
    return p, ot["J"].values


def main():
    print("=" * 96)
    print("1 — THE OVERTIME MIXTURE, from prior seasons")
    print("=" * 96)
    p, Js = ot_history()
    EJ, VJ = Js.mean(), Js.var(ddof=1)

    m = KC.load()
    u = m[~((m["bid"] <= 0) & (m["ask"] >= 1.0))]
    u = u[u["bucket"] == "regular"].copy()
    fits = {}
    for ev, g in u.groupby("event_ticker"):
        f = KC.fit_ladder(g)
        if f:
            fits[ev] = (f[0], f[1])
    u = u[u["event_ticker"].isin(fits)]
    u["mu"] = u["event_ticker"].map(lambda e: fits[e][0])
    u["sdh"] = u["event_ticker"].map(lambda e: fits[e][1])

    # per-game mixture with the SAME mean and variance as the ladder
    u["m0"] = u["mu"] - p * EJ
    s2 = u["sdh"] ** 2 - p * (1 - p) * EJ ** 2 - p * VJ
    u["s0"] = np.sqrt(s2.clip(lower=1.0))
    K = u["floor_strike"].values
    gauss = 1.0 - norm.cdf((K - u["mu"]) / u["sdh"])
    reg = 1.0 - norm.cdf((K - u["m0"]) / u["s0"])
    otp = np.zeros(len(u))
    for j in Js:                       # empirical J, exact mixture
        otp += 1.0 - norm.cdf((K - u["m0"] - j) / u["s0"])
    otp /= len(Js)
    u["S_model"] = (1 - p) * reg + p * otp
    u["pred"] = u["S_model"] - gauss
    u["dev"] = u["win"] - u["mid"]
    u["z"] = (K - u["mu"]) / u["sdh"]

    print("\n" + "=" * 96)
    print("2 — PREDICTED MISPRICING OF THE GAUSSIAN LADDER, by z position")
    print("=" * 96)
    u["zb"] = pd.cut(u["z"], [-2, -1.5, -1, -0.5, 0, 0.5, 1, 1.5, 2])
    t = u.groupby("zb", observed=True).agg(
        n=("dev", "size"), pred=("pred", "mean"), obs=("dev", "mean"))
    print(f"  {'z bin':>16}{'n':>7}{'PREDICTED pp':>14}{'OBSERVED pp':>13}")
    for b, r in t.iterrows():
        print(f"  {str(b):>16}{int(r['n']):>7}{100*r['pred']:>+14.3f}"
              f"{100*r['obs']:>+13.3f}")
    print("  [prediction: negative near the money, positive on both wings]")

    print("\n" + "=" * 96)
    print("3 — THE ONE-DF PROJECTION TEST  (game-clustered)")
    print("=" * 96)
    x, y = u["pred"].values, u["dev"].values
    A = np.column_stack([np.ones(len(x)), x])
    b, *_ = np.linalg.lstsq(A, y, rcond=None)
    r = y - A @ b
    XtXi = np.linalg.pinv(A.T @ A)
    codes, _ = pd.factorize(u["event_ticker"])
    meat = np.zeros((2, 2))
    for c in np.unique(codes):
        s = A[codes == c].T @ r[codes == c]
        meat += np.outer(s, s)
    V = XtXi @ meat @ XtXi
    se = np.sqrt(np.diag(V))
    print(f"  observed dev ~ predicted mispricing")
    print(f"  slope {b[1]:+.3f}  (clustered se {se[1]:.3f}, "
          f"t={b[1]/se[1]:+.2f})")
    print(f"  slope 1 = mixture is truth, ladder shape wrong; 0 = ladder fine")
    print(f"  t vs 1.0: {(b[1]-1)/se[1]:+.2f}")

    # log-loss: does the mixture beat the mid out of sample (no fitting here)?
    eps = 1e-6
    ll_mid = -np.mean(u["win"]*np.log(u["mid"].clip(eps, 1-eps))
                      + (1-u["win"])*np.log((1-u["mid"]).clip(eps, 1-eps)))
    ll_mod = -np.mean(u["win"]*np.log(u["S_model"].clip(eps, 1-eps))
                      + (1-u["win"])*np.log((1-u["S_model"]).clip(eps, 1-eps)))
    print(f"\n  log-loss: ladder mid {ll_mid:.5f}   mixture {ll_mod:.5f}   "
          f"improvement {ll_mid-ll_mod:+.6f}")

    print("\n" + "=" * 96)
    print("4 — ECONOMICS, if the mixture is right")
    print("=" * 96)
    u["edge"] = u["pred"].abs()
    for lab, msk in (("at the money  |z|<0.25", u["z"].abs() < 0.25),
                     ("wings         |z|>1.0", u["z"].abs() > 1.0)):
        s = u[msk]
        print(f"  {lab:26} n={len(s):5,}  mean |edge| "
              f"{100*s['edge'].mean():.2f}pp   maker hurdle -0.06pp   "
              f"taker ~2.2-2.8pp")
    e_atm = u[u["z"].abs() < 0.25]["edge"].mean()
    n_req = 7.84 * 0.25 / max(e_atm, 1e-9) ** 2
    print(f"\n  establishment at the ATM edge as maker: "
          f"{n_req:,.0f} bets  ({n_req/1230:.1f} seasons betting every game)")


if __name__ == "__main__":
    main()
