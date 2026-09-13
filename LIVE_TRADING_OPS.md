# Live trading — operating runbook, 2026-27

Governing amendment: **`AMENDMENT_live_trading.md`**. Read it first; it records
what deploying capital costs the prospective test.

```
nba_daily.py          signals   ->  logs            (places no orders)
nba_live_trader.py    logs      ->  Kalshi orders   (computes no signals)
nba_dashboard.py      account   ->  HTML -> S3
```

## WHERE THE FILES LIVE

| | path |
|---|---|
| signal producers, logs, `team_mapping.csv` | `/home/dpope/projects/nba_entropy_replication` |
| execution stack (copy) | `D:\Kalshi\nba` = `/mnt/d/Kalshi/nba` |
| Kalshi credentials | `/mnt/d/Kalshi` (`KALSHI_CLIENT_DIR`) |

**The execution copy reads signals from the project, not from its own
directory.** `nba_live_trader.PROJECT_DIR` resolves every relative source path
and defaults to the project; override with `NBA_PROJECT_DIR`. This matters
because cron sets no useful cwd, and **an unresolvable source file reads as "no
signals today"** — indistinguishable from a quiet slate, and it would never
raise. Verified running from `D:\Kalshi\nba` with cwd `/tmp`: auth OK, all three
sources resolved, `team_mapping.csv` found.

Keeping one copy of `team_mapping.csv` (in the project) is deliberate — a second
copy beside the trader would drift from the one the signal producers use, and
a silent abbreviation mismatch is how a game stops matching its Kalshi event.

**Two copies of the code now exist.** Edit one and the other is stale. Either
re-copy after every change, or point cron at a single copy and treat the other
as a backup. The crontab below uses `$NBA`; set it to whichever is authoritative.

## THE THREE STRATEGIES DO NOT SHARE A CLOCK

This is the single thing most likely to be "simplified" by a future edit, and it
would silently convert two backtested strategies into untested ones.

| strategy | settles vs | must fill | direction | why |
|---|---|---|---|---|
| **PaceGap** | opener | **early** | OVER/UNDER | edge is against the opener's error |
| **MOVE_COMBINED** | opener | **early** | OVER/UNDER | forecasts open→close; once the market moves, the edge is spent |
| **CrewShock** | close | **late** | OVER only | graded at the close, so a late fill is the faithful one |

A Kalshi ladder's implied mu **is** the closing total (established in
`LADDER_ASSUMPTION.md` / `MARKET_EMULATOR.md`). Filling MOVE_COMBINED near tip
therefore captures none of its edge by construction.

## TWO THINGS THAT WILL LOOK LIKE BUGS AND ARE NOT

**"Only one strategy traded a game I had three signals on."** By design. One
position per game across all three; the highest published edge claims it
(CrewShock 1.925 pts > MOVE 1.573 > PaceGap 1.184). The three are correlated —
PaceGap and MOVE both key off the opener — and no backtest measured their sum.

**"PaceGap/MOVE declined almost everything today."** Check the drift column. If
the market has moved against the signal by more than that strategy's whole edge,
the opener is stale and the trade is declined. **A late run will decline most of
its slate**, which is correct but silent, and is the main way a mistimed cron
entry hides itself. If the decline rate is high, check the clock before checking
the model.

## DAILY SEQUENCE

Times are ET. Phases 1–4 are `nba_daily.py` and are unchanged.

| # | when | command |
|---|---|---|
| 1 | as early as openers exist | `nba_daily.py capture $(date +%F)` |
| **T1** | **right after phase 1** | `nba_live_trader.py --date $(date +%F) --strategy pacegap --arm` |
| **T2** | **right after phase 1** | `nba_live_trader.py --date $(date +%F) --strategy move --arm` |
| 2 | after 9:30am | `nba_daily.py assignments $(date +%F)` |
| 3 | pregame | `nba_daily.py ladders $(date +%F)` |
| **T3** | **~2h before first tip** | `nba_live_trader.py --date $(date +%F) --strategy crewshock --arm` |
| **T4** | **every 30 min, 5pm–1am** | `nba_live_trader.py --cancel --arm` |
| **D** | **every 30 min** | `nba_dashboard.py --build --publish` |
| 4 | next morning, after BigDataBall | `nba_daily.py settle $(date -d yesterday +%F)` |

**T4 is not housekeeping.** NBA totals trade in-play; an uncancelled pregame bid
is a free option sold to whoever is watching the game. It runs on its own
entry so that a crash in T1–T3 does not take the cancels with it.

## CRONTAB

```cron
NBA=/home/dpope/projects/nba_entropy_replication
PY=/home/dpope/nba_env/bin/python
NBA_S3_BUCKET=CHANGE-ME
# NBA_NO_SIDE_VERIFIED=1     # uncomment ONLY after --verify-no-side prints PASS

# --- signals (no orders) ---
30 13 * * *  cd $NBA && $PY nba_daily.py capture     $(date +\%F)      >> ~/logs/nba.log 2>&1
45 14 * * *  cd $NBA && $PY nba_daily.py assignments $(date +\%F)      >> ~/logs/nba.log 2>&1
00 22 * * *  cd $NBA && $PY nba_daily.py ladders     $(date +\%F)      >> ~/logs/nba.log 2>&1
30 14 * * *  cd $NBA && $PY nba_daily.py settle $(date -d yesterday +\%F) >> ~/logs/nba.log 2>&1

# --- execution: EARLY pair, right after the openers land ---
40 13 * * *  cd $NBA && $PY nba_live_trader.py --strategy pacegap --arm >> ~/logs/nba_trade.log 2>&1
42 13 * * *  cd $NBA && $PY nba_live_trader.py --strategy move    --arm >> ~/logs/nba_trade.log 2>&1

# --- execution: LATE, ~2h before a 7pm ET tip ---
00 22 * * *  cd $NBA && $PY nba_live_trader.py --strategy crewshock --arm >> ~/logs/nba_trade.log 2>&1

# --- cancels: its own entry, on purpose ---
*/30 21-23,0-5 * * * cd $NBA && $PY nba_live_trader.py --cancel --arm  >> ~/logs/nba_trade.log 2>&1

# --- dashboard ---
*/30 * * * * cd $NBA && $PY nba_dashboard.py --build --publish          >> ~/logs/nba_dash.log 2>&1
```

Cron runs in **UTC** on this host; the hours above are set for ET during
standard time. **Re-check them at the 2027-03-08 DST change** — a one-hour slip
moves MOVE_COMBINED's fill window past the opener and quietly voids its edge.

Drop `--arm` from every execution line for a dry run. `%` must be escaped in
crontab; that is why `\%F` appears above.

## BEFORE OPENING NIGHT — in this order

```bash
/home/dpope/nba_env/bin/python crewshock_live.py validate
```
Must print `OVERALL: PASS`. If not, stop — the port has drifted.

```bash
/home/dpope/nba_env/bin/python nba_live_trader.py --date 2026-10-20
```
Dry run, no `--arm`. Prints the ladder inversion, mu_hat, drift and the rung it
would take for every signal. Nothing is sent.

```bash
/home/dpope/nba_env/bin/python nba_live_trader.py --verify-no-side
```
Buys **one** contract on the NO side. Until it prints PASS, every UNDER is
refused and PaceGap/MOVE_COMBINED trade their OVER signals only; CrewShock is
OVER-only and unaffected.

**Kalshi's demo needs its own API key** — production credentials return 401
there, which looks like a schema failure and is not. If there is no demo key,
run it against production instead:

```bash
/home/dpope/nba_env/bin/python nba_live_trader.py --verify-no-side --arm
```

One contract at a mid-book price, ~$1 at risk, and it proves the exact path the
trader will use rather than a sandbox approximation. It reports the resulting
position so it can be closed. Then set `NBA_NO_SIDE_VERIFIED=1` in the crontab.

```bash
/home/dpope/nba_env/bin/python nba_dashboard.py --build --publish
```
Confirms S3 credentials and the bucket before there is anything to lose.

## THE BIGDATABALL INPUT — the one missing dependency

CrewShock needs season-to-date officiating history. `crewshock_live.py` reads:

```
HIST     /mnt/c/NBA2/dfMaster_OT_2017-2026.csv   frozen, DO NOT MODIFY
CURRENT  /mnt/c/NBA2/dfMaster_2027.csv           BigDataBall season-to-date  <- NOT YET PRESENT
```

`dfMaster_2027.csv` must match the historical schema and carry at least:

| column | why |
|---|---|
| `GAME-ID`, `DATE` | join key and the prior-only cutoff |
| `OFFICIAL 1/2/3` | crew identity — the signal itself |
| `TEAM`, `OPPONENT`, `VENUE` | side and home/road |
| `F` (personal fouls) | the estimated quantity |
| `OPENING TOTAL`, `CLOSING TOTAL`, `TOTAL` | reference lines and settlement |
| `DATASET_H` or `BIGDATABALL\nDATASET_H` | season label |

**Update it daily, before phase 4.** Stale history is a hard stop, not a
warning: `_mean()` skips NaN, so a day-old file does not error — the crew state
silently freezes and CrewShock drifts with nothing visible in the output.

**Name spellings are the known failure.** `official.nba.com` writes `JT Orr`;
BigDataBall writes `J.T. Orr`. Unmatched, that zeroes an official's entire
history and biases CrewShock toward zero. Those games are flagged `DATA_GAP` and
never actioned. If gaps repeat, a new official has entered the league or a
spelling changed — reconcile before trusting any score involving that crew.

## HARD STOPS

1. `crewshock_live.py validate` does not print PASS.
2. `dfMaster_2027.csv` not updated since the last slate.
3. Zero assignment rows — the API returns `rows: []` for a bad date format as
   readily as for an empty slate. The date must be `YYYY-MM-DD`.
4. `DATA_GAP` rows — flagged, never actioned.
5. **Maker share below ~80%** on the dashboard. The entire economic case is that
   we rest rather than cross; at the median 2¢ book that is a 2¢/contract swing,
   larger than PaceGap's whole edge.
6. **Unattributed settlements** on the dashboard — a ticker settled that is in
   neither the order log nor a tagged fill. Reconcile before trusting the
   per-strategy table.

## KILL SWITCH

```bash
touch ~/data/NBA_TRADING_HALT
```

Every placement run exits immediately while that file exists. It does **not**
cancel what is already resting — run `--cancel --arm` for that, and it is the
right second command after halting.

## S3

```bash
export NBA_S3_BUCKET=your-bucket
export NBA_S3_KEY=nba/index.html
```

The page carries position sizes and account balance. `publish()` sets **no ACL**
and none should be added. If it needs browser access, front it with CloudFront +
OAC or a presigned URL — do not make the object public to fix a 403.

## WHAT THE DASHBOARD DELIBERATELY DOES NOT SHOW

`PREREG_2026_27_PROSPECTIVE` D3 still binds the research evaluation: no hit rate
by threshold, no alternative thresholds, no Over/Under split, no team or month
breakdown. The dashboard shows Kalshi trading results — a different settlement
basis, different prices, capacity-constrained fills — and cannot produce the
April read. `evaluate_season.py` still refuses to run before 2027-04-15.
