"""The Ewing Theory: does the market over-adjust when a star sits?

Hypothesis: when a team's best player is out, the line moves too far against
them, so the short-handed team beats its number.

This has the four properties that separated the one edge that ever worked here
(§14 mismatch) from the twenty-one nulls:

  * it targets the CLOSE, not the open-to-close move -- the absence is already
    public and priced, so the question is purely whether the price OVERSHOOTS
  * it is conditional, firing on a subset of games
  * it is behavioural -- a salient, nameable mispricing rather than diffuse
    statistical signal
  * it has a directional prediction: the short-handed team covers

Design, with the traps this project has already fallen into:

  STAR IDENTIFICATION IS WALK-FORWARD, AND MUST NOT CONDITION ON PLAYING. A
  first attempt picked each game's star from the players appearing in that game,
  so by construction the star was never absent -- it found 0 absences in 15,600
  team-games. The star is instead fixed from the team's FIRST 20 games of the
  season (leading scorer, minimum 10 appearances) and tested only on games 21+.
  That is leak-free and, unlike a running definition, does not let a player stop
  being the star merely because he is injured.

  ABSENCE means the player records no event in the game, and is split by TYPE:
  TEMPORARY (the star plays again later that season -- injury, rest, load
  management, the actual Ewing case) versus DEPARTED (the game falls after his
  final appearance -- traded, season-ending injury, shutdown). 33.7% of absences
  are DEPARTED and the market has had weeks to reprice those; they are not
  overreaction candidates and are reported separately.

  HOME/AWAY comes from HOMEDESCRIPTION, not from matching pbp-derived points to
  the box score. That heuristic was wrong on 5.82% of team-games because the
  points parsed from event descriptions match the box score exactly only 85.4%
  of the time. HOMEDESCRIPTION flags exactly one team per game in all 9,513
  games.

  Games where BOTH teams are missing a star are excluded from the directional
  test; there is no short-handed side.

  Permutation control and a by-season decay plot, per §14 and §16.
"""
import os
import warnings

import duckdb
import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")
RNG = np.random.default_rng(0)

PBP = "/home/dpope/data/pbp_lineups_all.parquet"
CACHE = "/home/dpope/data/player_game_pts.parquet"
TEAM_LO, TEAM_HI = 1610612737, 1610612766
DEFINE_WINDOW = 20      # team games used to fix the star
MIN_APPEARANCES = 10    # of those, how many the star must have played


def build_player_games():
    """One row per player-game: points scored, from the play-by-play."""
    if os.path.exists(CACHE):
        return pd.read_parquet(CACHE)
    con = duckdb.connect()
    q = f"""
    WITH ev AS (
      SELECT lpad(CAST(GAME_ID AS VARCHAR),10,'0') AS gid,
             SEASON, PLAYER1_ID AS pid, PLAYER1_TEAM_ID AS team,
             EVENTMSGTYPE AS et,
             lower(coalesce(HOMEDESCRIPTION, VISITORDESCRIPTION, '')) AS txt
      FROM read_parquet('{PBP}')
      WHERE SEASON_TYPE = 'RegularSeason'
        AND PLAYER1_TEAM_ID BETWEEN {TEAM_LO} AND {TEAM_HI}
        AND PLAYER1_ID > 100000
    )
    SELECT gid, SEASON AS season, pid, team,
           count(*) AS events,
           sum(CASE WHEN et = 1 AND txt LIKE '%3pt%' THEN 3
                    WHEN et = 1 THEN 2
                    WHEN et = 3 AND txt NOT LIKE '%miss%' THEN 1
                    ELSE 0 END) AS pts
    FROM ev GROUP BY gid, SEASON, pid, team
    """
    d = con.execute(q).fetchdf()
    d.to_parquet(CACHE, index=False)
    return d


def home_team_map():
    """Definitive home team per game: events carrying HOMEDESCRIPTION."""
    con = duckdb.connect()
    q = f"""
    SELECT lpad(CAST(GAME_ID AS VARCHAR),10,'0') AS gid,
           PLAYER1_TEAM_ID AS team,
           sum(CASE WHEN HOMEDESCRIPTION IS NOT NULL THEN 1 ELSE 0 END) AS nh,
           sum(CASE WHEN VISITORDESCRIPTION IS NOT NULL THEN 1 ELSE 0 END) AS na
    FROM read_parquet('{PBP}')
    WHERE SEASON_TYPE='RegularSeason'
      AND PLAYER1_TEAM_ID BETWEEN {TEAM_LO} AND {TEAM_HI}
    GROUP BY 1,2
    """
    d = con.execute(q).fetchdf()
    d["is_home"] = d["nh"] > d["na"]
    assert (d.groupby("gid")["is_home"].sum() == 1).all(), "home flag not unique"
    return d[["gid", "team", "is_home"]]


def main():
    pg = build_player_games()
    hm = home_team_map()

    from prepare_data import CSV, season_label
    raw = pd.read_csv(CSV, low_memory=False)
    raw["season_lbl"] = season_label(raw).astype(str)
    raw = raw[raw["season_lbl"].str.contains("Regular Season", na=False)].copy()
    raw["gid"] = raw["GAME-ID"].astype(str).str.zfill(10)
    raw["date"] = pd.to_datetime(raw["DATE"], errors="coerce")
    raw["close_spread"] = pd.to_numeric(raw["CLOSING SPREAD_H"], errors="coerce")
    raw["close_total"] = pd.to_numeric(raw["CLOSING TOTAL_H"], errors="coerce")
    games = raw.dropna(subset=["date", "close_spread", "PTS_H", "PTS_R"])
    games = games[["gid", "date", "season_lbl", "PTS_H", "PTS_R",
                   "close_spread", "close_total"]].drop_duplicates("gid")

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
    print(f"stars: {len(star):,} team-seasons, mean {star['ppg'].mean():.1f} ppg")

    test = tg[tg["tg_idx"] >= DEFINE_WINDOW].merge(
        star[["season", "team", "pid", "ppg"]], on=["season", "team"], how="inner")
    played = pg[["gid", "pid"]].drop_duplicates().assign(played=True)
    test = test.merge(played, on=["gid", "pid"], how="left")
    test["star_out"] = test["played"].isna()
    last = (test[~test["star_out"]].groupby(["season", "team"])["tg_idx"]
            .max().rename("last_app"))
    test = test.merge(last, on=["season", "team"], how="left")
    test["absence"] = np.where(
        ~test["star_out"], "present",
        np.where(test["tg_idx"] > test["last_app"], "DEPARTED", "TEMPORARY"))
    test = test.merge(hm, on=["gid", "team"], how="inner")
    print(f"team-games tested: {len(test):,}   "
          f"{100*test['star_out'].mean():.1f}% star absent "
          f"({100*(test['absence']=='TEMPORARY').mean():.1f}% temporary, "
          f"{100*(test['absence']=='DEPARTED').mean():.1f}% departed)")

    H = test[test["is_home"]][["gid", "absence"]].rename(columns={"absence": "home"})
    A = test[~test["is_home"]][["gid", "absence"]].rename(columns={"absence": "away"})
    g = games.merge(H, on="gid").merge(A, on="gid")
    g["home_cover"] = (g["PTS_H"] - g["PTS_R"]) + g["close_spread"]
    g = g[g["home_cover"] != 0]
    print(f"games with both sides classified: {len(g):,}")
    print(pd.crosstab(g["home"], g["away"]).to_string())

    def blk(x, lab):
        c = x["cov"]
        t, p = stats.ttest_1samp(c, 0)
        w = (c > 0).mean()
        se = np.sqrt(w * (1 - w) / len(c))
        return {"situation": lab, "n": len(x), "mean cover": round(c.mean(), 3),
                "cover %": round(100 * w, 2),
                "95% CI": f"[{100*(w-1.96*se):.1f}, {100*(w+1.96*se):.1f}]",
                "t": round(t, 2), "p": round(p, 4),
                "ROI110 %": round(100 * (w * (100 / 110) - (1 - w)), 2)}

    rows, sets = [], {}
    for kind in ("TEMPORARY", "DEPARTED"):
        mh = (g["home"] == kind) & (g["away"] == "present")
        ma = (g["away"] == kind) & (g["home"] == "present")
        x = pd.concat([g[mh].assign(cov=g.loc[mh, "home_cover"]),
                       g[ma].assign(cov=-g.loc[ma, "home_cover"])])
        sets[kind] = x
        rows.append(blk(x, f"short-handed: {kind}"))
    bp = (g["home"] == "present") & (g["away"] == "present")
    rows.append(blk(g[bp].assign(cov=g.loc[bp, "home_cover"]),
                    "baseline: both present (home side)"))

    print("\n" + "=" * 104)
    print("SHORT-HANDED TEAM ATS — corrected home/away, split by absence type")
    print("=" * 104)
    print(pd.DataFrame(rows).to_string(index=False))

    for kind, x in sets.items():
        print(f"\n--- {kind}, by season ---")
        print(x.groupby("season_lbl").apply(lambda y: pd.Series({
            "n": len(y), "mean cover": round(y["cov"].mean(), 3),
            "cover %": round(100 * (y["cov"] > 0).mean(), 2)}),
            include_groups=False).to_string())

    x = sets["TEMPORARY"]
    print("\n--- permutation null, TEMPORARY vs both-present ---")
    pool = np.concatenate([x["cov"].values, g[bp]["home_cover"].values])
    obs = x["cov"].mean()
    null = np.array([RNG.choice(pool, len(x), replace=False).mean()
                     for _ in range(4000)])
    print(f"  observed {obs:+.3f}   null {null.mean():+.3f} +/- {null.std():.3f}"
          f"   percentile {100*np.mean(null < obs):.1f}")
    x.to_csv("ewing_bets.csv", index=False)


if __name__ == "__main__":
    main()
