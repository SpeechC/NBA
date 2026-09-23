# ERROR LOCALIZATION — TRADE P&L (2026-09-13)

Ten model families, one frozen walk-forward harness, economics at the **actual per-game
juice**. Benchmark is P&L, not R2.

```
8,938 games | 6 walk-forward test seasons (2020-21 .. 2025-26) | 6,761 priced OOS bets
$100 flat per bet -> $676,100 staked | mean price -110.4 | mean hurdle 1.13 pts

BENCHMARK 1   do not bet ....................................  $0
BENCHMARK 2   bet at random, pay the vig ....................  -$31,689   (-4.69%)
```

## The scorecard

| model | bets | **P&L** | ROI | hit% | best subset found |
|---|---|---|---|---|---|
| market-only control (3 cols) | 6,761 | **−$14,567** | −2.15% | 51.35% | `\|pred\|≥1`: −$729 on 916 |
| XGBoost (563 feats) | 6,761 | −$24,790 | −3.67% | 50.55% | −$1,877 on 270 |
| mixture-of-experts | 6,761 | −$25,833 | −3.82% | 50.47% | **+$170 on 339** |
| LightGBM distributional | 6,761 | −$26,099 | −3.86% | 50.44% | −$127 on 144 |
| level features only | 6,761 | −$27,970 | −4.14% | 50.32% | −$1,322 on 99 |
| CatBoost | 6,761 | −$30,264 | −4.48% | 50.11% | −$4,372 on 339 |
| LightGBM (deeper) | 6,761 | −$30,584 | −4.52% | 50.08% | −$549 on 337 |
| MLP | 6,761 | −$31,427 | −4.65% | 50.04% | −$245 on 67 |
| change features only | 6,761 | −$32,031 | −4.74% | 49.99% | −$1,707 on 341 |

**Nothing made money. Winning seasons: 1 of 6 at best, 0 of 6 for three of them.**

**The ordering is the finding.** The best P&L belongs to the **market-only control with
three columns** (close, open, move). Every model that adds the 560 team features loses
MORE. Adding information to this problem costs money — the exact signature of zero
signal plus transaction costs. The richest model (change-features, 183 cols) is the
worst at −$32,031, statistically indistinguishable from betting at random.

**The single best subset discovered by ten model families and ~40 configurations is
+$170 on 339 bets.** That is the entire upside found.

## What the models said about themselves

More eloquent than any R2:

- **XGBoost**: early stopping fired at `best_iteration` = 7, 12, **0**, 9, **0**, 4
  across the six folds. Twice its own held-out training slice said *zero trees is
  optimal*. The 64-configuration inner-CV grid spanned 18.3606 to 18.4213 RMSE — a
  0.3% spread, i.e. nothing to tune.
- **CatBoost**: `best_iteration ≈ 0` in **all twelve** fold-fits; it bound against the
  a-priori 50-iteration floor. Its own validation says do not fit.
- **LightGBM distributional**: `sd(pred) = 0.686 pts` against a **1.13-pt hurdle** —
  the model's entire dynamic range is smaller than the price it must beat, so it is
  *arithmetically* incapable of clearing the vig regardless of accuracy.

## The gates you set

| gate | result |
|---|---|
| Residual prediction R2 > 0 | **fail** — best +0.0022%, six of nine negative |
| Stability across seasons | **fail** — 1/6 winning seasons at best |
| Localization (top vs bottom decile) | **fail, and backwards** — 6 of 7 models realise *smaller* \|dev\| in the decile they call most volatile |
| Direction in high-error subset | **fail** — top-10% ROI worse than all-games for 5 of 7 |
| Economics at actual juice | **fail** — every model loses |
| EV(high-error) > EV(all) | 3 of 7 "pass" — but both sides are negative, so it ranks two losses |

The localization gate failing *backwards* matters most for your framing: the models
cannot even identify which games are volatile, let alone which way they break.
`nba-factor-decomposition` already showed \|dev\| is unpredictable; this confirms it
with nine estimators and a distributional head.

## Verdict as a trading question

There is no trade here. Not "the edge is too small" — **the P&L is negative in every
formulation, and the more information we add the worse it gets.** Combined with the
prior arc (factor exposures forecastable at 27% OOS R2 worth −0.13% against the close;
the shot-volume channel capped below the vig by an information bound; the corrected
1.12-pt hurdle), NBA totals against a sportsbook closing line is closed as a
forecasting problem.

**Where trades in this programme actually are** — both are microstructure, not
forecasting, and both already have measured P&L:

1. **The FOMC / mention-market latency trade.** Scoring latency ~17s against an
   automated maker; takers earn +41.2c per contract in the 0-15s band; one FOMC event
   realises ~$5,575. This is adverse selection against a slow counterparty, not a
   forecast. It is revocable (Kalshi can close markets early) and latency-graded
   (17s vs 26s is a 3x P&L difference), which is what makes it a trading problem.
2. **Liquidity provision on wide Kalshi rungs.** The one preregistered positive-EV
   structure in the programme. Gated on the quote-inside tradeoff, and the measured
   constraint is that tight books have the size and no edge while wide books have the
   edge (+11c) and no size (10 contracts).

Both are execution problems with known P&L. The NBA totals work is a forecasting
problem with a measured negative one.

---

# ADDENDUM — THE TWO DIAGNOSTIC AGENTS (workflow completed, 10/10, zero survivors)

These do not produce a P&L. They produce the reason there isn't one.

## The open → move → close information table

Identical LightGBM in every cell, walk-forward, 6 test seasons. OOS R2 (%):

| feature block | **open** | **move** | **dev** | **\|dev\|** |
|---|---|---|---|---|
| full (team + market, 563) | **+72.67** | −0.82 | −5.66 | −6.16 |
| team only (560) | +72.67 | −0.82 | −6.21 | −7.23 |
| level `_m5/_m10/_m20/_m40` (240) | **+71.19** | −1.30 | −6.23 | −6.38 |
| change `_d5_20/_d10_20/_acc/_zreg` (240) | **+6.06** | −2.62 | −4.67 | −5.80 |
| vol/context `_sd20` + schedule (80) | −10.75 | −5.51 | −6.97 | −7.44 |
| market only (3) | n/a | n/a | −3.98 | −3.90 |

Read left to right:

1. **Everything the team features know is already in the OPEN.** Rolling levels alone
   reproduce the opening line at **+71.2% OOS R2**; the change block, the vol block and all
   the interaction terms together add 1.5 points.
2. **The MOVE is not team-driven at all** — every block at or below zero. Whatever carries
   the line from open to close (injuries, lineups, late money) is orthogonal to box-score
   history. The features that nail the open at +72.7% carry nothing about the revision.
3. **There is no block that predicts the residual but not the open.** The thing the
   exercise was designed to find does not exist. Ordering is monotone: open >> move ≈ 0 > dev.
4. **The change block is the informative null, and it answers the ΔPC1 hypothesis
   precisely.** Change features predict the open at only **+6.06%** against levels' +71.19% —
   so the market genuinely does *not* price momentum/regime-deviation features into the
   opener. That is exactly the gap the hypothesis predicted. But the same features then score
   **−2.62% on the move and −4.67% on the residual.** The market ignores fast-changing states
   because they carry no information, not because it has missed them.

## The conditional autoencoder — the cleanest efficiency statement available

16-dim bottleneck on the 20×13 sequence tensor, fit per fold on training seasons, **never
shown a betting outcome**, then frozen and probed with ridge:

| season | open | move | dev | \|dev\| |
|---|---|---|---|---|
| 2020 | **+43.09** | +0.29 | −0.41 | −0.15 |
| 2021 | **+59.66** | +0.32 | +0.00 | −0.03 |
| 2022 | **+41.19** | +0.24 | −0.00 | +0.00 |
| 2023 | **+69.77** | +1.08 | −0.09 | −0.05 |
| 2024 | **+58.31** | +0.97 | −0.10 | −0.06 |
| 2025 | **+53.76** | +1.57 | −0.00 | +0.00 |

**Z reconstructs the opening line at 41-70% OOS R2 in every fold and is at or below zero on
the closing residual in every fold.** The representation is not weak — it is a genuine,
strong, outcome-blind team-quality factor. The market has simply already used it.

Across all 96 (fold, dimension) univariate probes: open max +18.09%, **dev max +0.221%,
median −0.000%, only 42% positive.** No latent is weak on open/move and strong on dev.

## And the MLP's own verdict on itself

`alpha = 300`, the top of the grid, won **12 of 12** inner-CV selections, and in every fold
the inner-CV MSE was still **above `var(dev)`**. The train-only cross-validation
independently concluded *shrink to a constant* without ever seeing a test row.

**None of this changes the P&L table above — it explains it.** The signal decays to nothing
by the opening line and is gone before the market even revises.

## The null control, completed

Same harness, same two un-tuned models, target **shuffled within season** (12 resamples):

```
          REAL target OOS R2   |  shuffled: mean      sd        min       max
ridge         -4.4196%         |    -4.4345%      0.4649%   -5.2280%  -3.8571%
xgboost       -4.3419%         |    -4.5326%      0.3449%   -5.1164%  -4.0336%
```

**With an identical un-tuned model, the real target performs indistinguishably from a randomly
shuffled one** — xgboost beats its own null by 0.19pp, which is **0.55 standard deviations**.
Real-target economics on those same models: ridge 50.41% (z −3.35), xgboost 50.79% (z −2.73).

(These R2s are far below the tuned models' because the fixed hyperparameters here are much less
regularised — that is the point: the comparison is like-for-like against its own null, not
against the tuned scoreboard. With ~10 families searched the noise ceiling is mean + 1.6·sd.)
