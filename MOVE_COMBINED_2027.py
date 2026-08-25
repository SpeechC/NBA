"""
===============================================================================
 MOVE_COMBINED — 2026-27 daily recommendation engine        SINGLE-FILE / SPYDER
===============================================================================

 Run in Spyder: set the CONFIG block below, then press F5.
 No command-line arguments. No imports from the research project — everything
 the frozen spec needs is inlined here.

 WHAT IT DOES
   Forecasts how the TOTALS line will move from open to close, and bets the
   side of the predicted move AT THE OPENER.

       m = +0.0337 + 0.8402*ridge + 0.6869*latent
       |m| >= 1.0  -> BET (primary)      m > 0 -> OVER
       |m| >= 1.5  -> BET (confirmatory) m < 0 -> UNDER

   ridge   walk-forward RidgeCV on team form + market state + dis_open, where
           dis_open = cal_total - open_total comes from an XGBoost team-score
           model plus a calibration stage (frozen procedure; refits continue).
   latent  PCA->OLS on 96 features built ONLY from the bookmaker's own past
           opening errors. Frozen PARAMETERS: fitted once through 2025-26 by
           MODE = "freeze" and never refitted during the season.

 FIRST RUN
   1. MODE = "freeze"    -> writes the latent artifact .pkl  (do this once)
   2. MODE = "selftest"  -> replays a past date end to end   (sanity check)
   3. MODE = "daily"     -> produces today's recommendations

 YOU MUST SUPPLY OPENING TOTALS
   The strategy bets at the opener, so open_total is both an input feature and
   the price. No schedule feed carries prices. Create a small CSV each day:

       game_date,away_abbr,home_abbr,open_total,open_spread
       2026-10-21,GSW,LAL,231.5,-4.5

   Capture them AT THE OPEN. Games without an opener are reported and skipped.

 STATUS: paper/logging only. PREREG_move_combined.md makes CLV the primary
 endpoint; the historical ROI edge (~+2% at |m|>=1.0) is inside single-season
 noise and half a point of slippage erases it.
===============================================================================
"""

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
from xgboost import XGBRegressor

# =============================================================================
#  CONFIG  — edit this block, then run
# =============================================================================
MODE = "daily"            # "freeze" | "selftest" | "daily"

HIST_CSV    = r"C:\NBA2\dfMaster_OT_2017-2026.csv"       # historical master
CURRENT_CSV = r"C:\NBA2\dfMaster_current.csv"            # updated daily ("" if none)
LINES_CSV   = r"C:\NBA2\lines_today.csv"                 # YOUR opening totals
ARTIFACT    = r"C:\NBA2\move_combined_latent_2027.pkl"   # frozen latent mapping
OUT_DIR     = r"C:\NBA2\recommendations"

TARGET_DATE   = None      # "daily": None = today; or "2026-10-21"
SELFTEST_DATE = "2026-03-05"

SCHEDULE_CSV  = ""        # optional local schedule override (else fetch NBA.com)
FETCH_SCHEDULE = True     # False = derive the slate from LINES_CSV alone

# ---- FROZEN. Do not edit. (PREREG_move_combined.md s3/s5) --------------------
COMB_A, COMB_RIDGE, COMB_LATENT = 0.0337, 0.8402, 0.6869
THRESH_PRIMARY, THRESH_CONFIRM = 1.0, 1.5
EV_THRESH = 0.80          # latent PC count rule (cumulative explained variance)
MIN_PRIOR = 10            # both teams need >= 10 prior games that season
RIDGE_MIN_TRAIN = 500
LATENT_FREEZE_THROUGH = 2025      # last training season (2025-26)
LAG = 4                   # team-score model rolling window
SCORE_MIN, CAL_MIN, REFIT_DAYS, SEED = 300, 100, 7, 42

VARS = ["2PA", "2P%", "3PA", "3P%", "FTA", "FT%", "ORB", "DRB",
        "AST", "STL", "BLK", "TOV", "PF"]
EXT = ["PACE", "OEFF", "DEFF"]
ALLV = VARS + EXT
SEASON_COLS = ["DATASET_H", "BIGDATABALL\nDATASET_H"]
RT = ["rest_days", "is_b2b", "is_3in4", "is_4in5"]
STATES = ("scoreerr", "allowerr", "toterr", "sprerr")
LAGS = (1, 2, 3)
RMS = ((3, 3), (5, 3), (10, 5), (20, 10))
SDS = ((5, 3), (10, 5), (20, 10))

TEAM_ABBR = {
    "Atlanta": "ATL", "Boston": "BOS", "Brooklyn": "BKN", "Charlotte": "CHA",
    "Chicago": "CHI", "Cleveland": "CLE", "Dallas": "DAL", "Denver": "DEN",
    "Detroit": "DET", "Golden State": "GSW", "Houston": "HOU",
    "Indiana": "IND", "LA Clippers": "LAC", "LA Lakers": "LAL",
    "Memphis": "MEM", "Miami": "MIA", "Milwaukee": "MIL", "Minnesota": "MIN",
    "New Orleans": "NOP", "New York": "NYK", "Oklahoma City": "OKC",
    "Orlando": "ORL", "Philadelphia": "PHI", "Phoenix": "PHX",
    "Portland": "POR", "Sacramento": "SAC", "San Antonio": "SAS",
    "Toronto": "TOR", "Utah": "UTA", "Washington": "WAS"}


# =============================================================================
#  LOADING
# =============================================================================
def season_label(raw):
    a = raw[SEASON_COLS[0]] if SEASON_COLS[0] in raw.columns else pd.Series(np.nan, index=raw.index)
    b = raw[SEASON_COLS[1]] if SEASON_COLS[1] in raw.columns else pd.Series(np.nan, index=raw.index)
    return a.fillna(b)


MARKET_GATES = {"OPENING SPREAD_H": (-30.0, 30.0), "CLOSING SPREAD_H": (-30.0, 30.0),
                "OPENING TOTAL_H": (150.0, 300.0), "CLOSING TOTAL_H": (150.0, 300.0)}


def sanitize_market(raw, verbose=True):
    """Scrub physically impossible market values to NaN (see DATA_DEFECT notes).

    Six cells in the vendor master carry a price or a total in the wrong column.
    Two of them are in OPENING TOTAL_H and produce tmove values of +115.5 and
    +99.0 against a legitimate range of -15.5..+19.5, inflating the target's sd
    by 11.4%. Range gates are the only check that finds these: every offending
    value is a valid float and plausible for SOME betting column.
    """
    raw = raw.copy()
    for col, (lo, hi) in MARKET_GATES.items():
        if col not in raw.columns:
            continue
        v = pd.to_numeric(raw[col], errors="coerce")
        bad = v.notna() & ((v < lo) | (v > hi))
        if bad.any():
            if verbose:
                print(f"  [market gate] {col}: scrubbed {int(bad.sum())} impossible value(s)")
            raw.loc[bad, col] = np.nan
    for col in ("MONEYLINE_H", "MONEYLINE_R"):
        if col not in raw.columns:
            continue
        v = pd.to_numeric(raw[col], errors="coerce")
        bad = v.notna() & ((v.abs() < 100) | (v.abs() > 20000))
        if bad.any():
            if verbose:
                print(f"  [market gate] {col}: scrubbed {int(bad.sum())} impossible value(s)")
            raw.loc[bad, col] = np.nan
    return raw


def load_raw(paths):
    frames = []
    for p in paths:
        if p and os.path.exists(p):
            frames.append(pd.read_csv(p, low_memory=False))
            print(f"  loaded {os.path.basename(p)}: {len(frames[-1]):,} rows")
    if not frames:
        raise FileNotFoundError(f"none of these exist: {paths}")
    raw = pd.concat(frames, ignore_index=True)
    raw["GAME-ID"] = raw["GAME-ID"].astype(str).str.strip()
    raw = raw.drop_duplicates("GAME-ID", keep="last").reset_index(drop=True)
    return sanitize_market(raw)


def build_games(raw):
    """Game-level frame. Pending rows (NaN outcomes) pass through intact."""
    lbl = season_label(raw).astype(str)
    keep = lbl.str.contains("Regular Season|In-Season", na=False)
    d, lbl = raw[keep].copy(), lbl[keep]
    n = lambda c: pd.to_numeric(d[c], errors="coerce")
    g = pd.DataFrame({
        "gid": d["GAME-ID"].astype(str).str.strip(),
        "date": pd.to_datetime(d["DATE"], errors="coerce"),
        "season": lbl.str.extract(r"(\d{4})")[0].astype(float).values,
        "home": d["TEAM_H"], "away": d["TEAM_R"],
        "hpts": n("PTS_H"), "apts": n("PTS_R"),
        "ot_open": n("OPENING TOTAL_H"), "ot_close": n("CLOSING TOTAL_H"),
        "sp_open": n("OPENING SPREAD_H"), "sp_close": n("CLOSING SPREAD_H"),
        "pace_h": n("PACE_H"), "pace_a": n("PACE_R"),
        "oeff_h": n("OEFF_H"), "oeff_a": n("OEFF_R"),
        "deff_h": n("DEFF_H"), "deff_a": n("DEFF_R")})
    g = g.dropna(subset=["date", "gid", "ot_open"]).copy()
    g["season"] = g["season"].astype(int)
    g["margin"] = g.hpts - g.apts
    g["om_open"] = -g.sp_open          # home favourite carries a negative spread
    g["om_close"] = -g.sp_close
    g["total"] = g.hpts + g.apts
    g["te_open"] = g.total - g.ot_open
    g["te_close"] = g.total - g.ot_close
    g["se_open"] = g.margin - g.om_open
    g["se_close"] = g.margin - g.om_close
    g["tmove"] = g.ot_close - g.ot_open
    g["smove"] = g.om_close - g.om_open
    g["hse"] = g.hpts - (g.ot_open + g.om_open) / 2.0
    g["ase"] = g.apts - (g.ot_open - g.om_open) / 2.0
    return g.sort_values(["date", "gid"]).reset_index(drop=True)


# =============================================================================
#  SCHEDULE
# =============================================================================
def fetch_schedule(local_csv=""):
    if local_csv and os.path.exists(local_csv):
        s = pd.read_csv(local_csv)
        s["game_date"] = pd.to_datetime(s["game_date"]).dt.normalize()
        print(f"  schedule: {len(s):,} games from local {local_csv}")
        return s
    import requests
    hdr = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36"),
           "Referer": "https://www.nba.com/"}
    url = "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json"
    js = requests.get(url, headers=hdr, timeout=30).json()
    rows = []
    for gd in js["leagueSchedule"]["gameDates"]:
        for gm in gd["games"]:
            rows.append({"game_date": pd.to_datetime(gd["gameDate"]).normalize(),
                         "away_abbr": gm["awayTeam"]["teamTricode"],
                         "home_abbr": gm["homeTeam"]["teamTricode"],
                         "label": gm.get("gameLabel", "")})
    s = pd.DataFrame(rows)
    print(f"  schedule: {len(s):,} games from nba.com "
          f"({s.game_date.min().date()} .. {s.game_date.max().date()})")
    return s


# =============================================================================
#  dis_open — pending-capable port of the frozen score-model chain
# =============================================================================
def _side(df, suf):
    g = pd.DataFrame({"game_id": df["GAME-ID"],
                      "date": pd.to_datetime(df["DATE"], errors="coerce"),
                      "season": df["season"], "team": df[f"TEAM_{suf}"],
                      "home": 1 if suf == "H" else 0})
    num = lambda c: pd.to_numeric(df[c], errors="coerce")
    fg, fga = num(f"FG_{suf}"), num(f"FGA_{suf}")
    p3, p3a = num(f"3P_{suf}"), num(f"3PA_{suf}")
    ft, fta = num(f"FT_{suf}"), num(f"FTA_{suf}")
    g["2PA"] = fga - p3a
    g["2P%"] = (fg - p3) / (fga - p3a).replace(0, np.nan)
    g["3PA"] = p3a
    g["3P%"] = np.where(p3a > 0, p3 / p3a.replace(0, np.nan), 0.0)
    g["FTA"] = fta
    g["FT%"] = np.where(fta > 0, ft / fta.replace(0, np.nan), 0.0)
    for k, c in (("ORB", "OR"), ("DRB", "DR"), ("AST", "A"), ("STL", "ST"),
                 ("BLK", "BL"), ("TOV", "TO"), ("PF", "PF")):
        g[k] = num(f"{c}_{suf}")
    g["Y"] = num(f"PTS_{suf}")
    return g


def _rest(panel):
    p = panel.sort_values(["season", "team", "date"]).copy()
    grp = p.groupby(["season", "team"])["date"]
    p["rest_days"] = grp.diff().dt.days.clip(upper=7)
    s3 = (p["date"] - grp.shift(2)).dt.days
    s4 = (p["date"] - grp.shift(3)).dt.days
    p["is_b2b"] = (p["rest_days"] == 1).astype(float)
    p["is_3in4"] = (s3 <= 3).fillna(False).astype(float)
    p["is_4in5"] = (s4 <= 4).fillna(False).astype(float)
    p["rest_days"] = p["rest_days"].fillna(3.0)
    return p


DIS_FEATS = ([f"f_{v}" for v in ALLV] + [f"f_{v}_opp" for v in EXT]
             + RT + [c + "_opp" for c in RT])


def dis_open_panel(raw):
    raw = raw.copy()
    raw["GAME-ID"] = raw["GAME-ID"].astype(str).str.strip()
    raw["season"] = season_label(raw)
    raw = raw[raw["season"].astype(str).str.contains(
        "Regular Season|In-Season", na=False)].copy()
    sides = []
    for suf in ("H", "R"):
        s = _side(raw, suf)
        for v in EXT:
            s[v] = pd.to_numeric(raw[f"{v}_{suf}"], errors="coerce").values
        sides.append(s)
    panel = pd.concat(sides, ignore_index=True)
    panel = panel.sort_values(["season", "team", "date", "game_id"]).reset_index(drop=True)
    panel[ALLV] = panel[ALLV].astype(float)
    feats = (panel.groupby(["season", "team"])[ALLV]
             .apply(lambda x: x.shift(1).rolling(LAG).mean())
             .reset_index(level=[0, 1], drop=True).sort_index())
    feats.columns = [f"f_{c}" for c in feats.columns]
    panel = pd.concat([panel, feats], axis=1)
    panel = panel.dropna(subset=[f"f_{c}" for c in ALLV]).reset_index(drop=True)
    panel = _rest(panel)
    fc = [f"f_{v}" for v in EXT]
    opp = panel[["game_id", "home"] + fc + RT].copy()
    opp["home"] = 1 - opp["home"]
    opp = opp.rename(columns={c: c + "_opp" for c in fc + RT})
    return panel.merge(opp, on=["game_id", "home"], how="inner"
                       ).sort_values("date").reset_index(drop=True)


def compute_dis_open(raw):
    """Walk-forward dis_open. Pending rows are scored by the model trained on
    everything before them, so training rows keep OUT-OF-SAMPLE values."""
    panel = dis_open_panel(raw)
    X, y = panel[DIS_FEATS].values, panel["Y"].values.astype(float)
    dates = panel["date"].values
    done = ~np.isnan(y)
    pred = np.full(len(panel), np.nan)
    uniq = np.unique(dates[done])
    counts = np.cumsum([np.sum(dates[done] == u) for u in uniq])
    idx = np.searchsorted(counts, SCORE_MIN)
    if idx >= len(uniq):
        raise RuntimeError("not enough history for the team-score model")
    cuts = pd.date_range(pd.Timestamp(uniq[idx]),
                         pd.Timestamp(dates.max()) + pd.Timedelta(days=1),
                         freq=f"{REFIT_DAYS}D")
    for i, cut in enumerate(cuts):
        nxt = (cuts[i + 1] if i + 1 < len(cuts)
               else pd.Timestamp(dates.max()) + pd.Timedelta(days=1))
        tr = (dates < np.datetime64(cut)) & done
        te = (dates >= np.datetime64(cut)) & (dates < np.datetime64(nxt))
        if te.sum() == 0 or tr.sum() < SCORE_MIN:
            continue
        m = XGBRegressor(max_depth=2, n_estimators=100, learning_rate=0.3,
                         random_state=SEED, n_jobs=4, verbosity=0)
        m.fit(X[tr], y[tr])
        pred[te] = m.predict(X[te])
    panel["pred"] = pred
    sc = panel.dropna(subset=["pred"])
    h = sc[sc.home == 1].set_index("game_id")
    a = sc[sc.home == 0].set_index("game_id")
    G = pd.DataFrame({"date": h["date"],
                      "model_total": h["pred"] + a["pred"],
                      "actual_total": h["Y"] + a["Y"]}).dropna(subset=["model_total"])
    G = G.reset_index().rename(columns={"index": "game_id"}).sort_values("date")
    mk = pd.DataFrame({"game_id": raw["GAME-ID"].astype(str).str.strip(),
                       "open_total": pd.to_numeric(raw["OPENING TOTAL_H"],
                                                   errors="coerce")})
    G = G.merge(mk.drop_duplicates("game_id"), on="game_id", how="left")
    # walk-forward calibration model_total -> actual_total
    mt, ac = G.model_total.values, G.actual_total.values
    dn = ~np.isnan(ac)
    cal = np.full(len(mt), np.nan)
    for start in range(CAL_MIN, len(mt), 25):
        end = min(start + 25, len(mt))
        hist = dn[:start]
        if hist.sum() < CAL_MIN:
            continue
        b = np.polyfit(mt[:start][hist], ac[:start][hist], 1)
        cal[start:end] = np.polyval(b, mt[start:end])
    G["dis_open"] = cal - G.open_total
    G["gid"] = G.game_id.astype(str).str.strip()
    return G[["gid", "dis_open"]]


# =============================================================================
#  RIDGE
# =============================================================================
RIDGE_FEATS = ["ot_open", "pace_sum", "pace_diff", "pace_absdiff",
               "oeff_sum", "deff_sum", "implied_minus_open",
               "h_f_PACE", "a_f_PACE", "h_f_OEFF", "a_f_OEFF",
               "h_f_DEFF", "a_f_DEFF", "dis_open"]


def ridge_features(g, W=20, MINP=10):
    P = pd.concat([
        pd.DataFrame({"gid": g.gid, "season": g.season, "date": g.date,
                      "team": g.home, "side": "h", "pace": g.pace_h,
                      "oeff": g.oeff_h, "deff": g.deff_h}),
        pd.DataFrame({"gid": g.gid, "season": g.season, "date": g.date,
                      "team": g.away, "side": "a", "pace": g.pace_a,
                      "oeff": g.oeff_a, "deff": g.deff_a})]).sort_values("date")
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
    X["implied_minus_open"] = (X.pace_sum / 2) * X.oeff_sum / 100 - X.ot_open
    return X.reset_index()


def ridge_predict(X, asof):
    tr = X[(X.date < asof) & X.tmove.notna() & X[RIDGE_FEATS].notna().all(1)]
    te = X[X[RIDGE_FEATS].notna().all(1)]
    if len(tr) < RIDGE_MIN_TRAIN:
        raise RuntimeError(f"ridge needs {RIDGE_MIN_TRAIN} games, has {len(tr)}")
    m = make_pipeline(StandardScaler(), RidgeCV(alphas=np.logspace(-2, 3, 20)))
    m.fit(tr[RIDGE_FEATS].values, tr.tmove.values)
    out = pd.Series(np.nan, index=X.index)
    out.loc[te.index] = m.predict(te[RIDGE_FEATS].values)
    return out, len(tr), m.named_steps["ridgecv"].alpha_


# =============================================================================
#  LATENT — error-history state, frozen parameters
# =============================================================================
def latent_design(g):
    rows = []
    for side in ("home", "away"):
        sgn = 1.0 if side == "home" else -1.0
        rows.append(pd.DataFrame({
            "gid": g.gid, "date": g.date, "season": g.season, "team": g[side],
            "scoreerr": g.hse if side == "home" else g.ase,
            "allowerr": g.ase if side == "home" else g.hse,
            "toterr": g.te_open, "sprerr": sgn * g.se_open}))
    p = pd.concat(rows).sort_values(["date", "gid"]).reset_index(drop=True)
    grp = p.groupby(["season", "team"])
    feats = {}
    for st in STATES:
        s = grp[st]
        for L in LAGS:
            feats[f"{st}_lag{L}"] = s.shift(L)
        for w, mp in RMS:
            feats[f"{st}_rm{w}"] = s.transform(
                lambda x, w=w, mp=mp: x.shift(1).rolling(w, min_periods=mp).mean())
        for w, mp in SDS:
            feats[f"{st}_sd{w}"] = s.transform(
                lambda x, w=w, mp=mp: x.shift(1).rolling(w, min_periods=mp).std())
        feats[f"{st}_ewm"] = s.transform(
            lambda x: x.shift(1).ewm(halflife=5, min_periods=3).mean())
    F = pd.concat(feats, axis=1)
    F[["gid", "team"]] = p[["gid", "team"]]
    F["nprior"] = grp.cumcount()
    fcols = [c for c in F.columns if c not in ("gid", "team", "nprior")]
    h = g[["gid", "home"]].merge(F.rename(columns={"team": "home"}), on=["gid", "home"])
    a = g[["gid", "away"]].merge(F.rename(columns={"team": "away"}), on=["gid", "away"])
    X = g[["gid", "date", "season", "tmove"]].copy()
    for c in fcols:
        X[f"h_{c}"] = h[c].values
        X[f"a_{c}"] = a[c].values
    X["h_nprior"], X["a_nprior"] = h["nprior"].values, a["nprior"].values
    for st in STATES:
        X[f"sum_{st}"] = X[f"h_{st}_rm10"] + X[f"a_{st}_rm10"]
        X[f"dif_{st}"] = X[f"h_{st}_rm10"] - X[f"a_{st}_rm10"]
    X = X[(X.h_nprior >= MIN_PRIOR) & (X.a_nprior >= MIN_PRIOR)]
    featcols = [c for c in X.columns
                if c.startswith(("h_", "a_", "sum_", "dif_"))
                and not c.endswith("nprior")]
    return X.dropna(subset=featcols).reset_index(drop=True), featcols


def freeze_latent():
    raw = load_raw([HIST_CSV, CURRENT_CSV])
    g = build_games(raw)
    g = g[(g.season <= LATENT_FREEZE_THROUGH) & g.tmove.notna()]
    X, featcols = latent_design(g)
    tr = X[X.tmove.notna()]
    sc = StandardScaler().fit(tr[featcols].values)
    Z = sc.transform(tr[featcols].values)
    K = int(np.searchsorted(np.cumsum(PCA().fit(Z).explained_variance_ratio_),
                            EV_THRESH) + 1)
    pca = PCA(n_components=K).fit(Z)
    A = np.column_stack([np.ones(len(tr)), pca.transform(Z)])
    beta, *_ = np.linalg.lstsq(A, tr.tmove.values, rcond=None)
    art = {"featcols": featcols, "scaler": sc, "pca": pca, "K": K, "beta": beta,
           "n_train": len(tr), "seasons": sorted(tr.season.unique().tolist()),
           "frozen_on": str(pd.Timestamp.utcnow())}
    os.makedirs(os.path.dirname(ARTIFACT) or ".", exist_ok=True)
    with open(ARTIFACT, "wb") as f:
        pickle.dump(art, f)
    r2 = 1 - ((tr.tmove.values - A @ beta) ** 2).mean() / tr.tmove.var()
    print(f"\n  LATENT FROZEN -> {ARTIFACT}")
    print(f"    {len(tr):,} games, seasons {art['seasons']}, K={K}, "
          f"in-sample R2 {r2:+.4f}")
    return art


def latent_predict(X, art):
    Z = art["scaler"].transform(X[art["featcols"]].values)
    A = np.column_stack([np.ones(len(X)), art["pca"].transform(Z)])
    return A @ art["beta"]


# =============================================================================
#  PENDING ROWS
# =============================================================================
def make_pending(slate, lines, template_cols):
    name_by_abbr = {v: k for k, v in TEAM_ABBR.items()}
    L = lines.copy()
    L["game_date"] = pd.to_datetime(L["game_date"]).dt.normalize()
    k = lambda d, a, h: d.dt.strftime("%Y-%m-%d") + "|" + a.str.upper() + "|" + h.str.upper()
    L["k"] = k(L.game_date, L.away_abbr, L.home_abbr)
    S = slate.copy()
    S["k"] = k(S.game_date, S.away_abbr, S.home_abbr)
    keep = ["k", "open_total"] + (["open_spread"] if "open_spread" in L.columns else [])
    M = S.merge(L[keep], on="k", how="left")
    missing = M[M.open_total.isna()]
    M = M[M.open_total.notna()].reset_index(drop=True)
    if not len(M):
        return None, missing
    R = pd.DataFrame(np.nan, index=range(len(M)), columns=list(template_cols))
    R["GAME-ID"] = ("PEND_" + M.game_date.dt.strftime("%Y%m%d") + "_"
                    + M.away_abbr + M.home_abbr).values
    R["DATE"] = M.game_date.dt.strftime("%Y-%m-%d").values
    R["TEAM_H"] = M.home_abbr.map(name_by_abbr).values
    R["TEAM_R"] = M.away_abbr.map(name_by_abbr).values
    R["OPENING TOTAL_H"] = pd.to_numeric(M.open_total, errors="coerce").values
    if "open_spread" in M.columns:
        R["OPENING SPREAD_H"] = pd.to_numeric(M.open_spread, errors="coerce").values
    yr = M.game_date.dt.year
    st = np.where(M.game_date.dt.month >= 8, yr, yr - 1)
    R[SEASON_COLS[0]] = [f"NBA {y}-{y + 1} Regular Season" for y in st]
    bad = R[R.TEAM_H.isna() | R.TEAM_R.isna()]
    if len(bad):
        raise SystemExit(f"  unknown team abbreviations in {LINES_CSV}")
    return R, missing


# =============================================================================
#  MAIN
# =============================================================================
def run_daily(target_date=None):
    asof = (pd.Timestamp.today().normalize() if target_date is None
            else pd.to_datetime(target_date).normalize())
    print(f"\n{'=' * 74}\n MOVE_COMBINED — {asof.date()}\n{'=' * 74}")
    if not os.path.exists(ARTIFACT):
        raise SystemExit(f"  missing {ARTIFACT}. Set MODE='freeze' and run once.")
    with open(ARTIFACT, "rb") as f:
        art = pickle.load(f)
    if not os.path.exists(LINES_CSV):
        raise SystemExit(f"  missing {LINES_CSV}. Columns:\n"
                         f"      game_date,away_abbr,home_abbr,open_total,open_spread")
    lines = pd.read_csv(LINES_CSV)

    if FETCH_SCHEDULE:
        sch = fetch_schedule(SCHEDULE_CSV)
        slate = sch[sch.game_date == asof][["game_date", "away_abbr", "home_abbr"]]
        if not len(slate):
            print(f"  no NBA games scheduled on {asof.date()}")
            return None
    else:
        slate = lines.assign(game_date=pd.to_datetime(lines.game_date).dt.normalize())
        slate = slate[slate.game_date == asof][["game_date", "away_abbr", "home_abbr"]]
    print(f"  slate: {len(slate)} game(s)")

    raw = load_raw([HIST_CSV, CURRENT_CSV])
    pend, missing = make_pending(slate, lines, raw.columns)
    if len(missing):
        print(f"  !! no opening total for {len(missing)} game(s) — skipped:")
        for _, r in missing.iterrows():
            print(f"       {r.away_abbr} @ {r.home_abbr}")
    if pend is None:
        print("  nothing scoreable.")
        return None
    raw_all = pd.concat([raw, pend], ignore_index=True)

    print("  computing dis_open (walk-forward score model) ...")
    D = compute_dis_open(raw_all)
    g = build_games(raw_all)
    XR = ridge_features(g).merge(D, on="gid", how="left")
    rid, ntr, alpha = ridge_predict(XR, asof)
    XR["ridge"] = rid.values
    XL, _ = latent_design(g)
    XL["latent"] = latent_predict(XL, art)

    pend_ids = set(pend["GAME-ID"].astype(str))
    out = (XR[XR.gid.isin(pend_ids)][["gid", "home", "away", "ot_open", "ridge",
                                      "h_nprior", "a_nprior"]]
           .merge(XL[["gid", "latent"]], on="gid", how="left"))
    out["m"] = COMB_A + COMB_RIDGE * out.ridge + COMB_LATENT * out.latent
    ok = (out.h_nprior >= MIN_PRIOR) & (out.a_nprior >= MIN_PRIOR) \
        & out.ridge.notna() & out.latent.notna()
    out["side"] = np.where(out.m > 0, "OVER", "UNDER")
    out["action"] = np.select(
        [~ok, out.m.abs() >= THRESH_CONFIRM, out.m.abs() >= THRESH_PRIMARY],
        ["no bet (needs 10 prior games)", "BET confirmatory", "BET primary"],
        "no bet")
    print(f"\n  ridge: {ntr:,} training games, alpha={alpha:.3g}    "
          f"latent: frozen K={art['K']}")
    print(f"\n  {'matchup':30}{'open':>7}{'ridge':>8}{'latent':>8}{'m':>8}"
          f"{'side':>7}  action")
    print("  " + "-" * 76)
    for _, r in out.sort_values("m", key=abs, ascending=False).iterrows():
        mu = f"{str(r.away)[:13]} @ {str(r.home)[:13]}"
        print(f"  {mu:30}{r.ot_open:>7.1f}{r.ridge:>8.2f}{r.latent:>8.2f}"
              f"{r.m:>+8.2f}{r.side:>7}  {r.action}")
    nb = int(out.action.str.startswith("BET").sum())
    print(f"\n  {nb} bet(s) of {len(out)} game(s)")
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, f"move_combined_{asof.date()}.csv")
    out.assign(generated=str(pd.Timestamp.utcnow()),
               spec="MOVE_COMBINED frozen 2026-08").to_csv(path, index=False)
    print(f"  saved -> {path}")
    print("\n  PAPER ONLY. Bet at the OPENER. CLV is the endpoint of record.")
    return out


def run_selftest(date):
    """Replay a historical date through the full chain and grade it."""
    asof = pd.to_datetime(date).normalize()
    print(f"\n{'=' * 74}\n SELFTEST — {asof.date()}\n{'=' * 74}")
    with open(ARTIFACT, "rb") as f:
        art = pickle.load(f)
    raw = load_raw([HIST_CSV, CURRENT_CSV])
    D = compute_dis_open(raw)
    g = build_games(raw)
    g = g[g.date <= asof]
    XR = ridge_features(g).merge(D, on="gid", how="left")
    rid, ntr, alpha = ridge_predict(XR, asof)
    XR["ridge"] = rid.values
    XL, _ = latent_design(g)
    XL["latent"] = latent_predict(XL, art)
    out = (XR[XR.date == asof][["gid", "home", "away", "ot_open", "ot_close",
                                "total", "ridge"]]
           .merge(XL[["gid", "latent"]], on="gid", how="left").dropna(subset=["latent"]))
    out["m"] = COMB_A + COMB_RIDGE * out.ridge + COMB_LATENT * out.latent
    out["actual_move"] = out.ot_close - out.ot_open
    print(f"  ridge trained on {ntr:,} games (alpha={alpha:.3g}), {len(out)} games\n")
    print(f"  {'matchup':30}{'open':>7}{'m':>8}{'actual':>8}{'close':>8}")
    for _, r in out.iterrows():
        mu = f"{str(r.away)[:13]} @ {str(r.home)[:13]}"
        print(f"  {mu:30}{r.ot_open:>7.1f}{r.m:>+8.2f}{r.actual_move:>+8.2f}"
              f"{r.ot_close:>8.1f}")
    b = out[out.m.abs() >= THRESH_PRIMARY].dropna(subset=["actual_move"])
    if len(b):
        print(f"\n  |m|>=1.0: {len(b)} games, direction {100 * (np.sign(b.m) == np.sign(b.actual_move)).mean():.0f}%, "
              f"CLV {(np.sign(b.m) * b.actual_move).mean():+.2f} pts")
    print("  [plumbing check — one day is noise, and the latent saw these seasons]")
    return out


if __name__ == "__main__":
    if MODE == "freeze":
        freeze_latent()
    elif MODE == "selftest":
        run_selftest(SELFTEST_DATE)
    elif MODE == "daily":
        run_daily(TARGET_DATE)
    else:
        print(f"unknown MODE {MODE!r}; use 'freeze', 'selftest' or 'daily'")
