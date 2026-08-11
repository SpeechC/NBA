# Fat tails and variance modelling: both closed

Two related hypotheses about the *shape* of the totals distribution, rather than
its centre. Both tested; neither survives.

## 1. Are totals fat-tailed? No — that is overtime, and it is one-sided

| residual | n | skew | excess kurtosis | JB p |
|---|---|---|---|---|
| full total (incl OT) − close | 7,226 | +0.256 | **+0.526** | 0.0000 |
| regulation total − close | 7,226 | +0.071 | **+0.047** | 0.034 |
| non-OT games only | 6,846 | +0.070 | **+0.019** | 0.056 |

Strip overtime and excess kurtosis collapses from +0.53 to +0.02; on non-OT games
normality cannot be rejected. **Regulation basketball scores essentially normally
around the closing line.**

The tails are also asymmetric, not symmetric as the hypothesis assumed:

| z | over ratio vs normal | under ratio vs normal |
|---|---|---|
| 2.0 | 1.22 | **0.79** |
| 2.5 | 1.61 | **0.69** |
| 3.0 | 2.97 | **0.62** |

The right tail is fat; the **left tail is thin**. Mechanically sensible — overtime
only adds points, and there is a floor on how badly two NBA teams shoot.

And in the range anyone could bet (±5 to ±25 points, i.e. z ≈ 0.3–1.4), *both*
tails run slightly thin: empirical frequency is 0.1–1.2 percentage points **below**
normal at every distance. A book pricing an alternate ladder off a normal would be
overpricing the tails, so betting extremes loses before vig. The fat right tail
only appears beyond z ≈ 2.5 — 45+ points from the line, where no market exists.

## 2. Is game-level variance predictable? No

If some games were reliably higher-variance, and books priced their alternate
ladder off one sigma, extremes would be mispriced in a knowable direction.

Walk-forward model of |residual| on lagged team features (10-game windows):

| | |
|---|---|
| RMSE, constant (expanding mean) | 11.218 |
| RMSE, model | 11.310 |
| **improvement** | **−0.82% (worse than a constant)** |
| corr(predicted, realised) | **−0.019** |

The model produces confident-looking predictions — sigma from 16.0 to 20.2 across
quintiles — with no relationship to outcomes. Realised SD by predicted-sigma
quintile: 17.94, 18.81, 18.61, 17.45, 17.45. It goes *down*. That is the signature
of fitting noise.

### The individual mechanisms, tested directly

| mechanism | corr with \|residual\| | t |
|---|---|---|
| combined 3PA rate | +0.0135 | 1.07 |
| combined pace | +0.0096 | 0.75 |
| combined team scoring SD | −0.0040 | −0.32 |
| combined SD of game totals | +0.0047 | 0.37 |
| closing total level | +0.0136 | 1.08 |

Not one is significant. The three-point mechanism is the theoretically strongest
candidate — a 3PA-heavy game *should* have higher scoring variance per possession —
and it produces a correlation of 0.014. Quintiles of 3PA rate give realised SDs of
17.61, 18.49, 17.85, 18.21, 18.11: non-monotone noise.

Pace shows the only hint of structure — realised SD rises 17.68 → 18.64 across
quintiles (+5.4%), consistent with the mild heteroskedasticity measured in the
tails work (+0.016 sigma per point of closing total). But the continuous test gives
t = 0.75, and a 5% difference in sigma is worth roughly 2 percentage points on a
20-point alternate total — real in principle, undetectable in practice.

## Data note

The file's `TEAM_PACE_STD_H`, `TEAM_PTS_STD_H`, `TEAM_OEFF_STD_H` columns are
**not standard deviations** despite the naming: they average 98.6, 112.5 and 113.5
respectively — those are rolling *levels*. There are no variance columns in the
source data.

## What this closes

**Do not buy alternate-total or derivative price history for a variance strategy.**
The premise fails at step one: variance is not predictable, so there is nothing to
exploit even if books do price off a single sigma.

Worth noting what it *confirms*: modelling game totals as normal around a good
central estimate is safe. That means the CLV → win-rate conversion arithmetic used
throughout this project (which assumed exactly that) was sound rather than lucky.

It also re-confirms why the overtime-stripped `dfMaster.csv` was so dangerous — it
removed the entire fat side of the distribution.
