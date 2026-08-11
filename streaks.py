"""Streaks: two pre-registered tests, reported either way.

Framing matters here. "Do streaking teams keep winning?" is already answered by
everything else in this project -- team form is exactly what our lagged ratings
measure, and they add nothing against the closing line. The version still open is
different:

  A streak is the single most visible narrative in sports betting, so it is a
  free proxy for public money. Our only live signal is line movement, which is
  literally a record of money flow. So streaks are tested as a FLOW variable, not
  as a basketball variable.

Two tests, run once:

  1. OVERREACTION — does the closing line overprice streaking teams? A negative
     coefficient on the streak differential means fade them. There is old academic
     precedent (Camerer 1989; Brown & Sauer 1993) for NBA spreads overpricing
     streaks, but that is 35 years of arbitrage ago.
  2. FLOW — do streak features add CLV to the totals-movement model, against its
     +0.588 baseline?

Three streak flavours, all computed walk-forward within season and shifted so they
describe the state ENTERING the game:
    win streak  ·  against-the-spread streak  ·  over/under streak
"""

import numpy as np
import pandas as pd
from scipy import stats

ODDS = "/home/dpope/data/dfMaster_OT.parquet"


def signed_streak(outcomes):
    """+n after n consecutive wins, -n after n consecutive losses; ties reset."""
    out = np.zeros(len(outcomes))
    run = 0
    for i, o in enumerate(outcomes):
        out[i] = run
        if np.isnan(o):
            run = 0
        elif o > 0:
            run = run + 1 if run > 0 else 1
        elif o < 0:
            run = run - 1 if run < 0 else -1
        else:
            run = 0
    return out


def build():
    o = pd.read_parquet(ODDS)
    o["season"] = o["DATASET_H"].fillna(o["BIGDATABALL\nDATASET_H"])
    r = o[o["season"].str.contains("Regular Season|In-Season", na=False)].copy()
    r["date"] = pd.to_datetime(r["DATE"])
    cs = pd.to_numeric(r["CLOSING SPREAD_H"], errors="coerce")
    ct = pd.to_numeric(r["CLOSING TOTAL_H"], errors="coerce")
    ot_ = pd.to_numeric(r["OPENING TOTAL_H"], errors="coerce")
    ok = (cs.abs() <= 25) & ct.between(150, 300) & ot_.between(150, 300)
    r = r[ok].copy()
    r["close_margin"] = -cs[ok]
    r["close_total"] = ct[ok]
    r["open_total"] = ot_[ok]
    r["actual_margin"] = (pd.to_numeric(r["PTS_H"], errors="coerce")
                          - pd.to_numeric(r["PTS_R"], errors="coerce"))
    r["actual_total"] = (pd.to_numeric(r["PTS_H"], errors="coerce")
                         + pd.to_numeric(r["PTS_R"], errors="coerce"))
    r["gid"] = (r["GAME-ID"].astype(str)
                .str.replace(r"\.0$", "", regex=True).str.zfill(10))
    r = r.dropna(subset=["actual_margin", "close_margin", "close_total"])

    from team_mapping import NAME_TO_ID
    sides = []
    for suf, sign in (("H", 1), ("R", -1)):
        sides.append(pd.DataFrame({
            "gid": r["gid"], "date": r["date"], "season": r["season"],
            "team": r[f"TEAM_{suf}"].map(NAME_TO_ID), "is_home": suf == "H",
            "win": sign * r["actual_margin"],
            "ats": sign * (r["actual_margin"] - r["close_margin"]),
            "ou": r["actual_total"] - r["close_total"]}))
    p = pd.concat(sides, ignore_index=True).dropna(subset=["team"])
    p = p.sort_values(["season", "team", "date"]).reset_index(drop=True)
    for c in ("win", "ats", "ou"):
        p[f"st_{c}"] = (p.groupby(["season", "team"])[c]
                        .transform(lambda s: signed_streak(s.to_numpy())))

    h = p[p["is_home"]].set_index("gid")[["st_win", "st_ats", "st_ou"]].add_prefix("h_")
    a = p[~p["is_home"]].set_index("gid")[["st_win", "st_ats", "st_ou"]].add_prefix("a_")
    G = r.set_index("gid").join(h).join(a).dropna(
        subset=["h_st_win", "a_st_win"]).reset_index()
    G["excess_margin"] = G["actual_margin"] - G["close_margin"]
    G["excess_total"] = G["actual_total"] - G["close_total"]
    G["move_total"] = G["close_total"] - G["open_total"]
    for c in ("win", "ats", "ou"):
        G[f"d_{c}"] = G[f"h_st_{c}"] - G[f"a_st_{c}"]
        G[f"s_{c}"] = G[f"h_st_{c}"] + G[f"a_st_{c}"]
    return G


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
    G = build()
    n = len(G)
    one = np.ones(n)
    print(f"games: {n:,}   win-streak range {G['h_st_win'].min():.0f} .. "
          f"{G['h_st_win'].max():.0f}\n")

    print("=== TEST 1: OVERREACTION — does the close overprice streaking teams? ===")
    print("excess margin (actual - closing) ~ streak differential (home - away)\n")
    print(ols(G["excess_margin"].values,
              np.column_stack([one, G["d_win"], G["d_ats"]]),
              ["const", "win-streak diff", "ATS-streak diff"]).round(4).to_string())
    print("\nexcess total ~ combined over/under streak\n")
    print(ols(G["excess_total"].values,
              np.column_stack([one, G["s_ou"]]),
              ["const", "combined O/U streak"]).round(4).to_string())

    print("\n=== ATS cover rate by win-streak differential ===")
    G["q"] = pd.cut(G["d_win"], [-99, -4, -2, -0.5, 0.5, 2, 4, 99],
                    labels=["away hot 4+", "away 3-4", "away 1-2", "even",
                            "home 1-2", "home 3-4", "home hot 4+"])
    t = G.groupby("q", observed=True).agg(
        n=("excess_margin", "size"),
        home_cover_pct=("excess_margin", lambda s: 100 * (s > 0).mean()),
        mean_excess=("excess_margin", "mean"))
    print(t.round(2).to_string())

    print("\n=== over rate by combined over/under streak ===")
    G["qo"] = pd.cut(G["s_ou"], [-99, -4, -1, 1, 4, 99],
                     labels=["both under-ish", "under lean", "neutral",
                             "over lean", "both over-ish"])
    t2 = G.groupby("qo", observed=True).agg(
        n=("excess_total", "size"),
        over_pct=("excess_total", lambda s: 100 * (s > 0).mean()),
        mean_excess=("excess_total", "mean"),
        mean_move=("move_total", "mean"))
    print(t2.round(2).to_string())
    G.to_parquet("/home/dpope/data/streaks.parquet", index=False)


if __name__ == "__main__":
    main()
