# Pre-registration: crew-level referee foul aggregation

**Written before any outcome was examined.**

## Motivation

Individual referee foul propensity is strongly identifiable (family-wise
p_max = 0.0075, sigma_ref = 0.638 fouls per 100 opponent possessions), while the
individual referee *scoring* effect is not (p_max = 0.1759, sigma_ref = 0.672
points). The economic question is whether the accumulated effect of an
unusually extreme three-official crew survives where a single official does not.

## Signal — built from FOUL propensity only, never from scoring residuals

For each official `r` and game at date `t`:

```
pf_rate_g      = ADV_PF_PER100_OPP_POSS_H + ADV_PF_PER100_OPP_POSS_R
lg_t           = expanding league mean of pf_rate over PRIOR games in the
                 same season, min 50 games   (knowable pregame)
y_g            = pf_rate_g - lg_t
f_hat(r, t)    = sum of y over r's games STRICTLY BEFORE t
                 -------------------------------------------
                       (count of those games) + k
CrewFoul_t     = f_hat(r1, t) + f_hat(r2, t) + f_hat(r3, t)
```

`k` is the empirical-Bayes shrinkage constant, estimated by method of moments on
DEVELOP ONLY and then frozen. An official with no prior games contributes
exactly 0, which the formula gives automatically.

Everything is strictly prior-only. Nothing in `CrewFoul` uses the current game,
the current season's completed data, or any scoring residual.

## Design

- **Develop**: seasons through 2023-24. **Holdout**: 2024-25 and 2025-26.
  `ADV_PF_PER100_OPP_POSS` is 100% covered on both sides of the split, so unlike
  the play-by-play features this test validates on BOTH holdout seasons.
- **Regimes frozen on develop**, applied unchanged to holdout:
  `HIGH = CrewFoul >= Q85`, `LOW = CrewFoul <= Q15`.
  15% tails rather than 20% because the question is specifically whether
  pronounced combined effects get large enough to matter economically.

## The chain to be tested

```
CrewFoul -> actual fouls -> FTA -> actual total -> closing-total residual
```

Reported at every link so the attenuation is visible, in develop and holdout
separately. A genuine causal mechanism should weaken monotonically down the
chain; a spurious one should not show the early links at all.

## The market test

```
closing total ~ a + b*mu_state + c*CrewFoul     c_market
actual total  ~ a + b*mu_state + c*CrewFoul     c_true
```

`c_market = 0` with `c_true > 0` means the book ignores crew foul propensity
entirely. `c_market = c_true` means it prices it correctly. The hypothesis under
test is `0 < c_market < c_true` — partial pricing.

## Success criteria

1. the early links (fouls, FTA) must move in develop AND holdout, or the
   signal is not measuring what it claims to
2. the closing-residual contrast HIGH minus LOW must have the same sign in
   develop and holdout
3. the holdout over-rate in the favoured regime must clear 52.38%
4. the residual contrast must beat a within-season crew-reshuffle permutation

Criteria 1-2 failing means no mechanism. 1-2 passing with 3-4 failing means a
real but sub-economic mechanism, which is the expected outcome given that the
individual referee scoring effect is 0.672 points against a 1.08-point
break-even.
