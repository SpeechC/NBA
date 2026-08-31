# MONEYLINE — 20-GAME BLOCK ATLAS AND PROSPECTIVE CARRY-FORWARD (2026-08-30)

The last team-specific diagnostic. Half-season persistence near zero does not rule
out a six-week window in which the model is mis-estimating a team before the state
engine adapts. Four non-overlapping ~20-game blocks per team-season; block length
not optimised; no overlapping windows.

**480 blocks (120 team-seasons x 4), mean n = 19.0.** Full rows in
`moneyline_block_error_atlas.csv`.

## The one non-zero shrinkage weight in this entire investigation

```
EB shrinkage weight   market residual   0.0000
EB shrinkage weight   beta_D            0.0000
EB shrinkage weight   contrib           0.4386   <-- real block-level structure
```

`contrib` is the team's own contribution to margin error in points,
`sP/100 * (e_off - e_def)`. At the 20-game scale it carries genuine signal: **teams
really do surprise the model for weeks at a time.** That is the premise the whole
exercise needed. The question is whether it survives one block forward.

## TEST 1 — block -> block+1 persistence

`q(b+1) = alpha + rho*q(b)`, n = 360 transitions:

| quantity | rho | se | t |
|---|---|---|---|
| market residual | −0.0424 | 0.0515 | −0.82 |
| beta_D | +0.0018 | 0.0469 | +0.04 |
| offensive bias | −0.0976 | 0.0524 | −1.86 |
| **defensive bias** | **−0.1239** | 0.0521 | **−2.38** |
| **pace bias** | **−0.1060** | 0.0504 | **−2.10** |
| contrib | −0.0699 | 0.0524 | −1.33 |

By individual transition:

```
contrib   block 1->2  rho -0.0742 (t -0.86)   2->3  -0.1887 (t -2.00)   3->4  +0.0438 (t +0.48)
off_bias  block 1->2  rho -0.1908 (t -1.98)   2->3  -0.1035 (t -1.21)   3->4  -0.0296 (t -0.31)
```

**Every quantity is negative except beta_D, which is zero.** Two reach |t| > 2.

## TEST 2 — strictly prospective carry-forward (the central test)

State frozen at the end of block `b`, applied only to games in block `b+1`.
`Correction_g = S_H,prev - S_R,prev`. **n = 2,309 games** with a prior-block state
for both teams.

```
(ActualMargin - M_book) ~ Correction        beta +0.0247  se 0.1366  t +0.18
Phi^-1(P) = Phi^-1(p_mkt) + beta*Correction beta -0.00502 se 0.01393 t -0.36
```

**"If I had noticed the team error after the previous 20 games, could I have made
money from it during the next 20?" — No.**

## TEST 3 — does prior-block error tell us when to trust D_M?

```
Phi^-1(P) = Phi^-1(p_mkt) + b1*D_M + b2*D_M x S_prior
   b1 (D_M)          -0.01335  se 0.00629  t -2.12
   b2 (INTERACTION)  -0.00489  se 0.00365  t -1.34
```

The interaction is null. `b1` reaches |t| > 2 but is **negative**, and its economic
size is 2.08pp at a 1sd disagreement against a 2.09pp break-even — at the bar,
with the wrong sign, on a 2,309-game subsample where the full-sample estimate is
t = −0.79. Acting on it would require a post-hoc sign flip fitted to the subsample
that produced it.

## What this establishes

Not "teams do not differ." Something sharper, and it is the explanation the whole
moneyline investigation was missing:

**Teams genuinely do surprise the model — the block-level shrinkage weight of
0.4386 says so — but the state estimator adapts continuously at 4.2% per game,
absorbing roughly `1 - 0.958^19 = 56%` of a level displacement across a block.**

That is why team-specific misses are visible after the fact and cannot be turned
into a wager: the estimate is moving through the block, so block AVERAGES display
apparent reversal even though one-game forecast errors are effectively white
(one-step autocorrelation −0.0040, t = −0.38). The negative half-season
correlations reported earlier (−0.219, −0.257) are the same aggregation artefact
at coarser resolution — **not** evidence that the engine overshoots. See the
CORRECTION in `MONEYLINE_IMPULSE_RESPONSE.md`.

## Hierarchy of evidence, as specified

| level | result |
|---|---|
| 1. raw block structure | real — contrib shrinkage weight 0.4386 |
| 2. block b -> b+1 persistence | negative or zero on every quantity |
| 3. prospective prior-block correction | t = +0.18 (margin), t = −0.36 (moneyline) |
| 4. prior-block state x current D_M | interaction t = −1.34 |

Levels 2, 3 and 4 fail. **The "exceptions by current team" hypothesis is
exhausted**, and the moneyline channel is closed on the correct target with the
correct instrument.
