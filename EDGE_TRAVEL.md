# Does a strategy's edge travel along the ladder? (2026-10-07)

**Prompted by a correct objection:** a sportsbook line and a Kalshi strike are
dual parameterisations of the same distribution, so why should rung choice
matter at all?

- **Sportsbook** fixes the *price* (−110) and solves for the *line* → it sells
  one point on the CDF: the median.
- **Kalshi** fixes the *lines* (3-point strike grid) and solves for *prices* →
  it sells any point on the CDF.

The distributions agree: ladder μ = the close, median difference **0.001
points**, corr **0.9975** (`LINE_VS_STRIKE.md`). There is no information
difference between the venues.

The only genuine constraint is that **a hit rate is one number about one
event**. `54.21%` means `P(total > close)` and says nothing about
`P(total > close + 6)`. Betting another strike requires a *model* of how the
signal moves the distribution, and the trader assumes a pure location shift of a
normal. So the question reduces to: **is that model right?**

## Test — boxscores only, all 8 seasons

`edge(x) = P(actual > close + x | signal) − P(actual > close + x | all games)`,
against the location-shift prediction
`[1−Φ((x−δ)/σ)] − [1−Φ(x/σ)]`.

No Kalshi data, so all eight seasons are available and the test is properly
powered.

**CrewShock, n = 1,390** (se ≈ 1.4pp):

| x | edge | model | ratio |
|---|---|---|---|
| −6.0 | +2.87pp | +3.91 | 0.73 |
| −3.0 | +3.45pp | +4.11 | 0.84 |
| −1.5 | +3.87pp | +4.17 | 0.93 |
| **0.0** | **+4.48pp** | +4.20 | **1.07** |
| **+1.5** | **+4.38pp** | +4.21 | **1.04** |
| +3.0 | +3.33pp | +4.18 | 0.80 |
| +6.0 | +2.83pp | +4.05 | 0.70 |
| +12.0 | +2.56pp | +3.50 | 0.73 |

| | measured | model |
|---|---|---|
| mean edge, \|x\| ≤ 1.5 | **+4.24pp** | +4.19pp |
| mean edge, \|x\| ≥ 6 | **+2.72pp** | +3.70pp |
| **retention at \|x\| ≥ 6** | **64%** | 88% |

**final7, n = 537** (se ≈ 2.2pp): +6.26pp at the line (model +5.26), +4.47pp at
\|x\| ≥ 6 (model +4.65), **retention 71%** vs 88%.

## This corrects me, not the objection

**The edge does travel.** It is fully retained out to ±1.5–3 points — ratio 1.07
at the line and 1.04 at +1.5 — and decays meaningfully only beyond ±6 points.

And **max-edge's mean offset in 2025-26 was +1.83 points**, exactly where
retention is ~100%. **So edge decay cannot explain the max-edge
underperformance.** The mechanism I asserted in `RUNG_SELECTION_TAKER.md` and
`LINE_VS_STRIKE.md` — "the edge sits at the line and does not travel along the
ladder" — is **withdrawn**: it does not apply at the offsets that actually
occurred.

What remains is what the paired test already said: **t +0.79 and +1.16, both
confidence intervals including zero.** The 2025-26 max-edge-vs-nearest-line gap
was noise. I constructed a mechanism to explain an insignificant result rather
than accepting the insignificance — two messages after criticising exactly that
move in the context of dropping a bad season.

## What survives

1. **The venues are interchangeable.** Same distribution; ~0.3pp of cost
   difference, direction depending on whether the nearest-strike ask is below or
   above ≈50.6¢.
2. **Rung choice near the line is approximately free.** The location-shift model
   is accurate within ±3 points.
3. **Far rungs are the real caution.** Beyond ±6 points you keep ~64–71% of the
   edge while `p_model` assumes 88%, so the trader **overstates edge out there
   by 20–30% relative**. That is a genuine, measured misspecification.
4. **Max-edge is only exposed when it wanders far.** At +1.83 it is fine; a
   synthetic steep ladder had it selecting **+9.5 points**, which is where the
   overstatement bites.

## Consequence for the sidecar

`RUNG_CHOICE_SIDECAR.md` was justified as adjudicating a rule difference. Its
purpose is now **narrower and better defined**: flag the occasions when
max-edge selects beyond ±6 points, where the edge model is measurably
optimistic. `offset_pts` is already logged, so no code change is needed — only
the reading of it.

A cheap, well-motivated alternative to a rule change: cap the rung offset at
±6 points. That is supported by a measurement on 1,927 strategy-games across 8
seasons, rather than by one season of 280.

Script: `does_the_edge_travel.py`.
