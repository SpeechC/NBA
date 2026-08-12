"""Is the team-level H1/H2 differential priced into the live 2H total?

The pattern is established: road H2-H1 differentials vary across teams with
lambda = 0.858 and year-over-year persistence of +0.444, spanning ~9 points. The
mechanism does not matter for exploitation; persistence and predictiveness do.

The live 2H total is the only market here that can test pricing, and it is a good
one, because we already know it is set by a near-mechanical rule:

    2H_line ~ 4.62 + 0.4925 * pregame_total - 0.0330 * H1_total     R^2 = 0.78

That rule contains no team term. So the complete three-clause test from
SPORT_SCREENING_BRIEF section 1a applies:

  1 the book applies a simplifying rule            -- already demonstrated
  2 the rule discards something that predicts the residual  -- TESTED HERE
  3 that something is knowable before the bet      -- yes: differentials are
    computed from PRIOR SEASONS only, so they are known at tip-off

Predictor, strictly walk-forward:

    edge_i = road_diff(away team, prior seasons) + home_diff(home team, prior)

Both teams contribute, because the 2H total covers both. If the book ignores team
identity, edge should predict the 2H residual. If it does not, the omission is
correct and the pattern is already in the price.
"""
import warnings

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")

BE = 110 / 210


def build():
    from bench_side import build as bench_build
    from halves import period_scores
    from prepare_data import CSV, season_label

    L = bench_build()          # team-game level H1/H2, road flag, season year
    raw = pd.read_csv(CSV, low_memory=False)
    raw["lbl"] = season_label(raw).astype(str)
    d = raw[raw["lbl"].str.contains("Regular Season", na=False)].copy()
    d["gid"] = d["GAME-ID"].astype(str).str.zfill(10)
    d["date"] = pd.to_datetime(d["DATE"], errors="coerce")
    d["pre"] = pd.to_numeric(d["CLOSING TOTAL_H"], errors="coerce")
    a = pd.to_numeric(d["HALFTIME_H"], errors="coerce")
    b = pd.to_numeric(d["HALFTIME_R"], errors="coerce")
    d["h2_line"] = np.where(a.between(80, 160), a,
                            np.where(b.between(80, 160), b, np.nan))
    d["yr"] = d["lbl"].str.extract(r"(\d{4})")[0].astype(int)

    w = period_scores("RegularSeason")
    keep = ["gid", "h1", "h2"]
    d = d.merge(w[keep], on="gid", how="inner")
    d = d.dropna(subset=["h2_line", "pre", "h1", "h2"])
    d["r2h"] = d["h2"] - d["h2_line"]          # regulation H2 vs the 2H line

    # walk-forward differentials: for season Y use seasons strictly before Y
    diffs = []
    for yr in sorted(L["yr"].unique()):
        prior = L[L["yr"] < yr]
        if prior["yr"].nunique() < 1:
            continue
        for road, lab in ((True, "road"), (False, "home")):
            g = prior[prior["road"] == road].groupby("team")["diff"]
            t = g.agg(["mean", "size"]).reset_index()
            t = t[t["size"] >= 60]
            t["yr"], t["kind"] = yr, lab
            diffs.append(t.rename(columns={"mean": "d"}))
    D = pd.concat(diffs)
    road = D[D["kind"] == "road"][["yr", "team", "d"]].rename(
        columns={"team": "TEAM_R", "d": "away_road_diff"})
    home = D[D["kind"] == "home"][["yr", "team", "d"]].rename(
        columns={"team": "TEAM_H", "d": "home_home_diff"})
    d = d.merge(road, on=["yr", "TEAM_R"], how="inner")
    d = d.merge(home, on=["yr", "TEAM_H"], how="inner")
    d["edge"] = d["away_road_diff"] + d["home_home_diff"]
    return d


def main():
    d = build()
    print(f"{len(d):,} games with a 2H line, period scoring, and prior-season "
          f"differentials")
    print(f"  seasons: {sorted(d['yr'].unique())}")
    print(f"  edge: mean {d['edge'].mean():+.3f}  sd {d['edge'].std():.3f}  "
          f"range [{d['edge'].min():+.2f}, {d['edge'].max():+.2f}]\n")

    print("=" * 92)
    print("Does the walk-forward edge predict the 2H residual?")
    print("=" * 92)
    for col, lab in (("edge", "combined edge"),
                     ("away_road_diff", "away team's road differential"),
                     ("home_home_diff", "home team's home differential")):
        r = np.corrcoef(d[col], d["r2h"])[0, 1]
        b = np.polyfit(d[col], d["r2h"], 1)[0]
        t = r * np.sqrt(len(d) - 2) / np.sqrt(1 - r * r)
        print(f"  {lab:32} corr {r:+.4f}   slope {b:+.4f}   t={t:+.2f}")

    print("\n  does the book's own line already contain it?")
    for col, lab in (("edge", "combined edge"),):
        r = np.corrcoef(d[col], d["h2_line"])[0, 1]
        rp = np.corrcoef(d[col], d["h2_line"] - 0.4925 * d["pre"])[0, 1]
        print(f"  corr({lab}, 2H line)                {r:+.4f}")
        print(f"  corr({lab}, 2H line net of the rule) {rp:+.4f}")

    print("\n" + "=" * 92)
    print("Betting form: quintiles of the walk-forward edge")
    print("=" * 92)
    d = d[d["r2h"] != 0].copy()
    d["q"] = pd.qcut(d["edge"], 5, labels=[1, 2, 3, 4, 5])
    rows = []
    for q, s in d.groupby("q", observed=True):
        ov = (s["r2h"] > 0).mean()
        se = np.sqrt(ov * (1 - ov) / len(s))
        rows.append({"quintile": q, "n": len(s),
                     "mean edge": round(s["edge"].mean(), 2),
                     "2H resid": round(s["r2h"].mean(), 3),
                     "over %": round(100 * ov, 2),
                     "95% CI": f"[{100*(ov-1.96*se):.1f}, {100*(ov+1.96*se):.1f}]",
                     "ROI110": round(100 * (ov * (100 / 110) - (1 - ov)), 2)})
    t = pd.DataFrame(rows)
    print(t.to_string(index=False))
    rc = np.corrcoef(np.arange(5), t["over %"])[0, 1]
    print(f"\n  monotone: {t['over %'].is_monotonic_increasing}   "
          f"rank corr {rc:+.3f}   break-even {100*BE:.2f}%")

    print("\n--- top vs bottom quintile ---")
    hi, lo = d[d["q"] == 5], d[d["q"] == 1]
    tt, pp = stats.ttest_ind(hi["r2h"], lo["r2h"], equal_var=False)
    print(f"  Q5 resid {hi['r2h'].mean():+.3f}   Q1 resid {lo['r2h'].mean():+.3f}"
          f"   diff {hi['r2h'].mean()-lo['r2h'].mean():+.3f}  t={tt:+.2f} p={pp:.4f}")
    print(f"  predicted diff from the edge itself: "
          f"{hi['edge'].mean()-lo['edge'].mean():+.3f}")


if __name__ == "__main__":
    main()
