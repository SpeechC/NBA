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
