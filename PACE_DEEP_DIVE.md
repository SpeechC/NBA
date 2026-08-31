# PACE — MEASUREMENT DEEP DIVE (2026-08-30)

Our one surviving NBA edge is concentrated in pace, and a scalar realised-pace
statistic is the most compressed possible representation of that mechanism. This
asks whether a better construction exists — **without assuming BigDataBall is
wrong.**

## The parquet already contains a possession-level table

This was the main discovery. `pbp_lineups_all.parquet` is not just event PBP:

```
STARTTYPE                possession ORIGIN -- "Off At Rim Make", "Off Steal",
                         "Off Dead Ball", "Off FT Make", "Off Timeout", ...
STARTTIME / ENDTIME      possession boundaries -> DURATION
STARTSCOREDIFFERENTIAL   game state at possession start
```

**The offensive team is identified by `OPPONENT != PLAYER1_TEAM_ABBREVIATION`.**
That yields **98.31 possessions per team-game** and a mean duration of
**14.66 s**, and the identity closes exactly: `2880 / (2 x 14.66) = 98.3`.

So M2/M3/M4 do not require building a possession reconstruction — the raw material
is already there.

## GATE — exact PBP possessions vs BigDataBall GAME_PACE

n = 8,165 games:

```
BDB   mean 98.705  sd 4.714          PBP   mean 97.527  sd 4.695
corr 0.95816   MAE 1.437 poss   bias -1.178   sd(diff) 1.361
|diff| > 0.5: 78.4%    > 1: 57.8%    > 2: 26.8%
per-team count: PBP 98.31  vs  BDB POSS 99.17
```

**The two definitions disagree materially.** MAE 1.44 possessions is ~3.3 points of
`E_pace` at `EffSum ~ 230` — larger than the neighbourhood of the 4.77 threshold.
The gate is passed; the measurement question was worth asking.

A first counter (distinct PERIOD+STARTTIME / 2) undercounted at 97.7 and was
discarded once the `OPPONENT` marker was found. **The systematic −1.18 bias is a
definitional difference, not evidence either source is wrong.**

## Horse race — M0 / M1 / M2, same games, same machinery

Only the pace construction varies. M0 = frozen EWMA on BDB pace; M1 = same on
exact PBP pace; M2 = separate offensive and defensive possession-DURATION states,
`P = 2880 / (D_H + D_R)`.

### 1. Actual pace prediction (5,778 games, 2020+)

| forecast | RMSE(BDB) | MAE(BDB) | RMSE(PBP) | MAE(PBP) |
|---|---|---|---|---|
| M0 BDB pace | **3.9677** | **3.1538** | 4.0683 | 3.2525 |
| M1 exact PBP | 4.1524 | 3.2932 | **3.9071** | **3.0996** |
| M2 off/def duration | 3.9784 | 3.1607 | 3.9757 | 3.1712 |

Each scalar model wins on its own target. **M2 is the only one that predicts both
definitions about equally well** (3.978 / 3.976) — it is not tied to either
measurement convention.

### 2. Pace-gap outcome information (n = 3,495, 2022+)

| model | beta | se | t | hit | ROI |
|---|---|---|---|---|---|
| M0 BDB (frozen benchmark) | +0.2377 | 0.0761 | +3.12 | 51.55% | −1.59% |
| M1 exact PBP | +0.2475 | 0.0742 | +3.34 | 51.55% | −1.59% |
| **M2 off/def duration** | **+0.2676** | 0.0738 | **+3.63** | 51.52% | −1.65% |

**Monotone: M2 > M1 > M0.** beta rises 12.6% and t from +3.12 to +3.63.

### 3. Price discovery — and the ordering REVERSES

| model | beta on (Close − Open) | t |
|---|---|---|
| **M0 BDB** | **+0.28669** | **+21.71** |
| M1 exact PBP | +0.27254 | +21.11 |
| M2 off/def duration | +0.26810 | +20.83 |

This is the criterion that was supposed to separate "improved latent expectation"
from "fitted realised-pace noise", and **it points the other way.**

The benign reading: the market prices pace in the standard box-score convention —
the same formula BDB uses — so a gap measured in BDB units tracks market movement
better *by construction*, while a gap measured in true possession-duration units
tracks the actual outcome better. Both orderings are then consistent with M2 being
a better measure of the physical mechanism and a worse proxy for what the market
is thinking.

### 4. Stability

| season | n | M0 | M1 | M2 |
|---|---|---|---|---|
| 2018 | 1,151 | +0.147 (t+0.90) | +0.164 (t+1.06) | +0.196 (t+1.25) |
| 2020 | 1,076 | +0.354 (t+2.35) | +0.359 (t+2.46) | +0.371 (t+2.50) |
| 2021 | 1,206 | +0.513 (t+3.67) | +0.501 (t+3.64) | +0.506 (t+3.66) |
| 2022 | 1,198 | +0.141 (t+0.95) | +0.163 (t+1.12) | +0.189 (t+1.30) |
| 2023 | 1,148 | +0.247 (t+1.98) | +0.254 (t+2.09) | +0.265 (t+2.19) |
| 2024 | 1,149 | +0.312 (t+2.47) | +0.316 (t+2.56) | +0.342 (t+2.79) |

M2 leads in **five of six** seasons. Not one-season-driven.

## What this does and does not establish

**Does:** the offensive/defensive possession-duration decomposition is a modestly
better measure of the pace mechanism — a stable ~12% larger coefficient and
+0.5 of t on the outcome regression, robust across pace definitions and seasons.

**Does not:** produce a better wager. The three signals correlate **0.98-0.99** —
this is refinement, not a new signal — and betting every game gives 51.55% / 51.55%
/ 51.52%, ROI ~−1.6% for all three. Improving the points measurement does not fix
the points-to-hit-rate conversion, which is where this signal has always been weak.

**NO CHANGE TO THE FROZEN MODEL IS PROPOSED.** The 2026-27 preregistration is
frozen with 51 days to opening night, the improvement is small, and the price-
discovery criterion disagrees with the outcome criterion. Changing the pace
construction now on outcome-adjacent evidence is exactly what the prereg's
no-tuning clause exists to prevent. This is recorded as a **2027-28 candidate**.

## Not run

**M3 (possession-origin mix)** and **M4 (game-state adjustment)** were not built.
The raw material exists — `STARTTYPE` gives origin after made FG / rebound /
steal / dead ball / timeout, and `STARTSCOREDIFFERENTIAL` gives the score state at
every possession start — so both remain cheap to run. Given that M2's gain does not
reach the economics, neither is justified by a wagering objective; both are
justified only under "improve the pace model."
