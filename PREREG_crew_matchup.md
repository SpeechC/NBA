# Pre-registration: crew foul propensity × matchup foul pressure

**Written before any outcome was examined.** Follows Test 1 (`PREREG_crew_foul.md`).

## The claim under test

A high-calling crew should have disproportionately greater scoring consequences
when both matchups naturally generate foul situations. The mechanism dictates
the interaction; the variables merely identify it.

The result that would count is NOT that the interaction predicts scoring. It is
that the two chains diverge:

```
Crew x Matchup  ->  fouls -> FTA -> ACTUAL total      must strengthen
Crew x Matchup  ->  CLOSING total                     must stay weak
```

Components observable, joint implication not assembled by the market.

## Features, prior-only, drift-adjusted

League foul rates fell steadily 2017-2026. Test 1 showed that failing to adjust
for that drift makes frozen thresholds partition by season, so every propensity
here is expressed as a RATIO to the trailing 500-game league level, which is
scale-free, drift-free and monotone increasing in foul activity.

```
commits_i,g   = ADV_PF_PER100_OPP_POSS for team i in game g
draws_i,g     = same column for i's OPPONENT
                (fouls committed against i, per 100 of i's possessions)

FC_i,t        = mean(commits_i / lg) over i's PRIOR 20 games, shift(1), min 10
FD_i,t        = mean(draws_i   / lg) over i's PRIOR 20 games, shift(1), min 10

M_t           = FD_home * FC_away  +  FD_away * FC_home      ~ 2.0 at average
CrewFoul_t    = unchanged from Test 1
```

Ratios rather than demeaned deviations, deliberately: with demeaned inputs the
product `FD*FC` is large when both are HIGH *or* both are LOW, which would put
low-foul games in the high-pressure regime.

## Design

- Develop: through 2023-24. Holdout: 2024-25 and 2025-26. Both `ADV_` columns
  are 100% covered on both sides of the split.
- **Frozen on develop, applied unchanged to holdout**: `Q75` of `CrewFoul` and
  `Q75` of `M`.
- **2x2 cells**: neither / crew-only / matchup-only / BOTH.

## The interaction contrast

```
interaction = (BOTH - crew_only) - (matchup_only - neither)
```

Zero means the joint state is exactly the sum of its parts. The hypothesis is
that it is positive for fouls, FTA and the actual total, and that the market's
closing total does not contain it.

## The market test

```
closing total ~ mu_state + CrewFoul + M + CrewFoul*M      c_market on the product
actual total  ~ mu_state + CrewFoul + M + CrewFoul*M      c_true   on the product
```

## Success criteria, all required

1. the interaction contrast on FOULS and FTA is positive in develop AND holdout
2. the interaction contrast on the ACTUAL total is positive in both
3. the interaction contrast on the CLOSING total is materially smaller than on
   the actual total — this is the decomposition failure being claimed
4. the BOTH-cell closing residual beats a matched-size crew-reshuffle
   permutation
5. the BOTH-cell holdout over rate clears 52.38%

Criterion 3 is the one that makes this Voulgaris-like rather than a repackaged
main effect. If 1 and 2 hold but 3 fails — the book moves its total with the
interaction just as much as reality does — the market prices it and there is no
opportunity, which is the outcome for pace, efficiency and dispersion.

## Falsification

If the BOTH cell simply reproduces what CrewFoul alone delivers (interaction
contrast ~ 0 while main effects carry everything), the matchup adds nothing and
Test 2 is negative regardless of how strong the BOTH cell looks in isolation.
