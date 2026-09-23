# FACTOR DECOMPOSITION OF THE SIGNED PRICING ERROR — ALL FOUR GATES (2026-09-13)

Runs the proposed programme: decompose `E = Actual - Close` into point-denominated
scoring shocks, PCA the shocks, extract **team factor exposures**, and gate them.

**Result: gates 1-3 pass, several of them emphatically, and gate 4 fails hard.**
A latent factor whose realised score is forecastable at **27.0% out-of-sample R2**
carries **-0.13%** about the signed closing residual and bets at **50.24%,
z = -3.63**. That is the sharpest market-efficiency result this project has produced
— not a weak signal that missed, but a strong, persistent, pregame-knowable state
that the closing line already contains in full.

The team-exposure formulation is a genuine improvement over the per-feature approach:
it lifts component forecastability from *six of seven PCs negative OOS* to
**PC1 27.0%, PC2 16.0%**. It improves the forecast and changes nothing economic.

---

## 0. TWO CORRECTIONS TO MY OWN FIRST PASS

**(a) The forward window was not forward.** I first measured persistence with
`s.shift(-1).rolling(20).mean()`, which is still a *trailing* window and overlaps the
prior-20 window on 18 of 20 games. It returned +0.90 for every PC — an overlap
artefact. The correct forward mean is `s.rolling(20).mean().shift(-20)`. All
persistence numbers below use the fixed version.

**(b) Shocks measured against an ADAPTIVE baseline cannot persist, by construction.**
`TOTALS_MAD_DECOMPOSITION.md` differenced against a prior-only two-way *team* engine.
That engine updates both teams' states on every error, so a team's own shock series is
mechanically stripped of its persistent component:

```
lag-1 autocorrelation of a team's own shock series, engine-relative:  PC1 +0.018  PC4 +0.015  PC6 +0.001
lag-1 autocorrelation of the RAW channel level (3PA rate/poss):                    +0.341
```

**The persistence lives in the level, and the engine had already extracted it.**
Testing team factor exposure on engine residuals is guaranteed to find nothing for a
mechanical reason. Everything below therefore differences against a **fixed
prior-only league season-to-date baseline**, which is what makes the exposure
hypothesis testable at all. This is the single most important methodological point in
the run.

---

## 1. THE ACTUAL EIGENVALUES — two decompositions, both exact

`T = P(2·r2·p2 + 3·r3·p3 + rf·pf)`, contributions are Shapley values over the seven
factors, summing to the error to **1e-13**. Loadings estimated on the discovery period
(2017-18, 2018-19) only, sign-aligned to the summing direction.

### (a) League-relative shocks — the version the exposure test needs (n = 9,247)

| PC | eigval | % var | Pace | 2PVol | 2PConv | 3PVol | 3PConv | FTVol | FTAcc | reading |
|---|---|---|---|---|---|---|---|---|---|---|
| PC1 | 213.2 | **29.7%** | +.13 | **−.75** | +.28 | **+.57** | +.13 | +.04 | .00 | **shot-mix (3P for 2P)** |
| PC2 | 153.9 | 21.4% | **+.90** | −.01 | +.19 | −.27 | −.20 | +.20 | −.01 | **pace** |
| PC3 | 121.9 | 17.0% | −.29 | +.11 | **+.87** | −.14 | −.34 | −.04 | +.01 | 2P conversion |
| PC4 | 119.0 | 16.6% | +.09 | +.13 | +.33 | −.21 | **+.90** | −.08 | +.01 | 3P conversion |
| PC5 | 74.0 | 10.3% | −.27 | −.24 | −.04 | −.32 | +.08 | **+.87** | +.01 | foul environment |
| PC6 | 25.9 | 3.6% | +.09 | +.59 | +.11 | +.66 | +.06 | +.43 | −.01 | **shot volume (all same sign)** |
| PC7 | 10.1 | 1.4% | +.02 | .00 | −.01 | +.01 | −.01 | .00 | **+1.00** | FT accuracy |

### (b) Engine-relative shocks, and the ranking trap

| PC | % var of shocks | **% of Var(signed E)** |
|---|---|---|
| PC1 | 25.2% | 37.7% |
| PC2 | 21.9% | 1.9% |
| PC3 | 19.3% | 2.8% |
| PC4 | 17.1% | 27.9% |
| PC5 | 10.8% | 0.4% |
| **PC6** | **4.0%** | **26.4%** |
| PC7 | 1.6% | 2.9% |

Because `E = 1'c`, the variance of the error decomposes exactly as
`Var(E) = Σ (1'v_k)² λ_k`. **The two orderings are nearly reversed.** PC6 is 4.0% of
shock variance and 26.4% of the pricing error; PC5 is 10.8% and 0.4%. **Ranking
components by eigenvalue points at the wrong ones** — the relevant statistic is the
projection onto the summing direction, not the eigenvalue.

The spectrum is flat either way (29.7 / 21.4 / 17.0 / 16.6), and identical under a
first-order linearisation, so it is a property of basketball rather than of the
attribution rule. There is no single dominant factor to find.

---

## 2. GATE 1 — STRUCTURAL STABILITY: pass, with a caveat

```
season PC1 congruence vs pooled   0.87 - 0.99      worst pairwise 2018-19 vs 2023-24  0.643
top-4 SUBSPACE, worst pairwise season-to-season   0.9924   median 0.9972
eigenvalue gaps pooled  7.9 / 6.6 / 5.0 bootstrap sd   ->  at n~1,200/season only 2-3 sd
```

**The subspace is stable; the individual axes inside it are not identified season by
season.** With λ1..λ4 this close, "is PC1 stable" is not well posed — the honest
answer is that a four-dimensional space is stable and the rotation within it is
arbitrary. Walk-forward, PC1's share of Var(E) drifts 35.8% → 24.3% while PC3's
climbs 3.2% → 23.3%: they trade places inside a stable plane.

---

## 3. GATE 2 — TEMPORAL PERSISTENCE: pass, decisively

Team exposure = prior-only rolling 20-game mean of the component score. Null obtained
by permuting scores within season.

| PC | peak channel | lag-1 ac | **split-half** | null split-half | **prior-20 → next-20** |
|---|---|---|---|---|---|
| **PC1** | shot-mix | +0.160 | **+0.886** | +0.020 | **+0.673** |
| **PC2** | pace | +0.136 | **+0.835** | +0.077 | **+0.561** |
| PC3 | 2P conversion | +0.026 | +0.540 | +0.017 | +0.333 |
| PC4 | 3P conversion | +0.021 | +0.486 | +0.040 | +0.316 |
| PC5 | foul env. | +0.076 | +0.786 | +0.285 | +0.551 |
| PC6 | shot volume | +0.073 | +0.712 | +0.084 | +0.469 |
| PC7 | FT accuracy | +0.036 | +0.586 | +0.020 | +0.309 |

Windows are strictly non-overlapping. **Teams do carry persistent, current-state
exposure to these factors** — the hypothesis is correct.

---

## 4. GATE 3 — PREGAME PREDICTABILITY: pass, and it beats the per-feature approach

Ridge on the two teams' 14 prior-only exposures, walk-forward, coefficients from prior
seasons only:

| PC | **OOS R2 of the realised component score** |
|---|---|
| **PC1** | **27.0%** |
| **PC2** | **16.0%** |
| PC5 | 9.6% |
| PC6 | 7.2% |
| PC4 | 3.4% |
| PC3 | 2.4% |
| PC7 | 1.8% |

For comparison, forecasting the same components from the engine's own rate features
gave **six of seven PCs negative OOS R2**. **The factor-exposure formulation is
materially better** — the proposal's central methodological claim is right.

---

## 5. GATE 4 — THE ECONOMIC GATE: fails, and hard

| model | OOS R2 on **signed** `Actual − Close` | sd(prediction) |
|---|---|---|
| close only | −0.015% | 0.078 pts |
| **exposures + close** | **−0.127%** | 0.742 pts |
| exposures only | −0.187% | 0.876 pts |

Walk-forward bet at the **actual per-game juice** (n = 6,763 priced):

| threshold | n | hit | break-even | ROI | z |
|---|---|---|---|---|---|
| 0.0 | 6,763 | 50.24% | 52.45% | **−4.21%** | **−3.63** |
| 0.5 | 3,797 | 50.59% | 52.46% | −3.56% | −2.30 |
| 1.0 | 1,608 | 48.32% | 52.48% | −7.92% | −3.34 |
| 1.5 | 555 | 49.01% | 52.53% | −6.69% | −1.66 |

Not flat — **significantly negative**. A 27%-forecastable factor is worth less than
nothing against the close. This is the cleanest statement of the result: **the market
prices the persistent team state exactly, and the residual is what is left over,
which is the part nobody can forecast.**

---

## 6. THE MAGNITUDE MODEL — also null

| model | OOS R2 on `|Actual − Close|` |
|---|---|
| close only | +0.018% |
| exposures + close | **+0.050%** |

| predicted-magnitude quintile | predicted | realised \|dev\| | sd(dev) |
|---|---|---|---|
| Q1 | 13.84 | 13.95 | 17.80 |
| Q2 | 14.14 | **13.52** | 17.04 |
| Q3 | 14.30 | **14.79** | 18.63 |
| Q4 | 14.46 | 14.37 | 18.01 |
| Q5 | 14.78 | 14.52 | 18.34 |

Non-monotone, spread of 1.3 points against a predicted spread of 0.94. Consistent with
`nba-market-efficiency-findings` (dispersion AUC 0.4998) and with the 79% binomial
floor. **Total-game uncertainty is not systematically predictable**, so the alternate-
totals / wide-tail application does not open either.

---

## 7. THE CONDITIONING TEST — one cell, and it does not survive

The pre-specified idea (does a directional signal work better where magnitude is
predictable?) produced a striking cell: in Q5, `f_spp` runs **t +3.13, edge 1.616 pts
= 144% of the 1.123 bar**. Four checks:

```
1. permutation, shuffled quintile labels, max |t| over 5 cells
      null mean 2.20, 95th 3.17, observed 3.13   ->   p = 0.058          FAIL
2. season stability of the Q5 effect
      t +1.76 / +0.77 / +2.56 / +0.54 / +0.22    ->   two seasons carry it   FAIL
3. is it just "high total"?  corr(predicted magnitude, close) = +0.222
      splitting on the close directly: t +1.00 / +1.41 / +0.37 / +2.18 / +0.03
      non-monotone, and the top close-quintile is the WEAKEST                FAIL
4. WALK-FORWARD, Q5 only, at the actual juice, n = 754
      bet-all 53.32% vs 52.37% break-even, ROI +1.80%, z = +0.52
      by season 52.71 / 51.18 / 59.02 / 47.46 — one season (n=183) carries it  FAIL
```

Positive at every threshold and significant at none. A lead, not a finding, and the
same shape as the n=49 spread cell in `PRICE_BAR_AUDIT.md`.

---

## 8. SCORECARD AND WHAT IT MEANS

| gate | verdict | number |
|---|---|---|
| PCA structure | flat, 4 factors | 29.7 / 21.4 / 17.0 / 16.6 |
| 1. loading stability | subspace yes, axes no | subspace 0.9924, PC1 pairwise low 0.643 |
| 2. factor persistence | **PASS** | PC1 split-half **0.886** vs null 0.020 |
| 3. pregame predictability | **PASS** | PC1 OOS R2 **27.0%** |
| 4. signed closing residual | **FAIL** | OOS R2 **−0.13%**, 50.24%, z −3.63 |
| magnitude model | FAIL | OOS R2 +0.05%, non-monotone |
| walk-forward ROI at actual juice | FAIL | −4.21% |

**What the run establishes.** The proposal's diagnosis was right — several weak
signals *are* manifestations of a small number of persistent latent states, factor
extraction *does* recover them, and it *does* improve forecastability by a large
margin (six negative R2s to 27%). The reason it does not pay is not signal-to-noise.
It is that **the persistent, extractable, forecastable part of team scoring behaviour
is precisely the part the closing line is built from.** Improving our estimate of a
state the market already knows moves our forecast and not the residual — the fifth
independent instance of *CLV is earned and not converted* in this project, and by far
the most direct: 27.0% versus −0.13% in the same regression on the same games.

**Where a factor approach could still bite**, none of which this run touches:

1. **Factor exposures for a state the market observes LATE, not one it observes
   well.** Persistence is the wrong property to hunt — the market prices persistent
   things best. The exploitable version is a factor that *changes* discontinuously and
   is observable to us before the line moves. Injury-driven exposure shifts are the
   candidate (`~/data/injury_reports`), and the test is exposure *change* around a
   roster event, not exposure level.
2. **Factor exposures against the OPENER rather than the close.** The three-way split
   in `SHOT_VOLUME_PBP.md` showed the market prices `f_spp` intraday at t +3.4 and
   pace at t +14.7. Running the same open/move/close split on PC1 exposure would
   measure *when* each factor gets priced, and would identify any factor the opener
   misses that the close catches — the only place a latency trade could live.
3. **Kalshi ladders rather than a single total.** A factor that predicts the *shape*
   of the distribution without predicting its mean is worthless for O/U and not
   worthless for a rung ladder. §6 says the magnitude model fails on this data, but it
   was tested against a scalar total; the ladder gives a per-rung target that the
   sportsbook line cannot provide.

**Do not re-run:** exposure persistence on engine-relative shocks (mechanically zero);
PC1 as a directional feature against the close; the magnitude model as specified.
