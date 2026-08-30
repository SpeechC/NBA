# Are the dev distributions Gaussian? — audit 2026-08-29

Every points→hit-rate conversion in this program uses `φ(0)/σ = 0.3989/σ`,
which assumes normality. That assumption is now tested. n = 9,486 regular-season
games, 5.13% with overtime.

## The answer splits by market

| series | sd | skew | exc. kurtosis | Jarque-Bera p | verdict |
|---|---|---|---|---|---|
| FULL total | 18.06 | **+0.232** | +0.395 | 1.3e-32 | **NOT Gaussian** |
| FULL spread | 13.24 | +0.005 | **+0.498** | 4.9e-22 | **NOT Gaussian** |
| 1H total (resid) | 11.91 | +0.044 | +0.011 | **0.21** | **Gaussian** |
| 1H spread (resid) | 10.77 | −0.004 | +0.100 | **0.14** | **Gaussian** |

**First halves are Gaussian; full games are not.** Both full-game series are
**leptokurtic** — more mass at the centre *and* in the tails, less in the
shoulders. The full total is additionally **right-skewed (+0.232)**, which is
the overtime mixture: 5.13% of games get a one-sided scoring jump. The full
spread is almost perfectly symmetric (skew +0.005) but just as leptokurtic.

1H escapes both because it contains no overtime and fewer garbage-time blowouts.

## A structural fact that matters more than the shape

The win-probability gain from `x` points of edge is a **step function**, not a
smooth curve, because totals and margins land on integers and half-integers:

**FULL TOTAL** — exact empirical gain
```
edge 0.25 -> 1.08pp      edge 1.00 -> 2.30pp
edge 0.50 -> 1.08pp      edge 1.60 -> 4.60pp
                         edge 2.00 -> 4.60pp
```

0.25 and 0.50 points buy **identical** probability; so do 1.60 and 2.00. Key
numbers, not density, decide what a half-point is worth.

## What this does to the conversion — the Gaussian was CONSERVATIVE

Points of edge required to clear −110 (+2.381pp):

| market | Gaussian (used all session) | **EXACT empirical** | error |
|---|---|---|---|
| total | 1.078 | **1.000** | 8% too demanding |
| spread | 0.790 | **0.500** | **58% too demanding** |

The leptokurtic peak means a point at the line is worth **more** than the
Gaussian says — 2.67c vs 2.21c per point on totals, 4.12c vs 3.01c on spreads.
Every edge quoted in this session was therefore **understated**, which is the
safe direction to be wrong but is still wrong.

## Two reasons NOT to simply rescale everything upward

**1. The correction only applies to effects that are AT the line.** The
conversion assumes an effect shifts the whole distribution. `PREREG_cohesion`'s
did not — β = +0.0636 (t = +0.52) near the number against +2.82 in the blowout
tail — so no density is the right one for it, and its realised **−3.56% ROI**
stands. `CrewShock` does qualify: near-number cell 55.49%, so its
1.607 points is genuinely **1.61×** the 1.000 required, not 1.49×.

**2. The Gaussian's conservatism was accidentally offsetting prediction error.**
For MOVE_COMBINED, mean |m| = 1.610 points:

```
Gaussian implied   53.53%      EXACT implied   54.60%      REALISED   53.44%
```

The Gaussian was nearly exact and the empirical CDF **overshoots by 1.2pp**.
The reason: |m| is a *predicted* move, and a noisy prediction of 1.6 points
delivers less than 1.6 points of true edge. The conversion assumes you actually
get the points.

## Practice going forward

- Use the **exact empirical CDF**, not `φ(0)/σ`, and state which market —
  spreads and totals differ by nearly 2× in points-required.
- Never convert a **predicted** quantity as though it were a realised shift;
  report both the conversion and the realised rate, and prefer the realised.
- Check whether the effect sits **at the line** before converting at all.
- 1H work may use the Gaussian; full-game work should not.
