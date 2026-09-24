# Matchup dispersion study — boxscores only (2026-09-24)

**Question.** Are some identifiable pregame matchups systematically harder for
the closing total to price? "Harder" = wider conditional distribution of
`D = actual total − closing total`. Not the sign of D.

**No Kalshi data, prices, mids, ladders or ladder-derived σ anywhere.** The
script reads one source: `dfMaster_OT_2017-2026.csv`.

Script: `matchup_dispersion_study.py`. Full log:
`matchup_dispersion_results.txt`.

## Part 0 — Audit

| check | result |
|---|---|
| raw rows | 10,383 |
| **`DATASET_H` coalesced with `BIGDATABALL\nDATASET_H`** | 2,624 → **10,383** (+7,759 recovered) |
| duplicate `GAME-ID` | **0** |
| home+away reconcile to `TOTAL_PTS` | 10,382 / 10,383 (99.99%), max mismatch 1.0 |
| closing total present | 100.00% |
| closing spread present | 100.00% |
| playoffs | **671 (6.5%)** |

**Two data facts worth recording.** First, the coalescing matters enormously —
without it, 75% of rows carry no season label and the playoff sample collapses
to a fraction of its true size. Second, **season 2019 is absent from the file
entirely**: the seasons present are 2017, 2018, 2020–2025 — eight, not nine.
Everything below is eight seasons.

Games per season 1,171–1,323; 2020 is the short COVID season.

## Baseline facts — and a correction to a number I have been quoting

`SD(D) = 18.0510`, mean `+0.3629`, median `0.0000`,
`P(|D|>15) = 0.3945`, `P(|D|>20) = 0.2576`.

Closing-total quintiles, **all eight seasons**:

| bucket | N | mean D | SD(D) | mean\|D\| | P(\|D\|>15) | P(\|D\|>20) |
|---|---|---|---|---|---|---|
| Q1 | 2137 | +0.006 | 17.618 | 14.058 | .3912 | .2522 |
| Q2 | 2016 | +0.109 | 17.438 | 13.946 | .3889 | .2574 |
| Q3 | 2152 | +1.119 | 18.316 | 14.293 | .3792 | .2458 |
| Q4 | 2063 | +0.412 | 18.391 | 14.615 | .4125 | .2695 |
| Q5 | 2015 | +0.137 | 18.460 | 14.524 | .4015 | .2640 |

**SD Q5/Q1 = 1.0478, and it is NOT monotone.**

> **CORRECTION.** `MATCHUP_HETEROSKEDASTICITY.md` reported this control as
> **17.09 → 19.32, VarRatio 1.278**. That was computed on the **test seasons
> only** and on the PIT-filtered subsample. On the full corrected dataset it is
> **17.618 → 18.460, ratio 1.0478**. The test-season figure was the most
> extreme slice available, and I should not have carried it forward as *the*
> effect size. The underlying relationship is real but **modest and
> non-monotone** — roughly 0.8 pts of SD across quintiles, or 1.5 pts across
> 8 finer bins (17.53 → 19.05, the basis of the +0.04187 slope used in the
> Kalshi work, which is unaffected).
>
> This makes the Kalshi identification verdict *stronger*, not weaker: a 2.3 pt
> identified band against an effect now measured at 0.8–1.5 pts.

The positive control does its job — the pipeline reproduces a total-dependent
effect — but its magnitude was overstated.

## Parts I–II — Point-in-time state and matchup interactions

77 PIT features per team: rolling 5/10/20-game means (`min_periods` 3/5/8) of
pace, possessions, offensive and defensive rating, points per possession,
3PA rate, 3P%, 3-point scoring share, FT rate, opponent-allowed 3PA/3P%/FT
rates, OREB and DREB rates, turnover and forced-turnover rates, foul and
fouls-drawn rates; rolling SDs of pace, own points, opponent points, game total,
offensive rating and 3P makes; a 5-vs-20 pace trend. **Every one built with
`shift(1)` inside the season.** The `STD` columns are season-to-date means and
are not used anywhere.

31 matchup features, each with a basketball reading: combined pace, pace clash,
pace volatility, combined scoring volatility, 3-point dependence, 3PA × opponent
3PA-allowed (both directions), offence × opposing defence, volatility × opposing
volatility, FT rate × opposing foul rate, OREB × opposing DREB, turnover ×
forced-turnover, pace × efficiency, rest/B2B/3-in-4, playoff.

Join audit: 10,383 → 10,383 rows, `GAME-ID` unique. 1,008 rows lost to PIT
warm-up → **9,375 modelled**. Train 2017–2021 (n=4,615), test 2022–2025
(n=4,760). No random split.

**Feature-timing audit** (3 random games, printed in full in the log): stored
`pace_m10` equals the mean of the 10 **prior** games exactly, and does **not**
equal the value that would obtain if the current game were included. Confirmed
on all three.

## Part III — Archetype screen, cutoffs frozen on TRAIN

| feature | SD Q1 | SD Q5 | ratio | Levene p |
|---|---|---|---|---|
| **pace_sum** | 17.416 | 19.081 | **1.0956** | 0.0071 |
| closing total | 16.253 | 18.535 | 1.1404 | 0.0161 |
| ft_exp | 17.429 | 18.163 | 1.0421 | 0.378 |
| score_vol | 17.786 | 17.939 | 1.0086 | 0.783 |
| tp_dep | 18.257 | 18.003 | 0.9861 | 0.954 |
| eff_mismatch | 18.293 | 17.579 | 0.9609 | 0.401 |
| tov_exp | 18.713 | 17.512 | 0.9358 | 0.059 |
| \|closing spread\| | 18.285 | 18.154 | 0.9928 | 0.765 |

Combined pace is the only matchup feature with a credible signal, at
**1.0956** — below the 1.15 bar, and on one of twelve simultaneous screens.

## Parts IV–V — Conditional-scale model, out of sample

Target `|D|`, season blocks, two model families only.

| model | in-sample corr(score, \|D\|) | **out-of-sample** |
|---|---|---|
| Ridge | +0.0649 | **+0.0158** |
| GBM | +0.4904 | **−0.0075** |

The GBM's in-sample 0.49 against an OOS −0.008 is the whole story.

**Decisive OOS table (GBM):**

| difficulty | N | mean D | SD(D) | mean\|D\| | P(\|D\|>15) | P(\|D\|>20) | P(D>15) | P(D<−15) |
|---|---|---|---|---|---|---|---|---|
| Q1 easiest | 952 | −0.447 | 18.158 | 14.606 | .4181 | .2700 | .1954 | .2227 |
| Q2 | 952 | +0.000 | 17.437 | 13.975 | .3950 | .2595 | .1985 | .1964 |
| Q3 | 952 | +1.493 | 18.373 | 14.308 | .3803 | .2416 | .2080 | .1723 |
| Q4 | 952 | +1.007 | 17.410 | 13.808 | .3908 | .2447 | .2132 | .1775 |
| Q5 hardest | 952 | +0.404 | 18.488 | 14.565 | .3960 | .2710 | .2006 | .1954 |

**SD Q5/Q1 = 1.0182**, `P(|D|>15)` Q5−Q1 = **−0.0221** (wrong sign), **not
monotone**. Ridge: 1.0645, also not monotone.

## Part VI — Incremental to closing total and spread

**A. Residualised** on total, |spread|, season (which explain only 3.4% of the
score, so this is not what kills it): **SD Q5/Q1 = 1.0031**, P(|D|>15) Q5−Q1
= −0.0105, not monotone.

**B. Conditional benchmark:**

| model | OOS corr | MAE | RMSE |
|---|---|---|---|
| total + \|spread\| only | **+0.0312** | 8.7155 | 11.0056 |
| total + \|spread\| + matchup | **−0.0046** | 8.7109 | 11.1206 |

**Adding matchup information makes out-of-sample prediction worse.** The
positive control passes: total+spread alone gives SD Q5/Q1 = 1.0564, so the
pipeline can recover the known effect.

## Part VII — Replication

| test season | n | SD Q5/Q1 | mean\|D\| Q5−Q1 | P(\|D\|>15) Q5−Q1 |
|---|---|---|---|---|
| 2022 | 1193 | 0.9806 | −0.441 | −0.0418 |
| 2023 | 1188 | 1.1406 | +1.492 | +0.0084 |
| 2024 | 1188 | 1.0520 | +0.485 | −0.0042 |
| 2025 | 1191 | 1.0034 | −0.182 | +0.0018 |

One season above 1.1, one below 1.0, signs inconsistent. No replication.

## Part VIII — Inference

Season-block bootstrap: SD Q5/Q1 = 1.0182, **95% CI [0.9734, 1.1148]** — covers 1.

Permutation null (target shuffled within train season, 400 draws, full model
refit each time): median **0.9980**, 95th **1.0614**, max **1.1144**.
Observed 1.0182 → **p = 0.3250**.

## Part IX — Failure controls

- **Shuffle control:** the permutation above. Real target does **not** beat it.
- **Leakage control:** shifting every rolling feature back one extra game gives
  OOS corr −0.0094 vs +0.0138 at `shift(1)`. No suspicious improvement.
- **Feature-timing audit:** passed on all sampled games (above).
- **Total-only positive control:** passes (1.0564).

## Decision

| criterion | result |
|---|---|
| 1. orders realised dispersion OOS (monotone) | **FAIL** |
| 2. SD Q5/Q1 ≥ 1.15 | **FAIL** (1.0182) |
| 3. survives conditioning on total and spread | **FAIL** (1.0031) |
| 4. replicates across test seasons | **FAIL** |
| 5. beats shuffled/permutation null | **FAIL** (p = 0.325) |

**Conclusion, narrowly:** the available point-in-time team boxscore and matchup
information does not identify persistent differences in closing-total forecast
precision beyond the dispersion associated with the market total and spread.

This does **not** mean every NBA game has identical uncertainty. Combined pace
reached 1.0956 with Levene p = 0.0071 on a frozen-cutoff screen, which is the
one place a real effect might sit — but it is below the economic bar, it is one
of twelve simultaneous screens, and it does not survive into the fitted model
out of sample.

**Second-stage Kalshi question is not opened.** The gate required a robust
historical matchup-dispersion effect first, and there isn't one.

---

**CLOSED 2026-09-24.** The boxscore conditional-difficulty hypothesis is closed; see the closure record at the end of `PROJECT_CLOSED.md`. The market total identifies a real variance environment, but point-in-time boxscore/matchup information does not identify additional games whose totals, spreads or moneylines are systematically harder to forecast. Standard closing moneylines already accommodate the total-dependent margin variance despite simple normal-link models failing to do so.
