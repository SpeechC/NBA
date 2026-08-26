# The attrition fix — bracketing-independent implied line (2026-08-26)

`implied_line.probit_line` replaces median-crossing. A ladder is a sampled
survival function, so under a normal implied distribution
`K = mu + sigma * z` with `z = Phi^-1(1-p)`: regress strike on the probit of
price and the intercept is the line, the slope is the width. No crossing
needed; uses every rung; returns diagnostics (`extrap`, `r2`, `n`).

## Validation

**A. Agreement** where median-crossing works — both estimate the p=0.5 point,
so they must match:

| | corr | mean diff | sd | \|diff\|>1pt |
|---|---|---|---|---|
| WNBA weighted | 0.9997 | +0.18 | 0.35 | 3.3% |
| NBA weighted | 0.9884 | −0.04 | 1.48 | 25.5% |

phi(z)^2 weighting beat unweighted in both leagues. NBA is noisier because its
ladders carry wider quotes.

**B. Recovery.** WNBA 183 -> 239 ladders (+31%). NBA 220 -> 324 (+47%).
Rescued ladders extrapolate a median of only 0.27 sigma (WNBA) / 0.05 (NBA) —
they were failing the bracket test on a technicality, not being invented.

## What it did to the two suspect findings

**WNBA halftime over-bias: SURVIVES.** I had attributed it to attrition. On
31% more games it barely moves: +2.76 (incumbent, n=182) -> **+2.63 pts,
CI [+1.03,+4.24] (probit, n=238)**, and it holds on well-determined ladders
(+2.71 on r2>=0.95). Sample mean total falls 178.0 -> 176.1 against a league
174.7, so selection shrank but did not explain the result. **I was wrong to
call this attrition.**

**NBA under-reaction: DISSOLVES.** Full sample gives s=0.727 (n=324) vs
0.889 (n=220) — apparently *more* under-reaction. But splitting on ladder fit
quality shows where it lives:

| subset | n | s(H1) | benchmark | gap |
|---|---|---|---|---|
| r2 >= 0.95 | 171 | **0.958** | 0.988 | **−0.03** |
| r2 < 0.95 | 153 | 0.604 | 1.107 | −0.50 |
| interpolated | 255 | 0.769 | 0.963 | −0.19 |
| extrapolated >0.25 sigma | 28 | 1.149 | 1.215 | −0.07 |

On **well-determined ladders the NBA halftime line is efficient** (gap −0.03).
The apparent under-reaction is concentrated entirely where the ladder is
badly determined — and those games have sd(H1) 14.6 vs 10.0, i.e. the extreme
games where a poorly-pinned line gets attenuated toward the ladder centre.
That attenuation makes L look unresponsive to H1 and manufactures exactly the
"under-reaction" the programme has chased since the beginning.

Caveat, stated plainly: `r2` is a property of the ladder, not of the outcome,
so conditioning on it is a measurement-quality filter rather than selection on
the dependent variable. But r2 correlates with sd(H1), so the two subsets are
not exchangeable and this is not a clean experiment. The defensible claim is
narrow: **the NBA under-reaction is not robust to how the line is measured**,
which is enough to stop building on it.

## Standing consequence

Use `probit_line` for any in-game ladder work, report `extrap` and `r2`
alongside every estimate, and treat results that appear only in the low-r2
subset as measurement artefacts until shown otherwise.
