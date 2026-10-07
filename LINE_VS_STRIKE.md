# Is the sportsbook↔Kalshi gap in the line values? (2026-10-07)

Hypothesis: the strategies' hit rates are defined against the sportsbook
**closing total**, so the gap must be in the line values themselves.

**Answer: no — the line values agree almost exactly. The gap is the STRIKE you
are forced to bet, which is a different thing.**

## 1. The ladder IS centred on the close

μ from the executable-bounds identified set (no midpoint), n = 954 events:

| | |
|---|---|
| mean μ − close | **+0.035 pts** |
| median | **+0.001 pts** |
| sd | 0.567 |
| corr(μ, close) | **0.9975** |
| \|μ − close\| ≤ 1 pt | 94.5% of events |

The two venues post the same number. This confirms the standing result that the
ladder's implied μ *is* the closing total, now on executable bounds rather than
mids.

## 2. But you never get to bet it

Strikes sit on a **3-point grid at X.5**, so the nearest available strike is:

| | |
|---|---|
| mean (nearest strike − close) | +0.024 pts — **unbiased** |
| mean **absolute** distance | **0.688 pts** |
| sd | 0.830 |

## 3. And 0.688 points is not free

| strike − close | n | hit% | ask |
|---|---|---|---|
| (−7.5, −6.0] | 840 | 65.12% | 0.661 |
| (−3.0, −1.5] | 467 | 50.11% | 0.556 |
| (−1.5, 0.0] | 845 | 51.60% | 0.521 |
| (0.0, 1.5] | 467 | 44.33% | 0.484 |
| (1.5, 3.0] | 845 | 46.27% | 0.450 |
| (6.0, 7.5] | 466 | 33.05% | 0.370 |

Fitted slope **−2.109 pp of win rate per point of strike**, against the theory
value `φ(0)/σ = 2.187` pp/pt at σ = 18.244. Essentially exact.

So a 0.688-point mean displacement is ~1.4pp of win-rate dispersion around the
validated number. Unbiased, but it means **you are never betting the number the
hit rate was measured on.**

## 4. At the nearest-line rung the hit rate matches

| | |
|---|---|
| sportsbook over-rate at the close, full board | 49.47% |
| Kalshi hit% at the nearest-line rung | **49.01%** |
| difference | −0.46pp (se ≈ 1.4pp — consistent with zero) |

## Correction to what I said last message

I wrote that "Kalshi at the line beats the sportsbook." **That was overstated.**
Break-even win rate required:

| ask at the nearest strike | + fee | break-even | vs −110's 52.381% |
|---|---|---|---|
| 0.490 | 0.018 | 50.80% | Kalshi cheaper by 1.58pp |
| 0.502 | 0.018 | 52.00% | Kalshi cheaper by 0.38pp |
| **0.507 (board mean)** | 0.018 | **52.54%** | **Kalshi DEARER by 0.16pp** |
| 0.520 | 0.018 | 53.80% | Kalshi dearer by 1.42pp |

**Parity is at an ask of ≈0.506.** Held at an identical hit rate, Kalshi is
consistently ~0.3pp of ROI *worse* than −110:

| hit% | SB −110 ROI | Kalshi ROI | diff |
|---|---|---|---|
| 49.29% | −5.90% | −6.18% | −0.28pp |
| 52.38% | −0.00% | −0.30% | −0.30pp |
| 55.07% | +5.13% | +4.82% | −0.31pp |

final7 measured better on Kalshi (+5.96% vs +5.14%) only because its games
happened to carry a 0.502 average ask rather than the board's 0.507 — **half a
cent**. That is noise, not a venue advantage.


> **SUPERSEDED 2026-10-07 — see `EDGE_TRAVEL.md`.** The mechanism asserted below
> ("the edge sits at the line and does not travel along the ladder") is
> **withdrawn**. Measured on boxscores over all 8 seasons, the edge IS retained
> at the offsets that actually occurred: ratio to the location-shift model is
> 1.07 at the line and 1.04 at +1.5 points, and max-edge's mean offset was
> +1.83. Decay only appears beyond ±6 points, where retention is 64-71% against
> the model's 88%. The 2025-26 max-edge-vs-nearest-line gap was **noise**, as
> the paired test said (t +0.79 and +1.16, both CIs including zero); I built a
> mechanism to explain an insignificant result instead of accepting it.

## The corrected picture

1. **Line values: identical.** Median difference 0.001 points, corr 0.9975.
2. **Venue cost: Kalshi ~0.3pp of ROI worse** at the board's mean nearest-strike
   ask, flipping to cheaper below ~50.6¢. Roughly a wash, and driven by
   sub-cent ask differences.
3. **Strike quantisation: ±0.69 points, unbiased**, worth ~1.4pp of win-rate
   dispersion. Unavoidable.
4. **Rung choice: the large effect.** Max-edge moves a further **+1.83 points**
   off the close, where the validated hit rate simply does not apply — and the
   realised numbers confirm it (43.60% actual against ~49.6% modelled).

So the user's instinct was right that it is about the line — but not because
Kalshi's line differs. It is because **Kalshi's grid does not contain the line**,
and the trader then deliberately walks further away from it.

Script: `line_vs_strike_decomposition.py`.
