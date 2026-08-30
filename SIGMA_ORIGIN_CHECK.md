# PRE-STAGE-C CHECK — is ladder sigma imported from the sportsbook?

Stage B found the ladder **centre** is the sportsbook closing total (RMSE 0.584,
R2 0.9942, 93.1% within one point). If sigma were likewise imported, Stage C
would be modelling the wrong object. `sigma_origin.py`, n = 1,138, canonical
sigma = mean of WLS and INTERVAL, junk ladders excluded per A7.

## ANSWER: NO. Sigma is not imported, and it carries real basketball information.

## 1. Where sigma's variation comes from

```
mu (the total level) alone      R2 0.0970
QUOTE WIDTH alone               R2 0.0517
mu + quote width                R2 0.1349
+ n rungs, volume               R2 0.1784
```

**Sigma is NOT mechanically derived from the total.** Unlike the centre — which
the close reproduces at R2 0.9942 — mu explains under a tenth of sigma. Sextiles
rise monotonically (17.577 at mu 218.9 to 18.511 at mu 242.0) but the
relationship is weak.

**~82% of sigma's variation is unexplained by every market-side quantity
available.**

## 2. Head to head, quote width always controlled

```
block                                        R2    dR2 over width
quote width only (the artifact floor)    0.0517
+ SPORTSBOOK (mu, |line move|, |spread|) 0.1532          +0.1015
+ BASKETBALL (pace, 3PA rate)            0.1318          +0.0801
+ BOTH                                   0.1750          +0.1234
BASKETBALL incremental over width+sportsbook             +0.0219
```

Sportsbook-side explains slightly more than basketball-side, but **basketball is
not redundant** — it adds +0.0219 beyond width and every sportsbook quantity.

## 3. THE LINK 6/7 CLAIM, RE-RUN UNDER THE STAGE-A PROTOCOL — and it SURVIVES

Stage A required this before the 3PA result could be relied on: both estimators,
with and without a quote-width control.

```
estimator    width ctrl   3PA coef      t              95% CI
WLS          no            +4.7946   4.83   [+2.8473, +6.7419]
WLS          YES           +4.5102   4.63   [+2.6018, +6.4186]
INTERVAL     no            +4.7367   4.81   [+2.8074, +6.6661]
INTERVAL     YES           +4.4798   4.63   [+2.5820, +6.3777]
canonical    YES           +4.4950   4.70   [+2.6211, +6.3689]
```

**All four specifications agree to within 0.32, the width control moves the
coefficient by only −0.27, and t stays at 4.6-4.9.** This is exactly the
robustness Stage A demanded and it passes.

### This RETRACTS Link 6d's "shortfall"

```
Link 6   (contaminated mid-based sigma)              +3.259
Link 6d  (contaminated sigma, controlling for sprd)  +2.477  -> "significantly below benchmark"
HERE     (Stage A canonical, width controlled)       +4.495
CORRECTED PHYSICAL BENCHMARK (Link 6b)               +4.87
```

**The ladder prices shot mix at essentially the physically correct rate.** The
benchmark 4.87 sits inside every CI above, and the point estimates are within
8% of it. Link 6's "the ladder is at 61-67% of theory" and Link 6d's
"significantly below" were **both artifacts of the contaminated estimator** — and
6d compounded it by conditioning on the artifact instead of fixing the
instrument.

This is the third time the estimator, not the hypothesis, produced the finding.

## 4. Measurement noise, stated honestly

```
WLS-vs-INTERVAL disagreement sd 0.3077 -> canonical noise >= 0.154 (>= 2.7% of variance)
```

**That is a LOWER bound and should not be quoted as the noise level** — the two
estimators read the same quotes, so their errors are correlated. The earlier
**split-half estimate on DISJOINT rungs is the honest one: full-ladder noise sd
0.474 against a sigma sd of ~1.29, i.e. roughly 14% of sigma's variance is
measurement noise.**

So the explainable ceiling for Stage C is ~86%, and we currently reach 17.5%.

## Verdict for Stage C

**Stage C is worth running and is not modelling the wrong object.** Sigma is not
imported from the sportsbook, is not a mechanical function of the total, and
responds to basketball state at the physically correct magnitude for shot mix.

**But the honest framing is that sigma is mostly unexplained.** Everything
tested — the total level, line movement, spread, quote width, rung count,
volume, pace and shot mix — accounts for 17.5% of a quantity that is ~86%
signal. Stage C should be framed as explaining a largely open residual, not as
completing a nearly-recovered rule.

**Protocol carried forward, mandatory:** every Stage C sigma coefficient is
reported on WLS, INTERVAL and canonical, with and without a quote-width control.
A coefficient that depends on which is used is not a finding.
