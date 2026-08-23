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
