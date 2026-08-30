# TEAM x VENUE PACE UNCERTAINTY — the 60-state model

Two-way hierarchical variance model, exactly as specified:

```
u_g = PaceActual - PaceForecast - PaceDrift_hat
log sigma_g^2 = alpha + H[home team] + R[road team]
Gamma GLM with log link (correct for u^2), RIDGE penalty = hierarchical shrinkage
ridge lambda selected ONCE on the first split by held-out likelihood, then frozen
```

`twoway_pace_variance.py`. n = 3,109; 60 team-venue states.

## M2 DOES NOT BEAT M1 — the venue split is not supported

Held-out Gaussian log-likelihood, chronological:

| season | n | M0 const | M1 pooled team | M2 home/road | M2−M1 |
|---|---|---|---|---|---|
| 2024 | 1,039 | −2934.9 | −2934.7 | −2935.0 | −0.29 |
| 2025 | 1,034 | −2936.1 | −2935.4 | −2935.5 | −0.20 |
| **TOTAL** | 2,073 | −5871.0 | −5870.0 | −5870.5 | **−0.48** |

```
M1 - M0 = +1.00     M2 - M1 = -0.48
```

**Separating home and road roles COSTS held-out likelihood.** The pre-registered
criterion — "if M2 wins OOS we have demonstrated venue-conditioned team pace
uncertainty is real" — is **not met**.

**And note how small M1's own gain is: +1.00 nats across 2,073 games.** Even the
pooled team effect is worth almost nothing in likelihood terms.

## The home−road differences are two orders of magnitude smaller than hypothesised

```
home sd range   3.934 - 4.064     road sd range   3.924 - 4.058
sd of (home - road) across teams  =  0.0340 possessions
largest |H - R|: New Orleans +0.064,  Utah -0.057
corr(home_sd, road_sd) across teams = +0.4160
```

| team | home sd | road sd | H−R |
|---|---|---|---|
| Milwaukee | 3.934 | 3.932 | +0.002 |
| Cleveland | 3.938 | 3.937 | +0.001 |
| Oklahoma City | 3.969 | 3.924 | +0.045 |
| Boston | 4.032 | 3.970 | +0.062 |
| Utah | 4.002 | 4.058 | −0.057 |
| New Orleans | 4.064 | 4.000 | +0.064 |

**The hypothetical was Boston 3.5 home / 4.6 road — a gap of 1.1. The largest
observed gap in the league is 0.064.** Boston is in fact 4.032 / 3.970, a
difference of 0.06 possessions ~ 0.14 points of total.

**`corr(home_sd, road_sd) = +0.42`** says teams that are pace-uncertain at home
are also pace-uncertain away. **It is a single team-level trait, not a
venue-conditioned one.**

## A REVISION to the previous message

The likelihood-selected ridge chose **lambda = 1000, the top of the grid** — the
data wants near-maximal shrinkage. Under it, team sd spans **3.93-4.06 (spread
0.13)**, not the **3.72-4.19 (spread 0.48)** the empirical-Bayes parameterisation
gave.

**Both cannot be right, and the likelihood-selected one is the defensible
choice** for a predictive quantity. **So the team-level heterogeneity I reported
last message was overstated by roughly 4x.**

What survives: quintiles of the M2 prediction still separate — Q1 3.980 -> Q5
4.484, ratio 1.1266, F p = 0.0155 — but non-monotonically (3.980, 4.078, 4.007,
3.917, 4.484), with only Q5 standing apart.

## The measurement-error argument does not rescue the betting question

The reasoning was: if pooled Boston = 4.12 really decomposes into 3.5 home /
4.6 road, then assigning 4.12 to every Boston game injects measurement error that
attenuates the `PaceGap x sigma` interaction toward zero.

**That decomposition does not exist.** Boston is 4.032 / 3.970. There is no
hidden venue structure for a better `sigma` to recover, so the earlier interaction
results (t = −0.47 with volx, t = +1.52 with the EB sigma) are not attenuated by
this particular omission.

## Settled

| claim | verdict |
|---|---|
| Teams differ in pace uncertainty | **YES, but small** — 3.93-4.06 under likelihood-selected shrinkage |
| Home and road differ within a team | **NO** — M2 loses to M1 by 0.48 nats; sd(H−R) = 0.034 |
| It is a venue-conditioned trait | **NO** — corr(home, road) = +0.42, one trait |
| A better sigma would rescue the betting interaction | **NO** — the structure it would exploit is absent |

The prereg amendment stands unchanged: uncertainty constructs remain diagnostics,
not decision variables.
