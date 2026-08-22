# PREREG — CrewPace: crew-specific possession propensity as a totals signal

**Written before any pace quantity was computed.** Architecture, gate structure
and prohibitions are inherited verbatim from `PREREG_crew_tilt.md`; only the
outcome variable and the isolation step below differ.

## The claim

Officials might differ persistently in how many possessions a game runs —
through whistle frequency, replay tolerance, delay-of-game management, and how
quickly play is resumed. Possessions move the total directly, so a crew-specific
pace propensity would be a totals signal on a channel CrewShock does not own.

## The design trap, and the isolation step

Fouls mechanically affect possessions: whistles stop the clock and free throws
consume time without consuming a possession. A raw pace propensity would
therefore be substantially CrewShock re-expressed in different units, and a
"pass" on it would be double-counting an established signal rather than
finding a new one.

So the PRIMARY state is measured net of the foul channel:

```
pace48   = ((PBP_POSS_H + PBP_POSS_R) / 2) * 240 / MIN     per-48 possessions
pace_net = pace48 - (a + b * pf_rate)        a, b fit on DEVELOPMENT ONLY
```

`CrewPaceNet` (built on `pace_net`) is the primary. `CrewPace` (built on raw
`pace48`) is reported alongside but is **not** the test — if the raw version
passes while the net version fails, the correct reading is that CrewShock
already captured it, and the branch still closes.

Estimator is unchanged from `ref_features.py`: N=60 min 25, matched league
horizon, EB shrinkage `n/(n+k)` with k by method of moments on development,
summed over the crew. `ref_features.py` is not modified.

## Stage 1 gates (development only) — all four must pass

| gate | quantity | pass condition |
|---|---|---|
| G1a | between-official true variance after removing sampling noise (MoM) | τ² > 0 |
| G1b | within-season split-half correlation of official mean `pace_net`, ≥20 games per half | r > 0 and t > 2 |
| G1c | forward persistence: realized `pace_net` on prior-only CrewPaceNet + LeaguePaceState | slope > 0 and t > 2 |
| G1d | time-local permutation of G1c, whole crews reshuffled within 7-day blocks | p < 0.05 |

Reported, not a gate: `corr(CrewPaceNet, CrewShock)`. A large value means the
isolation step failed and the branch closes regardless.

**If any gate fails, STOP.** No total, closing line, or market quantity is
computed by the Stage 1 script.

## Stage 2 — market test (only if all four gates pass)

`CrewPaceNet → realized possessions → actual total`, then `c_true` vs
`c_market` on the closing total with the frozen `rsk.CTRL` controls, holdout
reported separately. Falsification: CrewPaceNet must not predict the foul rate.

## The economic bar, stated in advance

The closing-total residual has sd 18.08 (measured in `ist_incentive.py`), so the
density at zero is ≈ 0.0221 per point: **1 point of total edge buys ~2.2pp of
cover probability.** Break-even at −110 needs +2.38pp, hence about **+1.08
points** of un-priced total effect. At league efficiency, one extra possession
for each team is ~2.24 points, so the bar is roughly **0.48 possessions** of
crew-specific, unpriced pace.

Prior expectation, recorded so a null is not later reframed: the CrewShock
mechanism accounting found made free throws were **114%** of the scoring effect,
meaning non-FT scoring slightly *offsets*. If foul-heavy crews moved pace
materially, that decomposition should have shown it. **I expect this to fail.**
It is run for completeness of the referee family, not on an attractive prior.

## Coverage limitation

`PBP_POSS` is present for 2017-18 through 2024-25 and **absent for 2025-26**.
Development is 2017-18..2023-24; the holdout here is 2024-25 only, one season
rather than two.

## Prohibited afterwards

Identical to `PREREG_crew_tilt.md`. Regardless of outcome: no alternative
horizons, no substitution of a different pace proxy after a failure, no
conditioning, no combination with CrewShock, no crew-chief weighting.
