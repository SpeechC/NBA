# TOTALS MAD — CHANNEL DECOMPOSITION AND PCA (2026-09-13)

Question asked: dissect the NBA total MAD into systematic components, see how many
principal components describe it, and if PC1 is stable build a totals strategy on it.

**Answer: the MAD needs four components, not one; PC1 is not stable as a vector;
and the component that matters most for a strategy is the one PCA ranks sixth.**
That sixth component is real (t = +3.46 against the close, Bonferroni-clearing)
and still does not pay — its entire 95% CI sits below the vig bar.

Scripts: `s1_panel.py` … `s10_sigma.py` (scratchpad). Data
`dfMaster_OT_2017-2026.csv`, regular season, **n = 9,407, eight seasons**
(2017-18 … 2025-26; **2019-20 is absent from the file entirely**).

```
dev = actual total - closing total     mean +0.535   sd 18.060   MAD 14.286
BAR: to beat -110 a signal must shift E[total] by sd*Phi^-1(0.52381) = 1.079 pts
     (equivalently an OOS R2 on dev of 0.357%)
```

---

## 0. NEW DATA DEFECT — 3 games fail the box-score point identity

Extends `MARKET_COLUMN_AUDIT.md`. `PTS != 2*FG + 3P + FT` on:

| GAME-ID | date | teams | error |
|---|---|---|---|
| 22201146 | 2023-03-30 | MIL v BOS | 31 pts |
| 22201187 | 2023-04-04 | GSW v OKC | 12 pts |
| 22500029 | 2025-11-07 | WAS v CLE | 12 pts |

`TOTAL_PTS = PTS_H + PTS_R` still holds on all three, so the mirror check does not
catch them — same internally-consistent-corruption class as the six market cells.
**Any shot-level decomposition must gate on this identity.** Dropped throughout.

---

## 1. THE DECOMPOSITION IS EXACT, NOT A REGRESSION

```
TOTAL = P * (2*r2*p2 + 3*r3*p3 + rf*pf)      max abs error 8.5e-14 on 10,380 games
```
`P` total possessions, `r` per-possession attempt rates, `p` conversion rates.
Contributions are the **Shapley values** of the seven factors between a prior-only
forecast and the realised game, plus the model-market gap as an eighth channel:

```
dev = sum_k c_k          max |sum(c_k) - dev| = 1.0e-13
```

Shapley over 2^7 subsets — exact, symmetric, no ordering choice. The reference is a
prior-only two-way state engine (same gradient form as the frozen pace engine,
alphas frozen on 2017-18 + 2018-19 only). Its forecast is slightly worse than the
book (RMSE 18.67 vs 18.05), as expected.

**MAD attribution is then exact too**, since `MAD = E[sign(dev)*dev] = sum_k E[sign(dev)*c_k]`:

| channel | share of MAD | pts of MAD | sd(c_k) | share of Var(dev) |
|---|---|---|---|---|
| **3P%** | **38.7%** | 5.53 | 12.09 | 37.4% |
| **2P%** | **29.5%** | 4.22 | 10.70 | 27.5% |
| **possessions (pace)** | **21.7%** | 3.10 | 10.72 | 24.2% |
| FT attempt rate | 10.2% | 1.45 | 7.83 | 10.7% |
| FT% | 2.7% | 0.38 | 3.03 | 2.7% |
| model-market gap | **-0.1%** | -0.02 | 4.52 | -0.0% |
| 3P attempt rate | -0.2% | -0.03 | 8.61 | -0.1% |
| 2P attempt rate | -2.5% | -0.35 | 10.12 | -2.4% |

**Shooting accuracy is 70.9% of the MAD. Shot mix is zero** — a 2PA swapped for a
3PA is nearly point-neutral, and the two channels have corr -0.512, so they cancel.

**The model-market gap contributes -0.1% of the MAD.** Fifth independent restatement
of *CLV is earned and not converted*: our disagreement with the line is orthogonal to
the line's error, measured here as a share of the error itself rather than as a beta.

Stable across anchors and regimes (`s9`): vs the OPENER 37/29/22/11/3, in the
PLAYOFFS 41/30/18/10/4. Same under a first-order delta decomposition instead of
Shapley, and under two possession definitions.

---

## 2. THE BINOMIAL FLOOR — 79% of the variance is coin flips

Unbiased binomial variance component per game, in points:

| channel | attempts/game | rate | sd from sampling alone | sd observed | **irreducible** |
|---|---|---|---|---|---|
| 2P% | 108.2 | .536 | 10.37 pts | 10.70 pts | **93.9%** |
| 3P% | 68.7 | .360 | 11.94 pts | 12.09 pts | **97.5%** |
| FT% | 44.7 | .777 | 2.78 pts | 3.03 pts | **84.0%** |

```
irreducible shot-outcome variance   257.6 of 326.2 pts^2 = 79.0% of Var(dev)
MAD floor  sqrt(2/pi)*16.05         = 12.81 pts  vs an observed MAD of 14.29
=> the most any pre-game model can ever remove from the MAD is 1.48 pts (10%)
```

Confirms `MARGIN_ERROR_ANATOMY.md`'s "shooting is binomial by construction" on the
totals side, and quantifies it as a hard ceiling.

**But the floor does NOT foreclose a strategy, and it must not be quoted as if it
does.** The bar needs only 0.357% of R2; the floor leaves 21.0%, a ceiling of 8.28
pts of forecastable sd — 8x the bar. The obstacle is not the floor. It is that
almost none of the remaining 21% turns out to be forecastable.

---

## 3. PCA — the spectrum is flat, and the ranking is misleading

Covariance PCA on the seven point-scaled channel contributions. Because
`dev = 1'c`, the variance of dev decomposes exactly and orthogonally as
`Var(dev) = sum_k (1'v_k)^2 * lambda_k`:

| PC | eigenvalue | % var of channels | 1'v_k | **% of Var(dev)** | dominant loadings |
|---|---|---|---|---|---|
| PC1 | 160.7 | 25.8% | +0.73 | 24.6% | 3P% +.77, 2PA rate -.52 |
| PC2 | 136.6 | 21.9% | +0.36 | 5.0% | pace +.57, 2P% +.48, 2PA -.46 |
| PC3 | 119.2 | 19.2% | -0.84 | 24.0% | pace +.69, 3PA -.48, 3P% +.42 |
| PC4 | 107.3 | 17.2% | +0.67 | 13.9% | 2P% +.82, 3PA -.34 |
| PC5 | 65.0 | 10.4% | -0.08 | 0.1% | FTA rate +.88 |
| **PC6** | **24.6** | **3.9%** | **+2.05** | **29.8%** | **3PA +.68, 2PA +.55, FTA +.41 (all same sign)** |
| PC7 | 9.2 | 1.5% | +0.99 | 2.6% | FT% +1.00 |

**Three things follow.**

1. **There is no dominant factor.** 25.8 / 21.9 / 19.2 / 17.2 — four near-equal
   eigenvalues. Four PCs are needed for 92.3% of Var(dev). The channels are almost
   uncorrelated (largest |corr| is the mechanical 2PA-3PA -0.512), so there is no
   one-factor structure for PCA to find. Identical spectrum under a first-order
   decomposition, so this is a property of basketball, not of the attribution rule.

2. **PCA's ordering is by channel variance, not by contribution to the error, and
   here the two orderings are nearly reversed.** PC6 is 3.9% of the channel variance
   and **29.8% of Var(dev)** — the largest single share — because it is the one
   direction in which the attempt-rate channels do not cancel. PC5 is 10.4% of the
   channel variance and 0.1% of Var(dev). Ranking components by eigenvalue would have
   pointed at exactly the wrong ones.

3. **PC1 is not stable as a vector.** Bootstrap congruence with the pooled PC1 is
   high (0.989), but season-to-season it is not:

```
worst pairwise |phi| between season PC1s:  2018-19 vs 2023-24 = 0.643   median 0.908
eigenvalue gaps, pooled: 7.9, 6.6, 5.0 bootstrap sd -> separated at n=9,407
                         but at n~1,200 per season that is ~2-3 sd -> eigenvectors rotate
top-4 SUBSPACE, worst pairwise season-to-season: 0.9924   median 0.9972
```

The **subspace** is rock solid; the individual axes inside it are not identified
season by season. That is the correct reading when eigenvalues are this close, and it
means "is PC1 stable" is not a well-posed question here — the honest answer is that
the four-dimensional space is stable and the rotation within it is arbitrary.
Walk-forward, PC1's OOS share of Var(dev) drifts 35.8% -> 24.3% while PC3's climbs
3.2% -> 23.3%: the two are trading places inside a stable plane, not changing meaning.

---

## 4. FORECASTABILITY — the step that decides it

Loadings and regressions both fit on prior seasons only, ridge, 13 pre-game features
(engine states, close, gap, total move, B2B, days into season). n = 7,027 OOS.

| PC | OOS R2 of the score |
|---|---|
| PC1 | **-2.86%** |
| PC2 | +0.39% |
| PC3 | -0.37% |
| PC4 | -0.62% |
| PC5 | -0.79% |
| PC6 | -8.60% |
| PC7 | -0.55% |

Six of seven are negative — worse than predicting the mean. Direct ridge on dev:
**OOS R2 = 0.029%** against the 0.357% required.

**A trap worth recording.** The recombined PC prediction has sd 1.432 pts, which
*passes* the 1.079 bar — and loses at **49.55%, z = -4.72**. Prediction variance from
an overfit model is real variance that is uncorrelated with the outcome. **The
points-of-edge bar is only meaningful applied to an out-of-sample-validated
prediction.** Applied to a fitted one it inverts.

Nothing clears. Direct ridge peaks at 53.25% (n = 3,724, z = +1.06, n.s.) and the
threshold landscape is unstable in the way `nba-totals-reverse-engineering` records.

---

## 5. THE ONE LIVE FINDING — the shot-volume channel, and why it still fails

PC6 is not an abstraction. It is **shots produced per possession**:

```
corr(PC6 score, shots-per-possession surprise)  +0.824
corr(PC6 score, turnovers per possession)       -0.522
corr(PC6 score, OREB per possession)            +0.490
```

Turnovers and offensive rebounds — the two things that decide how many shots a
possession yields. It is the largest single contributor to the market's total error
(29.8% of Var(dev)) and PCA buried it at rank six.

A prior-only forecast of shots-per-possession tested against the **closing** line:

```
actual total ~ const + f_spp + close
  f_spp   beta +36.42   t +3.46   p 0.001        <- clears Bonferroni for 7 PCs (|t| > 2.69)
  close   beta +0.979   (t vs 1 = -1.09)         <- the line itself is unbiased
  corr(f_spp, close) = +0.287 -> genuinely not a proxy for the line
  edge at 1 sd = 0.673 pts       95% CI [0.292, 1.053]       BAR = 1.079
```

**The entire 95% confidence interval lies below the bar.** This is the mechanism
test from `nba-betting-systems-tested` applied to totals, and it gives the same
verdict in a much closer case: statistically real, economically insufficient. It is
the largest non-market factor this project has measured against a closing line —
62% of the way to break-even instead of the 23% the best spread factor reached.

Three further findings kill it as a trade:

**It decays and flips.** In-sample beta by season:
```
2017-18  +85.6 (t +2.33)   2021-22  +70.9 (t +2.44)
2018-19  +63.5 (t +2.09)   2022-23  +20.6 (t +0.66)
2020-21  +66.2 (t +2.08)   2023-24  +22.9 (t +0.81)
2021-22 ...                2024-25  +25.8 (t +0.83)
                           2025-26  -31.3 (t -1.07)
```

**It does not survive out of sample.** Beta fit on prior seasons, bet the sign:
```
thr 0.00  n=6,956  50.65%  z -2.89     thr 1.00  n=2,922  51.88%  z -0.54
thr 0.50  n=4,752  51.56%  z -1.14     thr 1.50  n=1,596  51.75%  z -0.50
thr 0.75  n=3,743  52.15%  z -0.28     thr 2.00  n=  813  52.28%  z -0.06
```
No season reaches 52.38% (49.42 … 51.90).

**The half that carries it is the half already closed.** Splitting the channel:
```
total ~ f_tovr + close   t -1.47   (sign BACKWARDS)
total ~ f_orbr + close   t +2.83   jointly t +3.07
```
The offensive-rebound half drives the result — and `CLOSING_OREB.md` already
established why it cannot pay: extensions are caused by misses, 68% of the gross
second-chance points are offset by weaker first-chance scoring, and the effect
reverses in the sealed holdout. My PCA rediscovered that channel from a pure error
decomposition and landed on the same structural wall.

Robust to the possession definition (vendor POSS t +3.14, formula t +3.29).

---

## 6. TWO OTHER SENSES OF "SYSTEMATIC", BOTH TESTED

**A common NIGHT factor — null, and underpowered.** One-way variance components over
1,252 nights: `F = 1.039, p = 0.180`; permutation on MSB `p = 0.190`. Between-night
component sd **1.30 pts, ICC 0.005**. Not predictable from #games, mean close, B2B
share or day-of-week (R2 0.011, F p = 0.146, max |t| 1.94), and lag-1 autocorrelation
of the night-mean error is +0.050 against a 2/sqrt(n) band of 0.057 — **the book does
not lag league scoring drift.** Note the point estimate (1.30 pts) is *above* the
1.079 bar, so this is a genuine underpower, not a refutation.

**Predictable variance heterogeneity — real but subsumed.** The decomposition yields
a pre-game predicted shot-outcome sd per game with no fitting at all:
`sqrt(4*A2*p2(1-p2) + 9*A3*p3(1-p3) + AF*pf(1-pf))`. It ranges 15.34 to 16.66 (p5-p95),
an 8.6% spread, and realised dispersion follows it monotonically (Q1 17.40 -> Q5 18.66,
`dev^2 ~ sig_hat` t = +1.88). But `corr(sig_hat, close) = +0.664`, and conditional on
the close **t collapses to +0.20**. The Kalshi ladder already scales sigma on mu
(slope +0.06061, t +14.09, `nba-market-efficiency-findings`) — that scaling *is* this
effect. Subsumed, not merely null.

---

## 7. VERDICT AND WHAT TO DO NEXT

**On the proposal as stated:** PCA does not support a totals strategy, and PC1 is the
worst possible candidate — it loads 0.77 on 3P%, which is 97.5% coin flips. Loading
stability and score forecastability are independent properties, and only the second
one pays. A perfectly stable loading vector on an unforecastable score is worth zero.

**What the exercise did buy**, and it is not nothing: an exact MAD accounting, a hard
10% ceiling on what any pre-game model can remove, and the identification of
shots-per-possession as the largest error channel — reached from an error
decomposition rather than a feature search, which is the provenance that made the
pace signal credible.

**Live angles, ranked.**

1. **Better instrument for the same channel (highest value).** The 0.673-pt edge comes
   from a forecast with R2 = 0.072 on shots-per-possession. Edge scales as sqrt(R2),
   so **reaching the 1.079 bar requires R2 ~ 18.5%** — a specific, falsifiable target.
   The instrument to try is the PBP store (`pbp_lineups_all.parquet`,
   `pbp_team_features.parquet`): possession-end typing (live-ball vs dead-ball
   turnovers, contested vs uncontested rebound chances) instead of a box-score rate.
   Same store as candidate **C1**, so one build serves both. The season decay is the
   reason to doubt it and the first thing such a build should test.
2. **The FT-rate channel is 10.2% of the MAD (1.45 pts) and has never been attacked
   directly.** It is a refereeing channel, crews are known pre-game, and the repo has
   `CLOSING_REFEREE.md` plus seven `PREREG_crew_*` files aimed at fouls but not at the
   totals FTA rate specifically. `CREW_H` covers 2017-2022 only.
3. **The night factor needs power, not another test.** ICC 0.005 with a 1.30-pt point
   estimate at 1,252 nights. It is the only route where a *conditional* effect could
   exceed the bar while the unconditional one is invisible; a decade more nights, or a
   conditioning variable that splits nights ex ante, would settle it.
4. **Test the decomposition against the Kalshi ladder rather than the book.** The
   ladder prices a whole distribution, so the channel-implied sd is directly
   comparable rung by rung rather than only through a hit rate. Section 6 shows the
   unconditional version is subsumed by mu-scaling; the untested version conditions on
   3PA rate at fixed mu, where the mechanical prediction is sharp.

**Do not re-run:** PC1 as a strategy input, aggregate |dev| classification
(`nba-market-efficiency-findings`, AUC 0.4998), the OREB level effect
(`CLOSING_OREB.md`), or the night factor as currently specified.

---

**FOLLOW-UP (2026-09-13):** §7.1's criterion is resolved in `SHOT_VOLUME_PBP.md`.
PBP possession-end typing lifts the shots-per-possession forecast OOS from R2 0.0605 to
0.0719, but the team-level information content of that quantity is only 5-9% of R2
against the 17.4% the criterion needs. The channel is capped near 0.7 pts of edge by an
information bound. §7.2 (the FTA/refereeing channel) is priced there too, at ~0.9 pts.
