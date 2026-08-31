# MONEYLINE ERROR ATLAS — named teams, named styles (2026-08-30)

Five diagnostic tables, built before any conclusion, because a pooled
`E[beta] ~ 0` does not establish `beta(X) = 0` for a given current matchup. The
earlier local-analog test deliberately excluded franchise identity, which is the
right instrument for "do profiles generalise" and the wrong one for "which teams."

**Sample:** 4,554 regular-season games / 9,108 team-games, 2022-23 .. 2025-26,
120 team-seasons at a mean of 76 games each. Team-seasons are **never pooled
across years**.

**Read the dispersion column first.** In every table below the observed spread
across team-seasons is at or BELOW what pure sampling noise alone produces.

## TABLE 1 — team-season moneyline calibration

`r = Y - p_mkt` from each team's own perspective.

```
observed sd across 120 team-seasons   0.0511
pure-noise sd                         0.0517
empirical-Bayes shrinkage weight      0.0000
team-seasons with |t| > 2:  4 of 120   (expect ~6 by chance)
```

Extremes, shown raw with standard errors:

| team-season | N | resid | se | t | fav cal | dog cal |
|---|---|---|---|---|---|---|
| Philadelphia 2022 | 71 | +0.1105 | 0.0539 | +2.05 | +0.1331 | +0.0603 |
| Detroit 2025 | 77 | +0.0970 | 0.0495 | +1.96 | +0.0265 | +0.3882 |
| San Antonio 2025 | 76 | +0.0933 | 0.0479 | +1.95 | +0.0793 | +0.1612 |
| … | | | | | | |
| Detroit 2023 | 78 | −0.0849 | 0.0410 | −2.07 | −0.2405 | −0.0647 |
| Toronto 2023 | 78 | −0.0890 | 0.0478 | −1.86 | −0.0740 | −0.0954 |

## TABLE 2 — value of OUR disagreement, by team-season

`Y - p_mkt = alpha + beta*D_M`

```
observed sd of beta   0.01274
pure-noise sd         0.01447
|t| > 2:  5 of 120   (expect ~6)  -- and ALL FIVE ARE NEGATIVE
total P/L betting our model's side at ACTUAL moneylines:
   -$29,251 over 4,554 bets   ROI -6.42%
```

| team-season | N | beta | se | t | n_bet | P/L $100 |
|---|---|---|---|---|---|---|
| Philadelphia 2023 | 78 | −0.03655 | 0.01036 | **−3.53** | 48 | −683 |
| Oklahoma City 2023 | 78 | −0.03252 | 0.01101 | −2.95 | 43 | −508 |
| Sacramento 2024 | 78 | −0.03353 | 0.01557 | −2.15 | 27 | −1,223 |
| Brooklyn 2025 | 78 | −0.02435 | 0.01141 | −2.13 | 53 | −2,956 |
| … | | | | | | |
| Utah 2023 | 78 | +0.02402 | 0.01694 | +1.42 | 52 | −331 |
| Boston 2022 | 71 | +0.02295 | 0.01735 | +1.32 | 32 | +203 |

Every team-season where our disagreement is statistically detectable, it points
the **wrong** way.

## TABLE 3 — current-team offensive / defensive forecast error

```
|t| > 2 on offensive bias   2 of 120   (expect ~6)
|t| > 2 on defensive bias   2 of 120
off bias sd 1.073 vs pure-noise 1.280      def bias sd 1.024 vs 1.281
```

| team-season | N | off bias | se | t | def bias | t | off +tail | off −tail |
|---|---|---|---|---|---|---|---|---|
| Charlotte 2025 | 78 | +3.307 | 1.263 | +2.62 | −1.203 | −0.84 | 0.231 | 0.077 |
| Boston 2023 | 77 | +2.612 | 1.401 | +1.86 | +0.183 | +0.17 | 0.195 | 0.091 |
| LA Clippers 2022 | 71 | +2.362 | 1.497 | +1.58 | +1.215 | +0.97 | 0.211 | 0.127 |
| … | | | | | | | | |
| Memphis 2023 | 78 | −2.199 | 1.129 | −1.95 | +0.686 | +0.58 | 0.103 | 0.167 |

**Persistence within season, first half -> second half:**
```
offensive bias corr  -0.2190
defensive bias corr  -0.2567
```

**Negative.** A team that over-performs early under-performs later. That is the
signature of an adaptive filter self-correcting — the state engine updates on
realised efficiency, so an early positive error raises the forecast and drives the
later error negative. It is not a team property.

## TABLE 4 — style-matchup error surfaces (home offence x road defence)

Median splits on prior-only profiles. Transition is computed from the **PBP
transition store** — the first load-bearing use of that pipeline.

| surface | cell | N | book err | our margin err | D_M value (t) |
|---|---|---|---|---|---|
| 3PA rate | HIGH/HIGH | 1,255 | −1.65pp (t−1.33) | −0.78 | −0.00445 (−1.43) |
| | LOW/LOW | 1,255 | +1.98pp (t+1.57) | +0.30 | −0.00524 (−1.59) |
| OREB | HIGH/LOW | 1,081 | −1.54pp (t−1.10) | −0.64 | +0.00155 (+0.43) |
| turnovers | HIGH/LOW | 1,075 | +1.04pp (t+0.76) | −0.32 | +0.00643 (+1.75) |
| | LOW/LOW | 1,202 | −1.72pp (t−1.36) | −0.46 | −0.00543 (−1.80) |
| **FT rate** | **LOW/LOW** | **1,259** | **−2.60pp (t−2.08)** | −1.02 | −0.00509 (−1.60) |
| transition (PBP) | HIGH/HIGH | 1,085 | +1.44pp (t+1.07) | +0.16 | +0.00150 (+0.43) |
| | LOW/HIGH | 1,141 | −1.40pp (t−1.06) | −0.72 | −0.00421 (−1.30) |

**Of 20 cells, exactly ONE exceeds |t| = 2** — FT-rate LOW/LOW — which is precisely
the chance expectation for 20 tests. **No D_M cell reaches |t| = 2** (max 1.80).

## TABLE 5 — named teams in the extreme cells

| surface, HIGH/HIGH offensive side | teams most frequently occupying it |
|---|---|
| 3PA rate | Golden State (77), Milwaukee (74), Boston (71), San Antonio (65) |
| OREB | Houston (74), New York (68), Portland (68), New Orleans (60) |
| turnovers | Utah (71), Charlotte (62), Portland (62), Memphis (56) |
| FT rate | LA Lakers (72), Orlando (67), Philadelphia (67), New Orleans (64) |
| transition (PBP) | Toronto (75), Indiana (75), Oklahoma City (74), San Antonio (65) |

The cells are populated by sensible, recognisable teams — the profiles are
measuring real basketball style. They simply do not locate market error.

## REPRODUCTION — do the exceptions survive?

| quantity | within-season H1 -> H2 | season t -> t+1 |
|---|---|---|
| market residual | +0.0655 | +0.0409 |
| beta(D_M) | −0.0451 | −0.0751 |
| offensive bias | −0.2190 | — |
| defensive bias | −0.2567 | — |

Nothing persists. The correlations are zero or negative in every case.

## What the atlas shows

Not "no significant effect" — **no structure.** Across three independent
dispersion checks (team calibration, team beta, team offensive/defensive bias)
the observed spread across 120 team-seasons is **smaller than pure sampling
noise**, so the empirical-Bayes shrinkage weight is exactly zero. There is no
team-level signal to shrink toward.

The market is not merely unbiased on average. It is unbiased **team by team**,
and the apparent extremes fail to reproduce in the next block of games.

## Honestly outstanding

eFG and rim-rate surfaces are not built (rim rate needs shot-location data beyond
the current PBP extract), and roster continuity is not in the style profiles.
Neither changes the structural obstacle recorded in `MARGIN_ERROR_ANATOMY.md`:
two-thirds of margin error is shooting efficiency, and shooting is binomial
(phi 0.9883, rho −0.00035, measured).
