"""Do large betting markets skew the lines?

Hypothesis: teams with huge followings (New York, Boston, the Lakers) attract
disproportionate public money, pushing their lines away from fair value.

There are two distinct claims inside that, and they have different consequences:

  A. OUTCOME BIAS — the closing line over-favours big-market teams, so they fail
     to cover. If true, fade them at the close. This is the classic "bet against
     the public" claim; it was documented in the 1980s-90s literature and has had
     three decades to be arbitraged away.

  B. FLOW BIAS — the line MOVES toward big-market teams between open and close as
     public money arrives. If true, you take the big-market side at the opener and
     collect CLV, *without predicting the game at all*. This can be true even when
     A is false: the move can be fully justified, in which case you capture the
     value but the market was never wrong.

B is the interesting one here, because the only live signal in this project is a
line-movement signal, and this would be an independent source of the same thing.

Market size is measured by metro population — objective, external, and fixed
before looking at any outcome. It is a proxy for betting handle, not a measure of
it. A judgment-based "popular teams" list would be a researcher degree of freedom,
so any such ranking below is reported as descriptive only, never as a test.
"""

import numpy as np
import pandas as pd
from scipy import stats

ODDS = "/home/dpope/data/dfMaster_OT.parquet"

# metro population, millions (2020 census metro areas; Toronto CMA)
METRO = {
    "New York": 19.5, "Brooklyn": 19.5, "LA Lakers": 13.0, "LA Clippers": 13.0,
    "Chicago": 9.5, "Dallas": 7.6, "Houston": 7.1, "Toronto": 6.2,
    "Washington": 6.3, "Philadelphia": 6.1, "Atlanta": 6.1, "Miami": 6.1,
    "Phoenix": 5.0, "Boston": 4.9, "Golden State": 4.7, "Detroit": 4.4,
    "Minnesota": 3.7, "Denver": 3.0, "Charlotte": 2.7, "Orlando": 2.7,
    "San Antonio": 2.6, "Portland": 2.5, "Sacramento": 2.4, "Cleveland": 2.1,
    "Indiana": 2.1, "Milwaukee": 1.6, "Oklahoma City": 1.4, "Utah": 1.3,
    "New Orleans": 1.3, "Memphis": 1.3,
}


def load():
    o = pd.read_parquet(ODDS)
    o["season"] = o["DATASET_H"].fillna(o["BIGDATABALL\nDATASET_H"])
    r = o[o["season"].str.contains("Regular Season|In-Season", na=False)].copy()
    r["date"] = pd.to_datetime(r["DATE"])

    cs = pd.to_numeric(r["CLOSING SPREAD_H"], errors="coerce")
    os_ = pd.to_numeric(r["OPENING SPREAD_H"], errors="coerce")
    ct = pd.to_numeric(r["CLOSING TOTAL_H"], errors="coerce")
    ot = pd.to_numeric(r["OPENING TOTAL_H"], errors="coerce")
    ok = (cs.abs() <= 25) & (os_.abs() <= 25) & ct.between(150, 300) & ot.between(150, 300)
    r = r[ok].copy()

    r["close_margin"] = -cs[ok]
    r["open_margin"] = -os_[ok]
    r["close_total"] = ct[ok]
    r["open_total"] = ot[ok]
    q = [f"{i}Q_{s}" for i in (1, 2, 3, 4) for s in ("H", "R")]
    for c in q:
        r[c] = pd.to_numeric(r[c], errors="coerce")
    otc = [f"OT{i}_{s}" for i in range(1, 6) for s in ("H", "R")]
    r["otp"] = sum(pd.to_numeric(r[c], errors="coerce").fillna(0) for c in otc)
    r["actual_margin"] = (pd.to_numeric(r["PTS_H"], errors="coerce")
                          - pd.to_numeric(r["PTS_R"], errors="coerce"))
    r["actual_total"] = (pd.to_numeric(r["PTS_H"], errors="coerce")
                         + pd.to_numeric(r["PTS_R"], errors="coerce"))

    r["pop_h"] = r["TEAM_H"].map(METRO)
    r["pop_a"] = r["TEAM_R"].map(METRO)
    r = r.dropna(subset=["pop_h", "pop_a", "actual_margin", "close_margin"])

    # log population differential: home minus away
    r["pop_diff"] = np.log(r["pop_h"]) - np.log(r["pop_a"])
    r["pop_sum"] = np.log(r["pop_h"]) + np.log(r["pop_a"])
    r["excess_margin"] = r["actual_margin"] - r["close_margin"]
    r["excess_total"] = r["actual_total"] - r["close_total"]
    r["move_margin"] = r["close_margin"] - r["open_margin"]
    r["move_total"] = r["close_total"] - r["open_total"]
    return r


def ols(y, X, names):
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    res = y - X @ coef
    dof = len(y) - X.shape[1]
    s2 = float(res @ res) / dof
    se = np.sqrt(np.diag(s2 * np.linalg.inv(X.T @ X)))
    t = coef / se
    return pd.DataFrame({"coef": coef, "se": se, "t": t,
                         "p": 2 * (1 - stats.t.cdf(np.abs(t), dof))}, index=names)


def main():
    r = load()
    n = len(r)
    print(f"games: {n:,}   metro population range "
          f"{min(METRO.values()):.1f}m .. {max(METRO.values()):.1f}m\n")

    one = np.ones(n)
    print("=== TEST A: does the CLOSING line over-favour big markets? ===")
    print("excess margin (actual - closing) ~ log population differential\n")
    print(ols(r["excess_margin"].values,
              np.column_stack([one, r["pop_diff"]]),
              ["const", "log pop diff (home-away)"]).round(4).to_string())
    print("\nexcess total (actual - closing) ~ combined log population\n")
    print(ols(r["excess_total"].values,
              np.column_stack([one, r["pop_sum"]]),
              ["const", "combined log pop"]).round(4).to_string())

    print("\n=== TEST B: does the line MOVE toward big markets? ===")
    print("spread move (close - open) ~ log population differential\n")
    print(ols(r["move_margin"].values,
              np.column_stack([one, r["pop_diff"]]),
              ["const", "log pop diff (home-away)"]).round(4).to_string())
    print("\ntotal move (close - open) ~ combined log population\n")
    print(ols(r["move_total"].values,
              np.column_stack([one, r["pop_sum"]]),
              ["const", "combined log pop"]).round(4).to_string())

    print("\n=== quintiles of population differential ===")
    r["q"] = pd.qcut(r["pop_diff"], 5, labels=["away much bigger", "2", "even",
                                               "4", "home much bigger"])
    t = r.groupby("q", observed=True).agg(
        n=("excess_margin", "size"),
        excess_margin=("excess_margin", "mean"),
        spread_move=("move_margin", "mean"),
        home_cover_pct=("excess_margin", lambda s: 100 * (s > 0).mean()))
    print(t.round(3).to_string())

    print("\n=== descriptive only: which teams do lines move toward? ===")
    rows = []
    for team in sorted(METRO):
        h = r[r["TEAM_H"] == team]
        a = r[r["TEAM_R"] == team]
        if len(h) + len(a) < 200:
            continue
        # movement toward this team, whichever side it is on
        mv = np.concatenate([h["move_margin"].to_numpy(),
                             -a["move_margin"].to_numpy()])
        ex = np.concatenate([h["excess_margin"].to_numpy(),
                             -a["excess_margin"].to_numpy()])
        rows.append({"team": team, "pop": METRO[team], "n": len(mv),
                     "line moves toward": mv.mean(),
                     "beats the close by": ex.mean()})
    d = pd.DataFrame(rows).sort_values("line moves toward", ascending=False)
    print(d.round(3).to_string(index=False))
    print(f"\ncorr(metro population, line moves toward team) = "
          f"{d['pop'].corr(d['line moves toward']):+.3f}")
    print(f"corr(line moves toward, beats the close)       = "
          f"{d['line moves toward'].corr(d['beats the close by']):+.3f}")


if __name__ == "__main__":
    main()
