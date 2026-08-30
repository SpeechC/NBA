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
| `frozen_models.py` | **BUILT** — state engine, replays all recursions deterministically |
| `capture_openers.py` | **BUILT**, end-to-end tested on a real slate |
| `settle_day.py` | **BUILT**, idempotent (re-runs settle 0, never overwrite) |

### Validation on a real historical slate (2026-02-04, 7 games)

```
states as of 2026-02-04: 9,012 prior games, a,b=(19.2817, 0.9204)
E_pace across the slate: +2.59, +1.73, -4.62, +5.21, -4.05, +0.24, +6.61
bet_flag rate on Feb 2026: 31.3%   (discovery 30.3%)
sd(E_pace) on that month: 4.63     (discovery 4.7)
round-trip: logged 7 -> settled 7 -> re-settle 0, incomplete_pregame []
```

The live engine reproduces the discovery distribution, which is the check that
matters: a re-implementation drifting from the frozen spec would show up here.

**`a,b` had to be fitted on the FORECAST product, not the realised one.** Fitting
`Open ~ realised_pace x realised_efficiency` gave `b = 0.231` and inverted to a
book pace of **125 possessions** — errors-in-variables attenuation. Corrected to
the forecast product it is `b = 0.920`.

### THE ONE REMAINING GAP: `m_X` is not computed

`m(X)` needs the 22-feature profile, four of which (`trans_H/R`, and the
`TransComp` interaction) derive from **play-by-play**, which is not wired into the
daily path. So:

```
m_X            logged EMPTY  (never 0.0)
D_star_profile logged EMPTY
health() reports  m_X_populated: 0   incomplete_pregame_fields: ['m_X','D_star_profile']
```

**Empty, not zero, is deliberate.** A silent 0.0 would make `D*_profile` identical
to `D` and make **S1's profile leg look evaluable when it is inert** — the same
silent-zero failure that mis-scored a CrewShock slate via an unmatched official
name.

**Status 2026-08-30 — CLOSED.** `pbp_transition.py` is built, validated against
the parquet (team-game corr 0.9854, bias −0.21pp) and backfilled over 18,330
team-games (2017-10-17 .. 2025-04-13). `settle_day.py` calls `PT.update(day)`
before the state rebuild, so the store advances daily. End-to-end on a simulated
2026-02-04 slate: `m_X_populated 7/7`, `incomplete_pregame_fields []`, and
`D*_profile` genuinely separates from `D`. **S1's profile leg is now evaluable.**

**The live feed is built.** `pbp_feed.py` (requests → cdn.nba.com) is primary in
`settle_day.py`, with the historical parquet as fallback. `stats.nba.com` is
blocked from this host (HTTP 200, 2-byte body), so the CDN liveData schema is
mapped back onto v2 and `_aggregate` runs unmodified. Validated on 40 games:
`trans_share` corr **0.9868**, sd 0.83pp — matching the frozen reconstruction's
own 0.9854/0.84pp against `STARTTIME`. A **+0.63pp uniform level shift** remains
and is documented, not corrected: it is 0.564 cross-team sd as a feature but only
−0.068 pts of m(X). See `PBP_FEED_VALIDATION.md`.

**Open call:** rebuilding the store from the CDN would remove that discontinuity,
but the CDN does not serve 2017-18, so it would cost the store two of its eight
seasons.

**Scope of the PBP dependency — verified, not assumed.** Deleting the transition
store entirely and re-running capture leaves `E_pace`, `bet_flag` and `side`
**bit-identical**; only `m_X` and `D_star_profile` go EMPTY. PBP feeds exactly one
path: `trans`/`live_to` -> profile -> `m(X)` -> `D*_profile` -> the SECONDARY
comparison endpoint S1. It never reaches `P_hat`, `P_book`, `D` or the threshold.

Therefore: the +0.63pp CDN level shift cannot affect a wager, and the staleness
hard-stop is a diagnostic guard, not a trading guard. B1's registered default is
already the non-PBP option ("if drift matches profile prospectively, use drift").

**Cache invalidation.** `frozen_models._TRC` loads the store once per process and
never re-reads it. `nba_daily.py` runs all four phases in ONE process, so a settle
that appends to the store would leave a later state rebuild reading the pre-update
snapshot -- silently. `PT.update()` and `PT.backfill()` now call
`_invalidate_caches()`, which clears `_TRC` via `sys.modules` (never importing
frozen_models itself). Verified in-process: 18,330 -> append 2 -> 18,332.

**Staleness is a hard stop, not a warning.** `_mean()` skips NaN, so a stale
store does not error — the transition state silently freezes at its last observed
value and `m(X)` drifts with nothing visible in the output. `PT.staleness(day)`
fails at >7 days and `capture_openers.py` then logs `m_X` **EMPTY**, which
`health()` surfaces via `incomplete_pregame_fields`. Verified: against 2026-02-04
the store reports 297 days stale and every `m_X` logs empty. A stale-store day is
reported as **profile-leg not evaluated for that day**, never as a null.

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
