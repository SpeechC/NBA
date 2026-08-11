"""Scoring-surprise EWMA: generalising the O/U-streak finding.

Pre-registered. One run, reported either way.

Motivation. A binary "did the last game go over" already predicts line movement
monotonically and captures roughly half the frozen model's CLV standalone. That is
a crude proxy for what is probably the real mechanism:

    recent scoring surprise  ->  public Over demand  ->  the total rises

The right variable is not raw scoring but scoring relative to what the market
expected:

    SURPRISE_t = actual_total_t - closing_total_t

normalised against the market's own forecast, then exponentially weighted so that
recent surprises count more. Raw team scoring would confound "this team scores a
lot" (known and priced) with "this team has been beating expectations lately"
(the extrapolation the flow story predicts).

Everything is lagged strictly: a game's features use only games that finished
before it, within season.

Baseline to beat: frozen spec A, CLV +0.746 all / ROI +3.18% at |pred| > 1.25.
"""

import warnings

import numpy as np
import pandas as pd
from scipy import stats

from models_frozen import SPECS, add_pace_terms, walk_forward
from prepare_data import CSV, season_label
from symmetric_features import build

warnings.filterwarnings("ignore")
RNG = np.random.default_rng(0)
THRESH = 1.25
HALFLIVES = (2, 3, 5, 10)


def surprise_features():
    """Per team-game EWMAs of (actual total - closing total), strictly lagged."""
    raw = pd.read_csv(CSV, low_memory=False)
    raw["season"] = season_label(raw)
    r = raw[raw["season"].str.contains("Regular Season|In-Season", na=False)].copy()
    r["date"] = pd.to_datetime(r["DATE"])
    r["gid"] = (r["GAME-ID"].astype(str)
                .str.replace(r"\.0$", "", regex=True).str.zfill(10))
    ct = pd.to_numeric(r["CLOSING TOTAL_H"], errors="coerce")
    tot = (pd.to_numeric(r["PTS_H"], errors="coerce")
           + pd.to_numeric(r["PTS_R"], errors="coerce"))
    r = r[ct.between(150, 300)].copy()
    r["surprise"] = tot[ct.between(150, 300)] - ct[ct.between(150, 300)]

    from team_mapping import NAME_TO_ID
    sides = []
    for suf in ("H", "R"):
        sides.append(pd.DataFrame({
            "gid": r["gid"], "date": r["date"], "season": r["season"],
            "team": r[f"TEAM_{suf}"].map(NAME_TO_ID),
            "is_home": suf == "H", "surprise": r["surprise"]}))
    p = pd.concat(sides, ignore_index=True).dropna(subset=["team", "surprise"])
    p = p.sort_values(["season", "team", "date"]).reset_index(drop=True)

    g = p.groupby(["season", "team"])
    for hl in HALFLIVES:
        p[f"sur_ewm{hl}"] = g["surprise"].transform(
            lambda s: s.shift(1).ewm(halflife=hl, min_periods=2).mean())
    # cumulative signed surprise and recent absolute surprise (volatility of surprise)
    p["sur_cum"] = g["surprise"].transform(lambda s: s.shift(1).expanding().mean())
    p["sur_abs5"] = g["surprise"].transform(
        lambda s: s.shift(1).abs().rolling(5).mean())
    cols = [f"sur_ewm{hl}" for hl in HALFLIVES] + ["sur_cum", "sur_abs5"]

    h = p[p["is_home"]].set_index("gid")[cols].add_prefix("h_")
    a = p[~p["is_home"]].set_index("gid")[cols].add_prefix("a_")
    out = h.join(a)
    for c in cols:                       # combined and differential forms
        out[f"sum_{c}"] = out[f"h_{c}"] + out[f"a_{c}"]
        out[f"dif_{c}"] = out[f"h_{c}"] - out[f"a_{c}"]
    return out.reset_index().rename(columns={"index": "gid"}), cols


def evaluate(G, feats, label):
    d = G.dropna(subset=feats + ["move_total", "actual_total", "open_total"])
    d = d.reset_index(drop=True)
    d["pm"] = walk_forward(d[feats].values, d["move_total"].values.astype(float),
                           d["date"].values)
    d = d.dropna(subset=["pm"])
    rows = []
    for thr in (0, 1.0, 1.25, 1.5):
        s = d[(d["pm"].abs() > thr) & (d["actual_total"] != d["open_total"])]
        if len(s) < 80:
            continue
        over = (s["actual_total"] > s["open_total"]).values
        win = np.where((s["pm"] > 0).values, over, ~over).astype(float)
        n, w = len(win), win.mean()
        clv = np.where(s["pm"] > 0, s["move_total"], -s["move_total"])
        bs = np.array([RNG.choice(win, n, replace=True).mean() for _ in range(5000)])
        roi_bs = bs * (100 / 110) - (1 - bs)
        rows.append({"spec": label, "thr": thr, "n": n,
                     "corr": float(np.corrcoef(d["pm"], d["move_total"])[0, 1]),
                     "CLV": clv.mean(), "beat close %": 100 * (clv > 0).mean(),
                     "win %": 100 * w,
                     "ROI %": 100 * (w * (100 / 110) - (1 - w)),
                     "P(ROI>0) %": 100 * (roi_bs > 0).mean()})
    return pd.DataFrame(rows)


def main():
    G = add_pace_terms(build())
    sur, cols = surprise_features()
    # normalise the join key on BOTH sides: G carries 8-char ids, the odds file
    # zfills to 10. This exact mismatch silently produced an all-NaN merge once.
    G["gid"] = G["gid"].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(10)
    sur["gid"] = sur["gid"].astype(str).str.zfill(10)
    G = G.merge(sur, on="gid", how="left")
    assert G["sum_sur_ewm3"].notna().mean() > 0.5, "surprise merge failed"

    base = SPECS["A"]
    sum_cols = [f"sum_{c}" for c in cols]
    dif_cols = [f"dif_{c}" for c in cols]
    side_cols = [f"{p}_{c}" for p in ("h", "a") for c in cols]

    specs = {
        "A frozen baseline": base,
        "A + surprise (combined)": base + sum_cols,
        "A + surprise (both sides)": base + side_cols,
        "A + surprise (all forms)": base + side_cols + sum_cols + dif_cols,
    }
    out = pd.concat([evaluate(G, f, k) for k, f in specs.items()], ignore_index=True)
    print(out.round(3).to_string(index=False))
    out.to_csv("surprise_results.csv", index=False)

    # is the mechanism monotone, before any model?
    d = G.dropna(subset=["sum_sur_ewm3", "move_total"]).copy()
    d["q"] = pd.qcut(d["sum_sur_ewm3"], 5, duplicates="drop",
                     labels=["most under", "2", "neutral", "4", "most over"])
    t = d.groupby("q", observed=True).agg(n=("move_total", "size"),
                                          mean_surprise=("sum_sur_ewm3", "mean"),
                                          mean_move=("move_total", "mean"))
    print("\n=== raw mechanism check: line movement by recent scoring surprise ===")
    print(t.round(3).to_string())
    r = np.corrcoef(d["sum_sur_ewm3"], d["move_total"])[0, 1]
    print(f"\ncorr(combined 3-game surprise EWMA, line movement) = {r:+.4f}")
    print("(binary O/U streak gave a monotone -0.40 .. +0.28 spread)")


if __name__ == "__main__":
    main()
