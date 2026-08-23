# PREREG — nonlinear COMBINATIONS of season-to-date stats vs the closing total error

**Written 2026-08-23, before fitting.** One pass. Motivation (user): the market
may price individual stats well while joint configurations — combinatorially
many, hard to model, high-variance — hide structure. Linear PCA cannot see
these; hand-picked pairs (the six dispersion interactions) sampled the space;
this sweeps it.

## Specification, fixed now
- Features: prior-only expanding season-to-date means of ALL 133 advanced/box
  stats, both teams (266 cols), >= 10 prior games per team, NaN kept (native
  handling). No game-level realized values.
- Model: HistGradientBoostingRegressor, FIXED params (lr=0.05, max_iter=500,
  early stopping on a random 15% of development, min_samples_leaf=50,
  seed=0). No tuning, no second configuration.
- Targets: e = actual - closing total (mean channel) and e^2 (dispersion).
- Fit on development (<= 2023); score R^2 on holdout (2024-25 + 2025-26,
  pooled and per season).
- CONTROL: identical fit on within-season-permuted targets -> the overfit
  floor. The real model must beat the control's holdout R^2 to mean anything.

## Decision, fixed now
Holdout R^2 <= 0 (or <= control) on both targets closes the combination
hypothesis for this feature space. A positive holdout R^2 gets a follow-up
prereg before any interpretation. No feature-importance readouts unless
holdout R^2 > 0 (importances of a null model are noise).

---

## RESULT — run once, 2026-08-23. Combination hypothesis CLOSED for this space.

6,222 development / 2,014 holdout games, 266 features.

| target | in-sample R2 | HOLDOUT R2 | control (permuted target) | per-season |
|---|---|---|---|---|
| mean e | +0.1035 | **-0.0318** | +0.0005 | -0.011 / -0.052 |
| e^2 | +0.0710 | **-0.0029** | -0.0063 | -0.003 / -0.006 |

The capacity check passes: the model fits 10% of development variance
in-sample, so it CAN represent combination structure. Out of sample it does no
better than the same model fit on within-season-permuted targets — for the
mean channel it is WORSE than the noise-floor control. Early stopping halted
at 18 and 12 iterations: the internal validation split detected almost
immediately that nothing generalizes.

Per the fixed decision rule: holdout R2 <= control on both targets ->
**the combination hypothesis is closed for this feature space.** No
feature importances are reported (importances of a null model are noise).

Scope note: this closes interactions among season-to-date TEAM-STAT
aggregates. Combinations involving non-stat-sheet information (referee
assignment, late injuries, price history) are separately established results
and are not touched by this null.
