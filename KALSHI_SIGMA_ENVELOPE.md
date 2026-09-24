# Does the executable Kalshi ladder scale σ with the posted total? (2026-09-24)

Supersedes the struck section of `MATCHUP_HETEROSKEDASTICITY.md`, which fit
`pregame_mid` and concluded "Kalshi prices it." **That conclusion is withdrawn.**
Quoted width on this board reaches 82¢ (median 28¢ above 90¢), so a midpoint
there manufactures a distribution nobody can trade.

**Standing rule established by that error: no midpoint anywhere in this project.
Bid/ask interval inference only.**

## Method

The book is an interval, not a point. For candidate (μ, σ) with
`p_j = 1 − Φ((K_j − μ)/σ)`:

```
L_j = (bid_j − p_j)²   if p_j < bid_j
      0                if bid_j ≤ p_j ≤ ask_j
      (p_j − ask_j)²   if p_j > ask_j
```

Rather than minimise to a point, this reports the **identified set** — every
(μ, σ) with zero loss — and reads off `[σ_lo, σ_hi]`, the dispersion the
executable book actually permits.

**Scale from the body only.** `NBA_TOTALS_SKEW_ERROR.md` established the outcome
is OT-right-skewed while the ladder is fitted normal, so outer rungs are
excluded (body = quote interval inside [10¢, 90¢]) and the tails are used only
as a consistency check. Otherwise skew masquerades as variance.

Join to the posted closing total via a 3-letter → city map, **validated 30/30
with zero unmapped**; 1,312 of 1,318 events joined.

## Finding 1 — 70% of ladders admit NO single normal
> **REVISED 2026-09-24 — see `KALSHI_DISTFREE_LADDER.md` §3.** This is mostly
> the 1¢ tick, not distributional shape. With ±0.5¢ of rounding slack -- the
> grid's own rounding unit -- normal feasibility rises from 30.1% to **66.6%**,
> and to 90.5% at ±1¢. Do not cite the 30% as evidence of curvature. The
> distribution-free monotone check passes on **99.9%** of ladders, so there is
> no stale-quoting problem either.

| body rungs | events | feasible |
|---|---|---|
| 9 | 12 | 58.3% |
| 10 | 40 | 52.5% |
| 11 | 1,256 | **28.8%** |

Only **397 of 1,318** events have a non-empty identified set. Feasibility falls
as constraints rise, and when infeasible the normal misses by just **1–2 rungs
of 11** (391 events miss 1, 268 miss 2, 165 miss 3).

So the ladder is *nearly* normal and reliably not exactly normal, at executable
precision — the curvature result of `KALSHI_NBA_MAKER_PREFLIGHT`, now reproduced
with **no midpoint anywhere**. This is a stronger form of it: not "the fitted
normal has curvature residuals" but "no normal lies inside the quotes at all."

## Finding 2 — the scaling question is NOT settled

On the 397 feasible events (median σ band width **1.00 pts**, IQR 0.47–1.92;
median μ band 0.25 pts):

| posted total | n | σ_lo | σ_hi |
|---|---|---|---|
| 220.6 | 74 | 17.334 | 18.359 |
| 227.0 | 65 | 17.503 | 19.106 |
| 231.0 | 70 | 17.671 | 19.226 |
| 234.0 | 61 | 17.600 | 19.438 |
| 236.6 | 63 | 17.659 | 19.454 |
| 242.8 | 59 | 17.876 | 19.592 |

| slope of σ per point of posted total | estimate | 95% CI |
|---|---|---|
| σ_lo (narrowest the book allows) | +0.02331 | [+0.01155, +0.03532] |
| σ_hi (widest the book allows) | +0.05473 | [+0.02944, +0.08355] |
| **realised** (`MATCHUP_HETEROSKEDASTICITY.md`) | **+0.04187** | [+0.01416, +0.07046] |

Both book bounds **overlap** the realised interval. The executable book is
therefore *consistent with* correct scaling — and that is all that can be said:

1. The identified band is ~1.0 pt of σ wide, which straddles the entire
   realised effect (17.53 → 19.05 is 1.5 pts across the whole total range).
2. The realised CI is itself wide, [+0.014, +0.070].
3. **The 397 feasible events are a selected subsample** — games whose ladder
   happens to be normal-compatible, i.e. 30% chosen on a property related to
   the shape being estimated.

**Verdict: not established, in either direction.** Neither "Kalshi prices the
scaling" nor "Kalshi misprices it" is supportable from the executable book.

## Tail consistency check

With σ at its body-implied lower bound, outer rungs fall outside their own
quotes on **2 of 52** (3.8%). Reported as a check, never as scale.

## What would settle it

1. **Drop the normal.** Fit a two-parameter scale + skew family inside the same
   bid/ask bounds; feasibility should rise well above 30% and remove the
   selection. This is the single highest-value next step.
2. **Forward collection at better resolution.** `pregame_*` is one snapshot per
   market; `nba_xmarket_collect.py` now captures 1-minute candles for
   `KXNBATOTAL`, giving many books per game instead of one.
3. **Tighten the band** by using only games where the quoted width is ≤2¢
   across the body — median width is already 2¢, so a tight-book subsample is
   available and would narrow the identified set.

Script: `screen_kalshi_sigma_envelope.py`. The superseded mid-based script
`screen_kalshi_sigma_vs_total.py` is retained with a header marking it invalid.
