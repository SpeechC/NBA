# Historical taker results per strategy — 2025-26 (2026-10-07)

**Only one season is measurable.** The team-stats database carries historical
lines back to 2017 but **no bid/ask**, and Kalshi books exist only for 2025-26.
A taker replay needs an executable ask, so it cannot reach any earlier season.
The 8-season records in `MONITOR_SEASON_PNL.md` are sportsbook results at −110
and are **not comparable**.

Method: each strategy's real 2025-26 signals, re-priced through the trader's own
`candidates()` and `gate()` with `take=True`, buying the max-edge rung **at the
ask**, paying the Kalshi fee, **settled against the actual final total**. These
are realised outcomes, not expected values.

| strategy | book | signals | traded | **Kalshi hit%** | **P&L** | outlay | **ROI** | ¢/ct | SB hit% |
|---|---|---|---|---|---|---|---|---|---|
| **crewshock** | pregame *(right)* | 238 | 211 | **43.60%** | **−$7.88** | $99.88 | **−7.89%** | −3.73¢ | 49.29% |
| **final7** | pregame *(right)* | 58 | 58 | **41.38%** | **−$2.74** | $26.74 | **−10.25%** | −4.73¢ | 53.45% |
| move | 09:00 *(right)* | 179 | **1** | — | — | — | — | — | — |
| move | pregame *(wrong book)* | 179 | 30 | 46.67% | +$0.80 | $13.20 | +6.07% | +2.67¢ | 56.67% |
| **pacegap** | — | — | — | **not replayed** | | | | | |

**Live configuration (right book, OVER-only, as armed): 270 trades, −$10.13,
ROI −7.97%.**

`SB hit%` grades the same games against the **line** at a sportsbook — the old
basis. It is not comparable to Kalshi hit%, which grades a **rung**.

## The structural fact in these numbers

Kalshi hit rate is **systematically below** the sportsbook hit rate: 43.60% vs
49.29% for crewshock, 41.38% vs 53.45% for final7. That is not a failure, it is
the translation: for an OVER the max-edge rung sits **above** the line, so it
wins less often and pays more. The taker loss is where that trade-off stops
paying once the half-spread and fee come out.

## Why this diverges from the +$6.35 projection

The projection is an **expected value under each strategy's published hit
rate**. This is **one realisation at the hit rate the season actually
delivered** — and 2025-26 under-delivered badly:

| | assumed | 2025-26 actual (SB basis) |
|---|---|---|
| crewshock | 54.21% | **49.29%** |
| final7 | 55.29% | 53.45% |

`MONITOR_SEASON_PNL.md` already flags 2025-26 as the season crewshock's
mechanism weakened (`b_fouls` 0.4775 against a prior-seven range of 0.79–1.36)
and the season with its **most bets ever, 238** — the frozen-threshold
selectivity problem. So the only season with Kalshi books is also a known-bad
season for the strategy that dominates the trade count.

**Neither number is "the" answer.** The projection is hit-rate-sensitive and
this is n=1 season. What the pair establishes is that the whole thing lives or
dies on the hit rate holding up, and that at 2025-26's realised rates it loses
as a taker.

## Two defects found while computing this

**1. `DATASET_H` labels Play-In separately from Playoffs.** Matching only
`'Playoff'` let the 6 play-in games through and pushed the 2025-26 "last
regular-season date" from **2026-04-12 to 2026-04-17**, moving final7's entire
7-day window and giving 21 signals instead of 58. Fixed by matching
`'Playoff|Play-In'`. **The live trader takes `NBA_LAST_REGULAR` from the
environment** (currently `2027-04-11`), so the same mistake there would bet the
wrong week — it must be the last regular-season date, **not** the play-in end.

**2. The final7 backtest window and the trader's window disagree.**
`MONITOR_SEASON_PNL.md` reports **69** bets for 2025-26. The trader's rule,
`0 <= (last − d).days < 7`, yields the 7 calendar days 04-06…04-12 = **58**
games. The missing 11 are exactly the 2026-04-05 slate, so the backtest window
spans 8 calendar days, not 7. The validated 55.29% is therefore on a window the
trader does not implement. Needs reconciling before April.

## What is not measured

- **pacegap** — its signal is `E_pace` from the frozen engine and no per-game
  2025-26 export exists. Reconstructing it means running `frozen_models`
  walk-forward across the season. Not approximated here.
- **move on the correct book** — the 09:00 ET reconstruction exists for only 54
  events, which overlaps move's 179 OVER signals on **one** game. The
  near-close figure is shown only to make the sample size visible; it is the
  wrong book for an opener-settled strategy and selects on line movement.

Script: `taker_history_2025_26.py`.
