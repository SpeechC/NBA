"""Pending-capable `dis_open` — a faithful port of the frozen movement_full
stage-1/stage-2 chain that can also score UNPLAYED games.

The frozen chain is:
    walkforward_pace.build_panel_ext()   LAG=4 rolling means of ALLV, per team
        + rest_travel features
    -> XGBRegressor(depth=2, n_estimators=100, lr=0.3) predicting team points,
       expanding walk-forward, refit every 7 days, min 300 team-games
    -> per-game model_total = home_pred + away_pred
    -> linear calibration model_total -> actual_total, walk-forward, min 100
    -> dis_open = cal_total - open_total

The ONLY thing that blocked live use was that build_panel_ext reads the vendor
CSV directly and therefore had no rows for scheduled games. Every feature in
the chain is `shift(1).rolling(LAG)` within (season, team), so appending a
pending row with NaN box scores yields correct features for that row. This
module takes the raw frame as an ARGUMENT instead of reading it, and is
otherwise the same recipe, verified against the stored frozen output.

Rest/travel for pending games: the vendor rest column does not exist for an
unplayed game, so rest_days is derived from the schedule gap (knowable
pregame) and the derived b2b/3in4/4in5 flags follow from it.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

from xgboost import XGBRegressor

from prepare_data import VARS, _side, season_label
from walkforward_pace import ALLV, EXT

LAG = 4                    # frozen: walkforward.LAG
SCORE_MIN = 300            # frozen: movement_full.SCORE_MIN (team-games)
CAL_MIN = 100              # frozen: movement_full.CAL_MIN (games)
REFIT_DAYS = 7
SEED = 42
RT = ["rest_days", "is_b2b", "is_3in4", "is_4in5"]


def _rest_from_schedule(panel):
    """Prior-only rest features from game dates. Matches rest_travel's flags."""
    p = panel.sort_values(["season", "team", "date"]).copy()
    g = p.groupby(["season", "team"])["date"]
    p["rest_days"] = g.diff().dt.days.clip(upper=7)
    prev = {k: g.shift(k) for k in (1, 2, 3)}
    span3 = (p["date"] - prev[2]).dt.days      # this + 2 prior
    span4 = (p["date"] - prev[3]).dt.days      # this + 3 prior
    p["is_b2b"] = (p["rest_days"] == 1).astype(float)
    p["is_3in4"] = (span3 <= 3).fillna(False).astype(float)
    p["is_4in5"] = (span4 <= 4).fillna(False).astype(float)
    p["rest_days"] = p["rest_days"].fillna(3.0)
    return p


def build_panel(raw):
    """build_panel_ext's recipe, on a supplied raw frame (may include pending)."""
    raw = raw.copy()
    raw["GAME-ID"] = raw["GAME-ID"].astype(str).str.strip()   # mixed int/str
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
    panel = panel.sort_values(["season", "team", "date", "game_id"]
                              ).reset_index(drop=True)
    panel[ALLV] = panel[ALLV].astype(float)
    feats = (panel.groupby(["season", "team"])[ALLV]
                  .apply(lambda g: g.shift(1).rolling(LAG).mean())
                  .reset_index(level=[0, 1], drop=True).sort_index())
    feats.columns = [f"f_{c}" for c in feats.columns]
    panel = pd.concat([panel, feats], axis=1)
    panel["f_naive"] = (panel.groupby(["season", "team"])["Y"]
                        .transform(lambda s: s.shift(1).rolling(LAG).mean()))
    panel = panel.dropna(subset=[f"f_{c}" for c in ALLV]).reset_index(drop=True)
    panel = _rest_from_schedule(panel)

    fcols = [f"f_{c}" for c in EXT]
    opp = panel[["game_id", "home"] + fcols + RT].copy()
    opp["home"] = 1 - opp["home"]
    opp = opp.rename(columns={c: c + "_opp" for c in fcols + RT})
    panel = panel.merge(opp, on=["game_id", "home"], how="inner")
    return panel.sort_values("date").reset_index(drop=True)


FEATCOLS = ([f"f_{v}" for v in ALLV] + [f"f_{v}_opp" for v in EXT]
            + RT + [c + "_opp" for c in RT])


def _fit_predict(tr_X, tr_y, te_X):
    m = XGBRegressor(max_depth=2, n_estimators=100, learning_rate=0.3,
                     random_state=SEED, n_jobs=4, verbosity=0)
    m.fit(tr_X, tr_y)
    return m.predict(te_X)


def score_walkforward(panel, step_days=REFIT_DAYS, min_train=SCORE_MIN):
    """Expanding-window team-score predictions (frozen protocol)."""
    X = panel[FEATCOLS].values
    y = panel["Y"].values.astype(float)
    dates = panel["date"].values
    pred = np.full(len(panel), np.nan)
    done = ~np.isnan(y)
    uniq = np.unique(dates[done])
    counts = np.cumsum([np.sum(dates[done] == u) for u in uniq])
    idx = np.searchsorted(counts, min_train)
    if idx >= len(uniq):
        return pred
    cuts = pd.date_range(pd.Timestamp(uniq[idx]),
                         pd.Timestamp(dates.max()) + pd.Timedelta(days=1),
                         freq=f"{step_days}D")
    for i, cut in enumerate(cuts):
        nxt = (cuts[i + 1] if i + 1 < len(cuts)
               else pd.Timestamp(dates.max()) + pd.Timedelta(days=1))
        tr = (dates < np.datetime64(cut)) & done
        te = (dates >= np.datetime64(cut)) & (dates < np.datetime64(nxt))
        if te.sum() == 0 or tr.sum() < min_train:
            continue
        pred[te] = _fit_predict(X[tr], y[tr], X[te])
    return pred


def score_asof(panel, asof, min_train=SCORE_MIN):
    """Single fit on everything completed before `asof` (the live daily path)."""
    X = panel[FEATCOLS].values
    y = panel["Y"].values.astype(float)
    dates = panel["date"].values
    done = ~np.isnan(y)
    tr = done & (dates < np.datetime64(pd.Timestamp(asof)))
    if tr.sum() < min_train:
        raise RuntimeError(f"score model needs {min_train} team-games, has {tr.sum()}")
    pred = np.full(len(panel), np.nan)
    pred[:] = _fit_predict(X[tr], y[tr], X)
    return pred


def calibrate_walkforward(model_total, actual, dates, min_train=CAL_MIN, step=25):
    """Walk-forward linear map model_total -> actual_total (frozen protocol)."""
    cal = np.full(len(model_total), np.nan)
    done = ~np.isnan(actual)
    n_done = int(done.sum())
    if n_done <= min_train:
        return cal
    order = np.argsort(dates)
    inv = np.empty_like(order)
    inv[order] = np.arange(len(order))
    mt, ac, dn = model_total[order], actual[order], done[order]
    for start in range(min_train, len(mt), step):
        end = min(start + step, len(mt))
        hist = dn[:start]
        if hist.sum() < min_train:
            continue
        b = np.polyfit(mt[:start][hist], ac[:start][hist], 1)
        cal[start:end] = np.polyval(b, mt[start:end])
    return cal[inv]


def compute(raw, asof=None, mode="walkforward"):
    """Return per-game dis_open.

    mode='walkforward'  historical reconstruction (validation / ridge training)
    mode='asof'         one fit on all completed games, scores pending rows too
    """
    panel = build_panel(raw)
    if mode == "asof":
        if asof is None:
            raise ValueError("mode='asof' needs asof")
        panel["pred"] = score_asof(panel, asof)
    else:
        panel["pred"] = score_walkforward(panel)
    sc = panel.dropna(subset=["pred"])
    h = sc[sc.home == 1].set_index("game_id")
    a = sc[sc.home == 0].set_index("game_id")
    G = pd.DataFrame({
        "date": h["date"], "season": h["season"],
        "model_total": h["pred"] + a["pred"],
        "actual_total": h["Y"] + a["Y"]}).dropna(subset=["model_total"])
    G = G.reset_index().rename(columns={"index": "game_id"}).sort_values("date")
    mk = pd.DataFrame({"game_id": raw["GAME-ID"].astype(str).str.strip(),
                       "open_total": pd.to_numeric(raw["OPENING TOTAL_H"],
                                                   errors="coerce")})
    G = G.merge(mk.drop_duplicates("game_id"), on="game_id", how="left")
    G["cal_total"] = calibrate_walkforward(
        G.model_total.values, G.actual_total.values, G.date.values)
    G["dis_open"] = G.cal_total - G.open_total
    G["gid"] = G.game_id.astype(str).str.strip()
    return G[["gid", "date", "season", "model_total", "cal_total",
              "open_total", "actual_total", "dis_open"]]


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate", action="store_true",
                    help="compare the port against the stored frozen dis_open")
    ap.add_argument("--hist", default="/mnt/c/NBA2/dfMaster_OT_2017-2026.csv")
    a = ap.parse_args()
    raw = pd.read_csv(a.hist, low_memory=False)
    G = compute(raw, mode="walkforward")
    print(f"  computed dis_open on {G.dis_open.notna().sum():,} games")
    if a.validate:
        mf = pd.read_csv("movement_full_games.csv")
        mf["gid"] = mf.game_id.astype(str).str.strip()
        J = G.merge(mf[["gid", "dis_open"]].rename(
            columns={"dis_open": "frozen"}), on="gid").dropna(
            subset=["dis_open", "frozen"])
        print(f"  overlap {len(J):,}")
        print(f"  corr(port, FROZEN)        {J.dis_open.corr(J.frozen):+.4f}")
        print(f"  sd port {J.dis_open.std():.2f}  sd frozen {J.frozen.std():.2f}"
              f"  mean diff {(J.dis_open - J.frozen).mean():+.3f}")
        print(f"  mean |diff| {np.abs(J.dis_open - J.frozen).mean():.3f} pts")
