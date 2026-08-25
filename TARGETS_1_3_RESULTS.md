# Voulgaris targets 1–3 — results (2026-08-25)

Tested the three "unattended question" targets that needed no new modelling.
All economics are gated the same way: edge ÷ round-trip cost > 1, with
game-clustered CIs (rungs inside a game share one outcome).

## 1. Ladder-tail calibration — PARTIAL SURVIVOR, maker-only
8,758 settled rungs, 1,385 events, 7 board families, pregame anchor.

- Season-wide drift: +0.0137, CI [-0.0057,+0.0342] — **no** overs confound.
- **Full favorite-longshot NOT confirmed**: slope of (win − price) on price
  is +0.0275, CI [-0.0272,+0.0811]. The favourite side is nothing
  (0.80–0.90 adj +0.012 CI [-0.016,+0.039] dies; 0.90–0.95 dies).
- **One-sided longshot bias survives**: the 0.10–0.20 band prices 0.160 and
  resolves 0.115 — diff −0.045, CI [-0.077,-0.011]; net of drift −0.058,
  CI [-0.090,-0.024]. 442 rungs across 361 distinct games, so not one game.
- Economics: fee at 13c is only 0.8c. **At mid (maker fill) the edge is
  +3.6c on ~84c staked and the CI stays positive throughout. Crossing the
  6c spread as a taker, the CI includes zero.** Sell the cheap overs; do it
  by resting, not lifting.
- Deeper tails (<10c) had too few quoted rungs at the anchor to test — the
  most-biased region is unmeasured.

## 2. Endgame pinning / OT optionality — DEAD
603,306 rungs joined to ESPN game-end clocks across 253 games.

| minutes after buzzer | mean \|mid−settle\| | >2c off |
|---|---|---|
| −10..−2 | 0.1328 | 55% |
| −2..0 | 0.0694 | 31% |
| **0..+2** | **0.0068** | **1%** |
| +5..+45 | 0.0068–0.0083 | 1% |

Pinning is effectively instantaneous — under a cent of error within two
minutes. The 1% still off are unquoted husks: 33c half-spread, median
volume **0**. Net −0.8c/contract. No slow-pinning edge exists.
(OT base rate measured: 3.7% of games.)

## 3. Team-total additivity — REAL DISPERSION, undersized
`KXWNBATEAMTOTAL` harvested (778 markets, 41 events; 731,901 candles).
25 events with both team lines and a full-game line.

- gap = (TT_home + TT_away) − full: mean **−0.91 pts**, median +0.24,
  sd 2.58, CI [-2.03,-0.03] — barely systematic.
- **Dispersion is the story: |gap| > 3 pts in 16% of events, > 5 pts in 8%** —
  versus 0% beyond 3 pts for the half/quarter identities. This board pair is
  genuinely looser than the internally-arbitraged ones.
- NOT yet costed: the team-total leg spreads are unmeasured, and it is a
  three-leg trade. Sample is 25 events. **Most promising of the three, and
  the one needing more data rather than a verdict.**

## Standing
1 → forward-test the longshot fade as a maker (fits target 6's machinery).
3 → widen the team-total harvest; measure leg spreads before believing it.
2 → closed.
Targets 4–7 (crew/calendar shocks, new-series launch windows, maker vs
phantom reversion, injury latency) remain queued.
