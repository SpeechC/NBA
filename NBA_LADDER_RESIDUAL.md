# NBA ladder residuals — the last surviving edge, deep-tested (2026-08-26)

Residual = quoted mid minus the leave-one-out probit fit from the rung's own
neighbours. Adverse selection was measured at ~0.02c and is charged here, as
is the fee.

## The edge is real in the data — and it is a wide-spread artefact

Edge scales with residual size, but **so does the spread it occurs on**:

| filter | n | maker edge | median spread |
|---|---|---|---|
| \|resid\| > 1c | 13,918 | +0.19c [−0.43,+0.82] | 3c |
| \|resid\| > 2c | 5,059 | +1.70c [+0.70,+2.72] | 6c |
| \|resid\| > 3c | 2,389 | +3.78c [+2.33,+5.27] | 11c |
| \|resid\| > 5c | 906 | +7.21c [+4.80,+9.73] | **19c** |

corr(|residual|, spread) = **+0.515**. Median |residual| by spread bucket:
0.69c at ≤2c spreads, 0.57c at 2–6c, **1.90c above 6c**. A wide quote has an
imprecise mid, so much of the "residual" is mid noise — and the maker edge is
computed assuming a fill *at the mid*, which on a 19c-spread ladder means
posting 9.5c inside the touch. Nobody fills you there except someone informed.

## It disappears exactly where the venue is heading

| period | spread | edge |
|---|---|---|
| 2025-10..12 | 12c | +1.91c [+0.43,+3.50] |
| 2026-01..02 | 4c | +1.94c [+0.25,+3.54] |
| **2026-03+** | **2c** | **+0.77c [−1.67,+3.17]** |

Same story by phase: in-game (8c spreads) +2.08c, pregame (3c) +1.06c with a
CI crossing zero. The board compressed 4c → 1c over the season and the edge
went with it.

## The residual does revert — but you cannot be filled

Mean reversion is genuine: persistence +0.613 at 1 min, +0.350 at 5, +0.238 at
10; |residual| decays 4.58c → 2.81c over ten minutes. The mechanism a maker
would rely on is present.

But **73% of the rung-minutes carrying a >2c residual have ZERO volume**
(median 0, mean 161). The mispricings sit on rungs nobody trades. That is not
a coincidence — a rung is mispriced *because* no one is trading it, and
resting there means waiting for flow that does not come.

## Verdict

The edge is measurable, mean-reverting, and survives adverse selection — and
it is still not a business. It lives on wide-spread, zero-volume rungs, it
requires a fill at the mid that would not happen, and it fades to statistical
insignificance in the tight-spread regime that now prevails.

This closes the last live candidate from the two-day search. It also restates
the programme's one durable finding in its sharpest form: **on this venue,
the size of an apparent mispricing is a measure of how untradeable the rung
is.** Spread, volume and mispricing are the same variable.
