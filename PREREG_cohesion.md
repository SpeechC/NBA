# PREREG — LINEUP COHESION

Written 2026-08-26, BEFORE any outcome variable was touched. Only the
feature-structure checks in §2 were run first (`cohesion_build.py`,
`cohesion_structure.py`); they read lineup stints and closing market columns —
no score, no `dev`.

## 0. The claim

The market watches **who is available** with great intensity — `PREREG_injury`
Hypothesis B confirmed that the line moves on intraday status changes. What no
one computes is **how much the available group has actually played together.**

Pairwise familiarity is derivable entirely from public play-by-play, but it
requires accumulating co-minutes across every five-man unit of every prior
game. It appears on no screen and in no injury report. That makes it a
candidate *derived-quantity omission* — the same shape as `CrewShock`, where
the input was public and the computation was not performed.

**This is not an injury test.** It conditions on no injury variable, uses no
status report, and makes no claim about absences. It is a property of the
minutes distribution. Stated explicitly because it would otherwise read as a
rescue of a confirmed branch, which the standing rules forbid.

## 1. Data and the split, which availability forces

Lineup stints: `/mnt/c/NBA2/out/pbp_lineups_all.parquet` (2.02M deduplicated
stints, 9,801 games). Outcomes and lines: `dfMaster_OT_2017-2026.csv` via
`read_master()`. **Source file never modified.**

The stint panel covers **2017-18 … 2024-25 only**. 2019-20 is absent from the
master. So the split used by `PREREG_quote_path` / `_tip_time` / `_national_tv`
(holdout 2024-25 + 2025-26) is **not available here**:

```
development   2017-18, 2018-19, 2020-21, 2021-22, 2022-23   (5 seasons)
holdout       2023-24, 2024-25                              (2 seasons)
```

This deviation is **forced by data availability, not chosen**, and is fixed now
so it cannot be adjusted after seeing a result.

## 2. Construction and Stage-0 gates — RESULTS IN HAND

**Prior-only by construction.** "Tonight's lineup" is same-game information and
is never used. For team T entering game t:

```
expected rotation  = top 10 players by minutes over T's previous 5 games,
                     weights w_i = share of those minutes
familiarity(i,j)   = co-minutes of i and j, summed over T's games STRICTLY
                     BEFORE t, within season
cohesion(T,t)      = SUM_{i<j} w_i w_j log(1 + familiarity(i,j))
                     ------------------------------------------
                              SUM_{i<j} w_i w_j
```

| gate | result | verdict |
|---|---|---|
| CONTENT — cohesion games joined to master | 8,049 / 8,058 | **PASS** |
| CONTENT — team rows per game | exactly 2.00 (22 games, 0.27%, dropped) | **PASS** |
| RANGE — cohesion | 1.754 – 6.909, 0 NaN | **PASS** |
| RANGE — rotation size | 10 on 16,063 of 16,116 | **PASS** |
| ERA — mean by season | 5.227 – 5.416, **1.04×** | **PASS** |
| ERA — sd by season | 0.729 – 0.769, **1.04×** | **PASS** |

### A build error caught at Stage 0

Keying each five-man unit off a single slot's modal season team mislabels every
game a **mid-season-traded** player spent with his other club, producing 2.46
team-rows per game instead of 2. Resolved by taking the modal label over every
slot of every stint in a game-side. A `!= 2 rows` gate now enforces it.

### The confound that dominates this feature

```
corr(cohesion, gameno) = +0.7501

games 1-10   mean 3.899      games 40-60   mean 5.744
games 10-20  mean 4.925      games 60-82   mean 5.858
games 20-40  mean 5.432
```

Cohesion rises mechanically as a season progresses. Removing the game-number
mean cuts its sd from 0.747 to **0.353 — over half the variance is the season
clock.** Any test that does not absorb this non-parametrically is testing the
calendar.

**Controls, fixed here:** **10 game-number bin dummies per side** (absorbing the
clock without assuming a shape), plus `closing_total` and `|closing_spread|`.

## 3. Targets

```
dev_s = actual_margin + closing_spread     (home side)   PRIMARY
dev   = actual_total  − closing_total                    secondary
C_diff = cohesion_home − cohesion_away
C_sum  = cohesion_home + cohesion_away
```

## 4. Predictions

**PRIMARY P1 — spread, one-sided.** A more cohesive team executes better; that
is unambiguous in *direction* on the margin.

```
dev_s ~ C_diff + gameno bins (both sides) + closing_total + |closing_spread|
PREDICTED:  beta_C_diff > 0     (one-sided)
```

Pass requires **both**: P1a Freedman-Lane p < 0.05 one-sided (5,000 reps); and
P1b the §5 incremental bar.

**Why the spread and not the total is primary.** On the total the direction is
genuinely ambiguous and I will not pretend otherwise: familiarity plausibly
improves offensive timing and spacing (→ higher total) *and* defensive
communication and rotations (→ lower total), and the defensive channel is if
anything the more communication-dependent of the two. Choosing a direction
there would be a coin flip dressed as a hypothesis.

**SECONDARY P2 — total, TWO-SIDED**, precisely because the direction is
ambiguous. `dev ~ C_sum + controls`. Reported two-sided; a significant result
in either direction is reported as such and as *not* pre-directed.

**P3 — POSITIVE CONTROL, no market involved.** Does cohesion predict on-court
performance at all?

```
actual_margin ~ C_diff + controls        PREDICTED: > 0
```

**This gates the interpretation of P1.** If P3 fails, the feature does not
measure anything real and a P1 null says nothing about market pricing — it
says the construct is empty. That distinction is fixed now. (The `ref_fatigue`
branch failed on mechanism while its positive control passed; here the control
is registered in advance rather than added afterwards.)

**P2 and P3 cannot rescue P1.** If P1 fails, the branch closes.

## 5. Incremental test

Fit on development, score **once** on holdout:

```
model A   dev_s ~ gameno bins + closing_total + |closing_spread|
model B   model A + C_diff
```

**Bar: model B's holdout OOS R² exceeds model A's.**

## 6. Inference

- **Freedman-Lane** permutation of the control-residualised target, 5,000 reps,
  within-season blocks — plain regressor permutation is not used, per the
  defect established in `PREREG_tip_time`.
- Three predictions declared; phantom-book 95th-percentile bar reported for P1.
- No same-game information enters any regressor: rotation weights come from the
  previous 5 games, familiarity from games strictly before t.

## 7. Detection burden

Reported with the **corrected** conversion established in
`PREREG_national_tv`: points → hit-rate edge is `φ(0)/σ = 0.3989/σ`, **not**
`1/σ`. MDE reported whether or not P1 passes, so a null is separable from low
power.

## 8. Known limitations, stated in advance

- Familiarity resets at each season boundary. Continuity carried across
  off-seasons is real and is **not** captured; early-season cohesion is
  therefore understated for stable rosters.
- `log(1+·)` compresses large co-minute totals. The transform is fixed in
  advance; no alternative will be tried after seeing a result.
- ROT_W = 5 and TOPN = 10 are fixed in advance and will not be tuned. They are
  conventional rotation figures, not selected on any outcome.
- Cohesion correlates with roster stability, which correlates with team
  quality. `dev_s` residualises the market's own view, which is the best
  available answer and not a complete one.
- 2019-20 and 2025-26 are unavailable, so this branch has less holdout than its
  siblings.

---

# RESULT — run 2026-08-26. Verdict: **P1 PASSES both conditions.**

Development n = 5,662 games; holdout n = 2,383.

## P3 — positive control PASSES first (this gates everything)

```
actual_margin ~ C_diff:   +6.2298  (t = +14.83)   FL p1 = 0.0002
```

Cohesion strongly predicts on-court performance. The construct measures
something real, so a P1 result is interpretable as a statement about **pricing**
rather than about an empty feature.

## P1 — PRIMARY, PASSES

```
dev_s ~ C_diff + gameno bins + closing_total + |closing_spread|
beta = +0.9181   (t = +2.36)   FL sd 0.3868   p1 = 0.0100
```

Correct sign, and **p = 0.0100 clears the Bonferroni bar for 3 declared
predictions (0.05/3 = 0.0167).**

### §5 incremental — B wins pooled AND in each holdout season separately

| holdout | n | A | B (+C_diff) | B − A |
|---|---|---|---|---|
| pooled | 2,383 | −0.003212 | −0.001548 | **+0.001664** |
| 2023-24 | 1,193 | −0.005466 | −0.005155 | +0.000311 |
| 2024-25 | 1,190 | −0.000990 | +0.002034 | +0.003024 |

**Both P1a and P1b are met. P1 passes.**

### The holdout coefficient is larger than development

```
development  +0.9181 (t = +2.36)
HOLDOUT      +1.2801 (t = +2.27)   <- independently significant, never fitted on
```

Per season: **6 of 7 positive** (2017-18 +1.64, 2018-19 −0.64, 2020-21 +2.06,
2021-22 +1.44, 2022-23 +0.28, 2023-24 +0.57, 2024-25 +2.18).

## Robustness — the parameter sweep, which is where mining would show

`ROT_W` and `TOPN` were fixed in advance, but they are researcher degrees of
freedom, so the grid was swept afterwards to see whether the registered cell is
special:

| ROT_W | TOPN | DEV beta | t | HOLDOUT beta | t |
|---|---|---|---|---|---|
| **5** | **10** | **+0.9181** | **+2.36** | **+1.2801** | **+2.27** |
| 3 | 10 | +0.9339 | +2.70 | +1.1450 | +2.31 |
| 10 | 10 | +1.2136 | +2.56 | +1.1198 | +1.66 |
| 5 | 8 | +0.8264 | +2.22 | +1.3408 | +2.49 |
| 5 | 12 | +0.9527 | +2.49 | +1.0289 | +1.90 |

**Positive in 5/5 cells on development and 5/5 on holdout.** The pre-registered
cell ranks **4th of 5** on the development coefficient — it is *not* the best
cell, which is the signature one would not see from a mined parameter choice.

## P2 — total: null, as the pre-registered ambiguity anticipated

```
dev ~ C_sum:   −0.3456  (t = −0.87)   p2 = 0.3965
```

§4 declined to pre-direct this because familiarity plausibly improves offensive
timing *and* defensive communication, which push the total opposite ways. The
null is consistent with those channels offsetting. **This is not a post-hoc
explanation — the ambiguity is stated in §4, written before the run.**

## How much does the market miss?

```
cohesion -> actual margin      +6.2298     (P3, the full effect)
cohesion -> dev_s              +0.9181     (P1, the unpriced remainder)

market prices  85.3%   misses  14.7%
```

Contrast `CrewShock`, where the market prices 4.6%. This is a **far more
efficient market response** — a modest under-reaction, not a blind spot. That
is what makes it credible.

## §7 — real, small, and NOT verifiable by betting record here

```
1 SD of C_diff = 0.449
observed effect  +0.412 pts (dev)  /  +0.575 pts (holdout)
MDE (95%)         0.340 pts
edge             1.27pp over the 52.38% break-even  ->  53.65% hit rate
n to verify      12,217 games
```

The effect clears the MDE, so this is a detection and not a power artefact. But
**1.27pp is an average across all games, and confirming it from a betting
record would take 12,217 games** — more than the entire sample. It is
detectable in regression and not verifiable in a P&L within anything we hold.

Any attempt to concentrate the edge by betting only high-`|C_diff|` games would
be a post-hoc threshold search, which §4 forbids. It is not done here.

## Disposition — PASSES, with the claim stated at its defensible width

This is the first candidate in this series to pass. The defensible claim is:

> The closing spread incorporates roughly 85% of a measurable lineup-familiarity
> effect and leaves roughly 15% unpriced, worth about 0.4–0.6 points of margin
> per standard deviation of the home-away cohesion difference.

It is **not** established that this is tradeable at scale, that the effect is
stable going forward, or that it survives transaction costs beyond the −110
already embedded in the break-even. 2018-19 is negative, and one negative
season in seven is what a real but modest effect looks like — and also what a
fragile one looks like.

**Next step, not taken here:** a proper forward test. 2025-26 lineup data does
not exist in this store and 2026-27 has not been played. Nothing should be
traded on this before the feature is frozen, written down with its exact
construction, and run forward on data that does not exist yet.

---

# P&L ADDENDUM — run 2026-08-26. **The finding does not trade.**

## The strategy loses money in every form and every period

Rule: bet the side with higher prior-only cohesion. $100/game at −110
(break-even 52.381%). No threshold, no sizing — §4 forbids threshold selection.

| period | bets | hit | profit | ROI | vs break-even |
|---|---|---|---|---|---|
| development (5 seasons) | 5,557 | 50.46% | −$20,391 | −3.67% | −1.92pp |
| holdout 2023-24 | 1,171 | 49.96% | −$5,418 | −4.63% | −2.42pp |
| holdout 2024-25 | 1,165 | 49.61% | −$6,155 | −5.28% | −2.77pp |
| **holdout pooled** | **2,336** | **49.79%** | **−$11,573** | **−4.95%** | −2.59pp |
| full sample | 7,893 | 50.26% | −$31,964 | −4.05% | −2.12pp |

The naive rule is partly betting favourites (`corr(C_diff, sp_close) = −0.40`).
Residualising `C_diff` on the controls — the form the coefficient actually
describes, fitted on development, applied to holdout — does not save it:

| residualised rule | bets | hit | profit | ROI |
|---|---|---|---|---|
| development | 5,557 | 50.13% | −$23,827 | −4.29% |
| holdout | 2,336 | 50.51% | −$8,327 | −3.56% |

Holdout 95% CI [48.49%, 52.54%], z = −1.80 against break-even.

The |C_diff| quintiles are non-monotone — +0.33%, −8.80%, **−12.96%**, −7.61%,
+4.32% — which is noise, not dose-response. A real tradeable edge rises with
signal strength.

## AN ERROR IN §7 THAT I MUST CORRECT

§7 reported "1.27pp edge over the 52.38% break-even → 53.65% hit rate." **That
is wrong.** The density conversion gives the probability shift **from 50%**, so
0.412 points → **51.27%**, which must then be *compared* to break-even, not
added to it. The correct reading is 51.27% against a required 52.38% —
**already unprofitable, by 1.11pp.**

Restated correctly:

```
break-even at -110                     52.381%
required shift from 50%                 2.381pp
density                                 3.073pp per point of spread edge
POINTS OF EDGE REQUIRED                 0.775
points of edge observed                 0.412 (dev) / 0.575 (holdout)
```

**The effect is roughly half to three-quarters of what −110 demands.** It never
implied a profitable strategy; I mis-stated the arithmetic, and the P&L above
is what that error was hiding.

## Why it fails even beyond the arithmetic — the effect is in the tail

Splitting by the realised margin (outcome-conditioned, so **diagnostic only**,
never a predictive claim):

| where | n | beta | t | mean abs dev_s |
|---|---|---|---|---|
| near the number | 2,694 | +0.0636 | +0.52 | 2.5 |
| middle | 2,669 | +0.1128 | +0.30 | 8.5 |
| **blowout tail** | 2,682 | **+2.8247** | **+3.28** | 19.7 |

**The entire effect lives in games that were already decided.** Cohesion widens
blowouts; it does not move covers. Directly:

```
cover-probability ~ C_diff:   development +0.0311 (t = +2.07)
                              holdout     +0.0164 (t = +0.79)   <- not significant
```

This is the same structural lesson this program recorded for overtime and
garbage time: **a mean effect overstates the betting edge when the effect sits
in the tail rather than at the line.**

## Revised disposition

`PREREG_cohesion` P1 **passes on its registered terms** — `C_diff` genuinely
predicts `dev_s`, on holdout, robust across the parameter grid. That result
stands and is not withdrawn.

But the registered target was a **continuous margin residual**, and a
coefficient on points is not an edge on covers. **There is no strategy here.**
The correct summary is:

> Lineup familiarity has a real, out-of-sample, unpriced effect on margin of
> about 0.4–0.6 points — which is below the ~0.78 points −110 requires, and
> which is concentrated in blowouts where it cannot be monetised.

Nothing is to be traded on this. The feature's remaining value is as a
**candidate control** in other models, not as a signal.

**A process lesson, recorded:** the economic translation should be computed at
the same time as the statistical one, not after. Had §7's arithmetic been done
correctly, this branch would have been reported as unprofitable at the moment
P1 passed.
