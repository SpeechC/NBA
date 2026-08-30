# PACE AS A SIGNAL — decomposing the 30.7% into drift, volatility, and disagreement

`pace_signal.py`. Everything strictly prior-only; economics on 2022+ (n = 3,299).

## 1. PACE UNCERTAINTY IS NOT FORECASTABLE — the sigma_P leg FAILS

Predicting `|pace error|` from prior-only inputs (EWMA sd of each team's pace
residuals, short-vs-long memory disagreement, home/road disagreement):

| predicted sigma_P tercile | n | predicted | **ACTUAL sd(dPace)** |
|---|---|---|---|
| low | 1,100 | 3.877 | **3.998** |
| mid | 1,099 | 3.971 | **3.869** |
| high | 1,100 | 4.068 | **4.123** |

**The terciles do not separate** — actual dispersion runs 3.87 to 4.12 and is
non-monotone. **Pace uncertainty cannot be predicted before tip**, so `Z_pace`
adds nothing over the raw gap (t = 3.68 vs 3.72) and the confidence-weighting
scheme has nothing to weight with.

## 2. BOOK-IMPLIED PACE, BY INVERSION — this works

```
P_book = 100(Open - a) / (b * EffSum)
P_book mean 98.63   our sP mean 98.80
gap sd 2.041 possessions = 4.71 POINTS of total
```

## 3. THE PACE GAP IS THE STRONGEST OUTCOME SIGNAL IN THE PROGRAMME

| predictor | → close−open | t | **→ ACTUAL−open** | **t** |
|---|---|---|---|---|
| **pace gap (points)** | 0.2030 | 16.67 | **0.2500** | **+3.72** |
| Z_pace (gap / sigma) | 1.8683 | 16.70 | 2.2727 | +3.68 |
| pace DRIFT (mu5) | 0.5587 | 13.81 | 0.4997 | +2.26 |
| pace VOLATILITY (sd10) | 0.1918 | 2.33 | −0.5583 | −1.28 |

**Their drift/volatility split is confirmed exactly as predicted: DRIFT is
directional (t = +2.26), VOLATILITY is not (t = −1.28).**

And the headline: **the pace-specific gap predicts outcomes at t = +3.72, versus
t = +1.88 for the aggregate model gap.** Isolating the pace channel roughly
doubles the outcome signal.

## 4. The grid is monotone in the gap

| gap | sigma | n | avg actual−open | Over % |
|---|---|---|---|---|
| neg gap | low | 537 | −0.643 | 45.4 |
| neg gap | high | 563 | −0.583 | 46.7 |
| mid | low | 598 | +0.657 | 51.5 |
| mid | high | 501 | +0.225 | 51.7 |
| **POS gap** | **low** | 515 | **+2.320** | **53.2** |
| POS gap | high | 585 | +1.479 | 52.1 |

Monotone across the gap (−0.6 → +0.4 → +1.9), and within the positive tail **low
uncertainty beats high (53.2% vs 52.1%)** — the direction they predicted, though
the sigma model itself is too weak to exploit.

## 5. ECONOMICS — the first thing in this programme to reach break-even

```
                  beta     edge      hit      ROI
point estimate  0.2500   1.177   52.58%   +0.38%
lower 95% CI    0.1183   0.557   51.22%   -2.22%
upper 95% CI    0.3817   1.798   53.94%   +2.97%
break-even                       52.381%
```

**52.58% at the point estimate against a 52.381% break-even — marginally
positive, with a confidence interval that straddles it.** ROI +0.38% [−2.22%,
+2.97%].

Every prior signal in this programme sat below break-even. This one sits on it.

## 6. Their specific high-total hypothesis is REFUTED

| opening total | sigma_P | n | avg actual−open | Over % |
|---|---|---|---|---|
| <220 | low | 264 | −0.557 | 48.1 |
| **<220** | **high** | 278 | **+3.016** | **59.0** |
| 220–230 | low | 727 | +0.860 | 49.9 |
| 230–240 | high | 571 | −0.026 | 48.2 |
| 240+ | low | 114 | +2.206 | 57.0 |
| **240+** | **high** | 166 | **−0.518** | **47.0** |

**`E[Actual−Open | Open>=240, high pace SE] = −0.518` with a 47.0% Over rate.
The hypothesis is refuted in its own terms.**

The `<220 x high sigma` cell at **59.0% Over (n=278)** is striking — but it is
**one cell of eight**, at roughly 2 standard errors, in a grid chosen after
seeing the data. **This programme has been burned by exactly that pattern**
(`papers/winkelmann_efficiency_simulations`: efficient markets throw significant
subgroup findings most of the time). **It is a candidate, not a finding.**

## Status and what is required next

**Established:** pace disagreement with the book is the strongest outcome
predictor found here (t = +3.72), the drift/volatility separation behaves exactly
as theorised, and pace uncertainty is not forecastable.

**Not established:** that it is profitable. The point estimate clears break-even
by 0.20pp with a CI spanning [−2.22%, +2.97%] ROI.

**This is now a SEARCH RESULT on data that has been examined repeatedly.** Under
this programme's standing rules it cannot be traded on. It requires a
pre-registration fixing: the pace-gap construction, the `Actual − Open` primary
endpoint, the break-even gate, and the `<220 x high sigma` cell as a *separate*
secondary hypothesis rather than part of the primary family — tested on 2026-27,
which is also the season that resolves the `GAP_TO_OUTCOME` overreaction question
needing ~823 more games.
