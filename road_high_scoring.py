"""Do the HIGHEST-SCORING teams underperform their implied team total on the
road?

THE MARKET OBJECT. The closing total and spread jointly imply a team total:

    own_spread  = CLOSING_SPREAD_H          if the team is home
                = -CLOSING_SPREAD_H         if the team is away
    implied_own = total/2 - own_spread/2

which satisfies implied_H + implied_R = total and implied_H - implied_R =
-spread_H by construction. Team totals are a real betting market, so this is a
directional test with a direct payoff mapping, not a dispersion test.

    resid = actual own points - implied_own

WHY IT MUST BE A DIFFERENCE-IN-DIFFERENCES. Home advantage is already inside the
spread, so road teams are ALREADY expected to score less. The hypothesis is not
"road teams underperform" -- that would just be asking whether the spread exists.
It is that the market UNDER-adjusts for the road specifically for high-scoring
teams. So the estimand is

    DiD = (HIGH road - HIGH home) - (rest road - rest home)

with DiD < 0 supporting the hypothesis. The simple HIGH-road mean is reported
too, but the DiD is the test.

DEFINING "HIGHEST SCORING", drift-robust. League scoring rose materially over
2017-2026, so an absolute prior-only threshold would select a drifting share --
the failure mode diagnosed in efg_steal_spread.py, where a frozen cutoff went
from 12.5% to 48.7% of the league. The state is therefore a DEVIATION from the
contemporaneous league level, mirroring ref_features.py's LeagueFoulState:

    score_dev = team's prior-20-game mean points
                - league trailing-500-game mean points

HIGH = top 20% of score_dev, threshold frozen on DEVELOPMENT. The qualifying
share is reported by season so any residual drift is visible rather than assumed
away.

Everything is prior-only: shift(1), rolling 20, min 10, within season.
Development 2017-18..2023-24; holdout 2024-25 and 2025-26.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import refs
from data_split import SPLIT_DATE
from dispersion_priced import ols

W, MINP = 20, 10
LGW = 500
Q = 0.80
NPERM = 5000
RNG = np.random.default_rng(20260821)


def build():
    m = refs.build()
    m["gid"] = m["GAME-ID"].astype(str).str.strip()
    n = lambda c: pd.to_numeric(m[c], errors="coerce")
    m["spread"] = n("CLOSING SPREAD_H")
    adv = pd.read_csv("/mnt/c/NBA2/advanced_stats/game_advanced_stats.csv",
                      low_memory=False)
    adv["gid"] = adv["GAME-ID"].astype(str).str.strip()
    m = m.merge(adv[["gid", "ADV_TEAM_ABBR_H", "ADV_TEAM_ABBR_R"]], on="gid",
                how="left")
    rows = []
    for s, o in (("H", "R"), ("R", "H")):
        rows.append(pd.DataFrame({
            "gid": m["gid"], "yr": m["yr"], "date": m["date"],
            "home": 1 if s == "H" else 0,
            "team": m[f"ADV_TEAM_ABBR_{s}"], "opp": m[f"ADV_TEAM_ABBR_{o}"],
            "pts": n(f"PTS_{s}"), "opp_pts": n(f"PTS_{o}"),
            "total": m["total"], "spread_h": m["spread"]}))
    L = pd.concat(rows, ignore_index=True).dropna(
        subset=["pts", "total", "spread_h", "team"])
    L["own_spread"] = np.where(L["home"] == 1, L["spread_h"], -L["spread_h"])
    L["implied"] = L["total"] / 2.0 - L["own_spread"] / 2.0
    L["resid"] = L["pts"] - L["implied"]
    L = L.sort_values(["date", "gid"]).reset_index(drop=True)

    # league trailing level, prior-only, on the game-ordered panel
    gl = L.groupby("gid", as_index=False)["pts"].mean().sort_values("gid")
    L["lg"] = L["pts"].shift(1).rolling(LGW, min_periods=LGW // 2).mean()
    L["prior_pts"] = L.groupby(["yr", "team"])["pts"].transform(
        lambda s: s.shift(1).rolling(W, min_periods=MINP).mean())
    L["score_dev"] = L["prior_pts"] - L["lg"]
    return L.dropna(subset=["score_dev", "resid"])


def cell(x):
    return len(x), x["resid"].mean(), x["resid"].std(ddof=1)


def did(x):
    """(HIGH road - HIGH home) - (rest road - rest home), with SE."""
    parts, means, vs, ns = [], [], [], []
    for h in (1, 0):
        for r in (0, 1):
            s = x[(x["high"] == h) & (x["home"] == r)]["resid"]
            means.append(s.mean()); vs.append(s.var(ddof=1)); ns.append(len(s))
    d = (means[1] - means[0]) - (means[3] - means[2])
    se = np.sqrt(sum(v / n for v, n in zip(vs, ns)))
    return d, se, ns


def main():
    L = build()
    print(f"  {len(L):,} team-games, {L['gid'].nunique():,} games")

    print("\n" + "=" * 96)
    print("0 — PREMISE: how big is home advantage, and is it already priced?")
    print("=" * 96)
    h, r = L[L["home"] == 1], L[L["home"] == 0]
    print(f"  home win rate            {100*(h['pts']>h['opp_pts']).mean():.2f}%")
    print(f"  points: home {h['pts'].mean():.2f}   road {r['pts'].mean():.2f}"
          f"   raw gap {h['pts'].mean()-r['pts'].mean():+.2f}")
    print(f"  IMPLIED team total: home {h['implied'].mean():.2f}   "
          f"road {r['implied'].mean():.2f}   "
          f"gap {h['implied'].mean()-r['implied'].mean():+.2f}")
    print(f"  residual (actual - implied): home {h['resid'].mean():+.4f}   "
          f"road {r['resid'].mean():+.4f}")
    d = h["resid"].mean() - r["resid"].mean()
    se = np.sqrt(h["resid"].var(ddof=1)/len(h) + r["resid"].var(ddof=1)/len(r))
    print(f"  -> home advantage is priced to within {d:+.4f} points "
          f"(t={d/se:+.2f}). The market already knows.")

    dev = L[L["date"] < SPLIT_DATE]
    thr = dev["score_dev"].quantile(Q)
    L["high"] = (L["score_dev"] >= thr).astype(int)
    print(f"\n  FROZEN development top-20% threshold: score_dev >= {thr:+.4f} "
          f"points above the trailing league level")
    print(f"  qualifying share by season (drift check):")
    t = L.groupby("yr")["high"].agg(["size", "mean"])
    print("    " + "   ".join(f"{y}:{100*v:.1f}%"
                              for y, v in t["mean"].items()))

    print("\n" + "=" * 96)
    print("1 — PRIMARY: DiD = (HIGH road - HIGH home) - (rest road - rest home)")
    print("  negative supports the hypothesis")
    print("=" * 96)
    for lab, x in (("development", L[L["date"] < SPLIT_DATE]),
                   ("holdout", L[L["date"] >= SPLIT_DATE]), ("pooled", L)):
        print(f"\n  {lab}")
        print(f"    {'group':14}{'n':>7}{'mean resid':>13}{'sd':>9}")
        for hl, hn in ((1, "HIGH"), (0, "rest")):
            for rd, rn in ((1, "home"), (0, "ROAD")):
                n_, mu, sd = cell(x[(x["high"] == hl) & (x["home"] == rd)])
                print(f"    {hn+' '+rn:14}{n_:7,}{mu:+13.4f}{sd:9.3f}")
            s = x[x["high"] == hl]
            a = s[s["home"] == 0]["resid"]; b = s[s["home"] == 1]["resid"]
            gap = a.mean() - b.mean()
            gse = np.sqrt(a.var(ddof=1)/len(a) + b.var(ddof=1)/len(b))
            print(f"    {'  road-home':14}{'':7}{gap:+13.4f}"
                  f"  (t={gap/gse:+.2f})")
        dd, dse, ns = did(x)
        print(f"    DiD {dd:+.4f}  (t={dd/dse:+.2f})")

    print("\n" + "=" * 96)
    print("2 — REGRESSION FORM, pooled: resid ~ HIGH + ROAD + HIGH x ROAD")
    print("=" * 96)
    for lab, x in (("development", L[L["date"] < SPLIT_DATE]),
                   ("holdout", L[L["date"] >= SPLIT_DATE]), ("pooled", L)):
        road = (1 - x["home"]).values
        X = np.column_stack([x["high"].values, road, x["high"].values * road])
        b, se, t = ols(x["resid"].values, X)
        print(f"  {lab:14} HIGH {b[1]:+.4f} (t={t[1]:+.2f})   "
              f"ROAD {b[2]:+.4f} (t={t[2]:+.2f})   "
              f"HIGH x ROAD {b[3]:+.4f} (t={t[3]:+.2f})")

    print("\n" + "=" * 96)
    print("3 — THE BET: team-total UNDER on a HIGH-scoring road team")
    print("=" * 96)
    print(f"  {'window':14}{'n':>7}{'mean resid':>13}{'under %':>10}"
          f"{'vs 52.38':>11}")
    for lab, x in (("development", L[L["date"] < SPLIT_DATE]),
                   ("holdout", L[L["date"] >= SPLIT_DATE]), ("pooled", L)):
        s = x[(x["high"] == 1) & (x["home"] == 0)]
        u = 100 * (s["resid"] < 0).mean()
        print(f"  {lab:14}{len(s):7,}{s['resid'].mean():+13.4f}{u:10.2f}%"
              f"{u-52.38:+11.2f}pp")

    print("\n" + "=" * 96)
    print(f"4 — PERMUTATION: reshuffle the HIGH flag within season, "
          f"home/road fixed, {NPERM} reps")
    print("=" * 96)
    for lab, x in (("development", L[L["date"] < SPLIT_DATE]), ("pooled", L)):
        obs, _, _ = did(x)
        yrs = x["yr"].values
        hi = x["high"].values.copy()
        blocks = [np.where(yrs == u)[0] for u in np.unique(yrs)]
        rv = x["resid"].values
        hm = x["home"].values
        null = np.empty(NPERM)
        for j in range(NPERM):
            h2 = hi.copy()
            for b_ in blocks:
                h2[b_] = hi[b_][RNG.permutation(len(b_))]
            mm = []
            for a in (1, 0):
                for c in (0, 1):
                    mm.append(rv[(h2 == a) & (hm == c)].mean())
            null[j] = (mm[1] - mm[0]) - (mm[3] - mm[2])
        p = (1 + np.sum(np.abs(null) >= abs(obs))) / (NPERM + 1)
        print(f"  {lab:14} observed DiD {obs:+.4f}   null {null.mean():+.4f} "
              f"sd {null.std():.4f}   two-sided p={p:.4f}")


if __name__ == "__main__":
    main()
