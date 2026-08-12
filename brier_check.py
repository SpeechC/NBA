"""Brier scores on our NBA moneylines — what the technique is and isn't worth.

The Kaggle notebook's method, applied to our data, plus the two things it leaves
out that decide whether the metric is useful.

  1. Devig by proportional normalisation:  p = (1/o_win) / (1/o_win + 1/o_lose)
  2. Brier score (the doubled two-outcome form the notebook uses)
  3. THE BENCHMARK. The notebook compares Brier against 0.5 -- what you would get
     from coin-flip forecasts. That is the wrong null. The right one is the
     climatological base rate: always forecast the league-average home win rate.
     Skill against THAT is what says whether the odds carry information.
  4. Murphy decomposition: Brier = Uncertainty - Resolution + Reliability.
     Reliability is miscalibration (potentially exploitable); Resolution is
     discrimination (how much signal exists at all).
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

from prepare_data import CSV, season_label


def american_to_prob(ml):
    ml = pd.to_numeric(ml, errors="coerce")
    return np.where(ml < 0, -ml / (-ml + 100), 100 / (ml + 100))


def murphy(p, o, bins=10):
    """Brier = Uncertainty - Resolution + Reliability (single-outcome form)."""
    obar = o.mean()
    unc = obar * (1 - obar)
    idx = np.clip((p * bins).astype(int), 0, bins - 1)
    rel = res = 0.0
    for k in range(bins):
        m = idx == k
        if not m.any():
            continue
        nk, pk, ok = m.sum(), p[m].mean(), o[m].mean()
        rel += nk * (pk - ok) ** 2
        res += nk * (ok - obar) ** 2
    return unc, res / len(p), rel / len(p)


def main():
    raw = pd.read_csv(CSV, low_memory=False)
    raw["season"] = season_label(raw).astype(str)
    d = raw[raw["season"].str.contains("Regular Season", na=False)].copy()
    d["ph_raw"] = american_to_prob(d["MONEYLINE_H"])
    d["pa_raw"] = american_to_prob(d["MONEYLINE_R"])
    d = d.dropna(subset=["ph_raw", "pa_raw", "PTS_H", "PTS_R"])
    d = d[(d["ph_raw"] > 0) & (d["pa_raw"] > 0)]
    d["overround"] = d["ph_raw"] + d["pa_raw"]
    d["p"] = d["ph_raw"] / d["overround"]           # proportional devig
    d["o"] = (d["PTS_H"] > d["PTS_R"]).astype(float)
    p, o = d["p"].values, d["o"].values

    print(f"n = {len(d):,} games")
    print(f"mean overround (vig) = {d['overround'].mean():.4f}  "
          f"-> hold {100*(d['overround'].mean()-1)/d['overround'].mean():.2f}%")
    print(f"home win rate = {o.mean():.4f}   mean devigged p(home) = {p.mean():.4f}")

    brier1 = np.mean((p - o) ** 2)                  # standard form
    print(f"\nBrier (standard)  = {brier1:.4f}")
    print(f"Brier (notebook's doubled form) = {2*brier1:.4f}")

    print("\n--- benchmarks: what to compare against ---")
    coin = np.mean((0.5 - o) ** 2)
    base = np.mean((o.mean() - o) ** 2)
    print(f"  coin flip p=0.5           {coin:.4f}   (the notebook's null)")
    print(f"  base rate p={o.mean():.3f}        {base:.4f}   (the CORRECT null)")
    print(f"  market                    {brier1:.4f}")
    print(f"\n  skill vs coin flip  = {100*(1-brier1/coin):5.2f}%   <- flattering")
    print(f"  skill vs base rate  = {100*(1-brier1/base):5.2f}%   <- honest")

    unc, res, rel = murphy(p, o)
    print("\n--- Murphy decomposition (Brier = Unc - Res + Rel) ---")
    print(f"  Uncertainty  {unc:.4f}   irreducible, a property of the sport")
    print(f"  Resolution   {res:.4f}   how much the odds discriminate (higher better)")
    print(f"  Reliability  {rel:.4f}   miscalibration (lower better; 0 = perfect)")
    print(f"  check: {unc:.4f} - {res:.4f} + {rel:.4f} = {unc-res+rel:.4f}"
          f"  vs Brier {brier1:.4f}")

    print("\n--- calibration table: is there exploitable miscalibration? ---")
    d["bin"] = pd.cut(d["p"], np.arange(0, 1.01, 0.1))
    t = d.groupby("bin", observed=True).apply(lambda x: pd.Series({
        "n": len(x), "mean p": round(x["p"].mean(), 4),
        "actual": round(x["o"].mean(), 4),
        "diff pp": round(100 * (x["o"].mean() - x["p"].mean()), 2),
    }), include_groups=False)
    se = np.sqrt(t["actual"] * (1 - t["actual"]) / t["n"]) * 100
    t["±1.96se"] = (1.96 * se).round(2)
    print(t.to_string())

    print("\n--- what the notebook's 'accuracy' metric actually measures ---")
    acc = ((p >= .5) == (o == 1)).mean()
    fav = np.maximum(o.mean(), 1 - o.mean())
    print(f"  odds 'correct' at the 50% threshold: {100*acc:.2f}%")
    print(f"  always picking the home team:        {100*fav:.2f}%")
    print("  The gap between these two is the only part that is forecast skill.")


if __name__ == "__main__":
    main()
