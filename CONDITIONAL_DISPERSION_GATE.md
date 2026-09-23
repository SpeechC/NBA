# THE CONDITIONAL-DISPERSION STRANGLE — STAGE 1 GATE (2026-09-13)

Proposal: stop forecasting the signed error and forecast its **scale**; buy both outer rungs
(a long strangle around the market median) in games whose true conditional distribution is
wider than Kalshi's implied one. Primary target `P(|D| > 15 | X)`, no normal imposed.

**Stage 1 gate, as specified: Q5 ≈ 50% vs Q1 ≈ 33% on `P(|D|>15)`. It fails on three
independent operationalizations, and on the strongest model it fails BACKWARDS.**

```
baseline   P(|dev|>15) = 0.3951    P(dev>15) = 0.2021    P(dev<-15) = 0.1930
gate asks for Q1 ~0.33 and Q5 ~0.50, i.e. a +0.17 spread
```

## Three attempts

**1. LightGBM, 563 pregame features, walk-forward OOS (n = 6,845). AUC 0.4910.**

| quintile | n | mean \|dev\| | **P(\|dev\|>15)** | predicted |
|---|---|---|---|---|
| Q1 | 1,369 | 14.514 | **0.4061** | 0.2763 |
| Q3 | 1,369 | 14.232 | 0.4054 | 0.3837 |
| Q5 | 1,369 | 13.579 | **0.3674** | 0.5068 |

`Q5 − Q1 = −0.0387 (z = −2.08)`. Realised `sd(dev)`: Q1 18.59, Q5 17.25, **ratio 0.928**
against the ~1.21 the trade needs. **The decile it calls most dispersed is the least.**

**2. Logistic, same features.** AUC 0.5042, `Q5 − Q1 = −0.0066 (z = −0.35)`, sd ratio 0.923.

**3. Recent residual volatility** — the feature named first in the proposal, and genuinely
absent from the 563-column panel (which carried `_sd20` on box-score quantities but never the
volatility of the team's own pricing residual). Built prior-only, summed over both teams:

| feature | n | corr w/ \|dev\| | t on \|dev\| | t on dev² | t on I(>15) |
|---|---|---|---|---|---|
| rsd10 | 9,327 | 0.0155 | 1.49 | 1.25 | 1.65 |
| rsd20 | 9,251 | 0.0047 | 0.45 | 0.40 | 0.85 |
| rsd40 | 9,097 | 0.0115 | 1.09 | 1.16 | 1.13 |

Conditional on the closing total it vanishes: `dev² ~ rsd20 + close` gives **rsd20 t = +0.27**
against **close t = +2.71**. Quintiles: `Q5 − Q1 = −0.0009 (z = −0.05)`, sd ratio **1.0014**.

This is now a fourth independent null on the same object, after
`nba-market-efficiency-findings`' median-split classifier at **AUC 0.4998**.

## The scale of the prize was overestimated — including by me

The worked example (σ 18.2 → 22, `P(|D|>15)` 41.0% → 49.5%) needs a **20.9%** dispersion gap.

Earlier in this session I reported Kalshi's implied σ spanning 17.37–20.36 (p5–p95) and said
the market was "already quoting the full range the hypothesis contemplates." **That number was
mostly fit noise and I withdraw it.** Fitting the ladder by probit at two independent pregame
windows on the same event:

```
corr(mu_a, mu_b)     = +0.9886     <- the centre is recovered reliably; the fit works
corr(sigma_a, sigma_b) = +0.4265   <- sigma is NOT
Spearman-Brown reliability 0.598 -> true cross-game sigma sd = 1.033 * sqrt(.4265) = 0.674 pts
```

**Kalshi's true game-to-game σ variation is about 3.6% (1 sd), not 17%.** Only ~4.5 rungs carry
a two-sided quote at a pregame snapshot (132 of 429 events fit at all), so the probit is noisy.

That cuts both ways and the honest reading is:

| quantity | value |
|---|---|
| σ gap the strangle needs | **20.9%** |
| Kalshi's true game-to-game σ variation | ~3.6% |
| largest conditional dispersion effect ever measured here (#7a, pace) | **8.1%** (Var 1.1687, z +2.10 OOS) |
| how much of that #7a effect Kalshi already prices | **+4.78% against a +4.79% realised excess** |

The single best dispersion signal this programme has found is worth 8.1% in σ, replicates out
of sample, and is priced to within **0.01 percentage points**. The strangle needs two and a half
times that effect, unpriced.

## Verdict

**Stage 1 fails. By the rule stated in advance, stop.**

The distinction drawn in the proposal is the right one — `E[D|X]` and `Var(D|X)` are different
objects and killing the first does not kill the second. But the second is now killed on its own
evidence: four operationalizations, one of them significantly backwards, and a required effect
size two to five times anything measured.

**What is NOT closed by this**, stated precisely so it is not over-read:

1. This tests whether dispersion is predictable **from pregame team state**. It says nothing
   about *in-play* dispersion, where the conditioning information is entirely different.
2. `P(|D|>15)` was targeted at the **closing** total. A strangle struck against an *opening*
   total would be a different object, since the open→close move is itself dispersion.
3. The one real dispersion effect (#7a pace) is priced **on average**. Whether it is priced
   correctly in the tails of the pace distribution specifically was never tested — but note
   the required |t| ≥ 1.5 rungs do not exist, so it would be unexpressible anyway.
