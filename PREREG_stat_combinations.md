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
