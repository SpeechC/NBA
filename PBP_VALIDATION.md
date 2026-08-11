# Play-by-play ingest and possession validation

Phase 1 of the pbp work: plumbing, validated against independent ground truth
before any modelling.

## Ingest

`pbp_lineups_all.parquet` copied to the Linux filesystem (453 MB, 2.5 s).
4,740,150 rows, 10,182 games, 65 columns, scans in 0.05 s.

**Lineup integrity is perfect.** Across all 4.74M rows, in every season: zero
null player slots, zero rows without 10 distinct on-court player ids.

`STARTTYPE` coverage 71.7% → 84.3%, improving over time exactly as the schema
doc records.

## Two joins verified

**pbp ↔ odds: 99.66%** (7,726 of 7,752 odds games).

⚠ The build stripped the leading zeros — `GAME_ID` is stored as **int64 with 8
digits** (`22400148`), so the §4 zfill rule must be applied to the parquet
itself, not only to the source CSVs. Both sides need `zfill(10)` or the join
silently returns zero rows.

The 26 unmatched are fully explained and expected:

| cause | n |
|---|---|
| play-in games (season type 5 — absent from the pbp build) | 24 |
| games dropped by the build in 2022-23 | 2 |

pbp games with no odds: 2019-20 (1,139) and 2024-25 (1,313), plus 4 in 2023-24.

## Possession reconstruction

Method: assign the team in possession from every shot, free throw, turnover and
rebound (`PLAYER1_TEAM_ID`), forward-fill within period, count changes of hand.

### Two bugs found and fixed

**1. Team rebounds and team turnovers carry the team in `PLAYER1_ID`, not
`PLAYER1_TEAM_ID`.** 15.3% of rebounds and 5.2% of turnovers have a null team
id — "PACERS Rebound", "Knicks Turnover: Shot Clock" — and on every one of those
rows `PLAYER1_ID` holds a value in the 1610612737-66 team block (21,112 of
21,112 in 2023-24). Dropping them lost ~19k possession changes per season.
Fixing it moved mean bias from **−0.400 to +0.128**.

**2. `POSS_H` == `POSS_R` in all 7,752 games.** BigDataBall reports a single
game-level possession count assigned to both sides. Comparing a per-team
reconstruction against it is comparing different quantities; the correct
comparison is the mean of the two team counts. A real per-team split differs by
0-2 in a normal game, since each period can leave whichever team opened it one
possession ahead.

**3. `EVENTNUM` is not chronological.** Only **7.2%** of games have
`PCTIMESTRING` monotonic in `EVENTNUM` order, and the excursions run to hundreds
of seconds — not tie-breaking. Events must be ordered by clock within period,
with `EVENTNUM` breaking ties. This was found via stint durations but it improved
possessions too.

### Result — six seasons with odds

| season | games | mean diff | SD | MAE | within 2 | corr |
|---|---|---|---|---|---|---|
| 2017-18 | 1,230 | −0.054 | 1.30 | 1.03 | 88.0% | 0.970 |
| 2018-19 | 1,230 | −0.074 | 1.25 | 0.99 | 89.1% | 0.976 |
| 2020-21 | 1,080 | −0.095 | 1.26 | 1.00 | 88.7% | 0.971 |
| 2021-22 | 1,230 | −0.136 | 1.30 | 1.05 | 87.1% | 0.967 |
| 2022-23 | 1,228 | −0.083 | 1.39 | 1.06 | 86.8% | 0.966 |
| 2023-24 | 1,226 | −0.063 | 1.25 | 0.99 | 89.1% | 0.970 |

Bias is **0.05–0.14 possessions on a base of ~99 (≈0.1%)** and stable across six
seasons, including the two COVID-affected ones. (Ordering by `EVENTNUM` instead
gave MAE 1.16–1.22 and correlation 0.955–0.968.)

The residual SD of ~1.5 is convention, not error: BigDataBall's own `POSS`
departs from the classic box-score formula with SD 1.7, so our agreement with
them is tighter than their agreement with the standard formula. At season level
the noise averages down to ~0.17 possessions per team.

**Verdict: possession reconstruction is validated.** Safe to build pace,
efficiency and lineup features on.

## Other findings

- `EVENTMSGTYPE = 18` exists (2,456 events in 2023-24) and is absent from the
  schema doc's code table. It is **Instant Replay** — not possession-relevant.
- `SCORE IS NOT NULL` is an exact made/missed flag for free throws
  (41,903 made = 53,430 total − 11,527 "MISS" descriptions).
- Rebound offensive/defensive **cannot** be read from the description: the
  `(Off:0 Def:1)` text is the player's season totals, not this rebound's type.
  Compare the rebounder's team to the prior possession instead.
- Free-throw "last of trip" is best parsed from the description's "X of Y"
  rather than by enumerating `EVENTMSGACTIONTYPE` — the subtype vocabulary runs
  to at least 15 values including flagrant, clear-path and technical variants.
- Technical free throws (subtype 16) must be excluded from possession logic:
  they are shot without a change of hand.

## Stints

`stints.py` builds contiguous 5-on-5 blocks: **67,165 stints over 1,230 games
(54.6 per game)** in 2023-24, each with possessions, points, duration and the
home/away five split out.

All three independent checks pass:

| check | result |
|---|---|
| stint seconds sum to 2880 + 300/OT per game | **exact on 100.0%** of games |
| ten on-court ids split exactly 5/5 by team | **100.00%** |
| stint points sum to the final score | **99.9% home / 99.8% away**, mean error 0.00 |

Team membership is recovered per game from that game's own
`PLAYER{1,2,3}_ID`/`PLAYER{1,2,3}_TEAM_ID` pairs — per game rather than per
season, because players get traded.

Two traps found here:

- **`PCTIMESTRING` is INTEGER seconds elapsed since tip, not an "MM:SS" string
  of clock remaining** as the schema doc states. Period 1 spans 0-720, period 4
  ends at 2880, each overtime adds 300. Parsing it as MM:SS yields times in the
  hundreds of thousands of seconds.
- **Stint duration must be accumulated at event level.** During rapid
  substitutions several stints share a timestamp, so stint-level start/end
  intervals overlap on ~3.4% of stints and a clipped difference breaks the
  telescoping sum by ~90s per game.

## Next

Garbage-time flagging — score margin and time remaining are now available per
possession, and it is the cheapest real improvement to the existing team ratings
since it cleans a known contaminant in every OEFF/DEFF rather than adding a
feature.
