# MONEYLINE — THE CONDITIONAL VARIANCE CHANNEL (2026-08-30)

A genuinely orthogonal hypothesis. Everything before this tested
`E[Margin - M_book | X]` — the LOCATION of the margin distribution. Moneylines are
also sensitive to its SCALE: at fixed `M > 0`, `dP(win)/dsigma < 0`, so two
6-point favourites with different matchup volatility deserve different moneylines.

The decomposition motivates it: 70.5% of margin-error variance is realization,
38.7% from 3P conversion and 29.3% from 2P. And 3P is close to exactly binomial
(phi 0.9883), so the generating mechanism is unusually well known.

**Gate A: can conditional margin variance be forecast at all? If not, stop.**

**Result: Gate A fails. Gate B was not run.**

## Construction — strictly prior-only, no outcomes

```
Var(3P pts) = 9 * [ E(n3)*p3*(1-p3) + Var(n3)*p3^2 ]
Var(2P pts) = 4 * [ E(n2)*p2*(1-p2) + Var(n2)*p2^2 ]
Var(FT pts) = 1 * [ E(nft)*pft*(1-pft) + Var(nft)*pft^2 ]
```
summed over both teams, with prior-only rolling (K=15) means and variances of
attempt counts and conversion rates. A second variant adds parameter-estimation
uncertainty around `p3_hat`/`p2_hat` (`p(1-p)/(K*n)`), the aleatoric-vs-estimation
split. n = 4,410 games.

| component | mean var | sd across games | implied sd | share |
|---|---|---|---|---|
| 3P | 232.1 | 32.54 | 15.23 | 44.5% |
| 2P | 224.9 | 37.54 | 15.00 | 43.2% |
| FT | 64.0 | 17.62 | 8.00 | 12.3% |
| total | 521.0 | 53.39 | 22.82 | — |

## Why the construction is misspecified in LEVEL — and it is instructive

```
predicted margin variance  521.0        realised  181.3
implied Cov(H pts, R pts) = 169.9   ->  corr ~ 0.65
```

**The margin is a DIFFERENCE.** Both teams share the game's pace and its state, so
their point totals are strongly positively correlated, and
`Var(H-R) = Var(H) + Var(R) - 2Cov`. Summing independent binomial variances
overstates margin variance by **2.9x**. The covariance term is larger than the
cross-sectional variation in the component variances (sd 53 on a mean of 521, ~10%),
so it dominates exactly the signal being looked for.

## GATE A — the test, and it fails

Actual sd of `(margin - closing spread)` by predicted-variance quintile:

| | Q1 | Q2 | Q3 | Q4 | Q5 |
|---|---|---|---|---|---|
| predicted sd | 21.27 | 22.13 | 22.72 | 23.37 | 24.51 |
| **ACTUAL sd** | **13.60** | **13.75** | **12.67** | **13.65** | **13.61** |
| \|e\|>20 | 0.132 | 0.145 | 0.109 | 0.135 | 0.137 |

Flat, with the minimum in the middle — the stated death case. Adding
parameter-estimation uncertainty changes nothing (13.61/13.73/12.72/13.64/13.57).

More sensitive than quintiles, all null:

```
e^2  ~ predicted variance      t -0.29
|e|  ~ predicted sd            t +0.17
log|e| ~ log predicted sd      t +0.54
```

## The component horse race — and what the two "significant" results mean

| specification | beta | t |
|---|---|---|
| 3P variance only | +0.30654 | **+2.36** |
| 2P variance only | −0.28931 | **−2.56** |
| 3P + 2P | −0.03318 | −0.39 |
| full shooting | −0.02266 | −0.29 |
| + parameter uncertainty | −0.01999 | −0.25 |

3P and 2P both clear |t| = 2 **with opposite signs, and cancel exactly when
combined.** A genuine variance effect would make both positive. Opposite-signed
components that annihilate are the signature of two correlated proxies for
something else — almost certainly shot mix — not of dispersion.

## Nothing else forecasts margin dispersion either

```
e^2 ~ forecast pace       t -0.35
e^2 ~ opening total       t +1.21
e^2 ~ |closing spread|    t -1.57
```

Consistent with the earlier measurement that realised sd(margin - spread) is flat
across spread buckets (12.89 / 13.16 / 12.71 / 13.58 / 12.71 / 13.30).

## The fairest possible version also fails

Rather than blame the binomial parameterisation, a regression was given 10
prior-only features (the three component variances, pace, total, both teams'
3PA means and variances, |spread|) and free rein to fit `log(e^2)`:

```
dev R2 (<=2023, n=2,096)      +0.00719
HELD-OUT R2 (2024-25, n=2,314) -0.00581     <-- worse than the mean
```

Held-out quintiles of that fitted forecast: 13.72 / 13.32 / 13.58 / 13.98 / 14.21.
A **+0.50 pt** spread from Q1 to Q5, against the ~4 pts that would constitute a
real signal.

## Verdict

**Conditional margin variance is not forecastable from prior-only shooting
mechanics, and the failure is not an artefact of the parameterisation** — a free
regression over the obvious drivers has negative held-out R^2.

Per the pre-stated gating, **Gate B was not run**: no outcome-versus-market test,
no `E_sigma`, no ROI. The hypothesis was sound and orthogonal to everything
previously tested; it fails at the first gate.

**Residual note.** The one thing this exercise did establish is structural: margin
dispersion is dominated by the covariance between the two teams' scoring (corr
~0.65 from shared pace and game state), not by either team's shooting variance.
Any future variance model would have to forecast that covariance, not the
components — and the flat realised dispersion across every conditioning variable
tried suggests there is little there to forecast.
