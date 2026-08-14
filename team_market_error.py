"""Team-specific market error: does DK price SOME visitors badly?

The pooled test asked whether the visitor signal S predicts DK pricing error
across all teams. It does not (t = 0.35). That is a different claim from "DK
prices every visitor equally well", and the second was never tested.

It is not a post-hoc rescue: true cross-team heterogeneity in the road H2-H1
effect was established on 2017-2023 data, years before this DK sample existed
(Var_true 3.17, lambda 0.858, year-over-year persistence +0.44).

SEQUENCE, as specified:

  1 freeze S_j from PRE-2023 road games, empirical-Bayes shrunk
  2 confirm which team effects persist in actual 2023-24 scoring  A_j
  3 compute DK's implied allocation  M_i = FG_line - 2*H1_line,  M_j = mean
  4 team market error  E_j = A_j - M_j, shrunk
  5 is there true between-team variance in E?   tau^2 > 0 with a permutation null
  6 DECISIVE: Oct-Dec team errors vs Jan-Mar team errors
  7 ROI only if 6 passes

Allocation uses actual_full - 2*actual_H1 so that overtime is included on both
sides, matching how the market's implied H2 is constructed from its full-game
line.

Also reported: the four-way categorisation (persistent+priced,
persistent+underpriced, effect decayed, new effect), which prevents mistaking
model decay for bookmaker error; and whether |A_j - M_j| grows with |S_j|, i.e.
whether DK prices historically unusual teams less accurately.
"""
import warnings

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")
RNG = np.random.default_rng(0)

DK = "/mnt/c/NBA/nba_draftkings_totals_historical.csv"
SPLIT = pd.Timestamp("2024-01-01")


def shrink(df, key, val):
    """Empirical-Bayes shrunk group means with the MoM variance component."""
    rows = []
    for g, s in df.groupby(key):
        if len(s) < 5:
            continue
        rows.append({key: g, "n": len(s), "raw": s[val].mean(),
                     "sv": s[val].var(ddof=1) / len(s)})
    t = pd.DataFrame(rows)
    vo, vs = t["raw"].var(ddof=1), t["sv"].mean()
    vt = max(0.0, vo - vs)
    lam = vt / (vt + vs) if vt + vs > 0 else 0.0
    t["shrunk"] = t["raw"].mean() + lam * (t["raw"] - t["raw"].mean())
    return t, vo, vs, vt, lam


def build():
    from bench_oos import build as bench_build
    from halves import period_scores
    from prepare_data import CSV, season_label

    # 1 -- pre-2023 visitor signal
    gg, L = bench_build()
    road = L[L["road"] & (L["yr"] < 2023)]
    sig, _, _, vt, lam = shrink(road, "team", "h21")
    lg = road["h21"].mean()
    sig["S"] = sig["shrunk"] - lg
    print(f"1  pre-2023 visitor signal: {len(sig)} teams, "
          f"Var_true {vt:.3f}, lambda {lam:.3f}, league mean {lg:+.3f}")

    # 2/3 -- 2023-24 games with DK lines
    raw = pd.read_csv(CSV, low_memory=False)
    raw["lbl"] = season_label(raw).astype(str)
    o = raw[raw["lbl"].str.contains("Regular Season", na=False)].copy()
    o["gid"] = o["GAME-ID"].astype(str).str.zfill(10)
    o["date"] = pd.to_datetime(o["DATE"], errors="coerce")
    o["actual_full"] = o["PTS_H"] + o["PTS_R"]
    ps = period_scores("RegularSeason")
    o = o.merge(ps[["gid", "q1", "q2"]], on="gid", how="inner")
    o["actual_h1"] = o["q1"] + o["q2"]
    o["A"] = o["actual_full"] - 2 * o["actual_h1"]
    tm = pd.read_csv("team_mapping.csv")
    ab = dict(zip(tm["bigdataball_name"], tm["abbr"]))
    o["key"] = (o["date"].dt.strftime("%Y-%m-%d") + "_" + o["TEAM_R"].map(ab)
                + "_" + o["TEAM_H"].map(ab))
    o["visitor"] = o["TEAM_R"]

    dk = pd.read_csv(DK)
    dk["key"] = dk["game_date_et"] + "_" + dk["away_abbr"] + "_" + dk["home_abbr"]
    dk = dk.dropna(subset=["h1_total_close", "full_game_total_close"])
    j = o.merge(dk[["key", "full_game_total_close", "h1_total_close",
                    "h1_over_price_close", "h1_under_price_close"]],
                on="key", how="inner")
    j["M"] = j["full_game_total_close"] - 2 * j["h1_total_close"]
    j["E"] = j["A"] - j["M"]
    j = j.merge(sig[["team", "S"]].rename(columns={"team": "visitor"}),
                on="visitor", how="inner")
    print(f"2/3 DK games joined with a frozen signal: {len(j)}  "
          f"({j['visitor'].nunique()} visitors, "
          f"{len(j)/j['visitor'].nunique():.1f} per team)")
    print(f"    mean actual allocation {j['A'].mean():+.3f}   "
          f"mean market allocation {j['M'].mean():+.3f}   "
          f"mean error {j['E'].mean():+.3f}")
    return j, sig


def main():
    j, sig = build()

    print("\n" + "=" * 104)
    print("4/5 — team market error E_j, and is there TRUE between-team variance?")
    print("=" * 104)
    t, vo, vs, vt, lam = shrink(j, "visitor", "E")
    print(f"  Var_obs {vo:.3f}   Var_samp {vs:.3f}   Var_true {vt:.3f} "
          f"(sd {np.sqrt(vt):.3f})   lambda {lam:.3f}")
    null = []
    for _ in range(2000):
        p = j.copy()
        p["visitor"] = RNG.permutation(p["visitor"].values)
        rows = [s["E"].mean() for _, s in p.groupby("visitor") if len(s) >= 5]
        null.append(np.var(rows, ddof=1))
    null = np.array(null)
    print(f"  permutation null Var_obs {null.mean():.3f} ± {null.std():.3f}"
          f"   observed at percentile {100*np.mean(null < vo):.1f}")
    if vt <= 0.01:
        print("  -> no true between-team variance in pricing error. Done.")

    print("\n" + "=" * 104)
    print("7-way view — signal S_j, actual A_j, market M_j, error E_j")
    print("=" * 104)
    agg = j.groupby("visitor").agg(n=("E", "size"), A=("A", "mean"),
                                   M=("M", "mean"), E=("E", "mean")).reset_index()
    agg = agg.merge(sig[["team", "S"]].rename(columns={"team": "visitor"}),
                    on="visitor")
    agg = agg.merge(t[["visitor", "shrunk"]].rename(
        columns={"shrunk": "E_shrunk"}), on="visitor")
    agg = agg.sort_values("S")
    print(agg.round(2).to_string(index=False))

    print("\n  does DK track the frozen signal at team level?")
    for a, b, lab in ((agg["S"], agg["A"], "S_j -> actual A_j  (does the effect persist?)"),
                      (agg["S"], agg["M"], "S_j -> market M_j  (does DK know it?)"),
                      (agg["S"], agg["E"], "S_j -> error  E_j  (is it underpriced?)")):
        r = np.corrcoef(a, b)[0, 1]
        print(f"    {lab:48} corr {r:+.3f}")

    print("\n  does DK price historically extreme teams less accurately?")
    r = np.corrcoef(agg["S"].abs(), agg["E"].abs())[0, 1]
    print(f"    corr(|S_j|, |E_j|) = {r:+.3f}")

    print("\n" + "=" * 104)
    print("6 — DECISIVE: Oct-Dec team error vs Jan-Mar team error")
    print("=" * 104)
    d1, d2 = j[j["date"] < SPLIT], j[j["date"] >= SPLIT]
    print(f"  discovery {len(d1)} games   holdout {len(d2)} games")
    t1, *_ , lam1 = shrink(d1, "visitor", "E")
    t2, *_ = shrink(d2, "visitor", "E")
    m = t1[["visitor", "raw", "shrunk"]].rename(
        columns={"raw": "E1_raw", "shrunk": "E1_shrunk"}).merge(
        t2[["visitor", "raw"]].rename(columns={"raw": "E2"}), on="visitor")
    print(f"  teams in both windows: {len(m)}")
    for c, lab in (("E1_raw", "raw"), ("E1_shrunk", "shrunk")):
        r = np.corrcoef(m[c], m["E2"])[0, 1]
        tt = r * np.sqrt(len(m) - 2) / np.sqrt(1 - r * r)
        print(f"    corr(E_OctDec {lab:6}, E_JanMar) = {r:+.3f}   t={tt:+.2f}")
    m["terc"] = pd.qcut(m["E1_shrunk"], 3, labels=["most neg", "middle",
                                                   "most pos"])
    print("\n  terciles of the discovery residual vs the holdout residual:")
    print(m.groupby("terc", observed=True).agg(
        teams=("visitor", "size"), E1=("E1_shrunk", "mean"),
        E2=("E2", "mean")).round(3).to_string())
    print("\n  monotone holdout response is required before any ROI is computed.")


if __name__ == "__main__":
    main()
