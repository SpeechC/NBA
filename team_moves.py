"""Do certain teams draw bigger line moves -- and does it persist?

Distinct from two earlier null results:
  * the team-identity test predicted the SIGNED move (60 dummies, CLV got worse)
  * the move-class test never included team identity among its strata

This asks about MAGNITUDE: are some teams' games systematically repriced more,
as a market-attention / flow effect would imply?

The decisive question is not whether a cross-sectional spread exists -- with 30
teams and ~500 games each, a spread appears by chance. It is whether the spread
PERSISTS from one season to the next. A team effect that does not carry forward
cannot be traded, however large it looks in hindsight.

Four checks:
  1. cross-sectional spread in mean |move| by team
  2. how big that spread is against what pure noise produces (permutation)
  3. season-to-season persistence -- the crux
  4. whether high-|move| teams actually pay us, i.e. our CLV inside them
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
RNG = np.random.default_rng(0)

BETS = "staking_bets_A.csv"
RAW = "/mnt/c/NBA2/dfMaster_OT_2017-2026.csv"


def load():
    b = pd.read_csv(BETS, parse_dates=["date"])
    raw = pd.read_csv(RAW, low_memory=False,
                      usecols=["GAME-ID", "TEAM_H", "TEAM_R"])
    raw["game_id"] = raw["GAME-ID"].astype(str).str.zfill(10)
    b["game_id"] = b["game_id"].astype(str).str.zfill(10)
    m = b.merge(raw[["game_id", "TEAM_H", "TEAM_R"]], on="game_id", how="left")
    assert m["TEAM_H"].notna().mean() > 0.95, \
        f"team join failed: {100*m['TEAM_H'].notna().mean():.1f}% matched"
    m["abs_move"] = m["move_total"].abs()
    return m


def long(m):
    """One row per team-game, so each game contributes to both its teams."""
    h = m.assign(team=m["TEAM_H"])
    a = m.assign(team=m["TEAM_R"])
    return pd.concat([h, a], ignore_index=True)


def main():
    m = load()
    L = long(m)
    print(f"{len(m):,} games, {L['team'].nunique()} teams, "
          f"mean |move| {m['abs_move'].mean():.3f}\n")

    print("=" * 92)
    print("1. Mean |move| by team, all seasons pooled")
    print("=" * 92)
    t = L.groupby("team").agg(games=("abs_move", "size"),
                              mean_abs_move=("abs_move", "mean")).sort_values(
        "mean_abs_move", ascending=False)
    print(pd.concat([t.head(6), t.tail(6)]).round(3).to_string())
    spread = t["mean_abs_move"].iloc[0] - t["mean_abs_move"].iloc[-1]
    print(f"\nobserved spread top-to-bottom: {spread:.3f} points "
          f"(sd across teams {t['mean_abs_move'].std():.4f})")

    print("\n" + "=" * 92)
    print("2. Is that spread bigger than chance? (labels permuted 2,000x)")
    print("=" * 92)
    vals = L["abs_move"].values
    grp = L["team"].values
    sizes = pd.Series(grp).value_counts().values
    null_sd, null_spread = [], []
    for _ in range(2000):
        perm = RNG.permutation(vals)
        idx, means = 0, []
        for n in sizes:
            means.append(perm[idx:idx + n].mean())
            idx += n
        means = np.array(means)
        null_sd.append(means.std())
        null_spread.append(means.max() - means.min())
    obs_sd = t["mean_abs_move"].std()
    print(f"  sd across teams   observed {obs_sd:.4f}   "
          f"null {np.mean(null_sd):.4f} +/- {np.std(null_sd):.4f}   "
          f"pctile {100*np.mean(np.array(null_sd) < obs_sd):.1f}")
    print(f"  top-bottom spread observed {spread:.4f}   "
          f"null {np.mean(null_spread):.4f}   "
          f"pctile {100*np.mean(np.array(null_spread) < spread):.1f}")

    print("\n" + "=" * 92)
    print("3. Does a team's |move| persist season to season? (THE CRUX)")
    print("=" * 92)
    ts = L.groupby(["season_lbl", "team"])["abs_move"].mean().unstack(0)
    seasons = list(ts.columns)
    rows = []
    for i in range(len(seasons) - 1):
        s0, s1 = seasons[i], seasons[i + 1]
        pair = ts[[s0, s1]].dropna()
        if len(pair) >= 20:
            r = np.corrcoef(pair[s0], pair[s1])[0, 1]
            rows.append({"from": s0, "to": s1, "teams": len(pair),
                         "corr": round(r, 3)})
    p = pd.DataFrame(rows)
    print(p.to_string(index=False))
    print(f"\n  mean year-over-year correlation: {p['corr'].mean():+.3f}")
    print("  A tradable team effect needs this clearly positive and stable.")

    print("\n" + "=" * 92)
    print("4. Do high-|move| teams actually pay us? (CLV by team tercile)")
    print("=" * 92)
    rank = L.groupby("team")["abs_move"].mean()
    terc = pd.qcut(rank, 3, labels=["low |move|", "mid", "high |move|"])
    L["terc"] = L["team"].map(terc)
    sel = L[(L["pm"].abs() > 0.75) & (~L["push"])]
    out = []
    for g, sub in sel.groupby("terc", observed=True):
        clv = np.where(sub["pm"] > 0, sub["move_total"], -sub["move_total"])
        out.append({"tercile": g, "team-games": len(sub),
                    "mean |move|": round(sub["abs_move"].mean(), 3),
                    "CLV": round(clv.mean(), 3),
                    "win %": round(100 * sub["won"].mean(), 2),
                    "$won": round(sub["$won"].sum(), 2)})
    print(pd.DataFrame(out).to_string(index=False))
    print("\n(team-games double-count each game; dollar totals are indicative only)")


if __name__ == "__main__":
    main()
