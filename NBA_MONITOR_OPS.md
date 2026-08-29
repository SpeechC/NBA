# NBA monitor 2026-27 — operating runbook

**Places no bets.** `nba_monitor.py` has no order-placement code and none is to
be added. It prints a table and appends to `nba_monitor_log.jsonl`. Structural.

## The five signals do NOT share a status. This is the point of the layout.

| # | signal | status | rule | source |
|---|---|---|---|---|
| 1 | **CrewShock** | FROZEN / validated | OVER when `CrewShock >= 0.8682` | `CLOSING_REFEREE.md`, `PREREG_crewshock_forward.md` |
| 2 | **final7** | **VALIDATED** 55.29% OOS, 454 bets, 97.2nd pct null, 7/8 seasons | OVER when `days_left <= 7` | `CLOSING.md` |
| 3 | **pre_asb3** | **NOT VALIDATED** — family-wise `p = 0.0712` | **display only, never actioned** | `CLOSING.md` |
| 4 | **MOVE_COMBINED** | FROZEN | `m = 0.0337 + 0.8402·ridge + 0.6869·latent`, \|m\| ≥ 1.0 / 1.5 | `PREREG_move_combined.md` |
| 5 | **roll7** | **UNTESTED** — no prereg, no result here | **display only, never actioned** | new |

**On signal 5.** A trailing **7-calendar-day rolling** mean of
`actual_total − closing_total` per team, strictly prior. This is a different
thing from `final7`, which is an end-of-season window. It has never been tested
in this program and its prior is poor: `BETTING_TOTALS.md` shows every totals
variant at ~50% with ROI −4% to −5%, and `CLOSING.md`'s headline lesson is that
predictability of basketball is not predictability of market error. The monitor
displays it with the game count and over-rate attached — a 2-game window and a
6-game window are not the same evidence — and emits
`DISPLAY_ONLY_UNTESTED`. It needs its own pre-registration before it can be
actioned.

**On signal 3.** `CLOSING.md` records 60.47% over on the pre-All-Star 3-day
window — but it was the best of seven pre-specified regimes and does not clear
family-wise correction. It is "the strongest untested lead, not a second
strategy," and the document explicitly forbids adopting a **7-day** version post
hoc. The monitor therefore implements the **3-day** window, displays it, and
emits `DISPLAY_ONLY_NOT_VALIDATED`. Promoting it to an action requires its own
pre-registration.

## Signal availability calendar — they do not come online together

A silent "no bet" from a signal that *cannot yet compute* looks identical to one
that computed and declined. The monitor prints which it is on every run.

| signal | first available | notes |
|---|---|---|
| CrewShock | **opening night** | officials carry cross-season history; most crews show `min_prior` 60 |
| MOVE_COMBINED | **~mid-November** | rolling features need ~10 games/team. On 2026-10-20 it returns `h_nprior=0, a_nprior=0` and correctly declines every game |
| final7 | **2027-04-04** | `days_left <= 7` against a last regular date of 2027-04-11 |
| pre_asb3 | **2027-02-16 … 02-18** | break located at 2027-02-18 (7-day gap); never actioned |

## Daily sequence

```bash
/home/dpope/nba_env/bin/python nba_monitor.py --date $(date +%F) --lines lines_today.csv
```

Run **after 9am ET**, when NBA.com posts referee assignments, and before tip.
`lines_today.csv` needs `game_date,away_abbr,home_abbr,open_total` — MOVE_COMBINED
bets at the opener and cannot be scored without it. CrewShock and the calendar
windows do not need it.

## Data sources

| input | now | when live |
|---|---|---|
| team box scores | `/mnt/c/NBA2/dfMaster_OT_2017-2026.csv` (through 2025-26) | set `NBA_CURRENT` to the daily file; the monitor reads both and de-duplicates |
| referee assignments | `official.nba.com` API, `?date=YYYY-MM-DD` | posts ~**9am ET** on game day |
| schedule | `nba_schedule_2026_27.csv` (1,271 games, 2026-10-03 → 2027-04-11) | already the real 2026-27 schedule |

## Preseason test — 2026-10-03

```bash
cd /home/dpope/projects/nba_entropy_replication && /home/dpope/nba_env/bin/python nba_monitor.py --date 2026-10-03
```

**A preseason run is a PLUMBING TEST and nothing else.** Both frozen estimators
are built on Regular-Season-only universes, so preseason games must never enter
CrewShock's official histories or MOVE_COMBINED's rolling features. Every signal
on a preseason date is emitted as `INVALID_PRESEASON`. What the test proves is
that the assignment fetch, the name resolution, the box-score join, the calendar
windows and the log write all work — not that any number is meaningful.

Expect on 2026-10-03: 1 game listed, calendar windows resolved, CrewShock
reporting "no referee assignments published yet" unless the NBA posts preseason
crews, and MOVE_COMBINED asking for `--lines`.

## Traps already gated

1. **`label` is blank for ordinary regular-season games.** It is populated only
   for special events (NBA Cup 67, Preseason 64, Rivals Week 12, international
   4). Testing `label contains "Regular"` matched nothing and silently emptied
   **both** calendar windows. Regular season is now `not preseason`.
2. **Calendar windows must come from the SCHEDULE, not from played games.**
   `days_left` was defined in backtest as `max(season date) − date`; live that
   maximum is only knowable from the published schedule, and the All-Star break
   cannot be located from games already played.
3. **Official name mismatch.** `official.nba.com` writes `JT Orr`, BigDataBall
   writes `J.T. Orr`. Unmatched, that zeroes a 60-game history. Canonical
   matching resolves it; anything still unresolved flags `DATA_GAP` and is never
   actioned.
4. **Assignment API date format** must be `YYYY-MM-DD`. `MM-DD-YYYY` returns
   zero rows and looks like an empty slate.
5. **Scoring a date already inside the history** (e.g. a 2026-01-15 replay)
   inserts a pending duplicate of a completed game and can let that duplicate
   enter the crew's own prior window. Fine for plumbing tests, invalid as a
   signal. Live this cannot happen — tonight's games are not yet in history.

## Hard stops

- `crewshock_live.py validate` must print `OVERALL: PASS` before opening night.
- Stale box-score file: if the daily file has not updated since the last slate,
  histories are a day behind. Skip the run.
- Zero assignment rows before 9am ET is normal; zero rows *after* is a flag.
