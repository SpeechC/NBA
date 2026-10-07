# Which rung should a taker buy? (2026-10-07)

Real 2025-26 books, realised settlement, bought **at the ask** with the fee.
Edge basis asserted in code, not assumed: `candidates()` runs `take=True` and
`price == yes_ask` on every candidate.

## Policy comparison

| | n | hit% | avg ask | mean offset | P&L | **ROI** |
|---|---|---|---|---|---|---|
| **CrewShock** | | | | | | |
| max-edge, gated *(current)* | 211 | 43.60% | 0.456 | +1.83 | −$7.88 | **−7.89%** |
| nearest-line, gated | 211 | 48.82% | 0.494 | +0.36 | −$5.11 | **−4.73%** |
| nearest-line, always | 236 | 50.00% | 0.506 | +0.05 | −$5.78 | −4.67% |
| **final7** | | | | | | |
| max-edge, gated *(current)* | 69 | 44.93% | 0.440 | +2.54 | −$0.57 | **−1.81%** |
| nearest-line, gated | 69 | 55.07% | 0.502 | +0.10 | +$2.14 | **+5.96%** |
| nearest-line, always | 69 | 55.07% | 0.507 | −0.07 | +$1.80 | +4.97% |

Nearest-line is better by **+3.16pp** (crewshock) and **+7.77pp** (final7).

## This overturns the previous message

I concluded that "the venue translation costs 2–7pp of ROI." **That was wrong —
it was a rung-selection cost, not a venue cost.** Compare like for like:

| | sportsbook −110 | Kalshi taker, nearest-line |
|---|---|---|
| crewshock (matched) | −5.90% | **−4.73%** |
| final7 | +5.14% | **+5.96%** |

**Kalshi at the line beats the sportsbook on both.** That is arithmetically
sensible: −110 break-even is 52.381%, while a 50.6¢ contract plus a 1.75¢ fee
breaks even at 52.35% — the two venues cost almost exactly the same, with Kalshi
marginally cheaper. The venue was never the problem.

## The offset curve is the stronger evidence

Every in-band rung, pooled, n = 3,263:

| strike − line | n | hit% | avg ask | P&L/ct | ROI |
|---|---|---|---|---|---|
| [−30, −9) | 680 | 75.15% | 0.781 | −4.19¢ | −5.28% |
| [−9, −6) | 303 | 67.66% | 0.687 | −2.62¢ | −3.72% |
| [−6, −3) | 305 | 62.30% | 0.627 | −2.13¢ | −3.30% |
| [−3, 0) | 305 | 55.74% | 0.554 | −1.44¢ | −2.53% |
| **[0, 3)** | 305 | 49.84% | 0.482 | **−0.17¢** | **−0.35%** |
| [3, 6) | 305 | 41.64% | 0.423 | −2.42¢ | −5.50% |
| [6, 9) | 304 | 36.51% | 0.367 | −1.84¢ | −4.79% |
| [9, 30) | 756 | 25.66% | 0.270 | −2.70¢ | −9.51% |

ROI peaks **at the line** and degrades in **both** directions, monotonically
outward. All buckets are negative because 2025-26 was a losing season overall;
the shape is the point, not the level.


> **SUPERSEDED 2026-10-07 — see `EDGE_TRAVEL.md`.** The mechanism asserted below
> ("the edge sits at the line and does not travel along the ladder") is
> **withdrawn**. Measured on boxscores over all 8 seasons, the edge IS retained
> at the offsets that actually occurred: ratio to the location-shift model is
> 1.07 at the line and 1.04 at +1.5 points, and max-edge's mean offset was
> +1.83. Decay only appears beyond ±6 points, where retention is 64-71% against
> the model's 88%. The 2025-26 max-edge-vs-nearest-line gap was **noise**, as
> the paired test said (t +0.79 and +1.16, both CIs including zero); I built a
> mechanism to explain an insignificant result instead of accepting it.

## Mechanism

`edge = p_model − ask − fee`, and `p_model` comes from a **normal at
`mu_hat = L + delta`**. The probability gain from a μ-shift is
`delta·φ(z)/σ`, largest at the money; the fee `0.07·p(1−p)` also peaks at 50¢.
Max-edge trades real probability edge for fee savings by moving off the line.

The realised numbers say that trade is bad because **`p_model` is overstated
off-line**: at a mean offset of +1.83 the model implied ~49.6% and the actual
win rate was **43.60%**, while at the line model and actual nearly agree
(48.82%). So max-edge selection is partly selecting on its own model error — it
concentrates exposure exactly where the normal is least reliable. This is
consistent with the standing result that **the book prices the median**: a
signal that shifts the median does not shift the whole distribution the way a
normal re-centring assumes.

## Why the original +24% for max-EV was an artifact

`maker_figure_provenance.py` generated truth and market from the **same normal
family with the same σ**:

```python
pmkt = 1 - norm.cdf((K - MU) / SIG)          # market
ptru = 1 - norm.cdf((K - MU - D) / SIG)      # "truth"
```

The pricing model was therefore **correct by construction**, so maximising
modelled EV had to win. On real books with real outcomes it does not. The +24%
was maker-framed *and* measured in a world where the model could not be wrong.

## Inference — and why I am not changing the trader

The paired per-game test, same board, nearest-line minus max-edge:

| | n | mean diff | t | 95% CI |
|---|---|---|---|---|
| crewshock | 211 | +1.31¢/game | +0.79 | [−1.85¢, +4.65¢] — **includes 0** |
| final7 | 69 | +3.93¢/game | +1.16 | [−2.32¢, +10.83¢] — **includes 0** |

**Neither is significant.** One season, and the rung differs on only 127 of 211
and 49 of 69 games. I have just finished criticising the practice of acting on
an insignificant single-season result, so I am not flipping rung selection on
one. The offset curve at n=3,263 is much better evidence for the *shape*, but it
pools games and is not a policy test.

What the evidence supports: **the max-edge rule is justified by a simulation
whose model was correct by construction, and on real books it does measurably
worse than the simplest alternative, in the same direction on both strategies,
with a coherent mechanism.** That is enough to call the current rule unproven —
not enough to certify its replacement.

Scripts: `rung_selection_taker.py`, curve in `rung_selection_curve.csv`.
