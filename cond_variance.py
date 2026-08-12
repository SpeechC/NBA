"""Conditional variance around discrete states -- Stage 1 and Stage 2.

Not generic variance modelling, which already failed. The hypothesis is that
variance is elevated around DISCRETE disruptions, and that the derived market
does not reflect it.

STATES, pre-specified:
    S1 lineup disruption   share of recent scoring newly absent (>=15% players)
    S2 style clash         |pace_home - pace_away|, both lagged
    S3 roster churn        distinct players used, averaged over the PRIOR 5
                           games -- lagged. A first version counted players used
                           in the CURRENT game, which is a consequence of the
                           result (blowouts empty the bench) and produced a
                           spurious sd(ATS) of 18.50 and a +9.07pp moneyline
                           error in the top quartile.

TARGET. Margin variance is the one distributional quantity with a live market
here: given a spread, higher outcome variance means more upsets, so the FAVOURITE
should win less often than the spread implies. The moneyline therefore prices
margin variance whether or not the book models it explicitly.

STAGE 1 (sports reality, no lines)
    (margin + spread)^2 = a + b*S          does the state raise ATS dispersion?
    require: coefficient, monotone buckets, plausible mechanism

STAGE 2 (contact with the market)
    favourite_won - P_implied(favourite) = a + b*S

    If the moneyline already reflects the elevated variance, b ~ 0 and we stop.
    If b < 0 for a variance-raising state, favourites win less than priced in
    exactly the states where variance is higher -- an exploitable distributional
    error.

STAGE 3 is not attempted unless Stage 2 survives.
"""
import warnings

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")


def build():
    from discontinuity import discontinuity
    from prepare_data import CSV, season_label

    D = discontinuity()
    raw = pd.read_csv(CSV, low_memory=False)
    raw["lbl"] = season_label(raw).astype(str)
    d = raw[raw["lbl"].str.contains("Regular Season", na=False)].copy()
    n = lambda c: pd.to_numeric(d[c], errors="coerce")
    d["gid"] = d["GAME-ID"].astype(str).str.zfill(10)
    d["date"] = pd.to_datetime(d["DATE"], errors="coerce")
    d["spread"] = n("CLOSING SPREAD_H")
    d["total"] = n("CLOSING TOTAL_H")
    d["mlh"], d["mla"] = n("MONEYLINE_H"), n("MONEYLINE_R")
    d["margin"] = d["PTS_H"] - d["PTS_R"]
    d["actual"] = d["PTS_H"] + d["PTS_R"]
    d = d.dropna(subset=["spread", "total", "mlh", "mla", "margin"])
    d = d[d["total"].between(150, 300)].copy()

    d["ats"] = d["margin"] + d["spread"]
    d["ats2"] = d["ats"] ** 2
    d["tot_resid2"] = (d["actual"] - d["total"]) ** 2
    ph = np.where(d["mlh"] < 0, -d["mlh"] / (-d["mlh"] + 100),
                  100 / (d["mlh"] + 100))
    pa = np.where(d["mla"] < 0, -d["mla"] / (-d["mla"] + 100),
                  100 / (d["mla"] + 100))
    d["p_home"] = ph / (ph + pa)
    d = d[(d["p_home"] > 0.03) & (d["p_home"] < 0.97)]
    d["fav_home"] = d["spread"] < 0
    d["p_fav"] = np.where(d["fav_home"], d["p_home"], 1 - d["p_home"])
    d["fav_won"] = np.where(d["fav_home"], d["margin"] > 0, d["margin"] < 0)
    d["ml_err"] = d["fav_won"].astype(float) - d["p_fav"]

    # S1 lineup disruption
    tm = pd.read_csv("team_mapping.csv")
    tid = dict(zip(tm["bigdataball_name"], tm["team_id"]))
    d["tid_h"], d["tid_a"] = d["TEAM_H"].map(tid), d["TEAM_R"].map(tid)
    d = d.merge(D.rename(columns={"team": "tid_h", "new_out": "out_h"})
                [["gid", "tid_h", "out_h"]], on=["gid", "tid_h"], how="left")
    d = d.merge(D.rename(columns={"team": "tid_a", "new_out": "out_a"})
                [["gid", "tid_a", "out_a"]], on=["gid", "tid_a"], how="left")
    d["S1"] = d["out_h"].fillna(0) + d["out_a"].fillna(0)

    # S2 style clash and S3 roster churn, both lagged
    from poss_vs_eff import quarter_poss
    qp = quarter_poss().groupby("gid")["poss"].sum().rename("poss").reset_index()
    d = d.merge(qp, on="gid", how="left")
    rows = []
    for side in ("H", "R"):
        rows.append(pd.DataFrame({"gid": d["gid"], "lbl": d["lbl"],
                                  "date": d["date"], "team": d[f"TEAM_{side}"],
                                  "poss": d["poss"]}))
    L = pd.concat(rows).sort_values("date")
    L["pace5"] = (L.groupby(["lbl", "team"])["poss"]
                  .transform(lambda s: s.shift(1).rolling(5, min_periods=3).mean()))
    d = d.merge(L[L.index.isin(L.index)][["gid", "team", "pace5"]]
                .rename(columns={"team": "TEAM_H", "pace5": "pace_h"}),
                on=["gid", "TEAM_H"], how="left")
    d = d.merge(L[["gid", "team", "pace5"]]
                .rename(columns={"team": "TEAM_R", "pace5": "pace_a"}),
                on=["gid", "TEAM_R"], how="left")
    d["S2"] = (d["pace_h"] - d["pace_a"]).abs()

    pg = pd.read_parquet("/home/dpope/data/player_game_pts.parquet")
    used = pg.groupby(["gid", "team"])["pid"].nunique().rename("nplay").reset_index()
    used = used.merge(d[["gid", "date", "lbl"]].drop_duplicates("gid"),
                      on="gid", how="inner").sort_values("date")
    # LAGGED: mean distinct players over the prior 5 games, strictly before this
    used["churn5"] = (used.groupby(["lbl", "team"])["nplay"]
                      .transform(lambda s: s.shift(1)
                                 .rolling(5, min_periods=3).mean()))
    k = used[["gid", "team", "churn5"]]
    d = d.merge(k.rename(columns={"team": "tid_h", "churn5": "np_h"}),
                on=["gid", "tid_h"], how="left")
    d = d.merge(k.rename(columns={"team": "tid_a", "churn5": "np_a"}),
                on=["gid", "tid_a"], how="left")
    d["S3"] = d["np_h"] + d["np_a"]
    return d


def stage(d, S, lab):
    s = d.dropna(subset=[S, "ats2", "ml_err"])
    print(f"\n--- {lab}   (n={len(s):,}, mean {s[S].mean():.3f}, "
          f"sd {s[S].std():.3f}) ---")
    for tgt, tl in (("ats2", "STAGE 1  ATS squared error"),
                    ("tot_resid2", "STAGE 1  total squared error"),
                    ("ml_err", "STAGE 2  moneyline error")):
        x, y = s[S].values, s[tgt].values
        r = np.corrcoef(x, y)[0, 1]
        b = np.polyfit(x, y, 1)[0]
        t = r * np.sqrt(len(x) - 2) / np.sqrt(1 - r * r)
        print(f"  {tl:32} slope {b:+.4f}  corr {r:+.4f}  t={t:+.2f}")
    q = pd.qcut(s[S].rank(method="first"), 4, labels=[1, 2, 3, 4])
    print("    quartiles:  " + "   ".join(
        f"Q{i}: sd(ats) {g['ats'].std():5.2f}  MLerr {100*g['ml_err'].mean():+5.2f}pp"
        for i, g in s.groupby(q, observed=True)))


def main():
    d = build()
    print(f"{len(d):,} games with spread, total, moneyline and states")
    print(f"  overall sd(ATS) {d['ats'].std():.2f}   "
          f"mean ML error {100*d['ml_err'].mean():+.2f}pp")
    print("=" * 92)
    print("CONDITIONAL VARIANCE BY DISCRETE STATE")
    print("=" * 92)
    stage(d, "S1", "S1 lineup disruption")
    stage(d, "S2", "S2 style clash (|pace difference|)")
    stage(d, "S3", "S3 roster churn (players used)")


if __name__ == "__main__":
    main()
