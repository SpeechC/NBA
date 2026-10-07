# NBA trader — where things stand, 2026-10-07

## Right now

| | |
|---|---|
| **Cron** | **DISARMED.** `early` and `late` no longer carry `--arm`. Only `cancel --arm` (pulls orders) and `dashboard` remain armed. Backup at `/tmp/cron.bak`. |
| **Season gate** | Live orders **refused before 2026-10-20** in both `run()` and `verify_no_side()`. Dry runs unaffected. |
| **Open position** | 1 NO contract, `KXNBATOTAL-26OCT07GSWPOR-213`, $0.44. Settles tonight. |
| **Resting orders** | 0 |
| **Funds** | shard 0 $35.05, **shard 3 (NBA) $4.54** |
| **Preflight** | 1 FAILING: BigDataBall feed (needs the Dropbox folder) |

## Live orders placed today — 3, which was 2 too many

| # | what | outcome |
|---|---|---|
| 1 | NO probe, `GSWPOR-213` @ 0.44 | **filled** — this is the one that verified the schema |
| 2 | NO probe, `MILOKC-219` | rested unfilled, **cancelled** |
| 3 | NO probe, `MILOKC-219` | rested unfilled, **cancelled** |

Orders 2 and 3 were placed by running `--verify-no-side --arm` *to test whether
a gate worked* — on preseason boards, after being told not to trade. The gate
had silently failed to apply because the patch anchor did not match and the
script printed success without asserting. **A gate must be verified by reading
the file, never by firing an order to see what happens.**

## What the live orders bought us — four infrastructure bugs

Each would have broken the season silently.

1. **Kalshi shards its exchange and funds do not cross.** NBA is
   `exchange_index 3`; our money was all on 0. Every NBA order would have
   returned `404 insufficient_shard_balance` all season.
2. **Orders were not shard-routed.** `_order()` never sent `exchange_index`,
   which defaults to 0. Now `-1` (auto-route by ticker).
3. **Portfolio reads are shard-scoped.** After a confirmed fill, shard 0 showed
   **zero** NBA fills and positions. The dashboard would have shown an empty
   book all season.
4. **`cancel()` used a dead V1 endpoint** returning `410
   deprecated_v1_order_endpoint`. `cancel_stale()` could never cancel anything,
   and had been logging "0/0 of our resting orders cancelled" twice an hour —
   indistinguishable from "nothing to do". NBA totals trade **in-play**, so an
   uncancelled resting order is a free option. Now `DELETE
   /portfolio/events/orders/{id}`.

**NO side is verified**: `outcome_side "no"`, `no_price_dollars 0.4400` at our
0.44 limit, `is_taker true`. `side='ask'` buys NO. UNDER is enabled.

## What changed in the trade path this session

| change | why |
|---|---|
| **Taker is the default** | we are not approved for market making; `--make --arm` is refused outright |
| **No midpoint anywhere** | `fit_ladder()` is bounds-only; the old mid version is `fit_ladder_mid()`, DO NOT USE |
| **final7 window `<=` not `<`** | the trader bet 451 games where the validated rule bets 527, a 14.4% shortfall |
| **Season gate** | strategies are validated on regular-season games only |
| **Shard routing + shard-scoped reads + V2 cancel** | above |
| **Rung-choice sidecar** | logs all three rung rules per signal, reporting only |

## What the numbers say

| | |
|---|---|
| 2025-26 taker, live config | **−$4.72 on 306 trades, ROI −3.22%** |
| same games, sportsbook −110 | −3.18% — **the venue is neutral** |
| the old $19.70 projection | **withdrawn** — it was a maker figure at bid+1¢ |
| 2017-2024 at the book | crewshock +6.39%, final7 +9.21%, move +1.83% — but this **drops the worst season because it was worst** |

2025-26 by strategy at the book: crewshock **−3.74%**, final7 +5.14%,
move +2.89%, pacegap +3.23%. Both two-sided strategies made their money on the
**UNDER** leg (OVER-only: move −1.33%, pacegap −2.25%).

## Open decisions

1. **Should the season be traded at all?** At 1 contract the expected edge
   (~$6) is smaller than its noise (±$10), and as a taker at the ask a logged
   simulation is faithful. Shadow mode gives the same information at zero risk.
2. **Shard funding** if it is traded: `MAX_NOTIONAL_DAY` is $30, shard 3 has
   $4.54.
3. **Rung selection** — max-edge is unproven; the sidecar settles it out of
   sample.

## Not yet done

- BigDataBall feed directory does not exist.
- `NBA_LAST_REGULAR=2027-04-11` must be the last **regular-season** date, never
  the play-in end.
- 12 commits unpushed; `injury_status_panel.csv` (108 MB) blocks the push.
