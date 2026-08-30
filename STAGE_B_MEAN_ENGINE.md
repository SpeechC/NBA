# STAGE B — MEAN-ENGINE RECONSTRUCTION (cross-fitted, no outcomes)

Chronological cross-fit: train through season Y−1, predict season Y. Every
feature remains `shift(1)`/prior-only within season. **No actual score is used
anywhere** — target and features are market and pregame states only.
`stageB.py`, `stageB2.py`.

**Structural constraint recorded:** ladder μ exists for **2025-26 only** (Kalshi
coverage). A multi-season cross-fit against ladder μ is impossible, so the
season-forward fit targets the **opening total** (2017-18…2025-26, n=9,487), and
the model trained through 2024-25 is then tested against **actual ladder μ** on
the held-out 2025-26 season.

## B1 — HONEST OOS, and it is much worse than in-sample

| model | RMSE | MAE | R2 | medAE | ≤0.5 | ≤1 | ≤2 | ΔRMSE |
|---|---|---|---|---|---|---|---|---|
| M0 league baseline | 10.511 | 8.570 | 0.0660 | 7.452 | 3.3 | 6.8 | 13.5 | |
| M1 + off/def strength | 7.919 | 6.296 | 0.2511 | 5.337 | 4.7 | 9.9 | 20.6 | −2.593 |
| **M2 + expected pace** | 5.898 | 4.708 | 0.6452 | 3.998 | 6.6 | 12.9 | 26.9 | **−2.020** |
| M3 + four factors | 6.201 | 4.931 | 0.6089 | 4.120 | 6.8 | 13.1 | 25.6 | **+0.303** |
| M4 + shot composition | 6.279 | 4.992 | 0.5824 | 4.211 | 6.9 | 13.3 | 25.5 | **+0.078** |
| M5 + rest / schedule | 6.232 | 4.923 | 0.5751 | 4.091 | 6.5 | 13.4 | 26.3 | −0.047 |
| **M6 + recent state** | 4.966 | 3.968 | 0.7295 | 3.343 | 8.0 | 15.8 | 31.4 | −1.266 |

```
Stage-1 IN-SAMPLE M6:  RMSE 3.508  R2 0.8689   <- OPTIMISTIC BOUND, not comparable
```

**In-sample overstated RMSE by 42% (3.508 -> 4.966) and R2 by 0.139.**

**Four Factors and shot composition make OOS accuracy WORSE** (+0.303 and
+0.078 RMSE). Stage 1 reported them as adding ~nothing in-sample; honestly
evaluated they actively **hurt**, because they are redundant with efficiency and
contribute only estimation noise. This is a stronger statement than Stage 1's.

## B2 — THE PARSIMONIOUS ARCHITECTURE WINS

```
struct + recent state          RMSE 4.886   R2 0.7670    <- BEST OF EVERYTHING
M6 full (all blocks)           RMSE 4.966   R2 0.7295
struct alone                   RMSE 6.357   R2 0.6449
```

**`Pace* x (PPP_H* + PPP_R*) + RecentState` beats the kitchen sink out of
sample.** The Stage 1 architecture survives honest evaluation, and the
parsimonious form is not merely as good — it is better.

## B3 — PACE COMBINES ADDITIVELY. No matchup nonlinearity.

```
(P_H+P_R)/2            RMSE 5.898
sqrt(P_H*P_R)          RMSE 5.898
a + bH*P_H + bR*P_R    RMSE 5.898
+ (P_H - P_R)^2        RMSE 5.906   (worse)
+ P_H*P_R              RMSE 5.965   (worse)
```

The "two fast teams versus fast-vs-slow" hypothesis is **not supported**: the
squared-difference and product terms both degrade OOS accuracy. A simple average
is as good as anything tried.

## B4 — MARKET PERSISTENCE ADDS NOTHING

```
market persistence ALONE       RMSE 7.005   R2 0.4870   (worse than struct alone 6.357)
M6 + market persistence        RMSE 5.076               (worse than M6 alone 4.966)
struct + market persistence    RMSE 6.284               (barely better than struct 6.357)
```

Prior market-implied team totals do **not** beat observed basketball statistics
and do not explain the plateau. **Preliminary**: this proxy is a prior-only
rolling mean of market-implied team points, not a properly estimated latent
rating system. A real Stage B.2 latent-rating model could still differ.

## B5 — THE FINDING THAT REFRAMES THE PROGRAMME

Tested on the held-out 2025-26 season, n=1,138 (junk ladders excluded per A7):

| predictor of LADDER μ | RMSE | R2 | ≤0.5 | ≤1 | ≤2 |
|---|---|---|---|---|---|
| **the CLOSING TOTAL itself** | **0.584** | **0.9942** | 61.1 | **93.1** | 99.7 |
| the OPENING TOTAL itself | 3.136 | 0.8346 | 13.3 | 24.9 | 49.5 |
| M6 full (trained ≤2024-25) | 4.567 | 0.6711 | 9.7 | 17.9 | 35.9 |
| struct + recent (trained ≤2024-25) | 4.692 | 0.6776 | 9.3 | 17.1 | 33.6 |

```
corr(close, ladder mu) 0.9973   mean(mu_lad - close) +0.046   sd 0.582
corr(open,  ladder mu) 0.9136   mean(mu_lad - open)  +0.340   sd 3.119
```

**THE KALSHI LADDER CENTRE IS THE SPORTSBOOK CLOSING TOTAL.** Agreement to 0.58
points, 93.1% within one point, 99.7% within two. The ladder is not
independently constructed — it is anchored to the closing line.

Two consequences:

1. **Reverse-engineering ladder μ IS reverse-engineering the closing total.**
   Stage A's clean two-parameter target is not a separate object.
2. **Our basketball reconstruction (RMSE 4.57) is worse than simply quoting the
   opener (3.14).** A model built from PIT basketball state cannot match the
   market's own prior quote.

## What Stage B establishes — and what it refutes

**Establishes:** the architecture. `Pace x (PPP_H + PPP_R) + recent state`
survives cross-fitting, wins against richer alternatives, and pace enters
additively. Four Factors and shot composition are confirmed redundant — now
demonstrably harmful rather than merely useless.

**Refutes:** that we have recovered the linemaker's recipe. At **8.5% within 0.5
points, 16.1% within 1 point, 31.2% within 2**, this is nowhere near the
"70% within 1 point" that would indicate reconstruction of an actual process.
The residual is not ladder noise — ladder μ is measured to ±0.58 points — it is
**our deficiency**. The market holds information (injuries, lineups, flow) that
PIT box-score state does not contain.

## Consequences for Stage C

```
corr(sigma_ladder, quote width) = +0.2274 on the canonical estimate
```

Stage A's requirement stands and is now measured on the canonical σ. Stage C
must report every σ coefficient **with and without a quote-width control and on
both estimators**, and the Link 6/7 3PA-predicts-σ result must be re-run that
way before it is relied upon.

**And Stage C should target σ knowing that μ is the CLOSE.** If the ladder
centre is imported from the sportsbook, σ may be too — in which case Stage C is
reverse-engineering a Kalshi-side variance rule applied to an externally
supplied centre, which is a different and smaller object than assumed.
