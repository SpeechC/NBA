"""Three confirmations for the favourite-H1 late-season effect.

1 MARKET-CONDITION IT.  Raw favourite H1 points could be elevated simply because
  late-season favourites are stronger favourites, or the games have higher totals.
  The book's own closing numbers imply a favourite team total:

      implied_fav_TT = (closing_total + |closing_spread|) / 2

  which is the market's estimate of that team's full-game scoring. Fitting
  fav_H1 on that (plus season effects) using ONLY games outside the window, then
  measuring the residual inside it, converts the claim from "favourites scored
  more" to "favourites scored more in H1 than the sportsbook's own assessment of
  team strength and scoring environment implies". That is a pricing-model failure
  rather than a scoring observation.

2 MAX-OF-FOUR PERMUTATION.  The favourite-H1 cell was selected after inspecting
  four cells, so its t must be compared against the distribution of the MAXIMUM
  of four t's under the null. The late-season flag is shuffled WITHIN season,
  preserving each season's count of late games and each game's four cells.

3 DECAY.  Effects of +3.18/+3.08/+3.90 followed by +0.73/+0.90/+0.46 mean the
  pooled +2.013 may not be the economically relevant number. Reported as a
  trend with season-block inference, and as full-history versus recent-three.
  With seven seasons the p-value on the trend is nearly meaningless; the point
  estimate of the CURRENT regime is what matters.
"""
import warnings

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")
RNG = np.random.default_rng(0)

WINDOW = 7
FIT_OUTSIDE = 14        # fit the market model on days_left > 14


def build():
    from halves import period_scores
    from prepare_data import CSV, season_label
    raw = pd.read_csv(CSV, low_memory=False)
    raw["season"] = season_label(raw).astype(str)
    d = raw[raw["season"].str.contains("Regular Season", na=False)].copy()
    d["gid"] = d["GAME-ID"].astype(str).str.zfill(10)
    d["date"] = pd.to_datetime(d["DATE"], errors="coerce")
    d["spread"] = pd.to_numeric(d["CLOSING SPREAD_H"], errors="coerce")
    d["close_total"] = pd.to_numeric(d["CLOSING TOTAL_H"], errors="coerce")
    d["days_left"] = (d.groupby("season")["date"].transform("max")
                      - d["date"]).dt.days
    d = d.dropna(subset=["spread", "close_total", "date"])

    w = period_scores()
    keep = ["gid"] + [f"{s}_p{q}" for s in ("home", "vis") for q in (1, 2, 3, 4)]
    m = d.merge(w[keep], on="gid", how="inner")
    hf = m["spread"] < 0
    m["fav_h1"] = np.where(hf, m["home_p1"] + m["home_p2"], m["vis_p1"] + m["vis_p2"])
    m["fav_h2"] = np.where(hf, m["home_p3"] + m["home_p4"], m["vis_p3"] + m["vis_p4"])
    m["dog_h1"] = np.where(hf, m["vis_p1"] + m["vis_p2"], m["home_p1"] + m["home_p2"])
    m["dog_h2"] = np.where(hf, m["vis_p3"] + m["vis_p4"], m["home_p3"] + m["home_p4"])
    m = m[(m["fav_h1"] > 25) & (m["dog_h1"] > 25)]
    m["abs_spread"] = m["spread"].abs()
    m["imp_fav_tt"] = (m["close_total"] + m["abs_spread"]) / 2
    m["imp_dog_tt"] = (m["close_total"] - m["abs_spread"]) / 2
    m["late"] = m["days_left"] <= WINDOW
    m["sidx"] = m["season"].rank(method="dense").astype(int) - 1
    return m.reset_index(drop=True)


def design(x, season_dummies, cols):
    X = [np.ones(len(x))] + [x[c].values for c in cols]
    for s in season_dummies[1:]:
        X.append((x["season"] == s).astype(float).values)
    return np.column_stack(X)


def residualise(m, target, cols):
    """Fit on games outside the window; return residuals everywhere."""
    seasons = sorted(m["season"].unique())
    fit = m[m["days_left"] > FIT_OUTSIDE]
    Xf, yf = design(fit, seasons, cols), fit[target].values
    beta, *_ = np.linalg.lstsq(Xf, yf, rcond=None)
    Xa = design(m, seasons, cols)
    return m[target].values - Xa @ beta, beta


def tstat(m, col, flag="late"):
    a, b = m.loc[m[flag], col], m.loc[~m[flag] & (m["days_left"] > FIT_OUTSIDE), col]
    return stats.ttest_ind(a, b, equal_var=False)[0], a.mean() - b.mean()


def main():
    m = build()
    print(f"{len(m):,} games   late {int(m['late'].sum()):,}   "
          f"{m['season'].nunique()} seasons\n")

    print("=" * 100)
    print("1. MARKET-CONDITIONED — residual against the book's own implied numbers")
    print("=" * 100)
    cols = ["imp_fav_tt", "close_total", "abs_spread"]
    for target in ("fav_h1", "fav_h2", "dog_h1", "dog_h2"):
        r, beta = residualise(m, target, cols)
        m[f"r_{target}"] = r
    print(f"  model: {' + '.join(cols)} + season effects, fit on "
          f"days_left > {FIT_OUTSIDE}\n")
    rows = []
    for target in ("fav_h1", "fav_h2", "dog_h1", "dog_h2"):
        raw_t, raw_d = tstat(m, target)
        res_t, res_d = tstat(m, f"r_{target}")
        rows.append({"cell": target, "RAW diff": round(raw_d, 3),
                     "raw t": round(raw_t, 2),
                     "MARKET-CONDITIONED diff": round(res_d, 3),
                     "cond t": round(res_t, 2),
                     "retained": f"{100*res_d/raw_d:.0f}%" if raw_d else "—"})
    print(pd.DataFrame(rows).to_string(index=False))
    print("\n  'retained' = how much of the raw effect survives conditioning on")
    print("  the market's own view. Near 100% means the book's numbers do not")
    print("  anticipate it at all.")

    print("\n" + "=" * 100)
    print("2. MAX-OF-FOUR PERMUTATION (late flag shuffled within season)")
    print("=" * 100)
    for tag, pre in (("raw", ""), ("market-conditioned", "r_")):
        cells = [f"{pre}{c}" for c in ("fav_h1", "fav_h2", "dog_h1", "dog_h2")]
        obs = max(abs(tstat(m, c)[0]) for c in cells)
        obs_fav = tstat(m, f"{pre}fav_h1")[0]
        null = []
        for _ in range(2000):
            p = m.copy()
            p["late"] = (p.groupby("season")["late"]
                         .transform(lambda s: RNG.permutation(s.values)))
            null.append(max(abs(tstat(p, c)[0]) for c in cells))
        null = np.array(null)
        print(f"  {tag:20} observed fav_H1 t = {obs_fav:+.2f}   "
              f"max|t| over 4 cells = {obs:.2f}")
        print(f"  {'':20} null max|t|: {null.mean():.2f} ± {null.std():.2f}   "
              f"95th pct {np.percentile(null,95):.2f}   "
              f"p = {np.mean(null >= obs):.4f}")

    print("\n" + "=" * 100)
    print("3. DECAY — is the current regime +2.0 or +0.7?")
    print("=" * 100)
    rows = []
    for s in sorted(m["season"].unique()):
        sm = m[m["season"] == s]
        a = sm.loc[sm["late"], "r_fav_h1"]
        b = sm.loc[~sm["late"] & (sm["days_left"] > FIT_OUTSIDE), "r_fav_h1"]
        raw_a = sm.loc[sm["late"], "fav_h1"]
        raw_b = sm.loc[~sm["late"] & (sm["days_left"] > FIT_OUTSIDE), "fav_h1"]
        rows.append({"season": s[4:13], "n late": len(a),
                     "RAW diff": round(raw_a.mean() - raw_b.mean(), 2),
                     "CONDITIONED diff": round(a.mean() - b.mean(), 2)})
    t = pd.DataFrame(rows)
    print(t.to_string(index=False))

    y = t["CONDITIONED diff"].values
    x = np.arange(len(y))
    sl, ic, r, p, se = stats.linregress(x, y)
    print(f"\n  trend on the conditioned effect: {sl:+.3f} pts/season "
          f"(se {se:.3f}, p={p:.3f}, n=7 seasons)")
    print(f"  full history mean : {y.mean():+.3f}")
    print(f"  recent 3 seasons  : {y[-3:].mean():+.3f}")
    print(f"  first 4 seasons   : {y[:4].mean():+.3f}")
    print("\n  With 7 season-blocks the trend p-value carries little weight;")
    print("  the recent-3 point estimate is the economically relevant figure.")

    # what the recent estimate implies for a 1H team total
    base = m.loc[~m["late"] & (m["days_left"] > FIT_OUTSIDE), "fav_h1"].mean()
    for lab, eff in (("full history", y.mean()), ("recent 3", y[-3:].mean())):
        sd = m.loc[m["late"], "fav_h1"].std()
        need = 0.0597 * sd
        print(f"  {lab:14} effect {eff:+.3f} pts vs break-even requirement "
              f"{need:.3f} pts (0.0597 x sd {sd:.2f})  "
              f"-> {'CLEARS' if eff > need else 'SHORT'}")


if __name__ == "__main__":
    main()
