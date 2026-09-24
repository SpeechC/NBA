# Are some matchups intrinsically harder to line? (2026-09-24)

`D_i = actual total_i − closing total_i`, 10,383 games, 2017-2025. Fitted on
2017-2021, read out of sample on 2022-2025. Every feature rebuilt point-in-time
from box scores with `shift(1).rolling(15, min_periods=5)` inside the season —
the `TEAM_*_STD_*` columns are season-to-date **means** (the suffix is not a
standard deviation) and their timing is undocumented, so none is used.
`DATASET_H` coalesced with `BIGDATABALL\nDATASET_H`.

## Q1 — Is there heteroskedasticity at all? No.

Breusch-Pagan on all 19 pregame features, train seasons: **LM = 26.31, 19 df,
p = 0.1217**, R² on D² = **0.00428**.

Strongest single features by variance ratio (top vs bottom quintile):

| feature | sd(D) Q1 | sd(D) Q5 | VarRatio | Levene p |
|---|---|---|---|---|
| pace_sum | 17.973 | 19.460 | 1.172 | 0.29 |
| off_def_r | 18.960 | 17.778 | 0.879 | 0.15 |
| \|spread\| | 18.845 | 17.531 | 0.865 | 0.12 |
| pace_gap | 17.477 | 18.275 | 1.093 | 0.26 |
| reb_mismatch | 17.778 | 18.422 | 1.074 | 0.44 |

No feature reaches Levene p < 0.12. Max VarRatio 1.17 against the 1.29 bar.

## Q2 — The fitted difficulty score, out of sample

| | corr(score, \|D\|) |
|---|---|
| in-sample (train) | **+0.6084** |
| **out-of-sample (test)** | **−0.0137** |

That gap is the whole result: the score is a pure overfit and transfers nothing.

**Raw difficulty score, test seasons 2022-2025**

| quintile | N | mean dev | SD(dev) | mean \|dev\| | P(\|d\|>15) | P(d>15) | P(d<−15) |
|---|---|---|---|---|---|---|---|
| Q1 easiest | 990 | −0.289 | 18.512 | 14.705 | .4202 | .2030 | .2172 |
| Q2 | 989 | +0.882 | 18.146 | 14.324 | .4014 | .2133 | .1881 |
| Q3 | 989 | −0.213 | 17.243 | 13.780 | .3802 | .1840 | .1962 |
| Q4 | 989 | +1.333 | 17.868 | 14.163 | .3812 | .2083 | .1729 |
| Q5 hardest | 990 | +0.719 | 17.806 | 14.070 | .3879 | .2010 | .1869 |

Q5 − Q1 = **−0.706** sd points. VarRatio 0.925. **Not monotone, and backwards.**

**Orthogonalised** against (total, spread, |spread|, total², |spread|²) — the
part of difficulty the market is not already pricing — Q5 − Q1 = −0.366,
VarRatio 0.960, still non-monotone. (total, spread) explain only 1.97% of the
score, so the orthogonalisation is not what killed it; there was nothing there.

Against the standard stated in advance — *"if Q1 is 17.5 and Q5 is 18.2 there is
probably nothing economically interesting"* — this does not even order correctly.

## The one real effect is the market's own variable

| closing total quintile | N | SD(dev) | mean \|dev\| | P(\|d\|>15) |
|---|---|---|---|---|
| Q1 | 1036 | 17.089 | 13.550 | .3649 |
| Q3 | 1044 | 18.164 | 14.353 | .4071 |
| Q5 | 965 | **19.319** | 15.119 | .4207 |

Q5 − Q1 = **+2.230** sd points, VarRatio **1.278** — bigger than anything the
matchup features produce, and it is driven by the single number the market
cannot fail to observe.

## Does Kalshi price it? Yes — in slope and in level.

Inverting all 1,310 pregame ladders of 2025-26 (`Φ⁻¹(1−p_mid)` on strike; median
fit RMSE **0.0214**, so the normal describes the ladder well):

| | σ slope per point of total |
|---|---|
| realised, sd(D) over 8 bins, n=10,383 | **+0.04187**, 95% CI [+0.01416, +0.07046] |
| **Kalshi implied σ vs implied μ**, n=1,310 | **+0.06222** — INSIDE the interval |

Level check: realised sd(D) for 2025-26 = **18.255**; Kalshi mean implied σ =
**18.214**, median 18.054. Agreement to **0.04 points**.

Kalshi's ladder rises 17.04 → 18.81 in σ across its own μ range, tracking the
realised 17.53 → 19.05. It prices the dispersion structure that exists, if
anything slightly over-scaling.

**Contrast worth carrying:** on the SIDES market the book *under*-scales σ with
the total, at +0.0144 against a realised +0.0352
(`CROSS_MARKET_SIGMA_SCAN.md` §8). On TOTALS, Kalshi scales correctly. The two
markets do not make the same mistake, and only the sides one even has a
mis-scaling — which separately failed to trade.

## Status

"These games are harder" is **not established** from matchup state — three
distinct operationalisations now agree (11 predefined archetypes in
`MATCHUP_HARDNESS.md`, the four in `CONDITIONAL_DISPERSION_GATE.md`, and the
fitted continuous score here). "Harder than the market realises" is
**refuted for the totals instrument**, in slope and level, on the venue we
actually trade.

Not closed, but the remaining room is narrow and specific:

1. **Within-game-state dispersion**, not pregame — the in-play regime is
   untouched and is where a dispersion error could survive.
2. **Injury-report dispersion**, named in `MATCHUP_HARDNESS.md` as untested and
   still untested — late scratches are the one pregame shock not in box scores.
3. **Cross-book disagreement on the total** as a difficulty proxy; we hold one
   book only, so this needs a second source.
4. The tails specifically: the σ agreement is a second-moment result. Kalshi's
   ladder is normal by construction (RMSE 0.0214) while the outcome is
   right-skewed by OT, which `NBA_TOTALS_SKEW_ERROR.md` already sized — and
   which failed on instrument availability, not on being wrong.

Scripts: `screen_matchup_heteroskedasticity.py`, `screen_kalshi_sigma_vs_total.py`.
