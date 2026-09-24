# Repeated shifted ladders: not identified from this sample (2026-09-24)

Tests whether intersecting many pregame ladder snapshots tightens the event-level
σ set enough to read Kalshi's dispersion scaling. Run on
`kalshi_nba_candles.sqlite` — 1-minute bid/ask for `KXNBATOTAL`, 429 events,
4,719 markets, 2025-10-21 → 2025-12-23. **No midpoint anywhere.**

Closed form, so no μ grid: for rung K with executable bounds [L, U],
`μ ∈ [K − σ·Φ⁻¹(1−L), K − σ·Φ⁻¹(1−U)]`. A snapshot is feasible at σ iff the
per-rung μ intervals intersect; the event's set is the intersection over
snapshots, with μ_t free per snapshot and σ common.

Bounds are **tick-aware**: ±0.5¢, the 1¢ grid's own rounding unit.

## Restriction 2 first — σ IS stable across the pregame window

| | no thinning (n=224) | ≥1 rung of μ movement (n=331) |
|---|---|---|
| early/late bands **overlap** | **95.1%** | **97.3%** |
| late − early band centre, mean | −0.045 | −0.249 |
| median | +0.025 | −0.075 |
| sd | 1.356 | 1.646 |

Early = T−6h..T−3h, late = T−1h..T−30m. No systematic drift in either
direction. **Common-σ across the pregame window is supported** — the assumption
was worth testing and it passes.

## Restriction 1 — and this is what kills it

| window | raw minutes | distinct book states | states after requiring ≥1 rung of μ movement |
|---|---|---|---|
| T−6h..T−3h | 160 | 30 | **1** |
| T−1h..T−30m | 31 | 7 | **1** |

> **CORRECTED 2026-09-24.** The rung criterion was an order of magnitude too
> coarse. With σ ≈ 18.2, `∂p/∂μ = φ(0)/18.2 = 0.0219`/pt, so a **half-tick
> re-round needs only 0.23 pts** near the centre (~0.35 at 20/80¢, ~0.5 at
> 10/90¢). Requiring 3 points discarded almost every useful re-rounding, so
> "μ does not move" is NOT supported by that test. See §"Phase-shift" below.
> The 2.3 pt headline is unaffected — the all-distinct-states calculation
> already used every snapshot.

Requiring a full rung of location movement leaves a median of **one** admitted
state per event — but that criterion is far too coarse to be informative.

## The band, against the bar set in advance

| window | one snapshot | all distinct states | ≥1 rung movement |
|---|---|---|---|
| T−6h..T−3h | 4.55 pts | **2.35** | 4.15 |
| T−1h..T−30m | 2.85 pts | **2.30** | 2.80 |

The bar: **0.2–0.3 pts** would settle the question; **~1.0 pt** was already
declared insufficient. The best achievable is **2.3 pts** — and that is the
optimistic figure, counting quote flickers that do not re-round μ. On the honest
thinning it is 2.8–4.2.

Note these bands are wider than the 1.0 pt reported in
`KALSHI_SIGMA_ENVELOPE.md`. That figure had **no tick slack** and so treated a
1¢ quote as an exact probability. 2.3 pts is the tick-aware number.

**The realised effect being tested is 2.2 pts of σ across the entire total
range. The per-event identified band is 2.3 pts.** The instrument cannot
resolve it.

## Verdict

**Not identified from the available 429-event pregame history at the precision
this effect requires.** The stronger product-level impossibility claim is not
proven — it would need phase-shifted repeated books to be shown incapable of
tightening the interval on a much larger sample. The 1¢ tick and truncated
ladder make it plausible; they do not establish it. Mechanically:

1. A 1¢ tick maps to roughly ±1 pt of σ at these strikes.
2. The ladder omits the quantiles a width needs (no rung beyond |t| = 1.456).
3. **μ re-phases the grid only ~2 times per event.** It is not stationary — see
   below — but two independent re-roundings cannot collapse a 4.5 pt
   single-snapshot band below ~2.3.

## Phase-shift test — the corrected criterion

Retaining a snapshot only when the modelled probability moves ≥0.5¢ at ≥3 body
strikes, with location taken continuously from the closed form (a first pass
used the centre of the bracketing strikes, which is quantised to 1.5 pts and
structurally cannot see a 0.23 pt move — it reported a spurious median travel
of exactly 0.00):

| window | location travel, median | p90 | phase-distinct states, median | ≥3 states |
|---|---|---|---|---|
| T−6h..T−3h | **0.45 pts** | 1.66 | **2** | 41.5% |
| T−1h..T−30m | 0.10 pts | 0.55 | 1 | 7.8% |

**μ does move** — 0.45 pts median early, about twice the 0.23 pts a half-tick
re-round requires. The limit is not stationarity but *count*: roughly two
phase-distinct books per event. Thinning to them alone gives 3.35 pts (early) /
2.68 (late), necessarily wider than the all-states 2.35 / 2.30, since dropping
snapshots only removes constraints.

More games does not fix (1) or (2). In-play data would break the common-σ
assumption by construction.

## Withdrawal: Kalshi's tail curvature

`MAKER_PREFLIGHT_VERDICT.md` concluded the venue "already embeds the same
right-skew curvature", on a quadratic coefficient of −7.09e−05 ± 1.16e−05,
**t = −6.09**. That evidence is **withdrawn as overstated**. It was computed at
**mid** ("At mid, against its own realised settlement frequency…"), so it is
subject to both defects found here: a midpoint is not an executable price, and
the test was not tick-aware. Once ±0.5¢ of slack moves normal feasibility from
30.1% to 66.6%, exact-containment failure is not evidence of curvature.

Curvature may still be there. It must be established **against the discrete
quote grid**, from executable bounds, not inferred from a normal failing to
contain mids. The downstream conclusion of that document — *do not freeze
H-MAKER* — rests on four other independent failures and is unaffected.

## Status of the whole thread

- **Established:** dispersion of `actual − closing total` rises with the closing
  total (8-bin sd 17.53 → 19.05; quintile ratio 1.048, see `MATCHUP_DISPERSION_STUDY.md`), and **no** additional matchup-state
  heteroskedasticity exists out of sample (19 point-in-time features, BP
  p = 0.122, OOS corr −0.014).
- **Not identified from the available 429-event pregame history** at the
  required precision: whether Kalshi prices that total-dependent dispersion.
  Not proven impossible in principle.
- **Not a next step:** any new matchup-model search. Three operationalisations
  have now agreed.

Script: `screen_kalshi_repeated_ladders.py`.
