# PAPER-INSPIRED MONEYLINE TEST — direct classifier, shot location, epistemic
# uncertainty (2026-08-30)

Tests the two ideas in Montrucchio et al. (2026) that are genuinely orthogonal to
what this programme has already closed: **spatial shot-location information** and
**epistemic (model-disagreement) uncertainty**. Four frozen stages, four gates, no
ROI examined at any point.

**Result: Gates 1, 2 and 3 all fail. Gate 4 was not run.**

## Data — a real spatial representation, built from PBP

Shot zones extracted from v2 PBP descriptions (distance in feet + shot-type
keywords) over 18,330 team-games, 2017-10-17 .. 2025-04-13:

```
league zone shares  rim 34.31%  paint 9.44%  mid 18.00%  three 38.40%
league zone PPA     rim 1.231   paint 0.892  mid 0.832   three 1.086
```

Corner threes are **not** separable: NBA PBP records the minimum 3PT distance as
24 ft (0.00% at <=22 ft), so the paper's corner/above-break split cannot be
reproduced from this source. rim / paint / mid / three plus shot-type
(pullup, driving) is the representation used, with per-zone points-per-attempt,
for each team's offence AND what it allows, on prior-only 15-game windows.

Frame: **9,489 games**, 8 seasons, 98.4% shot-zone coverage. Split train <=2022,
validate 2023, **test 2024-2025** (two test seasons; the paper uses one).

## GATES 1 & 2 — does anything add to the market?

| model | Brier | log-loss | AUC | acc |
|---|---|---|---|---|
| **M0 market only** | **0.19687** | **0.57586** | **0.7608** | 0.6957 |
| M0b market features [lr] | 0.19705 | 0.57648 | 0.7606 | 0.6936 |
| M1 + team states [lr] | 0.19710 | 0.57707 | 0.7604 | 0.6962 |
| M2 + shot location [lr] | 0.19762 | 0.57822 | 0.7589 | 0.6970 |
| M2n NO market [lr] | 0.20848 | 0.60382 | 0.7290 | 0.6670 |
| M0b market features [gb] | 0.20077 | 0.58567 | 0.7519 | 0.6923 |
| M1 + team states [gb] | 0.20196 | 0.58934 | 0.7481 | 0.6850 |
| M2 + shot location [gb] | 0.20285 | 0.59149 | 0.7468 | 0.6833 |
| M2n NO market [gb] | 0.21541 | 0.61993 | 0.7102 | 0.6549 |

**Every model is worse than the market alone.** Adding team states costs
+0.00023 Brier; adding shot location costs a further +0.00052. **Gate 1 fails and
Gate 2 fails.**

## The comparison that matters

| | Brier | AUC |
|---|---|---|
| paper's market baseline | 0.210 | (acc 0.650) |
| **paper's fused model** | **0.089** | **0.951** |
| our market (n=2,327 test) | 0.19687 | 0.7608 |
| our best fused model | 0.19710 | 0.7604 |
| our best NO-market model | 0.20848 | 0.7290 |

Our market Brier (0.197) agrees with theirs (0.210). **Their fused model claims a
58% Brier reduction against their own market baseline and AUC 0.951.**

An AUC of 0.951 on pregame NBA moneylines means near-perfect winner prediction —
far beyond the market's own 0.761, on a market that sets the price with every
piece of public information. Note also that the paper's **standalone CNN heatmap
model scores AUC 0.462, worse than a coin flip**, so the spatial representation
carries nothing on its own; the claim rests entirely on fusion. A faithful test of
those same feature families on 9,489 games produces **zero** improvement.

This does not diagnose their pipeline, and their exact architecture (LSTM +
MC-dropout, CNN+PCA embeddings) was not reproduced. But an information gain of
that size from pregame box-score, form and shot-chart features — none of which is
unavailable to the market — is not consistent with anything measurable here.

## GATE 3 — does epistemic uncertainty rank probability error?

Ensemble of 24 members: bootstrap resamples x {regularised logistic,
HistGradientBoosting, RandomForest}. Genuine spread — `u` mean 0.0562, range
0.0211 to 0.1558.

**`corr(u, |edge|) = +0.3186`**, so raw `u` is partly a proxy for edge magnitude —
the `p_survive` trap. Reported both raw and residualised on `|edge|` and `p_mkt`:

| Q | raw u | Brier(mkt) | Brier(ens) | \|y − pbar\| |
|---|---|---|---|---|
| Q1 | 0.0406 | 0.20497 | 0.20591 | 0.4070 |
| Q2 | 0.0503 | 0.19495 | 0.19656 | 0.4020 |
| Q3 | 0.0577 | 0.19539 | 0.19411 | 0.4013 |
| Q4 | 0.0656 | 0.20440 | 0.20787 | 0.4223 |
| Q5 | 0.0816 | **0.18465** | 0.18843 | 0.3961 |

Non-monotone, and the **highest**-uncertainty quintile has the **lowest** Brier —
backwards from the hypothesis. Residualised, it flattens entirely (0.20297,
0.19787, 0.18848, 0.19883, 0.19619; |y − pbar| 0.4123 / 0.4007 / 0.3956 / 0.4107 /
0.4095).

**Model disagreement does not identify games where the probability estimate is
less reliable. Gate 3 fails.**

## Verdict

**Gate 4 not run**, per the pre-stated sequence. The two ideas worth taking from
the paper have now been tested on 9,489 games with two held-out seasons:

- **Shot location adds nothing** over market + team states, consistent with the
  paper's own standalone CNN result (AUC 0.462).
- **Epistemic uncertainty does not rank probability error**, and its raw form is
  contaminated by edge magnitude.
- **A direct binary classifier does not beat the market**, in either a linear or a
  boosted specification, with or without spatial features.

The paper-based branch is closed. See `PAPER_montrucchio_uncertainty_aware.md`
for the critique of its economic claim.
