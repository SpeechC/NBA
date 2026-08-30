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

---

# RESULT — built and scored once, 2026-08-30. **P1 FAILS.**

Development 3,101 (2021-22…2023-24), holdout 2,004 (2024-25, 2025-26).

**Forced split, recorded:** `MOVE_COMBINED_OOS` begins 2021-22, so §5's 2017-18
start does not exist. Holdout n ≈ 2,000 is exactly the case §3 priced at
z = +1.09.

## Stage 1 — and the coefficient that exposes a flaw in my own design

```
m          -0.04035        <- NEGATIVE
CrewShock  +0.11433
final7     +0.40209
intercept  +0.00954
```

`CrewShock` and `final7` enter positive and sensible. **`m` enters negative**,
and the reason is a specification error in §1 of this document, not a property
of the signal: the outcome is **over versus the CLOSING total**, while
`MOVE_COMBINED` forecasts open→close movement and realises its edge **betting
the opener**. Referencing the close means `m`'s information is already inside
the target. Two of the three inputs are close-referenced; the third is not, and
I gave all three the same outcome.

**This is my error and it is not an excuse.** The prereg was mine, the outcome
definition was mine, and the result stands as registered.

## P1 PRIMARY — FAILS, decisively

```
calibration slope     +0.4308     required [0.80, 1.25]   FAIL
calibration intercept +0.0103     required [-0.05, +0.05] PASS
```

**A slope of 0.43 means the model is roughly 2.3× overconfident.** To be honest
its logit would have to shrink by ~57%: the forecast spread of sd 0.0425 should
really be about **0.018**.

That number is the practical finding. **The combined signal's honest strength is
about ±1.8pp of win probability, against a vig of 2.38pp.** Not enough.

## P2 RELIABILITY — the overconfidence is concentrated at the top

| decile | n | mean forecast | actual | gap |
|---|---|---|---|---|
| 1 | 807 | 46.68% | 47.58% | +0.90pp |
| 2 | 609 | 50.97% | 50.90% | −0.06pp |
| 3 | 412 | 55.07% | 54.61% | −0.46pp |
| **4** | **176** | **59.13%** | **53.98%** | **−5.15pp** |

Isotonic collapsed the output to four distinct levels. The first three are well
behaved (|gap| ≤ 0.90pp); **the confident bucket is wrong by 5.15pp** — the same
shape `CALIBRATION_AUDIT` found in MOVE_COMBINED's raw magnitude above 2.5, and
isotonic fitted on development did **not** fix it out of sample.

## P3 BRIER / LOG SCORE — reported, not decisive

```
Brier  model 0.25005   baseline 0.25000   gain -0.000052   z = -0.05
log loss model 0.69336 baseline 0.69315   gain -0.000210
```

§3 predicted z ≈ +1.09 and fixed in advance that a non-significant gain would
not be a failure. The gain is not merely non-significant — it is **marginally
negative**. The forecaster is not better than a coin flip on a proper scoring
rule.

## Economics — reported only, per §6

```
every game        2,004 bets   52.54%   ROI +0.31%
|p-0.5| >= 0.02   1,395 bets   53.26%   ROI +1.68%
|p-0.5| >= 0.04     652 bets   53.22%   ROI +1.60%
```

**These cannot pass this prereg and are not a finding.** They are also exactly
the trap the whole document was built to avoid: a model that is *miscalibrated*
can still show a positive hit rate, and reading the ROI here while ignoring
slope 0.43 is the error Walsh & Joshi describe.

## Disposition — and what §7 forbids

§7 fixed it: **"P1 fails with slope < 0.8 → report the slope; do NOT refit."**
No refit is performed. The obvious repair — reference `m` to the **opening**
total so its edge is not neutralised — is a **different specification** and
would need its own registration on data this run has now consumed.

**What is established:** the three frozen signals, combined by a fixed logistic
and isotonic-calibrated on development, **do not produce calibrated
probabilities out of sample.** Sizing on this object is not defensible, and
`CALIBRATION_AUDIT`'s conclusion stands unchanged — **flat-bet inside the frozen
thresholds.**

**What is not established:** that a correctly specified forecaster would fail.
The `m` handicap is real and quantified, and a close-referenced target was the
wrong instrument for an opener-traded signal.

## Lesson, recorded

**When combining signals that trade against different lines, the outcome must
match each signal's trading point.** Forcing one outcome on all three imported a
negative coefficient on the strongest input. This is the same class of error as
`PREREG_foul_q4`'s incomplete take-foul exclusion and `PREREG_roadtrip_foul`'s
road-only panel: the specification, not the statistics, did the damage.
