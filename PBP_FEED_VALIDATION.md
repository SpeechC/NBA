# Live PBP feed — validation (2026-08-30)

`pbp_feed.py` supplies `pbp_transition.update()` for 2026-27. This records what it
was checked against and what it costs.

## Why cdn.nba.com

`stats.nba.com/stats/playbyplayv2` returns **HTTP 200 with a 2-byte body** from
this host — blocked, not flaky, so retries do not help. `cdn.nba.com` serves
static JSON with no auth in ~0.2s. The 2026-27 schedule is already published
there (1,206 regular-season games).

The cost: the CDN serves the **liveData** schema (actionType strings), not the
**v2** schema the frozen reconstruction was validated on. `pbp_feed` maps liveData
back onto v2 so `_aggregate` runs unmodified.

## Faithful, not accurate — deliberately

The CDN labels every rebound `offensive`/`defensive` outright. That is strictly
better information than the frozen team-change heuristic. **It is not used.**
Computing live `trans_share` by a better rule than the 18,330 backfilled
team-games would put a rule change exactly at the season boundary, inside a team
state that pools history and live. The label is ignored and the heuristic
re-derived.

## What the mapping had to get right

The CDN is a **strict superset** of the parquet: 0 parquet-only events out of
15,673 aligned, and **100.000%** msgtype agreement. `actionNumber` *is* `EVENTNUM`.
So the mapping is confirmed correct, and the only question was what to drop.

Three defects found and fixed, each by measurement:

| Defect | Effect | Fix |
|---|---|---|
| Standalone `steal`/`block` rows (v2 folds these into the turnover/miss) carry the **defending** team and poison the `prev_team` shift that detects defensive rebounds | corr 0.9258, sd 1.98pp | drop unmapped rows |
| CDN emits a `period` row at t=0 that the parquet lacks; `recon` falls back to the period **minimum**, so the first shot of every period moves from sc=0 to sc≈17 — **141 of 141** trans-flag disagreements, ~1 per period per game | bias −1.54pp | `KEEP_MSG = {1,2,3,4,5,6}` |
| liveData clock is fractional; v2 renders MM:SS, truncating — so `elapsed_v2 = ceil(elapsed)` | corr 0.9756 → 0.9868 | `ceil` |

Also confirmed by measurement: v2 nulls `PLAYER1_TEAM_ABBREVIATION` on TEAM
rebounds and the CDN fills it in, so it is nulled back out (parquet 15.4% null vs
CDN 15.8%; defreb-eligible rebounds identical at 3,549). And the parquet's
`PCTIMESTRING` is **game-elapsed**, offset exactly 720×(period−1) then 300s per
OT — this cancels inside `sc` (both terms are within-period) but is emitted
correctly anyway.

## Result — 40 games, 80 team-games

| metric | corr | bias | sd |
|---|---|---|---|
| `trans_share` | **0.9868** | +0.63pp | 0.83pp |
| `live_to` | 0.9986 | +0.03 (97.5% exact) | — |
| `fga` | 0.9975 | +0.31 | — |

For scale, the frozen reconstruction scored corr 0.9854 / sd 0.84pp against
`STARTTIME`. The feed matches the reconstruction's own accuracy.

## The residual +0.63pp is a real discontinuity — stated, not corrected

It is small in output terms: **−0.068 pts** of m(X), 1.4% of the 4.77 threshold.
It is **not** small as a feature shift: 0.564 of the cross-team sd of
`trans_share` (1.118pp over 30 teams). Every 2026-27 team will read ~0.6pp more
transition-heavy than the parquet-derived history it is pooled with.

It is **uniform**, so it moves m(X) by approximately a constant and cannot create
game-to-game differential error — the thing that would actually corrupt bet
selection. No offset is applied: a fitted correction would be a free parameter
tuned on 40 games, and the frozen model has none.

**The clean fix exists and was not taken unilaterally.** Rebuilding the store from
the CDN for all seasons would remove the discontinuity outright. But the CDN does
not serve 2017-18 (verified: `0021700001` unavailable; 2019-20 onward all
return), so it would cost the store its first two seasons — 8 down to 6. That is
a judgement call about the frozen backfill and is left open.

## Operational behaviour

- `fetch_day` returns **partial** days rather than raising: a postponed game must
  not block the other nine. Missing games are printed by id.
- `settle_day.py` uses the feed as primary and falls back to the parquet when it
  yields nothing (backtests, pre-2026-27 dates).
- A real outage is caught downstream by `PT.staleness()` (>7 days ⇒ `m_X` logged
  EMPTY), not by this module.
