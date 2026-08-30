# CONSOLIDATED OPERATIONS — 2026-27 season

**Supersedes the scheduling sections of `CREWSHOCK_LIVE_OPS.md` and
`NBA_MONITOR_OPS.md`** (their diagnostics and failure modes remain authoritative).
Single entry point: `nba_daily.py`. **No component places bets.**

## THE FOUR PHASES, and why the order is not cosmetic

| phase | when | command | writes |
|---|---|---|---|
| **1 capture** | as early as openers exist | `nba_daily.py capture [date]` | `prospective_log`, `lines_today.csv` |
| **2 assignments** | **after 9:00am ET**, before tip | `nba_daily.py assignments [date]` | `crewshock_live_log.csv`, `nba_monitor_log.jsonl` |
| **3 ladders** | pregame | `nba_daily.py ladders [date]` | Kalshi sqlite |
| **4 settle** | next morning, after BigDataBall | `nba_daily.py settle [prior-date]` | appends outcomes to all logs |

**Phase 1 must precede the injury report and any line movement.** The
`open_obtained_at_utc` field is the one `INJURY_TIMING_AUDIT` proved we lacked in
2025-26 — 42% of injury reports arrive on game day, and without an opener
timestamp we could not adjudicate what preceded what. **This season we can.**

**Phase 2 cannot run earlier**: referee assignments do not exist before ~9am ET.
`CREWSHOCK_LIVE_OPS` records that a stale-history run is a hard stop, and that a
zero-row API response must be reported, never treated as an empty slate.

**Phase 4 must not run before BigDataBall lands**, or official histories are a
day behind and the next day's CrewShock is silently wrong.

## STATUS — what is built and what is NOT

| component | state |
|---|---|
| `crewshock_live.py` | **BUILT**, validated to max\|diff\| 1.8e-09 |
| `nba_monitor.py` | **BUILT**, 4 signals, calendar from published schedule |
| `prospective_log.py` | **BUILT**, immutable rows, duplicate/double-settle refused |
| Kalshi collector | **BUILT** (`/mnt/c/NBA2/Kalshi/download_nba_totals.py`) |
| `nba_daily.py` | **BUILT**, orchestration + health |
| **`capture_openers.py`** | **NOT BUILT** — must fetch openers with timestamps, call `prospective_log.log_game()`, and emit `lines_today.csv` for MOVE_COMBINED |
| **`settle_day.py`** | **NOT BUILT** — must call `prospective_log.settle()` and grade the CrewShock ledger and monitor rows |

**Both gaps are on the critical path and must be built before 2026-10-03.**
`capture_openers.py` also has to compute `P_hat`, `P_book`, `EffSum`, `mu5` and
`m_X` from the frozen models — that is the real work, and the specifications are
in `PREREG_2026_27_PROSPECTIVE` A3/B1.

## SEASON CALENDAR

| date | event | action |
|---|---|---|
| **2026-10-03** | preseason opens | **plumbing test only.** Run all four phases. Preseason games are NOT scored and must not enter any log used for evaluation. |
| **2026-10-20** | regular season opens | full daily cycle begins |
| ~**2026-11-15** | MOVE_COMBINED activates | before this it correctly returns `h_nprior=0` and declines every game — that is not a failure |
| **2027-02-18** | All-Star break | `pre_asb3` window closes (display-only signal) |
| **2027-04-11** | last regular-season date | daily cycle ends |
| **after 2027-04-11** | **evaluation day** | see below |

## EVERYTHING THAT COMES DUE AT SEASON END — read together, once

| prereg | endpoint | note |
|---|---|---|
| `PREREG_crewshock_forward` §4 | M1 `b_fouls` vs the z-rule; M2 `c_market` | z >= −1.5 intact / z <= −2.5 break |
| `PREREG_density_crewshock` | P3 positive control FIRST; if it fails, P1 is never run | held since 2026-08-29 for exactly this date |
| `PREREG_2026_27_PROSPECTIVE` H1 | `D -> Actual-Open`, continuous | **UNDERPOWERED** on one season (MDE 0.272 vs beta 0.222) |
| `PREREG_2026_27_PROSPECTIVE` H2 | `AggregateGap -> Actual-Close` | needs ~4,004 games; **pooled 2022-2027 read pre-committed** |
| `PREREG_2026_27_PROSPECTIVE` S1 | `D*_drift` / `D*_profile` vs `D` | incremental comparison, not significance |
| `PREREG_2026_27_PROSPECTIVE` S2 | frozen candidate \|E\| >= 4.77 vs bet-all | report all six economic metrics |

**A prereg written in August for an April read is exactly the kind of thing that
quietly disappears.** All six are listed here so one evaluation day covers them.

## BINDING IN-SEASON RULE

`PREREG_2026_27_PROSPECTIVE` D3: **no interim looks at wagering performance.** Not
running hit rate, ROI, alternative thresholds, Over/Under splits, or any
breakdown. `nba_daily.py status` deliberately computes none of these — it reports
row counts, settled counts, missing fields and code SHAs only.

Anything noticed anyway becomes a **2027-28 hypothesis** and does not touch the
frozen evaluation.

## SCHEDULING

Not yet automated — deliberately. The two missing scripts must exist and run
clean through the 2026-10-03 preseason test first. Once they do, the natural
cadence is four cron entries matching the phases above, with **phase 2 no earlier
than 9:30am ET** and **phase 4 gated on BigDataBall arrival** rather than a fixed
clock time.
