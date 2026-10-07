# Taker economics, 2026-27 live test (2026-10-07)

**Standing constraint: we are takers only.** Every P&L/ROI figure in this
project must be computed at the ASK with the fee, on a real book. This file
**supersedes the ~$19.70/season projection, which was a MAKER number** (edge
measured against the bid).

Method: real Kalshi books; max-edge rung bought at the **ask**; Kalshi fee
`ceil(0.07·p(1−p)·n·1000)/1000`; μ and σ from the **executable-bounds
identified set, never a midpoint**; the trader's own stale-reference guard
applied; win probability from the **empirical** OT-skewed outcome distribution
(2017-2025), not a normal.

## Trade count

| stage | count |
|---|---|
| raw signals/season (crewshock 174, pacegap 352, move 350, final7 67) | **943** |
| tradeable — NO-side blocked, so the UNDER half of pacegap and move is refused | **592** |
| games with a candidate — one trade per game (`claimed[ev]`) | **496** |
| **after the price gates, as a taker** | **~306** |

The historical per-strategy counts are the right starting point and are nearly
the final answer for crewshock and final7 (gate pass 88.9% and 97.3%). They
diverge for pacegap and move for three reasons no sportsbook backtest can see:
one-strategy-per-game claiming, the NO-side block, and `MIN_EDGE` at the ask.

## Taker P&L at 1 contract

| strategy | trades | EV/contract | season EV | outlay | **ROI** |
|---|---|---|---|---|---|
| crewshock | 145 | +1.28¢ | +$1.86 | $67.93 | **+2.73%** |
| final7 | 52 | +3.25¢ | +$1.68 | $24.10 | **+6.97%** |
| move | 72 | +2.31¢ | +$1.65 | $35.31 | **+4.68%** |
| pacegap | 38 | +3.04¢ | +$1.16 | $18.70 | **+6.20%** |
| **TOTAL** | **306** | | **+$6.35** | **$146.04** | **+4.35%** |

**Taker is 32% of the maker figure.** ROI denominator is cost + fee, matching
the dashboard.

## Two corrections made while computing this

**1. The stale-reference guard was omitted in the first pass**, which
manufactured edge out of open-vs-close disagreement: pacegap showed +13.02% ROI
and a 44.5% gate pass. With the guard applied as `run()` applies it, pass fell
to 23.6% and the season total from $11.93 to $7.36. A +13% ROI on the weakest
strategy was the tell.

**2. The opener strategies were priced on the wrong book.** pacegap and move
settle vs the OPENER and fill at 09:00 ET; `pregame_*` is a late pregame
snapshot. Pricing an opener strategy against a near-close book selects on line
movement. Rebuilt from 1-minute candles at 09:00 ET, their EV/ct falls from
+4.55¢/+3.59¢ to **+3.04¢/+2.31¢** — the expected direction.

## Confidence is not uniform

- **crewshock, final7 — solid.** Right book (late pregame), 1,312 boards.
- **pacegap, move — provisional.** A 09:00 ET book exists for only **54 of 429**
  events, because candles emit on book change and these markets are often quiet
  before 09:00. **n = 39 tradeable boards.** Directionally right but
  underpowered. Realised 2025-26 outcomes on those trades were +9.38¢ and
  +28.66¢ per contract — far too noisy at that n to use for anything.

Collecting 09:00 ET books forward (`nba_xmarket_collect.py` already captures
`KXNBATOTAL` at 1-minute) is what would firm these two up.

Scripts: `taker_pnl_2026_27.py`, `taker_pnl_opener_phase.py`,
`expected_trade_count_2026_27.py`.
