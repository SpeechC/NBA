# PREREG — combined movement decomposition with the late-injury information channel

**Written 2026-08-23, BEFORE the combined regression is estimated on the
control-free sample.** Authorised as a single confirmatory estimate. It is run
EXACTLY ONCE. `PREREG_move_combined.md` and the frozen `MOVE_COMBINED` signal
are NOT modified by this document.

---

## 1. Canonical role of the injury channel

Registered as a distinct object, deliberately NOT a movement-model feature:

```
LATE_INJURY_INFORMATION_STATE
  availability class : POST_OPEN_PRETIP
  role               : information-arrival / market-assimilation control
  NOT                : historical team state
  NOT                : a frozen movement-model feature
  NOT                : evidence of betting profitability
```

The distinction being preserved: `MOVE_RIDGE` and `MOVE_LATENT` are pregame
structural forecasts of movement, answering "can information available earlier
predict later repricing?". `OUT_late` is an observable information-arrival
event occurring DURING the adjustment process, answering "what happens when
genuinely new information arrives shortly before tip?". Folding the second into
the frozen model would blur two different questions.

Frozen interpretation of the Hypothesis B result:

> Late OUT information constitutes a third, partially independent
> information-arrival channel in NBA total price discovery.

## 2. The single specification

```
dTotal = a + bR * MOVE_RIDGE_OOS + bL * MOVE_LATENT_OOS + bI * OUT_late + e
```

- `dTotal` = `tmove`, open->close total movement (the object MOVE_COMBINED forecasts)
- `OUT_late` = MIN_SHARE-weighted count of OUT_late players, summed over both
  teams, from the definitions frozen in `PREREG_injury.md` section 2. No
  redefinition, no reweighting, no thresholds, no interactions.

Secondary row, REPORTED BUT NEVER PROMOTED: the signed variant
(`OUT_late - UPGRADE_late`). `UPGRADE_late` is already known to be empty
(31 firing games; t=-0.84 dev, +0.37 holdout), so the two must agree; a
disagreement would signal an error, not a finding.

## 3. Sample — and why it is LARGER than the A/B sample

This specification carries NO `rsk.CTRL` controls, so it is not subject to the
control warm-up that bound Hypotheses A and B.

Diagnosed 2026-08-23: `rsk.build()` returns 5,644 of 9,489 games, ~59% in
EVERY season. The cause is not referee data (`referee_game_states.csv` covers
all 9,489 with `CrewShock` non-null) and not raw box-score missingness (`3PA`
and `FGA` are complete in all seasons — an earlier attribution to `tpa_s`
missingness was WRONG). The cause is the `shift(1).rolling(20)` team-form
controls requiring ~20 prior games for BOTH teams:

| decile of season | 1 | 2 | 3 | 4 | 5 | 6-10 |
|---|---|---|---|---|---|---|
| retained | 0% | 0% | 0% | 6.4% | 87.7% | 100% |

The exclusion is deterministic by calendar position, not random. It removes
precisely the early season — when team form is least known, market priors are
weakest, and information-arrival effects are plausibly LARGEST. This is a
substantive selection, not a nuisance.

Sample here: **2020-21..2024-25, games with both frozen movement signals =
5,078** (vs 3,489 under controls, 1.46x), development 2020-21..2023-24,
holdout 2024-25, reported separately.

## 4. What this estimate is and is not

It is NOT independent evidence for the injury channel. Hypothesis B already
established the joint result (dev LATE t=-9.95, holdout t=-5.58) on the
controlled 3,489-game subsample. This is a completeness estimate: does the
channel materially improve the COMPLETE movement specification on the full
control-free sample, including the early-season games the controls excluded?

## 5. Decision rule, fixed before estimation

MATERIAL:
- `bI` with |t| >= 2 on development AND holdout, same sign on both;
- BOTH incumbents retain |t| >= 2 on both windows (no absorption);
- incremental R2 from `OUT_late` >= +0.010 on the HOLDOUT.

Anything less is recorded as "channel confirmed, contribution immaterial".
Failure of the incumbents to survive is recorded as absorption and retires the
third-channel interpretation.

## 6. Prohibited

- estimating more than once, or re-estimating after seeing the result
- any threshold, weighting, interaction, or role-split search on `OUT_late`
- modifying `PREREG_move_combined.md` or the frozen `MOVE_COMBINED` signal
- any claim of tradability from this regression (see section 7)

## 7. Tradability is NOT addressed here, and is currently untestable

The economically decisive question is what fraction of `bI` occurs AFTER the
report becomes observable. That requires an intraday quote path. **We do not
have one, and this is a hard blocker, not a modelling choice.**

Audited 2026-08-23: `kalshi_nba_totals.sqlite` has `candles` = **0 rows** and
`fetch_log` = **0 rows** (the schema exists; the fetch never ran). The
`markets` table carries two snapshot sets, and `close_mid` is populated on
**0 of 14,787** markets. `pregame_bar_ts` sits a median of **1 minute** before
tipoff — so the single usable observation is effectively the close. The
BigDataBall master carries open and close only. There is no intraday path in
any data currently held.

To make the latency question answerable, ACQUIRE:
1. 1-minute Kalshi candles for NBA totals markets (the fetcher scaffolding
   exists and is unrun);
2. overlap is bounded to **2025-10-21..2025-12-22, ~62 game dates** — Kalshi
   history starts at the former, the injury CDN wall falls at the latter;
3. the dependent variable then becomes `Line(report + k) - Line(report)` for
   k in {5, 15, 30} minutes, NOT close-minus-open.

Until then the frozen interpretation stands at market-microstructure, and no
P&L claim may be attached to `OUT_late`.

---

## 8. RESULT — estimated once, 2026-08-23. Verdict: MATERIAL

Sample 5,078 games (2020-21..2024-25); development 4,069, holdout 1,009.
`OUT_late` fires on 1,388 games.

| | development | holdout 2024-25 |
|---|---|---|
| ridge | +0.9727 (t=+14.45) | +0.7461 (t=+6.26) |
| latent | +0.7374 (t=+6.88) | +0.6618 (t=+3.08) |
| **OUT_late (bI)** | **-4.0864 (t=-9.88)** | **-4.6254 (t=-4.71)** |
| R2 incumbents -> joint | 0.07847 -> 0.10010 | 0.05766 -> 0.07802 |
| **incremental R2** | **+0.02163** | **+0.02036** |

All three section-5 criteria met: |t(bI)| >= 2 on both windows with the same
(negative) sign; both incumbents retain |t| >= 2 on both windows, so there is
no absorption; holdout incremental R2 +0.0204 clears the +0.010 bar. The
secondary signed variant agrees closely (-4.0029 / -4.6149), as required —
`UPGRADE_late` is empty, so disagreement would have signalled an error.

The three-channel decomposition is confirmed on the control-free sample:
**late OUT information is a third, partially independent information-arrival
channel in NBA total price discovery.**

### Qualification the run itself exposed — the early-season claim in section 3 does NOT hold

Section 3 argued the control-free sample is not merely larger but less
selected, restoring early-season games where information-arrival effects are
plausibly largest. The first half of that is true; the second is NOT, and the
prediction should be treated as refuted.

Deciles 1-3 contribute **1,525 games, on which `OUT_late` fires 12 times.**
The injury states carry their OWN warm-up: `MIN_SHARE` requires 10 prior games
and `BLK36` requires 300 prior minutes, so no player qualifies as SALIENT or
DEF_ANCHOR early in a season. Removing the control warm-up restored the GAMES
but not the SIGNAL. The ~1,589 additional games enter almost entirely as
`OUT_late = 0`, sharpening the incumbent baseline and the intercept while
adding essentially no new injury events.

This also explains why incremental R2 is LOWER here (+0.0216 / +0.0204) than
in the controlled Hypothesis B run (+0.0314 / +0.0413): the added games dilute
rather than reinforce. The coefficient itself is stable across the two samples
(-4.41/-5.76 controlled vs -4.09/-4.63 here), which is the reassuring part.

Consequence: the early season remains unmeasured for this channel. Testing it
would require role definitions with prior-season carryover — a DIFFERENT
specification, requiring its own pre-registration, and explicitly not
attempted here.

---

## 9. ACQUISITION COMPLETE, 2026-08-23 — and a timing fact that revises section 7

**Candles fetched.** 1-minute bars, 12h lookback, 2025-10-21..2025-12-22:
**1,256,843 rows over 4,719 markets / 429 games / 62 dates, 0 errors.**
Written to a SEPARATE store, `data/kalshi_nba_candles.sqlite`.

**Pipeline hazard found and contained.** `download_nba_totals.py` refreshes the
`markets` table on every run, and that upsert **NULLs `tipoff_ts` and
`pregame_mid`** — enrichment columns written separately by
`pregame_snapshot.py` and absent from the API payload. A single-date probe
silently stripped them from 110 markets (14,471 -> 14,361). Restored from a
pre-probe backup and verified at 14,471/14,471; all subsequent fetching was
isolated to the separate store. `tipoff_ts` is the key the entire latency
analysis depends on, so anyone re-running that script against
`kalshi_nba_totals.sqlite` will silently destroy the analysis key. Treat the
curated DB as read-only.

**Quote density: the book supports the test.** Every pregame window is 100%
two-sided-quoted at a median 3.0c spread; 4,683 of 4,719 markets carry a live
quote inside T-30..T-0. Minute coverage is partial (2.7 bars per market in the
final 5 minutes, 6.8 in T-30..T-15), i.e. bars exist when there is activity.

**The timing fact that revises the design.** Section 7 assumed the decisive
question was minute-scale: whether the move happens before the report is
observable. It is not. Measuring when an `OUT_late` designation FIRST appears
(960 player-events across 327 game-matchups in the window):

| percentile | 10% | 25% | 50% | 75% | 90% |
|---|---|---|---|---|---|
| hours before tip | 5.5 | 6.5 | **8.5** | 11.5 | 30.5 |

Within 6h: 168. Within 3h: **2**. Within 1h: **0**.

`OUT_late` is not last-minute news. It surfaces a median 8.5 hours before tip.
The k in {5,15,30} MINUTE horizons of section 7 are therefore the wrong
instrument: by tip the information is many hours old, and the market has had
the whole day to absorb it. The right horizons are hours, and the right
question is the shape of absorption over that day, not a minute-scale race.

Two consequences: (i) roughly the top decile (first appearance >12h before
tip) falls OUTSIDE the 12h candle lookback and is not measurable without a
deeper fetch; (ii) the near-zero count inside 1h means a minute-scale event
study has essentially no events and could not have been run regardless of
quote density.

CAVEAT on the table above: it uses the MEDIAN tipoff per date, not per game.
Games on one date tip across several hours, so these figures are approximate
and adequate only for the design decision they are used for here. A per-game
tipoff join is required before any estimate, and is not yet built.

**No event study has been run.** The horizons, the ladder-to-line conversion,
and the decision rule are all now open design choices and require their own
pre-registration before any estimate is produced.
