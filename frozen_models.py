"""FROZEN 2026-27 model state engine. Specifications locked 2026-08-30.

Replays every recursion from scratch on each call rather than persisting mutable
state: ~10k games replays in seconds, and a deterministic replay cannot silently
drift or corrupt the way a checkpointed state can. Same approach as
crewshock_live.py.

FROZEN CONSTANTS -- see PREREG_2026_27_PROSPECTIVE A3/B1. Do not tune.
"""
import numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore")

HIST    = "/mnt/c/NBA2/dfMaster_OT_2017-2026.csv"
CURRENT = "/mnt/c/NBA2/dfMaster_2027.csv"          # season-to-date, may not exist yet

# ---- structural pace/efficiency states (Layer 1) ----
HL_PACE, HL_OFF, HL_DEF, HL_LEAGUE = 5.7, 8.6, 7.4, 496.0
CARRY, SHARE = 0.42, 0.54
# ---- m(X) conditional pace-error correction ----
RIDGE_LAMBDA = 20.0
PROFILE = ["pace_H","pace_R","trans_H","trans_R","tov_H","tov_R","tovf_H","tovf_R",
           "ftr_H","ftr_R","ctrl_H","ctrl_R","mu5H","mu5R","ewvH","ewvR","sP",
           "PrefConflict","ControlConflict","TransComp","TovPressure","StyleDist"]
_a = lambda h: 1 - 0.5 ** (1.0 / h)

def load_history(paths=(HIST, CURRENT)):
    """Regular-season games, oldest first.

    Uses prepare_data.read_master/season_label -- the canonical loader for this
    programme -- because the season column changes name across eras
    (DATASET_H for 2017-19, BIGDATABALL\\nDATASET_H afterwards) and
    reimplementing that split silently dropped 8,000 games.
    """
    import sys as _s; _s.path.insert(0, "/home/dpope/projects/nba_entropy_replication")
    from prepare_data import read_master, season_label
    fr = []
    for p in paths:
        try:
            d = read_master(path=p, verbose=False)
        except Exception:
            continue
        d = d.copy(); d["_season"] = season_label(d).astype(str)
        fr.append(d)
    if not fr: raise FileNotFoundError(f"no readable source among {paths}")
    d = pd.concat(fr, ignore_index=True)
    d = d[d["_season"].str.contains("Regular Season", na=False)]
    n = lambda c: pd.to_numeric(d[c], errors="coerce") if c in d else np.nan
    g = pd.DataFrame({
        "date": pd.to_datetime(d["DATE"], errors="coerce"),
        "TEAM_H": d["TEAM_H"], "TEAM_R": d["TEAM_R"],
        "pH": n("PTS_H"), "pR": n("PTS_R"),
        "paceH": n("PACE_H"), "paceR": n("PACE_R"),
        "oH": n("OEFF_H"), "oR": n("OEFF_R"),
        "toH": n("TO_H"), "toR": n("TO_R"),
        "ftaH": n("FTA_H"), "ftaR": n("FTA_R"),
        "fgaH": n("FGA_H"), "fgaR": n("FGA_R"),
        "possH": n("POSS_H"), "possR": n("POSS_R"),
        "open": n("OPENING TOTAL_H"), "ospread": n("OPENING SPREAD_H"),
        "close": n("CLOSING TOTAL_H"), "season": d["_season"].values,
    })
    g = g.dropna(subset=["date","TEAM_H","TEAM_R"]).sort_values("date")
    g["gpace"] = (g.paceH + g.paceR) / 2
    g["played"] = g.pH.notna() & g.paceH.notna()
    return g.reset_index(drop=True)

def build_states(g, as_of):
    """Replay all recursions using ONLY games strictly before `as_of`.

    Same-day safe by construction: the cutoff is a date comparison, so no game on
    `as_of` can influence its own prediction.
    """
    as_of = pd.Timestamp(as_of)
    h = g[(g.date < as_of) & g.played].copy()
    teams = sorted(set(g.TEAM_H.dropna()) | set(g.TEAM_R.dropna()))
    ti = {t: i for i, t in enumerate(teams)}; NT = len(teams)
    Pst, Ost, Dst = np.zeros(NT), np.zeros(NT), np.zeros(NT)
    aP, aO, aD, aL = _a(HL_PACE), _a(HL_OFF), _a(HL_DEF), _a(HL_LEAGUE)
    LP = h.gpace.head(500).mean() if len(h) else 99.0
    LO = pd.concat([h.oH.head(500), h.oR.head(500)]).mean() if len(h) else 112.0
    resid = {t: [] for t in teams}          # per-team pace-forecast errors, in order
    fc = []                                 # per-game FORECASTS, for the a,b fit
    yr = lambda d: d.year if d.month >= 8 else d.year - 1
    prev_season = None
    for r in h.itertuples():
        s = yr(r.date)
        if prev_season is not None and s != prev_season:
            Pst *= CARRY; Ost *= CARRY; Dst *= CARRY
        prev_season = s
        hh, aa = ti[r.TEAM_H], ti[r.TEAM_R]
        sP  = LP + (Pst[hh] + Pst[aa]) / 2
        sOH = LO + Ost[hh] + Dst[aa]; sOR = LO + Ost[aa] + Dst[hh]
        fc.append((r.date, sP, sOH + sOR, r.open))
        ep = r.gpace - sP
        resid[r.TEAM_H].append(ep); resid[r.TEAM_R].append(ep)
        Pst[hh] += aP * ep; Pst[aa] += aP * ep; LP += aL * ep
        eH, eR = r.oH - sOH, r.oR - sOR
        Ost[hh] += SHARE * aO * eH; Dst[aa] += (1 - SHARE) * aD * eH
        Ost[aa] += SHARE * aO * eR; Dst[hh] += (1 - SHARE) * aD * eR
        LO += aL * (eH + eR) / 2
    ab = _fit_ab(fc, as_of)
    return {"teams": teams, "ti": ti, "Pst": Pst, "Ost": Ost, "Dst": Dst,
            "LP": LP, "LO": LO, "resid": resid, "n_games": len(h), "as_of": as_of,
            "ab": ab}

def _fit_ab(fc, as_of):
    """Open ~ a + b * (sP_forecast * EffSum_forecast / 100), COMPLETED PRIOR SEASONS only.

    Must use the FORECAST product, not the realised one. Fitting on realised
    pace x efficiency attenuates the slope badly (errors-in-variables: b fell to
    0.23 and the inversion returned a pace of 125). PREREG A3 item 2 also forbids
    in-season refitting, so the current season is excluded.
    """
    if not fc: return None
    as_of = pd.Timestamp(as_of)
    cur = as_of.year if as_of.month >= 8 else as_of.year - 1
    D = pd.DataFrame(fc, columns=["date","sP","EffSum","open"])
    yr = D.date.dt.year.where(D.date.dt.month >= 8, D.date.dt.year - 1)
    D = D[(yr < cur) & D.open.notna()]
    x = D.sP.values * D.EffSum.values / 100.0
    m = np.isfinite(x) & np.isfinite(D.open.values)
    if m.sum() < 400: return None
    A = np.column_stack([np.ones(m.sum()), x[m]])
    b, *_ = np.linalg.lstsq(A, D.open.values[m], rcond=None)
    return float(b[0]), float(b[1])

def team_profiles(g, as_of):
    """Prior-only team style states. Transition needs PBP and may be absent."""
    as_of = pd.Timestamp(as_of)
    h = g[(g.date < as_of) & g.played]
    rows = []
    for r in h.itertuples():
        for s, o in (("H","R"), ("R","H")):
            rows.append({"t": getattr(r, f"TEAM_{s}"), "date": r.date,
                "pace": getattr(r, f"pace{s}"),
                "tov": 100*getattr(r, f"to{s}")/max(getattr(r, f"poss{s}") or np.nan, 1),
                "tovf": 100*getattr(r, f"to{o}")/max(getattr(r, f"poss{o}") or np.nan, 1),
                "ftr": getattr(r, f"fta{s}")/max(getattr(r, f"fga{s}") or np.nan, 1)})
    if not rows: return {}
    P = pd.DataFrame(rows)
    return {t: {c: gg[c].mean() for c in ("pace","tov","tovf","ftr")}
            for t, gg in P.groupby("t")}

def predict_game(st, prof, team_h, team_r, open_total, open_spread):
    """All frozen quantities for one game. Returns NaN where inputs are missing."""
    ti, LP, LO = st["ti"], st["LP"], st["LO"]
    if team_h not in ti or team_r not in ti:
        raise KeyError(f"unknown team: {team_h} / {team_r}")
    hh, aa = ti[team_h], ti[team_r]
    P_hat = LP + (st["Pst"][hh] + st["Pst"][aa]) / 2
    EffSum = (LO + st["Ost"][hh] + st["Dst"][aa]) + (LO + st["Ost"][aa] + st["Dst"][hh])
    P_book = np.nan
    ab = st.get("ab")
    if np.isfinite(open_total) and np.isfinite(EffSum) and EffSum > 0 and ab is not None:
        a_, b_ = ab                                   # fitted on PRIOR SEASONS ONLY
        if abs(b_) > 1e-9:
            P_book = 100.0 * (open_total - a_) / (b_ * EffSum)
    mu5 = np.nan
    rh, ra = st["resid"].get(team_h, []), st["resid"].get(team_r, [])
    if len(rh) >= 2 and len(ra) >= 2:
        mu5 = (np.mean(rh[-5:]) + np.mean(ra[-5:])) / 2
    m_X = np.nan                                       # requires PBP-derived profile
    return {"P_hat": P_hat, "P_book": P_book, "EffSum": EffSum,
            "mu5": mu5, "m_X": m_X}
