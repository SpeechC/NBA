# NBA TRADING DATA INVENTORY (2026-09-13)

Deliverable for §2 of the trading mission. **Nothing was downloaded or rebuilt.**
Everything below already existed; the work was locating it and establishing what
is and is not executable.

## HEADLINE

> **`kalshi_nba_triangle.sqlite` holds 12,474,277 one-minute candles over a full
> NBA season (2025-10-10 .. 2026-06-13), of which 5,051,685 are KXNBATOTAL, and
> every one carries `yes_ask_close`.**

This was not known when this session began — the store that was being used
(`kalshi_nba_totals.sqlite`) has an **empty** `candles` table, which made it look
as though only two snapshots per market existed. It does not change what the
older analyses concluded, but it changes what is now testable: **Families #1, #2
and #3 are all runnable on executable prices at 1-minute resolution.**

---

## 1. KALSHI STORES

All under `/mnt/c/NBA2/Kalshi/data/`.

| store | size | events | markets | candles | interval | span |
|---|---|---|---|---|---|---|
| `kalshi_nba_triangle.sqlite` | 3.27 GB | 4,011 | 34,450 | **12,474,277** | **1 min** | 2025-10-10 .. 2026-06-13 |
| `kalshi_nba_candles.sqlite` | 322 MB | 429 | 4,719 | 1,256,843 | 1 min | 2025-10-21 .. 2025-12-22 |
| `kalshi_nba_totals.sqlite` | 33 MB | 1,324 | 14,787 | **0 (empty)** | — | 2025-10-21 .. 2026-06-13 |

`kalshi_nba_candles.sqlite` is a strict subset of the triangle store's
KXNBATOTAL coverage. **Use the triangle store.**

### Series inside the triangle store

| series | markets | span |
|---|---|---|
| KXNBASPREAD | 16,937 | 2025-10-21 .. 2026-06-13 |
| **KXNBATOTAL** | **14,787** | 2025-10-21 .. 2026-06-13 |
| KXNBAGAME | 2,726 | 2025-10-10 .. 2026-06-13 |

KXNBATOTAL: **1,324 events, 5,051,685 candles, `yes_ask_close` non-null on
100.00%**, 1,381,814 bars with volume > 0.

### §2 classification — which periods contain what

| content | availability |
|---|---|
| full order books (all levels) | **NONE, anywhere** |
| best bid AND ask | **YES — every 1-min bar, 2025-10-21 .. 2026-06-13** |
| displayed size / depth at best | **NONE** (see Limitation L1) |
| trades only | `volume` per bar; no trade prints, no signed flow |
| 60-minute candles | none — the store is 1-minute throughout |
| high-frequency live snapshots (sub-minute) | **NONE** (see L2) |

There is no hourly-candle period and no book period. **The entire Kalshi history
is one regime: 1-minute OHLC of bid and ask, one season.**

---

## 2. THE TWO USABLE VIEWS

**(a) Time series — triangle store.** 1-minute `yes_bid_*` / `yes_ask_*` OHLC per
rung. Bars run from market close backwards, so they cover the **live game as well
as pregame**; `end_period_ts <= tipoff_ts` is the pregame filter and is
mandatory.

**(b) One near-tip ladder per game — totals store.** `pregame_yes_bid/ask`, at
**T−1 min** (p10 1, p90 6 min before tip), two-sided on **97.9%** of 14,787
markets, median spread **2¢**, `result` populated on 100%.

**The totals store's `close_*` snapshot is unusable** — two-sided on 0.1%, median
spread 100¢. It is taken after settlement. Do not treat it as a closing price.

### Synchronized-ladder feasibility (the number that decides Family #1)

Pregame only, both sides quoted, 1¢ ≤ price ≤ 99¢:

```
events 1,317          pregame snapshots 640,559
two-sided rungs/snapshot   p10 1   p25 2   p50 4   p75 8   p90 11
median ladder spread       p10 1c  p25 1.5c p50 2c  p75 3c  p90 5c
```

| §6 primary screen | snapshots | share | events |
|---|---|---|---|
| ≥7 two-sided rungs | 198,447 | 30.98% | 1,303 |
| median spread ≤ 4¢ | 564,051 | 88.06% | 1,317 |
| **BOTH** | **172,105** | **26.87%** | **1,240** |

Distribution across time-to-tip (qualifying only):

```
T-0 to T-60m   35,566   (1,206 events)
T-1h to T-3h   45,100   (1,193 events)
T-3h to T-6h   48,504   (1,164 events)
beyond T-6h    42,935   (1,091 events)
```

**Family #1 is runnable with a large, well-distributed sample.** The binding
constraint is the rung count, not the spread: the median snapshot quotes only 4
rungs two-sided, so ~70% of minutes are discarded by the ≥7 requirement.

---

## 3. BASKETBALL STORES

| source | content | span |
|---|---|---|
| `/mnt/c/NBA2/dfMaster_OT_2017-2026.csv` | game results, box, open/close totals + spreads, officials | 2017-10 .. 2026-06 |
| `~/data/pbp_lineups_all.parquet` (452 MB) | possession/lineup PBP | 2017-18 .. 2024-25 |
| `/mnt/c/NBA2/out/pbp_lineups_*.parquet` | per-season PBP | 2017-18 .. 2024-25 |
| `~/data/pbp_transition_store.csv` | transition shares, 18,330 team-games | 2017-10-17 .. **2025-04-13** |
| `~/data/team_game_ratings.parquet`, `rapm_features`, `stints_all`, `streaks`, `spread_movement`, `player_game_pts` | derived states | 2017-18 .. 2024-25 |
| `~/data/injury_reports/` | injury panel | through 2026-08 |

**The Kalshi window joins cleanly to dfMaster**: 1,316 games dated 2025-10-21 ..
2026-06-13, with `OPENING TOTAL_H`, `CLOSING TOTAL_H` and `OPENING SPREAD_H`
non-null on **100%**. Against 1,324 Kalshi events this is an essentially complete
overlap.

---

## 4. LIMITATIONS — these bound what may be claimed

**L1 — No depth, anywhere.** Candles carry `volume` and `open_interest` but no
displayed size at the best bid/ask. Therefore §5's 1 / 5 / 10 / 25%-of-depth
reporting and §7's "capacity = min displayed size across legs" **cannot be
computed from history**. Any size claim must come from forward collection.
Historical results are per-contract edge only, and must be labelled
`CAPACITY_UNKNOWN`.

**L2 — 1-minute is the floor.** No sub-minute data exists. Family #3 can measure
incorporation at 1-minute granularity and no finer. Per §8, a 5-second latency
claim cannot be made from this store; it requires the forward collector.

**L3 — One season of Kalshi.** 2025-10-21 .. 2026-06-13. Chronological
partitioning (§18) therefore splits *within* one season, and no cross-season
out-of-sample exists. Basketball history back to 2017 may be used for PIT state
construction but **carries no Kalshi price**, so it can never establish
executable profitability.

**L4 — PBP does not reach the Kalshi season.** The transition store and lineup
parquets end **2025-04-13**. Every PBP-derived state for a 2025-26 game would
have to be built from prior seasons, or PBP re-fetched from the CDN. §16's
mechanism work is therefore available for *explaining* an error, but PBP-derived
*pregame states* for the Kalshi window do not currently exist.

**L5 — Candle prices are CENTS.** `yes_bid_close = 75.0` means 75¢. The live API
returns `*_dollars` strings ("0.7500"). Mixing the two is a silent 100×.

**L6 — `tipoff_ts` is NULL in the triangle store.** It is populated in
`kalshi_nba_totals.sqlite` (99.5%, source `schedule`) and must be joined in.
Without it, pregame cannot be separated from in-game.

**L7 — OHLC is not a tick.** `*_close` is the quote at the end of the minute.
Two rungs' `*_close` at the same `end_period_ts` are contemporaneous and may be
treated as simultaneously executable. `*_high`/`*_low` within a bar are **not**
simultaneous across rungs and must not be used to construct a spread or an arb.

---

## 5. EXECUTABILITY RULING (§4)

Per §4, entry is `YES ask` / `NO ask`, never mid, last, or bid.

- `yes_ask_close` is a **contemporaneous executable ask** at a known timestamp.
  Buying YES at it is executable.
- Buying NO at strike K consumes the YES **bid** book: `NO ask = 100 − yes_bid`.
  This is the mirrored side and is systematically thinner — a correction already
  on record from the weather work, and unverifiable here because of L1.
- Therefore historical results are labelled **`EXECUTABLE_PRICE / CAPACITY_UNKNOWN`**,
  not simply "executable". A rule that clears the price test still needs forward
  size verification before capital.

§4 also says a candidate found in candle data "must not be labeled historically
executable." The 1-minute bar is the boundary case the clause is aimed at: it is
far stronger than an hourly candle close, but it is still a bar, and a quote
present at minute-end need not have survived the seconds after. **Ruling adopted
here:** 1-minute bar results are reported as `EXECUTABLE_PRICE / CAPACITY_UNKNOWN`
and are sufficient to *advance a candidate to forward shadow*, and not sufficient
to authorise capital on their own.

---

## 6. WHAT IS RUNNABLE NOW

| family | runnable | on what |
|---|---|---|
| #1 stale rung (leave-one-out) | **YES** | 172,105 qualifying pregame snapshots, 1,240 events |
| #2 executable ladder arbitrage | **YES** | every snapshot, exhaustive pairs |
| #3 stale rung after center move | **PARTIAL** | 1-min granularity only (L2) |
| #4 sigma calibration | **YES** | T−1min ladder + settlement, 1,316 games |
| #5 overtime / close-game tail | **YES** | + `OPENING SPREAD_H` (100% coverage) |
| #6 3PA dispersion | **YES** | PIT states from 2017-2025 box data |
| #7 pace dispersion | **YES** | as above |
| #8 intentional-foul tail | **YES** | as above |
| #9 large-spread dispersion | **YES** | as above |
| #10 center forecast failures | deferred | per §15, only after 1-9 |
| §16 PBP mechanism | **BLOCKED** for 2025-26 | L4 |

## 7. CODE ALREADY PRESENT — do not rewrite

```
/mnt/c/NBA2/Kalshi/download_nba_totals.py     the fetcher (34 KB)
/mnt/c/NBA2/Kalshi/ladder_to_distribution.py  ladder -> (mu, sigma)
/mnt/c/NBA2/Kalshi/pregame_snapshot.py        pregame enrichment
/mnt/c/NBA2/Kalshi/storage.py                 schema + upsert
/mnt/c/NBA2/Kalshi/qa_report.py               QA
/mnt/d/Kalshi/kalshi_client.py                signed GET client
nba_kalshi.py                                 live market layer (this repo)
```

`/mnt/c/NBA2/KalshiCandle/` is a near-duplicate of `/mnt/c/NBA2/Kalshi/` with a
different `pregame_snapshot.py` (39 KB vs 30 KB). Treat `/mnt/c/NBA2/Kalshi/` as
authoritative; the manifest there warns not to point the fetcher at
`kalshi_nba_totals.sqlite` because a market refresh NULLs the enrichment columns.
