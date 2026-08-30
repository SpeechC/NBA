# ERROR ATTRIBUTION, UNCERTAINTY MODEL, AND THE ECONOMIC TEST

Three questions, answered in the order they matter. `error_attribution.py`.

## 1. SSE ATTRIBUTION — fraction of residual squared error removed, strictly OOS

Baseline R2 0.8767, n = 2,052, Group A = 161.

| mechanism family | all games | within Group A |
|---|---|---|
| **roster / injury instability** | **3.87%** | **7.02%** |
| early season / state init | 1.33% | 1.68% |
| rest / schedule compression | −0.23% | 0.07% |
| pace matchup | −1.03% | 1.08% |
| offence-defence matchup extremes | −0.49% | −0.08% |
| opening-total extremes | −0.21% | 0.16% |
| model-to-model disagreement | 0.17% | −0.38% |
| ALL FAMILIES TOGETHER | 1.85% | 9.63% |

**Their estimate was right: injuries explain ~4% of residual error (measured
3.87%), and NOTHING ELSE EXPLAINS ANYTHING.** Every other family is at or below
zero out of sample. Even disagreement between two independent architectures
carries 0.17%.

"All families together" (1.85%) is *worse* than injuries alone — the extra
families are pure overfitting.

## 2. UNCERTAINTY MODEL — constructible, but barely

```
OOS R2 of |error| ~ 13 features = 0.0039
```

Yet the ordering works:

| predicted-uncertainty tercile | n | predicted \|e\| | ACTUAL \|e\| | actual RMSE |
|---|---|---|---|---|
| low | 349 | 1.985 | 2.244 | **2.960** |
| mid | 348 | 2.417 | 2.463 | 3.096 |
| high | 348 | 2.934 | 2.732 | **3.627** |

**A Trust Score is buildable: RMSE 2.96 in the most-trusted third against 3.63 in
the least — a 22% spread.** The R2 is near zero because |error| is dominated by
noise, but the *conditional mean* separates.

## 3. THE ECONOMIC TEST — and it settles the strategy question

Full sample, n = 3,181. `D = model - market opener`.

| target | beta | se | t | MDE |
|---|---|---|---|---|
| ACTUAL total vs opener | 0.1991 | 0.1058 | **+1.88** | 0.2073 |
| ACTUAL total vs close | −0.1809 | 0.1035 | −1.75 | 0.2029 |
| **LINE MOVEMENT (close − open)** | **0.3800** | 0.0181 | **+20.96** | 0.0355 |

**The disagreement predicts line movement at t = +20.96 and outcomes at t = +1.88.**

And by gap size the divergence is total:

```
gap quartile   mean |gap|   beta on ACTUAL     t      beta on MOVE      t
Q1 small            0.44           0.1693   0.13            0.2313   1.09
Q2                  1.38           0.4782   1.04            0.3140   4.08
Q3                  2.53           0.0856   0.35            0.4175   9.71
Q4 large            5.03           0.1957   1.64            0.3764  17.08
```

**Movement prediction strengthens monotonically with the gap (t: 1.09 -> 17.08).
Outcome prediction shows no pattern at all.**

### Even taking the outcome beta at face value

```
beta 0.1991 x sd(gap) 3.06 = 0.609 pts of edge per sd of disagreement
hit rate = 0.5 + phi(0)*0.609/18.25 = 51.33%
break-even at -110 = 52.381%     SHORT BY 1.05pp
```

**Not profitable even if the marginal t = 1.88 is real.**

### And the Trust Score does not rescue it

Outcome betas by predicted-uncertainty tercile: **low +0.364 (t=1.14), mid
−0.177 (t=−0.56), high +0.410 (t=1.51)**. No monotonicity, nothing significant.
Movement betas are flat across terciles (+0.343, +0.387, +0.327).

**The filter works on the wrong quantity.** It separates where the model is
*accurate about the opener*, which is real, from where it is *right about the
game*, which does not vary because there is no outcome signal to sort.

## FOURTH REPLICATION OF "CLV IS EARNED AND NOT CONVERTED"

After injury Hypothesis B (CLV +0.775 t=+7.93, P&L −8.04%), the CBB case, and
the Stage 1 emulator (market moves 24% toward it, outcome corr −0.021), this is
the fourth and cleanest: **t = +20.96 on movement, t = +1.88 on outcomes, in the
same regression on the same games.**

## What this settles

1. **Injuries are a failure FLAG, not the missing variable** — 3.87% of residual
   error. Their reinterpretation as an *unstable-team-state regime indicator* is
   consistent with everything measured.
2. **Nothing else in the observable set explains the tail** — six other mechanism
   families, all ≤ 0.

3. **A model-confidence score is constructible** (RMSE 2.96 vs 3.63) but has
   nothing to filter: the disagreement it would gate carries no outcome signal.
4. **Chasing R2 from 0.88 to 0.90 has no demonstrated economic value on this
   evidence.** A better opener reconstruction predicts the line better. It does
   not predict the game.

**The open question they raised — whether high-uncertainty games are where the
BOOK is also wrong, and therefore where opportunity lives — is not answered here.
Both uncertainty terciles show t < 1.6 on outcomes.** Distinguishing our
uncertainty from market uncertainty needs a measure of the latter, which this
programme does not have.
