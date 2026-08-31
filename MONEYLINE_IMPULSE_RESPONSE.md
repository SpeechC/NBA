# MONEYLINE — IMPULSE RESPONSE OF A TEAM SURPRISE (2026-08-30)

The block atlas showed `block b -> block b+1` carries nothing. That cannot rule out
a shorter window. This measures the **full h = 1..20 game response curve** — no
window selection, no ROI inspection before the curves were estimated.

Surprise `S_{i,t}` is the realised source attribution in game `t`, known
immediately after that game. **No forward-looking event definition.** Horizons are
in the team's own subsequent GAMES, not calendar days. n = 8,884 team-games.

Three separate questions, deliberately not conflated:

```
basketball persistence   S_t -> S_{t+h}          beta_h
model adaptation         S_t -> F_{t+h} - F_t    gamma_h
market underreaction     S_t -> BookError_{t+h}  delta_h   <-- the wagering test
```

## 1. Basketball persistence — REAL, with measurable half-lives

| source | beta_1 | half-life | beta_8 | beta_20 |
|---|---|---|---|---|
| turnovers | +0.0933 (t +8.76) | **2 games** | +0.0527 | +0.0339 |
| FT generation | +0.0450 (t +4.23) | **5 games** | +0.0168 | +0.0212 |
| 2P conversion | +0.0422 (t +3.96) | **7 games** | +0.0247 | +0.0365 |
| state-engine level | +0.4167 (t +42.98) | **10 games** | +0.2553 | +0.1391 |
| **3P conversion (CONTROL)** | +0.0138 (t +1.29) | — | **−0.0117** | +0.0004 |

**The negative control passes.** 3P conversion — EB weight 0.0000, block r = −0.138
— shows no persistence at any horizon. The event study is not manufacturing
patterns, which means the turnover and FT-generation curves can be believed.

Turnover surprises decay with a 2-game half-life but remain detectable out to
h = 8. This is exactly the transient structure the 20-game block test could not see.

## 2. Model adaptation — the state engine absorbs 61% in ONE game

```
state-engine absorption of the surprise:
   60.9% by game 1     62.8% by game 5     62.4% by game 10
```

Effectively a one-game step to ~61%, then flat. This is the absorption rate the
block analysis could only infer from negative correlations.

**[SUPERSEDED — see the CORRECTION section at the end of this file.]** These two
numbers are both properties of the rolling-vs-state gap, not of innovation gain,
and the over-correction reading drawn from them is withdrawn. Measured on the
engine's own surprise the one-step forecast error is serially uncorrelated
(beta = −0.0040, t = −0.38) and a gain sweep puts the optimum exactly at the
frozen value.

## 3. Market underreaction — none, at any horizon

```
market tests run (7 sources x 20 horizons x 2 targets):  280
|t| > 1.96 observed:                                       8
expected by chance:                                       14
```

**Fewer significant results than chance.** The one channel that flickered, 2P
conversion against book error, has this t-curve across h = 1..20:

```
+1.8 +0.3 +1.4 +2.0 +0.8 -0.1 +1.9 +1.3 -0.0 -0.6 +2.6 +2.0 -0.4 -0.3 +2.0 +0.6 +1.0 +0.3 -1.5 +0.6
```

A genuine underreaction window decays monotonically toward zero. This spikes at
h = 11 and h = 15, which is noise, not a response.

Turnovers — the source with the strongest basketball persistence — return no
horizon above |t| = 1.4 on book error and none above |t| = 1.3 on the moneyline.

## The answer, in the form the question deserved

Previously: *"the window disappears before the next 20-game block."* What the
impulse response actually establishes:

> **A turnover surprise persists in the basketball with a 2-game half-life and is
> still detectable 8 games later. Our state estimator adapts continuously, at
> 4.2% per game, which is enough that aggregating into long blocks creates
> APPARENT negative persistence even though one-game forecast errors are
> effectively white. And the market shows no residual error at ANY horizon from 1
> to 20 games, at a rate below chance.**

The three-way separation is now measured rather than inferred: the basketball
signal is real, our model absorbs it steadily, and the market has already priced
it before the first subsequent game.

## Status

No betting rule was constructed and no ROI was examined; the specification
required the full curves first, and no curve qualified for a second-sample
validation. **This closes the transient-window hypothesis** — the last route by
which a team-specific moneyline edge could have survived the block analysis.

## Untested

Rim-rate / shot-location split of the 2P channel. 2P has the longest realization
half-life (7 games), which is what shot-quality drift would look like, but its
market curve is non-monotone noise — a refinement there would have to overturn a
null rather than sharpen a signal.

---

# CORRECTION — the "over-correction" finding was wrong (2026-08-30)

An earlier version of this file reported that the state engine "absorbs 60.9% of a
surprise by game 1" against a true persistence of 0.417, and concluded it
**over-corrects by ~19 percentage points**. **That is withdrawn.**

**What the measurement actually was.** `state_lvl` is *defined* as (rolling
15-game component forecast − state-engine forecast). So the gamma regression put
the change in the state forecast on the gap between the rolling and state
forecasts — that is **convergence between two estimators**, not the engine's
response to a game surprise. And `beta_1 = 0.417` was the persistence of the same
gap. Neither quantity says anything about innovation gain.

**Measured properly, on the engine's own surprise (n = 8,988 team-games):**

```
frozen per-game gain   SHARE*aO                    = 0.04182   (4.2%, not 61%)
engine forecast move per unit of surprise  gamma   = +0.0551  (t +14.35)
TRUE one-step persistence of the surprise  beta    = -0.0040  (t  -0.38)
```

**The engine's one-step forecast error is serially uncorrelated.** That is the
signature of a well-calibrated filter; an over-correcting filter produces negative
error autocorrelation, and there is none.

**The negative block correlations have a mundane cause.** At 4.2% per game the
engine absorbs `1 - 0.958^19 ≈ 56%` of a level error across a ~19-game block,
which mechanically induces negative correlation between successive block MEANS
even when game-level errors are white noise. That is any adaptive filter working,
not overshooting. The −0.219 / −0.257 half-season figures are the same artefact at
coarser resolution.

## Gain sweep — settled by chronological one-step prediction, not by argument

7,027 evaluation games (2020-2025), selection on forecast accuracy only, no
wagering criterion consulted:

| multiplier | effective gain | RMSE | MAE | corr(e_t, e_t+1) |
|---|---|---|---|---|
| 0.40 | 0.01673 | 14.2183 | 11.1847 | +0.0084 |
| 0.60 | 0.02509 | 14.0895 | 11.0632 | +0.0094 |
| 0.80 | 0.03345 | 14.0368 | 11.0117 | +0.0096 |
| 0.90 | 0.03763 | 14.0261 | 10.9998 | +0.0095 |
| **1.00 (FROZEN)** | **0.04182** | **14.0225** | **10.9945** | **+0.0094** |
| 1.10 | 0.04600 | 14.0242 | 10.9951 | +0.0092 |
| 1.25 | 0.05227 | 14.0345 | 11.0036 | +0.0088 |
| 1.50 | 0.06272 | 14.0661 | 11.0310 | +0.0080 |
| 2.00 | 0.08363 | 14.1627 | 11.1131 | +0.0062 |

**A smooth interior optimum exactly at the frozen value.** Error autocorrelation
is +0.0094 at that gain — near zero and *positive*, so the gain is marginally low
if anything. The proposed 0.35-0.50 range makes forecasts strictly worse
(RMSE 14.22 vs 14.02).

**The engineering hypothesis is refuted on its own criterion. No change to the
frozen engine is warranted, and none was made.** The 0.345-point gap to the book
(14.0225 vs 13.6772) is not a tuning problem.
