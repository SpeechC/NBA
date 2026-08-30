# DOES PACE VOLATILITY MODULATE THE PACE SIGNAL? — the decisive test

`pace_interaction.py`, n = 2,073 (2022+).

## 1. THE INTERACTION TEST — no attenuation detected

```
baseline:            PaceGapPoints  +0.3263 (t=+3.23)

with interaction:    PaceGapPoints  +0.3248 (t=+3.20)
                     volX (z)       -0.2634 (t=-0.62)
                     GAP x volX     -0.0429 (t=-0.47)

H: beta3 < 0     95% CI [-0.2201, +0.1343]   one-sided p = 0.3176
MDE(80%, one-sided) = 0.2248  ->  UNDERPOWERED for even a 50% attenuation
```

**`beta3` is negative as predicted but tiny and indistinguishable from zero.** At
+1 sd of volatility the slope falls 0.325 -> 0.282, a 13% attenuation. **A 50%
attenuation would require `beta3` ~ −0.16 and our MDE is 0.225, so we could not
detect it either way.** The test is inconclusive rather than negative.

## 2. The tercile split is NON-MONOTONE

| volx tercile | n | beta(gap → actual) | t | beta(gap → move) | t |
|---|---|---|---|---|---|
| low vol | 691 | 0.4480 | 2.62 | 0.2305 | 7.29 |
| mid | 691 | 0.1918 | 1.03 | 0.2354 | 7.20 |
| high vol | 691 | 0.3069 | 1.82 | 0.2703 | 8.56 |

**low > high > mid.** No clean attenuation. Movement betas are flat-to-rising
(0.231, 0.235, 0.270) — the market incorporates the pace gap *slightly more* in
volatile games, the opposite of a reliability story.

## 3. The bucket grid contradicts itself across gap size

| gap | volatility | n | hit rate | avg \|edge\| |
|---|---|---|---|---|
| small | low vol | 346 | **54.3%** | 1.24 |
| small | mid | 360 | 52.2% | 1.26 |
| small | high vol | 331 | **50.8%** | 1.30 |
| LARGE | low vol | 345 | 53.3% | 4.99 |
| LARGE | mid | 331 | 53.2% | 4.99 |
| **LARGE** | **high vol** | 360 | **55.0%** | 5.12 |

**Within SMALL gaps the predicted pattern appears (54.3 -> 52.2 -> 50.8). Within
LARGE gaps it reverses, and high-volatility is the BEST cell (55.0%).** The large
cells are the ones that would carry a bet, so the hypothesis fails where it
matters.

A further reason to distrust the small/low cell: a 1.24-point edge implies about
52.7%, not 54.3%. That cell is noise-inflated.

## 4. CORRECTION — the Vol_H x Vol_R interaction is NOT structurally necessary

Their proposed test, run directly:

```
u^2 = a + b_H Vol_H + b_R Vol_R + b_I Vol_H x Vol_R

Vol_H           +0.8771 (t=+2.07)
Vol_R           +0.8826 (t=+2.09)
Vol_H x Vol_R   +0.1585 (t=+0.41)
```

**The two main effects carry it; the interaction adds nothing.** My
`PACE_VARIANCE_V2` claim that "the volatility INTERACTION is what separates" is
**withdrawn** — `volx` sorted games well because it is a monotone-ish transform
of the two volatilities, not because the product term is structural. The nearly
identical main-effect coefficients (0.877 / 0.883) say pace variance is
**additive** in the two teams' volatilities.

That also removes the anchoring mechanism they proposed. There is no evidence
that "neither side provides an anchor" produces super-additive variance.

## Verdict, and it matches their own priority ordering

They wrote: *"The first two are much more important than the third."* Confirmed.

| phenomenon | status |
|---|---|
| **pace LEVEL / directional gap** | **robust: t = +3.23 to +3.72 on outcomes; survives every cut** |
| pace DRIFT | directional, t = +2.26; ~0.5% of pace variance but real |
| pace UNCERTAINTY | additive in team volatilities, ~0.7 pts of total sd, **no demonstrated betting modulation** |

**Keep the directional pace signal. Drop the uncertainty modulation** — not
because it is disproven, but because it is unmeasurable at this sample size and
non-monotone where it can be seen.

## CONSEQUENCE FOR THE FROZEN PREREG — resolved

`PACE_VARIANCE_V2` flagged that the prereg's `sigma_P` gate does not separate
(p = 0.4313) and recommended replacing it with the `volx` tercile split. **That
recommendation is now withdrawn too**: `volx` is not structurally necessary, and
it provides no betting modulation (β3 t = −0.47, non-monotone terciles).

**Revised recommendation for `PREREG_2026_27_PROSPECTIVE`: DROP the secondary
`<220 x high sigma` hypothesis entirely**, rather than re-specify its gate. Both
candidate definitions of the uncertainty split have now failed on their own
terms, and the cell's original 59% rested on one of eight post-hoc bins.

**H1 (pace gap) and H2 (overreaction) are unaffected and remain as registered.**
