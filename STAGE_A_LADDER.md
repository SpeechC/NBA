# STAGE A — LADDER RECONSTRUCTION (market measurement only)

No basketball inputs. No outcomes. Question: **can each game's ladder be
represented by a low-dimensional distribution characterised by mu and sigma, and
are those parameters robust to the estimation method?**
`stageA.py`, `stageA5.py`. 1,318 pregame ladders, 14,471 rungs, median 11 rungs,
median span 30 pts, mean quote width 3.60c. Midpoints are **not** used as a
primary estimator: WLS is primary, interval/censored is the robustness standard.

## A1/A2 — ONE (mu, sigma) LARGELY DOES REPRODUCE THE LADDER

```
param    WLS mean   WLS sd   INT mean   INT sd
mu        229.791    8.299    229.791    8.297
sigma      18.006    1.070     17.975    1.052

per-rung |error| vs mid   MAE 0.909c   RMSE 1.969c
per-game max|error|       median 1.603c   p90 3.460c
SPREAD-AWARE: fitted model lies INSIDE the quoted [bid,ask] band on 78.2% of rungs
mean excursion outside the band   WLS 0.108c   INTERVAL 0.100c
```

**1.75% of ladders (23/1,318) have max|error| > 10c, and they are junk books** —
mean quote widths of 44-47c. Excluding them the per-rung MAE falls 0.909c ->
**0.790c**. They should be excluded downstream.

## A5 — UNIVERSAL COLLAPSE: **YES, decisively**

Every rung from every game transformed to `z = (K - mu_g)/sigma_g` and pooled:

```
z bin            n    market   Normal   gap(c)   within-bin sd(c)
(-1.00,-0.75] 1275    0.8031   0.8048   -0.174              2.850
(-0.25, 0.00] 1976    0.5520   0.5496   +0.233              3.069
( 0.50, 0.75] 1805    0.2746   0.2672   +0.749              3.428
( 1.00, 1.25]  194    0.1558   0.1407   +1.508              3.919

POOLED sd of (market - Normal(z)) over ALL 14,471 rungs = 1.964c
sd of the raw market probabilities                      = 19.896c
=> the z-transform removes 99.03% of rung-price variance
```

**The ladder is essentially a two-parameter machine.** Fourteen thousand prices
from 1,318 different games collapse onto a single normal curve to within ~2
cents. This is the Stage A result the programme was looking for.

## A4 — the over-side gap is MOSTLY A QUOTE ARTIFACT

The gap rises monotonically in z (−0.17c to +1.51c), which looks like right
skew. It is largely not:

```
                     bid-model   mid-model   ask-model   width
cheap (mid<0.30)      -1.460c     +0.500c     +2.460c    3.92c
mid   (0.30-0.70)     -1.660c     +0.062c     +1.783c    3.44c
rich  (mid>0.70)      -1.818c     +0.062c     +1.943c    3.76c

restricted to TIGHT books (width <= 2c):
cheap +0.266c    mid -0.080c    rich +0.121c
```

Bid sits below and ask above the model by roughly equal amounts in every
bucket — that is the spread, not the distribution. The cheap-rung mid excess
**halves (0.500c -> 0.266c) when books tighten**, so most of it is a quote-width
effect. A small residual remains and cannot be characterised further (below).

## A6 IS NOT RUNNABLE — and this is the key limitation

```
z coverage: p1 = -1.07   p99 = +1.03
|z| > 1.5 : 0.00% of rungs      |z| > 2 : 0.000%
```

**The ladder spans only about +-1.1 sigma.** Normal, Student-t and skew-normal
are numerically near-identical over that interval. **Tail shape is not
identifiable from this data at all**, and no amount of modelling fixes it. Per
A6's own rule — let the residual demand the extra parameter — nothing here
demands one, and nothing here could distinguish one. **Do not add t or skew.**

## A3 — mu IS IDENTIFIED; sigma IS NOT, TO THE SAME STANDARD

```
corr(mu_WLS,  mu_INT)  = 0.999926   mean diff -0.0003   sd diff 0.1007
corr(sig_WLS, sig_INT) = 0.948315   mean diff +0.0308   sd diff 0.3416

disagreement vs market conditions:
  quote width   |d(mu)| +0.0132     |d(sigma)| +0.1977
  volume        |d(mu)| -0.0199     |d(sigma)| -0.0978

sigma vs quote width:   WLS +0.2609    INTERVAL +0.2354
```

**This is exactly the outcome that was flagged as the risk: the centre is
cleanly identified, the variance is not.** Estimator disagreement on sigma grows
with quote width (+0.198), and **sigma itself still correlates with quote width
at +0.24 to +0.26 even after the Link 7 estimator fix.**

That is ~6-7% of sigma's variance tied to a market-microstructure quantity, on
top of the ~14% pure noise implied by the earlier split-half reliability of
0.864. Roughly **79% of sigma's variation is real**.

### Binding consequence for Stage C

**Stage C must not regress sigma on basketball states without controlling for
quote width**, or it will partly model the measurement process — the precise
concern that motivated Stage A. Required: report every sigma coefficient with
and without a quote-width control, and with the WLS and interval estimators
separately. If a basketball coefficient depends on which is used, it is not a
finding.

The Link 6/7 result that 3PA rate predicts ladder sigma **must be re-run under
this protocol before it is relied upon.**

## A7 — FROZEN LADDER REPRESENTATION

```
P(T > K) = 1 - Phi( (K - mu) / sigma )
mu     : WLS and INTERVAL agree to corr 0.999926 -> use either; canonical = mean of the two
sigma  : corr 0.948, width-contaminated -> canonical = mean of the two, ALWAYS reported
         alongside quote width, and cross-checked on both estimators
exclude: ladders with max|error| > 10c (1.75%, junk books)
no skew or t parameter: not identifiable within +-1.1 sigma
```

## What Stage A establishes, and what it does not

**Establishes:** the linemaker's ladder is a mechanically generated
two-parameter object. Recovering `mu` and `sigma` reduces the reverse-
engineering problem from 11 prices per game to 2 numbers, and `mu` is recovered
essentially without error.

**Does not establish:** anything about the tails, because the ladder does not
reach them; or that `sigma` is clean enough to model directly, because it is
not — it carries a measurable quote-width component that Stage C must handle.

**Next:** Stage B on `mu`, which is the well-identified parameter, and which
must be **cross-fitted** — Stage 1's R2 0.8689 is in-sample and is not an honest
estimate of how well PIT basketball state reproduces the market's centre.
