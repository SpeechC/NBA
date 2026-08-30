# Calibration vs accuracy — audit of the two frozen signals, 2026-08-30

Prompted by Walsh & Joshi (`papers/ssrn_4705918.pdf`): select models on
**calibration**, not accuracy, and **Kelly only works on a calibrated model**.

**DESCRIPTIVE. On data already used.** This can only *downgrade* confidence in
signal magnitude. No new signal, threshold or strategy comes out of it, and
none is authorised by it.

## First, the thing that makes their advice only half-applicable here

**This program has no probabilistic forecaster.** `MOVE_COMBINED` emits `m`, a
predicted movement in *points*. `CrewShock` emits a continuous propensity and a
frozen threshold. Neither outputs a probability, so "select the model with the
better Brier score" has nothing to act on.

What *does* transfer is the Kelly half. Our signals' **magnitudes** are used as
if they were edges. So the live question is:

> Does a bucket whose points-of-edge implies 54% actually win 54%?

If yes, sizing by edge is defensible. If the curve flattens or reverses,
**only the sign is informative** and Kelly would put the most capital in the
least reliable cells. Implied probabilities use the **exact empirical CDF**
from `DISTRIBUTION_AUDIT`, not the Gaussian.

## MOVE_COMBINED — calibrated in a BAND, broken at both ends

| \|m\| bucket | n | mean edge | implied | actual | gap |
|---|---|---|---|---|---|
| 0.0–0.5 | 1,915 | 0.242 | 50.25% | 50.08% | −0.17pp |
| 0.5–1.0 | 1,443 | 0.732 | 52.11% | 49.55% | **−2.56pp** |
| **1.0–1.5** | 973 | 1.225 | 52.37% | 52.62% | **+0.26pp** |
| **1.5–2.0** | 470 | 1.723 | 54.34% | 54.68% | **+0.34pp** |
| **2.0–2.5** | 206 | 2.192 | 54.67% | 54.85% | **+0.18pp** |
| 2.5–3.0 | 86 | 2.696 | 56.42% | 51.16% | **−5.25pp** |

Monotonic on only **3 of 5** steps; `corr(edge, actual) = +0.548`.

**The frozen decision thresholds land exactly in the honest band.** Between 1.0
and 2.5 the gaps are +0.26, +0.34, +0.18 — the model says what it means. Below
1.0 it is overconfident by 2.56pp; above 2.5 by 5.25pp (n = 86, so noisy, but
it matches the frozen grid's own non-monotonicity, where the ≥2.5 cell fell to
52.90%).

**Operational reading: flat-bet inside the frozen thresholds. Do not Kelly-size
on |m|, and do not extend the signal above 2.5.** The 1.0/1.5 cells chosen by
`PREREG_move_combined` were not arbitrary — they sit where the magnitude is
truthful.

## CrewShock — monotone, and UNDER-stated

Converted at the frozen mechanism's +0.813 points per unit (`CLOSING_REFEREE`).

| CrewShock→pts | n | mean edge | implied | actual | gap |
|---|---|---|---|---|---|
| 0.0–0.3 | 6,427 | 0.034 | 51.07% | 49.04% | −2.03pp |
| 0.3–0.6 | 1,203 | 0.446 | 51.07% | 52.54% | +1.46pp |
| 0.6–0.9 | 900 | 0.740 | 52.30% | 53.00% | +0.70pp |
| 0.9–1.2 | 488 | 1.034 | 53.17% | 54.10% | +0.93pp |
| 1.2–1.6 | 288 | 1.367 | 53.17% | 53.82% | +0.65pp |
| 1.6+ | 81 | 1.817 | 54.59% | **60.49%** | **+5.90pp** |

Monotonic on **4 of 5** steps; `corr(edge, actual) = +0.919` — far cleaner than
MOVE_COMBINED. And every gap from 0.3 upward is **positive**: the +0.813
conversion **understates** what the signal delivers.

**This is NOT a licence to raise the threshold or to size.** The 60.49% top cell
is 81 games. The 0.8682 threshold is frozen and stays frozen; the standing rule
forbids re-thresholding, and mining a top bucket after the fact is exactly the
move `PREREG_roadtrip_foul` and `PREREG_national_tv` were written to prevent.
Any sizing scheme is a new strategy needing its own registration and its own
out-of-sample data.

## What this actually establishes

1. **The two signals differ in kind.** CrewShock's magnitude carries real
   information (corr +0.92). MOVE_COMBINED's carries it only within a band.
2. **Both frozen threshold choices are vindicated** — independently, by a test
   that could have embarrassed them.
3. **Kelly sizing is not supported for MOVE_COMBINED**, which matters because
   the Kelly literature in `papers/` (Wharton, Chu/Wu/Swartz, Uhrín, LUISS)
   presupposes a calibrated edge and this one is not calibrated outside 1.0–2.5.
4. **The session's recurring failure has a name.** Cohesion passing on points
   and losing on covers, the Gaussian map mispricing extremes by 2.81pp, the
   foul channel "explaining" 108.6% of its target — all three are calibration
   failures, not accuracy failures. Walsh & Joshi is the cleanest published
   statement of the principle this program kept rediscovering.

## What would make the calibration idea genuinely actionable

Build a forecaster that **emits a probability** and select it on Brier or log
score rather than on hit rate — then Walsh & Joshi applies directly rather than
by analogy. That is a new build, not an audit, and it should be registered
before it is started, with the endpoint fixed as a proper scoring rule and the
economics reported separately.

---

# LESSONS — the calibration thread, closed 2026-08-30

Four documents: `DISTRIBUTION_AUDIT`, `CALIBRATION_AUDIT`,
`PREREG_probabilistic_forecaster`, plus the cohesion P&L. **None produced an
edge. All produced constraints.** That is the honest headline.

## 1. Calibration is a distinct failure mode, and it had been unnamed here

Three failures this program hit independently turn out to be the same thing:

| failure | what it looked like | what it was |
|---|---|---|
| cohesion | passed on points (β +0.92, holdout-confirmed), lost **−3.56% ROI** | effect in the tail, not at the line |
| Gaussian ML map | misprices extremes by **2.81pp** | overconfident transform |
| foul channel | "explains" **108.6%** of its target | contaminated magnitude |

All three are **calibration** failures. None is an accuracy failure. Walsh &
Joshi named the principle; this program had been paying for it.

## 2. Miscalibration manufactures phantom edges AT THE EXTREMES

The naive Gaussian spread→probability map errs **2.81pp** on big favourites
against a **2.381pp** vig. **The error exceeds the hurdle, and it is largest
exactly where a model has most conviction** — which is where it would bet most.
An uncalibrated model does not fail randomly; it fails where it is loudest.

## 3. A positive hit rate does not imply calibration

The forecaster hit **53.26%** at |p−0.5| ≥ 0.02 with a calibration slope of
**0.43**. Reading the ROI and ignoring the slope is the specific error to avoid,
and it is seductive because the ROI is the number one wants to see.

## 4. When power kills your endpoint, look for a SHAPE statistic

Brier needs ~6,700 games for z = 2; we had 2,004 (z = +1.09 best case). But
calibration **slope** is a statement about shape, not magnitude, and it resolved
decisively at the same n — **0.43, far outside [0.80, 1.25]**. Magnitude
questions are expensive; shape questions are cheap. Same move as
`PREREG_move_combined` choosing CLV over ROI, and `PREREG_crewshock_forward`
choosing mechanism over P&L.

## 5. A MORE accurate transform can be WORSE on a noisy input

The Gaussian `φ(0)/σ` understates spread edge by **58%** against the exact
empirical CDF. But on MOVE_COMBINED it was *more* accurate in practice:

```
Gaussian implied 53.53%   exact-CDF implied 54.60%   REALISED 53.44%
```

Because |m| is a **predicted** move, a noisy 1.6-point forecast delivers less
than 1.6 points of true edge — and the Gaussian's conservatism accidentally
offset the prediction error. **Never fix the transform without also asking
whether the input is a realised quantity or a forecast.**

## 6. Kelly is not available to us, so flat-betting is correct, not timid

Every staking paper in `papers/` presupposes a calibrated edge. MOVE_COMBINED is
honest only inside 1.0–2.5; the combined forecaster is 2.3× overconfident. **The
honest combined signal is ±1.8pp against a 2.38pp vig.** Flat-betting inside the
frozen thresholds is the correct response to that, not caution.

## 7. Edge is a step function over key numbers

0.25 and 0.50 points of totals edge buy **identical** win probability (+1.08pp);
so do 1.60 and 2.00 (+4.60pp). "Half a point of edge" is meaningless without
saying *which* half-point. Continuous-density reasoning is wrong at the
resolution that decides bets.

## 8. The two frozen signals differ in kind

`CrewShock` is monotone (corr **+0.919**, 4/5 rising) and **understated** by its
own conversion. `MOVE_COMBINED` is band-limited (corr +0.548, 3/5 rising). They
should not be treated as interchangeable, and only one of them could ever
support sizing — which would still need its own registration.

## 9. The specification does the damage, not the statistics

The forecaster gave its strongest input a **negative coefficient** because I
referenced an opener-traded signal to a closing-line outcome. That joins
`PREREG_foul_q4`'s incomplete take-foul exclusion and `PREREG_roadtrip_foul`'s
road-only panel. **Three specification errors, zero statistical ones**, in a
session where the statistics were never the bottleneck.

## What calibration did NOT do

**It found nothing.** Every result was a downgrade, a constraint, or a
correction. Its value was **preventing errors, not creating opportunities** —
including the correction that the `1/σ` conversion had understated every edge
figure this program quoted, and the finding that our best combined object is
2.3× overconfident.

That is a reasonable return for the effort, and it should be expected of
calibration work generally: it tells you what your numbers *mean*, and the
answer is usually "less than you thought."
