# STAGE D3 — REPAIRING THE STATE. It was not memory; it was the update channel.

Stage E found lag-2-to-4 scoring shocks entering the market innovation with
smoothly decaying, overwhelmingly significant coefficients — evidence that D2's
single-parameter state at k = 0.30 was mis-specified.

## The two-speed model FAILS, and the specification test says why

`R = w*Fast + (1-w)*Slow`, each updating on the same innovation, tuned on
2017-2021 and applied unchanged to 2022-2026. Selected `kf=0.50, ks=0.10,
w=0.65, lambda=0.6`.

```
model (HELD-OUT 2022-2026)          RMSE     MAE       R2
D2 single-speed (k=0.30)           3.336   2.574   0.8259
D3 two-speed                       3.368   2.601   0.8226      <- WORSE
```

And the decisive diagnostic — the lags do **not** collapse:

```
D2:  sh2 +0.0269 (t=+19.1)   sh3 +0.0187 (t=+13.3)   sh4 +0.0121 (t=+8.6)   R2 0.0910
D3:  sh2 +0.0247 (t=+17.3)   sh3 +0.0157 (t=+11.0)   sh4 +0.0089 (t=+6.2)   R2 0.0810
```

A 10-25% shrink with t-statistics still at 17, 11 and 6. **Per the pre-agreed
reading — RMSE barely moves and the lags persist — the defect is NOT longer
memory.**

## The real defect: the market updates on TWO channels

Positive lag coefficients mean that after a team overperforms, the market **keeps
raising its quote for several subsequent games**. That is gradual assimilation of
the game result, not a memory-length problem. So the update was re-specified to
blend the quote error with the **realised scoring surprise**:

```
update = mix * (quote error) + (1-mix) * (actual points - implied points)
```

```
update source                     k   dev R2   TEST R2   TEST RMSE
100% scoring surprise          0.02   0.3102    0.3970       6.236
75% scoring / 25% quote        0.05   0.5957    0.5602       5.348
50% / 50%                      0.10   0.7907    0.7314       4.168
**25% scoring / 75% quote**    0.20   0.8788   **0.8331**   **3.272**
100% quote error (= D2)        0.40   0.8717    0.8180       3.412
```

**D4 (75% quote error / 25% scoring surprise, k = 0.20) is the best line-only
model in the programme: RMSE 3.272, R2 0.8331**, beating D2's 3.336.

And it absorbs the lag structure that motivated the whole exercise:

```
D2 lag model    R2 0.0910   sh1 +0.0381  sh2 +0.0269  sh3 +0.0187  sh4 +0.0121
D4 lag model    R2 0.0145   sh1 -0.0153  sh2 -0.0116  sh3 -0.0081  sh4 -0.0065
```

**84% of the residual lag structure is removed.** The remaining coefficients flip
mildly **negative** and stay significant (t = −10.0 to −4.4), so the fix slightly
**overshoots** — D4 now over-weights recent performance a little. The
specification is much better, not perfect.

## What this says about the linemaker

**The market is predominantly self-referential.** Updating purely on realised
performance is a disaster (R2 0.397); updating purely on its own quote error
gives 0.818; the optimum is **75% anchoring on its own prior number, 25%
correcting toward what actually happened.**

That is a genuine architectural finding and it was invisible until the lag
diagnostic forced it. The state is:

```
Rating_t = Rating_{t-1} + 0.20 * [ 0.75*(quote error) + 0.25*(scoring surprise) ]
offseason carry: lambda = 0.6
```

## Status of the running best

| model | held-out RMSE | R2 |
|---|---|---|
| Stage B M6 (all box-score blocks) | 4.508 | 0.7444 |
| D2 single-speed latent ratings | 3.336 | 0.8259 |
| D3 two-speed | 3.368 | 0.8226 |
| **D4 dual-channel** | **3.272** | **0.8331** |

## Agreed consequence: stop expanding the box-score feature set

Four Factors have now failed to add incremental information in **four**
independent settings — Stage 1 in-sample, Stage B OOS (where they made it
*worse*), Stage C on sigma, and Stage E on the update rule. Further
decomposition of historical box scores (3P luck, rim rate, AST%, turnover and
rebound subtypes) would be specification mining against a residual driven by
something else.

**The next high-value input is PIT player availability and lineup data with
status-change timestamps, not more game statistics.** The dependent variable for
that work already exists: the D4 innovation.

**Caveat retained:** the large unexplained share is *evidence for* missing
contemporaneous information, not proof of it. D3 and D4 have just demonstrated
that part of what looked like missing information was in fact state
mis-specification — and some residual may still be.
