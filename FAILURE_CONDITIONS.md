# WHEN THE MODEL FAILS — worst-decile diagnosis

Held-out 2022+, n = 4,717, worst decile = 472 games with |error| >= 4.85.
`failure_analysis.py`.

## THE FAILURE CONDITION IS INJURY BURDEN — and only that

Worst vs rest on every observable:

| variable | worst | rest | diff | t |
|---|---|---|---|---|
| **injury VORP (sum)** | **17.346** | **11.583** | **+5.763** | **+7.24** |
| opening total | 227.515 | 228.587 | −1.072 | −2.41 |
| actual game pace | 99.291 | 98.864 | +0.427 | +1.76 |
| days into season | 85.775 | 89.993 | −4.218 | −1.58 |
| \|spread\| | 6.021 | 6.330 | −0.309 | −1.64 |
| min rest | 1.034 | 1.031 | +0.003 | +0.37 |

**One discriminator dominates.** Failure rate is monotone in injury burden:

```
burden quintile   mean VORP   mean err   mean |err|   worst-rate
1                      1.28     +0.612        2.095        6.1%
3                      9.57     +0.176        2.139        6.9%
5                     29.19     -1.339        2.849       18.1%
```

**6.1% -> 18.1%, a 3x increase in failure rate.**

## What it is NOT

```
stale state       worst-decile error autocorrelation +0.16 (vs +0.11 overall) -> ONE-OFF EVENTS
extreme ratings   sum|team ratings| worst 11.433 vs rest 11.425 -> identical
league regime     daily worst-rate autocorrelation +0.0413 -> no clustering in time
team-specific     no team materially over-represented
pace / rest / spread / total level   all |t| < 2.5
```

Partial exception: **the first 10 days of a season fail at 18.2%** versus 8.6-10.5%
later — a state-initialisation problem, separate and separately fixable.

## The signature says it is a GAME-level, DIRECTIONAL miss

```
corr(home-side error, road-side error)   worst +0.5193   rest -0.1309
worst-decile mean signed error           -1.573   (only 39.4% positive)
```

Both teams' implied points move down **together**, and we **over-predict**. That is
what a roster-availability shock looks like: it marks the whole game down, not one
side, and it is the market that moves, not us.

## THE GENERALIZATION THAT BREAKS

**The model assumes a team's latent state describes the team that will actually
play.** It is a slowly-updating rating over a nominally-constant roster. When a
material share of that roster is unavailable, the assumption fails — and it fails
in two separable ways.

### Component 1 — SYSTEMATIC BIAS (correctable)

```
err ~ injury VORP:   beta -0.0716 (t=-14.58)
```

**Per net point of absent production, the market marks down 0.072 more than we
do.** At the worst-decile burden of 17.35 that is **1.24 points of systematic
under-adjustment**. We know absences matter; we under-weight them.

### Component 2 — WIDENED DISPERSION (not correctable by a scalar)

```
                        mean err    sd(err)   |err|
top-decile burden        -1.685      3.581    3.001
bottom-decile burden     +0.583      2.541    2.091
                     bias -2.268   spread +1.040
```

**High-injury games are both systematically mispriced by us AND intrinsically
more variable.** The bias is a level shift a coefficient can absorb; the widened
spread is the variance across *which* 17 points are missing — a scalar burden
cannot distinguish losing one star from losing three rotation players.

### And that is why a linear correction barely helps

```
mean |err|          2.335 -> 2.266   (3% better)
worst-decile |err|  6.762 -> 6.268   (7% better)
R2 of the injury correction on the error: 0.0627
```

## This RECONCILES the earlier puzzle

Stage F found injury data worth only +0.006 R2 on the opener, yet injury burden
is by far the strongest failure discriminator (t = +7.24). Both are true:

- **injuries identify WHERE the model fails** — decisively;
- **a scalar injury measure fixes only the BIAS**, which is the smaller component.

The market does not price a burden. It prices *specific absences* — who, what
role, what minutes, which replacement, against which opponent. Our VORP is the
correct concept collapsed to one number, and the collapse is where the accuracy
goes.

## Actionable consequence

**The next gain is not a better burden statistic; it is a per-absence model.**
Value the individual absence in matchup context rather than summing team-level
VORP. That is the only route identified that addresses Component 2, and Component
2 is where the worst-decile error actually lives.

Failing that, the honest operating rule is: **the model is materially less
reliable when combined injury VORP exceeds ~16 points** (quintiles 4-5), which is
40% of games and carries 29% of them into the worst decile.
