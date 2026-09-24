# Side forecast difficulty — are some spreads/moneylines harder? (2026-09-24)

The reverse of `MATCHUP_DISPERSION_STUDY.md`. There the closing total was the
**forecast being graded**; here it is an **explanatory variable**, and the
graded forecasts are the side markets.

**No Kalshi data anywhere.** Stage 5 is gated and was not run.

Two dependent variables:

- **Spread** `D_spr = (F_H − F_R) + CLOSING SPREAD_H` — actual home margin minus
  the spread-implied margin.
- **Moneyline** — de-vig the closing pair to `p = P(home win)`, then grade with
  **excess Brier** `= (Y−p)² − p(1−p)`. This has mean zero at every `p` under
  perfect calibration, so it isolates *"harder than the price says"* from
  *"closer to a coin flip."* A raw Brier would merely rediscover that `p ≈ 0.5`
  is uncertain.

Audit: 10,383 rows, 0 duplicate `GAME-ID`, closing spread and moneyline pair
present on **100%**, 0 ties. `DATASET_H` coalesced. 64 PIT features per team
(rolling 5/10/20, `shift(1)` within season) → 21 matchup interactions.
Train 2017–2021 (n=4,801), test 2022–2025 (n=4,947).

Baseline: `D_spr` mean −0.0489, **sd 13.5950**. Moneyline Brier 0.20597,
log loss 0.59791, excess Brier **−0.00011**.

## 1. Spread positive control — PASSES, weakly

| closing-total quintile | N | mean | SD | mean\|·\| | P(\|·\|>15) |
|---|---|---|---|---|---|
| Q1 | 2137 | −0.082 | 13.428 | 10.349 | .2344 |
| Q2 | 2016 | −0.135 | 13.170 | 10.175 | .2376 |
| Q3 | 2152 | −0.187 | 13.225 | 10.327 | .2333 |
| Q4 | 2063 | +0.234 | 13.510 | 10.474 | .2409 |
| Q5 | 2015 | −0.069 | **14.635** | 10.773 | .2591 |

**SD Q5/Q1 = 1.0899**, not monotone. 8-bin slope **+0.03696** per point of
total, against **+0.04187** for the totals market. Margin dispersion does rise
with the posted total, at essentially the same rate — consistent with a
mechanical possession-count channel rather than anything market-specific.

By |closing spread| instead: ratio 1.0337, not monotone (U-shaped — widest at
both pick'em and large spreads).

## 2. Moneyline positive control — FAILS

| total quintile | N | mean p | win rate | bias | Brier | excess Brier |
|---|---|---|---|---|---|---|
| Q1 | 2137 | .5780 | .5793 | +0.0013 | .21219 | +0.00224 |
| Q2 | 2016 | .5652 | .5600 | −0.0052 | .20157 | −0.00486 |
| Q3 | 2152 | .5591 | .5488 | −0.0103 | .20484 | −0.00058 |
| Q4 | 2063 | .5588 | .5768 | +0.0180 | .20326 | +0.00005 |
| Q5 | 2015 | .5537 | .5489 | −0.0049 | .20777 | +0.00250 |

Excess Brier Q5−Q1 = **+0.00026**. Formal test,
`logit(Y) ~ logit(p) + total/10`:

- coefficient on `logit(p)` = **+1.0042** (1.0 is perfect calibration)
- coefficient on total = **−0.00587**, LR χ² = 0.081, **p = 0.7765**

**The closing moneyline is essentially perfectly calibrated, and its calibration
does not depend on the total.** There is nothing here for matchup variables to
explain.

*This resolves an apparent tension with `CROSS_MARKET_SIGMA_SCAN.md` §8, where
moneyline-implied σ scaled with the total at +0.0144 against a realised +0.0352.
That mismatch is a property of the **normal link function**, not of calibration:
measured directly against outcomes, there is no total-dependent error. Which is
why backing dogs in high-total games returned −1.74% when we traded it.*

## 3–4. Do matchup variables add beyond spread + total? — FAILS

Target `|D_spr|`:

| feature set | OOS corr | MAE |
|---|---|---|
| market only (total, \|spread\|, spread) | −0.0063 | 6.7388 |
| matchup only | +0.0150 | 6.7698 |
| market + matchup | +0.0136 | 6.7556 |

In-sample corr **+0.4091** vs out-of-sample **+0.0150**.

**Decisive OOS table — spread difficulty score:**

| difficulty | N | mean | SD | mean\|·\| | P(\|·\|>10) | P(\|·\|>15) |
|---|---|---|---|---|---|---|
| Q1 easiest | 990 | −0.116 | 14.953 | 10.566 | .4253 | .2475 |
| Q2 | 989 | +0.419 | 13.468 | 10.550 | .4348 | .2477 |
| Q3 | 989 | +0.017 | 14.236 | 10.915 | .4429 | .2669 |
| Q4 | 989 | −0.075 | 14.199 | 10.526 | .4146 | .2437 |
| Q5 hardest | 990 | +0.320 | 13.573 | 10.700 | .4404 | .2505 |

**SD Q5/Q1 = 0.9077 — backwards**, not monotone.

Residualised on total, |spread|, season: **1.1199**, still not monotone. That is
higher than the raw figure, which is a warning sign rather than a result — the
permutation null for this design has a **95th percentile of 1.1459**, so 1.1199
is *inside* the null and the nominal 1.15 bar is barely above what chance
produces here.

## 4b. Moneyline — can matchup state predict excess Brier? — FAILS

| feature set | OOS corr with excess Brier |
|---|---|
| market only | +0.0099 |
| matchup only | **−0.0035** |
| market + matchup | −0.0006 |

Excess Brier Q5−Q1 = **−0.00895** — wrong sign.

## Inference

- Season-block bootstrap: SD Q5/Q1 = 0.9077, 95% CI **[0.8394, 1.0810]**.
- Permutation null (target shuffled within train season, 300 refits): median
  1.0224, 95th 1.1459, max 1.2581. Observed 0.9077 → **p = 0.9433**.
- Per-season: 1.1743 / 0.8089 / 0.9530 / 0.9008. No replication.

## Decision

| stage | result |
|---|---|
| 1. spread positive control | **PASS** (1.0899, 8-bin slope +0.03696) |
| 2. moneyline positive control | **FAIL** (calib. slope 1.0042, total p = 0.7765) |
| 3. orders dispersion OOS, monotone | **FAIL** |
| 4. SD Q5/Q1 ≥ 1.15 | **FAIL** (0.9077) |
| 5. survives conditioning | **FAIL** (1.1199, inside the null) |
| 6. beats permutation null | **FAIL** (p = 0.9433) |

**Stage 5 (Kalshi) is gated on 3–6 and was not run.**

### What this establishes

The two side markets fail in **different places**, which is the informative part.

**Moneyline:** fails at the positive control. It is calibrated to a slope of
1.0042 and shows no total-dependent error at all. There is no difficulty
structure to find, so the question closes before matchup variables enter.

**Spread:** the positive control passes — margin dispersion genuinely rises with
the posted total, at +0.037 per point, nearly identical to the +0.042 the totals
market shows. But point-in-time matchup state cannot locate *which* games,
exactly as in the totals study.

**Conclusion, narrowly:** the available point-in-time team boxscore and matchup
information does not identify persistent differences in spread or moneyline
forecast precision beyond the dispersion associated with the market's own
total and spread. This does not mean every game carries identical side
uncertainty.

That is now **five** operationalisations landing in the same place — 11
predefined archetypes, 4 dispersion gates, a fitted totals score, the full
totals protocol, and this side protocol. The common thread across all of them
is that dispersion tracks the **posted total** and nothing else that box scores
can see.

Scripts: `side_forecast_difficulty_study.py`, log `side_forecast_results.txt`.
