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
### Deep re-test (`team_total_additivity.py`) — VERDICT: DEAD, well-characterised
No more history exists (team totals begin 2026-08-10; `/historical/markets`
returns nothing for this series). But the first pass used one snapshot per
market out of 731,901 candles. Walking the full minute-by-minute history:

- **3,606 simultaneous three-board minutes across all 41 events** (median 78
  per event), versus 25 snapshots before.
- Gap = (TT_a+TT_b) − full: mean −0.50, median −0.17, sd 2.71.
  |gap|>2pts 23%, >3 14%, >5 6%. **Directional**: CI [−0.86,−0.13] — the
  team pair sits systematically BELOW the game line.
- **The team legs are demonstrably the mispriced side.** Regressing the
  5-minute change on the gap: the full board moves +0.043 per point
  (se .019, i.e. barely), the team pair moves **−0.543** (se .021). The thin
  boards drift and snap back to the liquid one. Persistence +0.414 — a gap
  decays ~59% in five minutes.
- **And it is untradeable, by a mile.** Team-leg spread is **38.9c** (full
  board: 1.5c). A three-leg round trip costs ~44.9c = **17.3 points of
  total**. The gap clears that bar in **0.2%** of minutes, in 4 episodes of
  median 2 minutes, none lasting 5.

**The general law this makes explicit: a board's spread is the market's own
statement about how much attention it receives.** Team totals are mispriced
BECAUSE nobody watches them, and untouchable for exactly the same reason.
The viable target profile is therefore narrow: **tight spread (so it can be
traded) AND low analytical attention (so it is wrong)** — which is why the
10–20c tail rungs on LIQUID boards (6c spread) survived as target 1, while
this did not.

## Standing
1 → forward-test the longshot fade as a maker (fits target 6's machinery).
3 → widen the team-total harvest; measure leg spreads before believing it.
2 → closed.
Targets 4–7 (crew/calendar shocks, new-series launch windows, maker vs
phantom reversion, injury latency) remain queued.
