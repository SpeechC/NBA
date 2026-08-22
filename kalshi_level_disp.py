"""Do HIGH-SCORING games/teams get wider Kalshi ladders, and is that widening
RIGHT? The ladder is calibrated on average (family-wise p=0.97); the question
here is whether it is calibrated CONDITIONALLY on scoring level -- an average
can hide offsetting errors: too narrow for high-total games, too wide for low.

TOOL. Each fitted ladder gives (mu, sd). Define the normalised outcome

    z = (actual - mu) / sd_implied

If conditional dispersion pricing is right, sd(z) = 1 in EVERY slice. sd(z) > 1
in a slice = ladders there are too narrow (wings cheap); < 1 = too wide.

FOUR TESTS
  1. LEVEL: does implied sd rise with the level of the total, does realised sd
     rise the same way, and what is each one's elasticity? A Poisson-like game
     implies elasticity ~0.5 on the mean.
  2. CONDITIONAL CALIBRATION by level quintile: sd(z) per quintile of mu, with
     chi-square bands.
  3. TEAM PRIOR SCORING: games between high prior-scoring teams (the state a
     bettor sees) -- implied vs realised sd by tercile of the two teams' mean
     prior-20 points.
  4. PER-TEAM: each team's sd(z) over its games, against the noise floor
     (SE ~ 1/sqrt(2n)); method-of-moments for true between-team spread in
     calibration; correlation of team sd(z) with team scoring level.

2025-26 regular season, 1,157 fitted games. One season -- every result is a
candidate for the 2026-27 monitoring file, not a finding.
"""
import warnings

import numpy as np
import pandas as pd
from scipy.stats import chi2

warnings.filterwarnings("ignore")

import kalshi_calib as KC
import kalshi_rungs as KR


def build():
    m = KC.load()
    u = m[~((m["bid"] <= 0) & (m["ask"] >= 1.0))]
    u = u[u["bucket"] == "regular"]
    rows = []
    for ev, g in u.groupby("event_ticker"):
        f = KC.fit_ladder(g)
        if f:
            rows.append({"event_ticker": ev, "k": g["k"].iloc[0],
                         "mu": f[0], "sd": f[1],
                         "actual": g["actual"].iloc[0],
                         "home": g["home_team"].iloc[0],
                         "away": g["away_team"].iloc[0]})
    G = pd.DataFrame(rows)
    G["e"] = G["actual"] - G["mu"]
    G["z"] = G["e"] / G["sd"]
    F = KR.features()
    return G.merge(F[["k", "p_tot"]], on="k", how="left")


def sdz_ci(n):
    """95% band for sd(z) under correct pricing, from chi-square."""
    lo = np.sqrt(chi2.ppf(0.025, n - 1) / (n - 1))
    hi = np.sqrt(chi2.ppf(0.975, n - 1) / (n - 1))
    return lo, hi


def main():
    G = build()
    print(f"  {len(G):,} fitted regular-season games   overall sd(z) = "
          f"{G['z'].std(ddof=1):.4f}  (1.0 = perfectly priced dispersion)")

    print("\n" + "=" * 96)
    print("1 — DOES DISPERSION SCALE WITH LEVEL, AND DOES THE LADDER KNOW?")
    print("=" * 96)
    lx = np.log(G["mu"])
    A = np.column_stack([np.ones(len(G)), lx])
    b_imp, *_ = np.linalg.lstsq(A, np.log(G["sd"]), rcond=None)
    r = np.log(G["sd"]) - A @ b_imp
    se = np.sqrt(np.diag(np.linalg.pinv(A.T @ A)) * (r @ r) / (len(G) - 2))
    print(f"  implied:  log(sd) ~ log(mu)   elasticity {b_imp[1]:+.3f} "
          f"(se {se[1]:.3f})")
    # realised elasticity via log |e| (E|e| proportional to sd for normal)
    y = np.log(G["e"].abs().clip(lower=0.5))
    b_re, *_ = np.linalg.lstsq(A, y, rcond=None)
    r2 = y - A @ b_re
    se2 = np.sqrt(np.diag(np.linalg.pinv(A.T @ A)) * (r2 @ r2) / (len(G) - 2))
    print(f"  realised: log|e| ~ log(mu)    elasticity {b_re[1]:+.3f} "
          f"(se {se2[1]:.3f})")
    print(f"  sqrt-scaling benchmark: +0.500")

    print("\n" + "=" * 96)
    print("2 — CONDITIONAL CALIBRATION BY LEVEL OF THE IMPLIED TOTAL")
    print("=" * 96)
    G["lq"] = pd.qcut(G["mu"], 5, labels=False) + 1
    print(f"  {'quintile':>9}{'n':>6}{'mean mu':>10}{'implied sd':>12}"
          f"{'realised sd':>13}{'sd(z)':>8}{'95% band':>16}{'flag':>7}")
    for q, g in G.groupby("lq"):
        sz = g["z"].std(ddof=1)
        lo, hi = sdz_ci(len(g))
        flag = "NARROW" if sz > hi else ("WIDE" if sz < lo else "")
        print(f"  {q:>9}{len(g):>6}{g['mu'].mean():>10.1f}{g['sd'].mean():>12.2f}"
              f"{g['e'].std(ddof=1):>13.2f}{sz:>8.3f}"
              f"{f'[{lo:.3f},{hi:.3f}]':>16}{flag:>7}")
    print("  sd(z) > band = ladder too NARROW there; < band = too WIDE")

    print("\n" + "=" * 96)
    print("3 — BY THE TEAMS' PRIOR SCORING (the state a bettor sees pregame)")
    print("=" * 96)
    s = G.dropna(subset=["p_tot"]).copy()
    s["tq"] = pd.qcut(s["p_tot"], 3, labels=["low-scoring", "mid",
                                             "HIGH-scoring"])
    print(f"  {'tercile':>14}{'n':>6}{'prior pts':>11}{'implied sd':>12}"
          f"{'realised sd':>13}{'sd(z)':>8}{'95% band':>16}")
    for q, g in s.groupby("tq", observed=True):
        sz = g["z"].std(ddof=1)
        lo, hi = sdz_ci(len(g))
        print(f"  {str(q):>14}{len(g):>6}{g['p_tot'].mean():>11.1f}"
              f"{g['sd'].mean():>12.2f}{g['e'].std(ddof=1):>13.2f}{sz:>8.3f}"
              f"{f'[{lo:.3f},{hi:.3f}]':>16}")

    print("\n" + "=" * 96)
    print("4 — PER-TEAM CALIBRATION (each game counts for both teams)")
    print("=" * 96)
    long = pd.concat([
        G[["home", "z", "mu"]].rename(columns={"home": "team"}),
        G[["away", "z", "mu"]].rename(columns={"away": "team"})])
    per = long.groupby("team").agg(n=("z", "size"), sdz=("z", lambda v:
                                                         v.std(ddof=1)),
                                   mu=("mu", "mean"))
    per["se"] = 1.0 / np.sqrt(2 * per["n"])
    vobs = per["sdz"].var(ddof=1)
    vnoise = (per["se"] ** 2).mean()
    tau2 = vobs - vnoise
    print(f"  teams {len(per)}   games per team ~{per['n'].mean():.0f}")
    print(f"  observed var of team sd(z) {vobs:.5f}   noise var {vnoise:.5f}")
    print(f"  TRUE between-team var {tau2:+.5f} -> true SD "
          f"{np.sqrt(max(tau2, 0)):.4f}")
    print(f"  share of teams outside their own 95% band: "
          f"{(per['sdz'] > 1 + 1.96*per['se']).sum()} narrow, "
          f"{(per['sdz'] < 1 - 1.96*per['se']).sum()} wide  "
          f"(expect ~{0.05*len(per):.1f} total by chance)")
    r_ = np.corrcoef(per["mu"], per["sdz"])[0, 1]
    t_ = r_ * np.sqrt(len(per) - 2) / np.sqrt(1 - r_ ** 2)
    print(f"  corr(team implied-total level, team sd(z)) = {r_:+.4f} "
          f"(t={t_:+.2f})")
    print(f"\n  extremes (descriptive only):")
    p2 = per.sort_values("sdz")
    for lab, rows_ in (("most OVER-priced dispersion (sd(z) low)",
                        p2.head(3)), ("most UNDER-priced (sd(z) high)",
                                      p2.tail(3))):
        print(f"    {lab}")
        for t, row in rows_.iterrows():
            print(f"      {t:5} sd(z) {row['sdz']:.3f}  (n={int(row['n'])}, "
                  f"se {row['se']:.3f})")


if __name__ == "__main__":
    main()
