# Out-of-sample validation from data already in the database

Live paper-trading is not the only route to out-of-sample evidence. Two holdouts
existed in the file and neither had been used. They were both run. **They
disagree**, and that disagreement is the finding.

## What leaked, and what did not

The walk-forward predictions were always honest -- each used only prior games.
What leaked was **selection**: ridge, the feature spec and the threshold were all
chosen after seeing all six seasons. So the question is not "does the model work
out of sample" but "would this PROCEDURE, run honestly at the time, have produced
a model that worked afterwards?"

## Test 1 — was the estimator choice a full-sample artefact? **No.**

Re-running the estimator comparison using **only games before 2023-04-10**:

| estimator | n | corr | CLV |
|---|---|---|---|
| **Ridge** | 2,932 | **0.271** | **0.737** |
| RandomForest | 2,932 | 0.233 | 0.689 |
| XGBoost | 2,932 | 0.231 | 0.636 |

Same ordering as the full sample. Ridge would have been chosen in April 2023
without seeing anything after. **This is a genuine validation** -- the estimator
decision was not hindsight.

## Test 2 — temporal holdout (2023-24)

| sample | n | CLV | beat close | win % | 95% CI | ROI % | ROI 95% CI | P(ROI>0) |
|---|---|---|---|---|---|---|---|---|
| development (< 2023-04-10) | 592 | 1.695 | 66.0% | 51.35 | [47.3, 55.4] | −1.97 | [−9.7, +5.8] | 30% |
| **HELD OUT (≥ 2023-04-10)** | **211** | 2.263 | 68.2% | **61.61** | [54.9, 68.0] | **+17.62** | [+5.0, +30.3] | **99.6%** |

Superficially spectacular. **It is not independent evidence**, for three reasons:

1. **n = 211 is one season**, and season ROI has ranged −5.85% to +6.65%.
2. **That season was already known to be the best one.** The cut happens to place
   2022-23 (the worst season) in development and 2023-24 (the best) in the
   holdout.
3. **Training set size grows over time.** The walk-forward model has ~500 games
   of history early and ~4,000 by 2023-24, so later-is-better is expected and
   is not evidence about generalisation.

## Test 3 — playoffs and play-in: 526 genuinely untouched games

Every model filtered to "Regular Season|In-Season", so these were never used for
fitting, feature selection, estimator choice or thresholds. Lags were carried
from the regular season into the playoffs (a team's first playoff game uses its
last four regular-season games), and the model was refit only on completed
regular-season games.

| sample | n | CLV | beat close | win % | 95% CI | ROI % | ROI 95% CI | P(ROI>0) |
|---|---|---|---|---|---|---|---|---|
| **playoffs / play-in** | **91** | **+0.275** | **46.2%** | **43.96** | [34.1, 54.2] | **−16.08** | [−35.0, +2.8] | **5.9%** |

Negative. But confounded in the other direction:

* **Different regime.** Playoff line movement has SD 2.46 vs 3.10 in the regular
  season; mean total 216.9 vs 222.6. The signal itself is weaker there --
  CLV +0.275 against +1.844.
* **n = 91**, interval [−35%, +3%]. It excludes almost nothing.
* **The frozen spec was approximated.** `dis_open` requires the upstream score
  model, which is not built for playoffs; the structural implied-total residual
  was substituted. So this is not exactly model A.

## What the two together actually say

Nothing conclusive — and that is worth more than either alone.

Run only the temporal test and the honest report would have been "+17.6% ROI out
of sample, 99.6% probability positive". Run only the playoffs and it would have
been "−16.1%, the edge does not survive". Both would have been overclaims from
~100-200 bets.

To distinguish a true 54% from the 52.38% break-even at reasonable power needs
roughly **1,400 settled bets**. The holdouts supply 211 and 91.

## What would settle it

**2024-25 odds.** The play-by-play for that season is already ingested and
validated (1,229 games); only the BigDataBall odds file is missing. That would
provide a genuine unseen regular season -- same regime, right sample size,
roughly 250 bets at the operating threshold -- with every piece of infrastructure
already built and frozen.

That is a data purchase, not a research project, and it is the highest-value next
step by a wide margin.
