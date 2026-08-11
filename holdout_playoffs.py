"""Playoffs as a true holdout: 526 games no model in this project has seen.

Every model filtered to "Regular Season|In-Season". Playoff and play-in games
carry full opening and closing totals and were never used for fitting, feature
selection, estimator choice or threshold choice. That makes them the only
genuinely untouched sample available.

Two things have to be right for the test to be fair:

  * lags must CARRY from the regular season into the playoffs. A team's first
    playoff game must use its last four regular-season games, not restart from
    empty. Playoff labels ("NBA 2024 Playoffs") are therefore mapped onto their
    parent season ("NBA 2023-2024") for the rolling windows.
  * the model must only ever be fitted on games that finished earlier. It is
    refit on all completed regular-season games before each playoff date.

Caveat stated up front, not discovered later: playoffs are a different regime --
sharper markets, shorter rotations, slower pace, more public attention. A null
here is genuinely ambiguous between "the edge is not real" and "the edge does not
transfer to playoffs".
"""

import re
import warnings

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import RidgeCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from models_frozen import SPECS, add_pace_terms
from prepare_data import CSV, VARS, season_label, _side
from symmetric_features import build
from walkforward_pace import ALLV, EXT

warnings.filterwarnings("ignore")
RNG = np.random.default_rng(0)
THRESH = 1.25
LAG = 4


def parent_season(label):
    """'NBA 2024 Playoffs' -> 'NBA 2023-2024'; regular season passes through."""
    if pd.isna(label):
        return label
    m = re.search(r"(\d{4})-(\d{4})", str(label))
    if m:
        return f"NBA {m.group(1)}-{m.group(2)}"
    m = re.search(r"NBA (\d{4})", str(label))
    if m:                                    # playoffs / play-in of that year
        y = int(m.group(1))
        return f"NBA {y - 1}-{y}"
    return label


def build_all():
    """Team-game panel spanning regular season AND playoffs, lags carrying over."""
    raw = pd.read_csv(CSV, low_memory=False)
    raw["season_raw"] = season_label(raw)
    raw = raw[raw["season_raw"].notna()].copy()
    raw["season"] = raw["season_raw"].map(parent_season)
    raw["is_playoff"] = raw["season_raw"].str.contains("Playoffs|Play-in|Play-In",
                                                       na=False)

    sides = []
    for suf, osuf in (("H", "R"), ("R", "H")):
        s = _side(raw, suf)
        for v in EXT:
            s[v] = pd.to_numeric(raw[f"{v}_{suf}"], errors="coerce").values
        s["is_playoff"] = raw["is_playoff"].values
        sides.append(s)
    p = pd.concat(sides, ignore_index=True)
    p["season"] = p["game_id"].map(raw.set_index("GAME-ID")["season"])
    p = p.sort_values(["season", "team", "date", "game_id"]).reset_index(drop=True)
    p[ALLV] = p[ALLV].astype(float)

    f = (p.groupby(["season", "team"])[ALLV]
           .apply(lambda g: g.shift(1).rolling(LAG).mean())
           .reset_index(level=[0, 1], drop=True).sort_index())
    f.columns = [f"f_{c}" for c in f.columns]
    p = pd.concat([p, f], axis=1)

    h = p[p["home"] == 1].set_index("game_id")
    a = p[p["home"] == 0].set_index("game_id")
    fc = [f"f_{v}" for v in ALLV]
    G = pd.DataFrame({"date": h["date"], "season": h["season"],
                      "is_playoff": h["is_playoff"],
                      "actual_total": h["Y"] + a["Y"]})
    for c in fc:
        G[f"h_{c}"] = h[c]
        G[f"a_{c}"] = a[c]

    mk = pd.DataFrame({
        "game_id": raw["GAME-ID"],
        "open_total": pd.to_numeric(raw["OPENING TOTAL_H"], errors="coerce"),
        "close_total": pd.to_numeric(raw["CLOSING TOTAL_H"], errors="coerce")})
    G = G.join(mk.set_index("game_id"))
    G = G[G["open_total"].between(150, 300) & G["close_total"].between(150, 300)]
    G["move_total"] = G["close_total"] - G["open_total"]
    return G.dropna(subset=["actual_total"]).sort_values("date").reset_index(drop=True)


def econ(d, label):
    s = d[(d["pm"].abs() > THRESH) & (d["actual_total"] != d["open_total"])]
    if len(s) < 25:
        return {"sample": label, "n": len(s), "note": "too few bets"}
    over = (s["actual_total"] > s["open_total"]).values
    win = np.where((s["pm"] > 0).values, over, ~over).astype(float)
    n, w = len(win), win.mean()
    lo, hi = stats.beta.ppf([.025, .975], win.sum() + .5, n - win.sum() + .5)
    clv = np.where(s["pm"] > 0, s["move_total"], -s["move_total"])
    bs = np.array([RNG.choice(win, n, replace=True).mean() for _ in range(6000)])
    roi_bs = bs * (100 / 110) - (1 - bs)
    return {"sample": label, "n": n, "CLV": clv.mean(),
            "beat close %": 100 * (clv > 0).mean(), "win %": 100 * w,
            "win lo": 100 * lo, "win hi": 100 * hi,
            "ROI %": 100 * (w * (100 / 110) - (1 - w)),
            "ROI lo": 100 * np.percentile(roi_bs, 2.5),
            "ROI hi": 100 * np.percentile(roi_bs, 97.5),
            "P(ROI>0) %": 100 * (roi_bs > 0).mean()}


def main():
    G = add_pace_terms(build_all())
    # dis_open needs the upstream score model; approximate it with the structural
    # implied total, which is what it mostly proxies (and is available here)
    G["dis_open"] = G["implied_minus_open"]
    feats = SPECS["A"]
    G = G.dropna(subset=feats + ["move_total", "actual_total"]).reset_index(drop=True)

    reg = G[~G["is_playoff"]]
    po = G[G["is_playoff"]].copy()
    print(f"regular season {len(reg):,}   playoff/play-in {len(po):,}\n")

    # refit on completed REGULAR-SEASON games only, predict playoffs
    est = make_pipeline(StandardScaler(), RidgeCV(alphas=np.logspace(-2, 3, 20)))
    pm = np.full(len(po), np.nan)
    for i, row in enumerate(po.itertuples()):
        pass
    # refit per playoff run (they cluster in April-June) rather than per game
    po = po.sort_values("date").reset_index(drop=True)
    for cut in pd.date_range(po["date"].min(), po["date"].max() + pd.Timedelta(days=30),
                             freq="15D"):
        nxt = cut + pd.Timedelta(days=15)
        hist = reg[reg["date"] < cut]
        te = ((po["date"] >= cut) & (po["date"] < nxt)).values
        if te.sum() == 0 or len(hist) < 1000:
            continue
        est.fit(hist[feats].values, hist["move_total"].values.astype(float))
        pm[te] = est.predict(po.loc[te, feats].values)
    po["pm"] = pm
    po = po.dropna(subset=["pm"])

    print("=== TRUE HOLDOUT: playoffs and play-in, never used ===")
    print(pd.DataFrame([econ(po, "playoffs/play-in")]).round(3).to_string(index=False))
    print(f"\nselection rate {100 * (po['pm'].abs() > THRESH).mean():.1f}% "
          f"of {len(po)} playoff games")
    print(f"prediction SD {po['pm'].std():.3f}  (regular season ~1.0)")

    # regime check: is playoff movement even comparable?
    print("\n=== regime check ===")
    for lab, s in (("regular season", reg), ("playoffs", po)):
        print(f"  {lab:16} move SD {s['move_total'].std():.3f}   "
              f"mean |move| {s['move_total'].abs().mean():.3f}   "
              f"mean total {s['close_total'].mean():.1f}")


if __name__ == "__main__":
    main()
