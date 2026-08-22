# PREREG — pregame injury-report states: role-specific absence and the totals
# channel, plus intraday status changes as a movement source

**Written 2026-08, BEFORE any injury-report PDF has been parsed or joined to
any outcome or line.** The scrape (raw PDF download) may run concurrently; no
state construction or outcome join happens until this file is committed.
This is `PROSPECTIVE.md` acquisition item 1 executed under the CrewShock
template: exogenous to the game, published at league-mandated times,
mechanically linked to scoring.

---

## 1. Data and timing structure

Official NBA injury reports, 2019-20 policy onward: PDFs at
`ak-static.cms.nba.com/referee/injury/Injury-Report_{DATE}_{HH}{AM/PM}.pdf`,
verified live for 2019 and 2022. Panel overlap: **2020-21 .. 2025-26**
(the master has no 2019-20 season). Development = 2020-21..2023-24; holdout =
2024-25 ONLY (2025-26 dropped — see the Q1 resolution in §5).

The timing structure does the identification work:

- the **day-before ~5PM report** typically PRECEDES the totals opener
  -> absences known there should be priced into the OPEN;
- **subsequent updates** (game-day reports) are POST_OPEN_PRETIP — the same
  knowability class as referee assignments, and the clean exogenous shock.

## 2. Frozen state definitions (all prior-only, all from data already held)

Per player-game, from the report sequence:

```
OUT_baseline   player listed OUT in the earliest captured report for the game
OUT_late       player NOT OUT (or absent) in the earliest report, but OUT in
               the latest pregame report        <- the post-open shock
UPGRADE_late   listed OUT/Doubtful early, then playing-eligible late
```

Player salience and role, frozen before any join to outcomes:

```
MIN_SHARE      player's trailing within-season share of team minutes,
               shift(1) over prior games (lineup parquet), min 10 prior games
SALIENT        MIN_SHARE in the player's team's top 3 at that date
BLK36          trailing blocks per 36 minutes, shift(1), min 300 prior minutes
               (blocks from PBP: blocked-shot events attribute the blocker)
DEF_ANCHOR     SALIENT and BLK36 in the development top quintile (threshold
               frozen on development player-seasons)
OFF_STAR       SALIENT and not DEF_ANCHOR
```

Game-level states: counts and MIN_SHARE-weighted sums of each category per
team. **No injury-type, severity, or player-name conditioning is permitted** —
role enters only through the two frozen categories above.

## 3. Hypothesis A (PRIMARY) — the totals channel of role-specific absence

The market prices star absences into the SPREAD; the claim is that it
under-prices the TOTALS consequence of DEFENSIVE role. A defensive anchor's
absence raises opponent scoring with little offset in own scoring, so:

```
prediction A1:  for DEF_ANCHOR absences, gap = c_true - c_market > 0 on the
                closing TOTAL (market total set too low)
prediction A2:  for OFF_STAR absences, gap ~ 0 (priced)
```

Estimator: the project-standard c_true / c_market / gap regressions on the
closing total, controls = the frozen `rsk.CTRL` set, absence states entering
as MIN_SHARE-weighted counts per category per team. Development first; holdout
reported separately; cluster-robust at game level. Inference of record:
within-season permutation of the absence state across games (5,000 reps).

Falsification (A3): OUT_baseline absences (known before the open) must show
gap ~ 0 against the OPEN — if the market prices day-before news into the
opener, the baseline component is NOT an omission and only the post-open
component may be. A large baseline gap would indicate a data/timing error
before it indicates an edge.

## 4. Hypothesis B (SECONDARY) — intraday status change as a movement source

```
prediction B1:  OUT_late / UPGRADE_late (signed, MIN_SHARE-weighted) predict
                open->close TOTAL movement
prediction B2:  the effect survives JOINTLY with MOVE_RIDGE_OOS and
                MOVE_LATENT_OOS (move_signal_states.csv) — the incremental
                standard. Alone-only significance = rediscovery, not a source.
```

B is the candidate THIRD movement source. It does not modify
`PREREG_move_combined.md`; if B2 passes on development AND holdout, a
combined-spec extension gets its own pre-registration.

## 5. Stage-0 data-quality gate (before any market number is read)

| gate | requirement |
|---|---|
| Q1 coverage | >= 90% of panel games in the ANALYSIS WINDOW have >= 1 captured report |
| Q2 parse validity | players listed OUT in the final pregame report play 0 seconds in the lineup parquet in >= 97% of cases |
| Q3 timing sanity | report timestamps precede tip for >= 99% of used reports |

**Any Q-gate failure stops the market tests** until the data defect is fixed —
fixing data is permitted; touching the hypothesis or states is not.

**Q1 resolution, recorded 2026-08 after the gates ran.** Measured coverage on
2020-21..2025-26 was 88.0% — a FAIL driven entirely by the documented
2025-12-22 CDN wall (2025-26 at 31.2%; every other season 96.6-100%). Per §8
risk 3, which anticipated exactly this, **2025-26 is dropped in full** and the
analysis window becomes **2020-21..2024-25**. Scoped coverage is
**5,821/5,868 = 99.2%, PASS**. 2025-26 is excluded entirely rather than
included partially: the surviving 31% slice ends 22 December, so it carries no
post-Christmas games and no trade-deadline period — the window where late
status churn peaks and where Hypothesis B would be most affected. A
compositionally skewed partial season is worse than none.

CONSEQUENCE, stated plainly: development is 2020-21..2023-24 (four seasons,
intact) and the **holdout is ONE season, 2024-25 (1,166 games)**, not two.
All holdout claims carry correspondingly less power and must say so.


## 6. Decision thresholds, fixed now

- A1 PASS: development gap > 0 with permutation p < 0.05, holdout gap same
  sign. Economic relevance requires >= +1.0 point of closing-total gap per
  MIN_SHARE-weighted DEF_ANCHOR absence.
- B2 PASS: joint t >= 2 on development AND holdout sign agreement.
- All other cells (A2, A3, falsifications) are reported, never promoted.

## 7. Prohibited

- injury-type/severity/body-part conditioning; player-name selection
- re-tuning MIN_SHARE top-3, the BLK36 quintile, or the min-prior floors after
  seeing any outcome (all frozen here, computed on development only)
- substituting Doubtful/Questionable weighting schemes after a failure
- any use of post-tip information in state construction
- promotion of B without the joint-survival standard
- proxying missing report days with third-party day-level sources inside the
  test windows (Pro Sports Transactions may extend HISTORY for descriptive
  context only, never for the tested states)

## 8. Known risks, recorded in advance

1. The opener may already price game-day news via early respray — A3 checks
   the baseline, but openers are captured once in our feed; timing residue is
   possible in both directions.
2. DEF_ANCHOR via BLK36 is a crude role proxy; if A1 fails, that is evidence
   against the hypothesis AS SPECIFIED, and no alternative role definition may
   be tried under this document.
3. 2025-26 report URLs returned 403 under the old naming in a probe; if that
   season cannot be captured, the holdout shrinks to 2024-25 and the document
   proceeds with the reduced window, flagged.
