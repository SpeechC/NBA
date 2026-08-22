# PREREG — CrewTilt: crew-specific home/road whistle tilt as a spread signal

**Written before any tilt quantity was computed. Nothing below was chosen after
seeing an outcome.**

## The claim

Every referee state in this project is a *level* effect: CrewShock predicts
combined fouls and therefore the total. We have never measured the *directional*
dimension — whether officials differ persistently in how their whistles split
between the home and road teams.

The market certainly prices average home advantage. The CrewShock finding was
that the market prices the league-wide officiating component (`c_market` +0.862
against `c_true` +1.152) and ignores the crew-specific deviation (`c_market`
+0.043 against `c_true` +0.922). CrewTilt asks whether the same split holds on
the *directional* channel and the *spread* market.

This inherits the exogeneity work for free. Five independent checks already
established that crew assignment is orthogonal to team state, each landing below
its own permutation null. Nothing about those checks was specific to the foul
level, so they transfer to tilt.

## The state

Per game, from `game_advanced_stats.csv`:

```
tilt = ADV_PF_PER100_OPP_POSS_R - ADV_PF_PER100_OPP_POSS_H
```

Fouls committed by the road team minus fouls committed by the home team, both
per 100 opponent possessions. **Positive = the road team is whistled more =
officiating favours the home side.**

Estimator architecture is copied from `ref_features.py` with no change other
than the outcome variable:

- official's horizon N = 60 games, minimum 25
- each official's mean tilt over their last N games **minus the league mean tilt
  over the identical calendar span** (matched horizons — this is the fix that
  re-centred the CrewShock permutation null from +0.405 to −0.024)
- empirical-Bayes shrinkage `n/(n+k)`, k by method of moments on development
  only, on the matched scale
- `CrewTilt = sum of the three officials' shrunk effects`
- `LeagueTiltState = trailing 200-game league mean tilt - trailing 1230-game
  mean`, to separate crew identity from the secular decline in home advantage

`ref_features.py` is not modified, imported-and-mutated, or re-run. CrewTilt
lives in a new module and a new file.

## Stage 1 — persistence gate (development only)

**This is the whole point of the two-stage design.** CrewShock worked because
foul propensity persists (forward slope 1.43–2.33). A within-official *
differential* is a much noisier object than a level, and tilt may simply not be
a trait. If it is not, the test must die here, before any spread residual is
computed, so that no outcome can influence the decision to continue.

All four gates must pass:

| gate | quantity | pass condition |
|---|---|---|
| G1a | between-official true SD after removing sampling noise (MoM) | τ² > 0 strictly, and reported signal share |
| G1b | within-season split-half correlation of official mean tilt, officials with ≥20 games per half | r > 0 and t > 2 |
| G1c | forward persistence: realized game tilt on prior-only CrewTilt + LeagueTiltState, development | slope > 0 and t > 2 |
| G1d | time-local permutation of G1c's slope, whole crews reshuffled within 7-day blocks | p < 0.05 |

**If any gate fails, STOP.** Do not compute the spread residual, do not
condition, do not try FTA in place of fouls, do not extend the horizon. Record
the failure and close the branch.

Reported alongside but **not** gates: `corr(CrewTilt, CrewShock)` — expected near
zero, since one is a sum and the other a difference of the same two quantities.
A large correlation would mean CrewTilt is not a new channel and would be
grounds to stop regardless of the gates.

## Stage 2 — market test (only if all four gates pass)

Pre-specified now so it cannot be designed around a Stage 1 result.

1. Mechanical chain, each link with cluster-robust OLS at game level:
   `CrewTilt → tilt in fouls → tilt in FTA → tilt in FTM → final margin`
2. `c_true`: margin on CrewTilt, controls `pace_s, oeff_s, deff_s, mu_state`
   plus LeagueTiltState (the frozen `rsk.CTRL` set)
3. `c_market`: closing implied home margin (`-CLOSING SPREAD_H`) on CrewTilt,
   identical controls
4. gap = `c_true - c_market`, with the difference tested directly
5. Holdout 2024-25 and 2025-26 reported separately, never pooled with development
6. Falsification: CrewTilt must **not** predict the combined total, and
   CrewShock must **not** predict realized tilt. Both are directional/level
   orthogonality checks.

## The economic bar, stated in advance

The spread residual has sd ≈ 12.9, so the density at zero is ≈ 0.031 per point:
**1 point of margin edge buys roughly 3.1pp of cover probability.** Break-even
at −110 is 52.38%, so a tradeable signal needs about **+0.77 points** of
un-priced margin.

Rough forward expectation, so that a sub-economic result is not later spun as a
success: if the per-official true SD of tilt is ~0.3 fouls/100, the crew sum has
SD ~0.5, and at the measured conversion of ~0.4 points per foul that is ~0.2
points of margin per SD. **That is roughly a quarter of the economic bar.** The
realistic outcome of this test is a real-but-untradeable effect, in the same
category as the confirmed-but-untradeable H2 and OT results.

It is still worth running once because it is the only unexplored *directional*
referee channel, it costs one script, and the exogeneity work is already done.
It is not worth running twice.

## Prohibited afterwards

Regardless of outcome: no alternative horizons, no FTA-based tilt substituted
for foul-based tilt after a failure, no conditioning on team type or venue, no
combination with CrewShock, no crew-chief weighting. A second specification is
specification mining by definition, exactly as recorded for CrewShock in
`PROSPECTIVE.md`.

## Inherited risk

2025-26 triggered M1 and M2: foul-propensity persistence weakened
(`REFEREE_PROPENSITY_PERSISTENCE_WEAKENED`). Any signal built on "officials'
tendencies persist" partially inherits that risk. Tilt-persistence and
level-persistence are different behavioural traits and can decouple — but if
officiating standardisation is compressing all individual heterogeneity, this
branch decays with the rest of the referee family.
