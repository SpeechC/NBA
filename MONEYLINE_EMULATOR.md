# MONEYLINE EMULATOR — the spread read through a smile (2026-08-30)

Same approach as the Kalshi ladder and the spread opener: model the market's own
number before asking whether it is beatable.

**Result: the moneyline carries no information the spread does not.** It is a
deterministic transform of the closing spread, reproducible to **1.42 cents held
out** — and the transform is *not* the single normal the ladder uses.

## Data

```
MONEYLINE_H / MONEYLINE_R   American odds, 100% coverage
CLOSING SPREAD_H            paired with it (corr 0.8419 vs 0.8111 for the opener,
                            so the moneyline is a CLOSING number)
n = 9,672 regular-season games, 2017-10-17 .. 2026-04-12
```

**Regular season only.** The naive pull gave n = 10,379; `GAME-ID` prefix shows
**707 of those are playoffs (4xxxxxxx) or play-in (5xxxxxxx)** — 6.8%
contamination, the same failure that manufactured the HH/LL variance result.
`DATASET_H` cannot be used as the filter: it is populated for only the first two
seasons.

`OPENING ODDS_H` / `CLOSING ODDS_H` are **not** moneylines — they hold spread
values at 17-22% coverage. Unusable.

## Formulation

```
p_home = Phi( a + M / sigma(|M|) )        M = -(CLOSING SPREAD_H)
```

Basketball has **no ties**, so `P(home wins) = P(margin > 0)` exactly — no push
term, unlike totals.

### De-vigging

Overround averages **1.0418 (vig 4.18%)**. Four standard methods, scored by how
cleanly they linearise the probit relation:

| de-vig | implied sigma | probit R^2 | MAE |
|---|---|---|---|
| **multiplicative** | **12.342** | **0.9883** | **0.0160** |
| additive | 11.648 | 0.9872 | 0.0175 |
| Shin | 11.648 | 0.9872 | 0.0175 |
| power | 11.239 | 0.9857 | 0.0189 |

**Multiplicative wins.** Used throughout.

## The single-sigma model, and where it fails

```
BOOK implied sigma (spread -> prob)      12.343
REALISED sd(margin - spread)             13.229
OUTCOME-CALIBRATED sigma (MLE on wins)   12.241
probit R^2 0.9886   MAE 1.60c
```

An intercept exists but is economically irrelevant: `a = +0.00308` (t = +4.71),
worth **0.12pp** of probability at a pick-em.

**One sigma is not enough.** Non-parametric implied sigma at each quoted spread —
no functional form imposed:

| \|spread\| | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 12 | 13 |
|---|---|---|---|---|---|---|---|---|---|---|
| implied sigma | 15.48 | 14.15 | 13.50 | 12.96 | 12.67 | 12.25 | 12.02 | 11.59 | 11.53 | 11.54 |

A monotone **1.35x decline**. Held out (fit 2017-2021, test 2022-2025):

| model | dev MAE | HELD-OUT MAE |
|---|---|---|
| one sigma | 1.80c | 2.01c |
| sigma varies with \|spread\| | 1.18c | 1.54c |
| **+ cubic** | **0.90c** | **1.42c** |

**Sigma is UNIDENTIFIED below ~2 points.** `Phi(M/sigma) ~ 0.5 + phi(0)M/sigma`,
so a narrow band near pick-em estimates a slope from almost no variation. At a
0.5-point spread the "favourite" prices at **0.4996** — below even money — and the
implied sigma returns −540. An earlier bucket estimate of 18.94 for `|spread| 0.5-3`
was dominated by these and is **withdrawn**; the curve above starts at 3 points.

## The smile is CORRECT

Direct calibration — implied versus realised outcomes on the same games:

| spread | n | market | realised | diff | z | one-sigma error |
|---|---|---|---|---|---|---|
| 3 | 2,093 | 0.5689 | 0.5662 | +0.0027 | −0.25 | **+0.0227** |
| 5 | 1,925 | 0.6355 | 0.6317 | +0.0038 | −0.34 | +0.0175 |
| 7 | 1,649 | 0.7007 | 0.7065 | −0.0058 | +0.51 | +0.0006 |
| 9 | 1,229 | 0.7636 | 0.7632 | +0.0004 | −0.03 | −0.0035 |
| 11 | 850 | 0.8194 | 0.8129 | +0.0065 | −0.48 | −0.0058 |
| 14 | 398 | 0.8748 | 0.8894 | −0.0146 | +0.93 | −0.0239 |

```
weighted MAE vs realised outcomes:   market 0.0042   one-sigma 0.0124
overall (n=9,672):  implied 67.84%   realised 68.03%   diff +0.20pp   z +0.41
```

**The market's smile is 3x more accurate than a constant sigma**, and every
bucket sits within |z| < 1. A single sigma would overprice short favourites by
~2.2pp and underprice big favourites by ~2.4pp.

**No favourite-longshot bias.** All eight implied-probability deciles fall within
|z| < 1.3 with no monotone drift — the classic bias in racing and most sports
markets is absent here.

## Why the smile exists — leptokurtosis, NOT heteroskedasticity

The obvious explanation fails. Realised margin dispersion is **flat** across
spreads:

| \|spread\| | 3-5 | 5-7 | 7-9 | 9-11 | 11-14 | 14+ |
|---|---|---|---|---|---|---|
| implied sigma | 14.42 | 13.15 | 12.41 | 11.90 | 11.69 | 12.33 |
| **realised sd** | 12.89 | 13.16 | 12.71 | 13.58 | 12.71 | 13.30 |

Implied falls 14%; realised moves +3%. `corr(implied, realised) = −0.168`. **The
smile does not track real heteroskedasticity.**

The actual mechanism is the shape of the margin distribution:

```
margin - spread,  n=9,672
  sd 13.228   skew +0.0023 (t +0.09)   EXCESS KURTOSIS +0.4904 (t +9.84)   JB p 9e-22

  |z|>1.0   normal 31.731%   actual 30.159%   ratio 0.950
  |z|>2.0   normal  4.550%   actual  4.994%   ratio 1.098
  |z|>3.0   normal  0.270%   actual  0.527%   ratio 1.953
```

Symmetric, but sharply **leptokurtic** — a peaked centre with fat tails. A single
normal CDF cannot price a leptokurtic variable across a wide range of effective
strikes. The smile is the market's empirical correction, and it is well made.

## The unifying result across both markets

This closes a question the ladder work left open.

**Kalshi's totals ladder uses ONE sigma and needs no smile** — it quotes only
within ±1.1 sigma, and inside that span the normal is accurate to a ratio of
0.996. Its normality violation lives beyond 2.5 sigma, where nothing is priced.

**The moneyline has a single strike (margin = 0) but the spread sweeps the whole
distribution**, so the book is effectively pricing deep into the tails on every
big favourite — exactly where normality fails. A smile is therefore *required*,
and the book has one.

**Same distribution, same violation, opposite conclusions — because the two
markets quote different regions of it.**

## WHICH SPREAD ANCHORS IT — and why the close, against the programme's habit

Everything else in this programme is anchored on the **opener**: the totals
emulator predicts the opening total, the spread emulator predicts the opening
spread, and Amendment 6 settles wagers against `open_total`. The moneyline is the
exception, and not by choice.

**There is no opening moneyline in the data.** `MONEYLINE_H/R` is a single column
and it is a CLOSING number:

```
z ~ opening spread    R2 0.9180   sigma 12.229
z ~ closing spread    R2 0.9887   sigma 12.361
HORSE RACE  z ~ open + close:  open t +14.4   close t +248.6
```

So the transform is estimated on the timestamp-consistent pair (closing spread ->
closing moneyline), which isolates **pricing structure**. It is then applied to an
opening-spread forecast. That composition is defensible because the mapping is
timestamp-stable — fitted sigma at a 6-point spread is 12.47 anchored on the
opener versus 12.85 on the close.

Anchoring the fit on the opener instead costs accuracy that is **line movement,
not structure**:

| anchor / spec | R^2 on p, OOS | OOS MAE | sigma @ 6 |
|---|---|---|---|
| opening spread / one sigma | 0.9181 | 4.22c | 11.82 |
| opening spread / smile | 0.9204 | 4.19c | 12.38 |
| opening spread / cubic | 0.9220 | 4.11c | 12.47 |
| closing spread / one sigma | 0.9876 | 2.01c | 11.81 |
| closing spread / smile | 0.9911 | 1.54c | 12.70 |
| **closing spread / cubic** | **0.9922** | **1.42c** | 12.85 |

## SPECIFICATION AND FIT

```
M      = -(SPREAD)                       implied home margin
p_home = Phi(z)                          de-vigged multiplicatively
z      = a + b*M + c*M|M| + d*M|M|^2
```

Fitted on 2017-2021, applied unchanged to 2022-2025:

| spec | a | b | c | d | R^2 z dev | R^2 z OOS | R^2 p dev | **R^2 p OOS** | OOS MAE |
|---|---|---|---|---|---|---|---|---|---|
| S1 one sigma | +0.00399581 | +0.08464988 | — | — | 0.9875 | 0.9852 | 0.9889 | 0.9876 | 2.01c |
| S2 smile | +0.00237542 | +0.06932297 | +0.00157288 | — | 0.9923 | 0.9746 | 0.9946 | 0.9911 | 1.54c |
| **S3 cubic** | +0.00201020 | +0.04377192 | +0.00743204 | −0.00029310 | 0.9955 | 0.9856 | 0.9967 | **0.9922** | **1.42c** |

**S2's held-out R^2 on the probit scale (0.9746) falls BELOW S1's** while its R^2
on probability rises. The quadratic overshoots on a handful of extreme-spread
games where |z| is large; that punishes the z-scale metric and barely moves the
traded price. S3 fixes both.

### R^2 near 0.99 does almost no work here — the ladder trap again

```
naive LINEAR    p = a + b*M      R2 0.9886   MAE 1.53c
naive QUADRATIC in M             R2 0.9910   MAE 1.53c
probit ONE sigma                 R2 0.9910   MAE 1.60c
probit SMILE                     R2 0.9929   MAE 1.37c
```

R^2 spans **0.9886 -> 0.9929** across everything from a straight line to the full
smile, and a straight line in M beats the probit one-sigma model on MAE. The
moneyline is a monotone function of the spread, so any sensible monotone curve
scores in the high nineties — exactly as any downward curve scored 98.82% on the
ladder before sigma was involved. **MAE in cents and calibration against outcomes
are the metrics that discriminate.**

## ERROR BUDGET — the transform is not the bottleneck

Held out, MAE against the market's de-vigged probability:

| driven by | MAE | increment |
|---|---|---|
| the book's CLOSING spread | 1.42c | pricing structure alone |
| the book's OPENING spread | 4.12c | +2.70c line movement |
| **our opening-spread model** | **6.18c** | +2.06c our spread error |

Our spread emulator sits at RMSE 2.596 points against the book's opener; with
`dp/dM = phi(0)/sigma = 0.0322` per point at the centre, that is the dominant
term. **The transform contributes 1.42c of a 6.18c total.** Improving the
spread -> probability mapping cannot help; the expected margin is the constraint —
the same conclusion `MARGIN_ERROR_ANATOMY.md` reaches from the other direction.

## Frozen emulator

```
fitted on 2017-2021 ONLY, applied unchanged to 2022-2025
z      = +0.002375 +0.069323*M +0.00157288*M*|M|   [+ cubic term for best fit]
p_home = Phi(z)                                     M = -(CLOSING SPREAD_H)
```

Held-out MAE 1.42c. Held-out outcome calibration drifts to −1.04pp (the emulator
slightly overstates favourites out of sample, where the market's own price does
not) — the polynomial extrapolates imperfectly at extreme spreads.

## What this means for a signal

**Nothing new is available here.** The moneyline is the closing spread plus a
fixed, correct transform. Any moneyline model is the spread model
(`MARKET_MODEL_SPEC.md` §3.4, held-out R^2 0.8689) composed with this curve, and
any moneyline edge must come from the spread — which §4.4 of that document
records as closed on both channels.

The residual after the transform is ~1.4 cents, against American-odds quote
granularity of roughly 0.3-0.6 cents. Whether that ~1pp residual carries
information beyond the spread is a separate, untested question. **It has not been
tested, and no claim is made about it.**
