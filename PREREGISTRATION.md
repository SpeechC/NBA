# Pre-registration: the 2024-25 holdout test

**Written 2026-08-11, before the 2024-25 odds data exists.** The point of writing
it now is that every decision below is fixed while the answer is unknown. If any
of it is changed after the data arrives, the test is no longer a test.

## What is being tested

Frozen model **spec A** (21 features), threshold **1.25**, exactly as committed in
`models_frozen.py` at `f71858f`. No refitting of the specification, no feature
changes, no threshold search, no estimator substitution.

## Data required

BigDataBall odds for the **2024-25 regular season** (~1,230 games), same schema as
`dfMaster_OT.csv`. Play-by-play for 2024-25 is already ingested and validated
(1,229 games, 69,576 stints, 100% lineup integrity) and is **not** used by these
models anyway.

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

Expected yield: ~250 bets at the historical 20% selection rate.

## The primary metric is CLV, not ROI

This is the most important line in the document, and it follows from arithmetic
rather than preference.

At ~250 bets:

| metric | standard error | what one season can resolve |
|---|---|---|
| **CLV** | **~0.20 pts** | a real signal of +1.84 would land in roughly [1.44, 2.24] — **decisive** |
| win rate | ~3.2 pp | 54% lands in roughly [47.8, 60.2] — **spans break-even, inconclusive** |

To separate a true 54% win rate from the 52.38% break-even at 80% power needs
roughly **5,900 bets** — about 24 seasons. **No single-season holdout can ever
establish the ROI.** Anyone who reports one as if it did is overclaiming.

CLV has an order of magnitude less variance and is therefore the only metric that
one season can actually settle.

## Success and failure, defined now

| outcome | CLV at \|pred\|>1.25 | verdict |
|---|---|---|
| **PASS** | ≥ +1.2 with 95% CI excluding zero | signal replicates; proceed to execution |
| **AMBIGUOUS** | +0.4 to +1.2, CI excluding zero | weaker than backtest but real; re-examine |
| **FAIL** | ≤ +0.4, or CI including zero | the backtested edge does not replicate |

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