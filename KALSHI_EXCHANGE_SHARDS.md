# Kalshi shards its exchange, and NBA is not on our shard (2026-10-07)

Found by arming the 1-contract NO probe. It returned:

```
http=404  {"error": {"code": "insufficient_shard_balance",
           "message": "insufficient shard balance",
           "details": "Exchange user not found. For Predictions: reference
                       documentation Exchange Sharding documentation."}}
```

**This is an account-routing error, not a verdict on the NO schema.** The first
version of `verify_no_side()` reported it as *"FAIL — side='ask' is not the NO
schema; do NOT arm UNDER"*, which was flatly wrong and is now fixed.

## What is actually going on

`/portfolio/balance` returns a `balance_breakdown` per shard, and
`/exchange/status` names them:

| exchange_index | description | our balance |
|---|---|---|
| 0 | Default | **$40.05** |
| 1 | Combos | $0.00 |
| 2 | Crypto & Commodities | $0.00 |
| 3 | **Tennis, Baseball, Basketball** | **$0.00** |

And every NBA series reports `exchange_index = 3`:

```
KXNBATOTAL            exchange_index = 3
KXNBAGAME             exchange_index = 3
KXEARNINGSMENTIONPEP  exchange_index = 0     <- where this account has traded
```

**Funds do not cross shards.** The account's entire balance is on shard 0,
where the mention markets live and where every proven order has been placed.
NBA is on shard 3 with **$0.00**.

## Why this was about to matter a great deal

The cron is armed (`early --arm` 09:00, `late --arm` 17:00). With $0 on shard 3,
**every NBA order would have returned 404 all season** — and each rejection
would have printed as a bad order rather than a funding problem. Opening night
is 2026-10-20. This was 13 days from being discovered the hard way.

It also means **nothing about the order path has ever been exercised for NBA**,
which is consistent with the account showing 0 NBA fills ever. The YES path is
proven on shard 0 only.

## Fixes

1. **`nba_kalshi.shard_balance()`** — `{exchange_index: dollars}`.
2. **`nba_kalshi.series_shard()`** — reads `exchange_index` from an open event
   rather than hardcoding 3, which is a property of the venue and can change.
3. **`verify_no_side()`** now checks shard funding *before* spending, aborts with
   the right diagnosis, and no longer reports a shard error as a schema failure.
4. **Preflight gained "NBA shard funded"**, which now reads:

```
NBA shard funded   FAIL  $0.00 on exchange_index 3 (0=$40.05, 1=$0.00,
                         2=$0.00, 3=$0.00) -- TRANSFER FUNDS TO SHARD 3;
                         every NBA order will 404 until then
```

Preflight is now **3 FAILING**: BigDataBall feed, NBA shard funded, NO-side
verified.

## Status of the NO side

**Still unverified, and not because of the schema.** The probe could not reach
the exchange. `side='ask'` remains untested against a real NBA order. Intra-
exchange transfers are active on all four shards (`/exchange/status` reports
`intra_exchange_transfers_active: true`), so the fix is a funds transfer to
shard 3 — a money movement, which is not something to do unasked.

Once shard 3 is funded, `nba_live_trader.py --verify-no-side --arm` buys 1
contract at ~$0.45 and settles the schema question in one call.


---

# How to transfer funds between shards (2026-10-07)

Found via `docs.kalshi.com/getting_started/exchange_sharding` — the page the
error message was pointing at.

## The endpoint

```
POST /portfolio/intra_exchange_instance_transfer
{
  "source": "event_contract",          # exchange INSTANCE, not the shard
  "destination": "event_contract",
  "amount": 100000,                    # *** CENTICENTS ***  $10 = 100,000
  "source_exchange_shard": 0,
  "destination_exchange_shard": 3,
  "source_subaccount": 0,
  "destination_subaccount": 0
}
```

Returns `transfer_id` on HTTP 200. Two traps in that body:

- **`amount` is in centicents**, not cents and not dollars. $1 = 10,000. Off by
  a factor of 100 either way is the obvious failure, so `transfer_shard()` takes
  **dollars**, converts, and prints the computed body before sending.
- **`source`/`destination` are the exchange *instance*** (`event_contract` or
  `margined`), which is a *different axis* from the shard index. A shard-to-shard
  move inside event contracts keeps both as `event_contract` and varies only
  `*_exchange_shard`.

## A second bug this uncovered — our orders were not shard-routed

The same doc: *"If `exchange_index` is `-1`, auto-routes using the required
`market_ticker`"*, and omitting it **defaults to shard 0**. Our `_order()` never
sent `exchange_index` at all, so NBA orders were being addressed to the wrong
shard independently of the funding problem. `exchange_index: -1` is now in the
order body.

Routing alone would not have been enough: *"Programmatic traders must
preallocate collateral on a given exchange shard before order placement"* —
collateral checks run inside each matching engine. Both fixes are required.

## The command

```bash
cd /mnt/d/Kalshi/nba
/home/dpope/nba_env/bin/python nba_live_trader.py --fund-shard 10          # dry run
/home/dpope/nba_env/bin/python nba_live_trader.py --fund-shard 10 --arm    # sends it
```

It reads the target `exchange_index` from a live NBA event rather than
hardcoding 3, refuses if shard 0 cannot cover the amount, prints the exact body,
and is **dry by default**. Dry-run output:

```
balance by shard: 0=$40.05, 1=$0.00, 2=$0.00, 3=$0.00
KXNBATOTAL trades on exchange_index 3
transfer $10.00 = 100,000 centicents  shard 0 -> 3
```

## How much

The trade path needs enough on shard 3 to cover a day, not a season — positions
settle and return collateral. `MAX_NOTIONAL_DAY` is **$30**, and ~306 trades a
season at ~$0.48 is ~$147 of cumulative turnover. **$10–15 funds the
1-contract test comfortably**; the whole account is $40.05.

Transfers are reversible — the same call with source and destination swapped
moves it back.

---

# NO SIDE VERIFIED (2026-10-07)

Transfer sent ($5.00, shard 0 → 3, `transfer_id 9f370172-024f-41b2-a0b9-11b477e261aa`,
HTTP 200). **The transfer is asynchronous** — a balance read immediately after
still showed `3=$0.00`; it appeared within a few seconds. Do not read that as a
failed transfer.

Probe: `KXNBATOTAL-26OCT07GSWPOR-213`, 1 contract NO at 0.44, HTTP **201**,
`fill_count 1.00`.

## The order response is YES-denominated — do not misread it

```json
{"average_fill_price": "0.5600", "average_fee_paid": "0.0173", "fill_count": "1.00"}
```

0.5600 is the **YES** price. We sent a NO limit of 0.44 and 0.44 + 0.56 = 1.00,
so this is a reporting convention, not the wrong side. The fill record proves it:

```json
{"outcome_side": "no", "side": "no", "action": "sell", "book_side": "ask",
 "no_price_dollars": "0.4400", "yes_price_dollars": "0.5600",
 "is_taker": true, "fee_cost": "0.017300"}
```

Position: `position_fp "-1.00"`, `market_exposure_dollars "0.440000"`.

**Three things established at once:**

1. **`side='ask'` buys NO**, at the NO price, at our exact limit. The one
   unproven call in the stack is now proven against the real exchange.
2. **`is_taker: true`** — it crossed. The taker default (`2a86820`) works end
   to end against a live book.
3. The NO quote derivation is right: NO ask 0.44 = 1 − YES bid 0.56.

## A third shard trap: PORTFOLIO READS ARE SHARD-SCOPED

After a confirmed NBA fill, `exchange_index=0` returned **zero** NBA fills and
**zero** NBA positions. Only `exchange_index=3` showed them.

Without this, all season:
- the dashboard would have reported an **empty NBA book** — it reads fills and
  settlements;
- **`cancel_stale()` would never have found an NBA order to pull**, which
  matters because NBA totals trade **in-play** and an uncancelled resting bid is
  a free option sold to whoever is watching the game.

Note `-1` auto-routes **orders** but is **rejected on reads**
(`ExchangeIndex failed on the 'gte' tag`), so reads need a concrete index.

Fixed: `NBAKalshi.shard()` resolves the index once from a live event (falling
back to `NBA_EXCHANGE_INDEX`, default 3) and `positions()`, `fills()`,
`settlements()` and `resting_orders()` all pass it. Verified: 1 fill, 1
position, 0 resting orders, all on shard 3.

## Status

`NBA_NO_SIDE_VERIFIED=1` is now set in `run_nba_trader.sh`, so **UNDER is
enabled**. Preflight is down to **1 FAILING** — the BigDataBall feed, which
needs the Dropbox folder to exist.

Open position: **1 NO contract of `KXNBATOTAL-26OCT07GSWPOR-213` at $0.44**,
left to settle tonight. Shard 3 holds $4.54 after the probe and its fee.

**Sizing note:** `MAX_NOTIONAL_DAY` is **$30** and shard 3 has $4.54. That caps
a live day well below the configured limit — fund shard 3 further before running
a real slate, or lower the cap deliberately.
