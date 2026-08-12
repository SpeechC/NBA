"""Is the live 2H total a mechanical formula that ignores blowout collapse?

A Type-4 hypothesis in the taxonomy: correct full-game valuation translated too
simplistically into a derivative market. This is the structure Voulgaris
reportedly attacked, one level below the primary market.

The mechanism, stated so it can fail:

  A book setting a second-half total at halftime has seconds and a rule --
  roughly, pregame expectation minus what has already happened, nudged by
  first-half pace. What it cannot do in that time is model the CONDITIONAL
  distribution of the second half, which is bimodal. Competitive games keep
  scoring. Blowouts collapse: starters sit, possessions lengthen, nobody fouls
  to stop the clock. If the 2H total is a smooth function of pace and score, it
  will systematically OVERPRICE second halves in games likely to become
  blowouts.

Three steps, in order, because step 2 is meaningless without step 1:

  1. RECOVER THE BOOK'S RULE. Regress the 2H line on the inputs a mechanical
     rule would use. A high R^2 IS the finding: it demonstrates the line is a
     formula rather than a per-game judgement.
  2. FIND WHAT THE RULE OMITS. Does halftime margin enter the line? If the
     coefficient is near zero, the book is not pricing blowout risk.
  3. TEST WHETHER THE OMISSION PAYS. Does |halftime margin| predict the residual
     (2H actual - 2H line)? Under-bias in blowout-likely games is the edge.

Then the standard controls: by-season decay, permutation, and break-even.

⚠ 2H line coverage is uneven -- 91% in 2017-19, ~0% in 2020-21, 12% in 2021-22,
70-74% thereafter. Play-by-play stops at 2024-25, so 2025-26 cannot be used.
"""
import warnings

import duckdb
import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")
RNG = np.random.default_rng(0)

PBP = "/home/dpope/data/pbp_lineups_all.parquet"


def halftime_scores():
    """Score at the end of period 2. SCORE is 'visitor - home'."""
    con = duckdb.connect()
    q = f"""
    WITH s AS (
      SELECT lpad(CAST(GAME_ID AS VARCHAR),10,'0') AS gid,
             PERIOD, CAST(PCTIMESTRING AS INTEGER) AS t, SCORE,
             row_number() OVER (
               PARTITION BY GAME_ID
               ORDER BY PERIOD DESC, CAST(PCTIMESTRING AS INTEGER) DESC) AS rn
      FROM read_parquet('{PBP}')
      WHERE SEASON_TYPE='RegularSeason' AND PERIOD <= 2 AND SCORE IS NOT NULL
    )
    SELECT gid, SCORE FROM s WHERE rn = 1
    """
    d = con.execute(q).fetchdf()
    parts = d["SCORE"].str.split("-", expand=True)
    d["h1_vis"] = pd.to_numeric(parts[0].str.strip(), errors="coerce")
    d["h1_home"] = pd.to_numeric(parts[1].str.strip(), errors="coerce")
    d["h1_total"] = d["h1_vis"] + d["h1_home"]
    d["h1_margin"] = d["h1_home"] - d["h1_vis"]
    return d.dropna(subset=["h1_total"])[["gid", "h1_total", "h1_margin"]]


def load():
    from prepare_data import CSV, season_label
    raw = pd.read_csv(CSV, low_memory=False)
    raw["season"] = season_label(raw).astype(str)
    d = raw[raw["season"].str.contains("Regular Season", na=False)].copy()
    d["gid"] = d["GAME-ID"].astype(str).str.zfill(10)
    d["date"] = pd.to_datetime(d["DATE"], errors="coerce")
    d["pre_total"] = pd.to_numeric(d["CLOSING TOTAL_H"], errors="coerce")
    d["pre_spread"] = pd.to_numeric(d["CLOSING SPREAD_H"], errors="coerce")
    d["final_total"] = d["PTS_H"] + d["PTS_R"]

    # HALFTIME_H / HALFTIME_R hold the 2H total and 2H spread, swapped between
    # columns (same pattern as five other families -- see DATA_DICTIONARY.md).
    a = pd.to_numeric(d["HALFTIME_H"], errors="coerce")
    b = pd.to_numeric(d["HALFTIME_R"], errors="coerce")
    tot = np.where(a.between(80, 160), a, np.where(b.between(80, 160), b, np.nan))
    spr = np.where(a.between(-30, 30), a, np.where(b.between(-30, 30), b, np.nan))
    d["h2_line"] = tot
    d["h2_spread"] = spr

    d = d.merge(halftime_scores(), on="gid", how="inner")
    d["h2_actual"] = d["final_total"] - d["h1_total"]
    d["abs_h1_margin"] = d["h1_margin"].abs()
    d = d.dropna(subset=["h2_line", "h2_actual", "pre_total", "h1_total", "date"])
    d = d[d["h2_actual"].between(60, 180)]
    return d


def ols(y, X, names):
    X = np.c_[np.ones(len(y)), X]
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    yhat = X @ beta
    r2 = 1 - ((y - yhat) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    se = np.sqrt(np.diag(np.linalg.pinv(X.T @ X)) *
                 ((y - yhat) ** 2).sum() / (len(y) - X.shape[1]))
    return pd.DataFrame({"term": ["intercept"] + names,
                         "coef": beta.round(4), "se": se.round(4),
                         "t": (beta / se).round(2)}), r2


def main():
    d = load()
    print(f"{len(d):,} games with a 2H line and a halftime score")
    print(d.groupby("season").size().to_string())

    print("\n" + "=" * 92)
    print("STEP 1 — recover the book's rule for the 2H total")
    print("=" * 92)
    y = d["h2_line"].values
    tab, r2 = ols(y, np.c_[d["pre_total"], d["h1_total"]],
                  ["pre_total", "h1_total"])
    print(tab.to_string(index=False))
    print(f"  R^2 = {r2:.4f}")
    tab2, r22 = ols(y, np.c_[d["pre_total"], d["h1_total"], d["abs_h1_margin"]],
                    ["pre_total", "h1_total", "|h1_margin|"])
    print("\n  adding halftime margin:")
    print(tab2.to_string(index=False))
    print(f"  R^2 = {r22:.4f}   (gain {r22-r2:+.4f})")

    print("\n" + "=" * 92)
    print("STEP 2/3 — does the omission predict the residual?")
    print("=" * 92)
    d["resid"] = d["h2_actual"] - d["h2_line"]
    print(f"  overall 2H residual {d['resid'].mean():+.3f} "
          f"(sd {d['resid'].std():.2f}, t={d['resid'].mean()/(d['resid'].std()/np.sqrt(len(d))):+.2f})")
    d["band"] = pd.cut(d["abs_h1_margin"], [-1, 5, 10, 15, 20, 99],
                       labels=["0-5", "6-10", "11-15", "16-20", "21+"])
    rows = []
    for g, s in d.groupby("band", observed=True):
        r = s["resid"]
        se = r.std() / np.sqrt(len(r))
        under = (r < 0).mean()
        rows.append({"|halftime margin|": g, "n": len(s),
                     "mean 2H line": round(s["h2_line"].mean(), 2),
                     "mean 2H actual": round(s["h2_actual"].mean(), 2),
                     "residual": round(r.mean(), 3), "t": round(r.mean() / se, 2),
                     "under %": round(100 * under, 2),
                     "ROI under": round(100 * (under * (100 / 110) - (1 - under)), 2)})
    print(pd.DataFrame(rows).to_string(index=False))

    print("\n--- by season, |halftime margin| >= 16 ---")
    big = d[d["abs_h1_margin"] >= 16]
    print(big.groupby("season").apply(lambda x: pd.Series({
        "n": len(x), "residual": round(x["resid"].mean(), 3),
        "under %": round(100 * (x["resid"] < 0).mean(), 2)}),
        include_groups=False).to_string())

    print("\n--- permutation: shuffle the margin labels ---")
    obs = big["resid"].mean()
    pool = d["resid"].values
    null = np.array([RNG.choice(pool, len(big), replace=False).mean()
                     for _ in range(4000)])
    print(f"  observed {obs:+.3f}   null {null.mean():+.3f} +/- {null.std():.3f}"
          f"   percentile {100*np.mean(null < obs):.1f}")
    d.to_csv("half_totals_games.csv", index=False)


if __name__ == "__main__":
    main()
