"""Audit the betting-line data, because it is the benchmark every result rests on.

If the "closing line" in this file is not really a closing line -- wrong timestamp,
a soft book, a stale quote, a consensus of mixed vintages -- then every conclusion
in the project is measured against the wrong yardstick, and the direction of the
error is not obvious. A weak benchmark would make us look BETTER than we are, not
worse, so the nulls would survive; but the movement signal would be suspect.

Seven checks, each of which a real market must pass:

  1. increments      spreads and totals should sit on half-point ticks
  2. no duplicates   one line per game
  3. efficiency      ATS and over/under should land near 50%
  4. close > open    the closing line must be the more accurate one
  5. coherence       the moneyline and the spread must imply the same win prob
  6. home advantage  the average home spread should be ~2-3 points
  7. favourite bias  check for the classic favourite-longshot distortion
"""

import numpy as np
import pandas as pd
from scipy import stats

ODDS = "/home/dpope/data/dfMaster_OT.parquet"


def load():
    o = pd.read_parquet(ODDS)
    o["season"] = o["DATASET_H"].fillna(o["BIGDATABALL\nDATASET_H"])
    r = o[o["season"].str.contains("Regular Season|In-Season", na=False)].copy()
    r["gid"] = (r["GAME-ID"].astype(str)
                .str.replace(r"\.0$", "", regex=True).str.zfill(10))
    for a, b in (("cs", "CLOSING SPREAD_H"), ("os", "OPENING SPREAD_H"),
                 ("ct", "CLOSING TOTAL_H"), ("ot", "OPENING TOTAL_H"),
                 ("mlh", "MONEYLINE_H"), ("mlr", "MONEYLINE_R")):
        r[a] = pd.to_numeric(r[b], errors="coerce")
    r["pts_h"] = pd.to_numeric(r["PTS_H"], errors="coerce")
    r["pts_r"] = pd.to_numeric(r["PTS_R"], errors="coerce")
    r["margin"] = r["pts_h"] - r["pts_r"]
    r["total"] = r["pts_h"] + r["pts_r"]
    return r


def main():
    r = load()
    print(f"rows: {len(r):,}\n")

    print("=== 1. INCREMENTS (should be half-point ticks) ===")
    for c, lab in (("cs", "closing spread"), ("os", "opening spread"),
                   ("ct", "closing total"), ("ot", "opening total")):
        v = r[c].dropna()
        bad = (np.abs(v * 2 - np.round(v * 2)) > 1e-6).sum()
        oor = ((v.abs() > 30) if "spread" in lab else ~v.between(150, 300)).sum()
        print(f"  {lab:16} n={len(v):5d}  off-tick {bad:4d}  out-of-range {oor:4d}"
              f"  range {v.min():.1f}..{v.max():.1f}")

    print("\n=== 2. DUPLICATES ===")
    d = r["gid"].duplicated().sum()
    print(f"  duplicate game ids: {d}")

    print("\n=== 3. EFFICIENCY: should be near 50% ===")
    ok = (r["cs"].abs() <= 25) & r["ct"].between(150, 300)
    g = r[ok]
    ats = (g["margin"] + g["cs"]).dropna()
    ou = (g["total"] - g["ct"]).dropna()
    for lab, s in (("home ATS cover", ats), ("over", ou)):
        nz = s[s != 0]
        p = (nz > 0).mean()
        z = (p - 0.5) / np.sqrt(0.25 / len(nz))
        print(f"  {lab:16} {100 * p:.2f}%  (n={len(nz):,}, z vs 50% = {z:+.2f})")

    print("\n=== 4. CLOSING SHOULD BEAT OPENING ===")
    m = ok & r["os"].abs().le(25) & r["ot"].between(150, 300)
    s = r[m]
    for lab, close, open_ in (("margin", -s["cs"], -s["os"]),
                              ("total", s["ct"], s["ot"])):
        act = s["margin"] if lab == "margin" else s["total"]
        rc = float(np.sqrt(np.mean((close - act) ** 2)))
        ro = float(np.sqrt(np.mean((open_ - act) ** 2)))
        flag = "OK" if rc < ro else "*** PROBLEM ***"
        print(f"  {lab:8} closing RMSE {rc:.3f} vs opening {ro:.3f}   {flag}")

    print("\n=== 5. COHERENCE: moneyline vs spread ===")
    def amp(x):
        return np.where(x < 0, -x / (-x + 100), 100 / (x + 100))
    c = s.dropna(subset=["mlh", "mlr"]).copy()
    ph, pa = amp(c["mlh"].values), amp(c["mlr"].values)
    c["p_ml"] = ph / (ph + pa)                      # de-vigged
    sd = float((c["margin"] + c["cs"]).std())
    c["p_spread"] = stats.norm.cdf(-c["cs"] / sd)   # spread -> win prob
    diff = c["p_ml"] - c["p_spread"]
    print(f"  n={len(c):,}  mean |disagreement| {100 * diff.abs().mean():.2f} pp"
          f"  correlation {c['p_ml'].corr(c['p_spread']):.4f}")
    print(f"  games where they disagree by >10pp: {(diff.abs() > .10).sum()} "
          f"({100 * (diff.abs() > .10).mean():.2f}%)")
    print(f"  implied hold from the two moneylines: {100 * (ph + pa - 1).mean():.2f}%")

    print("\n=== 6. HOME ADVANTAGE ===")
    print(f"  mean closing spread (home): {-s['cs'].mean():+.3f}  "
          f"median {-s['cs'].median():+.2f}")
    print(f"  actual mean home margin   : {s['margin'].mean():+.3f}")
    print(f"  home win rate             : {100 * (s['margin'] > 0).mean():.2f}%")

    print("\n=== 7. FAVOURITE-LONGSHOT BIAS (moneyline) ===")
    c["bucket"] = pd.cut(c["p_ml"], [0, .3, .4, .5, .6, .7, .8, 1.0])
    t = c.groupby("bucket", observed=True).apply(
        lambda x: pd.Series({"n": len(x), "implied %": 100 * x["p_ml"].mean(),
                             "actual %": 100 * (x["margin"] > 0).mean()}),
        include_groups=False)
    t["gap pp"] = t["actual %"] - t["implied %"]
    print(t.round(2).to_string())
    print("\n  (a monotone gap would indicate favourite-longshot distortion;"
          " noise around zero is what a clean two-way market looks like)")


if __name__ == "__main__":
    main()
