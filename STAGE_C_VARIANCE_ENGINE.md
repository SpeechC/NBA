# STAGE C — VARIANCE-ENGINE RECONSTRUCTION

Target: ladder sigma (canonical = mean of WLS and INTERVAL, junk ladders
excluded per A7). No outcomes. n = 1,138. `stageC.py`.

**Constraint:** ladder sigma exists for one season only, so cross-fitting is
**chronological within season** — train on games 1..k, predict the next 100,
rolling. **Ceiling: ~86%** (14% measurement noise, disjoint-rung split-half).

## C1-C6 — OOS PEAKS AT C3 AND THEN DEGRADES

| model | IS R2 | IS RMSE | **OOS R2** | OOS RMSE | +width IS R2 |
|---|---|---|---|---|---|
| C0 baseline | 0.0000 | 0.9430 | −0.0169 | 0.8202 | 0.0517 |
| C1 + mu (scale) | 0.0970 | 0.8960 | 0.1177 | 0.7555 | 0.1349 |
| C2 + pace | 0.1041 | 0.8925 | 0.1213 | 0.7516 | 0.1409 |
| **C3 + shot composition** | 0.1238 | 0.8827 | **0.1385** | **0.7405** | 0.1585 |
| C4 + FT / turnover rate | 0.1245 | 0.8823 | 0.1214 | 0.7460 | 0.1588 |
| C5 + team scoring dispersion | 0.1305 | 0.8793 | 0.1042 | 0.7463 | 0.1618 |
| C6 + \|spread\|, rest | **0.1483** | 0.8703 | **0.0642** | 0.7467 | 0.1759 |

**C6 has the best in-sample R2 and less than half the OOS R2 of C3.** With
n = 1,138 the later blocks are fitting noise. **The honest Stage C model is C3:
`mu + pace + shot composition`, OOS R2 0.1385.**

## The physical skeleton IS recovered — both benchmarks matched

Width controlled, all three estimators:

```
POISSON  d(sigma)/d(pace) = +0.0911
  WLS        +0.0943 (t=+3.26)  CI [+0.0376, +0.1510]   bench INSIDE
  INTERVAL   +0.0920 (t=+3.20)  CI [+0.0356, +0.1483]   bench INSIDE
  canonical  +0.0931 (t=+3.28)  CI [+0.0375, +0.1488]   bench INSIDE

SHOT-MIX benchmark = +4.87
  WLS        +4.1558 (t=+3.83)  CI [+2.0276, +6.2840]   bench INSIDE
  INTERVAL   +4.2755 (t=+3.96)  CI [+2.1611, +6.3898]   bench INSIDE
  canonical  +4.2157 (t=+3.96)  CI [+2.1276, +6.3037]   bench INSIDE
```

**The linemaker's variance rule uses possessions at the Poisson rate and shot
mix at approximately the shot-variance rate**, and this survives both estimators
and the quote-width control. That is a genuine structural recovery.

Estimator robustness on the full model: WLS 0.1732, INTERVAL 0.1698, canonical
0.1759 (width controlled). No coefficient depends on the choice.

## Team scoring dispersion — significant in-sample, NOT a finding

```
WLS -0.0409 (t=-2.19)   INTERVAL -0.0441 (t=-2.37)   canonical -0.0425 (t=-2.32)
```

Negative and significant on all three: the ladder assigns **narrower** sigma to
matchups whose teams have higher prior scoring dispersion. This reproduces the
Link 6 oddity (`esd` −0.063, t=−2.41) on the corrected estimator.

**But adding it (C5) DEGRADES OOS from 0.1385 to 0.1042.** A coefficient that is
significant in-sample and harms out-of-sample prediction is not a finding.
**Link 4b's conclusion stands: the ladder does not use team dispersion.**

## What remains — the honest accounting

```
sd(ladder sigma)             0.943
explained OOS (C3)           13.85%   -> residual sd 0.875
measurement noise (~14%)              -> noise sd    0.353
REAL, STRUCTURED, UNEXPLAINED         -> sd 0.80 points
```

**About 0.80 points of the linemaker's sigma is real, systematic, and
unrecovered** — roughly 4.4% of a sigma near 18. That is a large quantity: if it
could be predicted it would be an economically meaningful mispricing signal, and
it cannot be, by anything in this programme.

## Where the A-B-C arc leaves the reverse-engineering project

| object | status |
|---|---|
| ladder shape | **SOLVED** — two-parameter normal, z-transform removes 99.03% of rung-price variance |
| ladder centre mu | **SOLVED, but trivially** — it IS the sportsbook close (R2 0.9942); PIT basketball reaches only R2 0.7670 OOS, worse than quoting the opener |
| ladder sigma skeleton | **RECOVERED** — pace at the Poisson rate, shot mix at the shot-variance rate, robust to estimator and width |
| ladder sigma variation | **NOT RECOVERED** — OOS R2 0.1385 of an ~86% ceiling; 0.80 pts of real structure unexplained |
| tail shape | **NOT IDENTIFIABLE** — ladder spans only +-1.1 sigma |

**The machine is understood in form and not in detail.** We know it is
`Normal(mu, sigma)` with `mu` imported from the sportsbook close and `sigma`
built on possessions and shot mix at physically correct rates. We cannot
reproduce what it actually outputs.

**The binding constraint is data, not method.** One season of ladders (n=1,138)
cannot support the model complexity Stage C needs — C6 demonstrated that
directly by halving its own OOS R2. **2026-27 roughly doubles the ladder sample**
and is the single highest-value input to this programme.
