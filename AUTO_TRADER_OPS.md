# Automatic trader — setup and schedule (2026-09-23)

Code: `D:\Kalshi\nba`. Governing: `AMENDMENT_live_trading.md`,
`LIVE_TRADING_OPS.md`, `PREREG_2026_27_PROSPECTIVE.md`.

`PROJECT_CLOSED.md` closed the NBA totals **research** on 2026-09-14. It
explicitly did **not** cancel the frozen 2026-27 prospective evaluation, which
is what these three strategies are. This trader implements that evaluation with
capital.

---

## THE SCHEDULE — and why 09:00 ET is two entries, not one

| entry | when | what |
|---|---|---|
| **early** | **09:00 ET** | BDB feed refresh, capture openers, PaceGap + MOVE_COMBINED orders |
| **late** | **17:00 ET** | BDB feed (strict), referee assignments, CrewShock orders |
| **cancel** | every 30 min, 19:00–01:00 ET | pull resting orders on games near tip |
| **dashboard** | every 30 min | build + publish `s3://kalshi-strat/nba.html` |

**09:00 ET is correct for two of the three and wrong for the third**, for two
independent reasons:

- PaceGap and MOVE_COMBINED settle against the **opener** → fill early. 09:00 is right.
- CrewShock settles against the **close** → fill late. At 09:00 the close does not exist.
- Separately: **referee assignments do not exist at 09:00 ET.** `official.nba.com`
  publishes around or after 9am. A 09:00 CrewShock run scores an **empty slate**
  and logs nothing — it does not error, it silently does nothing.

`--force-crewshock` will run it at 09:00 anyway. The open→close move is roughly
unbiased (mean −0.032 pts) but carries sd 3.175 pts against a 1.925-pt edge, so
it adds noise for nothing. Not recommended.

## CRONTAB

**`CRON_TZ` is mandatory.** The season spans both DST directions (EDT in
Oct–Nov and Mar–Apr, EST in between). A fixed UTC entry silently drifts an hour
at each boundary, which moves the early run off the opener and voids
MOVE_COMBINED's edge by construction.

```cron
CRON_TZ=America/New_York
NBA=/mnt/d/Kalshi/nba
PY=/home/dpope/nba_env/bin/python
NBA_S3_BUCKET=kalshi-strat
NBA_S3_KEY=nba.html
# NBA_NO_SIDE_VERIFIED=1        # uncomment ONLY after --verify-no-side prints PASS
# ODDS_API_KEY=...              # required for PaceGap + MOVE_COMBINED

00 09 * * *  cd $NBA && $PY nba_auto_trader.py early --arm  >> ~/logs/nba_auto.log 2>&1
00 17 * * *  cd $NBA && $PY nba_auto_trader.py late  --arm  >> ~/logs/nba_auto.log 2>&1
*/30 19-23,0-1 * * * cd $NBA && $PY nba_auto_trader.py cancel --arm >> ~/logs/nba_auto.log 2>&1
*/30 * * * * cd $NBA && $PY nba_auto_trader.py dashboard    >> ~/logs/nba_dash.log 2>&1
```

Drop `--arm` from every line for a dry run. **Not installed** — install it
yourself when the preflight passes.

## MANUAL START — opening day

```bash
cd /mnt/d/Kalshi/nba
./run_nba_trader.sh preflight          # 1. everything green? trades nothing
./nba_bdb_feed.py --probe              # 2. feed column spellings, writes nothing
./run_nba_trader.sh early              # 3. DRY RUN of the 09:00 phase
./run_nba_trader.sh early --arm        # 4. for real
./run_nba_trader.sh late --arm         # 5. ~2h before first tip: CrewShock
```

Cron already runs 3–5 automatically; these are for the first day, when you want
to watch each step. `--date YYYY-MM-DD` targets another day.

**`--date` in the future is guarded.** `capture_openers` writes the IMMUTABLE
prospective row and refuses duplicates, so a row written for a future date
permanently blocks the real capture that day. More than 1 day ahead, the
immutable write is skipped and everything else still runs. A rehearsal on a
28-days-out slate wrote 9 such rows and had to be unwound by hand — hence the
guard.

## PRIOR-SEASON CREW STATS — already covered, no action

CrewShock's officials history comes from the frozen
`dfMaster_OT_2017-2026.csv`, which holds **all three officials for every season
through 2025-26** — including 2024-25 (1,166 games). The columns change name
partway through and `load_history()` reads both eras:

```
2017-18 .. 2021-22   MAIN REF_R / CREW_R / CREW_H
2022-23 .. 2025-26   CREW CHIEF_R / REFEREE&UMPIRE_R / REFEREE&UMPIRE_H
```

**`24-25-nba-team/06-22-2025-nba-season-team-feed.xlsx` is therefore not
needed.** 1,315 of its 1,321 games are already in the frozen file (the other 6
are playoffs, which `load_history()` filters out as non-Regular-Season), and the
referee names agree **100%** on all 1,315 after `_norm_ref`. Adding it as a
second source would be a pure no-op — `drop_duplicates("gid", keep="last")`
would simply overwrite each frozen row with an identical one.

Do not add it. A second source of the same games is a standing risk to the
frozen estimator: it is harmless only for as long as the two spellings agree,
and nothing would warn you if a future file diverged.

## PREFLIGHT — run this first, it trades nothing

```bash
/home/dpope/nba_env/bin/python /mnt/d/Kalshi/nba/nba_auto_trader.py preflight
```

As of 2026-09-23 it reports **3 failing**, all expected before the season:

| check | status | action |
|---|---|---|
| BigDataBall feed | FAIL | folder does not exist yet; appears when the feed starts |
| NO-side verified | FAIL | run `--verify-no-side`; **CrewShock unaffected** |
| S3 bucket | FAIL | **no AWS credentials on this host** — dashboard cannot publish |
| opening totals | PASS | Odds API live, 9 games on 2026-10-21, quota 8/500 |
| Kalshi auth | PASS | balance $18.92 |

## THE OPENING-TOTAL DEPENDENCY

PaceGap needs `open_total`; MOVE_COMBINED needs `ot_open` as **both a model
input and the settlement reference**. Neither can be synthesised. Sources, in
order:

1. `openers_YYYY-MM-DD.csv` in the project dir
2. **The Odds API** via `nba_openers.py` — the early phase fetches it
   automatically. Key lives in `D:\Kalshi\nba\odds_config.json` (mode 600,
   gitignored; `ODDS_API_KEY` in the environment overrides it).

With neither, the early phase **skips both strategies and says so**. It does
**not** substitute Kalshi's own ladder centre. That substitution is tempting
(at 09:00 Kalshi's centre is near the opener) and wrong: the backtests were
struck on the sportsbook opening number, and changing the reference changes what
is being traded. **CrewShock is unaffected** — it is OVER-only against the
ladder's own centre and runs fully automatically in `late`.

**It is "the line at capture time", not literally the opener.** The Odds API
serves current odds. A 09:00 capture is the earliest practical observation and
is what D2 anticipates — which is why it requires `open_obtained_at_utc`. Every
row is stamped with the real observation time and `open_line_source`. **Do not
backfill this file later in the day and call it an opener**, and note that
`nba_openers.py` refuses to overwrite an existing capture for exactly that
reason.

The consensus is the **median across books**, with the contributing book count
recorded. One book posting a stale number moves a single-book capture by a full
point, and PaceGap's entire margin is 0.064 points.

**Quota: 500/month.** Two calls per early run (one probe-equivalent per fetch)
against ~170 game days is comfortable, but a `*/30` schedule would exhaust it in
days. Do not put `nba_openers.py` on a frequent timer.

## THE BIGDATABALL FEED

```
SOURCE  C:\Users\rando\Dropbox\26-27-nba-team\MM-DD-YYYY-nba-season-team-feed.xlsx
TARGET  C:\NBA2\dfMaster_2027.csv
```

A new dated file each day; `nba_bdb_feed.py` takes the newest at or before the
as-of date. **Run `--probe` on day one before arming anything** — it reports the
feed's actual column spellings and writes nothing:

```bash
/home/dpope/nba_env/bin/python /mnt/d/Kalshi/nba/nba_bdb_feed.py --probe
```

The feed is **team-level** (one row per team per game); CrewShock reads
**game-wide** (`PF_H`/`PF_R`, `MAIN REF_R`, `CREW_H`, …). The adapter pivots on
VENUE and **hard-stops** if any game is not exactly one H + one R row — a game
with two H rows folds one team's fouls onto itself and flips the sign of every
CrewShock input without erroring.

Other hard stops, all deliberate: feed older than 1 day (a stale foul history
does not error — the crew state silently freezes and drifts); any required
column missing; no row containing "Regular Season"; zero usable games.

**The known silent failure is name spelling.** `official.nba.com` writes
`JT Orr`, BigDataBall writes `J.T. Orr`. Unmatched, that zeroes an official's
entire history and biases CrewShock toward zero — it mis-scored a real slate
before canonical matching was added. Those games are flagged `DATA_GAP` and
never actioned. If gaps repeat, reconcile before trusting any score for that crew.

## THE BAR MOVED

`PROJECT_CLOSED.md` result 1 (2026-09-14): the sportsbook hurdle is **1.12 pts,
not 1.089** — only 44% of totals are at −110 and the juice skews against the
bettor. Margins against the real bar:

```
crewshock 1.925 pts   clears by 0.805
move      1.573 pts   clears by 0.453
pacegap   1.184 pts   clears by 0.064      <- thin; was 0.095 at the old bar
```

PaceGap is the marginal strategy. Resting rather than crossing is what makes it
viable at all — crossing a 2¢ book puts it underwater.

## KILL SWITCH

```bash
touch ~/data/NBA_TRADING_HALT
```

`early`, `late` and every placement run exit immediately while it exists. It
does **not** cancel resting orders — run `nba_auto_trader.py cancel --arm` next.
