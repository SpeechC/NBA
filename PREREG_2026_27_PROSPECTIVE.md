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
