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
| **final7** | pregame *(right)* | 69 | 69 | **44.93%** | **−$0.57** | $31.57 | **−1.81%** | −0.83¢ | 55.07% |
| move | 09:00 *(right)* | 179 | **1** | — | — | — | — | — | — |
| move | pregame *(wrong book)* | 179 | 30 | 46.67% | +$0.80 | $13.20 | +6.07% | +2.67¢ | 56.67% |
| **pacegap** | — | — | — | **not replayed** | | | | | |

**Live configuration (right book, OVER-only, as armed): 281 trades, −$7.96,
ROI −6.03%.**

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
| final7 | 55.29% | 55.07% |

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

**2. The final7 window was off by one day. RECONCILED AND FIXED.** Full
derivation below.

## What is not measured

- **pacegap** — its signal is `E_pace` from the frozen engine and no per-game
  2025-26 export exists. Reconstructing it means running `frozen_models`
  walk-forward across the season. Not approximated here.
- **move on the correct book** — the 09:00 ET reconstruction exists for only 54
  events, which overlaps move's 179 OVER signals on **one** game. The
  near-close figure is shown only to make the sample size visible; it is the
  wrong book for an opener-settled strategy and selects on line movement.

Script: `taker_history_2025_26.py`.


---

# final7 window reconciliation — RESOLVED

## The validated rule, from the backtest itself

`monitor_season_pnl.py` lines 47–64 are the authority:

```python
d = raw[raw["lbl"].str.contains("Regular Season", na=False)]        # reg season only
d["days_left"] = (d.groupby("lbl")["date"].transform("max") - d["date"]).dt.days
d["final7"]    = d["days_left"] <= 7
```

So the window is **`days_left ∈ [0, 7]` — eight calendar days**, anchored on the
last date of the *Regular Season* label. Pushes are then dropped from the bet
count (`res_over = sign(actual − close)`); a push is a sportsbook no-action and
**cannot occur on Kalshi**, where every strike ends in .5.

## The trader was off by one

```python
return 0 <= (last - d).days < FINAL7_DAYS      # FINAL7_DAYS = 7  ->  days_left 0..6
```

Seven calendar days, not eight. It dropped the **earliest day of the window**.

| | 2017 | 2018 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | total |
|---|---|---|---|---|---|---|---|---|---|
| published | 62 | 62 | 68 | 63 | 67 | 69 | 67 | 69 | **527** |
| `days_left ≤ 7`, no pushes | 62 | 62 | 68 | 63 | 67 | 69 | 67 | 69 | **527** ✓ |
| trader's `< 7` | 56 | 54 | 61 | 53 | 55 | 57 | 57 | 58 | **451** |

**Exact match on all eight seasons.** The trader was betting 451 games where
the validated rule bets 527 — **14.4% fewer** — so the live rule was not the
rule the 55.29% was measured on.

## Fix

`in_final7_window()` now uses `<=`:

```python
return 0 <= (last - d).days <= FINAL7_DAYS     # <= : days_left 0..7, eight days
```

Verified: with `FINAL7_LAST_REGULAR = 2027-04-11` the window spans exactly 8
calendar days, 2027-04-04 … 2027-04-11.

`FINAL7_DAYS = 7` is retained deliberately so the constant reads the same as
the backtest's `days_left <= 7`; it means **eight** calendar days, and that is
now documented at both the constant and the function.

## Independent confirmation

With the corrected window the 2025-26 reconstruction produces **69 signals at a
55.07% sportsbook hit rate** — exactly the `MONITOR_SEASON_PNL.md` 2025-26
final7 row (69 bets, 55.07%). The game set is now provably identical to the
backtest's.

## Effect on the taker read

final7's one-season taker ROI moves from **−10.25% to −1.81%** (P&L −$2.74 →
−$0.57), and the live-configuration total from −$10.13/−7.97% to
**−$7.96/−6.03%**. The off-by-one was penalising the strategy as well as
mis-specifying it.

## Still outstanding

`FINAL7_LAST_REGULAR` is an environment value, currently `2027-04-11`. It **must
be the last regular-season date, never the play-in end** — `DATASET_H` labels
"Play-In" separately from "Playoffs", and in 2025-26 treating play-in games as
regular season moved the anchor from 2026-04-12 to 2026-04-17 and shifted the
entire window. Confirm the real 2026-27 date before April.
