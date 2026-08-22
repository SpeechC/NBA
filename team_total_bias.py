"""Are individual TEAMS mispriced on the closing total?

Complement to kalshi_level_disp.py: that showed zero between-team heterogeneity
in DISPERSION calibration. This asks about the MEAN -- does some team's slate
of games carry a systematic signed error e = actual - closing total?

Three layers, in decreasing power:

  1. 8-SEASON PANEL (each team ~630 games, SE ~0.72 pts):
     per-team mean e, method-of-moments true between-team variance, and a
     FAMILY-WISE max-|t| permutation (game-level e reshuffled within season,
     team fixtures held fixed -- each game feeds two teams, and the reshuffle
     preserves exactly that overlap structure).
  2. PERSISTENCE: a real team bias must persist. Split the panel 2017-2021 vs
     2022-2025 and correlate the two halves' team means.
  3. KALSHI 2025-26: per-team mean z from the fitted ladders, same MoM.
     One season, SE ~0.115 in z units (~2.1 points) -- reported for
     completeness, decidable by the panel, not by this.

The premise deserves scepticism stated up front: a per-team mean error is the
LEAST likely place for an edge -- team identity is the single most attended
input in the market. But 'least likely' has never been tested directly here.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import refs

NPERM = 5000
RNG = np.random.default_rng(20260823)


def main():
    m = refs.build()
    m = m.dropna(subset=["total", "actual"])
    m["e"] = m["actual"] - m["total"]
    long = pd.concat([
        m[["yr", "TEAM_H", "e"]].rename(columns={"TEAM_H": "team"}),
        m[["yr", "TEAM_R", "e"]].rename(columns={"TEAM_R": "team"})],
        ignore_index=True)
    print(f"  {len(m):,} games -> {len(long):,} team-game rows, "
          f"{long['team'].nunique()} teams, seasons "
          f"{m['yr'].min()}-{m['yr'].max()}")

    print("\n" + "=" * 92)
    print("1 — PER-TEAM MEAN CLOSING-TOTAL ERROR, 8 seasons")
    print("=" * 92)
    per = long.groupby("team")["e"].agg(["size", "mean", "std"])
    per["se"] = per["std"] / np.sqrt(per["size"])
    per["t"] = per["mean"] / per["se"]
    vobs = per["mean"].var(ddof=1)
    vnoise = (per["se"] ** 2).mean()
    tau2 = vobs - vnoise
    print(f"  league mean e {long['e'].mean():+.4f}   per-team n ~"
          f"{per['size'].mean():.0f}   per-team SE ~{per['se'].mean():.3f} pts")
    print(f"  observed var of team means {vobs:.4f}   noise var {vnoise:.4f}")
    print(f"  TRUE between-team variance {tau2:+.4f} -> true SD "
          f"{np.sqrt(max(tau2, 0)):.3f} points")
    print(f"\n  most extreme teams (raw, before any correction):")
    srt = per.sort_values("t")
    for lab, rows in (("most UNDER-generating", srt.head(3)),
                      ("most OVER-generating", srt.tail(3))):
        print(f"    {lab}")
        for t, r in rows.iterrows():
            print(f"      {t:15} mean e {r['mean']:+.3f}  (n={int(r['size'])},"
                  f" t={r['t']:+.2f})")
    obs_max = per["t"].abs().max()
    who = per["t"].abs().idxmax()

    # family-wise: reshuffle game e within season, teams keep their fixtures
    g = m[["yr", "TEAM_H", "TEAM_R", "e"]].reset_index(drop=True)
    yrs = g["yr"].values
    blocks = [np.where(yrs == u)[0] for u in np.unique(yrs)]
    teams = sorted(long["team"].unique())
    tidx = {t: i for i, t in enumerate(teams)}
    hi = g["TEAM_H"].map(tidx).values
    ri = g["TEAM_R"].map(tidx).values
    ev = g["e"].values
    cnt = np.bincount(hi, minlength=30) + np.bincount(ri, minlength=30)
    # per-team variance of e barely differs; use each team's own std for t
    sds = per.loc[teams, "std"].values
    ns = per.loc[teams, "size"].values
    null = np.empty(NPERM)
    for j in range(NPERM):
        p = ev.copy()
        for b in blocks:
            p[b] = ev[b][RNG.permutation(len(b))]
        s = np.bincount(hi, weights=p, minlength=30) + \
            np.bincount(ri, weights=p, minlength=30)
        mns = s / cnt
        null[j] = np.max(np.abs(mns) / (sds / np.sqrt(ns)))
    pfw = (1 + np.sum(null >= obs_max)) / (NPERM + 1)
    print(f"\n  observed max|t| = {obs_max:.2f} ({who})   "
          f"null max|t|: mean {null.mean():.2f}  95th {np.percentile(null,95):.2f}")
    print(f"  FAMILY-WISE p = {pfw:.4f}")

    print("\n" + "=" * 92)
    print("2 — PERSISTENCE: 2017-2021 team means vs 2022-2025 team means")
    print("=" * 92)
    a = long[long["yr"] <= 2021].groupby("team")["e"].mean()
    b = long[long["yr"] >= 2022].groupby("team")["e"].mean()
    j = pd.concat([a, b], axis=1, keys=["h1", "h2"]).dropna()
    r = np.corrcoef(j["h1"], j["h2"])[0, 1]
    t = r * np.sqrt(len(j) - 2) / np.sqrt(1 - r * r)
    print(f"  corr = {r:+.4f} (t={t:+.2f}, n={len(j)} teams)")
    print(f"  [a real team-level bias persists; noise does not]")

    print("\n" + "=" * 92)
    print("3 — KALSHI 2025-26: per-team mean z from the fitted ladders")
    print("=" * 92)
    import kalshi_level_disp as KL
    G = KL.build()
    lz = pd.concat([
        G[["home", "z"]].rename(columns={"home": "team"}),
        G[["away", "z"]].rename(columns={"away": "team"})])
    pz = lz.groupby("team")["z"].agg(["size", "mean"])
    pz["se"] = 1.0 / np.sqrt(pz["size"])   # sd(z)~1 established
    vo = pz["mean"].var(ddof=1)
    vn = (pz["se"] ** 2).mean()
    print(f"  mean z overall {lz['z'].mean():+.4f}   observed var of team "
          f"mean z {vo:.4f}   noise var {vn:.4f}")
    print(f"  TRUE between-team variance {vo-vn:+.4f} -> true SD "
          f"{np.sqrt(max(vo-vn,0)):.3f} z-units "
          f"({np.sqrt(max(vo-vn,0))*18.4:.2f} points)")
    print(f"  teams beyond |t|>1.96 on their own SE: "
          f"{int((pz['mean'].abs()/pz['se'] > 1.96).sum())} "
          f"(chance expects ~1.5)")


if __name__ == "__main__":
    main()
