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
