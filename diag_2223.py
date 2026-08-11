"""Is 2022-23 an anomalous regime, or an ordinary bad draw?

The proposal is to train a season-specific model on 2022-23 and ensemble it.
That is only defensible if 2022-23 is genuinely DIFFERENT in some way visible
BEFORE the results are known. Three checks:

  1. Is its P&L outside what season-to-season luck produces at this bet count
     and win rate? Simulated under the null of a constant edge.
  2. Did the environment differ observably -- scoring, movement, over rate?
  3. Are A and D independent enough for an ensemble of them to add anything?
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
RNG = np.random.default_rng(0)

A = pd.read_csv("staking_bets_A.csv", parse_dates=["date"])
D = pd.read_csv("staking_bets_D.csv", parse_dates=["date"])

lvl = 0.75
a = A[A["pm"].abs() > lvl].copy()

print("=" * 96)
print("1. Is 2022-23's loss outside normal season variation?")
print("=" * 96)
live = a[~a["push"]]
p = live["won"].mean()
print(f"pooled win rate across all seasons: {100*p:.2f}%  (n={len(live):,})\n")

rows = []
for s, sub in live.groupby("season_lbl"):
    n = len(sub)
    if n < 50:
        continue
    # simulate this season's $won under a CONSTANT edge, using its own stakes
    stakes = sub["stake_$"].values
    sims = np.array([np.where(RNG.random(n) < p, stakes * (100 / 110), -stakes).sum()
                     for _ in range(20000)])
    actual = sub["$won"].sum()
    pct = 100 * (sims < actual).mean()
    rows.append({"season": s, "bets": n, "win %": round(100 * sub["won"].mean(), 2),
                 "$won": round(actual, 2), "sim mean $": round(sims.mean(), 2),
                 "sim sd $": round(sims.std(), 2),
                 "z": round((actual - sims.mean()) / sims.std(), 2),
                 "pctile": round(pct, 1)})
t = pd.DataFrame(rows)
print(t.to_string(index=False))
print("\nUnder a constant edge, one season in eight lands below the 12th percentile")
print("by construction. A z of about -1.5 is the 7th percentile -- unremarkable.")

print("\n" + "=" * 96)
print("2. Did the 2022-23 ENVIRONMENT differ observably?")
print("=" * 96)
env = A.groupby("season_lbl").apply(lambda x: pd.Series({
    "games": len(x),
    "mean open_total": x["open_total"].mean(),
    "mean actual_total": x["actual_total"].mean(),
    "over rate %": 100 * (x["actual_total"] > x["open_total"]).mean(),
    "mean |move|": x["move_total"].abs().mean(),
    "sd move": x["move_total"].std(),
    "mean |pred|": x["pm"].abs().mean(),
    "corr(pred,move)": np.corrcoef(x["pm"], x["move_total"])[0, 1],
}), include_groups=False)
print(env.round(3).to_string())

print("\n" + "=" * 96)
print("3. Are A and D independent enough to ensemble?")
print("=" * 96)
m = A[["game_id", "pm"]].merge(D[["game_id", "pm"]], on="game_id",
                               suffixes=("_A", "_D"))
print(f"corr(pred_A, pred_D) = {np.corrcoef(m['pm_A'], m['pm_D'])[0,1]:.4f}  "
      f"on {len(m):,} games")
agree = (np.sign(m["pm_A"]) == np.sign(m["pm_D"])).mean()
print(f"they call the same DIRECTION on {100*agree:.1f}% of games")
