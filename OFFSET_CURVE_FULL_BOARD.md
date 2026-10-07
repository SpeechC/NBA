# Unconditional offset curve, full 2025-26 board (2026-10-07)

Every in-band OVER rung on all 1,312 events bought **at the ask** with the fee,
settled on the actual. **14,284 rungs.** No signal conditioning — this measures
the ladder's own taker cost structure.

| rungs from line | n | ask | hit% | ask−hit | spread | fee | P&L/ct | ROI |
|---|---|---|---|---|---|---|---|---|
| −7 | 72 | 0.869 | 88.89% | **−1.96** | 3.00¢ | 0.83¢ | **+1.13¢** | +1.28% |
| −6 | 445 | 0.851 | 86.52% | **−1.45** | 3.78¢ | 0.92¢ | **+0.53¢** | +0.62% |
| −5 | 952 | 0.814 | 79.94% | +1.46 | 3.97¢ | 1.11¢ | −2.57¢ | −3.11% |
| −4 | 1215 | 0.765 | 74.32% | +2.21 | 3.74¢ | 1.31¢ | −3.52¢ | −4.52% |
| −3 | 1293 | 0.711 | 68.99% | +2.11 | 3.89¢ | 1.48¢ | −3.59¢ | −4.95% |
| −2 | 1305 | 0.650 | 62.53% | +2.47 | 3.40¢ | 1.63¢ | −4.11¢ | −6.16% |
| −1 | 1312 | 0.581 | 55.64% | +2.48 | 2.17¢ | 1.75¢ | −4.23¢ | −7.07% |
| **0** | 1312 | 0.507 | 49.01% | +1.73 | **1.49¢** | 1.80¢ | −3.53¢ | −6.72% |
| +1 | 1312 | 0.441 | 42.99% | +1.11 | 2.25¢ | 1.79¢ | −2.90¢ | −6.32% |
| +2 | 1309 | 0.387 | 36.75% | +1.99 | 3.57¢ | 1.70¢ | −3.69¢ | −9.12% |
| +3 | 1289 | 0.333 | 30.88% | +2.46 | 4.10¢ | 1.59¢ | −4.04¢ | −11.58% |
| +4 | 1196 | 0.282 | 25.42% | +2.73 | 4.33¢ | 1.45¢ | −4.19¢ | −14.14% |
| +5 | 834 | 0.236 | 21.34% | +2.24 | 4.39¢ | 1.30¢ | −3.54¢ | −14.21% |
| +6 | 342 | 0.199 | 16.67% | +3.25 | 4.37¢ | 1.15¢ | −4.39¢ | −20.87% |
| **ALL** | **14284** | 0.523 | 50.35% | **+2.00** | 3.37¢ | 1.52¢ | **−3.52¢** | **−6.53%** |

Regular season only (12,598 rungs) is materially identical.

## The board is efficient and taking costs exactly what it should

Mean overpayment `ask − hit` is **+2.00pp** against a **half-spread of 1.69¢**.
So the mid sits only ~0.3pp above the realised frequency. Add the 1.52¢ fee and
the −3.52¢/contract result is fully accounted for by **half-spread + fee**.
There is no unconditional edge anywhere on this ladder, which is what an
efficient board looks like.

## The important result: this does NOT explain the nearest-line advantage

The signal-conditioned run had max-edge picking a mean offset of **+1.83
points** (≈ +0.6 rungs) and nearest-line **+0.36 points** (≈ rung 0).
Unconditionally those two locations cost the **same**:

| | unconditional ROI | with the signal |
|---|---|---|
| rung 0 | −6.72% | nearest-line **−4.73%** |
| rung +1 | −6.32% | — |
| max-edge location (~+0.6 rungs) | ≈ −6.5% | max-edge **−7.89%** |

So the ladder's baseline is flat across the region the two policies choose
between. **The nearest-line advantage is therefore not the ladder's cost
structure — it is that the strategies' edge sits AT the line and does not travel
along the ladder.** Nearest-line converts the baseline −6.7% into −4.73% (≈ +2pp
of signal); max-edge converts ≈ −6.5% into −7.89% (≈ −1.4pp, i.e. *worse* than
no signal at all).

That is the sharpest form of the standing result that **the book prices the
median**. A signal that moves the median moves `P(total > line)`; it does not
move `P(total > line + 6)` by the amount a re-centred normal assumes, so
`p_model` off the line is overstated and max-edge selects on that error.

## A separate observation, not a strategy

Rungs **−6 and −7** have `ask − hit` **negative** (−1.45, −1.96pp) and are the
only positive cells: +0.53¢ and +1.13¢ per contract. Deep favourites are
underpriced. That is the **favourite–longshot bias**, and it matches
`paper-burgi-makers-takers` (makers on ≥50¢ +2.6%). But n is 445 and 72, the
absolute edge is under 1.2¢ on an 85¢ contract, and it is unconditional — no
signal involved. Noted, not pursued.

## My bootstrap was the wrong statistic

I ran an event-clustered bootstrap of "which rung has the best ROI" and it
returned rung −7 in 44.8% of resamples, −6 in 28.3%, and **+7 in 25.2%** — the
two thinnest buckets (n=72 and 83) plus one other. An argmax over buckets with
n ranging 72 to 1,312 is dominated by the noisiest cells and says almost
nothing. It should not be read as evidence that −7 is the best rung. The
informative statistics here are the level (−3.52¢ = half-spread + fee) and the
shape above +2 rungs, both of which rest on n > 1,000 per cell.

## Where this leaves rung selection

Three things now point the same way, with different evidence:

1. Signal-conditioned policy comparison: nearest-line better by 3.2–7.8pp,
   **paired test not significant** on one season.
2. Unconditional curve: the baseline is **flat** between the two policies'
   locations, so the difference is signal placement, not ladder cost.
3. Mechanism: `p_model` is overstated off the line, and the measured hit rate
   confirms it (43.60% realised against ~49.6% modelled at +1.83).

Still one season. The max-edge rule remains **unproven**; nearest-line is now
the better-motivated default but is not certified. The decisive evidence is
forward: the 2026-27 shadow season, where logging **both** rung choices per
signal costs nothing and settles it with real out-of-sample data.

Scripts: `offset_curve_full_board.py`, rows in `offset_curve_full_board.csv`.
