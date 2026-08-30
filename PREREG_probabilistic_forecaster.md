# PREREG — A CALIBRATED PROBABILISTIC FORECASTER FOR NBA TOTALS

Written 2026-08-30. **NOT YET BUILT.** Only the power arithmetic in §3 has been
run. No model has been fitted.

## 0. Why this is not the build it looks like

The obvious design is: fit a model, score it on Brier, beat the baseline.
**Stage-0 shows that endpoint is unreachable on our data**, and the prereg is
written around that fact rather than discovering it afterwards.

`CALIBRATION_AUDIT` established the gap this fills: **this program has no
probabilistic forecaster.** `MOVE_COMBINED` emits points of predicted movement;
`CrewShock` emits a propensity and a frozen flag. Neither outputs a probability,
so we cannot size, cannot combine signals coherently, cannot compute expected
value per bet, and cannot compare across markets. Walsh & Joshi
(`papers/ssrn_4705918.pdf`) is right that Kelly needs a calibrated model — we do
not have one to Kelly on.

## 1. The baseline is 0.5, and that is not a weakness

For **totals**, the market's implied probability is ≈ 0.5 by construction: the
line is set so both sides are near-even. Measured: **over rate 50.27%** against
the closing total (push 1.03%). So the honest baseline is a flat 0.5 forecast,
**Brier = 0.2500 exactly**.

Contrast **moneyline**, where the market *is* an informative forecaster —
measured Brier **0.20502** on 9,489 games, calibrated within ~1pp everywhere
(`DISTRIBUTION_AUDIT`). Beating that is a far harder target and we hold no
moneyline signal. **Totals is the right venue and moneyline is out of scope.**

## 2. Scope, and the rule it operates under

**Inputs are FROZEN, ALREADY-PASSED signals only.** No feature search, no new
variable, no discovery:

```
m          MOVE_COMBINED_OOS   (walk-forward, frozen weights)
CrewShock  frozen ref_features.csv, read-only
final7     days_left <= 7      (CLOSING.md, validated)
```

`PREREG_move_combined` §4 stated that a combined-spec extension "gets its own
pre-registration." **This is that registration, and it is for CALIBRATION ONLY.**
The resulting probability object is **not authorised for trading**; deploying it
requires a separate registration with its own out-of-sample data. Nothing here
rescues a failed branch — all three inputs passed on their own terms.

## 3. THE POWER ARITHMETIC — run first, and it decides the endpoint

MOVE_COMBINED's implied probability deviation from 0.5, at the exact empirical
density of 2.22pp per point:

```
sd(delta) 0.0244    mean|delta| 0.0190    max|delta| 0.1390
E[delta^2] = 0.000595      <- the BEST-CASE paired Brier gain, if perfectly calibrated
```

Paired Brier improvement against the 0.5 baseline, best case:

| n | se(mean paired diff) | z |
|---|---|---|
| 1,000 | 0.000771 | +0.77 |
| 2,000 | 0.000545 | +1.09 |
| **5,158** (our full walk-forward sample) | 0.000340 | **+1.75** |
| 10,000 | 0.000244 | +2.44 |
| 20,000 | 0.000172 | +3.45 |

**Even using every game we have, and assuming the model is perfectly
calibrated, the Brier improvement reaches only z = +1.75.** A holdout of ~2,000
gives z = +1.09. Roughly 6,700 games are needed for z = 2, and we cannot supply
them out of sample.

**Consequence, fixed here: Brier improvement CANNOT be the primary endpoint.**
It is reported, with this table beside it, and it is **not decisive** — the same
logic by which `PREREG_move_combined` made CLV primary because ROI needed 49
seasons.

## 4. The primary endpoint is CALIBRATION, which IS measurable

Calibration is a statement about **shape**, not magnitude, and it is testable at
this sample size where a Brier difference is not.

**P1 PRIMARY — calibration slope and intercept.** Regress the outcome on the
forecast logit:

```
logit(P(over)) fitted on the holdout against the model's own logit
PASS requires:  slope in [0.8, 1.25]   AND   intercept in [-0.05, +0.05]
```

A slope below 1 means **overconfident** — the model's extremes are too extreme,
which is exactly the failure that made a naive Gaussian map misprice by 2.81pp
and manufacture phantom edges. Slope above 1 means underconfident.

**P2 — reliability across deciles.** Mean forecast versus realised frequency in
each holdout decile. Reported as a table, with the maximum absolute gap. The
`CALIBRATION_AUDIT` benchmark to beat is MOVE_COMBINED's raw magnitude, which
was honest inside 1.0–2.5 (gaps +0.18 to +0.34pp) and broken outside it
(−2.56pp and −5.25pp). **The forecaster's job is to be honest across the WHOLE
range, not just in a band.**

**P3 — paired Brier and log score**, reported with §3's power table. Expected to
be positive and not significant. **A non-significant Brier gain is NOT a
failure** — §3 fixed that in advance.

## 5. Model class — fixed now, no search

```
Stage 1   logistic regression, P(over) ~ m + CrewShock + final7
Stage 2   isotonic calibration of Stage 1's output, fitted on DEVELOPMENT only
```

No alternative model class, no hyperparameter search, no feature addition, no
interaction terms. If the fixed class fails P1, **the finding is that these
signals do not calibrate**, not that a better architecture should be sought.

Split, matching the program's convention:

```
development   2017-18 .. 2023-24
holdout       2024-25, 2025-26        scored ONCE
```

## 6. Economics — reported, explicitly NOT the endpoint

Hit rate and ROI at the corrected `1.90909·hit − 1` are reported for the
holdout, with the block-bootstrap interval. **They cannot pass or fail this
prereg.** `CALIBRATION_AUDIT` already showed MOVE_COMBINED's magnitude is only
trustworthy inside 1.0–2.5; if the forecaster is calibrated, the operational
consequence is that **sizing becomes defensible where flat-betting was
previously the only safe choice** — and that is a capability, not an edge claim.

## 7. Fixed readings

- **P1 passes → we have a calibrated forecaster.** That is the deliverable. It
  licenses sizing and coherent signal combination; it does **not** license
  deployment without a separate registration.
- **P1 fails with slope < 0.8 →** the signals are overconfident in combination.
  Report the slope; do **not** refit to fix it — a refit on the holdout would
  destroy the only out-of-sample evidence we have.
- **P3 positive but not significant →** expected, per §3, and reported as such.
- **P3 NEGATIVE and significant →** the combination is worse than a coin flip
  and the branch closes.

## 8. What is NOT permitted

No feature beyond the three named. No model class beyond the two fixed stages.
No re-fitting after seeing the holdout. No threshold on the output probability
chosen post hoc. No promotion of P3 to primary if it happens to clear.

## 9. Prior

The three inputs are individually established, so a positive Brier point
estimate is likely. Calibration is genuinely open: `CALIBRATION_AUDIT` showed
MOVE_COMBINED's raw magnitude is well-behaved only inside a band, and isotonic
regression on development may or may not fix the tails on 2,000 holdout games.
**I expect P1 to pass on slope and to be marginal on the extreme deciles**,
which is where the honest work is.
