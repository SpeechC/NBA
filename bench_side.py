"""The Voulgaris bench-side claim, tested directly.

CLAIM: the away team chooses which side of the court its bench occupies; most
teams have a fixed preference; a team scores more in the half when it shoots
toward its own bench. Therefore a few teams should score systematically more in
the SECOND half when on the road.

The claim makes three predictions that can be separated, and the third is the
one that matters:

  P1 heterogeneity   the ROAD H2-H1 differential varies across teams by more
                     than sampling noise
  P2 asymmetry       the HOME differential does NOT vary the same way, because
                     the home bench position is fixed by the arena and involves
                     no choice. This is the control that distinguishes a bench
                     effect from a generic team trait.
  P3 PERSISTENCE     a team's road differential is stable season to season. A
                     fixed preference must persist; noise cannot. This is the
                     decisive test -- exactly the filter that killed the
                     team-level line-movement effect.

Method mirrors eos_heterogeneity.py: method-of-moments variance decomposition
with a permutation null, because 30 teams x ~41 road games leaves large sampling
error and raw spread across teams looks impressive when nothing is there.

⚠ Even if all three hold, this is a claim about SCORING, not about pricing. A
stable, findable team effect would very likely be in the market by now; the
interest is whether the underlying basketball fact is real.
"""
import warnings

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")
RNG = np.random.default_rng(0)


def build():
    from halves import period_scores
    from prepare_data import CSV, season_label
    raw = pd.read_csv(CSV, low_memory=False)
    raw["lbl"] = season_label(raw).astype(str)
    d = raw[raw["lbl"].str.contains("Regular Season", na=False)].copy()
    d["gid"] = d["GAME-ID"].astype(str).str.zfill(10)
    d["date"] = pd.to_datetime(d["DATE"], errors="coerce")
    w = period_scores("RegularSeason")
    keep = ["gid"] + [f"{s}_p{q}" for s in ("home", "vis") for q in (1, 2, 3, 4)]
    m = d[["gid", "lbl", "date", "TEAM_H", "TEAM_R"]].merge(w[keep], on="gid")

    rows = []
    for side, opp in (("home", "vis"), ("vis", "home")):
        team = "TEAM_H" if side == "home" else "TEAM_R"
        rows.append(pd.DataFrame({
            "lbl": m["lbl"], "date": m["date"], "team": m[team],
            "road": side == "vis",
            "h1": m[f"{side}_p1"] + m[f"{side}_p2"],
            "h2": m[f"{side}_p3"] + m[f"{side}_p4"]}))
    L = pd.concat(rows, ignore_index=True)
    L["diff"] = L["h2"] - L["h1"]          # positive = scores more in H2
    L["yr"] = L["lbl"].str.extract(r"(\d{4})")[0].astype(int)
    return L[(L["h1"] > 20) & (L["h2"] > 20)]


def decompose(df, label):
    """MoM variance components of the per-team H2-H1 differential."""
    rows = []
    for t, s in df.groupby("team"):
        if len(s) < 100:
            continue
        rows.append({"team": t, "n": len(s), "d": s["diff"].mean(),
                     "sv": s["diff"].var(ddof=1) / len(s)})
    t = pd.DataFrame(rows)
    vo, vs = t["d"].var(ddof=1), t["sv"].mean()
    vt = max(0.0, vo - vs)
    lam = vt / (vt + vs) if vt + vs > 0 else 0.0
    t["shrunk"] = t["d"].mean() + lam * (t["d"] - t["d"].mean())
    print(f"\n  {label}")
    print(f"    mean differential {t['d'].mean():+.3f}   "
          f"Var_obs {vo:.4f}  Var_samp {vs:.4f}  Var_true {vt:.4f} "
          f"(sd {np.sqrt(vt):.3f})   lambda {lam:.3f}")
    return t, vo, vs, vt, lam


def perm_null(df, n=1200):
    """Shuffle team labels within (season, road) cells."""
    out = []
    for _ in range(n):
        p = df.copy()
        p["team"] = (p.groupby(["yr", "road"])["team"]
                     .transform(lambda s: RNG.permutation(s.values)))
        rows = []
        for t, s in p.groupby("team"):
            if len(s) < 100:
                continue
            rows.append(s["diff"].mean())
        if len(rows) > 5:
            out.append(np.var(rows, ddof=1))
    return np.array(out)


def main():
    L = build()
    print(f"{len(L):,} team-games   {L['team'].nunique()} teams   "
          f"{L['yr'].nunique()} seasons")
    road, home = L[L["road"]], L[~L["road"]]
    print(f"pooled H2-H1:  road {road['diff'].mean():+.3f}   "
          f"home {home['diff'].mean():+.3f}")

    print("\n" + "=" * 92)
    print("P1/P2 — does the differential vary by team, on the road but not at home?")
    print("=" * 92)
    tr, vor, vsr, vtr, lamr = decompose(road, "ROAD games")
    th, voh, vsh, vth, lamh = decompose(home, "HOME games (control)")

    nr, nh = perm_null(road), perm_null(home)
    print(f"\n  permutation null on Var_obs (team labels shuffled):")
    print(f"    ROAD  observed {vor:.4f}   null {nr.mean():.4f} ± {nr.std():.4f}"
          f"   percentile {100*np.mean(nr < vor):.1f}")
    print(f"    HOME  observed {voh:.4f}   null {nh.mean():.4f} ± {nh.std():.4f}"
          f"   percentile {100*np.mean(nh < voh):.1f}")

    print("\n  most extreme ROAD teams (raw vs shrunk H2-H1):")
    x = tr.sort_values("d")
    print(pd.concat([x.head(4), x.tail(4)])[["team", "n", "d", "shrunk"]]
          .round(3).to_string(index=False))

    print("\n" + "=" * 92)
    print("P3 — PERSISTENCE: is a team's road differential stable year to year?")
    print("=" * 92)
    ts = (road.groupby(["yr", "team"])["diff"].agg(["mean", "size"])
          .reset_index())
    ts = ts[ts["size"] >= 25]
    piv = ts.pivot(index="team", columns="yr", values="mean")
    yrs = sorted(piv.columns)
    rows = []
    for i in range(len(yrs) - 1):
        pair = piv[[yrs[i], yrs[i + 1]]].dropna()
        if len(pair) >= 20:
            rows.append({"from": yrs[i], "to": yrs[i + 1], "teams": len(pair),
                         "corr": round(np.corrcoef(pair.iloc[:, 0],
                                                   pair.iloc[:, 1])[0, 1], 3)})
    P = pd.DataFrame(rows)
    print(P.to_string(index=False))
    print(f"\n  mean year-over-year correlation: {P['corr'].mean():+.3f}")
    print("  A fixed bench preference REQUIRES this to be clearly positive.")

    # split-half within season, as a same-sample-size comparison
    road2 = road.sort_values("date").copy()
    road2["half"] = (road2.groupby(["yr", "team"]).cumcount()
                     < road2.groupby(["yr", "team"])["diff"].transform("size") / 2)
    sh = road2.groupby(["yr", "team", "half"])["diff"].mean().unstack()
    sh = sh.dropna()
    if len(sh) > 20:
        r = np.corrcoef(sh.iloc[:, 0], sh.iloc[:, 1])[0, 1]
        print(f"  within-season split-half correlation: {r:+.3f} "
              f"(n={len(sh)} team-seasons)")

    print("\n" + "=" * 92)
    print("Is any single team significant after correcting for 30 tests?")
    print("=" * 92)
    rows = []
    for t, s in road.groupby("team"):
        tt, pp = stats.ttest_1samp(s["diff"], road["diff"].mean())
        rows.append({"team": t, "n": len(s), "road H2-H1": round(s["diff"].mean(), 3),
                     "t": round(tt, 2), "p": round(pp, 4)})
    R = pd.DataFrame(rows).sort_values("p")
    print(R.head(6).to_string(index=False))
    p = R["p"].values
    o = np.argsort(p)
    thr = 0.10 * np.arange(1, len(p) + 1) / len(p)
    k = np.max(np.where(p[o] <= thr)[0]) + 1 if (p[o] <= thr).any() else 0
    print(f"\n  raw p<0.05: {int((R['p']<0.05).sum())} of {len(R)} "
          f"(expect ~{0.05*len(R):.1f})   surviving BH q<0.10: {k}")


if __name__ == "__main__":
    main()
