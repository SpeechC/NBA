"""Ewing, split by absence TYPE — temporary vs permanent departure.

The pooled test mixes two situations that have no reason to behave alike:

  TEMPORARY   the star plays again later that season. A one-off absence --
              injury, rest, load management. This is the actual Ewing case: a
              salient event the market may overreact to.

  DEPARTED    the game falls after the star's final appearance. Traded, season
              ending injury, shutdown. The team has permanently reorganised and
              the market has had weeks to reprice. No overreaction is expected,
              and none should be claimed.

33.7% of "star out" team-games are DEPARTED, and the absence rate climbs from
19.4% in games 21-35 to 38.7% in games 66-82 -- so the pooled sample is heavily
weighted toward the case the hypothesis does not describe, especially late in
seasons. If the dilution is what killed the recent seasons, the temporary subset
should still show an effect.
"""
import warnings

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")
RNG = np.random.default_rng(0)

from ewing import DEFINE_WINDOW, MIN_APPEARANCES, build_player_games
from prepare_data import CSV, season_label


def main():
    pg = build_player_games()
    raw = pd.read_csv(CSV, low_memory=False)
    raw["season_lbl"] = season_label(raw).astype(str)
    raw = raw[raw["season_lbl"].str.contains("Regular Season", na=False)].copy()
    raw["gid"] = raw["GAME-ID"].astype(str).str.zfill(10)
    raw["date"] = pd.to_datetime(raw["DATE"], errors="coerce")
    raw["close_spread"] = pd.to_numeric(raw["CLOSING SPREAD_H"], errors="coerce")
    games = raw.dropna(subset=["date", "close_spread", "PTS_H", "PTS_R"])
    games = games[["gid", "date", "season_lbl", "PTS_H", "PTS_R",
                   "close_spread"]].drop_duplicates("gid")

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
        star[["season", "team", "pid", "ppg"]], on=["season", "team"], how="inner")
    played = pg[["gid", "pid"]].drop_duplicates().assign(played=True)
    test = test.merge(played, on=["gid", "pid"], how="left")
    test["star_out"] = test["played"].isna()

    # last appearance of the star, to separate temporary from departed
    last = (test[~test["star_out"]].groupby(["season", "team"])["tg_idx"]
            .max().rename("last_app"))
    test = test.merge(last, on=["season", "team"], how="left")
    test["absence"] = np.where(
        ~test["star_out"], "present",
        np.where(test["tg_idx"] > test["last_app"], "DEPARTED", "TEMPORARY"))

    tp = pg.groupby(["gid", "team"])["pts"].sum().reset_index(name="team_pts")
    test = test.merge(tp, on=["gid", "team"], how="left").merge(games, on="gid")
    test["is_home"] = (test["team_pts"] - test["PTS_H"]).abs() < \
                      (test["team_pts"] - test["PTS_R"]).abs()

    cnt = test.groupby("gid").size()
    test = test[test["gid"].isin(cnt[cnt == 2].index)]
    g = test.pivot_table(index="gid", columns="is_home", values="absence",
                         aggfunc="first")
    g.columns = ["away", "home"]
    g = g.join(games.set_index("gid"))
    g["home_cover"] = (g["PTS_H"] - g["PTS_R"]) + g["close_spread"]
    g = g[g["home_cover"] != 0]

    print(f"games {len(g):,}")
    print(pd.crosstab(g["home"], g["away"]).to_string())

    def block(mask_h, mask_a, label):
        a = g[mask_h].assign(cov=g.loc[mask_h, "home_cover"])
        b = g[mask_a].assign(cov=-g.loc[mask_a, "home_cover"])
        x = pd.concat([a, b])
        if len(x) < 30:
            return None, x
        c = x["cov"]
        t, p = stats.ttest_1samp(c, 0)
        w = (c > 0).mean()
        return {"situation": label, "n": len(x), "mean cover": round(c.mean(), 3),
                "cover %": round(100 * w, 2), "t": round(t, 2), "p": round(p, 4),
                "ROI110 %": round(100 * (w * (100 / 110) - (1 - w)), 2)}, x

    rows, sets = [], {}
    for lab, kind in (("TEMPORARY absence", "TEMPORARY"),
                      ("DEPARTED (traded/shutdown)", "DEPARTED")):
        mh = (g["home"] == kind) & (g["away"] == "present")
        ma = (g["away"] == kind) & (g["home"] == "present")
        r, x = block(mh, ma, lab)
        if r:
            rows.append(r)
            sets[kind] = x
    both_present = (g["home"] == "present") & (g["away"] == "present")
    c = g[both_present]["home_cover"]
    w = (c > 0).mean()
    rows.append({"situation": "baseline: both present (home)", "n": len(c),
                 "mean cover": round(c.mean(), 3), "cover %": round(100 * w, 2),
                 "t": round(stats.ttest_1samp(c, 0)[0], 2),
                 "p": round(stats.ttest_1samp(c, 0)[1], 4),
                 "ROI110 %": round(100 * (w * (100 / 110) - (1 - w)), 2)})

    print("\n" + "=" * 96)
    print("SHORT-HANDED TEAM ATS, by absence type")
    print("=" * 96)
    print(pd.DataFrame(rows).to_string(index=False))

    for kind, x in sets.items():
        print(f"\n--- {kind}, by season ---")
        print(x.groupby("season_lbl").apply(lambda y: pd.Series({
            "n": len(y), "mean cover": round(y["cov"].mean(), 3),
            "cover %": round(100 * (y["cov"] > 0).mean(), 2)}),
            include_groups=False).to_string())

    if "TEMPORARY" in sets:
        x = sets["TEMPORARY"]
        recent = x[x["season_lbl"].str.contains("2020|2021|2022|2023|2024")]
        c = recent["cov"]
        w = (c > 0).mean()
        se = np.sqrt(w * (1 - w) / len(c))
        print(f"\n--- TEMPORARY absences, 2020-21 onward only ---")
        print(f"  n={len(c):,}  mean cover {c.mean():+.3f}  cover% {100*w:.2f}"
              f"  95% CI [{100*(w-1.96*se):.2f}, {100*(w+1.96*se):.2f}]"
              f"  ROI {100*(w*(100/110)-(1-w)):+.2f}%")
        print(f"  break-even 52.38%")


if __name__ == "__main__":
    main()
