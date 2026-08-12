"""Rotation discontinuity x derivative-market pricing.

HYPOTHESIS (Type 4, mechanical translation). When a rotation player is
unexpectedly absent, the book moves the FULL-GAME total efficiently but applies
its usual H1 share. If the true H1/H2 allocation shifts when a rotation is
disrupted, the derived H1 line inherits an allocation error the full-game line
does not have.

The state variable is a CHANGE, not a level -- books price persistent team
traits well, so the candidate is a discontinuity:

    D_new_i  = share of the team's recent scoring contributed by SIGNIFICANT
               players (>= BIG of team scoring) who PLAYED THE PREVIOUS GAME and
               are absent tonight

⚠ A first version counted ANY player who played last game and not tonight. That
fired in 83.3% of games with a mean share of 0.166 -- routine rotation churn, not
a discontinuity -- and Stage 1 was null with non-monotone buckets. BIG restricts
it to players carrying a real share of the offence.
    D_back_i = same for players absent last game who RETURN tonight

Both are computed from the prior 5 games' point shares, strictly before tonight.
Ongoing absences do not count: those are already in the price. Only the
transition does.

STAGE 1 (sports reality, full sample, no lines)
    actual_H1_share = a + b*D          does a disrupted rotation shift the
                                       temporal allocation of scoring at all?

STAGE 2 (contact with the market, DK window only)
    actual_H1_share - market_H1_share = a + b*D

    The DK file supplies h1_share_full_game_close directly, so the market's
    allocation is observed rather than inferred. If b -> 0, stop. No thresholds,
    no subgroup rescue.

STAGE 3 is not attempted unless Stage 2 survives.
"""
import warnings

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")

DK = "/mnt/c/NBA/nba_draftkings_totals_historical.csv"
CACHE = "/home/dpope/data/player_game_pts.parquet"
ROLL = 5
BIG = 0.15          # a player must carry >=15% of recent team scoring


def discontinuity():
    """Per team-game: share of recent scoring newly absent / newly returning."""
    pg = pd.read_parquet(CACHE)          # gid, season, pid, team, events, pts
    from prepare_data import CSV, season_label
    raw = pd.read_csv(CSV, low_memory=False)
    raw["lbl"] = season_label(raw).astype(str)
    o = raw[raw["lbl"].str.contains("Regular Season", na=False)].copy()
    o["gid"] = o["GAME-ID"].astype(str).str.zfill(10)
    o["date"] = pd.to_datetime(o["DATE"], errors="coerce")
    pg = pg.merge(o[["gid", "date"]], on="gid", how="inner").sort_values("date")

    # team-game roster: who played, and each player's prior-5 share of team pts
    pg["team_pts"] = pg.groupby(["gid", "team"])["pts"].transform("sum")
    tg = pg[["season", "team", "gid", "date"]].drop_duplicates()
    tg = tg.sort_values("date")
    tg["tidx"] = tg.groupby(["season", "team"]).cumcount()
    pg = pg.merge(tg[["season", "team", "gid", "tidx"]],
                  on=["season", "team", "gid"], how="left")

    pg = pg.sort_values(["season", "team", "pid", "tidx"])
    g = pg.groupby(["season", "team", "pid"])
    pg["prior_pts"] = g["pts"].transform(
        lambda s: s.shift(1).rolling(ROLL, min_periods=2).mean())
    tp = (pg.groupby(["season", "team", "tidx"])["prior_pts"].sum()
          .rename("team_prior").reset_index())
    pg = pg.merge(tp, on=["season", "team", "tidx"], how="left")
    pg["share"] = pg["prior_pts"] / pg["team_prior"].replace(0, np.nan)

    # presence matrix: did this player appear in game tidx, and in tidx-1?
    played = pg[["season", "team", "pid", "tidx"]].assign(p=1)
    full = []
    for (s, t), grp in pg.groupby(["season", "team"]):
        idx = np.sort(grp["tidx"].unique())
        pids = grp["pid"].unique()
        mesh = pd.MultiIndex.from_product([[s], [t], pids, idx],
                                          names=["season", "team", "pid", "tidx"])
        full.append(pd.DataFrame(index=mesh).reset_index())
    F = pd.concat(full).merge(played, on=["season", "team", "pid", "tidx"],
                              how="left")
    F["p"] = F["p"].fillna(0)
    F = F.sort_values(["season", "team", "pid", "tidx"])
    F["p_prev"] = F.groupby(["season", "team", "pid"])["p"].shift(1)
    F = F.merge(pg[["season", "team", "pid", "tidx", "share"]],
                on=["season", "team", "pid", "tidx"], how="left")
    # share is only defined on games the player appeared in; carry it forward
    F["share"] = (F.groupby(["season", "team", "pid"])["share"]
                  .transform(lambda s: s.ffill()))
    sh = F["share"].fillna(0)
    big = sh >= BIG
    F["new_out"] = ((F["p"] == 0) & (F["p_prev"] == 1) & big) * sh
    F["new_back"] = ((F["p"] == 1) & (F["p_prev"] == 0) & big) * sh
    D = (F.groupby(["season", "team", "tidx"])[["new_out", "new_back"]]
         .sum().reset_index())
    D = D.merge(tg[["season", "team", "tidx", "gid"]],
                on=["season", "team", "tidx"], how="left")
    return D[["gid", "team", "new_out", "new_back"]]


def main():
    from halves import period_scores
    from prepare_data import CSV, season_label

    D = discontinuity()
    raw = pd.read_csv(CSV, low_memory=False)
    raw["lbl"] = season_label(raw).astype(str)
    o = raw[raw["lbl"].str.contains("Regular Season", na=False)].copy()
    o["gid"] = o["GAME-ID"].astype(str).str.zfill(10)
    o["date"] = pd.to_datetime(o["DATE"], errors="coerce")
    o["actual_full"] = o["PTS_H"] + o["PTS_R"]
    ps = period_scores("RegularSeason")
    o = o.merge(ps[["gid", "q1", "q2"]], on="gid", how="inner")
    o["actual_h1"] = o["q1"] + o["q2"]
    o["h1_share"] = o["actual_h1"] / o["actual_full"]

    tm = pd.read_csv("team_mapping.csv")
    tid = dict(zip(tm["bigdataball_name"], tm["team_id"]))
    o["tid_h"], o["tid_a"] = o["TEAM_H"].map(tid), o["TEAM_R"].map(tid)
    dh = D.rename(columns={"team": "tid_h", "new_out": "out_h",
                           "new_back": "back_h"})
    da = D.rename(columns={"team": "tid_a", "new_out": "out_a",
                           "new_back": "back_a"})
    o = o.merge(dh, on=["gid", "tid_h"], how="left")
    o = o.merge(da, on=["gid", "tid_a"], how="left")
    o = o.dropna(subset=["out_h", "out_a", "h1_share"])
    o["D_out"] = o["out_h"] + o["out_a"]
    o["D_back"] = o["back_h"] + o["back_a"]
    o["D_any"] = o["D_out"] + o["D_back"]

    print(f"STAGE 1 sample: {len(o):,} games")
    print(f"  D_out  mean {o['D_out'].mean():.4f}  sd {o['D_out'].std():.4f}  "
          f">0 in {100*(o['D_out']>0.01).mean():.1f}% of games")
    print(f"  D_back mean {o['D_back'].mean():.4f}  "
          f">0 in {100*(o['D_back']>0.01).mean():.1f}%")
    print(f"  actual H1 share: mean {o['h1_share'].mean():.4f}  "
          f"sd {o['h1_share'].std():.4f}\n")

    print("=" * 92)
    print("STAGE 1 — does a rotation discontinuity shift the H1 share?")
    print("=" * 92)
    for col in ("D_out", "D_back", "D_any"):
        r = np.corrcoef(o[col], o["h1_share"])[0, 1]
        b = np.polyfit(o[col], o["h1_share"], 1)[0]
        t = r * np.sqrt(len(o) - 2) / np.sqrt(1 - r * r)
        print(f"  H1 share ~ {col:7} corr {r:+.4f}  slope {b:+.5f}  t={t:+.2f}")
    print("\n  quartiles of D_out:")
    o["q"] = pd.qcut(o["D_out"].rank(method="first"), 4, labels=[1, 2, 3, 4])
    for q, s in o.groupby("q", observed=True):
        print(f"    Q{q}  D_out {s['D_out'].mean():.4f}  n={len(s):5,}  "
              f"H1 share {s['h1_share'].mean():.4f}  "
              f"H1 pts {s['actual_h1'].mean():6.2f}  "
              f"full {s['actual_full'].mean():6.2f}")

    print("\n" + "=" * 92)
    print("STAGE 2 — does it survive against the DraftKings H1 line?")
    print("=" * 92)
    dk = pd.read_csv(DK)
    dk["key"] = dk["game_date_et"] + "_" + dk["away_abbr"] + "_" + dk["home_abbr"]
    ab = dict(zip(tm["bigdataball_name"], tm["abbr"]))
    o["key"] = (o["date"].dt.strftime("%Y-%m-%d") + "_" + o["TEAM_R"].map(ab)
                + "_" + o["TEAM_H"].map(ab))
    cols = ["key", "full_game_total_close", "h1_total_close",
            "h1_share_full_game_close", "h1_over_price_close",
            "h1_under_price_close"]
    j = o.merge(dk[cols].dropna(subset=["h1_total_close",
                                        "h1_share_full_game_close"]),
                on="key", how="inner")
    j["share_err"] = j["h1_share"] - j["h1_share_full_game_close"]
    j["h1_resid"] = j["actual_h1"] - j["h1_total_close"]
    print(f"  joined: {len(j)} games")
    print(f"  market H1 share mean {j['h1_share_full_game_close'].mean():.4f}"
          f"  actual {j['h1_share'].mean():.4f}"
          f"  error {j['share_err'].mean():+.4f}")
    print(f"  market H1 share sd {j['h1_share_full_game_close'].std():.4f} "
          f"-- how much the book varies its allocation at all\n")
    for col in ("D_out", "D_back", "D_any"):
        for tgt, lab in (("share_err", "H1 share error"),
                         ("h1_resid", "H1 residual")):
            r = np.corrcoef(j[col], j[tgt])[0, 1]
            b = np.polyfit(j[col], j[tgt], 1)[0]
            t = r * np.sqrt(len(j) - 2) / np.sqrt(1 - r * r)
            print(f"  {lab:16} ~ {col:7} corr {r:+.4f}  slope {b:+.5f}  "
                  f"t={t:+.2f}")
    print("\n  does the BOOK move its H1 share with the discontinuity?")
    for col in ("D_out", "D_any"):
        r = np.corrcoef(j[col], j["h1_share_full_game_close"])[0, 1]
        print(f"    corr(market H1 share, {col}) = {r:+.4f}")


if __name__ == "__main__":
    main()
