"""Build PRIOR-ONLY lineup-cohesion features from the stint panel.

"Tonight's lineup" is same-game information and is never used. The expected
rotation for game t is taken from the team's previous ROT_W games, and pairwise
familiarity is accumulated strictly from games before t within the season.

Writes cohesion_panel.csv (one row per game-team).
"""
import itertools
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

SRC = "/mnt/c/NBA2/out/pbp_lineups_all.parquet"
ROT_W = 5            # games used to infer the expected rotation
TOPN = 10            # rotation size
PAIRS = list(itertools.combinations(range(5), 2))     # 10 pairs per 5-man unit


def load_season(season):
    cols = (["GAME_ID", "PERIOD", "STARTTIME", "ENDTIME", "GAMEDATE", "SEASON",
             "SEASON_TYPE", "PLAYER1_ID", "PLAYER1_TEAM_ABBREVIATION"]
            + [f"PLAYER{i}" for i in range(1, 11)])
    d = pd.read_parquet(SRC, columns=cols,
                        filters=[("SEASON", "==", season),
                                 ("SEASON_TYPE", "==", "RegularSeason")])
    # player -> team map for this season, from event rows
    pt = d.loc[d.PLAYER1_ID.gt(0) & d.PLAYER1_TEAM_ABBREVIATION.notna(),
               ["PLAYER1_ID", "PLAYER1_TEAM_ABBREVIATION"]]
    pmap = (pt.groupby("PLAYER1_ID").PLAYER1_TEAM_ABBREVIATION
              .agg(lambda s: s.value_counts().idxmax()))

    st = d.dropna(subset=["STARTTIME", "ENDTIME"]).drop_duplicates(
        subset=["GAME_ID", "PERIOD", "STARTTIME", "ENDTIME"]
        + [f"PLAYER{i}" for i in range(1, 11)]).copy()
    st["dur"] = (st.ENDTIME - st.STARTTIME).clip(lower=0)
    return st, pmap


def side_frames(st, pmap):
    """Split each stint into its two 5-man units, tagged with the team."""
    out = []
    for lo, hi in ((1, 6), (6, 11)):
        cols = [f"PLAYER{i}" for i in range(lo, hi)]
        f = st[["GAME_ID", "GAMEDATE", "dur"] + cols].copy()
        f.columns = ["gid", "gdate", "dur"] + [f"p{i}" for i in range(5)]
        # A player traded mid-season has ONE modal team, so keying the unit off
        # a single slot mislabels every game he played for the other club and
        # yields >2 team labels per game. Resolve the team ONCE PER GAME-SIDE by
        # the modal label over every slot of every stint in that game-side --
        # a vectorised groupby, not a per-row vote (which was ~50x slower).
        lab = pd.concat([f[["gid"]].assign(lab=f[f"p{i}"].map(pmap))
                         for i in range(5)])
        mode = (lab.dropna().groupby(["gid", "lab"]).size()
                .reset_index(name="n").sort_values("n")
                .drop_duplicates("gid", keep="last").set_index("gid")["lab"])
        f["team"] = f["gid"].map(mode)
        out.append(f)
    return out


def accumulate(frames):
    """Per (gid, team): player seconds and pairwise co-seconds."""
    mins, cop = [], []
    for f in frames:
        f = f.dropna(subset=["team"])
        for i in range(5):
            mins.append(f[["gid", "team", f"p{i}", "dur"]]
                        .rename(columns={f"p{i}": "pid"}))
        a = f[[f"p{i}" for i in range(5)]].values.astype(np.int64)
        for i, j in PAIRS:
            lo = np.minimum(a[:, i], a[:, j])
            hi = np.maximum(a[:, i], a[:, j])
            cop.append(pd.DataFrame({"gid": f.gid.values, "team": f.team.values,
                                     "pair": lo * 10**9 + hi,
                                     "dur": f.dur.values}))
    M = (pd.concat(mins).groupby(["gid", "team", "pid"], as_index=False)
         .dur.sum().rename(columns={"dur": "secs"}))
    C = (pd.concat(cop).groupby(["gid", "team", "pair"], as_index=False)
         .dur.sum().rename(columns={"dur": "cosecs"}))
    return M, C


def cohesion_for_season(season):
    st, pmap = load_season(season)
    if st.empty:
        return pd.DataFrame()
    frames = side_frames(st, pmap)
    M, C = accumulate(frames)

    order = (st[["GAME_ID", "GAMEDATE"]].drop_duplicates()
             .rename(columns={"GAME_ID": "gid", "GAMEDATE": "gdate"}))
    order["gdate"] = pd.to_datetime(order.gdate)
    order = order.sort_values("gdate").reset_index(drop=True)
    M = M.merge(order, on="gid")
    C = C.merge(order, on="gid")

    rows = []
    for team, mt in M.groupby("team"):
        ct = C[C.team == team]
        gs = order[order.gid.isin(mt.gid.unique())].sort_values("gdate")
        gids = gs.gid.tolist()
        # cumulative prior co-seconds per pair, and prior minutes per player
        prior_co = {}
        mt_by_g = {g: x for g, x in mt.groupby("gid")}
        ct_by_g = {g: x for g, x in ct.groupby("gid")}
        recent = []                      # last ROT_W games' player-second maps
        for gi, g in enumerate(gids):
            if gi >= 1 and recent:
                agg = {}
                for r in recent[-ROT_W:]:
                    for pid, s in r.items():
                        agg[pid] = agg.get(pid, 0.0) + s
                top = sorted(agg.items(), key=lambda kv: -kv[1])[:TOPN]
                tot = sum(v for _, v in top)
                if tot > 0 and len(top) >= 5:
                    w = {p: v / tot for p, v in top}
                    num = den = 0.0
                    ids = list(w)
                    for a in range(len(ids)):
                        for b in range(a + 1, len(ids)):
                            i, j = ids[a], ids[b]
                            lo, hi = (i, j) if i < j else (j, i)
                            co = prior_co.get(lo * 10**9 + hi, 0.0)
                            ww = w[i] * w[j]
                            num += ww * np.log1p(co / 60.0)
                            den += ww
                    rows.append({"gid": g, "team": team, "season": season,
                                 "cohesion": num / den if den else np.nan,
                                 "gameno": gi,
                                 "rot_size": len(top),
                                 "prior_games": len(recent)})
            if g in mt_by_g:
                recent.append(dict(zip(mt_by_g[g].pid, mt_by_g[g].secs)))
            if g in ct_by_g:
                x = ct_by_g[g]
                for p, s in zip(x.pair.values, x.cosecs.values):
                    prior_co[p] = prior_co.get(p, 0.0) + s
    return pd.DataFrame(rows)


def main():
    seasons = ["2017-18", "2018-19", "2020-21", "2021-22",
               "2022-23", "2023-24", "2024-25"]
    all_rows = []
    for s in seasons:
        r = cohesion_for_season(s)
        print(f"  {s}: {len(r):,} game-teams   "
              f"cohesion mean {r.cohesion.mean():.3f} sd {r.cohesion.std():.3f}",
              flush=True)
        all_rows.append(r)
    d = pd.concat(all_rows, ignore_index=True)
    # gate: a game must contribute exactly two team rows
    n_per = d.groupby("gid").size()
    bad = n_per[n_per != 2]
    print(f"\n  games with != 2 team rows: {len(bad):,} of {len(n_per):,} "
          f"({100*len(bad)/len(n_per):.2f}%) -- dropped")
    d = d[d.gid.isin(n_per[n_per == 2].index)]
    d.to_csv("cohesion_panel.csv", index=False)
    print(f"\nwrote cohesion_panel.csv  {len(d):,} game-teams, "
          f"{d.gid.nunique():,} games")


if __name__ == "__main__":
    main()
