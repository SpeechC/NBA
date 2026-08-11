# Pre-registration: the 2024-25 and 2025-26 holdout test

**Written 2026-08-11, before the 2024-25 odds data exists.** The point of writing
it now is that every decision below is fixed while the answer is unknown. If any
of it is changed after the data arrives, the test is no longer a test.

## What is being tested

Frozen model **spec A** (21 features), threshold **1.25**, exactly as committed in
`models_frozen.py` at `f71858f`. No refitting of the specification, no feature
changes, no threshold search, no estimator substitution.

## Data required

BigDataBall odds for the **2024-25 and 2025-26 regular seasons** (~2,460 games),
same schema as `dfMaster_OT.csv`.

**Play-by-play is not needed for either season.** The frozen models turned out to
be odds-file-only -- every pbp-derived feature was tested and rejected -- so the
absence of 2025-26 pbp blocks nothing. That is an accidental benefit of the pbp
work returning null.

2025-26 is the more valuable of the two: it is the most recent season and
therefore tests whether the edge **still exists now**, not merely whether it
existed in 2019-2024. Markets sharpen over time; if this signal has decayed, the
latest season is where it shows.

**Run `accept_new_data.py` on the file before anything else.** It gates on nine
checks, the critical one being that overtime games are present. An OT-stripped
file already fooled this project once -- it looks entirely normal and silently
drags the over rate to 47.95%, manufacturing a fake under bias in every totals
result.

## Procedure, fixed in advance

1. Append 2024-25 odds to the existing panel. Do not re-tune anything.
2. Build features exactly as `symmetric_features.build()` does today.
3. Refit the ridge estimator walk-forward on all completed games, predicting
   2024-25 only. Training may use 2017-2024; it must never use a game that had
   not finished.
4. Bet `sign(pred)` where `|pred| > 1.25`, struck and graded at the **opening**
   total, pushes void.
5. Report every metric below. No subsetting, no alternative thresholds, no
   "excluding the first month".

Expected yield: ~250 bets per season, ~500 pooled, at the historical 20%
selection rate.

**Both seasons will be reported separately as well as pooled.** This is
pre-committed precisely so that a good season cannot be presented alone.

## The primary metric is CLV, not ROI

This is the most important line in the document, and it follows from arithmetic
rather than preference.

| n | CLV standard error | win-rate standard error |
|---|---|---|
| 250 (one season) | **0.202 pts** | 3.16 pp — CI [47.9, 60.3] |
| **500 (both pooled)** | **0.143 pts** | 2.24 pp — CI [49.7, 58.4] |
| 5,542 (needed for 80% power on ROI) | — | 0.67 pp |

A pooled CLV interval is roughly **±0.28 points**, which cleanly separates PASS
(≥ +1.2) from FAIL (≤ +0.4). The win-rate interval still spans break-even even
with both seasons.

To separate a true 54% win rate from the 52.38% break-even at 80% power needs
roughly **5,500 bets — about 22 seasons.** **No two-season holdout can establish
the ROI.** Anyone who reports one as if it did is overclaiming.

CLV has an order of magnitude less variance and is therefore the only metric that
one season can actually settle.

## Success and failure, defined now

| outcome | CLV at \|pred\|>1.25 | verdict |
|---|---|---|
| **PASS** | ≥ +1.2 with 95% CI excluding zero | signal replicates; proceed to execution |
| **AMBIGUOUS** | +0.4 to +1.2, CI excluding zero | weaker than backtest but real; re-examine |
| **FAIL** | ≤ +0.4, or CI including zero | the backtested edge does not replicate |

Applied to the **pooled** sample. In addition, a pre-committed consistency check:
if the two seasons disagree in sign, the verdict is **AMBIGUOUS regardless of the
pooled figure**. Two independent seasons agreeing is evidence that pooling alone
cannot provide; two disagreeing is a warning that pooling would conceal.

If 2025-26 is materially weaker than 2024-25, the working hypothesis is **edge
decay from market sharpening**, and the honest conclusion is that the strategy is
closing rather than that it never existed.

Backtest anchor at this threshold: **CLV +1.844, beat-close 66.6%, win 54.05%,
ROI +3.18%.**

Secondary (reported, not decisive): beat-close rate, win rate with binomial
interval, ROI with bootstrap interval, per-month breakdown.

## Pre-committed interpretations

* **ROI will be reported but is not the test.** If CLV passes and ROI is
  negative, the signal replicated and the season was unlucky — that is the
  expected outcome roughly 30% of the time even with a genuine edge.
* **A negative CLV is a genuine failure** and will be reported as such. There is
  no regime argument available: 2024-25 is a normal regular season, the same
  population the model was built on. This is exactly why it is a better holdout
  than the playoffs.
* **No threshold will be re-optimised on 2024-25.** If 1.25 fails but 1.5 works,
  that is noise, not a discovery.

## Why this is the right next step

The estimator choice has already been validated out of sample (ridge wins on
pre-2023 data alone). What has not been validated is whether the *edge* survives
in a season nobody has looked at, in the same regime.

The two holdouts already run disagree and both are confounded — the temporal one
by season selection and growing training size, the playoff one by a different
regime and a mis-specified feature set. 2024-25 has neither problem.

It is a data purchase, not a research project. Every piece of infrastructure is
built, frozen and committed.
EOF
echo written