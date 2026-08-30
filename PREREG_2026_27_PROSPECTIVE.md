# NBA Totals 2026-27 Prospective Validation

**Authored by the user, recorded 2026-08-30, BEFORE the 2026-27 season exists
(NBA opens 2026-10-20).** Both hypotheses were discovered on data through the end
of 2025-26.

**No model specification, threshold, sign convention, subgroup definition, or
evaluation metric may be changed using 2026-27 outcomes before the season-level
evaluation is complete.**

---

## PRIMARY HYPOTHESIS 1 — Pace-Gap Outcome Signal

### Signal

For each game compute the pregame model's expected pace `Pace_hat`, and infer the
pace embedded in the bookmaker's opening total holding the model's expected
offensive-efficiency components fixed:

```
PaceGap        = Pace_hat - Pace_book
PaceGapPoints  = PaceGap x (OE_H_hat + OE_R_hat) / 100
```

**Positive `PaceGapPoints` indicates an Over direction; negative indicates
Under.** All model parameters and state-update rules are frozen before observing
2026-27 outcomes.

### Primary statistical endpoint

```
ActualTotal - OpeningTotal = alpha + beta * PaceGapPoints + eps
H1: beta > 0
```

### Economic endpoint

Bet in the sign of `PaceGapPoints`. Report: number of qualifying bets, hit rate,
profit at −110, ROI, average model edge, average closing-line value.

**Break-even hit rate 52.381%. The signal passes the economic gate only if the
realised prospective hit rate exceeds it.** No threshold on pace-gap magnitude
may be introduced after observing prospective data unless separately labelled
exploratory.

### Historical discovery result — NOT part of the test

```
beta ~ 0.250   t ~ 3.72   hit ~ 52.58%   ROI ~ +0.38% at -110
```

Benchmarks only. **They may not be used to alter the prospective specification.**

---

## PRIMARY HYPOTHESIS 2 — Market-Movement Overreaction

```
G = ModelOpeningTotal - ActualOpeningTotal
ActualTotal - ClosingTotal = alpha + gamma * G + eps
H1: gamma < 0
```

Tests whether the market's movement toward the model gap systematically
overshoots the realised outcome.

```
historical: gamma ~ -0.181   t ~ -1.75   95% CI ~ [-0.384, +0.022]
```

**Separate from the pace-gap hypothesis.**

---

## SECONDARY HYPOTHESIS — Low-Total / High-Pace-Uncertainty

Historical exploratory: `OpeningTotal < 220` and the pre-defined high
pace-uncertainty category showed **n ~ 278, Over rate ~ 59%**.

**This arose from an eight-cell post-hoc grid and is explicitly classified as
exploratory discovery, not an established result.**

Frozen before the season: the `< 220` definition, the pace-uncertainty formula,
the high-uncertainty cutoff, and Over as the direction. **Evaluated once on the
full prospective sample. No neighbouring total thresholds, alternative
uncertainty cutoffs, or alternate cells count as confirmation.**

---

## ADDITIONAL REPORTING

Pace-gap results by pre-specified magnitude buckets, **descriptive only**. Also
report `Close - Open` to show how much of the signal the market subsequently
incorporates.

**The primary economic conclusion is determined by `Actual - Open` and realised
profitability. Do not promote a CLV-only result to evidence of betting
profitability.**

## INTERPRETATION RULES

- Significant positive pace-gap coefficient **without** a hit rate above
  break-even establishes outcome information, not a profitable strategy.
- Hit rate above break-even **without** statistical precision is encouraging, not
  conclusive.
- Strongest confirmation requires all four: positive credible
  `PaceGapPoints -> Actual - Open`; hit rate > 52.381%; positive realised ROI;
  positive CLV in the predicted direction.

**2026-27 is a prospective holdout and may not be used for feature selection or
specification tuning before these tests are evaluated.**

---
---

# FROZEN IMPLEMENTATION — added so nothing can drift

## Model constants (all fixed now)

```
TWO-WAY LINE STATE (aggregate model, source of G)
  D2: k=0.30, lambda=0.6, mix=1.00 (quote error only)
  D4: k=0.20, lambda=0.6, mix=0.75 (75% quote error / 25% scoring surprise)
  impH=(open+M)/2, impR=(open-M)/2, M = -(OPENING SPREAD_H)
  update: Off[h]+=k*u ; Def[a]+=k*u   (two-way, opponent-adjusted)
  SAME-DAY BATCHING: predict every game on date D before ANY date-D update

STRUCTURAL LAYER (source of Pace_hat, OE_hat)
  pace HL 5.7, offence HL 8.6, defence HL 7.4, league HL 496 games
  offseason carry 0.42, offence innovation share 0.54
  same-day batching as above

BOOK-IMPLIED PACE
  Pace_book = 100 * (Open - a) / (b * EffSum),  EffSum = OE_H_hat + OE_R_hat
  a, b refit each season on ALL PRIOR SEASONS ONLY, from Open ~ sP*EffSum/100

PACE UNCERTAINTY (secondary hypothesis only)
  features: sd10, |mu5-mu15|, |mu5_H - mu5_R|, sd10_H, sd10_R
    mu5  = prior-only 5-game mean of that team's pace surprise
    mu15 = prior-only 15-game mean
    sd10 = prior-only 10-game sd
  sigma_P = 1.2533 * OOS-predicted |pace error|
  HIGH-UNCERTAINTY = above the MEDIAN of sigma_P within the prospective season
```

Universe: regular season only; both teams must have >= 10 prior games in-season.
Code of record: `pace_signal.py`, `v5_combine.py`, `oracle_attribution.py`.

## POWER — priced now, and two endpoints are UNDERPOWERED

One season is ~1,230 games (~1,150 usable). One-sided alpha 0.05, 80% power, so
MDE = 2.487 x se.

| endpoint | discovery estimate | se at n~1,230 | **MDE** | verdict |
|---|---|---|---|---|
| **H1 pace-gap** | beta 0.250 | 0.110 | **0.274** | **marginally UNDERPOWERED** |
| **H2 overreaction** | gamma −0.181 | 0.166 | **0.414** | **badly UNDERPOWERED** |
| **Secondary <220** | 59% on n~278 | ~4.9pp on n~104 | ~12pp | **UNDERPOWERED** |

**Consequences, fixed now:**

1. **H1** — a null is expected roughly half the time even if the effect is real
   at its discovered size. **A non-significant positive beta with a hit rate
   above 52.381% is a PASS on the economic gate and an "underpowered" on the
   statistical one**, and must be reported as both.
2. **H2** — one season CANNOT resolve it. `GAP_TO_OUTCOME` computed that ~4,004
   games are needed and 3,181 are held. **Pre-committed here: H2 is evaluated on
   2026-27 alone as registered, AND the pooled 2022-2027 estimate is reported
   alongside as the properly-powered read.** Pooling is declared now, before any
   2026-27 data exists, so it cannot be chosen after seeing the result.
3. **Secondary** — ~104 games gives a ±12pp interval. **It cannot confirm 59%.**
   It can only fail to contradict. Registered as such.

## Fixed readings

| H1 statistical | H1 economic | verdict |
|---|---|---|
| beta > 0, credible | hit > 52.381% | **CONFIRMED** — proceed to a sizing prereg |
| beta > 0, credible | hit <= 52.381% | outcome information, NOT tradeable |
| not credible | hit > 52.381% | encouraging, underpowered; carry to 2027-28 |
| beta <= 0 | any | **FAILED** — report as a failed registered prediction, do not reframe |

**H2:** `gamma < 0` credible on the pooled read = overreaction confirmed;
`gamma >= 0` = the market's movement is price discovery, and the "fade the move"
branch closes.

**Standing rule that binds this document:** movement/CLV results may not advance
either hypothesis. This programme has four independent replications of CLV earned
and not converted (injury Hypothesis B, CBB, the Stage 1 emulator, and
`ERROR_ATTRIBUTION` at t=+20.96 movement vs t=+1.88 outcomes).

## What is NOT permitted

No re-tuning of k, lambda, mix, half-lives, carry, or share. No alternative
pace-uncertainty formula. No threshold on `|PaceGapPoints|` introduced post hoc.
No substitution of `Actual - Close` for `Actual - Open` in H1. No promotion of
the secondary cell to primary. No new subgroup added to any family.

---
---

# AMENDMENT — 2026-08-30, BEFORE any 2026-27 data exists

Three analyses run after the original registration (`PACE_VARIANCE_V2`,
`PACE_INTERACTION`, `canonical_spec.py`) require amendments. **All are made now,
with no 2026-27 data in existence.**

## A1. THE SECONDARY HYPOTHESIS IS WITHDRAWN

`<220 x high sigma` is **dropped entirely**, not re-specified. Both candidate
definitions of the uncertainty gate failed on their own terms:

```
5-feature linear sigma_P    predicted terciles give actual sd(u) 4.060/4.047/4.184, F p=0.4313
volx (Vol_H x Vol_R)        NOT structurally necessary: main effects +0.877/+0.883 (t~2.1),
                            interaction +0.1585 (t=+0.41)
```

The original 59% rested on one of eight post-hoc cells. Carrying it forward would
add multiple-testing burden without a functioning mechanism.

## A2. ALL UNCERTAINTY CONSTRUCTS ARE REMOVED FROM THE DECISION RULE

Removed from the betting specification: predicted `sigma_P` weighting, `volx`
gating, volatility-based sizing, and any high/low pace-volatility split.
**They may be reported as diagnostics. They may not affect a bet.**

Basis: the interaction test gave `beta(Gap x Vol) = -0.0429 (t = -0.47)`,
CI [−0.220, +0.134], with non-monotone tercile betas (0.448 / 0.192 / 0.307) and
a bucket grid that reverses sign across gap size. **No empirical basis exists for
modulating a bet on pace volatility.**

## A3. THE CANONICAL IMPLEMENTATION — the ten items, frozen

Two pace-gap estimates were reported during discovery (β 0.2500 t=3.72; β 0.3263
t=3.23). **Cause identified:** the second required 10-game rolling volatility
features to exist, which silently dropped early-season games. **Since volatility
is no longer in the specification, those exclusions are wrong.** The canonical
estimate uses the maximal eligible sample.

```
1  MODEL VERSION     structural latent states: pace HL 5.7, offence HL 8.6,
                     defence HL 7.4, league HL 496 games, offseason carry 0.42,
                     offence innovation share 0.54; SAME-DAY BATCHING (every game
                     on date D predicted before any date-D update).
                     Code of record: oracle_attribution.py / canonical_spec.py

2  BOOK-IMPLIED PACE Pace_book = 100 * (Open - a) / (b * EffSum)
                     EffSum = OE_H_hat + OE_R_hat
                     a, b refit each season by OLS of Open on sP*EffSum/100 using
                     ALL PRIOR SEASONS ONLY. No in-season refitting.

3  SIGNAL           PaceGapPoints = (sP - Pace_book) * EffSum / 100

4  ELIGIBLE GAMES   NBA regular season only. Both teams must have a defined
                    structural state. At least one full prior season must exist
                    for the a,b fit (so 2026-27 is fully eligible). No minimum
                    gap magnitude. No exclusions for injury, rest, or total level.

5  PUSHES           Actual == Open is a PUSH: excluded from the hit-rate
                    denominator, retained in the regression. Historical rate 0.23%.

6  OPENING LINE     `OPENING TOTAL_H` from dfMaster_OT_2017-2026.csv, the single
                    vendor used throughout this programme. `OPENING SPREAD_H` for
                    the implied-points identity.

7  REGRESSION       Actual - Open = alpha + beta * PaceGapPoints + eps, OLS.
                    Report BOTH classical and HC1 robust standard errors.
                    (Discovery: they agree to two decimals.)

8  THRESHOLD        NONE. Every game with a nonzero PaceGapPoints is a
                    theoretical bet, in the sign of the gap. Descriptive
                    magnitude bins are FROZEN at
                    [-inf,-4), [-4,-2), [-2,0), [0,2), [2,4), [4,inf)
                    and are reported for description only.

9  ECONOMIC GATE    Break-even at -110 = 52.381%. ROI = 1.90909*hit - 1.

10 NO TUNING        No specification change may use 2026-27 outcomes before the
                    season-level evaluation is complete.
```

## A4. CANONICAL DISCOVERY BENCHMARKS — reference only

```
n = 3,488 (2023-2025 eligible)      pushes 8 (0.23%)
beta +0.2223   se 0.0650   t +3.42   95% CI [+0.0948, +0.3497]
HC1 robust se 0.0659   t +3.38
bets 3,480   hit 52.59%   ROI +0.39%   se(hit) 0.85pp   CI [50.93%, 54.25%]
```

**The economic result clears break-even by 0.21pp with a confidence interval
that straddles it.** Frozen magnitude bins, hit rate by bin: 52.9 / 54.0 / 49.8 /
52.6 / 53.1 / 52.9 — **essentially flat, with no monotone strengthening in gap
size.** This is expected: a larger gap gives more edge in points, but the
points-to-hit-rate conversion compresses it.

## A5. POWER, RESTATED ON THE CANONICAL SPECIFICATION

```
se at n = 1,230 (one season) = 0.1095      MDE(80%, one-sided) = 0.2723
canonical discovery beta      = 0.2223      ->  UNDERPOWERED
```

**One season cannot confirm H1 at 80% power.** The reading fixed in the original
prereg stands and is now attached to the canonical number: **a non-significant
positive beta with a hit rate above 52.381% is an economic PASS and a statistical
UNDERPOWER, and must be reported as both.**

H2 remains as registered, with the pre-committed pooled 2022-2027 read alongside.

## A6. WHAT IS PROTECTED FROM FURTHER TUNING

The result worth protecting is not the coefficient. It is the **provenance**: the
pace component was isolated by an error decomposition — pace carried 45.4% of
worst-decile squared error — and isolating it **roughly doubled** the outcome
relationship relative to the aggregate model gap (t 1.88 -> 3.42). **That is a
mechanism-first finding, not a feature search.** No further variable may be added
to this hypothesis before 2026-27 is scored.

---
---

# AMENDMENT 2 — 2026-08-30, still BEFORE any 2026-27 data exists

## B1. THREE FROZEN COMPETITORS

Registered now, run unchanged all season, never re-tuned:

```
D          = Pace_hat - Pace_book                      (H1 primary, unchanged)
D*_drift   = D + mu5_hat        mu5 = prior-5 mean pace-forecast error, both teams
D*_profile = D + m_hat(X)       m(X) = ridge(lambda=20) on 22 profile features
```

**`m(X)` frozen specification:** target `dPace`, features
`pace_H/R, trans_H/R, tov_H/R, tovf_H/R, ftr_H/R, ctrl_H/R, mu5_H/R, ewv_H/R,
sP, PrefConflict, ControlConflict, TransComp, TovPressure, StyleDist`,
standardised, intercept unpenalised, chronological fit on all prior seasons.
**No opener, book pace, or |D| may enter `m(X)`.**

**The secondary endpoint is a COMPARISON, not a significance test:**

```
does D*_profile beat D?       does D*_drift beat D?      does profile beat drift?
```

Discovery evidence (n=942, one season): `m(X)` predicts pace error at
**t = +2.62** vs drift's **t = +2.20**, but with both in the model neither
dominates (t = +0.62 / +1.54) and they are **67% collinear**. **If drift matches
profile prospectively, use drift** — simpler and more stable.

## B2. PROBABILITY CALIBRATION — and a caution that matters more than the table

```
logit p_win = +0.0388 + 0.01606 * |E_pace|      E_pace = D x EffSum/100
slope se 0.01155,  t = +1.39                    <- NOT SIGNIFICANT
|E| at which p_win = 52.381%:  3.52 points
```

| \|E\| >= | model p_win | ACTUAL hit | n | % slate | ROI |
|---|---|---|---|---|---|
| 0 | 50.97% | 52.47% | 3,488 | 100.0% | +0.16% |
| 2 | 51.77% | 53.17% | 2,289 | 65.6% | +1.50% |
| 5 | 52.97% | 54.01% | 972 | 27.9% | +3.11% |
| 8 | 54.17% | **56.59%** | 311 | 8.9% | **+8.04%** |

**THE CAUTION.** The hit-rate slope is `t = +1.39` — **not significant** — and the
decile calibration is non-monotone:

```
decile   1      2      3      4      5      6      7      8      9     10
pred  51.09  51.32  51.55  51.79  52.06  52.38  52.71  53.11  53.69  54.97
act   51.29  54.15  49.86  52.87  53.58  53.01  50.00  52.44  52.44  55.01
```

**Reconciling this with the H1 primary:** the continuous regression gives
`beta = 0.222, t = +3.42`, but the binary hit-rate slope gives only `t = +1.39`.
Both are correct — **the signal is real in POINTS and weak in HIT RATE**, because
converting to a binary discards outcome magnitude. That is the honest character
of the edge, and it is why `|E| >= 8 -> 56.59%` must not be read as a strategy.

## B3. ONE FROZEN THRESHOLD, chosen by the CALIBRATION not the outcome table

Selecting a cutoff from the ROI column is exactly the error this programme has
made before. The threshold is therefore taken from the **fitted logistic**, which
does not see the ROI ranking:

```
BET      if  |E_pace| >= 4.77 points   (the |E| at which fitted p_win = 52.881%,
                                        i.e. break-even + a 0.5pp safety margin)
PASS     otherwise
```

Discovery behaviour of that rule: **n = 1,056 (30.3% of slate), hit 53.31%
(se 1.54pp), ROI +1.78%.** Recorded as a benchmark, **not** as a claim.

**The +0.5pp margin is frozen now and may not be re-optimised.** The 2.0pp
variant (|E| >= 8.53, n = 248, 60.08%) is **explicitly NOT registered** — it is a
tail cell of a continuum whose underlying slope is insignificant.

## B4. HIERARCHY, restated

```
PRIMARY   H1   D -> Actual-Open, continuous, NO THRESHOLD          (unchanged)
PRIMARY   H2   AggregateGap -> Actual-Close, gamma < 0             (unchanged)
SECONDARY S1   does D*_profile or D*_drift beat D?
SECONDARY S2   does the frozen |E| >= 4.77 rule beat betting every game?
NOT REGISTERED: p_survive; the <220 x high-sigma cell; any |E| threshold
                other than 4.77
```

**H1 remains threshold-free.** S2 tests a threshold *against* H1 rather than
replacing it, so a failure of S2 leaves H1 intact.
