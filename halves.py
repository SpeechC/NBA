"""The Voulgaris half-totals hypothesis, tested on what we can actually observe.

Claims:
  A. NBA scoring differs systematically between halves
  B. Books priced halves too symmetrically -- roughly half the full-game total
  C. Fourth quarters differ in kind (fouling, timeouts, clock stoppage)
  D. Teams score more shooting toward their own bench (H2 by NBA convention)

What we can and cannot test:

  CAN: the basketball facts (A, C, D-as-an-H2-effect) from period scoring, and
       whether the book's LIVE 2H line reflects them.
  CANNOT: the historical edge itself. That was on PREGAME half totals, which
       this dataset does not contain -- our 2H lines are set AT halftime, with
       the first half already known. A pregame H1/H2 market is where the
       symmetry assumption would bite, and we cannot see it.

So this establishes whether the underlying asymmetry exists and is stable, which
is the precondition for the edge, without being able to price it directly.

Note D cuts both ways: if BOTH teams shoot toward their own bench in the second
half, the effect is symmetric between teams and shows up as H2 > H1 overall, not
as an advantage to either side.
"""
import warnings

import duckdb
import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")

PBP = "/home/dpope/data/pbp_lineups_all.parquet"


def period_scores():
    """Points per period per side, from the SCORE column ('visitor - home')."""
    con = duckdb.connect()
    q = f"""
    WITH s AS (
      SELECT lpad(CAST(GAME_ID AS VARCHAR),10,'0') AS gid,
             SEASON AS season, PERIOD,
             CAST(PCTIMESTRING AS INTEGER) AS t, SCORE,
             row_number() OVER (PARTITION BY GAME_ID, PERIOD
                                ORDER BY CAST(PCTIMESTRING AS INTEGER) DESC) AS rn
      FROM read_parquet('{PBP}')
      WHERE SEASON_TYPE='RegularSeason' AND SCORE IS NOT NULL AND PERIOD <= 4
    )
    SELECT gid, season, PERIOD, SCORE FROM s WHERE rn = 1
    """
    d = con.execute(q).fetchdf()
    p = d["SCORE"].str.split("-", expand=True)
    d["vis"] = pd.to_numeric(p[0].str.strip(), errors="coerce")
    d["home"] = pd.to_numeric(p[1].str.strip(), errors="coerce")
    d = d.dropna(subset=["vis", "home"])
    w = d.pivot_table(index=["gid", "season"], columns="PERIOD",
                      values=["vis", "home"], aggfunc="first")
    w.columns = [f"{a}_q{b}" for a, b in w.columns]
    w = w.reset_index().dropna()
    # cumulative -> per period
    for side in ("vis", "home"):
        for q in (4, 3, 2):
            w[f"{side}_p{q}"] = w[f"{side}_q{q}"] - w[f"{side}_q{q-1}"]
        w[f"{side}_p1"] = w[f"{side}_q1"]
    w["h1"] = (w["vis_p1"] + w["vis_p2"] + w["home_p1"] + w["home_p2"])
    w["h2"] = (w["vis_p3"] + w["vis_p4"] + w["home_p3"] + w["home_p4"])
    for q in (1, 2, 3, 4):
        w[f"q{q}"] = w[f"vis_p{q}"] + w[f"home_p{q}"]
    return w


def main():
    w = period_scores()
    w = w[(w["h1"] > 60) & (w["h2"] > 60) & (w["h1"] < 160) & (w["h2"] < 160)]
    print(f"{len(w):,} games with clean period scoring\n")

    print("=" * 92)
    print("A/C. Scoring by period (regulation only)")
    print("=" * 92)
    rows = []
    for q in (1, 2, 3, 4):
        v = w[f"q{q}"]
        rows.append({"period": f"Q{q}", "mean pts": round(v.mean(), 2),
                     "sd": round(v.std(), 2)})
    print(pd.DataFrame(rows).to_string(index=False))
    t, p = stats.ttest_rel(w["h1"], w["h2"])
    print(f"\n  H1 {w['h1'].mean():.2f}   H2 {w['h2'].mean():.2f}   "
          f"difference {w['h1'].mean()-w['h2'].mean():+.2f}   t={t:+.1f}  p={p:.2e}")
    print(f"  H2 share of regulation scoring: "
          f"{100*w['h2'].sum()/(w['h1'].sum()+w['h2'].sum()):.2f}%")
    print(f"  Q4 vs Q1: {w['q4'].mean()-w['q1'].mean():+.2f}   "
          f"Q4 vs Q3: {w['q4'].mean()-w['q3'].mean():+.2f}")

    print("\n" + "=" * 92)
    print("D. Is the H1/H2 asymmetry symmetric between teams?")
    print("=" * 92)
    hv = (w["home_p1"] + w["home_p2"]).mean(), (w["home_p3"] + w["home_p4"]).mean()
    av = (w["vis_p1"] + w["vis_p2"]).mean(), (w["vis_p3"] + w["vis_p4"]).mean()
    print(f"  HOME  H1 {hv[0]:.2f}  H2 {hv[1]:.2f}  diff {hv[1]-hv[0]:+.2f}")
    print(f"  AWAY  H1 {av[0]:.2f}  H2 {av[1]:.2f}  diff {av[1]-av[0]:+.2f}")
    print("  A bench-side effect applying to both teams predicts equal, "
          "positive diffs.")

    print("\n" + "=" * 92)
    print("Stability by season")
    print("=" * 92)
    s = w.groupby("season").apply(lambda x: pd.Series({
        "n": len(x), "H1": round(x["h1"].mean(), 2), "H2": round(x["h2"].mean(), 2),
        "H1-H2": round((x["h1"] - x["h2"]).mean(), 2),
        "H2 share %": round(100 * x["h2"].sum() / (x["h1"].sum() + x["h2"].sum()), 2)}),
        include_groups=False)
    print(s.to_string())

    print("\n" + "=" * 92)
    print("B. Does the book's LIVE 2H line reflect the asymmetry?")
    print("=" * 92)
    from prepare_data import CSV, season_label
    raw = pd.read_csv(CSV, low_memory=False)
    raw["season_l"] = season_label(raw).astype(str)
    raw = raw[raw["season_l"].str.contains("Regular Season", na=False)].copy()
    raw["gid"] = raw["GAME-ID"].astype(str).str.zfill(10)
    raw["pre"] = pd.to_numeric(raw["CLOSING TOTAL_H"], errors="coerce")
    a = pd.to_numeric(raw["HALFTIME_H"], errors="coerce")
    b = pd.to_numeric(raw["HALFTIME_R"], errors="coerce")
    raw["h2_line"] = np.where(a.between(80, 160), a,
                              np.where(b.between(80, 160), b, np.nan))
    m = raw[["gid", "pre", "h2_line"]].dropna().merge(w, on="gid", how="inner")
    print(f"  {len(m):,} games with both a pregame total and a 2H line")
    print(f"  mean pregame total   {m['pre'].mean():.2f}")
    print(f"  mean 2H line         {m['h2_line'].mean():.2f}   "
          f"= {100*m['h2_line'].mean()/m['pre'].mean():.2f}% of pregame")
    print(f"  mean ACTUAL H2 (reg) {m['h2'].mean():.2f}   "
          f"= {100*m['h2'].mean()/m['pre'].mean():.2f}% of pregame")
    print(f"  mean ACTUAL H1       {m['h1'].mean():.2f}")
    print(f"\n  If the book halved the pregame total it would post "
          f"{m['pre'].mean()/2:.2f}; it posts {m['h2_line'].mean():.2f}, i.e. "
          f"{m['h2_line'].mean()-m['pre'].mean()/2:+.2f} vs naive halving.")
    print(f"  Actual H2 sits {m['h2'].mean()-m['pre'].mean()/2:+.2f} vs naive "
          f"halving, so the book's adjustment is "
          f"{'IN THE RIGHT DIRECTION' if np.sign(m['h2_line'].mean()-m['pre'].mean()/2)==np.sign(m['h2'].mean()-m['pre'].mean()/2) else 'BACKWARDS'}.")


if __name__ == "__main__":
    main()
