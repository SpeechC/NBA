"""Build the paper's team-game panel and lagged designed features.

Chen, Jhou, Lee & Lu (2021), Entropy 23(4), 477.

Step 1 of the paper's scheme: each game contributes two rows (home team and
away team), 13 box-score variables per row plus the team's final score as the
target. Variables are min-max normalised, then each designed feature is the mean
of the normalised variable over the previous l games (l = 1..6), so the first six
games of a team's season are dropped.
"""

import numpy as np
import pandas as pd

CSV = "/mnt/c/NBA2/dfMaster_OT.csv"  # complete file: includes overtime games

# paper Table 1 order: V1..V13
VARS = ["2PA", "2P%", "3PA", "3P%", "FTA", "FT%", "ORB", "DRB",
        "AST", "STL", "BLK", "TOV", "PF"]


# the file labels seasons in two different columns: the original one covers
# 2017-18 and 2018-19, the BigDataBall one covers 2020-21 onward.
SEASON_COLS = ["DATASET_H", "BIGDATABALL\nDATASET_H"]


def season_label(raw):
    return raw[SEASON_COLS[0]].fillna(raw[SEASON_COLS[1]])


def _side(df, suf):
    """Extract one side (H or R) of a game as a team-game row."""
    g = pd.DataFrame({
        "game_id": df["GAME-ID"],
        "date": pd.to_datetime(df["DATE"]),
        "season": df["season"],
        "team": df[f"TEAM_{suf}"],
        "home": 1 if suf == "H" else 0,
    })
    fg, fga = df[f"FG_{suf}"], df[f"FGA_{suf}"]
    p3, p3a = df[f"3P_{suf}"], df[f"3PA_{suf}"]
    ft, fta = df[f"FT_{suf}"], df[f"FTA_{suf}"]
    g["2PA"] = fga - p3a
    g["2P%"] = (fg - p3) / (fga - p3a)
    g["3PA"] = p3a
    g["3P%"] = np.where(p3a > 0, p3 / p3a.replace(0, np.nan), 0.0)
    g["FTA"] = fta
    g["FT%"] = np.where(fta > 0, ft / fta.replace(0, np.nan), 0.0)
    g["ORB"] = df[f"OR_{suf}"]
    g["DRB"] = df[f"DR_{suf}"]
    g["AST"] = df[f"A_{suf}"]
    g["STL"] = df[f"ST_{suf}"]
    g["BLK"] = df[f"BL_{suf}"]
    g["TOV"] = df[f"TO_{suf}"]
    g["PF"] = df[f"PF_{suf}"]
    g["Y"] = df[f"PTS_{suf}"]
    return g


def all_seasons():
    raw = pd.read_csv(CSV, low_memory=False, usecols=SEASON_COLS)
    s = season_label(raw)
    return sorted(s[s.str.contains("Regular Season", na=False)].unique())


def load_panel(season="NBA 2018-2019 Regular Season"):
    """season: a season label, or None for every regular season pooled."""
    raw = pd.read_csv(CSV, low_memory=False)
    raw["season"] = season_label(raw)
    if season is None:
        raw = raw[raw["season"].str.contains("Regular Season", na=False)].copy()
    else:
        raw = raw[raw["season"] == season].copy()
    panel = pd.concat([_side(raw, "H"), _side(raw, "R")], ignore_index=True)
    panel = panel.sort_values(["season", "team", "date", "game_id"]).reset_index(drop=True)
    panel[VARS] = panel[VARS].astype(float)
    # game index restarts each season, so lag windows never cross a season boundary
    panel["game_no"] = panel.groupby(["season", "team"]).cumcount() + 1
    return panel


def designed_features(panel, max_lag=6):
    """Min-max normalise, then average each variable over the previous l games."""
    norm = panel.copy()
    # normalise within season: the paper works inside one season, and league-wide
    # shooting rates drift enough over 2017-2024 to make a pooled min-max misleading
    norm[VARS] = norm.groupby("season")[VARS].transform(lambda c: (c - c.min()) / (c.max() - c.min()))

    out = {}
    for l in range(1, max_lag + 1):
        feats = (norm.groupby(["season", "team"])[VARS]
                     .apply(lambda g: g.shift(1).rolling(l).mean())
                     .reset_index(level=[0, 1], drop=True)
                     .sort_index())
        d = pd.concat([norm[["season", "team", "game_no", "Y"]], feats], axis=1)
        # keep t >= 7 for every l so all six models share one sample set
        d = d[norm["game_no"] >= max_lag + 1].dropna().reset_index(drop=True)
        out[l] = d
    return out


if __name__ == "__main__":
    print("seasons:", *all_seasons(), sep="\n  ")
    for s in all_seasons() + [None]:
        p = load_panel(s)
        n = p.groupby(["season", "team"]).size()
        d = designed_features(p)
        print(f"{str(s):32} team-games={len(p):5d}  games/team={n.min()}-{n.max()}"
              f"  modelled={len(d[4]):5d}")
    print(d[4].head().to_string())
