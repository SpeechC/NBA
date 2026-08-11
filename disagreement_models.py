"""Alternative disagreement models.

`dis_open` -- our total forecast minus the opening total -- is the single largest
driver of the movement model, so its quality caps everything downstream. The
version used so far is the paper's construction: predict each team's score from
4-game lagged means, sum the two.

Three things it never tried, all built here:

  A. sum-of-two-teams, lag 4              (current; the paper's construction)
  B. direct total model, lag 4            (optimise the quantity we actually use)
  C. longer / decayed windows             (the replication found lag 6 beat lag 4
                                           monotonically, yet every betting model
                                           has used lag 4 because the paper did)
  D. opponent-adjusted pace x efficiency  (structural: a total is possessions times
                                           efficiency, and raw OEFF/DEFF are
                                           schedule-dependent -- a team that faced
                                           four elite defences looks bad)

D solves, on games finished before each refit, the standard adjusted-rating system

    OEFF_ij = mu + home + off_i - def_j
    PACE_ij = mu_p + pace_i + pace_j

by ridge, then predicts total = pace_hat * (oeff_home + oeff_away) / 100.
"""

import numpy as np
import pandas as pd

TEAMS = None


def _design(teams_i, teams_j, teams, home=None):
    n, k = len(teams_i), len(teams)
    idx = {t: i for i, t in enumerate(teams)}
    X = np.zeros((n, 1 + (1 if home is not None else 0) + 2 * k))
    X[:, 0] = 1.0
    off = 1 + (1 if home is not None else 0)
    if home is not None:
        X[:, 1] = home
    for r, (a, b) in enumerate(zip(teams_i, teams_j)):
        X[r, off + idx[a]] = 1.0
        X[r, off + k + idx[b]] = -1.0
    return X


def adjusted_ratings(hist, teams, alpha=25.0):
    """Ridge-fit offence/defence and pace ratings from finished games."""
    X = _design(hist["team"].values, hist["opp"].values, teams, hist["home"].values)
    y = hist["OEFF"].values
    A = X.T @ X + alpha * np.eye(X.shape[1])
    A[0, 0] -= alpha
    off_coef = np.linalg.solve(A, X.T @ y)

    # pace is symmetric: both teams contribute additively
    k = len(teams)
    idx = {t: i for i, t in enumerate(teams)}
    Xp = np.zeros((len(hist), 1 + k))
    Xp[:, 0] = 1.0
    for r, (a, b) in enumerate(zip(hist["team"].values, hist["opp"].values)):
        Xp[r, 1 + idx[a]] += 1.0
        Xp[r, 1 + idx[b]] += 1.0
    Ap = Xp.T @ Xp + alpha * np.eye(Xp.shape[1])
    Ap[0, 0] -= alpha
    pace_coef = np.linalg.solve(Ap, Xp.T @ hist["PACE"].values)
    return off_coef, pace_coef, idx


def predict_adjusted(off_coef, pace_coef, idx, home_team, away_team, k):
    mu, hfa = off_coef[0], off_coef[1]
    o = off_coef[2:2 + k]
    d = off_coef[2 + k:]
    ih, ia = idx.get(home_team), idx.get(away_team)
    if ih is None or ia is None:
        return np.nan
    oeff_h = mu + hfa + o[ih] - d[ia]
    oeff_a = mu + o[ia] - d[ih]
    pace = pace_coef[0] + pace_coef[1 + ih] + pace_coef[1 + ia]
    return pace * (oeff_h + oeff_a) / 100.0


def walk_forward_adjusted(games, refit_days=7, min_games=300):
    """games: one row per game with team/opp/OEFF/PACE for both sides already stacked."""
    long = games
    out = pd.Series(np.nan, index=games.index)
    return out
