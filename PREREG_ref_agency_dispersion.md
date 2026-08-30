# PREREG — REFEREE AGENCY IN THE Q4 DEFICIT RESPONSE (dispersion design)

Written 2026-08-30. **NOT YET RUN.** Only the structural checks in §3 have been
executed — join rate, games per official, within-official spread of the
regressor, and the implied per-official standard error. No slope has been
estimated for any official and no dispersion statistic computed.

## 0. The question this exists to answer

`PREREG_foul_q4` established that the Q4 comeback effect runs through free
throws — `dFTA ~ D` at **+0.04747 (t = +10.05)** on the conservative panel — and
then refused to attribute it, because three mechanisms produce the same
signature and that design separated none of them:

1. residual intentional fouling
2. bench foul-proneness in blowouts
3. shot location

**"Within-crew" as ordinarily meant would not help.** Crew fixed effects remove
referee variation; they do not isolate it. The identifying idea is the
opposite — **exploit dispersion**:

> If the deficit→free-throw response is produced by **players and tactics**, it
> must be **the same for every official**. Benches empty, teams drive, clocks
> get stopped — none of that depends on who is officiating.
>
> If **referees** have agency in it, the response **varies across officials**.

So the estimand is not a mean. It is a **variance**: does the per-official
deficit slope disperse beyond sampling noise?

**This is what makes the design identifying.** Bench foul-proneness, shot
location and end-game tactics all act on every crew alike, so they contribute
to the *level* of the pooled slope and **nothing to its dispersion**. Only
referee agency does that.

## 1. Relationship to the frozen CrewShock work — read before running

This **reuses CrewShock's logic on a different quantity**. CrewShock estimates
each official's idiosyncratic **level** of foul propensity; this estimates each
official's **slope** with respect to game state. They are different statistics.

**The frozen estimator is not touched.** `ref_features.csv`,
`ref_features.py`, k = 78.247119, N = 60, MINN = 25 and the 0.8682 threshold
are read-only and are not used here at all — only the officials' names are
taken from `ref_features.csv`.

**No tradeable object may be built from this result.** If P1 passes, the
tempting next step is a pregame-knowable crew-responsiveness signal, since
assignments post at 9am. That is the "combine with CrewShock" family the
standing rules govern, and it requires its own pre-registration on data not
used here. It is **not authorised by this document**.

## 2. This is still a mechanism test

No line, no `dev`, no vig, no P&L. `QUARTER_WINNER_AUDIT` closed the economics
separately — the derivative instruments quoted 15–30c against a 3–6c edge.
Nothing here reopens that.

## 3. Data and Stage-0 — RESULTS IN HAND

Panel: `foul_q4.build(drop_last3=True)` — the **conservative** version with the
final 3:00 excluded. That choice is **fixed in advance** on the ground that
`PREREG_foul_q4` showed the last three minutes carry residual intentional
fouling that halves the effect; using the full-Q4 panel here would import a
known contaminant.

Officials from `ref_features.csv` (`ref1/ref2/ref3`), read-only.

| check | result |
|---|---|
| games in panel | 8,083 |
| join to officials | **8,083 / 8,083 = 100.0%** |
| official-games | 24,249 |
| distinct officials | 103 |
| games per official | median **273**, p10 22, p90 394 |
| officials with ≥ 150 games | **70**, covering 91.8% of official-games |
| within-official sd(D) | median **8.49** vs pooled **8.50** |

**The regressor varies fully inside each official** — within-official sd(D) is
indistinguishable from the pooled figure, so every official sees the whole
range of deficits. That is what makes a per-official slope estimable at all.

**MING = 150 games is fixed here**, giving 70 officials and 91.8% coverage.

### The power problem, stated before the run

```
sd(dFTA) 3.93   median within-official sd(D) 8.49   median n 273
implied se(beta_i)  ~  0.0255
pooled slope        =  0.04747
=> the per-official standard error is 54% of the effect being measured
```

**This test can only detect LARGE heterogeneity.** With 70 officials and a
sampling variance of ≈0.00065 per slope, a true dispersion sd below roughly
**0.015** — officials differing by less than ~±30% of the mean response — is
not resolvable. §6 fixes how that is reported.

## 4. Construction

For each official *i* with ≥ 150 games, over that official's games:

```
beta_i  from   dFTA ~ D + dFGA          (within-official OLS)
```

`dFTA` and `dFGA` are oriented trailing-minus-leading exactly as in
`PREREG_foul_q4`; `dFGA` remains the shot-volume control. The statistic is

```
V_obs = Var_i(beta_i)          weighted by games, over the 70 retained officials
```

## 5. Predictions — fixed

**P0 POSITIVE CONTROL.** The pooled slope reproduces on this panel at
`dFTA ~ D | dFGA` ≈ +0.047. Also report **mean D by official** — if assignment
is balanced, officials should not differ materially in the deficits they see.
A large imbalance is a confound and is reported before anything else.

**P1 PRIMARY — dispersion of the free-throw slope.**

```
V_obs(dFTA)  vs  a null from PERMUTING OFFICIAL LABELS WITHIN SEASON
PREDICTED: V_obs above the 95th percentile of the permuted null
```

5,000 permutations. Under the null that referees have no agency, which
official is assigned is irrelevant to the deficit slope, so shuffling labels
preserves every game-level fact except referee identity. **This is the same
label-permutation logic as CrewShock's exogeneity battery**, applied to a slope
rather than a level.

**P2 PLACEBO — and it is the test's spine.**

```
V_obs(dNTO)  vs  its own permuted null
PREDICTED: NOT above the 95th percentile
```

Bad passes and lost balls require **no whistle**. A referee cannot cause them.
If per-official dispersion appears **here too**, the dispersion statistic is
picking up something other than referee agency — assignment patterns, opponent
quality, era — and **P1 is void regardless of its own p-value.**

**P2 is not a secondary result. A P1 pass with a P2 pass is a FAILED test.**

## 6. Fixed readings

| P1 | P2 placebo | verdict |
|---|---|---|
| above null | clean | **referee agency supported** |
| above null | **also above null** | **VOID** — the statistic is confounded, not a finding |
| not above | clean | no detectable agency **at this power**; report the MDE, do not claim absence |
| not above | also above | void |

**On a null result:** §3 fixed that dispersion below ~0.015 is unresolvable.
A P1 null will therefore be reported as **"no heterogeneity detectable above
±30% of the mean response"**, never as "referees do not have agency."

## 7. What this design CANNOT do

**Dispersion establishes agency, not apportionment.** Even a decisive P1 does
not say what share of the +0.047 pooled slope is refereeing. Showing that
officials differ is not the same as measuring how much of the average effect
they cause, and no share will be quoted from this test.

Answering the apportionment question needs a different instrument — plausibly
an assignment-based one, and it does not exist in this data.

## 8. What is NOT permitted

MING = 150 is fixed; no re-thresholding to change the number of officials. The
panel is the last-3:00-excluded one; the full-Q4 panel may be reported only as
a labelled robustness and never as the primary. No substitution of crews for
officials. No alternative outcome in place of `dFTA`. If P1 fails or P2 voids
it, **the referee-versus-personnel question closes as unresolved on this data**,
and `PREREG_foul_q4`'s disposition stands: residual localised to free throws,
attribution not identified.

## 9. Prior

`CLOSING_REFEREE` established that officials differ substantially in foul
*level* — that is CrewShock, and it is well evidenced. Whether they also differ
in *responsiveness to game state* is a strictly stronger claim and has no
support in this repository. Against it: the pooled effect is large and smooth
across the deficit range, which is more consistent with a mechanical
player/tactics story than with 103 officials each choosing a slope. **I expect
P1 to fail at this power**, and the value of running it is that a clean null
with a stated MDE closes a question that is currently open-ended.

---

# RESULT — run once, 2026-08-30. **No individual referee agency detected. Placebo clean.**

24,249 official-games, 103 officials, 70 retained at MING = 150.

## P0 — passes, and assignment is well balanced

```
pooled dFTA ~ D | dFGA   = +0.04709          (prereg expected ~ +0.047)
BALANCE: mean D by official, 70 officials
         range 10.43 - 12.56   sd 0.487   pooled mean 11.39
```

Officials see materially the same deficits. There is no assignment confound to
explain away a dispersion result — in either direction.

## P1 PRIMARY — NOT above the null, and not marginally

```
officials 70    mean slope +0.04759    observed slope sd 0.02296
V_obs        5.270e-04
null median  5.682e-04      95th pct  7.434e-04
p = 0.6637
```

**The observed dispersion is BELOW the noise-only expectation** — observed slope
sd 0.02296 against an implied noise-only 0.02384, so the excess-variance point
estimate is **exactly zero**. This is not a borderline null. Officials' deficit
slopes are indistinguishable from all being the same number plus sampling error.

## P2 PLACEBO — clean, which is what makes P1 readable

```
dNTO:  V_obs 1.036e-04   null median 1.020e-04   p = 0.4617
```

The statistic does **not** manufacture dispersion on a channel referees cannot
touch. Per §5, a placebo firing would have voided P1 regardless; it did not.

## Verdict, per §6

**"Not above / clean" → no agency detectable at this power.** Reported as
`§6` requires: **no heterogeneity above roughly ±30% of the mean response**, and
**not** as proof that referees lack agency.

The result is nonetheless stronger than the minimum that wording implies. A
merely-insignificant result would leave the point estimate leaning; here it does
not lean at all — observed variance sits *at or below* the pure-noise floor.

## THE LIMITATION THAT MATTERS MOST, and it is not the power

**A uniform league-wide officiating norm would produce exactly this null.**
Dispersion detects officials differing *from each other*. If every official
applies the same game-state adjustment — a league standard rather than 103
individual choices — the between-official variance is zero and this test is
blind to it.

So the null rules out **heterogeneous individual discretion**. It does not rule
out **refereeing** as such. That distinction was implicit in §7's
"agency, not apportionment" and is now stated explicitly.

## What this does to the Q4 decomposition

| channel | share of +1.65 | status after this run |
|---|---|---|
| turnovers | 22.2% | clean |
| free throws | 43–84% | real; **affirmative case for individual refereeing removed** |
| everything else | remainder | untested |

The free-throw channel stands. What has changed is that the three mechanical
candidates `PREREG_foul_q4` listed — residual intentional fouling, bench
foul-proneness, shot location — are now the **better-supported** explanations,
because the one story that predicted between-official variation produced none.

## It does NOT contradict CrewShock — and mildly supports it

CrewShock says officials differ in foul **level**; this says they do not differ
in **responsiveness to the scoreboard**. Both can hold, and together they
describe an official who carries a persistent personal whistle rate and applies
it **uniformly regardless of the score**.

That is the behaviour `CLOSING_REFEREE`'s exogeneity battery already assumed —
a fixed propensity rather than a game-state response — and this is independent
evidence for it, from a test that could have embarrassed it and did not.

## Disposition

Per §8, the referee-versus-personnel question **closes as unresolved on this
data**, with the affirmative referee case weakened. `PREREG_foul_q4`'s
disposition stands unchanged: residual localised to free throws, attribution
not identified. No tradeable object was built and none is authorised.

**Prior check:** §9 predicted P1 would fail at this power and said the value
would be a clean null with a stated MDE. That is what happened. Recorded
because the prediction was made before the run and is one of the few in this
program to come out right.
