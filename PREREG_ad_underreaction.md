# Pre-registration: A/D market-underreaction residual

**Written before any outcome was examined.**

## The construction

Models A and D are frozen and unmodified. Their target is unchanged. This uses
their existing out-of-sample predictions without retargeting them.

```
dT      = close_total - open_total            the move the market actually made
pm_A    = model A's walk-forward prediction of dT   (frozen spec, frozen protocol)
pm_D    = model D's walk-forward prediction of dT

ADUnder = pm - dT
```

`ADUnder > 0` means that, on the historically observed market response to this
basketball state, the total would normally have moved farther up than it
actually did.

## Primary hypothesis

```
Residual = actual_total - close_total = a + bU * ADUnder + eps      bU > 0
```

A and D are tested **separately**. Neither is selected after the fact.

## The mechanical-confound decomposition, specified in advance

`ADUnder = pm - dT` and `Residual = actual - close` both contain `dT`. If the
closing line reverts at all — if a total that moved up tends to go under — then

```
Cov(Residual, ADUnder) = Cov(Residual, pm) - Cov(Residual, dT)
```

and the second term alone produces `bU > 0` with A and D contributing nothing.
Under an efficient close `Cov(Residual, dT) = 0` and the test is clean, but that
cannot be assumed. Three specifications are therefore run together and reported
together:

```
(a)  Residual ~ ADUnder                the pre-registered test
(b)  Residual ~ pm                     A/D information alone
(c)  Residual ~ pm + dT                the decomposition
```

**The claim is supported only if the `pm` coefficient in (c) is positive.** If
(a) is positive while `pm` in (c) is ~0 and `dT` carries it, the result is line
reversion, not A/D information, and the candidate fails.

## Additive test against the frozen referee signal

```
Residual = a + bR*CrewShock + bU*ADUnder + bL*LeagueFoulState + X'b + eps
```

`CrewShock`, `LeagueFoulState` and the +0.8682 threshold are loaded from
`ref_features.csv` and are not rebuilt, retuned or reinterpreted. X is the same
11 full-coverage team controls used in the final referee identification.

## Requirements

1. `|corr(ADUnder, CrewShock)|` preferably < 0.10
2. positive `pm` coefficient in decomposition (c) — the anti-confound gate
3. `c_true > c_market` for ADUnder
4. `bU > 0` after controlling for CrewShock
5. `bR` remains roughly intact
6. same coefficient sign in develop and holdout

No significant interaction is required or wanted. No threshold search: if an
economic test follows, it uses develop Q85 of the fitted additive score, matching
the selectivity of the frozen CrewShock strategy.

## Split

Develop through 2023-24; holdout 2024-25 and 2025-26. Economic weights are fitted
on development only and applied unchanged to holdout.
