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

---

# GATE A1 — THE MATCHUP-SPECIFIC COVARIANCE MODEL (2026-08-30)

The Gate A0 conclusion — "dispersion lives in the covariance, therefore the
channel fails" — was **premature**. That the covariance dominates is an argument
for modelling it as a property of the specific matchup, not for abandoning the
question. This runs that test.

## Exact decomposition, against the BOOK's own implied points

```
impH = (close_total + M)/2      eH = PTS_H - impH
impR = (close_total - M)/2      eR = PTS_R - impR
eH - eR == margin - M           MAE 0.000000   (exact)

Var(eH) 127.0   Var(eR) 124.3   Cov 35.6   corr 0.283
Var(eM) = 127.0 + 124.3 - 2(35.6) = 180.0   realised 180.0
the covariance removes 28% of the summed team variance
```

## Construction

33 strictly prior-only features: both teams' 20-game scoring-error volatility
(own, allowed, pace), own scoring/allowed covariance state, efficiency and pace
states, transition / 3PA / OREB / TOV / FTr profiles both directions, rest, and the
relational interactions (`trans_H x trans_allowed_R`, `3PAR_H x 3PA_allowed_R`,
`OREB_H x DREB_R`, `TOV_H x forcedTOV_R`, and reverses). K = 200 nearest prior
matchups, franchise identity excluded, EB-shrunk toward league baselines.

**The model produces genuinely differentiated predictions**: predicted margin sd
ranges **10.98 to 15.90**, mean 13.27, sd 0.696. This is not a degenerate forecast.

## GATE A1a — does predicted covariance rank `eH*eR`?

| Q | n | pred cov | ACTUAL eH*eR | se |
|---|---|---|---|---|
| Q1 | 640 | 24.3 | 34.7 | 5.5 |
| Q2 | 640 | 32.2 | 28.1 | 5.0 |
| Q3 | 639 | 37.6 | 30.8 | 4.9 |
| Q4 | 640 | 43.0 | 29.4 | 6.0 |
| Q5 | 640 | 52.8 | 38.4 | 5.6 |

Predicted covariance more than doubles across quintiles; actual is flat and
non-monotone. `eH*eR ~ predicted cov`: **t = +0.67**.

## GATE A1b — does predicted margin sd rank realised dispersion?

| Q | n | pred sd | ACTUAL sd | \|e\|>20 |
|---|---|---|---|---|
| Q1 | 640 | 12.30 | **13.81** | 0.139 |
| Q2 | 640 | 12.90 | 14.27 | 0.141 |
| Q3 | 639 | 13.27 | 13.74 | 0.142 |
| Q4 | 640 | 13.64 | 13.65 | 0.144 |
| Q5 | 640 | 14.25 | **13.50** | 0.136 |

**Predicted spread +1.95 pts; actual spread −0.31 pts — slightly INVERTED.**
`eM^2 ~ predicted variance` t = −0.75; `|eM| ~ predicted sd` t = −1.13.

## The 2-D diagnostic is inverted in the theory's own key corner

| team volatility | predicted rho | n | pred sd | ACTUAL sd |
|---|---|---|---|---|
| HIGH | LOW | 542 | 13.88 | 13.38 |
| HIGH | MID | 516 | 13.45 | 14.07 |
| HIGH | HIGH | 541 | 12.93 | 13.72 |
| LOW | LOW | 525 | 13.56 | 13.13 |
| LOW | MID | 550 | 13.11 | 13.84 |
| **LOW** | **HIGH** | 525 | **12.71** (tightest predicted) | **14.62** (widest actual) |

The configuration the mechanism predicts should be tightest — low individual
volatility, high scoring correlation — is empirically the **widest**.

## Root cause: there is no stable team dispersion property to find

```
|e_next| ~ prior 20-game own-scoring volatility:   beta +0.0684  t +1.47
prior-vol quintile -> next-game scoring-error sd:
   Q1 11.11   Q2 11.39   Q3 11.07   Q4 11.23   Q5 11.65      (0.54 pt spread)

team-season margin dispersion, first half -> second half:   corr +0.0399
```

**Team scoring volatility barely persists game to game, and team-season margin
dispersion barely persists half to half.** No conditional model can forecast a
property that is not there.

### The one number that looked encouraging, checked

`corr(predicted sd, actual sd)` across 90 team-seasons is **+0.3999** — but that is
aggregation over overlapping games, not skill:

```
same-half   corr(pred_h1, act_h1)  +0.1927      overlapping games
same-half   corr(pred_h2, act_h2)  +0.3801
DISJOINT    corr(pred_h1, act_h2)  +0.1668      the honest test (t ~ 1.6 on n=90)
persistence corr(act_h1,  act_h2)  +0.0399      the target itself
```

## Verdict

**Gate A1 fails. Gate B was not run** — no outcome-versus-market test, no
`E_sigma`, no ROI, per the pre-stated gating.

The corrected conclusion is not "dispersion lives in the covariance, therefore the
channel fails." It is:

> **NBA margin dispersion has no stable team- or matchup-level component to
> forecast.** Team scoring volatility persists at t = +1.47 with a 0.54-point
> quintile spread; team-season dispersion persists at corr +0.04. A matchup model
> given 33 prior-only features and local analogs produces confidently
> differentiated predictions (10.98 to 15.90) that rank realised dispersion
> **inversely**, and is inverted precisely in the corner where the covariance
> mechanism makes its sharpest prediction.

This is the variance analogue of the mean-channel result, established at the same
level of specificity: with named teams, matchup interactions, local analogs and
current-state profiles rather than league averages.
