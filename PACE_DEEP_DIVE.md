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

**Stated only as measured**, since we do not know what internal pace
representation bookmakers use:

> BDB-based pace is slightly better aligned with subsequent market movement, while
> duration-based pace is slightly better aligned with realised scoring.

A convention explanation (the market thinking in the standard box-score formula) is
plausible but **not established** and should not be asserted.

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

---

# M3 / M4 — POSSESSION ORIGIN AND GAME STATE (2026-08-30)

Built as a **pace-model research programme**, not a wagering search. Selection is
on **actual pace forecasting**; no ROI or hit rate was computed during development.

## Is the BDB - PBP gap random bookkeeping, or style-correlated?

**Style-correlated.** Regression of `BDB − PBP` on box-score aggregates, per sd:

```
OREB -0.3513 (t -20.57)   FTA -0.2799 (t -11.12)   PF  +0.2743 (t +10.74)
FGA  +0.1997 (t +11.06)   TO  +0.0671 (t  +4.40)   3PA -0.0403 (t  -2.58)
joint R2 0.0719

BDB-PBP by OREB quintile:  +1.543  +1.318  +1.121  +0.978  +0.818
```

Mechanically expected: `FGA − OREB + TO + 0.44·FTA` uses fixed coefficients, so the
gap varies with the terms it approximates. **This raised a real risk** — part of the
original pace signal could have been a measurement artefact correlated with style.

**The risk is falsified by evidence already in hand.** If the signal were largely a
BDB artefact, M2 — built from possession durations and immune to the formula —
should WEAKEN it. M2 **strengthens** it (t +3.63 vs +3.12) in 5 of 6 seasons. The
artefact hypothesis predicts the opposite of what is observed.

## Possession origin — the mechanism is real

Mean duration by `STARTTYPE` group, 1.95M possessions:

| origin | share | mean duration |
|---|---|---|
| steal | 7.5% | **8.79 s** |
| miss / rebound | 33.2% | 11.20 s |
| FT make | 8.7% | 16.49 s |
| dead ball / timeout | 15.5% | 16.87 s |
| FG make | 35.1% | **17.97 s** |

**`D_steal` is 9.2 seconds shorter than `D_madeFG`.** The hypothesised mechanism
(`TOVForced -> transition starts -> short possessions -> pace`) exists.

## M3 — and the mix is what cannot be forecast

M3 forecasts the origin mix `pi_hat` from prior-only own/allowed states (never the
realised mix) and combines with origin-specific duration states.

### A. Actual pace prediction — the selection criterion (n = 5,778, 2020+)

| model | RMSE(PBP) | MAE(PBP) | RMSE(BDB) | MAE(BDB) |
|---|---|---|---|---|
| M0 BDB pace | 4.0683 | 3.2525 | **3.9677** | **3.1538** |
| **M1 exact PBP pace** | **3.9071** | **3.0996** | 4.1524 | 3.2932 |
| M2 off/def duration | 3.9757 | 3.1712 | 3.9784 | 3.1607 |
| M3 + origin mix | 3.9723 | 3.1688 | 4.0064 | 3.1800 |

**M1 wins the selection criterion decisively**, and in every season (B, stability:
M1 lowest RMSE(PBP) in all 7). M3 improves on M2 by 0.003 — nothing.

### The diagnostic that explains it

```
M1 exact PBP pace, simple EWMA           RMSE(PBP) 3.9071
M3 forecast mix x forecast durations                3.9723
ORACLE: ACTUAL mix x league durations               4.6529
```

**Even with the start-type mix known in advance, the origin decomposition is worse
than a naive EWMA on past pace.** The mix varies little across games (sd 0.029 to
0.051) and a fast game jointly determines both its mix and its pace, so
decomposing carries no information the aggregate lacks.

## M4 — premise measured, and it is weak

Mean possession duration by absolute score differential:

| \|margin\| | 0-5 | 6-10 | 11-15 | 16-20 | 20+ |
|---|---|---|---|---|---|
| duration | 14.796 | 14.711 | 14.773 | 14.665 | **14.451** |

**0.35 s from close games to 20+ blowouts — a 2.4% effect.** Garbage time does not
materially change possession duration. M4 was **not built**: its premise does not
survive measurement at the duration level. (A possession-COUNT channel — late
fouling creating extra FT trips — is untested and is the only remaining version
worth considering.)

## Conclusion of the pace programme

On the pre-stated selection criterion — forecasting actual pace — **M1 is the
better pace model**: exact PBP possessions fed through the existing machinery,
RMSE 3.9071 vs M0's 4.0683 on the PBP target, winning every season.

Three criteria, three different winners:

| criterion | winner |
|---|---|
| actual pace forecasting (**the selection criterion**) | **M1** |
| outcome information (`Actual − Open`) | M2 (t +3.63) |
| price discovery (`Close − Open`) | M0 (t +21.71) |

M2's outcome advantage is **not** grounds for selection — that was the explicit
rule, and selecting on it would be retrospective optimisation.

**The frozen 2026-27 model is unchanged.** The candidate for a later prospective
test is **M1**, not M2 or M3.
