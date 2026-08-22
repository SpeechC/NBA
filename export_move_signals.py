"""Export the frozen per-game OOS movement predictions as a sidecar for the
structural research agent (and any other consumer).

Writes C:\\NBA2\\move_signal_states.csv (/mnt/c/NBA2/move_signal_states.csv):

    GAME-ID              vendor game id (string, matches dfMaster)
    SEASON               start year of the season label (2017 = 2017-18)
    DATE                 YYYY-MM-DD
    MOVE_RIDGE_OOS       walk-forward ridge forecast of (close - open) total,
                         from movement_full.py (7-day refits, min 500 games,
                         clean rows only). NaN where unavailable.
    MOVE_LATENT_OOS      error-only latent forecast of the same target,
                         season-fold walk-forward (train <= N, test N+1),
                         opening_line_error_decomposition.py matrix. NaN for
                         2017-2018 (burn-in folds) and games where either team
                         has < 10 prior games in season.
    MOVE_COMBINED_OOS    recursive combiner (weights fit on PRIOR OOS seasons
                         only, move_combined_econ.py). NaN for the first joint
                         season (2020-21). THIS is the historical MOVE_COMBINED
                         evaluation series.

EVERY VALUE IS STRICTLY OUT-OF-SAMPLE for its own game: no row's prediction
was produced by any model that saw that game, its season (latent/combined
weights), or any later game. Pregame-safe by construction; the inputs are
prior games and the OPENING line only.

FOR 2026-27 these historical values are NOT the deployment path -- live
generation uses the frozen mapping of PREREG_move_combined.md
(m = 0.0337 + 0.8402*ridge + 0.6869*latent, latent mapping fit once through
2025-26). This file is the frozen HISTORICAL record for incremental testing:
any candidate movement state must survive jointly with these columns, not
alone.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import opening_line_error_decomposition as OLE
import resid_variance as RV

OUT = "/mnt/c/NBA2/move_signal_states.csv"


def main():
    g = OLE.load()
    X, fc = OLE.design_matrix(g)
    lat = RV.pca_oos(X, fc, ["tmove"])["tmove"]
    D = X[["gid", "season", "date", "tmove"]].copy()
    D["MOVE_LATENT_OOS"] = lat

    mv = pd.read_csv("movement_full_games.csv",
                     usecols=["game_id", "pred_move", "clean"])
    mv["gid"] = mv["game_id"].astype(str).str.strip()
    mv = mv.loc[mv["clean"] == True, ["gid", "pred_move"]] \
        .rename(columns={"pred_move": "MOVE_RIDGE_OOS"})
    # start from the FULL game universe so ridge-only games are kept too
    base = g[["gid", "season", "date"]].merge(
        D[["gid", "MOVE_LATENT_OOS", "tmove"]], on="gid", how="left")
    base = base.merge(mv, on="gid", how="left")

    # recursive combiner on games where BOTH components exist
    both = base.dropna(subset=["MOVE_RIDGE_OOS", "MOVE_LATENT_OOS"]).copy()
    seasons = sorted(both["season"].unique())
    base["MOVE_COMBINED_OOS"] = np.nan
    for i, yr in enumerate(seasons):
        if i == 0:
            continue
        tr = both["season"] < yr
        te = both["season"] == yr
        A = np.column_stack([np.ones(tr.sum()),
                             both.loc[tr, "MOVE_RIDGE_OOS"],
                             both.loc[tr, "MOVE_LATENT_OOS"]])
        b, *_ = np.linalg.lstsq(A, both.loc[tr, "tmove"], rcond=None)
        pred = (b[0] + b[1] * both.loc[te, "MOVE_RIDGE_OOS"]
                + b[2] * both.loc[te, "MOVE_LATENT_OOS"])
        base.loc[base["gid"].isin(both.loc[te, "gid"]),
                 "MOVE_COMBINED_OOS"] = pred.values

    out = pd.DataFrame({
        "GAME-ID": base["gid"],
        "SEASON": base["season"],
        "DATE": base["date"].dt.strftime("%Y-%m-%d"),
        "MOVE_RIDGE_OOS": base["MOVE_RIDGE_OOS"].round(4),
        "MOVE_LATENT_OOS": base["MOVE_LATENT_OOS"].round(4),
        "MOVE_COMBINED_OOS": base["MOVE_COMBINED_OOS"].round(4)})
    assert not out["GAME-ID"].duplicated().any()
    out.to_csv(OUT, index=False)

    print(f"wrote {OUT}   {len(out):,} games (full regular-season universe)")
    cov = out.assign(
        R=out["MOVE_RIDGE_OOS"].notna(), L=out["MOVE_LATENT_OOS"].notna(),
        C=out["MOVE_COMBINED_OOS"].notna()).groupby("SEASON")[
        ["R", "L", "C"]].sum()
    cov["games"] = out.groupby("SEASON").size()
    print(cov.to_string())
    # provenance check vs the committed economics
    chk = base.dropna(subset=["MOVE_COMBINED_OOS"])
    cr = np.corrcoef(chk["MOVE_COMBINED_OOS"], chk["tmove"])[0, 1]
    print(f"\nsanity: corr(MOVE_COMBINED_OOS, realized move) = {cr:+.4f} "
          f"on {len(chk):,} games  [move_combined_econ.py: +0.2540 on the "
          f"2021-2025 slice]")


if __name__ == "__main__":
    main()
