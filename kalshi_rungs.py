"""Two questions the earlier calibration work did NOT settle.

Q1 — ARE ALL RUNGS PROPERLY PRICED?
    kalshi_calib.py tested 10 implied-probability deciles and, separately, 6
    z-position bins, with no family-wise correction and naive SEs on clustered
    data. That is not an answer. Done properly here:

      * deviation measured by RUNG INDEX (1..11), the actual tradeable object
      * game-CLUSTERED standard errors throughout (11 rungs per game are not
        independent observations)
      * family-wise inference by PARAMETRIC BOOTSTRAP under the null "the
        ladder is right": draw each game's total from its own implied
        Normal(mu, sd), recompute every rung, and build the null distribution
        of max|t| across rung positions. This respects the within-game
        correlation structure and corrects for testing 11 positions at once.

    It tests the joint hypothesis: every rung priced correctly AND the implied
    shape is the true shape.

Q2 — DO WIDER LADDERS CORRESPOND TO GENUINELY WIDER MATCHUPS?
    kalshi_vs_book.py found the implied sd is over-dispersed across games:
    the widest quartile priced sd 21.10 against a realized 18.72 (ratio 0.887).
    Two competing explanations:

      (a) the market responds to real matchup features that predict variance,
          and merely over-weights them
      (b) the implied sd contains noise, in which case sorting on it produces
          regression to the mean mechanically and the finding is an artefact

    Distinguished by splitting the implied sd into the part PREDICTABLE from
    prior-only matchup features and the residual part:

        implied_sd = fitted(features) + orthogonal

    If (a), the fitted part should order realized dispersion. If (b), the
    orthogonal part should NOT order it at all -- and if the orthogonal part
    does not order realized dispersion while the market still charges for it,
    that is the over-reaction, isolated.

All features are strictly prior-only: shift(1), rolling 20, min 10, within
season. 2025-26 regular season.
"""
import warnings

import numpy as np
import pandas as pd
from scipy.stats import norm

warnings.filterwarnings("ignore")

import kalshi_calib as KC
from prepare_data import CSV, season_label

W, MINP = 20, 10
NBOOT = 2000
RNG = np.random.default_rng(20260822)


def ladders():
    m = KC.load()
    u = m[~((m["bid"] <= 0) & (m["ask"] >= 1.0))].copy()
    u = u[u["bucket"] == "regular"]
    u = u.sort_values(["event_ticker", "floor_strike"])
    u["rung"] = u.groupby("event_ticker").cumcount() + 1
    rows = []
    for ev, g in u.groupby("event_ticker"):
        f = KC.fit_ladder(g)
        if f:
            rows.append({"event_ticker": ev, "mu": f[0], "sd": f[1],
                         "actual": g["actual"].iloc[0], "k": g["k"].iloc[0]})
    G = pd.DataFrame(rows)
    return u.merge(G, on="event_ticker", suffixes=("", "_g")), G


def features():
    """Prior-only matchup features that plausibly predict total variance."""
    mp = pd.read_csv("team_mapping.csv").set_index(
        "bigdataball_name")["abbr"].to_dict()
    raw = pd.read_csv(CSV, low_memory=False)
    raw["lbl"] = season_label(raw).astype(str)
    raw["d"] = pd.to_datetime(raw["DATE"], errors="coerce")
    g = raw[raw["lbl"].str.contains("Regular Season", na=False)
            & (raw["d"] >= "2025-10-01")].copy()
    n = lambda c: pd.to_numeric(g[c], errors="coerce")
    g["tot"] = n("PTS_H") + n("PTS_R")
    g["H"] = g["TEAM_H"].map(mp)
    g["R"] = g["TEAM_R"].map(mp)
    g["book"] = n("CLOSING TOTAL_H")
    rows = []
    for s, o in (("H", "R"), ("R", "H")):
        rows.append(pd.DataFrame({
            "d": g["d"], "team": g[f"{s}"], "tot": g["tot"],
            "tpa": n(f"3PA_{s}") / n(f"FGA_{s}"), "pts": n(f"PTS_{s}")}))
    L = pd.concat(rows).sort_values("d")
    gb = L.groupby("team")
    L["p_tot"] = gb["tot"].transform(
        lambda s: s.shift(1).rolling(W, min_periods=MINP).mean())
    L["p_vol"] = gb["tot"].transform(
        lambda s: s.shift(1).rolling(W, min_periods=MINP).std())
    L["p_tpa"] = gb["tpa"].transform(
        lambda s: s.shift(1).rolling(W, min_periods=MINP).mean())
    L["prev"] = gb["d"].shift(1)
    L["b2b"] = ((L["d"] - L["prev"]).dt.days == 1).astype(float)
    mk = lambda d, a, b: (d.dt.strftime("%Y-%m-%d") + "|"
                          + np.where(a < b, a, b) + "-" + np.where(a < b, b, a))
    g["k"] = mk(g["d"], g["H"], g["R"])
    agg = []
    for s, o in (("H", "R"), ("R", "H")):
        t = g[["k", "d", s]].rename(columns={s: "team"})
        agg.append(t.merge(L[["d", "team", "p_tot", "p_vol", "p_tpa", "b2b"]],
                           on=["d", "team"], how="left"))
    A = pd.concat(agg).groupby("k", as_index=False).agg(
        p_tot=("p_tot", "mean"), p_vol=("p_vol", "mean"),
        p_tpa=("p_tpa", "mean"), b2b=("b2b", "max"), nn=("p_tot", "size"))
    A = A[A["nn"] == 2]
    return A.merge(g[["k", "book"]].drop_duplicates("k"), on="k", how="left")


def clustered_t(df, val="dev", clus="event_ticker"):
    per = df.groupby(clus)[val].mean()
    if len(per) < 5:
        return np.nan, np.nan, len(per)
    se = per.std(ddof=1) / np.sqrt(len(per))
    return per.mean(), per.mean() / se, len(per)


def main():
    u, G = ladders()
    u["dev"] = u["win"] - u["mid"]
    print(f"  {len(u):,} rungs, {G.shape[0]:,} regular-season games")

    print("\n" + "=" * 96)
    print("Q1 — ARE ALL RUNGS PROPERLY PRICED?  by rung index, game-clustered")
    print("=" * 96)
    obs = {}
    print(f"  {'rung':>5}{'n':>7}{'mean strike':>13}{'implied':>10}"
          f"{'realised':>10}{'dev':>9}{'clust t':>9}")
    for r, g in u.groupby("rung"):
        mn, t, ng = clustered_t(g)
        obs[r] = t
        print(f"  {r:>5}{len(g):>7}{g['floor_strike'].mean():>13.1f}"
              f"{g['mid'].mean():>10.4f}{g['win'].mean():>10.4f}"
              f"{mn:>+9.4f}{t:>9.2f}")
    valid = {k: v for k, v in obs.items() if np.isfinite(v)}
    mx = max(abs(v) for v in valid.values())
    worst = max(valid, key=lambda k: abs(valid[k]))
    print(f"\n  observed max|t| = {mx:.2f} at rung {worst}")

    # parametric bootstrap under "the ladder is right"
    gi = G.set_index("event_ticker")
    ev = u["event_ticker"].values
    mu = gi.loc[ev, "mu"].values
    sd = gi.loc[ev, "sd"].values
    K = u["floor_strike"].values
    mid = u["mid"].values
    rung = u["rung"].values
    codes, uniq = pd.factorize(ev)
    null = np.empty(NBOOT)
    for b in range(NBOOT):
        draw = RNG.normal(gi["mu"].values, gi["sd"].values)
        tot = draw[codes]
        dev = (tot > K).astype(float) - mid
        best = 0.0
        for r in np.unique(rung):
            msk = rung == r
            per = pd.Series(dev[msk]).groupby(codes[msk]).mean()
            if len(per) < 5:
                continue
            s = per.std(ddof=1) / np.sqrt(len(per))
            if s > 0:
                best = max(best, abs(per.mean() / s))
        null[b] = best
    p = (1 + np.sum(null >= mx)) / (NBOOT + 1)
    print(f"  parametric-bootstrap null max|t|: mean {null.mean():.2f} "
          f"sd {null.std():.2f}  95th pct {np.percentile(null,95):.2f}")
    print(f"  FAMILY-WISE p = {p:.4f}")
    print(f"  -> {'no rung is mispriced' if p > 0.05 else 'at least one rung IS mispriced'}"
          f" once clustering and multiplicity are handled")

    print("\n" + "=" * 96)
    print("Q2 — DO WIDER LADDERS MATCH GENUINELY WIDER MATCHUPS?")
    print("=" * 96)
    F = features()
    D = G.merge(F, on="k", how="inner").dropna(
        subset=["p_tot", "p_vol", "p_tpa", "book"])
    D["e"] = D["actual"] - D["mu"]
    print(f"  {len(D):,} games with the full prior-only feature set")

    X = ["p_tot", "p_vol", "p_tpa", "b2b", "book"]
    A = np.column_stack([np.ones(len(D))] + [D[c].values for c in X])

    def reg(y):
        b, *_ = np.linalg.lstsq(A, y, rcond=None)
        r = y - A @ b
        se = np.sqrt(np.diag(np.linalg.pinv(A.T @ A)) * (r @ r) / (len(y) - A.shape[1]))
        r2 = 1 - (r @ r) / ((y - y.mean()) @ (y - y.mean()))
        return b, b / se, r2

    print(f"\n  what does the market's IMPLIED SD respond to?")
    b1, t1, r2a = reg(D["sd"].values)
    print(f"  {'feature':12}{'coef':>11}{'t':>8}")
    for i, c in enumerate(X):
        print(f"  {c:12}{b1[i+1]:>+11.4f}{t1[i+1]:>8.2f}")
    print(f"  R^2 = {r2a:.4f}")

    print(f"\n  what does REALISED |deviation| respond to?  (same features)")
    b2, t2, r2b = reg(D["e"].abs().values)
    for i, c in enumerate(X):
        print(f"  {c:12}{b2[i+1]:>+11.4f}{t2[i+1]:>8.2f}")
    print(f"  R^2 = {r2b:.4f}")

    print("\n" + "=" * 96)
    print("  DECOMPOSITION: split implied sd into the part explained by")
    print("  matchup features and the orthogonal remainder")
    print("=" * 96)
    D["sd_fit"] = A @ b1
    D["sd_orth"] = D["sd"] - D["sd_fit"]
    print(f"  implied sd: total sd {D['sd'].std():.2f}  "
          f"explained {D['sd_fit'].std():.2f}  orthogonal "
          f"{D['sd_orth'].std():.2f}")
    print(f"  -> only {100*D['sd_fit'].var()/D['sd'].var():.1f}% of the "
          f"cross-game variation in implied sd is matchup-explainable")
    for lab, col in (("FITTED part (matchup-driven)", "sd_fit"),
                     ("ORTHOGONAL part (unexplained)", "sd_orth"),
                     ("RAW implied sd", "sd")):
        D["q"] = pd.qcut(D[col], 4, labels=["Q1", "Q2", "Q3", "Q4"])
        print(f"\n  sorted on {lab}")
        print(f"    {'quartile':10}{'n':>6}{'mean implied sd':>17}"
              f"{'realised sd':>13}{'ratio':>8}")
        for q, g in D.groupby("q", observed=True):
            rs = g["e"].std(ddof=1)
            print(f"    {str(q):10}{len(g):>6}{g['sd'].mean():>17.2f}"
                  f"{rs:>13.2f}{rs/g['sd'].mean():>8.3f}")
    print("\n  if the ORTHOGONAL sort orders realised dispersion, the market is")
    print("  seeing something real that our features miss. if it does NOT, the")
    print("  market is charging for variance that does not materialise.")


if __name__ == "__main__":
    main()
