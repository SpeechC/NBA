# PURIFIED PACE — closed, and one claim withdrawn (2026-09-13)

Two questions, both now answered on 8,257 games (2018-19 .. 2025-26), prior-only:

1. Is the frozen pace update contaminated by opponent mixture? **No — it is the
   purified estimator.**
2. Is `E_pace` contaminated by efficiency? **No — 99.38% of its variance is the
   possession channel.** This reverses an error recorded below.

---

## 1. THE EQUAL SPLIT IS THE PURIFIED GRADIENT

The "purified pace" literature fits each team a pace `p_i` minimising
`Σ_g ((p_i+p_j)/2 − y_g)²`, on the argument that a team's raw average game pace
is a mixture contaminated by its opponents' pace. That argument is correct, and
the frozen engine already solves it. With `ep = y_g − ŷ_g`:

```
∂L/∂p_i = −ep          (the ½ from the average cancels the 2 from the square)
SGD     : p_i += α·ep ,  p_j += α·ep
frozen  : Pst[hh] += aP*ep ;  Pst[aa] += aP*ep        <- the same line
```

**The equal split is not a naive average — it is the exact online gradient of
the additive opponent-purified model.** The frozen engine differs from batch
purified least squares only in weighting.

### Measured, prior-only, refit every game date, min 10 games/team, n = 7,042

| model | MAE | RMSE | vs prev |
|---|---|---|---|
| constant (league mean) | 3.759 | 4.722 | |
| naive team average | 3.330 | 4.192 | −11.4% |
| purified average (least squares) | 3.209 | 4.043 | −3.6% |
| purified LS, exponential weights (hl 5.7) | 3.140 | 3.962 | −2.2% |
| **FROZEN state engine** | **3.115** | **3.924** | −0.8% |

`corr(weighted purified LS, frozen forecast) = +0.9683`, mean |difference| 0.69
possessions. They are the same estimator.

Published comparison figures for reference: constant 3.97/5.47, naive 3.34/4.71,
purified 3.11/4.40. Our naive MAE reproduces theirs almost exactly (3.330 vs
3.34); **the purification gain is real but half the claimed size** (−3.6% here,
−7% claimed).

### WITHDRAWN: "the remaining margin comes from the league-drift term"

Asserted without test, and the ablation refutes it.

| frozen engine variant | MAE | Δ |
|---|---|---|
| CARRY 0.42, aL hl 496 — **FROZEN** | 3.1147 | — |
| CARRY 0.42, **aL = 0** | 3.1160 | +0.0013 |
| **CARRY 0.00** (full reset), aL hl 496 | 3.1219 | +0.0072 |
| CARRY 1.00 (no decay), aL hl 496 | 3.1202 | +0.0055 |
| weighted purified LS (within season) | 3.1400 | +0.0253 |

League drift is worth **+0.0013 MAE, 5% of the gap**. Cross-season carry — the
better suspect, since the LS fit is within-season — is worth +0.0072. Together
they are a third of it. **The remainder is diffuse** (the LS refits per date on
equal per-game weights; the engine updates per game within a date), and at 0.8%
of MAE it is not worth attributing further.

### The trap this creates

Someone reading `Pst[hh] += aP*ep; Pst[aa] += aP*ep` alongside a "contaminated
mixture" explanation will see a naive equal split and try to opponent-adjust it.
**That breaks the gradient and changes the estimator rather than purifying it.**
A comment at the update site says so.

The efficiency channel is purified differently and correctly: `Ost`/`Dst` split
0.54/0.46 between the scorer's offence and the opponent's defence. Pace is a
joint property of a game and takes the symmetric update; efficiency is
directional and takes the asymmetric one.

---

## 2. `E_pace` IS A POSSESSION DISCREPANCY — a correction

**An earlier statement in this programme's working notes — that `E_pace` is "57%
efficiency by variance" and therefore materially misnamed — was wrong.** It
decomposed the wrong object: the 43/57 split is of the *total forecast*
`sP·EffSum/100`, not of the signal.

### Exact additive decomposition

```
E_pace = D·E/100 = D·Ebar/100 + D·(E−Ebar)/100 = E_poss + E_eff
max|E_pace − (E_poss+E_eff)| = 5.3e-15          Ebar = 226.574
```

| component | sd | var | share of var(E_pace) |
|---|---|---|---|
| **E_poss** (possession channel) | 3.8869 | 15.1078 | **99.38%** |
| E_eff (efficiency channel) | 0.1241 | 0.0154 | **0.10%** |
| 2·Cov(E_poss, E_eff) | | 0.0784 | 0.52% |
| **total** | 3.8989 | 15.2016 | 100.00% |

| object | pace | efficiency |
|---|---|---|
| total forecast `sP·EffSum/100` | 43.1% | 56.9% |
| **`E_pace` signal** | **99.38%** | **0.10%** |

**Why they differ.** `E_pace` is identically

```
E_pace = sP·EffSum/100 − (open − a)/b          verified to 8.6e-14
```

a *difference* between our total forecast and the affinely rescaled opener. The
book's efficiency view and ours largely agree, so efficiency differences out.
`EffSum` survives only as a unit converter — possessions into points.

### Selection impact of removing the multiplier

| rule | bets | hit | se | ROI |
|---|---|---|---|---|
| `|E_pace| ≥ 4.77` — FROZEN | 1,614 | 54.83% | 1.24 | +4.68% |
| `|E_poss|` matched count | 1,614 | 55.20% | 1.24 | +5.39% |

Overlap **97.7%** (1,585 of 1,622). The entire difference is 74 swapped games:

```
dropped by the possession rule   37 live, 19 wins (51.4%)
added   by the possession rule   37 live, 25 wins (67.6%)
net                              +6 wins  ->  +6/1614 = +0.37pp
H0 sd of net wins 4.30   z = +1.39   p = 0.163
```

**A clean null.** The two variables are nearly the same object, and the
difference between them is six games' worth of coin flips.

---

## WHAT THIS CHANGES

**Nothing in the frozen 2026-27 rule**, which is untouched: threshold 4.77,
`side = sign(E_pace)`, the state engine, the shrinkage constants, the settlement
line. The only edits are a comment at the pace update, a comment at the `E_pace`
computation, and this file.

**The opponent-purification branch is closed.** There is nothing to recover.

**The possession-only threshold is demoted, not promoted.** It was worth
recording while `E_pace` was believed to be 57% efficiency; at 0.10% it is a
0.6%-of-variance change affecting 2.3% of selections, with p = 0.163. Logged in
`CANDIDATES_2027_28.md` at that weight, which is low.
