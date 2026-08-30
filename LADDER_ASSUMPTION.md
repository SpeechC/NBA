# THE KEY ASSUMPTION BEHIND THE LADDER SHAPE

```
P(Total > K) = 1 - Phi( (K - mu) / sigma )
```

Choosing the normal commits the linemaker to four things: **symmetry**, **no fat
tails**, **one sigma across all strikes** (no smile), and **continuity** for a
discrete integer score. Underneath all four sits a single claim:

> **The game total is a sum of many small, near-independent scoring events, so
> the Central Limit Theorem applies.**

## The microfoundation is CORRECT — we measured it

`Link 6b` measured the premise directly on 18,977 team-games without realising
it was the ladder's foundation:

```
3PT   phi 0.9883   rho -0.00035     (essentially EXACTLY binomial)
2PT   phi 1.0583   rho +0.00110
FT    phi 1.1219   rho +0.00571
cross-channel correlations:  3PT-2PT -0.019,  3PT-FT +0.011,  2PT-FT +0.001
```

**Shots really are independent.** There is no hot hand at team-game level and a
hot night is not hot everywhere. The CLT premise holds where it needs to.

## But the assumption is measurably FALSE overall

```
n=9,489    SKEW +0.2319 (t=+9.22)    EXCESS KURTOSIS +0.3944 (t=+7.84)
Jarque-Bera 146.54, p < 0.0001
```

The realised distribution is **right-skewed and fat-tailed**, both overwhelmingly
significant.

## And yet the linemaker gets away with it — look WHERE it fails

```
|z| >     normal %   actual %   ratio        within the ladder's span?
1.0         31.731     30.330   0.956        YES
1.1         27.133     27.021   0.996        YES  <- the ladder's edge
1.5         13.361     12.530   0.938        no
2.0          4.550      4.331   0.952        no
2.5          1.242      1.381   1.112        no
3.0          0.270      0.411   1.522        no
```

**Inside +-1.1 sigma — precisely the ladder's span — the normal is accurate to a
ratio of 0.996.** The violation is entirely beyond 2.5 sigma, where the true
distribution carries 11% to 52% more mass than Gaussian.

The skew is in the same place:

```
beyond 1.0 sigma:  over 15.207%  under 15.123%   diff +0.084pp   symmetric
beyond 2.0 sigma:  over  2.656%  under  1.676%   diff +0.980pp   over 1.58x
beyond 2.5 sigma:  over  0.980%  under  0.400%   diff +0.580pp   over 2.45x
```

**Near the money the distribution is symmetric to 0.08pp. Far out, the over side
is 1.6x to 2.5x the under side.**

## The mechanism, and why the CLT does not cover it

The CLT governs the sum given a **fixed** number of events. It does not govern a
**random** number of them. Overtime adds possessions, and it adds them **only
upward** — a game can reach 350 points through double OT, but nothing
symmetrically drags a total to 100. Consistent with the earlier measurement that
OT games carry sd(dev) 19.77 against 17.10 for regulation.

So the failure is not in the shot process (which is binomial, as measured) but
in the **possession count**, which the model treats as known.

## What this means

**The linemaker's assumption is wrong in a way that cannot be exploited on this
instrument.** Kalshi's ladder spans ~+-1.1 sigma; the normal's error lives beyond
2.5 sigma. The assumption is violated exactly where it is never priced.

If Kalshi ever quotes rungs beyond ~2 sigma, the normal would **systematically
underprice the over side** — at 2.5 sigma the true over-tail is 0.980% against a
Gaussian 0.621%, i.e. **58% too cheap**. Contracts that thin are also where the
`0.07*p*(1-p)` fee is smallest, so it is the one place the shape error could in
principle matter. **Those rungs do not currently exist**, which is why this is
recorded as structure and not as an opportunity.

Discreteness is a non-issue: the continuity correction is 0.5/18.07 = **0.028
sigma**, and totals take 140 distinct values over a 152-351 range.

---

# THE VARIANCE ASSUMPTION — and it matters far more than normality

Normality fails only beyond 2.5 sigma, where no rungs exist. **A sigma error is
different in kind, because of where it lands.**

## Why sigma bites where shape does not

The sensitivity of a binary to sigma is `dP/dsigma = phi(z)*z/sigma`:

| z | model P | dP per 1pt sigma | per 0.80pt (the unexplained sigma) |
|---|---|---|---|
| 0.00 | 0.5000 | 0.000c | 0.000c |
| 0.50 | 0.3085 | 0.978c | 0.782c |
| **1.00** | 0.1587 | **1.344c** | **1.075c** |
| 1.10 | 0.1357 | 1.331c | 1.065c |
| 2.00 | 0.0228 | 0.600c | 0.480c |

**Vega is zero at the money and PEAKS at |z| = 1 — precisely the edge of the
ladder's +-1.1 sigma span.** The shape error lives beyond 2.5 sigma where nothing
is quoted; the sigma error lives exactly on rungs that exist.

Stage C left **0.80 points of real, unexplained sigma**. At z = 1 that is
**1.075c**, against a Kalshi maker fee of `0.25*0.07*p*(1-p)` = **0.23c**.
**4.7x the fee.** That is the prize.

## What IS verified about sigma

**The level is right.**
```
mean implied sigma 18.074   realised sd(total - mu) 18.411   -> -1.83%
95% CI on realised [17.655, 19.167]   implied is INSIDE
```

**Rung-level absolute calibration is flat** (12,502 rungs, 1,139 games; NOT
rescaled to the ladder's own quantiles — that was the PIT-vacuity error):

```
model P bucket      n   predicted   actual   gap(pp)   se(pp)*
(0.15, 0.3]      2403      0.2355   0.2385     +0.29      2.87
(0.3, 0.45]      2737      0.3738   0.3697     -0.40      3.07
(0.45, 0.55]     1707      0.4997   0.4909     -0.88      4.01
(0.55, 0.7]      2744      0.6263   0.6246     -0.17      3.06
(0.7, 0.85]      2626      0.7676   0.7688     +0.12      2.73
*se inflated for within-game clustering (11 rungs/game)
```

Every populated bucket is inside one standard error. **On average, the ladder is
priced correctly.**

## What is NOT verified — the cross-section

```
quintile   ladder sigma   REALISED sd   +-noise
1               16.958         18.671     0.874
3               17.963         18.247     0.856
5               19.484         19.293     0.903

ladder CLAIMS a Q5-Q1 sigma gap of  +2.526 pts
reality DELIVERS                    +0.622 pts   se 1.257   t=+0.49
95% CI [-1.843, +3.086] -> contains BOTH zero AND the claimed 2.526

continuous  dev^2 ~ ladder sigma   +19.91 (t=+1.32)   CI [-9.7, +49.5]
  fully informative = 36.1;  pure noise = 0;  BOTH inside
```

**The point estimate delivers 25% of what the ladder claims, and the data cannot
distinguish "fully informative" from "pure noise".** MDE on the quintile gap is
2.394 points against a claimed 2.526 — we sit exactly at the edge of
detectability.

## The answer

**The normality assumption is violated and does not matter. The variance
assumption is unverified and matters a great deal.**

- shape error: real (skew +0.23, kurtosis +0.39, JB p<0.0001) but confined
  beyond 2.5 sigma, where Kalshi quotes nothing.
- sigma error: unknown in the cross-section, and it lands at |z| = 1 where vega
  peaks and where roughly a fifth of every ladder's rungs sit.

**This is now the single most valuable open question in the programme**, and it
is decidable: it needs games, not methods. At n = 1,139 the CI half-width is
2.46 points; **2026-27 roughly doubles the sample and takes it to ~1.7**, which
separates "the ladder's sigma is informative" from "the ladder's sigma is noise"
for the first time.

If it turns out to be noise, the 0.80 points of unexplained sigma is a
liquidity-provision opportunity at 4.7x the maker fee on the |z|~1 rungs. If it
is information, the ladder is doing something we cannot yet reproduce and the
correct response is to keep reverse-engineering. **Either answer is worth
having, and one more season buys it.**
