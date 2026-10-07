# The Kalshi reference line, and getting mids out of the trade path (2026-10-07)

## "Why aren't we using Kalshi's equivalent of the closing line?" — we are

`signals()` passes `ref=None` for **crewshock** and **final7**, and `run()` does

```python
ref = s["ref"] if s["ref"] is not None else mu_mkt
```

So for both close-settled strategies the reference **is** the Kalshi ladder's
own centre. That is the right design: the closing total is not knowable at
17:00 ET when CrewShock fills, and this programme established that the ladder's
implied μ *is* the close. The opener-settled pair correctly uses the captured
sportsbook opener instead, which **is** knowable at 09:00 — and the orchestrator
refuses to substitute Kalshi's centre for it, which the dry run prints
explicitly.

## But that made the mid problem much worse than recorded

`mu_mkt` came from `fit_ladder()`, which regressed `Φ⁻¹(1 − p_mid)` on strike.
So the **anchor of the entire bet** for both close-settled strategies was a
midpoint — not merely the drift guard, as previously noted.

Measured on the 951 fittable 2025-26 ladders:

| | |
|---|---|
| μ_mid − μ_bounds | mean **+0.058** pts, median +0.036, sd **0.360** |
| \|diff\| > 0.5 pt | 6.4% of events |
| \|diff\| > 1 pt | 2.1% |
| in probability | **0.79 pp** of win rate (at 2.187 pp/pt) |
| σ | mid 18.117, bounds 18.000 |

0.79pp of probability injected by a number that does not exist in the book.

## The fix

`fit_ladder()` is now **bounds-only**. The old one is retained as
`fit_ladder_mid()` and marked DO NOT USE so the error stays legible.

A rung with bid *b* and ask *a* says only that the market's probability lies in
`[b, a]`, so the estimator is the set of (μ, σ) whose survival curve sits inside
**every** quote, with half-a-tick slack because a 1¢ grid cannot express a
probability more finely:

```
b_j − slack  ≤  1 − Φ((K_j − μ)/σ)  ≤  a_j + slack
```

Closed form per rung, so no μ grid is needed in the feasible case:
`μ ∈ [K_j − σ·Φ⁻¹(1−b_j), K_j − σ·Φ⁻¹(1−a_j)]`, and a σ is feasible iff those
intervals intersect. The estimate is the centre of the feasible region.

**The important engineering detail.** On real ladders the identified set is
empty about a third of the time — no single normal fits inside the quotes:

| | |
|---|---|
| identified set non-empty | **937 / 1318 (71.1%)** |
| hinge-loss fallback used | **381 / 1318 (28.9%)** |
| unusable | **0** |

So the estimator falls back to the (μ, σ) **minimising a hinge loss** that is
zero inside each quote and quadratic in the violation outside it. That keeps it
always defined. Returning `(None, None)` there would silently drop a third of
all signals for a numerical reason — a worse failure than an approximate anchor.
(The old mid estimator was unusable on 8 ladders; the new one on none.)

## Effect on 2025-26

| strategy | reference | n | hit% | P&L | ROI |
|---|---|---|---|---|---|
| crewshock | sportsbook close | 213 | 45.54% | −$4.83 | −4.75% |
| crewshock | Kalshi μ (MID) — *old live* | 231 | 46.32% | −$6.78 | −5.96% |
| crewshock | **Kalshi μ (BOUNDS) — new live** | **236** | 46.19% | **−$4.69** | **−4.13%** |
| final7 | sportsbook close | 69 | 46.38% | −$0.40 | −1.23% |
| final7 | Kalshi μ (MID) — *old live* | 69 | 49.28% | +$1.27 | +3.89% |
| final7 | **Kalshi μ (BOUNDS) — new live** | **69** | 46.38% | **−$0.52** | **−1.61%** |

Combined: old mid −$5.51 over 300 trades, new bounds −$5.21 over 305.
**Aggregate effect is a wash**, while the individual strategies move ±5pp in
opposite directions — the mid was flattering final7 and penalising crewshock.
At this sample size those are noise.

## A sensitivity worth recording

The `sportsbook close` row moved from **−7.89% to −4.75%** between two runs of
the same replay, purely because σ came from a slightly different estimator
(grid step 0.05 → 0.25 plus the hinge fallback). **A 3pp swing from an
estimator detail** is as large as the rung-selection effect chased earlier in
this thread. One season cannot adjudicate any of these choices; it is not a
power problem that more careful analysis fixes.

## Status

- **No midpoint anywhere in the trade path.** Price paid is the ask (since
  `2a86820`), and the anchor is now bounds-only.
- Verified on the live 26OCT07 board: 21 rungs, bounds fit μ 240.59 / σ 19.50,
  identified set non-empty; the old mid fit gave μ 240.40, a +0.197 pt
  difference on a single live ladder.
- Dry run through `run_nba_trader.sh` unchanged in behaviour.

Scripts: `kalshi_reference_line.py`; code in `nba_live_trader.py`
(`fit_ladder`, `fit_ladder_detail`, `fit_ladder_mid`).
