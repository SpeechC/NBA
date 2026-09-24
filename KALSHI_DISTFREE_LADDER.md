# Distribution-free ladder inference (2026-09-24)

Runs the agreed sequence on the 2025-26 Kalshi totals board, 1,312 events joined
to the posted closing total. **No midpoint anywhere.**

## 1. Executable intervals — the NO side is mechanically redundant

`L_K = max(YES bid, 1 − NO ask)`, `U_K = min(YES ask, 1 − NO bid)`.

**Verified on 470 live markets across 4 series (`KXNBAGAME`, `KXNFLGAME`,
`KXNFLTOTAL`, `KXNFLSPREAD`): `no_bid ≡ 1 − yes_ask` and `no_ask ≡ 1 − yes_bid`,
0 violations.** Kalshi's NO book is the exact complement, not an independent
book, so the two-sided tightening collapses to `[yes_bid, yes_ask]`. Step 1 is
satisfied exactly rather than approximated — and it adds no information here.

## 2. Distribution-free monotone feasibility — 99.9% pass

Exact greedy check (`S₁ = U₁`, `S_j = min(U_j, S_{j−1})`, feasible iff
`S_j ≥ L_j`): **99.9% of 1,312 ladders** admit a monotone survival curve inside
their executable quotes, on all rungs and on the body alone. The single failure
violates 1 rung of 11.

**There is no stale/asynchronous cross-rung quoting problem.** Whatever rejects
the normal is not incoherent quoting.

## 3. THE 70% NORMAL REJECTION IS MOSTLY TICK GRANULARITY — revision

This supersedes the "shape rejection" reading in `KALSHI_SIGMA_ENVELOPE.md`.
`KXNBATOTAL` is `linear_cent`: a 1¢ grid cannot represent a probability more
finely than ±0.5¢. Re-running normal feasibility with rounding slack:

| slack | normal feasible |
|---|---|
| ±0.0¢ | 30.1% (397/1318) |
| **±0.5¢** (the tick's own rounding unit) | **66.6%** (878/1318) |
| ±1.0¢ | 90.5% (1193/1318) |
| ±1.5¢ | 98.0% (1292/1318) |

**Two thirds of ladders admit a normal once the tick is respected.** The 30.1%
figure measures the price grid, not the distribution. It should not be cited as
evidence of curvature.

## 4. Nonparametric quantile widths — NOT IDENTIFIED, structurally

From the envelope, `K*(s) ∈ (max{K : L_K > s}, min{K : U_K < s})`:

| width | identified both sides | band |
|---|---|---|
| **W68 = Q84 − Q16** | **0 of 1312 (0.0%)** | — |
| IQR = Q75 − Q25 | 525 of 1312 (40.0%) | median **9.00 pts** |

W68 is identified on **zero** events because the ladder does not span ±1σ —
consistent with the standing structural fact that Kalshi lists no rung beyond
|t| = 1.456. Q16 and Q84 lie outside the quoted board entirely. The IQR is
identified on 40% but with a 9-point band, three rung-spacings of slack.

**The nonparametric route is unavailable on this instrument.** That is an
instrument fact, not a sample-size problem.

## 5. Frozen empirical shape — hypothesis refuted

`Y = m + s·D_hist`, shape frozen on seasons ≤ 2024 (n = 9,067; skew **+0.2346**,
excess kurtosis **+0.4529**, sd 18.021), evaluated on grids **identical** to the
normal's (113 locations × 211 scales):

| shape | feasible | scale band |
|---|---|---|
| normal | **29.9%** (392/1312) | 1.00 pts |
| frozen empirical | **22.9%** (300/1312) | 1.10 pts |

The historical shape fits **worse**, not better. Kalshi's deviation from
normality is **not** the higher-moment structure of historical NBA totals.

*(A first pass reported 12.8% vs 30.1%; those grids differed in location step,
scale step and location range, all biasing the empirical shape down. On matched
grids the direction holds but the gap is 7pp, not 17pp.)*

Tight-body subsample (all body rungs ≤2¢): only **16 of 1,312** events qualify
and none is feasible. That identification lever is unavailable.

## 6. Scale slope vs posted total — still unidentified

Required by realised dispersion: **+0.04187**, CI [+0.01416, +0.07046].

| shape | bound | slope | 95% CI | vs required |
|---|---|---|---|---|
| normal | s_lo | +0.02256 | [+0.01079, +0.03500] | **excludes** |
| normal | s_hi | +0.05290 | [+0.02735, +0.07945] | covers |
| empirical | s_lo | +0.03045 | [+0.01585, +0.04713] | covers |
| empirical | s_hi | +0.06509 | [+0.03169, +0.10040] | covers |

The one interval that excludes the required rate is the normal's **lower**
bound — the narrowest dispersion the book permits rises more slowly than reality
demands. That is a hint of under-scaling and **not a finding**: it sits on a 30%
subsample selected on normal-feasibility, under a shape the tick analysis shows
is mostly a grid artefact, and the companion upper bound covers the requirement.

## Verdict

**Does Kalshi treat high-total games as less uncertain than they truly are?
Still unidentified — and the reason is now structural, not statistical.**

Two instrument properties bound how precisely any scale can be read from the
executable book, and neither is fixed by more games:

1. **1¢ tick.** ±0.5¢ of unavoidable rounding maps to roughly ±1 pt of σ at
   these strikes — the entire realised effect is 2.2 pts.
2. **Strike span ≤ |t| 1.456.** The quantiles that define a width (Q16, Q84)
   are not quoted.

## Next — and it is not "more games"

**Use the minute candles for within-event identification, not as extra n.** As μ
drifts minute to minute the same underlying σ is rounded onto *different* cent
grids, so the rounding error decorrelates across snapshots while σ does not.
Estimating one event-level scale across many snapshots — with the event still
the unit of inference — is the one route that attacks the 1¢ bound directly
rather than averaging over it. Fixed horizons (T−6h, T−3h, T−1h, T−30m) or μ
free by minute with a single event-level scale.

`nba_xmarket_collect.py` already captures `KXNBATOTAL` at 1-minute resolution,
so this needs collection time, not new infrastructure.

Scripts: `screen_kalshi_distfree.py`, `screen_kalshi_shape_race.py`.
