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

  ABSENCE means the player records no event in the game.

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


def main():
    pg = build_player_games()
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
    print(f"player-games {len(pg):,}   odds games {len(games):,}")

    # team-game ordering within season
    tg = pg[["season", "team", "gid", "date"]].drop_duplicates().sort_values("date")
    tg["tg_idx"] = tg.groupby(["season", "team"]).cumcount()
    pg = pg.merge(tg[["season", "team", "gid", "tg_idx"]],
                  on=["season", "team", "gid"], how="left")

    # star fixed from the team's first DEFINE_WINDOW games
    early = pg[pg["tg_idx"] < DEFINE_WINDOW]
    cand = (early.groupby(["season", "team", "pid"])
                 .agg(apps=("pts", "size"), ppg=("pts", "mean")).reset_index())
    cand = cand[cand["apps"] >= MIN_APPEARANCES]
    star = (cand.sort_values("ppg", ascending=False)
                .groupby(["season", "team"], as_index=False).first())
    print(f"stars identified: {len(star):,} team-seasons, "
          f"mean {star['ppg'].mean():.1f} ppg")

    # test window: games 21+, did the star appear?
    test = tg[tg["tg_idx"] >= DEFINE_WINDOW].merge(
        star[["season", "team", "pid", "ppg"]], on=["season", "team"], how="inner")
    played = pg[["gid", "pid"]].drop_duplicates().assign(played=True)
    test = test.merge(played, on=["gid", "pid"], how="left")
    test["star_out"] = test["played"].isna()
    print(f"team-games in test window: {len(test):,}   "
          f"star absent in {100*test['star_out'].mean():.2f}%")

    # team points from pbp, to identify the home side
    tp = pg.groupby(["gid", "team"])["pts"].sum().reset_index(name="team_pts")
    test = test.merge(tp, on=["gid", "team"], how="left")
    test = test.merge(games, on="gid", how="inner")
    test["is_home"] = (test["team_pts"] - test["PTS_H"]).abs() < \
                      (test["team_pts"] - test["PTS_R"]).abs()

    # keep games where BOTH teams are in the test window
    cnt = test.groupby("gid").size()
    test = test[test["gid"].isin(cnt[cnt == 2].index)]
    g = test.pivot_table(index="gid", columns="is_home",
                         values=["star_out", "ppg"], aggfunc="first")
    g.columns = [f"{a}_{'home' if b else 'away'}" for a, b in g.columns]
    g = g.join(games.set_index("gid")).dropna(subset=["close_spread"])
    g["margin"] = g["PTS_H"] - g["PTS_R"]
    g["home_cover"] = g["margin"] + g["close_spread"]
    g["total_resid"] = (g["PTS_H"] + g["PTS_R"]) - g["close_total"]
    g = g[g["home_cover"] != 0]
    g["star_out_home"] = g["star_out_home"].astype(bool)
    g["star_out_away"] = g["star_out_away"].astype(bool)

    only_h = g["star_out_home"] & ~g["star_out_away"]
    only_a = g["star_out_away"] & ~g["star_out_home"]
    both = g["star_out_home"] & g["star_out_away"]
    neither = ~g["star_out_home"] & ~g["star_out_away"]
    print("\n" + "=" * 96)
    print("EWING TEST — does the short-handed team beat the closing spread?")
    print("=" * 96)
    print(f"  games {len(g):,}   neither {neither.sum():,}   "
          f"home star out {only_h.sum():,}   away star out {only_a.sum():,}   "
          f"both {both.sum():,}")

    sh = pd.concat([g[only_h].assign(sh_cover=g.loc[only_h, "home_cover"]),
                    g[only_a].assign(sh_cover=-g.loc[only_a, "home_cover"])])
    base = g[neither].assign(sh_cover=g.loc[neither, "home_cover"])

    def blk(x, lab):
        c = x["sh_cover"]
        t, p = stats.ttest_1samp(c, 0.0)
        w = (c > 0).mean()
        return {"set": lab, "n": len(x), "mean cover": round(c.mean(), 3),
                "cover %": round(100 * w, 2), "t": round(t, 2), "p": round(p, 4),
                "ROI110 %": round(100 * (w * (100 / 110) - (1 - w)), 2)}

    print()
    print(pd.DataFrame([blk(sh, "SHORT-HANDED team ATS"),
                        blk(base, "baseline: home, neither out")]).to_string(index=False))

    print("\n--- totals ---")
    for lab, x in (("star out (one side)", g[only_h | only_a]),
                   ("neither out", g[neither])):
        r = x["total_resid"]
        t, p = stats.ttest_1samp(r, 0)
        print(f"  {lab:22} n={len(x):5,}  actual-close {r.mean():+.3f}  "
              f"over% {100*(r>0).mean():5.2f}  t={t:+.2f}  p={p:.3f}")

    print("\n--- by season (decay check) ---")
    print(sh.groupby("season_lbl").apply(lambda x: pd.Series({
        "n": len(x), "mean cover": round(x["sh_cover"].mean(), 3),
        "cover %": round(100 * (x["sh_cover"] > 0).mean(), 2)}),
        include_groups=False).to_string())

    print("\n--- permutation null ---")
    obs = sh["sh_cover"].mean()
    pool = pd.concat([sh, base])["sh_cover"].values
    null = np.array([RNG.choice(pool, len(sh), replace=False).mean()
                     for _ in range(4000)])
    print(f"  observed {obs:+.3f}   null {null.mean():+.3f} +/- {null.std():.3f}"
          f"   percentile {100*np.mean(null < obs):.1f}")
    sh.to_csv("ewing_bets.csv")


if __name__ == "__main__":
    main()
