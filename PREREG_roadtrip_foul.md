# PREREG — ROAD-TRIP FATIGUE × LEAGUE FOUL ENVIRONMENT

Written 2026-08-29, BEFORE any outcome variable was touched. Only the
structural checks in §2 were run first — cell counts, era spread and time
clustering of the two states. No `dev`, no score, no total was read.

## 0. The hypothesis, and its poor prior stated up front

**Claim.** A visiting team deep into a road trip defends worse; a high league
foul environment converts that deterioration into free throws; clock-stopped
scoring pushes the total above the closing number. Neither leg needs standalone
power — **the claim is the interaction.**

**The prior is poor, and the reasons are in this repository, not invented
here:**

| prior art | says |
|---|---|
| `STREAKS.md` §3 | `road_trip_game` vs the closing total: coef **+0.1683, t = 0.99, p = 0.32**. Null. |
| `STREAKS.md` §1 | deep-in-trip own scoring **+0.19 pts** within venue — near zero, and the *wrong sign* for fatigue |
| `STREAKS.md` verdict | *"NBA teams do not measurably tire from being on the road per se; they tire from playing games in quick succession"* |
| `STREAKS.md` §2 | 13 schedule variables jointly vs the spread: mean squared t **0.49** — *below* the 1.0 pure noise produces |
| `CLOSING_REFEREE.md` | the market **does** incorporate broad shifts in the league officiating environment; only the *crew-specific* component is unpriced |
| `CLOSING_REFEREE.md` retired list | crew × matchup foul pressure: *"additive, not superadditive; every interaction null"* |

So leg 1 is null and leg 2 is the priced component. The hypothesis survives only
as a claim about the **nonlinear combination**, and it is tested once on that
basis.

## 1. Data and states — both already frozen

- `road_trip_game`: `rest_travel.add_rest_travel`, AWAY side. **Requires the
  full two-sided panel** — a team's streak needs its home games. Passing a
  road-only panel makes every game look like a trip continuation and fires the
  condition on 97.6% of games. That error was made and caught in §2.
- `LeagueFoulState`: **frozen** `ref_features.csv`, read-only. Trailing
  200-game league mean minus trailing 1230-game mean.
- Target `dev = actual_total − closing_total`, as throughout this program.
- Universe: Regular Season, 8,874 games with both states.

## 2. Stage-0 structural checks — RESULTS IN HAND

```
road_trip_game (away):  1:4,200  2:2,530  3:1,434  4:773  5:362  6:142  7:36  8:9
road_trip_game >= 2  ..............  56.0% of games
LeagueFoulState upper-20% cutoff ..  +0.9315
GATE CELL (trip>=2 AND high-foul) ..  975 games, 11.0%
```

**Gate semantics verified.** The road-trip condition genuinely binds: 56.0% →
11.0% when intersected. The prior agent run whose gate admitted high-foul games
with no road-trip condition is correctly classified `INVALID_GATE_SEMANTICS`
and is **not evidence in either direction**. It is not consulted here.

### The finding that governs the inference

**The high-foul regime is 35 contiguous time blocks, not 1,775 independent
games**, and it does not span the sample:

| season | 2017 | 2018 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|---|---|
| high-foul games | 0 | 276 | 0 | **777** | 152 | 0 | 90 | 480 |
| gate cell | 0 | 146 | 0 | **443** | 87 | 0 | 47 | 252 |

`LeagueFoulState` is a slow trailing difference and is heavily autocorrelated,
so its top quintile is a handful of stretches — **5 of 8 seasons, with 2021
alone holding 43.8%**. Any game-level standard error on this gate is wrong by
construction.

**Fixed consequences:** inference is by **permutation over the 35 contiguous
foul-regime blocks**, never game-level; and the result is reported
**season-by-season**, because a pooled figure here is substantially a statement
about 2021.

## 3. Predictions — fixed

**P1 PRIMARY — the interaction, one-sided.**

```
dev ~ trip2 + hifoul + trip2*hifoul + closing_total + season dummies
PREDICTED:  beta_interaction > 0
```

Pass requires block-permutation p < 0.05 one-sided over the 35 foul-regime
blocks. A significant *negative* interaction is a **failure of the registered
prediction** and will not be reframed as a finding.

**P2 SECONDARY — the tradeable form.** Mean `dev` in the gate cell minus mean
`dev` in matched controls (same season, closing total within ±3 points).
Reported with the same block permutation. This is the estimand as proposed; it
is secondary because it cannot separate the interaction from the two mains.

**P3 POSITIVE CONTROL — and it gates everything.**

```
home_points   ~ road_trip_game + controls     PREDICTED: > 0
home_FTA      ~ road_trip_game + controls     PREDICTED: > 0
```

No market variable. **Does a deep road trip actually degrade the visitor's
defence?** `STREAKS.md` found no first-order own-scoring effect, but it never
tested the *opponent* side, which is what this mechanism requires.

**If P3 fails, a P1 null is uninformative** — it would mean there is no fatigue
to interact with, not that the market prices the interaction. That distinction
is fixed now, exactly as in `PREREG_cohesion` where the control was registered
in advance rather than added afterwards.

**P2 and P3 cannot rescue P1.** If P1 fails the branch closes.

## 4. What is NOT permitted

No alternative road-trip threshold (2 is fixed), no alternative foul quantile
(top 20% is fixed), no substitution of `days_away` or `streak_signed` for
`road_trip_game`, no addition of rotation concentration, and no swap of
`LeagueFoulState` for `CrewShock`. The hierarchy the proposal sets out — add
rotation concentration only if the two-state version survives, and swap in a
crew-specific variable only after that — is adopted, and step 1 is all that is
authorised here.

## 5. Detection burden

Reported with the corrected conversion: points → hit-rate edge is `φ(0)/σ`,
compared to break-even, never added to it. MDE reported whether or not P1
passes, computed on the **block** standard error, so a null is separable from
low power.

---

# RESULT — run once, 2026-08-29. Verdict: **NOT A FINDING.**

8,874 games; foul cutoff +0.9315; gate cell 975; 75 contiguous regime blocks.

## P3 POSITIVE CONTROL — **FAILS, and one leg has the wrong sign**

```
home points ~ road_trip_game    +0.1090  (t = +1.12)   not significant
home FTA    ~ road_trip_game    -0.0537  (t = -1.29)   WRONG SIGN
```

The mechanism requires *fatigued road defence → more contact → more home free
throws*. **Home FTA goes slightly DOWN as the road trip deepens.** The
free-throw channel — the entire causal spine of the hypothesis — is not there.

## P1 PRIMARY — meets its numerical bar, and should not be believed

```
beta_interaction = +1.6462   (naive t = +1.70)
block-null sd 0.9593   one-sided block-permutation p = 0.0486
```

p = 0.0486 clears the pre-registered p < 0.05. **It is still not a finding**,
for three reasons that were all anticipated in §2 before the run:

**1. It is one season.** §2 warned "a pooled figure here is substantially a
statement about 2021." It is:

| season | gate n | mean dev \| gate | mean dev \| rest | diff |
|---|---|---|---|---|
| 2018 | 146 | −1.116 | +0.978 | **−2.095** |
| **2021** | **443** | +1.375 | −0.252 | **+1.627** |
| 2022 | 87 | +0.379 | +1.052 | −0.673 |
| 2024 | 47 | −0.330 | +1.044 | −1.374 |
| 2025 | 252 | +1.060 | +0.386 | +0.674 |

**Two of five seasons positive.** 2021 holds 443 of 975 gate games and is the
only season with both a large cell and a positive difference. 2018 is *more*
negative than 2021 is positive.

**2. The tradeable estimand is a quarter of the headline.** P2 — the gate cell
against matched controls (same season, closing total ±3) — gives **+0.4361
points on 974 matched pairs**, against the +1.6462 interaction coefficient. The
number you could act on is not the number that cleared the p-value.

**3. The effect is at the noise floor.** Block MDE at 95% is **1.88 points**
against an observed **1.65**. On the one-sided 1.645 bar it scrapes through;
that is what p = 0.0486 means. The block standard error is 0.96 points — the
same order as the effect.

## A gap in this pre-registration, recorded rather than papered over

§3 fixed what a P3 failure means for a P1 **null** ("uninformative"). It did not
state what a P3 failure means for a P1 **pass**. That case occurred, and the
honest reading is fixed now: **a P1 pass without its mechanism is an
unexplained regularity, not the hypothesis as written.** The hypothesis claimed
a specific causal spine — road fatigue → contact → free throws → clock-stopped
points. That spine is measured here and is absent. Whatever produced +1.65 in
2021, the pre-registered story is not it.

## Disposition — branch closes

Per §4: no alternative trip threshold, no alternative foul quantile, no
substitution of `days_away`, no rotation concentration, no swap to `CrewShock`.
The hierarchy's step 2 and step 3 are **not** authorised, because step 1 did
not establish the interaction — it produced a marginal pooled coefficient with
no mechanism and no cross-season replication.

**What was correctly diagnosed by the proposal:** the earlier −1.30 result was
indeed `INVALID_GATE_SEMANTICS` and is not evidence either way. Gate semantics
were verified here before the run — the road-trip condition binds, 56.0% → 11.0%
on intersection — so this run is the clean one, and it is the only one that
should be cited.

**What the proposal got wrong:** it treated both legs' individual nullity as
support for testing the interaction. `STREAKS.md` had already established that
road-trip depth has no first-order scoring effect at all (+0.19 within venue),
which is not "a priced main effect" — it is *no effect to price*. An
interaction needs at least one leg that does something.
