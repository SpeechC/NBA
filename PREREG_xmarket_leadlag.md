# PREREG — Kalshi cross-market coherence and lead-lag (2026-27)

Written **2026-09-24**, before the season, on a 3-event offseason pilot. Frozen
before the data that will test it exists. Amendments append, never rewrite.

## Why this and not the sportsbook

`CROSS_MARKET_SIGMA_SCAN.md` found the closing sportsbook spread and moneyline
agree to ~1.4pp, with no conditional exception surviving multiplicity across 8
dimensions. The remaining plausible inefficiency is **temporary cross-market
incoherence on a thinner, machine-priced venue**, not permanent mispricing on a
mature one.

**The methodological rule for this whole file:** a price-discovery test comes
first, and a settlement-P&L test only runs if it passes. A structural
inconsistency is not automatically tradable. Treating one as tradable is the
error that produced the withdrawn claim in `CROSS_MARKET_SIGMA_SCAN.md` §6.

## Data

`nba_xmarket_collect.py` → `~/data/kalshi_local/kalshi_nba_xmarket.sqlite`.
1-minute candles for `KXNBAGAME`, `KXNBASPREAD`, `KXNBATOTAL`.

**Kalshi deletes the markets of settled events** (verified 2026-09-24: 1,448
settled `KXNBAGAME` and 1,324 settled `KXNBASPREAD` events still listed, zero
markets on any status filter). Candles reconstruct the full intraday path
retroactively while a market lives, so this is a **daily capture-before-purge
job, not a poller**. If the job lapses for a month the data is gone permanently.

Forward-fill per ticker at analysis time — candles emit only on book change.

## Pilot result (3 events, offseason, ≥26 days to tip) — NOT a finding

| quantity | value |
|---|---|
| aligned minutes | 43,113 |
| mid incoherence `m0+m1−1`, sd | **2.097¢** |
| \|incoherence\| > 1¢ | 49.5% of minutes |
| \|incoherence\| > 2¢ | 17.5% of minutes |
| median summed quoted spread | 4.00¢ |
| model-free arbitrage, fees in | **0 of 43,113 minutes** |

Incoherence decays at every horizon (1m → 240m). That part is a within-event
time-series fact and is solid.

**Which leg corrects is NOT established.** The labels (favourite, more liquid,
tighter) are near-constant *within* each event — favourite=leg0 runs 0.09 /
0.00 / 1.00 across the three games — so the comparison is between-event with
**n = 3**, and the block bootstrap resamples within events and cannot see that.
The apparently non-overlapping intervals are an artefact of that mismatch.
`corr(incoherence, m0−m1) = −0.255`, so the favourite label is additionally
contaminated by the level.

## Frozen hypotheses

**H1 (coherence).** Mid incoherence in `KXNBAGAME` has sd > 1¢ in-season.
*Pilot estimate 2.10¢; in-season may be tighter as attention arrives.*

**H2 (price discovery — the gate).** Conditional on \|incoherence\| ≥ 2¢ at time
t, the **wider-quoted leg** does more of the subsequent correction than the
tighter leg, over horizons 15m / 60m / 240m.
- Statistic: β from `Δmid_leg ~ incoherence`, legs labelled at time t.
- Inference: bootstrap clustered on **EVENT**, not on time blocks. n_events is
  the sample size. Report it beside every number.
- **Pass:** the two 95% intervals do not overlap, in the same direction, at
  ≥2 of the 3 horizons, with **n_events ≥ 150**.

**H3 (cross-series).** Same as H2 between `KXNBAGAME` and the `KXNBASPREAD`
rung nearest zero, once both are listed simultaneously. Index the spread ladder
by **moneyness**, never by strike label.

**H4 (execution — runs only if H2 or H3 passes).** The implied trade clears
fees and depth. Entry at the **ask** for YES and the ask side for NO; never
mid, never last. The lagging leg is expected to be lagging *because* it is
expensive to trade — H4 is where that is priced, not assumed.

## Kill conditions

- H1 fails if in-season incoherence sd < 1¢ → the venue is coherent, stop.
- H2/H3 fail if intervals overlap at ≥2 horizons with n_events ≥ 150.
- H4 fails if median edge after fee and half-spread ≤ 0.
- **Any H2/H3 pass on n_events < 150 is provisional and may not be traded.**

## Power

The unit is the **event**, not the minute. 43,113 minutes from 3 events is
n = 3. Regular season is ~1,230 games; preseason adds ~70 from early October.
n_events ≥ 150 is reached within roughly the first three weeks of games.

## Things that will bite

1. `KXNBASPREAD` was **not listed** on 2026-09-24 while `KXNBAGAME` had been
   open since 2026-08-20. H3 may only be testable close to tip.
2. NBA markets trade **in-play**. Every test above is pregame-only; the
   in-play regime is a different question and must be split off by `close_ts`.
3. Offseason quotes are not in-season quotes. The pilot's 2.10¢ may shrink.
4. The 5,000-candle cap forces 3-day chunks at 1-minute resolution.
