# Late-session findings not covered by the other documents

Everything here was established after the holdout result. Recorded so the repo,
not conversation memory, is the record.

---

## 1. Estimator choice: ridge beats everything (and it validated out of sample)

Nine model families on the totals-movement task:

| model | corr | CLV | beat close |
|---|---|---|---|
| **Ridge (linear)** | **0.294** | **0.746** | **55.4%** |
| RandomForest | 0.249 | 0.673 | — |
| CatBoost | 0.252 | 0.637 | — |
| XGB shallow/regularised | 0.247 | 0.625 | — |
| XGB fixed (used in all earlier work) | 0.236 | 0.605 | 53.3% |
| XGB deep/slow | 0.214 | 0.541 | — |
| LightGBM | 0.212 | 0.500 | — |
| MLP (2 hidden layers) | did not converge in 4.6h; ridge fits in 1.0s |

**The ordering is by regularisation strength, not flexibility.** Every step toward
more capacity made it worse. Re-running the comparison on games before 2023-04-10
only, ridge still wins in the same order — so the choice was not hindsight.

## 2. The CLV → win-rate conversion (the most useful constant in the project)

Measured across thresholds: **each +1.0 point of CLV buys +3.83pp of game win rate.**

| threshold | LINE direction % | mean \|move\| | CLV | GAME win % | ROI −110 | ROI −105 |
|---|---|---|---|---|---|---|
| all | 59.66 | 2.53 | 0.75 | 51.12 | −2.42 | −0.20 |
| 1.00 | 67.96 | 2.79 | 1.47 | 53.02 | +1.22 | +3.51 |
| 1.25 | 70.61 | 2.98 | 1.79 | 53.54 | +2.21 | +4.52 |
| 1.50 | 72.54 | 3.10 | 2.04 | 54.64 | +4.32 | +6.68 |
| 2.00 | 80.15 | 3.57 | 2.82 | 58.99 | +12.62 | +15.18 |

Break-even requires **CLV 1.30 at −110**, **0.99 at −105**, **0.81 on an exchange**.

⚠ **Calling line direction 60% of the time is worth a 51.1% win rate — a loss.**
Direction accuracy on the LINE is not the win rate on the GAME. Break-even needs
roughly **76% direction accuracy at −110**, ~70% at −105.

Selectivity works through two channels: it raises direction accuracy (59.7→70.6%)
AND the mean move on selected games (2.53→2.98).

## 3. Proportional staking — the one improvement that survived screening

Dev-only screen, identical spec-A predictions, only the money allocation changes:

| staking rule | units | ROI % | **season-ROI sd** | profit (u) |
|---|---|---|---|---|
| flat above 1.25 (frozen rule) | 820 | 2.21 | **42.4** | 18.1 |
| flat above 1.00 | 1,275 | 1.22 | 17.8 | 15.5 |
| **linear: max(\|pred\|−0.75, 0)** | 995 | **3.51** | **7.7** | 34.9 |
| linear capped at 2u | 990 | 3.23 | 7.3 | 32.0 |
| quadratic capped at 3u | 1,377 | 3.25 | 7.8 | 44.8 |

All three proportional variants land together (3.2–3.5%, sd ~7.5), which is what a
real effect looks like. The **stability gain matters more than the ROI**: season
swings fall ~80%, and it was season variance that made the flat rule untradeable.

**But it does not create an edge.** On the holdout the same rule gives −1.26%.

## 4. Dollar economics, $100 base bet, quadratic capped staking

| set | seasons | risked/season | profit @−110 | profit @−105 | ROI |
|---|---|---|---|---|---|
| dev (in-sample) | 5 | $27,547 | **+$896** | +$1,541 | +3.25% |
| **HOLDOUT (unseen)** | 2 | $37,348 | **−$471** | **+$366** | −1.26% |

Per-season holdout: 2024-25 **−$2,923**, 2025-26 **+$1,982**.
Mechanics: ~967 bets/season, median stake $17, mean $31, max $300.

**~$37k of risk cycled annually for a result between −$500 and +$900.**

## 5. What "one more feature" would have to deliver

| target | gap | CLV increase required |
|---|---|---|
| break-even at −110 | +0.80pp | **+12%** |
| a real business (3% ROI) | +2.37pp | **+36%** |
| break-even at −105 | −0.36pp | **already there** |

Best CLV gain from any of eighteen feature families: **+2.6%** (ensemble). The
next feature would need to be ~5x better than the best one found.

**The price lever (−110 → −105) is worth 1.16pp — larger than the entire 0.80pp
gap it needs to close.**

## 6. Unresolved: the conversion discrepancy

CLV of 1.740 implies an expected win rate of **56.7%**. The holdout delivered
**51.58%** — **2.1 standard errors below**. Two readings, not distinguishable on
442 bets:

1. the model is already well past break-even and the holdout drew badly (~1 in 25); or
2. the CLV→win conversion is weaker than the linear fit implies, perhaps because
   our CLV concentrates in games where the move overshoots.

This 5-point discrepancy is larger than anything a new feature would address, and
is the better research target.

## 7. Additional null results (families 15–18)

| tested | result |
|---|---|
| **Team identity** (60 dummies; proxy for embeddings) | corr 0.2946→0.2994, CLV **worse** (1.78→1.41). Team effects sd 0.082 vs pace coefficients ~0.74. Kills the embedding case. |
| **pbp possession context** (STARTTYPE, shot mix, 22 features) | corr 0.2946→0.2670 raw. PCA(5/10/20) recovers but never beats baseline, and declines monotonically with components — compression repairing harm, not extracting signal. Also costs 15% of sample. |
| **Season phase** (game number, phase×pace) | corr 0.2946→0.2931. Null. |
| **Move-class segmentation** | No class predicts move magnitude (max quintile spread 14% of mean). Two-stage magnitude×direction fails badly (CLV 0.68 vs 1.80). **Magnitude corr −0.036; direction accuracy 59.9%** — all signal is in the sign, none in the spread. |

## 8. Deep learning: not recommended

The ordering in §1 runs against flexibility; the MLP failed to converge; team
embeddings are ruled out by §7; n=7,335 with ~20 features and ~8% R² is the wrong
regime. The binding constraint is the information set, not the function class.

## 9. Betting-splits data — sources and the timing problem

BetLabs (built for historical splits backtesting), Action Network, VSiN
(DraftKings splits), Sports Insights. Verify before buying: whose book's flow,
bet% AND money%, timestamps, and a join key.

⚠ **The timing problem:** splits exist only after money arrives, and 83.8% of the
open-to-close move has happened by the first repricing. Splits therefore cannot
improve the bet-the-opener strategy much — they support a *different* strategy
(react to flow rather than anticipate it) with a later entry point.

**Cheaper substitute to price first: multi-book line divergence** (e.g. The Odds
API, multi-book snapshots from ~mid-2020). Available at the moment you would bet,
and directly measures where consensus is heading.

---

## 10. Spec re-check on the 2017-start panel — A and D survive

The panel changed materially (7,335 → 8,696 games) and `dis_open` became noisier
when its burn-in was cut, so the spec ranking was re-run rather than assumed.
**Development only** — choosing a spec is selection.

| spec | k | corr | bets | CLV | CLV lo | win% | ROI −110 |
|---|---|---|---|---|---|---|---|
| C (symmetric+pace, 41) | 41 | 0.2632 | 424 | **2.153** | 1.811 | 56.13 | +7.16 |
| **A (frozen, 21)** | 21 | 0.2635 | 453 | 2.000 | 1.676 | 55.41 | +5.78 |
| B (symmetric, 34) | 34 | 0.2610 | 501 | 1.987 | 1.673 | 55.09 | +5.17 |
| **D (frozen, 15)** | 15 | **0.2687** | 456 | 1.976 | 1.667 | 54.17 | +3.41 |
| D_nodis (14) | 14 | 0.2646 | 494 | 1.951 | 1.652 | 52.02 | −0.68 |
| A_nodis (20) | 20 | 0.2612 | 445 | 1.818 | 1.501 | 54.38 | +3.82 |
| market only (2) | 2 | 0.2121 | 35 | 3.757 | 2.257 | 57.14 | +9.09 |
| open_total only (1) | 1 | 0.0108 | 0 | — | — | — | — |

**The top six are statistically indistinguishable** — every CLV interval overlaps
every other. C leads on CLV point estimate, D on correlation, A sits between.
Switching to C on a 0.15 CLV gap with overlapping CIs would be exactly the
noise-chasing pre-registration exists to prevent. **A and D stand**, and they are
the specs with holdout results.

### `open_total` alone predicts nothing

Correlation **0.0108**, zero bets clearing the threshold. The line does not
predict its own movement; all signal comes from the team-form features. This is
a useful sanity check on where the edge originates.

### `dis_open` is nearly free to remove from D

| | CLV | corr | win% |
|---|---|---|---|
| D | 1.976 | 0.2687 | 54.17 |
| D without `dis_open` | 1.951 | 0.2646 | **52.02** |

CLV cost is 0.025 — noise. But `dis_open` is the **most expensive feature in the
pipeline**: it requires an XGBoost score model plus a calibration stage, and its
burn-in is the only reason the panel cannot start at the 2017-10-25 feature
floor. Removing it would delete the most fragile component and recover ~250 games.

⚠ It costs 2.1pp of realised win rate, which is the metric already failing (§6).
Worth investigating, not worth acting on yet — and any such change is a new spec
requiring its own pre-registration, not an edit to D.
