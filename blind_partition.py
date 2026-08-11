"""Blind search for partitions of game-space where the CLOSING line is biased.

Every angle tested so far was hypothesis-driven -- mismatch, extremes, teams,
season phase. This inverts that: let a tree search the feature space for regions
where `actual_total - close_total` departs from zero, with no prior about where
to look. "Blind statistical factors" rather than basketball reasoning.

Target is deliberately `actual - CLOSE`, not the open-to-close move. Everything
in this project so far has predicted the MOVE, which front-runs a correction the
market makes anyway -- hence real CLV and no win rate. Bias against the CLOSE is
the thing that actually pays.

The method is designed around the fact that a tree WILL find something. A depth-3
tree evaluates thousands of candidate splits, so its best leaf is an extreme
order statistic and looks impressive on noise alone. Three controls:

  1. fit on DEVELOPMENT only
  2. permutation null -- refit the identical tree on shuffled residuals many
     times and record the largest |leaf mean| each time. That distribution is
     what "nothing there" looks like after the same search.
  3. anything surviving is checked on the HOLDOUT, untouched by the search.

A leaf is only interesting if it beats the permuted maximum AND repeats out of
sample. Break-even needs |bias| >= 0.76 points, from 12.7 sd through -110 vig.
"""
import warnings

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.tree import DecisionTreeRegressor, export_text

warnings.filterwarnings("ignore")
RNG = np.random.default_rng(0)

import data_split as ds
from models_frozen import SPECS, add_pace_terms
from prepare_data import CSV, season_label
from symmetric_features import build

BREAK_EVEN_BIAS = 1.08      # points needed to clear -110: 0.0597 * 18.08 sd of
                            # the TOTAL residual (not 12.7, which is one team)
MAX_DEPTH = 3
MIN_LEAF = 250
N_PERM = 400


def panel():
    G = add_pace_terms(build()).sort_values("date").reset_index(drop=True)

    # bring in closing spread and walk-forward W-L, which §14 showed matter
    raw = pd.read_csv(CSV, low_memory=False)
    raw["season_r"] = season_label(raw).astype(str)
    raw["game_id"] = raw["GAME-ID"].astype(str).str.zfill(10)
    r = raw[["game_id", "CLOSING SPREAD_H", "TEAM\nREST DAYS_H",
             "TEAM\nREST DAYS_R"]].copy()
    r.columns = ["game_id", "close_spread", "rest_h", "rest_a"]
    G["game_id"] = G["game_id"].astype(str).str.zfill(10)
    G = G.merge(r, on="game_id", how="left")

    G["abs_spread"] = G["close_spread"].abs()
    G["rest_diff"] = pd.to_numeric(G["rest_h"], errors="coerce") - \
        pd.to_numeric(G["rest_a"], errors="coerce")
    G["resid"] = G["actual_total"] - G["close_total"]
    G["month"] = G["date"].dt.month
    return G.dropna(subset=["resid", "close_total"])


def leaves(tree, X, y, names):
    """Per-leaf n, mean residual and t-stat."""
    node = tree.apply(X)
    out = []
    for nid in np.unique(node):
        m = node == nid
        v = y[m]
        t = v.mean() / (v.std(ddof=1) / np.sqrt(len(v))) if len(v) > 2 else np.nan
        out.append({"leaf": int(nid), "n": int(m.sum()),
                    "bias": round(v.mean(), 3), "t": round(t, 2)})
    return pd.DataFrame(out).sort_values("bias")


def main():
    G = panel()
    feats = [c for c in (SPECS["A"] + ["pace_sum", "pace_diff", "pace_absdiff",
                                       "implied_minus_open", "abs_spread",
                                       "close_spread", "month",
                                       "close_total"])
             if c in G.columns]
    d = G.dropna(subset=feats + ["resid"]).copy()
    dev, ho = ds.split(d)
    print(f"features {len(feats)}   dev {len(dev):,}   holdout {len(ho):,}")
    print(f"dev mean residual {dev['resid'].mean():+.3f} "
          f"(sd {dev['resid'].std():.2f})  -- the market's overall bias\n")

    Xd, yd = dev[feats].values, dev["resid"].values
    tree = DecisionTreeRegressor(max_depth=MAX_DEPTH, min_samples_leaf=MIN_LEAF,
                                 random_state=0).fit(Xd, yd)
    L = leaves(tree, Xd, yd, feats)
    print("=" * 96)
    print("DEVELOPMENT leaves found by blind search")
    print("=" * 96)
    print(L.to_string(index=False))
    best = max(abs(L["bias"].min()), abs(L["bias"].max()))
    print(f"\nlargest |leaf bias| found: {best:.3f} points "
          f"(break-even needs {BREAK_EVEN_BIAS})")

    print("\n" + "=" * 96)
    print(f"PERMUTATION NULL — same search on {N_PERM} shuffled residuals")
    print("=" * 96)
    null = []
    for _ in range(N_PERM):
        yp = RNG.permutation(yd)
        tp = DecisionTreeRegressor(max_depth=MAX_DEPTH, min_samples_leaf=MIN_LEAF,
                                   random_state=0).fit(Xd, yp)
        lp = leaves(tp, Xd, yp, feats)
        null.append(max(abs(lp["bias"].min()), abs(lp["bias"].max())))
    null = np.array(null)
    print(f"  max |leaf bias| on pure noise: {null.mean():.3f} +/- {null.std():.3f}")
    print(f"  95th percentile of null:       {np.percentile(null, 95):.3f}")
    print(f"  observed:                      {best:.3f}")
    print(f"  percentile of observed:        {100*np.mean(null < best):.1f}")
    verdict = ("EXCEEDS the null" if best > np.percentile(null, 95)
               else "INSIDE the null — this is what the search finds on noise")
    print(f"  --> {verdict}")

    print("\n" + "=" * 96)
    print("HOLDOUT: do the same leaves repeat?")
    print("=" * 96)
    Xh, yh = ho[feats].values, ho["resid"].values
    nh = tree.apply(Xh)
    nd = tree.apply(Xd)
    rows = []
    for nid in np.unique(nd):
        vd, vh = yd[nd == nid], yh[nh == nid]
        if len(vh) < 40:
            continue
        rows.append({"leaf": int(nid), "dev n": len(vd),
                     "dev bias": round(vd.mean(), 3),
                     "ho n": len(vh), "ho bias": round(vh.mean(), 3),
                     "same sign": bool(np.sign(vd.mean()) == np.sign(vh.mean()))})
    R = pd.DataFrame(rows)
    print(R.to_string(index=False))
    if len(R):
        agree = R["same sign"].mean()
        r = np.corrcoef(R["dev bias"], R["ho bias"])[0, 1] if len(R) > 2 else np.nan
        print(f"\n  leaves keeping their sign out of sample: "
              f"{int(R['same sign'].sum())}/{len(R)} ({100*agree:.0f}%, chance 50%)")
        print(f"  corr(dev bias, holdout bias) across leaves: {r:+.3f}")

    print("\n" + "=" * 96)
    print("The tree the search actually built")
    print("=" * 96)
    print(export_text(tree, feature_names=feats, max_depth=MAX_DEPTH,
                      decimals=2)[:2600])


if __name__ == "__main__":
    main()
