# Montrucchio, Barbierato & Gatti (2026) — "Uncertainty-Aware ML for NBA
# Forecasting in Digital Betting Markets", *Information* 17(1):56

PDF: `C:\Users\rando\Downloads\information-17-00056-v2.pdf` (24pp, MDPI, open
access, doi 10.3390/info17010056). Received 2025-10-17, published 2026-01-08.

**Why it matters here:** its headline claim is the direct opposite of our
conclusion. We find the moneyline channel closed; they find it is the one market
where economic value emerges.

## What they claim

> "Economic value emerges primarily in less-efficient segments of the market: The
> fused predictor outperforms both market-only and non-market-only variants on
> moneylines, while spreads and totals show limited exploitable edge, consistent
> with higher pricing efficiency."

Note this is **an efficiency claim, not an uncertainty claim** — the paper does not
argue moneylines carry more outcome uncertainty than totals. On that separate
question our own measurement runs the other way: moneyline Brier **0.20498** vs
0.25000 for a totals over/under (n=9,570), because the moneyline inherits the
spread's information (p from 0.065 to 0.963, 69.7% of games outside [0.40,0.60])
while a total is pinned at p=0.500 by construction.

## Method

MC-dropout LSTM over team form, plus CNN+PCA shot-chart embeddings and market
features (`implied_prob_team`, spread, total, overround). Strict chronological
split: train <= 2022, validate 2023, **test 2024 only**. Decision layer:
0.3-Kelly, EV = p*o > 1.1, EUR 100 per-bet cap, odds capped at 10.0, bankroll
starts at EUR 100.

Their reported market baseline is Brier **0.210** / accuracy 0.650, close to our
measured market Brier of 0.20498 over 2017-2026. **We do not disagree about the
market's calibration.**

## The headline economic result

```
main model (LSTM + MC-dropout):  EUR 100 -> ~EUR 100,000   in ONE season
```

A ~1000x return across a single NBA season. Their own tabular baselines on the
same protocol:

| model | Acc | Brier | log-loss | final BK | ROI |
|---|---|---|---|---|---|
| market-implied (no model) | 0.650 | 0.210 | 0.590 | 100.00 | 0.000 |
| logistic regression | 0.688 | **0.199** | **0.583** | 80.34 | −0.197 |
| XGBoost | 0.680 | 0.202 | 0.589 | 143.76 | **+0.438** |
| GRU sequence | 0.604 | 0.232 | 0.657 | **0.00** | **−1.000** |

## Four reasons the economic result should not move our conclusion

**1. The winning baseline is 36 bets.** XGBoost's +43.8% ROI comes from **36
wagers** at hit rate 0.389. se(hit) = 8.1pp. That is not an estimate of anything.
Meanwhile the logistic model with the BEST Brier and log-loss loses 19.7%, and the
GRU goes bankrupt. Economic outcome is uncorrelated with probability quality
across their own table — which they note, attributing it to "non-linear"
interaction with the staking rule. The simpler reading is that at these sample
sizes the bankroll column is noise.

**2. Their control is degenerate by construction.** To show the staking engine
cannot manufacture growth, they feed it market-implied probabilities and get
exactly EUR 100 with a bootstrap of [100, 100]. But `p = 1/o` gives
`EV = p*o = 1.0 < 1.1` for **every** game, so the filter places **zero bets**. A
control that never wagers cannot detect the failure mode that matters: a
miscalibrated model that overstates longshot probabilities, clears EV > 1.1
precisely on long odds, and is then rewarded by the odds cap of 10.0. The
appropriate control is a noise model matched on bet volume and odds profile.

**3. The mechanism the result requires is absent in our data.** A strategy that
profits through an EV filter at long odds needs longshots to be underpriced. On
19,352 team-sides, 2017-2026 regular season, betting the posted price:

| decimal odds | n | hit rate | break-even | ROI |
|---|---|---|---|---|
| 1.0-1.5 | 5,456 | 0.7603 | 0.7837 | −4.01% |
| 1.5-2.0 | 4,671 | 0.5656 | 0.5848 | −3.98% |
| 2.0-3.0 | 4,754 | 0.4041 | 0.4141 | −3.69% |
| 3.0-5.0 | 2,850 | 0.2589 | 0.2673 | −4.99% |
| 5.0-10.0 | 1,420 | 0.1514 | 0.1505 | −5.26% |
| **10.0+** | 201 | 0.0597 | 0.0834 | **−31.50%** |

Every band loses roughly the vig, and **the longest odds are the worst band of
all**. This matches our decile calibration test, which found no
favourite-longshot bias anywhere (all eight deciles |z| < 1.3). There is no
longshot mispricing in this market to harvest.

**4. "Moneylines are less efficient than spreads/totals" is confounded with the
odds range.** That conclusion is inferred from where their bankroll grew in one
season, not from a direct efficiency test. An `EV > 1.1` filter can only fire
where quoted odds span a wide range. Moneylines run from ~1.07 to their 10.0 cap;
spreads and totals are pinned at ~1.91 on both sides. So the filter mechanically
finds "value" only in the moneyline market **regardless of relative efficiency**.
Our own work reaches the opposite ordering by direct measurement: the moneyline is
a deterministic transform of the spread (held-out MAE 1.42c) whose smile is
calibrated to 0.42pp against outcomes and 3x more accurate than a constant sigma.

## What is sound, and worth borrowing

- Strict chronological splitting, with ablations against odds circularity.
- Honest reporting of failures: the GRU losing 100%, the best-calibrated model
  losing money, the CNN underperforming tabular baselines.
- Explicit acknowledgement of frictionless execution, and that injury news and
  line movement are excluded — the latter is exactly the timing channel our own
  injury work found is worth +0.544 pts/sd (t = +16.16) between open and close.
- Calibration-first evaluation (ECE/MCE) rather than accuracy-only.

## Verdict for this programme

**No change.** The paper does not test market efficiency directly; it reports
where a Kelly simulator grew a bankroll in a single test season, on a protocol
whose control cannot fire. Its one directly comparable measurement — market Brier
~0.21 — agrees with ours. The mechanism its headline result would require
(longshot underpricing) is measurably absent across 19,352 sides.

Cross-reference `paper-winkelmann-efficiency-simulations`: efficient markets
produce season-level "significant" findings >75% of the time. A single-season
bankroll curve is exactly the statistic that finding warns about.
