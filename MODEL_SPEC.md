# Specification: totals line-movement model (ridge)

The model behind the economics table. Everything below is what the code does, not
a description of intent.

## Target

    move_total = closing_total − opening_total          SD 3.199, mean −0.077

It predicts **where the line goes**, not what the teams score. The bet is then a
directional wager on the total at the opening number.

## Sample

| | |
|---|---|
| games | 5,128 (4,572 graded after pushes at the loosest threshold) |
| span | 2019-01-01 → 2024-04-14 |
| seasons | 2018-19, 2020-21, 2021-22, 2022-23, 2023-24 (+ 2023 IST) |

The start date is set by upstream burn-in, not by choice: the score model that
produces `dis_open` needs 1,500 team-games, then its calibration needs 300 games.
2019-20 and 2024-25 are absent because the odds file has no lines for them.

## Features (21)

**Market state (2)**
| feature | meaning |
|---|---|
| `open_total` | the opening total itself |
| `dis_open` | `calibrated_model_total − open_total` — our score model's disagreement with the opener |

`dis_open` is a *derived* feature with its own upstream pipeline: an XGBoost model
predicts each team's score from lagged box-score, pace/efficiency and rest/travel
features; the two are summed; the sum is affinely calibrated to actual totals on
an expanding window. All of it walk-forward.

**Team form (19)** — lagged 4-game means, all from the HOME team's row:
`f_2PA · f_2P% · f_3PA · f_3P% · f_FTA · f_FT% · f_ORB · f_DRB · f_AST · f_STL ·
f_BLK · f_TOV · f_PF · f_PACE · f_OEFF · f_DEFF` (home team, 16)
plus `f_PACE_opp · f_OEFF_opp · f_DEFF_opp` (away team, 3)

⚠ **This is asymmetric and it is a genuine weakness.** The home team contributes
all 16 variables; the away team contributes only pace and the two efficiency
ratings. There is no principled reason for that — it is an artefact of how the
panel was joined — and given that `f_PACE_opp` turns out to be the single largest
coefficient, the missing away-team variables are the most obvious place to look
for improvement.

## Estimator

    StandardScaler → RidgeCV(alphas = logspace(-2, 3, 20))

Alpha chosen by RidgeCV's internal leave-one-out at every refit.
**Median selected alpha 26.4** (range 7.9–297.6) — substantial shrinkage, which is
why ridge beat all seven tree families on this task.

## Walk-forward protocol

- expanding window, refit **every 7 days**, **266 refits**
- minimum 500 games before the first prediction (first: 2019-03-17)
- every fit uses only games that finished before the cut date
- `dis_open` and its calibration are independently walk-forward, so no stage sees
  the future

## Betting rule

- predict `move_total` for each game
- bet **over** if prediction > 0, **under** if prediction < 0
- stake at the **opening** total
- graded against the **opening** total (not the close); pushes excluded
- thresholds filter on |prediction|

## What the fitted model actually weights

Standardised coefficients, averaged over 265 refits:

| feature | coef | sd across refits |
|---|---|---|
| `f_PACE_opp` | **+0.623** | 0.218 |
| `open_total` | **−0.602** | 0.318 |
| `f_PACE` | **+0.426** | 0.248 |
| `f_DEFF_opp` | +0.241 | 0.057 |
| `f_OEFF` | +0.237 | 0.239 |
| `f_3P%` | −0.204 | 0.135 |
| `f_2P%` | −0.171 | 0.160 |
| `f_DEFF` | +0.168 | 0.125 |
| `f_OEFF_opp` | +0.156 | 0.203 |
| `f_AST` | +0.130 | 0.019 |
| … | | |
| `dis_open` | +0.062 | 0.062 |

Three things stand out.

**Pace dominates.** Opponent pace and own pace are the largest team-form terms.
The model is mostly saying: *fast teams draw over money the opener has not fully
priced.*

**The opening total enters negatively (−0.602)** — line-level mean reversion.
High openers drift down, low openers drift up.

**`dis_open` is nearly irrelevant (+0.062)**, ranking 15th of 21. That is the
sharpest finding in the whole specification: the elaborate score-model pipeline
feeding this feature contributes almost nothing. The signal is pace plus mean
reversion, not our forecast of the game.

Team-form features carry 2.887 of total |coefficient| against 0.665 for the two
market features — but that is spread across 19 correlated variables, and the two
pace terms alone account for over a third of it.

## Honest caveats

- ~20 model variants and 5 thresholds have been evaluated on this one sample.
- Every ROI confidence interval spans zero except `|pred|>2`, which rests on
  n=134 and sits in the range this project's own guidance calls a probable bug.
- The by-season breakdown at `|pred|>1` is +1.67, +0.83, −5.85, +6.65 — three of
  four positive, one clearly negative.
- Nothing here has been tested on data that was not used to develop it.
