"""Is CBB a candidate for MODELLING? — conditional predictability test.

Stage 1 asked whether the unconditional closing line is beatable. It is not.
That does not settle modelling candidacy, which turns on whether the residual
the line leaves behind is PREDICTABLE from information available before tip-off.

THE BAR (derived in the session, verified by simulation):
    win rate ~ 0.5 + 0.3183 * rho,  rho = corr(prediction, residual)
    -110 needs rho = 0.0748  ->  R2 = 0.559% on the RESIDUAL
    -105 needs rho = 0.0383  ->  R2 = 0.147%
    -102 needs rho = 0.0157  ->  R2 = 0.025%

Note the scale: the CBB closing line already explains 21.3% of total variance
and 39.4% of margin variance. The target is not "beat 7.6% R2 on the total" —
that would be far worse than the line. It is 0.56% on what the line missed.

PRE-REGISTERED SPECIFICATION (fixed before running; no variants tried):
  features  rolling pre-game team form, prior games only, min 5 games burn-in:
            OEFF/DEFF/PACE for each side, their sums and differences,
            rest days, games played, the closing line itself, |closing spread|
  target    totals: total_pts - close_total ; sides: margin + close_spread
  model     Ridge(alpha=1.0) on standardised features
  split     first 60% of games by date = train, last 40% = test. No shuffling.
  decision  OOS R2 on the residual vs the 0.559% bar; OOS win rate vs 52.38%;
            permutation null on the OOS win rate (500 target shuffles)
"""
import numpy as np
import pandas as pd
import re
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline

from cbb_load import XLSX, SHEET, load

BURN_IN = 5
TRAIN_FRAC = 0.60
N_PERM = 500
BARS = {-110: 0.5238, -105: 0.5122, -102: 0.5050}


def team_form():
    """Rolling pre-game form per team, using PRIOR games only (no leakage)."""
    d = pd.read_excel(XLSX, sheet_name=SHEET)
    d.columns = [re.sub(r"\s+", " ", str(c)).strip() for c in d.columns]
    d = d[d["BIGDATABALL DATASET"].str.contains("Regular Season", na=False)].copy()
    d["DATE"] = pd.to_datetime(d["DATE"], errors="coerce")
    for c in ("OEFF", "DEFF", "PACE", "PTS"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.sort_values(["TEAM", "DATE"])
    gb = d.groupby("TEAM")
    for c in ("OEFF", "DEFF", "PACE"):
        # shift(1) so the current game is excluded
        d[f"roll_{c}"] = gb[c].transform(lambda s: s.shift(1).expanding().mean())
    d["gp"] = gb.cumcount()
    d["rest"] = gb["DATE"].diff().dt.days
    return d[["GAME-ID", "TEAM", "VENUE", "roll_OEFF", "roll_DEFF",
              "roll_PACE", "gp", "rest"]]


def build():
    g = load().dropna(subset=["close_total", "close_spread", "total_pts"])
    f = team_form()
    h = f[f.VENUE == "Home"].drop(columns=["VENUE", "TEAM"])
    r = f[f.VENUE == "Road"].drop(columns=["VENUE", "TEAM"])
    g = g.merge(h, on="GAME-ID", suffixes=("", "_h")).merge(
        r, on="GAME-ID", suffixes=("_h", "_r"))

    g["oeff_sum"] = g.roll_OEFF_h + g.roll_OEFF_r
    g["deff_sum"] = g.roll_DEFF_h + g.roll_DEFF_r
    g["pace_sum"] = g.roll_PACE_h + g.roll_PACE_r
    g["oeff_diff"] = g.roll_OEFF_h - g.roll_OEFF_r
    g["deff_diff"] = g.roll_DEFF_h - g.roll_DEFF_r
    g["pace_diff"] = g.roll_PACE_h - g.roll_PACE_r
    g["rest_diff"] = g.rest_h - g.rest_r
    g["abs_spread"] = g.close_spread.abs()
    g["exp_total"] = g.pace_sum * (g.oeff_sum / 2) / 100   # crude pace*eff prior

    g["resid_total"] = g.total_pts - g.close_total
    g = g[(g.gp_h >= BURN_IN) & (g.gp_r >= BURN_IN)]
    feats = ["roll_OEFF_h", "roll_DEFF_h", "roll_PACE_h",
             "roll_OEFF_r", "roll_DEFF_r", "roll_PACE_r",
             "oeff_sum", "deff_sum", "pace_sum",
             "oeff_diff", "deff_diff", "pace_diff",
             "rest_h", "rest_r", "rest_diff", "gp_h", "gp_r",
             "close_total", "abs_spread", "exp_total"]
    g = g.dropna(subset=feats + ["total_pts", "margin_vs_line"])
    return g.sort_values("date"), feats


def run(g, feats, target, label, rng):
    y = g[target].values
    X = g[feats].values
    cut = int(TRAIN_FRAC * len(g))
    Xtr, Xte, ytr, yte = X[:cut], X[cut:], y[:cut], y[cut:]

    m = make_pipeline(StandardScaler(), Ridge(alpha=1.0)).fit(Xtr, ytr)
    pred = m.predict(Xte)

    ss_res = ((yte - pred) ** 2).sum()
    ss_tot = ((yte - ytr.mean()) ** 2).sum()
    r2 = 1 - ss_res / ss_tot
    rho = np.corrcoef(pred, yte)[0, 1]

    live = pred != 0
    win = (np.sign(pred[live]) == np.sign(yte[live])).mean()
    n = live.sum()
    se = np.sqrt(win * (1 - win) / n)

    # permutation null on the OOS win rate
    null = []
    for _ in range(N_PERM):
        ysh = ytr[rng.permutation(len(ytr))]
        ms = make_pipeline(StandardScaler(), Ridge(alpha=1.0)).fit(Xtr, ysh)
        ps = ms.predict(Xte)
        null.append((np.sign(ps) == np.sign(yte)).mean())
    null = np.array(null)

    print(f"\n--- {label}  (train {cut}, test {len(yte)}) ---")
    print(f"  OOS R2 on residual : {100*r2:+.3f}%   "
          f"(bar: 0.559% for -110, 0.147% for -105)")
    print(f"  OOS corr(pred,resid): {rho:+.4f}   (bar: 0.0748 for -110)")
    print(f"  OOS win rate        : {100*win:.2f}%  +/- {196*se:.2f}pp (95%)")
    for pr, be in BARS.items():
        print(f"      vs {pr} ({100*be:.2f}%): {100*(win-be):+.2f}pp  "
              f"t={(win-be)/se:+.2f}")
    print(f"  permutation null    : mean {100*null.mean():.2f}%, "
          f"95th pct {100*np.quantile(null,0.95):.2f}%, "
          f"observed at {100*(null<win).mean():.1f}th percentile")
    return r2, win


def main():
    rng = np.random.default_rng(11)
    g, feats = build()
    print("=" * 78)
    print("CBB MODELLING CANDIDACY — conditional predictability of the residual")
    print("=" * 78)
    print(f"games after burn-in and feature construction: {len(g)}")
    print(f"features: {len(feats)}   split: first {int(100*TRAIN_FRAC)}% by date")
    run(g, feats, "resid_total", "TOTALS  residual = total_pts - close_total", rng)
    run(g, feats, "margin_vs_line", "SIDES   residual = margin + close_spread", rng)


if __name__ == "__main__":
    main()
