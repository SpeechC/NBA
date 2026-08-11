"""Fix the asymmetric feature set and test pace constructions.

The shipped model gives the HOME team all 16 lagged variables but the away team
only 3 (pace, offensive and defensive efficiency). That is an artefact of how the
panel was joined, not a design choice -- and since `f_PACE_opp` carries the single
largest coefficient, the missing away-team variables are the obvious place to look.

Four specifications, all ridge, all the same walk-forward protocol, all reported:

  A  current (asymmetric, 21 features)                     -- the baseline
  B  symmetric: both teams get all 16                      -- fixes the bug
  C  symmetric + explicit pace constructions               -- sum / diff / product
  D  pace-and-efficiency only, symmetric, plus market       -- is the box score
                                                              doing anything at all?

D matters as much as C: pace dominates the fitted coefficients, so if a
6-feature pace model matches the 34-feature one, the box-score variables are
decoration and the model should be simplified rather than extended.
"""

import warnings

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import RidgeCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from walkforward_pace import ALLV, EXT, build_panel_ext

warnings.filterwarnings("ignore")
RNG = np.random.default_rng(0)


def build():
    g = pd.read_csv("movement_full_games.csv", parse_dates=["date"])
    g["gid"] = g["game_id"].astype(str)
    panel, _ = build_panel_ext()
    panel["gid"] = panel["game_id"].astype(str)

    fcols = [f"f_{v}" for v in ALLV]
    h = panel[panel["home"] == 1].set_index("gid")[fcols].add_prefix("h_")
    a = panel[panel["home"] == 0].set_index("gid")[fcols].add_prefix("a_")
    G = g.set_index("gid").join(h).join(a).reset_index()

    # explicit pace constructions -- pace dominates the fitted model
    G["pace_sum"] = G["h_f_PACE"] + G["a_f_PACE"]
    G["pace_diff"] = G["h_f_PACE"] - G["a_f_PACE"]
    G["pace_absdiff"] = G["pace_diff"].abs()
    G["pace_prod"] = G["h_f_PACE"] * G["a_f_PACE"] / 100
    G["oeff_sum"] = G["h_f_OEFF"] + G["a_f_OEFF"]
    G["deff_sum"] = G["h_f_DEFF"] + G["a_f_DEFF"]
    # implied total from pace x efficiency, the structural estimate
    G["implied_total"] = (G["pace_sum"] / 2) * (G["oeff_sum"]) / 100
    G["implied_minus_open"] = G["implied_total"] - G["open_total"]
    return G.sort_values("date").reset_index(drop=True)


def walk(X, y, dates, step=7, min_train=500):
    pred = np.full(len(y), np.nan)
    uniq = np.unique(dates)
    cnt = np.cumsum([np.sum(dates == u) for u in uniq])
    cuts = pd.date_range(pd.Timestamp(uniq[np.searchsorted(cnt, min_train)]),
                         pd.Timestamp(uniq.max()) + pd.Timedelta(days=1), freq=f"{step}D")
    for i, c in enumerate(cuts):
        nxt = cuts[i + 1] if i + 1 < len(cuts) else pd.Timestamp(uniq.max()) + pd.Timedelta(days=1)
        tr = dates < np.datetime64(c)
        te = (dates >= np.datetime64(c)) & (dates < np.datetime64(nxt))
        if te.sum() == 0 or tr.sum() < min_train:
            continue
        m = make_pipeline(StandardScaler(), RidgeCV(alphas=np.logspace(-2, 3, 20)))
        m.fit(X[tr], y[tr])
        pred[te] = m.predict(X[te])
    return pred


def evaluate(G, feats, label):
    d = G.dropna(subset=feats + ["move_total", "actual_total", "open_total"]).reset_index(drop=True)
    p = walk(d[feats].values, d["move_total"].values.astype(float), d["date"].values)
    d = d.assign(pm=p).dropna(subset=["pm"])
    rows = []
    for thr in (0, 1, 1.5):
        s = d[d["pm"].abs() > thr]
        s = s[s["actual_total"] != s["open_total"]]
        if len(s) < 100:
            continue
        over = (s["actual_total"] > s["open_total"]).values
        win = np.where((s["pm"] > 0).values, over, ~over).astype(float)
        n, w = len(win), win.mean()
        clv = np.where(s["pm"] > 0, s["move_total"], -s["move_total"])
        bs = np.array([RNG.choice(win, n, replace=True).mean() for _ in range(4000)])
        roi_bs = bs * (100 / 110) - (1 - bs)
        rows.append({"spec": label, "n feats": len(feats), "thr": thr, "n": n,
                     "corr": float(np.corrcoef(d["pm"], d["move_total"])[0, 1]),
                     "CLV": clv.mean(), "beat close %": 100 * (clv > 0).mean(),
                     "win %": 100 * w,
                     "ROI %": 100 * (w * (100 / 110) - (1 - w)),
                     "P(ROI>0) %": 100 * (roi_bs > 0).mean()})
    return pd.DataFrame(rows)


def main():
    G = build()
    print(f"games {len(G):,}  {G['date'].min().date()} .. {G['date'].max().date()}\n")

    MKT = ["open_total", "dis_open"]
    home16 = [f"h_f_{v}" for v in ALLV]
    away16 = [f"a_f_{v}" for v in ALLV]
    away3 = [f"a_f_{v}" for v in EXT]
    paceX = ["pace_sum", "pace_diff", "pace_absdiff", "pace_prod",
             "oeff_sum", "deff_sum", "implied_minus_open"]

    specs = {
        "A current (asymmetric)": MKT + home16 + away3,
        "B symmetric": MKT + home16 + away16,
        "C symmetric + pace terms": MKT + home16 + away16 + paceX,
        "D pace/eff only": MKT + [f"h_f_{v}" for v in EXT] + away3 + paceX,
    }
    out = [evaluate(G, f, k) for k, f in specs.items()]
    res = pd.concat(out, ignore_index=True)
    print(res.round(3).to_string(index=False))
    res.to_csv("symmetric_results.csv", index=False)

    # what does the symmetric model weight?
    feats = specs["B symmetric"]
    d = G.dropna(subset=feats + ["move_total"]).reset_index(drop=True)
    m = make_pipeline(StandardScaler(), RidgeCV(alphas=np.logspace(-2, 3, 20)))
    m.fit(d[feats].values, d["move_total"].values)
    s = pd.Series(m[-1].coef_, index=feats).sort_values(key=abs, ascending=False)
    print("\ntop 12 coefficients, symmetric spec (full-sample fit, illustrative):")
    print(s.head(12).round(4).to_string())


if __name__ == "__main__":
    main()
