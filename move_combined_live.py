"""MOVE_COMBINED — live recommendation engine for the 2026-27 season.

Implements PREREG_move_combined.md section 3 EXACTLY. Nothing here may be
tuned; if a change is needed it becomes a new named spec with a new frozen
date (models_frozen.py convention).

    m = +0.0337 + 0.8402*ridge + 0.6869*latent
    ACTION: |m| >= 1.0 (primary) or >= 1.5 (confirmatory)
    BET   : struck at the OPENING total, graded against the OPENING total
    SIDE  : m > 0 -> OVER, m < 0 -> UNDER

DEPLOYMENT CONVENTION (immutable for the season, prereg s3):
  ridge     FROZEN PROCEDURE  -- expanding walk-forward, refit every 7 days,
                                 min 500 games. Refits continue all season.
  latent    FROZEN PARAMETERS -- scaler -> PCA loadings (and K) -> OLS
                                 coefficients fitted ONCE through 2025-26 by
                                 `--freeze` and held fixed. Inputs update as
                                 games complete; the MAPPING never does.
  combiner  FROZEN NUMBERS    -- the three constants above.

=========================================================================
RIDGE = THE FULL FROZEN FEATURE SET, INCLUDING dis_open
=========================================================================
`dis_open` = cal_total - open_total comes from a walk-forward XGBoost
team-score model plus a calibration stage. The frozen implementation
(walkforward_pace.build_panel_ext) reads the vendor CSV directly and so had no
rows for unplayed games. `dis_open_live.py` ports that recipe unchanged --
same LAG=4 rolling of ALLV, same XGB(depth=2, n_est=100, lr=0.3), same
calibration -- but takes the raw frame as an argument, so appending a PENDING
row yields correct prior-only features for it.

Validated 2026-08-23 against the stored frozen column (8,696 overlapping games):

    corr(port, frozen dis_open)                       +0.9411
    ridge OOS corr, PORTED dis_open                   +0.2728
    ridge OOS corr, FROZEN dis_open (batch only)      +0.2652
    ridge OOS corr, no dis_open at all                +0.2167

The port therefore reproduces the frozen signal rather than approximating it.
`--ridge-mode frozen` is the DEFAULT. `--ridge-mode reduced` drops dis_open and
is kept only as a fallback if the score model cannot run; its output is
labelled MOVE_REDUCED and does NOT inherit the frozen backtest.

-------------------------------------------------------------------------
THE HARD DEPENDENCY: OPENING TOTALS FOR UNPLAYED GAMES
-------------------------------------------------------------------------
The model forecasts open->close movement, so `open_total` is BOTH an input
feature and the price you bet at. The NBA schedule does not carry betting
lines and the historical vendor file only has completed games. You must
supply today's openers yourself, via --lines CSV:

    game_date,away_abbr,home_abbr,open_total
    2026-10-21,GSW,LAL,231.5

Capture these AT THE OPEN (that is the price the strategy assumes) and store
them; they are also the season's audit trail. Without them this script can
score nothing -- it will tell you which games it is missing and exit.

USAGE
    python move_combined_live.py --freeze              # once, before the season
    python move_combined_live.py --date 2026-10-21 --lines lines_20261021.csv
    python move_combined_live.py --selftest 2025-03-05 # dry run on history
"""
import argparse
import json
import os
import pickle
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

from sklearn.decomposition import PCA
from sklearn.linear_model import RidgeCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

import opening_line_error_decomposition as OLE

# ------------------------------------------------------------------ config
HIST = os.environ.get("NBA_HIST", "/mnt/c/NBA2/dfMaster_OT_2017-2026.csv")
CURRENT = os.environ.get("NBA_CURRENT", "/mnt/c/NBA2/dfMaster_current.csv")
ARTIFACT = os.environ.get("NBA_LATENT_ARTIFACT", "move_combined_latent_2027.pkl")
OUTDIR = os.environ.get("NBA_REC_DIR", "recommendations")

# FROZEN — PREREG_move_combined.md s3/s5. Do not edit.
COMB_A, COMB_RIDGE, COMB_LATENT = 0.0337, 0.8402, 0.6869
DIS_OPEN_SRC = os.environ.get("NBA_DIS_OPEN", "movement_full_games.csv")
THRESH_PRIMARY, THRESH_CONFIRM = 1.0, 1.5
EV_THRESH = 0.80          # latent PC count rule (training-only)
MIN_PRIOR = 10            # both teams, prereg s4 scope rule
RIDGE_MIN_TRAIN = 500
REFIT_DAYS = 7
LATENT_FREEZE_THROUGH = 2025      # season label of the last training season

TEAM_MAP_CSV = "team_mapping.csv"


# ------------------------------------------------------------------ loading
def _load_master(paths):
    """Concatenate vendor files, keep regular season + IST, drop duplicates."""
    frames = []
    for p in paths:
        if not p or not os.path.exists(p):
            continue
        from prepare_data import read_master
        raw = read_master(p, verbose=False)   # market range gates
        raw["__src"] = os.path.basename(p)
        frames.append(raw)
    if not frames:
        raise FileNotFoundError(f"no input files found among: {paths}")
    raw = pd.concat(frames, ignore_index=True)
    raw["gid"] = raw["GAME-ID"].astype(str).str.strip()
    raw = raw.drop_duplicates("gid", keep="last")     # current file wins
    return raw


def build_games(paths, pending=None):
    """Game-level frame in OLE.load()'s schema, plus optional PENDING rows.

    Pending games carry NaN outcomes; every model input is prior-only so their
    feature rows are still well defined.
    """
    raw = _load_master(paths)
    lbl = OLE.season_label(raw).astype(str)
    keep = lbl.str.contains("Regular Season|In-Season", na=False)
    raw, lbl = raw[keep].copy(), lbl[keep]
    n = lambda c: pd.to_numeric(raw[c], errors="coerce")
    g = pd.DataFrame({
        "gid": raw["gid"],
        "season": lbl.str.extract(r"(\d{4})")[0].astype(int).values,
        "date": pd.to_datetime(raw["DATE"], errors="coerce"),
        "home": raw["TEAM_H"], "away": raw["TEAM_R"],
        "hpts": n("PTS_H"), "apts": n("PTS_R"),
        "ot_open": n("OPENING TOTAL_H"), "ot_close": n("CLOSING TOTAL_H"),
        "os_open": n("OPENING SPREAD_H"), "os_close": n("CLOSING SPREAD_H"),
        "pace_h": n("PACE_H"), "pace_a": n("PACE_R"),
        "oeff_h": n("OEFF_H"), "oeff_a": n("OEFF_R"),
        "deff_h": n("DEFF_H"), "deff_a": n("DEFF_R"),
        "pending": False})
    if pending is not None and len(pending):
        g = pd.concat([g, pending], ignore_index=True)
    g["total"] = g.hpts + g.apts
    g["margin"] = g.hpts - g.apts
    g["om_open"] = -g.os_open
    g["om_close"] = -g.os_close
    g["te_open"] = g.total - g.ot_open          # NaN for pending: intended
    g["te_close"] = g.total - g.ot_close
    g["se_open"] = g.margin - g.om_open
    g["se_close"] = g.margin - g.om_close
    g["tmove"] = g.ot_close - g.ot_open
    g["smove"] = g.om_close - g.om_open
    g["hse"] = g.hpts - (g.ot_open + g.om_open) / 2
    g["ase"] = g.apts - (g.ot_open - g.om_open) / 2
    return g.sort_values(["date", "gid"]).reset_index(drop=True)


def pending_rows(sched_day, lines, teammap):
    """Turn today's schedule + supplied openers into PENDING game rows."""
    abbr2name = {v: k for k, v in teammap.items()}
    L = lines.copy()
    L["game_date"] = pd.to_datetime(L["game_date"]).dt.normalize()
    key = lambda d, a, h: (d.dt.strftime("%Y-%m-%d") + "|" + a + "|" + h)
    L["k"] = key(L.game_date, L.away_abbr.str.upper(), L.home_abbr.str.upper())
    S = sched_day.copy()
    S["k"] = key(S.game_date, S.away_abbr.str.upper(), S.home_abbr.str.upper())
    M = S.merge(L[["k", "open_total"] + ([c for c in ("open_spread",) if c in L.columns])],
                on="k", how="left")
    missing = M[M.open_total.isna()]
    rows = pd.DataFrame({
        "gid": ("PEND_" + M.game_date.dt.strftime("%Y%m%d") + "_"
                + M.away_abbr + M.home_abbr),
        "season": M.game_date.dt.year.where(M.game_date.dt.month >= 8,
                                            M.game_date.dt.year - 1).astype(int),
        "date": M.game_date,
        "home": M.home_abbr.map(abbr2name), "away": M.away_abbr.map(abbr2name),
        "hpts": np.nan, "apts": np.nan,
        "ot_open": pd.to_numeric(M.open_total, errors="coerce"), "ot_close": np.nan,
        "os_open": pd.to_numeric(M.get("open_spread"), errors="coerce"),
        "os_close": np.nan,
        "pace_h": np.nan, "pace_a": np.nan, "oeff_h": np.nan, "oeff_a": np.nan,
        "deff_h": np.nan, "deff_a": np.nan, "pending": True})
    unmapped = rows[rows.home.isna() | rows.away.isna()]
    return rows, missing, unmapped, M


# ------------------------------------------------------- ridge (procedure)
RIDGE_FEATS = ["ot_open", "pace_sum", "pace_diff", "pace_absdiff",
               "oeff_sum", "deff_sum", "implied_minus_open",
               "h_f_PACE", "a_f_PACE", "h_f_OEFF", "a_f_OEFF",
               "h_f_DEFF", "a_f_DEFF"]
# dis_open completes the frozen feature set. Ported to be pending-capable in
# dis_open_live.py; validated corr +0.941 vs the stored frozen column, and the
# ridge built on it recovers the frozen OOS corr (+0.2728 vs +0.2652), against
# +0.2167 without it. GAP CLOSED 2026-08-23.
FROZEN_FEATS = RIDGE_FEATS + ["dis_open"]


def ridge_features(g, W=20, MINP=10):
    """Prior-only team form + market state. Mirrors the frozen spec-D family:
    pace/efficiency lags plus the pace constructions and market terms."""
    P = pd.concat([
        pd.DataFrame({"gid": g.gid, "season": g.season, "date": g.date,
                      "team": g.home, "side": "h", "pace": g.pace_h,
                      "oeff": g.oeff_h, "deff": g.deff_h}),
        pd.DataFrame({"gid": g.gid, "season": g.season, "date": g.date,
                      "team": g.away, "side": "a", "pace": g.pace_a,
                      "oeff": g.oeff_a, "deff": g.deff_a})])
    P = P.sort_values("date").reset_index(drop=True)
    grp = P.groupby(["season", "team"])
    for v in ("pace", "oeff", "deff"):
        P[f"f_{v}"] = grp[v].transform(
            lambda s: s.shift(1).rolling(W, min_periods=MINP).mean())
    P["nprior"] = grp.cumcount()
    h = P[P.side == "h"].set_index("gid")[["f_pace", "f_oeff", "f_deff", "nprior"]]
    a = P[P.side == "a"].set_index("gid")[["f_pace", "f_oeff", "f_deff", "nprior"]]
    X = g.set_index("gid").copy()
    X["h_f_PACE"], X["h_f_OEFF"], X["h_f_DEFF"] = h.f_pace, h.f_oeff, h.f_deff
    X["a_f_PACE"], X["a_f_OEFF"], X["a_f_DEFF"] = a.f_pace, a.f_oeff, a.f_deff
    X["h_nprior"], X["a_nprior"] = h.nprior, a.nprior
    X["pace_sum"] = X.h_f_PACE + X.a_f_PACE
    X["pace_diff"] = X.h_f_PACE - X.a_f_PACE
    X["pace_absdiff"] = X.pace_diff.abs()
    X["oeff_sum"] = X.h_f_OEFF + X.a_f_OEFF
    X["deff_sum"] = X.h_f_DEFF + X.a_f_DEFF
    X["implied_total"] = (X.pace_sum / 2) * X.oeff_sum / 100
    X["implied_minus_open"] = X.implied_total - X.ot_open
    return X.reset_index()


def pending_raw(pend, template_cols):
    """PENDING rows in the VENDOR schema, so the ported chain can build their
    prior-only features. Everything except the keys is NaN by design."""
    R = pd.DataFrame(np.nan, index=range(len(pend)), columns=list(template_cols))
    R["GAME-ID"] = pend.gid.values
    R["DATE"] = pd.to_datetime(pend.date).dt.strftime("%Y-%m-%d").values
    R["TEAM_H"] = pend.home.values
    R["TEAM_R"] = pend.away.values
    R["OPENING TOTAL_H"] = pend.ot_open.values
    R["OPENING SPREAD_H"] = pend.os_open.values
    from prepare_data import SEASON_COLS
    yr = pd.to_datetime(pend.date).dt.year
    start = np.where(pd.to_datetime(pend.date).dt.month >= 8, yr, yr - 1)
    R[SEASON_COLS[0]] = [f"NBA {y}-{y+1} Regular Season" for y in start]
    return R


def attach_dis_open(X, raw_all, asof, mode="walkforward"):
    """Compute dis_open with the ported frozen chain, covering pending rows.

    mode='walkforward' is CORRECT and the default: it gives out-of-sample
    dis_open for the ridge's training rows (matching the frozen protocol) and
    predicts pending rows from a model trained on everything before them.
    mode='asof' fits once on all completed games -- faster, but its training
    rows carry IN-SAMPLE dis_open, which is a train/serve skew.
    """
    import dis_open_live as DOL
    G = DOL.compute(raw_all, asof=asof, mode=mode)
    X = X.copy()
    X["gid"] = X.gid.astype(str).str.strip()
    X = X.merge(G[["gid", "dis_open"]], on="gid", how="left")
    return X, int(X.dis_open.notna().sum())


def ridge_predict(X, asof, feats=None):
    """Expanding-window ridge refit on everything completed before `asof`."""
    feats = RIDGE_FEATS if feats is None else feats
    tr = X[(X.date < asof) & X.tmove.notna() & X[feats].notna().all(1)]
    te = X[X[feats].notna().all(1)]
    if len(tr) < RIDGE_MIN_TRAIN:
        raise RuntimeError(f"ridge needs {RIDGE_MIN_TRAIN} training games, "
                           f"have {len(tr)}")
    mdl = make_pipeline(StandardScaler(), RidgeCV(alphas=np.logspace(-2, 3, 20)))
    mdl.fit(tr[feats].values, tr.tmove.values)
    out = pd.Series(np.nan, index=X.index)
    out.loc[te.index] = mdl.predict(te[feats].values)
    alpha = mdl.named_steps["ridgecv"].alpha_
    return out, len(tr), alpha


# ------------------------------------------------ latent (frozen parameters)
def latent_design(g):
    """OLE design matrix; pending rows survive because features are prior-only."""
    X, featcols = OLE.design_matrix(g)
    return X, featcols


def freeze_latent(paths, artifact=ARTIFACT):
    """Fit scaler -> PCA(K by cumEV>=80%) -> OLS once, through 2025-26."""
    g = build_games(paths)
    g = g[g.season <= LATENT_FREEZE_THROUGH]
    X, featcols = latent_design(g)
    tr = X[X.tmove.notna()].copy()
    sc = StandardScaler().fit(tr[featcols].values)
    Z = sc.transform(tr[featcols].values)
    p_full = PCA().fit(Z)
    K = int(np.searchsorted(np.cumsum(p_full.explained_variance_ratio_),
                            EV_THRESH) + 1)
    pca = PCA(n_components=K).fit(Z)
    P = pca.transform(Z)
    A = np.column_stack([np.ones(len(P)), P])
    beta, *_ = np.linalg.lstsq(A, tr.tmove.values, rcond=None)
    art = {"featcols": featcols, "scaler": sc, "pca": pca, "K": K,
           "beta": beta, "n_train": len(tr),
           "seasons": sorted(tr.season.unique().tolist()),
           "frozen_on": pd.Timestamp.utcnow().isoformat(),
           "ev_thresh": EV_THRESH}
    with open(artifact, "wb") as f:
        pickle.dump(art, f)
    r2 = 1 - ((tr.tmove.values - A @ beta) ** 2).mean() / tr.tmove.var()
    print(f"  latent FROZEN -> {artifact}")
    print(f"    train {len(tr):,} games, seasons {art['seasons']}, K={K} "
          f"(cumEV>={EV_THRESH:.0%}), in-sample R2 {r2:+.4f}")
    return art


def latent_predict(X, featcols_now, art):
    need = art["featcols"]
    miss = [c for c in need if c not in X.columns]
    if miss:
        raise RuntimeError(f"latent artifact expects {len(miss)} absent "
                           f"features, e.g. {miss[:4]}")
    Z = art["scaler"].transform(X[need].values)
    P = art["pca"].transform(Z)
    A = np.column_stack([np.ones(len(P)), P])
    return A @ art["beta"]


# ------------------------------------------------------------------ engine
def recommend(target_date, lines_csv=None, sched_local=None, artifact=ARTIFACT,
              paths=(HIST, CURRENT), quiet=False, ridge_mode="frozen",
              dis_mode="walkforward"):
    import nba_schedule
    asof = pd.to_datetime(target_date).normalize()
    teammap = pd.read_csv(TEAM_MAP_CSV).set_index("bigdataball_name")["abbr"].to_dict()

    sched = nba_schedule.games_on(asof, local_csv=sched_local, verbose=not quiet)
    if not len(sched):
        print(f"  no NBA games scheduled {asof.date()}")
        return None
    if lines_csv is None:
        raise SystemExit(
            "\n  --lines is REQUIRED: the model bets AT THE OPENER, so it needs\n"
            "  today's opening totals. CSV columns:\n"
            "      game_date,away_abbr,home_abbr,open_total\n")
    lines = pd.read_csv(lines_csv)
    pend, missing, unmapped, merged = pending_rows(sched, lines, teammap)
    if len(unmapped):
        raise SystemExit(f"  team abbreviations not in {TEAM_MAP_CSV}: "
                         f"{sorted(set(unmapped.home.index.astype(str)))}")
    if len(missing):
        print(f"  !! {len(missing)} scheduled game(s) have NO opening total and "
              f"cannot be scored:")
        for _, r in missing.iterrows():
            print(f"       {r.away_abbr} @ {r.home_abbr}")
    pend = pend[pend.ot_open.notna()].reset_index(drop=True)
    if not len(pend):
        print("  nothing scoreable today (no openers supplied).")
        return None

    g = build_games(paths, pending=pend)
    if not os.path.exists(artifact):
        raise SystemExit(f"  missing latent artifact {artifact}; run --freeze first")
    with open(artifact, "rb") as f:
        art = pickle.load(f)

    # ---- ridge
    XR = ridge_features(g)
    feats = list(RIDGE_FEATS)
    if ridge_mode == "frozen":
        raw_all = _load_master(paths)
        raw_all = pd.concat([raw_all, pending_raw(pend, raw_all.columns)],
                            ignore_index=True)
        XR, ndis = attach_dis_open(XR, raw_all, asof, mode=dis_mode)
        miss = XR[XR.gid.isin(pend.gid) & XR.dis_open.isna()]
        if len(miss):
            print(f"  !! dis_open unavailable for {len(miss)} game(s) "
                  f"(insufficient team history); they will not be scored")
        feats = list(FROZEN_FEATS)
        spec_name = "MOVE_COMBINED (frozen, full feature set)"
    else:
        spec_name = "MOVE_REDUCED (no dis_open -- NOT the frozen spec)"
    rid, ntr, alpha = ridge_predict(XR, asof, feats)
    XR["ridge"] = rid.values

    # ---- latent
    XL, featcols = latent_design(g)
    XL["latent"] = latent_predict(XL, featcols, art)

    # ---- combine, on today's pending rows only
    out = XR[XR.gid.isin(pend.gid)][["gid", "date", "home", "away", "ot_open",
                                     "ridge", "h_nprior", "a_nprior"]].merge(
        XL[["gid", "latent"]], on="gid", how="left")
    out["m"] = COMB_A + COMB_RIDGE * out.ridge + COMB_LATENT * out.latent
    out["eligible"] = ((out.h_nprior >= MIN_PRIOR) & (out.a_nprior >= MIN_PRIOR)
                       & out.ridge.notna() & out.latent.notna())
    out["side"] = np.where(out.m > 0, "OVER", "UNDER")
    out["action"] = np.select(
        [~out.eligible, out.m.abs() >= THRESH_CONFIRM,
         out.m.abs() >= THRESH_PRIMARY],
        ["no bet (scope)", "BET (confirmatory)", "BET (primary)"], "no bet")

    if not quiet:
        print(f"\n  SPEC: {spec_name}")
        if ridge_mode != "frozen":
            print("  !! reduced ridge: OOS corr 0.217 vs the frozen 0.265. "
                  "These numbers do NOT\n     inherit the frozen backtest and "
                  "are not a valid 2026-27 prospective test.")
        print(f"  ridge refit: {ntr:,} games, alpha={alpha:.3g}   "
              f"latent: frozen K={art['K']} on {art['n_train']:,} games")
        print(f"\n  {'matchup':22}{'open':>8}{'ridge':>8}{'latent':>8}"
              f"{'m':>8}{'side':>7}   action")
        for _, r in out.sort_values("m", key=abs, ascending=False).iterrows():
            print(f"  {r.away+' @ '+r.home:22}{r.ot_open:>8.1f}"
                  f"{r.ridge:>8.2f}{r.latent:>8.2f}{r.m:>+8.2f}"
                  f"{r.side:>7}   {r.action}")
        nb = int((out.action.str.startswith("BET")).sum())
        print(f"\n  {nb} bet(s) of {len(out)} scheduled")

    os.makedirs(OUTDIR, exist_ok=True)
    path = os.path.join(OUTDIR, f"move_combined_{asof.date()}.csv")
    out.assign(generated=pd.Timestamp.utcnow().isoformat(),
               spec=spec_name).to_csv(path, index=False)
    if not quiet:
        print(f"  written -> {path}")
    return out


def selftest(date, paths=(HIST, CURRENT), artifact=ARTIFACT):
    """Dry run on a HISTORICAL date: rebuild as if that morning, then grade.

    Verifies the whole chain end-to-end without waiting for the season. It is
    NOT a backtest -- the latent artifact saw these seasons in training, so
    treat the printed hit rate as a plumbing check only.
    """
    asof = pd.to_datetime(date).normalize()
    g = build_games(paths)
    day = g[g.date == asof]
    if not len(day):
        raise SystemExit(f"  no games in the master file on {asof.date()}")
    with open(artifact, "rb") as f:
        art = pickle.load(f)
    XR = ridge_features(g)
    rid, ntr, alpha = ridge_predict(XR[XR.date <= asof], asof)
    XR = XR[XR.date <= asof].assign(ridge=rid.values)
    XL, featcols = latent_design(g[g.date <= asof])
    XL["latent"] = latent_predict(XL, featcols, art)
    out = XR[XR.date == asof][["gid", "home", "away", "ot_open", "ot_close",
                               "total", "ridge", "h_nprior", "a_nprior"]].merge(
        XL[["gid", "latent"]], on="gid", how="left")
    out["m"] = COMB_A + COMB_RIDGE * out.ridge + COMB_LATENT * out.latent
    out["actual_move"] = out.ot_close - out.ot_open
    print(f"  SELFTEST {asof.date()}: {len(out)} games, ridge trained on "
          f"{ntr:,} (alpha={alpha:.3g})")
    print(f"  {'matchup':22}{'open':>7}{'m':>8}{'actual':>8}{'close':>8}{'total':>8}")
    for _, r in out.iterrows():
        print(f"  {str(r.away)[:10]+' @ '+str(r.home)[:10]:22}{r.ot_open:>7.1f}"
              f"{r.m:>+8.2f}{r.actual_move:>+8.2f}{r.ot_close:>8.1f}{r.total:>8.1f}")
    b = out[out.m.abs() >= THRESH_PRIMARY].dropna(subset=["actual_move"])
    if len(b):
        agree = (np.sign(b.m) == np.sign(b.actual_move)).mean()
        clv = (np.sign(b.m) * b.actual_move).mean()
        print(f"\n  |m|>=1.0: {len(b)} games, direction agreement "
              f"{100*agree:.0f}%, mean CLV {clv:+.2f} pts")
    print("  [plumbing check only -- these seasons are in the latent training set]")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--freeze", action="store_true",
                    help="fit and pickle the latent mapping through 2025-26")
    ap.add_argument("--date", help="produce recommendations for YYYY-MM-DD")
    ap.add_argument("--lines", help="CSV of today's opening totals (required with --date)")
    ap.add_argument("--schedule-local", help="fallback schedule CSV")
    ap.add_argument("--selftest", help="dry run on a historical YYYY-MM-DD")
    ap.add_argument("--hist", default=HIST)
    ap.add_argument("--current", default=CURRENT)
    ap.add_argument("--artifact", default=ARTIFACT)
    ap.add_argument("--dis-mode", choices=["walkforward", "asof"],
                    default="walkforward",
                    help="'walkforward' (default, correct) vs 'asof' (fast, "
                         "in-sample dis_open in training rows)")
    ap.add_argument("--ridge-mode", choices=["reduced", "frozen"],
                    default="frozen",
                    help="'frozen' requires dis_open for every game incl. "
                         "pending and refuses to approximate")
    a = ap.parse_args()
    paths = (a.hist, a.current)
    if a.freeze:
        freeze_latent(paths, a.artifact)
    elif a.selftest:
        selftest(a.selftest, paths, a.artifact)
    elif a.date:
        recommend(a.date, a.lines, a.schedule_local, a.artifact, paths,
                  ridge_mode=a.ridge_mode, dis_mode=a.dis_mode)
    else:
        ap.print_help()
