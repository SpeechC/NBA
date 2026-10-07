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
