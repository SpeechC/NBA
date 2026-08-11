# Holdout result: PASS on the pre-registered metric

Executed 2026-08-11 against `dfMaster_OT_2017-2026.csv`, following
`PREREGISTRATION.md` without deviation. Frozen spec A, threshold 1.25, CLV as
primary, both seasons reported separately and pooled.

Data passed the acceptance gate first: overtime present at 5.11%, over rate
50.33%, closing beats opening on both markets.

## Result

| sample | n | **CLV** | 95% CI | beat close | win % | ROI % | P(ROI>0) |
|---|---|---|---|---|---|---|---|
| development (in sample) | 820 | 1.784 | [1.546, 2.021] | 66.0% | 53.54 | +2.21 | 75.0% |
| **HOLDOUT 2024-25** | 222 | **+1.718** | [1.272, 2.165] | 69.4% | 49.55 | −5.41 | 18.9% |
| **HOLDOUT 2025-26** | 220 | **+1.761** | [1.276, 2.246] | 67.7% | 53.64 | +2.40 | 63.0% |
| **HOLDOUT pooled** | **442** | **+1.740** | **[1.410, 2.069]** | 68.6% | 51.58 | −1.52 | 36.8% |

**VERDICT: PASS.** Pooled CLV +1.740 clears the pre-registered threshold of
+1.2 with a confidence interval well above zero, and the two seasons agree in
sign.

## What replicated, and how closely

* **CLV: +1.740 against a backtest anchor of +1.844** — within 6%, on 442 bets
  no model had seen.
* **The two seasons agree almost exactly**: +1.718 and +1.761, on independent
  samples of 222 and 220. Independent agreement is evidence pooling cannot give.
* **Beat-close is higher than the backtest**: 68.6% vs 66.6%.
* **The movement→outcome mechanism is intact and slightly stronger**:

  | | development | holdout |
  |---|---|---|
  | corr(move, actual−open) | 0.195 | 0.219 |
  | slope | +1.118 (t=14.2) | +1.155 (t=10.5) |

  A slope above 1.0 means the market's moves are, if anything, under-done.

This was a genuine out-of-sample test. 2025-26 in particular was untouched in
every respect — no odds, no play-by-play, nothing.

## What did not replicate: the payout

Pooled ROI is **−1.52%** and the win rate **51.58%** against a backtested
54.05%. That is roughly one standard error low (SE 2.4pp at n=442), so it is
within noise — but it is the opposite direction from the CLV result and should
not be waved away.

The arithmetic reconciles them: CLV 1.740 × movement-outcome slope 1.155 ≈ 2.0
points of expected edge, which on a residual SD of ~18 implies a win rate near
**54%**. We observed 51.58%, about 1.2 standard errors below. Every component
replicated; the realised outcome landed on the unlucky side of what those
components imply.

Note the split: 2024-25 won 49.55% and 2025-26 won 53.64%. The more recent and
cleaner season performed better, which argues against edge decay from market
sharpening.

## What this does and does not establish

**Established:** the model predicts NBA totals line movement out of sample, at
essentially the magnitude backtested, consistently across two independent
seasons. That is no longer a hypothesis.

**Not established:** that it is profitable. The pre-registration computed this
in advance — separating a true 54% win rate from the 52.38% break-even at 80%
power needs roughly **5,500 bets, about 22 seasons**. The holdout supplies 442.
No amount of additional analysis of this data changes that.

The pre-registration also pre-committed the reading of exactly this outcome:
"If CLV passes and ROI is negative, the signal replicated and the season was
unlucky -- that is the expected outcome roughly 30% of the time even with a
genuine edge." The observed P(ROI>0) of 36.8% is consistent with that.

## Where the remaining risk sits

Not in the model. The binding constraints are the ones alpha decay identified
and this test cannot address:

* **92.4% of the CLV is gone by the first line repost.** The edge exists only at
  the opening number.
* **Price.** Break-even needs ~1.35 points of CLV at -110 but only ~0.69 at -105.
  At 1.740 the strategy has room at either price -- but the win rate is what
  pays, and it is unproven.
* **Limit at the opener**, which is typically the smallest of the day.

The honest position: a real, replicated, out-of-sample signal of the expected
size, whose profitability remains statistically unproven and whose execution
window is minutes wide.
