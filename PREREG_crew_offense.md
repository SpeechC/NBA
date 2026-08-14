# Pre-registration: does CrewShock scale with offensive strength?

**Written before any outcome was examined.**

## Hypothesis

The scoring and pricing effect of `CrewShock` is larger for stronger offenses
than it is across defensive strength.

```
beta_O > 0                     primary
beta_O > beta_D                stronger version
```

Signs are fixed here and will not be revisited.

## Panel

Two rows per game, one per team. Inference is **clustered at the game level**,
since the two rows share a game, a crew and a total.

## Frozen states — recovered, windows unaltered

Two prior-only efficiency states exist in the repo and neither is silently
chosen:

- **primary**: `models_frozen` / `walkforward.py LAG = 4` -> `h_f_OEFF`,
  `a_f_OEFF`, `h_f_DEFF`, `a_f_DEFF`. This is the only state the project
  labels FROZEN (`FROZEN_ON = 2026-08-11`).
- **robustness**: the W=20 trailing states built in `ref_shock.build()` and used
  as controls in the final referee identification.

`CrewShock` and `LeagueFoulState` are loaded from `ref_features.csv`.

## Orientation, fixed in advance

Both interaction states are oriented so that **higher means more expected team
points**, which is what makes `beta_O` and `beta_D` comparable:

```
OwnOffense   = z(own team's f_OEFF)          higher = better offense
OppDefAllow  = z(opponent's f_DEFF)          higher = opponent allows more,
                                             i.e. weaker opposing defense
```

Standardisation uses **development only**.

## Implied closing team scores

```
implied_home = (closing_total - closing_spread_H) / 2
implied_away = (closing_total + closing_spread_H) / 2
TeamResidual = actual team points - implied closing team points
```

## The model

```
TeamResidual = a + bR*CrewShock
                 + bO*(CrewShock x OwnOffense)
                 + bD*(CrewShock x OppDefAllow)
                 + g*OwnOffense + h*OppDefAllow
                 + controls + eps
```

Controls: home indicator, `LeagueFoulState`, game pace state.

## The same decomposition is run for

fouls drawn (opponent fouls committed), team FTA, team FTM, actual team points,
implied closing team points, and the team closing residual.

The desired chain is

```
CrewShock x OffensiveStrength -> FTA -> FTM -> team points
```

with **less corresponding adjustment in implied closing team points**.

## Reporting

Development, holdout, each holdout season, pooled. Plus a descriptive
monotonicity check: `CrewShock` slopes within development-defined offensive
terciles and quintiles, and the same across defensive buckets. Those buckets are
**descriptive only** — no threshold is selected for trading.

## Stopping rule

If the broad OEFF interaction fails, **stop**. Do not search offensive
components. Only if it survives development and holdout with the predicted sign
does a decomposition of offense into foul-relevant scoring composition get
separately pre-registered.
