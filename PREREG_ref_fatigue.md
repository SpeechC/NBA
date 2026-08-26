# PREREG — referee schedule fatigue and the totals market

**Written 2026-08-26, BEFORE any fatigue state is joined to any outcome or
line.** Estimated EXACTLY ONCE per window.

## 0. Provenance and framing

Not mined. Reasoned from the program's own ledger under the inattention
framework: every survivor (CrewShock, late-season congestion, MOVE_COMBINED)
pairs an UNATTENDED INPUT with an ATTENDED (liquid) VENUE, while every
execution failure came from betting in thin venues. Officials have schedules,
travel and rest exactly as teams do; team rest is priced obsessively and
referee rest is, to our knowledge, priced by no one. This is the same
structural slot that produced CrewShock — exogenous to the teams, published
pre-tip, mechanically linked to scoring through the whistle.

Feasibility confirmed before writing (no outcomes touched): 28,467
official-games, 110 officials, 2,571 official-games on 1 day's rest (9.0%),
15.5% of official-games arriving with >= 4 games in the prior 7 days.

## 1. Frozen state definitions (prior-only, from held assignments)

Per official, per game, using only games strictly EARLIER in the file:

```
REF_REST      days since that official's previous game (NaN on first)
REF_B2B       REF_REST == 1
REF_LOAD7     count of that official's games in the trailing 7 days (exclusive)
REF_HEAVY     REF_LOAD7 >= 4
```

Game level, over the three-official crew:

```
CREW_B2B_N     number of officials on 1 day's rest        (0..3)
CREW_LOAD7     sum of REF_LOAD7 across the crew
CREW_FATIGUE   CREW_B2B_N >= 1  AND  CREW_LOAD7 >= its development-frozen Q75
```

Thresholds are computed on DEVELOPMENT ONLY and never re-cut. Games where any
official lacks 10 prior games in the file are dropped (warm-up, as in every
prior-only spec here).

## 2. Direction, FIXED BEFORE LOOKING

The literature and physiology are ambiguous (fatigue could reduce whistles via
inattention, or raise them via slower positioning). Committing anyway, because
a two-sided test after the fact is not a test:

    PREDICTION: fatigued crews call FEWER fouls -> fewer FTAs -> LOWER totals.
    i.e. CREW_FATIGUE carries a NEGATIVE coefficient on fouls, FTA and actual
    total.

A significant effect in the OPPOSITE direction is recorded as a REFUTATION of
the stated mechanism, not as a finding with the sign relabelled.

## 3. The chain test (CrewShock template)

The signal must move the SPORT before it can be an edge, and the market must
NOT already carry it:

```
link 1   CREW_FATIGUE -> game foul count            expect negative
link 2   CREW_FATIGUE -> FTA (both teams)           expect negative
link 3   CREW_FATIGUE -> ACTUAL total               expect negative
link 4   CREW_FATIGUE -> CLOSING total              expect ~ZERO  (the omission)
link 5   CREW_FATIGUE -> closing residual e         expect negative
```

Estimator: OLS with the frozen `rsk.CTRL` control set, cluster-robust at game
level. Inference of record: within-season permutation of the crew-fatigue
state across games, 5,000 reps.

## 4. Positive control (mandatory; bar derived from measured quantities)

`CrewShock` itself must reproduce its known link on the SAME sample and
estimator: CrewShock -> fouls positive with |t| >= 4. Derived from its measured
strength, not intuition (LINEAGE lesson 8, sharpened form). If the control
fails, the harness is broken and NO fatigue cell is interpreted.

## 5. Decision rule, fixed now

PASS requires ALL:
- links 1-3 negative on DEVELOPMENT, each |t| >= 2;
- link 4 (closing total) NOT significant at |t| >= 2 — the market omission;
- link 5 negative with within-season permutation p < 0.05 on development;
- holdout (2024-25 + 2025-26) link 5 same sign;
- economic relevance: >= 1.0 point of closing-total residual per fatigued
  game, since the -110 vig needs ~1.08 points.

Anything less is recorded as detected-but-not-tradable, or as a null, and the
branch closes. No re-thresholding, no alternative fatigue definitions, no
switching to spreads.

## 6. Prohibited

- estimating more than once per window; re-cutting Q75 after seeing results
- trying REF_LOAD over other windows (14d, 30d) after a failure
- individual-official effects (that is CrewShock's territory, already frozen)
- promoting a wrong-signed result
- any Kalshi/derivative expression from this document

---

## 7. RESULT — run once, 2026-08-26. Verdict: NULL, branch closes

5,066 games after the 10-prior-game warm-up (dev 3,729 / holdout 1,337).
Frozen dev Q75 of CREW_LOAD7 = 7.0; CREW_FATIGUE fires on 680 games (13.4%),
identically in dev and holdout.

**Positive control PASSES**: CrewShock -> fouls on this exact sample and
estimator gives +1.0619, t = +10.63 (bar was |t| >= 4). The harness detects a
real officiating effect; the fatigue null is therefore a finding, not broken
plumbing.

### The chain (development)

| link | coef | t | predicted |
|---|---|---|---|
| 1 fatigue -> fouls | **+0.5815** | 1.95 | negative |
| 2 fatigue -> FTA | +0.4932 | 0.97 | negative |
| 3 fatigue -> ACTUAL total | +0.8970 | 1.00 | negative |
| 4 fatigue -> CLOSING total | +0.2180 | 0.99 | ~zero |
| 5 fatigue -> closing residual | +0.6790 | 0.78 | negative |

Permutation on link 5: **p = 0.4227**. Holdout link 5 +1.0385 (t = 0.73).

### Decision

Three of five criteria fail. Links 1-3 are not merely insignificant but
**positively signed** — the opposite of the committed direction. Per section 2
that is a REFUTATION of the stated mechanism; the sign is not relabelled and
no "fatigue raises whistles" variant is pursued under this document. The only
two criteria that pass are the ones a null trivially satisfies (link 4 absent,
holdout agreeing in a sign that is itself wrong).

Worth recording honestly: link 1 at t = 1.95 is the largest cell, and a
results-first program would have flipped the hypothesis and called it
"fatigued crews call MORE fouls." Its permutation-tested descendant (link 5)
sits at p = 0.42, so that story would not have survived either.

### What this closes and what it does not

Closed: **crew-level SCHEDULE fatigue as a totals signal**, on this data, with
these definitions. Not closed, and deliberately out of scope here: individual
official heterogeneity (CrewShock, already frozen and working) and any
non-schedule officiating state.

The inattention framework survives the null intact — it predicts WHERE to
look, not that every unattended input is priced wrong. Referee rest is
genuinely unattended by the market; it also appears not to matter.
