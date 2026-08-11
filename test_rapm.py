"""Does player-level impact beat team-level ratings against the closing line?

Two feature sets, both fed through the same walk-forward harness as A/B/C in
test_ratings.py so the numbers are directly comparable:

  D  RAPM projected with ACTUAL minutes  — LOOK-AHEAD, reports the ceiling
  E  RAPM projected with LAGGED minutes  — honestly tradable

D is not a backtest result and is never quoted as one. It answers the question
that decides whether to buy an injury feed at all: if knowing exactly who played
and for how long still does not beat the closing line, then no real-time
availability feed can rescue this, because D is strictly better than anything a
feed could deliver.

E reacts to an absence one game late. That lag is precisely what a feed removes,
so the gap between D and E prices the feed.
"""

import numpy as np
import pandas as pd

from movement_full import CAL_MIN, SCORE_MIN, wf_calibrate, wf_xgb
from rapm import fit_rapm, load_stints, player_minutes, to_observations

REFIT_DAYS = 21
TRAIN_SEASONS = 2      # trailing window of stints used to fit RAPM


def game_dates():
    o = pd.read_parquet("/home/dpope/data/dfMaster_OT.parquet")
    o["gid"] = (o["GAME-ID"].astype(str)
                .str.replace(r"\.0$", "", regex=True).str.zfill(10))
    o["date"] = pd.to_datetime(o["DATE"])
    m = pd.DataFrame({
        "gid": o["gid"], "date": o["date"],
        "close_total": pd.to_numeric(o["CLOSING TOTAL_H"], errors="coerce"),
        "open_total": pd.to_numeric(o["OPENING TOTAL_H"], errors="coerce"),
        "pts_h": pd.to_numeric(o["PTS_H"], errors="coerce"),
        "pts_r": pd.to_numeric(o["PTS_R"], errors="coerce")})
    return m[m["close_total"].between(150, 300)
             & m["open_total"].between(150, 300)].dropna()


def team_projection(mins, off, dfn, home_lu, away_lu):
    """5 x minutes-weighted mean rating for each side."""
    def proj(players, ratings):
        w = np.array([mins.get(p, 0.0) for p in players], dtype=float)
        r = np.array([ratings.get(p, 0.0) for p in players], dtype=float)
        return 5.0 * (w @ r / w.sum()) if w.sum() > 0 else np.nan
    return proj(home_lu, off), proj(away_lu, dfn)


def main():
    st = load_stints()
    md = game_dates()
    st = st.merge(md[["gid", "date"]], on="gid", how="inner")
    st = st.sort_values("date").reset_index(drop=True)
    print(f"stints with odds: {len(st):,} over {st['gid'].nunique():,} games", flush=True)

    obs = to_observations(st)
    obs = obs.merge(st[["gid", "date"]].drop_duplicates(), on="gid", how="left")
    mins = player_minutes(st)
    mins = mins.merge(st[["gid", "date"]].drop_duplicates(), on="gid", how="left")

    # roster of each team-game, and each team's players
    rost = []
    for col, side in (("home_lineup", "H"), ("away_lineup", "R")):
        e = st[["gid", "date", "season", col]].explode(col)
        e = e.rename(columns={col: "pid"})
        e["side"] = side
        rost.append(e)
    rost = pd.concat(rost, ignore_index=True).dropna(subset=["pid"])
    rost["pid"] = rost["pid"].astype("int64")
    rost = rost.drop_duplicates(subset=["gid", "side", "pid"])

    games = md[md["gid"].isin(st["gid"])].sort_values("date").reset_index(drop=True)
    games["total"] = games["pts_h"] + games["pts_r"]

    dates = games["date"].to_numpy()
    cuts = pd.date_range(pd.Timestamp(dates[SCORE_MIN // 2]),
                         pd.Timestamp(dates.max()) + pd.Timedelta(days=1),
                         freq=f"{REFIT_DAYS}D")
    print(f"{len(cuts)} RAPM refits", flush=True)

    # minutes per player: actual (this game) and lagged (trailing 5 games)
    mins_sorted = mins.sort_values("date")
    mins_sorted["lag_secs"] = (mins_sorted.groupby(["season", "pid"])["seconds"]
                               .transform(lambda s: s.shift(1).rolling(5, min_periods=1).mean()))
    actual_map = {(g, p): s for g, p, s in
                  zip(mins_sorted["gid"], mins_sorted["pid"], mins_sorted["seconds"])}
    lagged_map = {(g, p): s for g, p, s in
                  zip(mins_sorted["gid"], mins_sorted["pid"], mins_sorted["lag_secs"])}

    feats = {k: [] for k in ("gid", "D_off_h", "D_def_h", "D_off_a", "D_def_a",
                             "E_off_h", "E_def_h", "E_off_a", "E_def_a")}
    lineups = {(g, s): tuple(v) for (g, s), v in
               rost.groupby(["gid", "side"])["pid"].apply(tuple).items()}

    for i, cut in enumerate(cuts):
        nxt = cuts[i + 1] if i + 1 < len(cuts) else pd.Timestamp(dates.max()) + pd.Timedelta(days=1)
        tr = obs[obs["date"] < cut]
        if len(tr) < 20000:
            continue
        seasons = sorted(tr["season"].unique())[-TRAIN_SEASONS:]
        tr = tr[tr["season"].isin(seasons)]
        off, dfn, b0, bh = fit_rapm(tr)
        offd, dfnd = off.to_dict(), dfn.to_dict()

        blk = games[(games["date"] >= cut) & (games["date"] < nxt)]
        for gid in blk["gid"]:
            h = lineups.get((gid, "H"), ())
            a = lineups.get((gid, "R"), ())
            if not h or not a:
                continue
            for tag, mp in (("D", actual_map), ("E", lagged_map)):
                mh = {p: mp.get((gid, p), 0.0) or 0.0 for p in h}
                ma = {p: mp.get((gid, p), 0.0) or 0.0 for p in a}
                oh = 5 * sum(mh[p] * offd.get(p, 0.0) for p in h) / max(sum(mh.values()), 1)
                dh = 5 * sum(mh[p] * dfnd.get(p, 0.0) for p in h) / max(sum(mh.values()), 1)
                oa = 5 * sum(ma[p] * offd.get(p, 0.0) for p in a) / max(sum(ma.values()), 1)
                da = 5 * sum(ma[p] * dfnd.get(p, 0.0) for p in a) / max(sum(ma.values()), 1)
                feats[f"{tag}_off_h"].append(oh); feats[f"{tag}_def_h"].append(dh)
                feats[f"{tag}_off_a"].append(oa); feats[f"{tag}_def_a"].append(da)
            feats["gid"].append(gid)
        print(f"  refit {i + 1}/{len(cuts)} @ {cut.date()}  train obs {len(tr):,}  "
              f"players {len(off):,}  games projected {len(feats['gid']):,}", flush=True)

    F = pd.DataFrame(feats).merge(games, on="gid", how="inner").sort_values("date")
    F = F.reset_index(drop=True)
    print(f"\nprojected {len(F):,} games", flush=True)

    rows = []
    for tag, label in (("D", "D RAPM actual minutes (LOOK-AHEAD)"),
                       ("E", "E RAPM lagged minutes (tradable)")):
        cols = [f"{tag}_off_h", f"{tag}_def_h", f"{tag}_off_a", f"{tag}_def_a"]
        d = F.dropna(subset=cols).reset_index(drop=True)
        d["pred"] = wf_xgb(d[cols].values, d["total"].values.astype(float),
                           d["date"].values, SCORE_MIN, depth=3, n_est=150, lr=0.05)
        d = d.dropna(subset=["pred"]).reset_index(drop=True)
        d["cal"] = wf_calibrate(d["pred"].values, d["total"].values, CAL_MIN)
        d = d.dropna(subset=["cal"])
        rmse = float(np.sqrt(np.mean((d["cal"] - d["total"]) ** 2)))
        line = float(np.sqrt(np.mean((d["close_total"] - d["total"]) ** 2)))
        rows.append({"set": label, "n": len(d), "total RMSE": rmse,
                     "line RMSE": line, "gap": rmse - line})
        print(f"{label:38} RMSE {rmse:.3f}  line {line:.3f}  gap {rmse - line:+.3f}",
              flush=True)
    pd.DataFrame(rows).to_csv("rapm_results.csv", index=False)
    F.to_parquet("/home/dpope/data/rapm_features.parquet", index=False)
    print("\n" + pd.DataFrame(rows).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
