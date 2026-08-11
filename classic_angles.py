"""Two classic betting angles, tested.

  1. HOME UNDERDOGS. The oldest systematic angle in sports betting: home dogs are
     said to cover more often than the line implies. Decent sample here.

  2. DO-OR-DIE PLAYOFF HOME TEAMS. Game 5 of a 2-2 series, elimination games,
     Game 7. The claim is that home teams facing (or applying) elimination are
     underpriced. Sample is thin and that is stated up front, not discovered
     afterwards.

Series structure is derived, not assumed: playoff games are grouped by season and
by the unordered pair of teams, sorted by date to get the game number, and the
series score entering each game is accumulated. That is more robust than decoding
the game-id, and it self-checks (series must run 4-7 games and end 4-x).

Break-even at -110 is 52.38%. A cover rate of 51% is not an edge, it is a losing
strategy that happens to win more than half its bets.
"""

import numpy as np
import pandas as pd
from scipy import stats

ODDS = "/home/dpope/data/dfMaster_OT.parquet"


def load():
    o = pd.read_parquet(ODDS)
    o["season"] = o["DATASET_H"].fillna(o["BIGDATABALL\nDATASET_H"])
    o["gid"] = (o["GAME-ID"].astype(str)
                .str.replace(r"\.0$", "", regex=True).str.zfill(10))
    o["type"] = o["gid"].str[2]
    o["date"] = pd.to_datetime(o["DATE"])
    cs = pd.to_numeric(o["CLOSING SPREAD_H"], errors="coerce")
    o = o[cs.abs() <= 25].copy()
    o["close_margin"] = -cs[cs.abs() <= 25]
    o["actual_margin"] = (pd.to_numeric(o["PTS_H"], errors="coerce")
                          - pd.to_numeric(o["PTS_R"], errors="coerce"))
    o = o.dropna(subset=["actual_margin", "close_margin"])
    o["excess"] = o["actual_margin"] - o["close_margin"]
    o["home_cover"] = o["excess"] > 0
    o["push"] = o["excess"] == 0
    o["home_win"] = o["actual_margin"] > 0
    return o


def rate(sub, col="home_cover"):
    s = sub[~sub["push"]]
    n = len(s)
    if n == 0:
        return dict(n=0)
    w = s[col].mean()
    lo, hi = stats.beta.ppf([.025, .975], s[col].sum() + .5, n - s[col].sum() + .5)
    z = (w - 110 / 210) / np.sqrt(0.25 / n)
    return {"n": n, "cover %": 100 * w, "95% lo": 100 * lo, "95% hi": 100 * hi,
            "vs 52.38% (z)": z, "ROI %": 100 * (w * (100 / 110) - (1 - w))}


def build_series(pl):
    """Derive game number and series score entering each playoff game."""
    pl = pl.sort_values("date").copy()
    pl["pair"] = [frozenset(x) for x in zip(pl["TEAM_H"], pl["TEAM_R"])]
    out = []
    for (season, pair), g in pl.groupby(["season", "pair"], sort=False):
        g = g.sort_values("date").copy()
        wins = {t: 0 for t in pair}
        gn, h_w, a_w = [], [], []
        for _, row in g.iterrows():
            gn.append(len(gn) + 1)
            h_w.append(wins[row["TEAM_H"]])
            a_w.append(wins[row["TEAM_R"]])
            winner = row["TEAM_H"] if row["actual_margin"] > 0 else row["TEAM_R"]
            wins[winner] += 1
        g["game_no"] = gn
        g["h_wins"] = h_w
        g["a_wins"] = a_w
        out.append(g)
    s = pd.concat(out, ignore_index=True)
    s["home_elim"] = s["a_wins"] == 3           # home team faces elimination
    s["away_elim"] = s["h_wins"] == 3           # away team faces elimination
    s["do_or_die"] = s["home_elim"] | s["away_elim"]
    s["g5_tied"] = (s["game_no"] == 5) & (s["h_wins"] == 2) & (s["a_wins"] == 2)
    s["g7"] = s["game_no"] == 7
    return s


def main():
    o = load()
    reg = o[o["type"] == "2"]
    pl = o[o["type"] == "4"]
    print(f"regular season {len(reg):,}   playoffs {len(pl):,}\n")

    print("=== 1. HOME UNDERDOGS (regular season) ===")
    rows = {}
    rows["all games"] = rate(reg)
    rows["home favourite"] = rate(reg[reg["close_margin"] > 0])
    rows["home underdog"] = rate(reg[reg["close_margin"] < 0])
    for lo, hi in ((0, 3), (3, 6), (6, 10), (10, 30)):
        sub = reg[(reg["close_margin"] < 0) & (-reg["close_margin"] >= lo)
                  & (-reg["close_margin"] < hi)]
        rows[f"home dog +{lo} to +{hi}"] = rate(sub)
    print(pd.DataFrame(rows).T.round(2).to_string())

    print("\n=== home underdogs, by season (consistency check) ===")
    hd = reg[reg["close_margin"] < 0]
    t = hd[~hd["push"]].groupby("season").agg(
        n=("home_cover", "size"), cover=("home_cover", lambda s: 100 * s.mean()))
    print(t.round(2).to_string())

    print("\n=== 2. PLAYOFFS: do-or-die ===")
    s = build_series(pl)
    chk = s.groupby(["season", "pair"]).size()
    print(f"series reconstructed: {len(chk)}  "
          f"(games per series {chk.min()}-{chk.max()}, should be 4-7)")
    rows2 = {}
    rows2["all playoff games"] = rate(s)
    rows2["playoff home dogs"] = rate(s[s["close_margin"] < 0])
    rows2["do-or-die (either side)"] = rate(s[s["do_or_die"]])
    rows2["home team facing elimination"] = rate(s[s["home_elim"]])
    rows2["home team can eliminate"] = rate(s[s["away_elim"]])
    rows2["Game 5, series tied 2-2"] = rate(s[s["g5_tied"]])
    rows2["Game 7"] = rate(s[s["g7"]])
    print(pd.DataFrame(rows2).T.round(2).to_string())

    print("\n=== straight-up home win rates (not ATS) ===")
    for lab, sub in (("all playoff", s), ("home facing elimination", s[s["home_elim"]]),
                     ("Game 5 tied 2-2", s[s["g5_tied"]]), ("Game 7", s[s["g7"]])):
        if len(sub):
            print(f"  {lab:28} n={len(sub):4d}  home wins {100 * sub['home_win'].mean():.1f}%"
                  f"   mean closing spread {sub['close_margin'].mean():+.2f}")


if __name__ == "__main__":
    main()
