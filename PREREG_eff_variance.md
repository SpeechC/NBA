# Pre-registration: efficiency state and closing-total dispersion

**Written before any outcome was examined. The feature definition below is
frozen and will not be altered after seeing results.**

## Feature construction — fixed here because `eff_level_20` did not previously exist

The hypothesis names `eff_level_20` as an existing feature. It does not exist in
this repo, so it is defined now, in advance:

```
team_oeff_i      = TEAM_OEFF for that team in that game   (vendor column)
roll20_i         = mean of team_oeff over that team's PRIOR 20 games,
                   lagged with shift(1), min_periods = 12, within season
eff_level_20     = roll20_home + roll20_away
```

Basis chosen for one reason, decided before running: `TEAM_OEFF` is populated
85–97% in **every** season including 2024-25 and 2025-26. Possession-derived
efficiency from play-by-play would be preferable on quality grounds but the
play-by-play stops at 2024-25, which would leave the validation window
half-covered. The requirement that discovery and validation use the identical
feature outranks the quality preference.

⚠ If a different `eff_level_20` was intended, this test does not answer that
hypothesis and must be re-run. The result below stands only for the definition
above.

## Design, as specified

- **Discovery**: seasons through 2023-24 (`yr <= 2023`)
- **Validation**: 2024-25 and 2025-26 (`yr in {2024, 2025}`). Nothing later.
- `total_error = actual_total - closing_total`, `abs_total_error = |total_error|`
- **Tail cutoff**: 80th percentile of `abs_total_error` computed on DISCOVERY
  ONLY, frozen as a number, never recomputed in validation
- **Quintile boundaries**: fitted on discovery, applied unchanged to validation

## Primary hypothesis

As `eff_level_20` rises, P(large absolute closing-total error) rises
monotonically. This is a **dispersion** hypothesis, not a direction hypothesis.

## Falsification requirement

Signed `total_error` must remain approximately unpredictable from
`eff_level_20`. If the feature materially predicts signed error, the
variance-state interpretation is not clean.

## Success criteria, all required

1. pooled validation beta > 0
2. both validation seasons showing the same positive tail-risk direction
3. positive validation log-loss improvement over the unconditional baseline
4. positive validation Brier improvement
5. monotonic or approximately monotonic validation quintiles

A positive pooled absolute-error correlation alone is **not** sufficient.

## Robustness, only after the primary test

Identical frozen procedure using a 10-game and 30-game efficiency consensus.
Treated as the SAME mechanism, not independent evidence. No other windows or
thresholds will be searched.
