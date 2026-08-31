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

**And it identifies a real defect.** The state composite's true persistence is
`beta_1 = +0.417`, while the engine absorbs **0.609** of it immediately. The engine
**over-corrects by roughly 19 percentage points** on a single-game surprise. That
over-absorption is the mechanical cause of every negative autocorrelation reported
earlier — block-to-block rho of −0.10 to −0.12, half-season −0.219/−0.257. The
engine does not merely adapt; it overshoots, so yesterday's exception becomes
negatively informative about tomorrow's error.

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
> still detectable 8 games later. Our state engine absorbs 61% of it within a
> single game — over-correcting relative to its true 42% persistence, which is why
> team errors mean-revert. And the market shows no residual error at ANY horizon
> from 1 to 20 games, at a rate below chance.**

The three-way separation is now measured rather than inferred: the basketball
signal is real, our model over-absorbs it, and the market has already priced it
before the first subsequent game.

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
