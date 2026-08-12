"""Do the departed-star and end-of-season signals share one mechanism?

Two results, in DIFFERENT markets:

  §19  teams playing after their star's final appearance cover only 44.07% ATS
       -- fading them wins 55.93%, 7 of 7 seasons below 50%
  §21  the last 7 days of a season go over 55.87%

Both were explained as organisational disengagement: teams stop competing, rest
veterans, play out the string. If that single mechanism is real it makes four
predictions, and the point of testing them jointly is that a shared cause has to
show up in both markets, not just be assertable about each.

  P1 OVERLAP      departed-star games concentrate late in the season
  P2 INTERACTION  the ATS effect STRENGTHENS late -- a team that lost its star
                  in December is differently motivated in January than in April
  P3 CROSS-MARKET departed-star games also go OVER. §19 found star-out totals
                  null, but that pooled temporary absences with departures; only
                  departures imply disengagement.
  P4 ADDITIVE     stacking markers beats either alone

P3 is the real test. If disengagement raises scoring, it must raise it in the
games where disengagement is measured directly -- not only in games that happen
to fall in April. A calendar effect that does not appear in the roster-based
measure is a calendar effect, not a disengagement effect.

⚠ Play-by-play stops at 2024-25, so departed-star flags cannot cover 2025-26.
"""
import warnings

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")
RNG = np.random.default_rng(0)

from ewing import (DEFINE_WINDOW, MIN_APPEARANCES, build_player_games,
                   home_team_map)

BE = 110 / 210


def panel():
    pg = build_player_games()
    hm = home_team_map()
    from prepare_data import CSV, season_label
    raw = pd.read_csv(CSV, low_memory=False)
    raw["season"] = season_label(raw).astype(str)
    raw = raw[raw["season"].str.contains("Regular Season", na=False)].copy()
    raw["gid"] = raw["GAME-ID"].astype(str).str.zfill(10)
    raw["date"] = pd.to_datetime(raw["DATE"], errors="coerce")
    raw["close_spread"] = pd.to_numeric(raw["CLOSING SPREAD_H"], errors="coerce")
    raw["close_total"] = pd.to_numeric(raw["CLOSING TOTAL_H"], errors="coerce")
    games = raw.dropna(subset=["date", "close_spread", "close_total",
                               "PTS_H", "PTS_R"])
    games = games[["gid", "date", "season", "PTS_H", "PTS_R",
                   "close_spread", "close_total"]].drop_duplicates("gid")
    games["days_left"] = (games.groupby("season")["date"].transform("max")
                          - games["date"]).dt.days
    games["home_cover"] = (games["PTS_H"] - games["PTS_R"]) + games["close_spread"]
    games["tot_resid"] = (games["PTS_H"] + games["PTS_R"]) - games["close_total"]

    pg = pg.merge(games[["gid", "date"]], on="gid", how="inner").sort_values("date")
    tg = pg[["season", "team", "gid", "date"]].drop_duplicates().sort_values("date")
    tg["tg_idx"] = tg.groupby(["season", "team"]).cumcount()
    pg = pg.merge(tg[["season", "team", "gid", "tg_idx"]],
                  on=["season", "team", "gid"], how="left")

    early = pg[pg["tg_idx"] < DEFINE_WINDOW]
    cand = (early.groupby(["season", "team", "pid"])
                 .agg(apps=("pts", "size"), ppg=("pts", "mean")).reset_index())
    cand = cand[cand["apps"] >= MIN_APPEARANCES]
    star = (cand.sort_values("ppg", ascending=False)
                .groupby(["season", "team"], as_index=False).first())
    test = tg[tg["tg_idx"] >= DEFINE_WINDOW].merge(
        star[["season", "team", "pid"]], on=["season", "team"], how="inner")
    played = pg[["gid", "pid"]].drop_duplicates().assign(played=True)
    test = test.merge(played, on=["gid", "pid"], how="left")
    test["out"] = test["played"].isna()
    last = (test[~test["out"]].groupby(["season", "team"])["tg_idx"]
            .max().rename("last_app"))
    test = test.merge(last, on=["season", "team"], how="left")
    test["state"] = np.where(~test["out"], "present",
                             np.where(test["tg_idx"] > test["last_app"],
                                      "DEPARTED", "TEMP"))
    test = test.merge(hm, on=["gid", "team"], how="inner")
    H = test[test["is_home"]][["gid", "state"]].rename(columns={"state": "home"})
    A = test[~test["is_home"]][["gid", "state"]].rename(columns={"state": "away"})
    g = games.merge(H, on="gid").merge(A, on="gid")
    return g[g["home_cover"] != 0].copy()


def ats(x, lab):
    c = x["cov"]
    w = (c > 0).mean()
    se = np.sqrt(w * (1 - w) / len(x))
    return {"split": lab, "n": len(x), "fade wins %": round(100 * w, 2),
            "95% CI": f"[{100*(w-1.96*se):.1f}, {100*(w+1.96*se):.1f}]",
            "ROI110": round(100 * (w * (100 / 110) - (1 - w)), 2)}


def main():
    g = panel()
    print(f"{g['gid'].nunique():,} games, {g['season'].nunique()} seasons "
          f"({g['date'].min().date()} .. {g['date'].max().date()})\n")

    dep_h = (g["home"] == "DEPARTED") & (g["away"] == "present")
    dep_a = (g["away"] == "DEPARTED") & (g["home"] == "present")
    anydep = (g["home"] == "DEPARTED") | (g["away"] == "DEPARTED")

    print("=" * 96)
    print("P1 OVERLAP — are departed-star games late-season?")
    print("=" * 96)
    for lab, m in (("last 7 days", g["days_left"] <= 7),
                   ("last 14 days", g["days_left"] <= 14),
                   ("last 30 days", g["days_left"] <= 30),
                   ("rest of season", g["days_left"] > 30)):
        s = g[m]
        print(f"  {lab:16} n={len(s):5,}   departed present in "
              f"{100*((s['home']=='DEPARTED')|(s['away']=='DEPARTED')).mean():5.1f}%")

    print("\n" + "=" * 96)
    print("P2 INTERACTION — does the ATS fade strengthen late?")
    print("=" * 96)
    sh = pd.concat([g[dep_h].assign(cov=-g.loc[dep_h, "home_cover"]),
                    g[dep_a].assign(cov=g.loc[dep_a, "home_cover"])])
    rows = []
    for lab, m in (("all departed games", sh["days_left"] >= 0),
                   ("departed, >30 days left", sh["days_left"] > 30),
                   ("departed, last 30 days", sh["days_left"] <= 30),
                   ("departed, last 14 days", sh["days_left"] <= 14)):
        if m.sum() >= 40:
            rows.append(ats(sh[m], lab))
    print(pd.DataFrame(rows).to_string(index=False))
    print(f"\n  break-even {100*BE:.2f}%")

    print("\n" + "=" * 96)
    print("P3 CROSS-MARKET — do departed-star games go OVER?  (the real test)")
    print("=" * 96)
    rows = []
    for lab, m in (("departed present, ANY time", anydep),
                   ("departed present, last 30d", anydep & (g["days_left"] <= 30)),
                   ("departed present, last 14d", anydep & (g["days_left"] <= 14)),
                   ("NO departed, last 14 days", ~anydep & (g["days_left"] <= 14)),
                   ("NO departed, rest of season", ~anydep & (g["days_left"] > 14))):
        s = g[m]
        if len(s) < 40:
            continue
        ov = (s["tot_resid"] > 0).mean()
        se = np.sqrt(ov * (1 - ov) / len(s))
        rows.append({"split": lab, "n": len(s),
                     "resid": round(s["tot_resid"].mean(), 3),
                     "over %": round(100 * ov, 2),
                     "95% CI": f"[{100*(ov-1.96*se):.1f}, {100*(ov+1.96*se):.1f}]",
                     "ROI over": round(100 * (ov * (100 / 110) - (1 - ov)), 2)})
    print(pd.DataFrame(rows).to_string(index=False))

    print("\n" + "=" * 96)
    print("P4 ADDITIVE — stacking markers")
    print("=" * 96)
    g["marks"] = (anydep.astype(int) + (g["days_left"] <= 14).astype(int))
    rows = []
    for k, s in g.groupby("marks"):
        ov = (s["tot_resid"] > 0).mean()
        se = np.sqrt(ov * (1 - ov) / len(s))
        rows.append({"disengagement markers": k, "n": len(s),
                     "total resid": round(s["tot_resid"].mean(), 3),
                     "over %": round(100 * ov, 2),
                     "95% CI": f"[{100*(ov-1.96*se):.1f}, {100*(ov+1.96*se):.1f}]",
                     "ROI over": round(100 * (ov * (100 / 110) - (1 - ov)), 2)})
    print(pd.DataFrame(rows).to_string(index=False))

    print("\n--- departed-star ATS fade, by season ---")
    print(sh.groupby("season").apply(lambda x: pd.Series({
        "n": len(x), "fade wins %": round(100 * (x["cov"] > 0).mean(), 2)}),
        include_groups=False).to_string())


if __name__ == "__main__":
    main()
