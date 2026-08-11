"""Walk-forward player impact (RAPM) and team projection from lineups.

Model. Each stint contributes two observations, one per offensive team. For an
offensive team O facing defensive team D, points per 100 possessions is regressed
on indicators for the five offensive players (an offence rating each) and the five
defensive players (a defence rating each), plus a home-court term:

    PPP100 ~ intercept + home + sum(off_i for i in O) + sum(def_j for j in D)

Sign convention: the target is points scored BY THE OFFENCE, so a good defender
carries a NEGATIVE defensive coefficient. Total impact is `off - def`, not
`off + def` -- adding them ranks Gobert and Draymond Green among the worst players
in the league, which is how the error announces itself.

Solved by ridge, weighted by possessions. Ridge is not optional: five players
always appear together, so the design is severely collinear and unregularised APM
produces nonsense.

Two ways to project a team, and the difference decides whether a result is real:

  * `actual`  — weight each player's rating by the minutes they actually played
    that night. This is LOOK-AHEAD: on the morning of the game you do not know
    who will play. It measures the ceiling — what a perfect availability feed
    would be worth — and must never be quoted as a backtest result.
  * `lagged`  — weight by minutes played in the team's previous games. Known
    before tip, so it is honestly tradable, but it reacts to an absence one game
    late, which is exactly the lag the market does not have.

Reporting both is the point: `actual` bounds the opportunity, `lagged` measures
what is capturable without an injury feed. If `actual` does not beat the closing
line, no injury feed will rescue the approach and the personnel thesis is dead.
"""

import ast

import numpy as np
import pandas as pd
from scipy import sparse
from scipy.sparse.linalg import lsqr

STINTS = "/home/dpope/data/stints_all.parquet"
MIN_POSS = 1        # drop empty stints
RIDGE_ALPHA = 2000  # possessions-weighted; tuned only on the first training window


def load_stints(path=STINTS):
    st = pd.read_parquet(path)
    st["home_lineup"] = st["home_lineup"].apply(ast.literal_eval)
    st["away_lineup"] = st["away_lineup"].apply(ast.literal_eval)
    st = st[(st["n_home"] == 5) & (st["n_away"] == 5)].copy()
    return st


def to_observations(st):
    """One row per (stint, offensive team)."""
    a = pd.DataFrame({
        "gid": st["gid"], "season": st["season"],
        "off": st["home_lineup"], "dfn": st["away_lineup"],
        "poss": st["poss_home"], "pts": st["pts_home"], "is_home_off": 1})
    b = pd.DataFrame({
        "gid": st["gid"], "season": st["season"],
        "off": st["away_lineup"], "dfn": st["home_lineup"],
        "poss": st["poss_away"], "pts": st["pts_away"], "is_home_off": 0})
    obs = pd.concat([a, b], ignore_index=True)
    return obs[obs["poss"] >= MIN_POSS].reset_index(drop=True)


def fit_rapm(obs, alpha=RIDGE_ALPHA):
    """Ridge on possession-weighted PPP100. Returns (off_rating, def_rating, intercept)."""
    players = pd.unique(np.concatenate([
        np.concatenate(obs["off"].to_numpy()),
        np.concatenate(obs["dfn"].to_numpy())]))
    idx = {p: i for i, p in enumerate(players)}
    n, k = len(obs), len(players)

    rows, cols, vals = [], [], []
    for r, (o, d) in enumerate(zip(obs["off"], obs["dfn"])):
        for p in o:
            rows.append(r); cols.append(idx[p]); vals.append(1.0)
        for p in d:
            rows.append(r); cols.append(k + idx[p]); vals.append(1.0)
    rows += list(range(n)); cols += [2 * k] * n; vals += [1.0] * n           # intercept
    rows += list(range(n)); cols += [2 * k + 1] * n
    vals += obs["is_home_off"].astype(float).tolist()                         # home term

    X = sparse.csr_matrix((vals, (rows, cols)), shape=(n, 2 * k + 2))
    y = 100.0 * obs["pts"].to_numpy() / obs["poss"].to_numpy()
    w = np.sqrt(obs["poss"].to_numpy(dtype=float))
    Xw = sparse.diags(w) @ X
    yw = y * w

    # ridge via augmentation (do not penalise intercept or home term)
    pen = np.sqrt(alpha) * np.ones(2 * k + 2)
    pen[-2:] = 0.0
    A = sparse.vstack([Xw, sparse.diags(pen)]).tocsr()
    b = np.concatenate([yw, np.zeros(2 * k + 2)])
    sol = lsqr(A, b, atol=1e-8, btol=1e-8, iter_lim=500)[0]

    off = pd.Series(sol[:k], index=players)
    dfn = pd.Series(sol[k:2 * k], index=players)
    return off, dfn, sol[2 * k], sol[2 * k + 1]


def player_minutes(st):
    """Minutes per (gid, player), from stint durations."""
    rows = []
    for lu_col in ("home_lineup", "away_lineup"):
        e = st[["gid", "season", "seconds", lu_col]].explode(lu_col)
        e = e.rename(columns={lu_col: "pid"})
        rows.append(e)
    m = pd.concat(rows, ignore_index=True).dropna(subset=["pid"])
    m["pid"] = m["pid"].astype("int64")
    return m.groupby(["gid", "season", "pid"])["seconds"].sum().reset_index()
