# PREREG — the day-move and the publication-jump inside ONE instrument

**Written 2026-08-23, BEFORE any Kalshi day-move is computed.** Estimated
EXACTLY ONCE.

## 1. Why this exists

The claim currently standing is: *late OUT information moves the total, but the
move happens BEFORE the official report publishes.* That claim is assembled
from two different datasets:

- "`OUT_late` predicts open->close movement" — sportsbook, 2020-24;
- "publication moves nothing" — Kalshi, 2025-26 (`JUMP` = +0.045, t=+0.29).

Combining them is a cross-sample inference, not a measurement. This document
closes that gap by putting BOTH halves in the same instrument, the same season
and the same games: the 429 Kalshi games with 1-minute candles,
2025-10-21..2025-12-22.

## 2. The two quantities, same games

```
L(t)        implied total, median crossing of the rung ladder, EXACTLY the
            estimator frozen in PREREG_injury_absorption.md s3 (>=4 two-sided
            quoted rungs, bracketed crossing, no extrapolation)

DAY_MOVE    L(last usable bar before tip) - L(first usable bar in the window)
            the whole-day repricing, ~12h of candle history

JUMP        already measured, +0.045 (t=+0.29): L_0 - L_pre around the report
```

Treatment is the carryover-weighted late-OUT state frozen in
`PREREG_injury_absorption.md` s4 amendment (2024-25 prior-season MIN_SHARE;
PBP has no 2025-26 data). Unchanged, not re-derived.

## 3. The single test

```
DAY_MOVE = a + b * treatment + e
```

reported treated-vs-control as well, on the same same-date matched control arm
as the absorption study. Inference: within-date block permutation of the
treatment across games, 5,000 reps.

## 4. Prediction, and what each outcome means

Prediction: `b < 0` — the Kalshi total falls over the day when important late
absences occur, mirroring the sportsbook `OUT_late` coefficient.

| DAY_MOVE | JUMP (already measured) | conclusion |
|---|---|---|
| **negative, |t| >= 2** | ~0 | the move is real in THIS instrument and happens away from publication -> "before the report" is established WITHIN one sample |
| ~0 | ~0 | **the elimination argument COLLAPSES.** No day-level relationship here at all; "the move happened earlier" becomes unsupported, and the cross-sample story must be withdrawn |
| negative | negative | publication does contribute after all; the absorption result would need revisiting |

The second row is a live possibility on 429 games in one partial season, and is
the outcome this document exists to be able to report.

## 5. Decision rule, fixed before estimation

- ESTABLISHED WITHIN-SAMPLE: `b < 0`, |t| >= 2, permutation p < 0.05, and the
  treated-minus-control difference also negative.
- NOT ESTABLISHED: anything else. Then the standing "information arrives
  upstream" interpretation is downgraded to unsupported speculation in every
  document that carries it, and this is recorded there.

No magnitude threshold: this is an existence question, not an economic one.
Tradability stays closed regardless — `PREREG_injury_absorption.md` settled it.

## 6. Prohibited

- estimating more than once, or after inspecting the answer
- altering `L(t)`, the treatment, or the control arm — all are frozen elsewhere
- re-cutting the window, or dropping dates after seeing results
- reading this as a tradability result
- writing to `kalshi_nba_totals.sqlite`

## 7. Known limitations, recorded in advance

1. 429 games, one partial season, ending 2025-12-22. No deadline period.
2. `DAY_MOVE` starts at the first usable bar, which is ~12h before market
   close, NOT at the sportsbook open. It is a day-move, not an open->close
   move, and the two are not the same object.
3. Many `OUT_late` events first appear before the candle window starts (top
   decile >12h pre-tip), so part of the day-level response can precede even
   `DAY_MOVE`. This biases the test TOWARD the null.
4. Carryover importance weights, not within-season — PBP lacks 2025-26.
