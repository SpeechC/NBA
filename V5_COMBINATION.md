# COMBINING THE v5 STRUCTURAL LAYER WITH THE TWO-WAY LINE STATE

v5 Layer 1 reimplemented from the published spec (pace HL 5.7, offence 8.6,
defence 7.4, league HL 496, offseason carry 0.42, offence innovation share 0.54,
opponent-adjusted). **Their same-day batching adopted** — every game on date D is
predicted before any date-D result updates any state. `v5_combine.py`.

**My earlier loop had this leak** and the fix is free: D2 went 0.8259 -> 0.8275
under same-day batching, so nothing was being exploited.

## RESULT — the line state SUBSUMES the structural layer

Held-out 2022+, n = 4,717:

| model | MAE | RMSE | R2 |
|---|---|---|---|
| v5 structural alone (my reimplementation) | 2.948 | 3.803 | 0.7738 |
| M6 box-score block alone | 3.569 | 4.547 | 0.7379 |
| **two-way LINE states alone** | **2.350** | **3.052** | **0.8548** |
| LINE + v5 structural | 2.348 | 3.064 | **0.8532** ← worse |
| M6 + LINE | 2.358 | 3.070 | 0.8554 |
| M6 + v5 structural + LINE (everything) | 2.350 | 3.060 | 0.8554 |

**Adding the v5 structural layer to the line state makes it slightly WORSE
(0.8548 -> 0.8532). Adding the entire box-score block buys +0.0006.**

**My prediction was wrong.** I argued the two channels were capturing partly
different information and would combine. They do not — the line state contains
everything the structural basketball layer knows.

The reason is straightforward in hindsight: **the linemaker's prior openers ARE
the output of their structural model plus their private information.** Recovering
a state from the lines captures both; recovering it from box scores captures only
the first, and worse.

## Independent convergence, season by season

| season | this line-state model | their v5 exploratory |
|---|---|---|
| 2021-22 | 0.8647 | 0.835 |
| 2022-23 | **0.8154** | **0.815** |
| 2023-24 | **0.8937** | **0.903** |
| 2024-25 | 0.8362 | 0.816 |
| 2025-26 | 0.8332 | 0.839 |

**Same peak (2023-24 ~0.90) and same trough (2022-23 ~0.815), from two
independent architectures.** That is strong evidence both are recovering the same
underlying object rather than fitting noise.

**Consequence for their open validation question:** their exploratory 0.867 was
flagged as not-yet-nested. This model reaches 0.8548 under stricter conditions —
a purely recursive state with no parameters fitted against the target, same-day
safe, chronological. **Their 0.867 is very likely real, not a validation
artifact.**

## Caveat on the comparison

My reimplementation of Layer 1 reaches 0.7738 against their reported 0.792 — I
used their published hyperparameters without re-tuning and did not separately fit
`wP/wO/wD`. **A better structural layer might behave differently**, though the
gap would have to be large: a layer at 0.774 adds nothing to a state at 0.855,
and one at 0.792 is unlikely to differ in kind.

## What this implies for both efforts

**Further work on the structural basketball layer has low marginal value.** It is
already dominated, and the dominating object is cheaper to build — two recursive
states, two hyperparameters, no feature engineering.

The remaining ~0.145 is not in the basketball representation. Per the error
concentration analysis:

```
worst 10% of games hold 50.7% of squared error
fix worst 10%  ->  R2 0.9175
|error| ~ (doy, rest, pace, efficiency, |spread|)   R2 0.0016
corr(|error|, |close-open|) = +0.2147
```

**The 0.90 target is a ~10% subset of games, unpredictable from observables, and
correlated with how much the market itself repriced.** Injury VORP addresses part
of it (+0.006 on the opener, ~8% of the market's revision) and is the only
external input tested that moves the number at all.
