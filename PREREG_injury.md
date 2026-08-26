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

---

## 9. RESULTS, recorded 2026-08-23 (repaired panel, all four gates PASS)

Development 2020-21..2023-24 (2,798 games), holdout 2024-25 (691 games).
Sample is capped by `tpa_s` missingness in `rsk.CTRL` (2,379 of 5,868 games
league-wide, uniform across seasons) -- a PRE-EXISTING control-set limitation,
not an injury-data one. State incidence: DEF_ANCHOR baseline absences fire on
696 games, OUT_late on 1,524.

### Hypothesis A — FAIL (A1 rejected on its own frozen gate)

| cell | window | c_true | c_market | gap | t |
|---|---|---|---|---|---|
| A1 DEF_ANCHOR / close | dev | +3.041 (0.66) | -0.162 (-0.15) | **+3.203** | 0.72 |
| A1 DEF_ANCHOR / close | holdout | +8.882 (1.17) | -5.675 (-2.67) | +14.557 | 2.00 |
| A2 OFF_STAR / close | dev | -7.047 (-2.94) | -9.030 (-16.42) | +1.983 | 0.85 |
| A2 OFF_STAR / close | holdout | -6.664 (-1.53) | -10.570 (-9.09) | +3.906 | 0.93 |
| A3 DEF_ANCHOR / OPEN | dev | +3.041 | -1.841 (-1.86) | +4.882 | 1.07 |
| A3 DEF_ANCHOR / OPEN | holdout | +8.882 | -6.597 (-3.66) | +15.479 | 2.06 |

A1 permutation p = **0.4875** (5,000 within-season reps; gate required
p < 0.05). **A1 FAILS.** Economic scale also fails: +3.203 x mean weight
0.1907 = **+0.61 points per firing game**, against a >= +1.0 requirement.
c_true itself is insignificant (t=0.66) -- the premise that a DEF_ANCHOR
absence raises the total is not established here, so there is no omission to
price. Per section 8 risk 2 this is evidence against the hypothesis AS
SPECIFIED, and no alternative role definition may be tried under this document.

The holdout cell (gap +14.557, t=2.00) does NOT rescue A1 and must not be read
as one. Three reasons, all pre-committed: (i) the gate is sequential -- the
development permutation decides, and it failed at p=0.49; (ii) the A3
falsification fires at the same time and the same size (+15.479 vs +14.557),
so whatever it is appears identically against the OPEN and the CLOSE, which is
precisely the pattern section 3 designated as "a data/timing error before it
indicates an edge"; (iii) it is driven entirely by c_market (t=-2.67), not by
c_true (t=1.17) -- the market lowers the total on these absences and outcomes
do not follow, on one season.

A2 behaved exactly as predicted and is the pipeline's validity check: the
market prices OFF_STAR absences hard (c_market -9.030, t=-16.42), c_true is
close behind (-7.047), and the gap is ~0 (p=0.38). The machinery detects real
pricing where real pricing exists. That is what makes the A1 null credible
rather than a plumbing failure.

### Hypothesis B — PASS (B2 met on both windows)

| window | B1 alone | JOINT ridge | JOINT latent | JOINT LATE | incr. R2 |
|---|---|---|---|---|---|
| development | -4.022 (t=-8.69) | +1.053 (12.84) | +0.773 (5.86) | **-4.405 (t=-9.95)** | +0.0314 |
| holdout | -4.851 (t=-4.60) | +0.748 (4.88) | +0.657 (2.45) | **-5.763 (t=-5.58)** | +0.0413 |

B2 required joint |t| >= 2 on development AND holdout sign agreement: met, with
both incumbents surviving alongside. Incremental R2 is +0.0314 on development
(over 0.0818) and +0.0413 on holdout (over 0.0466 -- nearly doubling it). The
effect is entirely OUT_late (t=-10.14 dev, -5.57 holdout); UPGRADE_late is
empty (t=-0.84, +0.37) on 31 firing games and carries nothing.

Partial encoding exists -- MOVE_RIDGE_OOS ~ LATE gives t=+3.07 dev / +3.02
holdout -- so the incumbents already anticipate some late-out news, but LATE
survives jointly at t=-9.95 / -5.58 and is mostly independent.

**What this does and does not license.** B is a DECOMPOSITION result: late
status changes are a third partly-independent source of open->close total
movement, sign negative (net late absences move the total down). It is NOT a
tradable edge as it stands. The final pregame report precedes tip by ~30
minutes and the close is at tip, so this is near-contemporaneous with the
market's own reaction; converting it to P&L is a latency question (receive and
act on the report faster than the market), not a research one. Per section 4,
a combined-spec extension requires its own pre-registration and does not
modify PREREG_move_combined.md. The frozen MOVE_COMBINED signal is untouched.

### Process note — two silent parser defects preceded these numbers

An earlier run of these same tests produced different numbers (A1 dev gap
+6.54; B holdout t=-2.43) on a panel missing ~530,000 rows. The archive has
two layout eras and BOTH transitions broke the parser silently: column
x-positions differ pre/post Nov-2023, and the old layout repeats the column
header on every page while the new one prints it on page 1 only -- so pages
2..N of every modern report were skipped, yielding ~15 rows/report instead of
~100. Q1-Q3 could not see this: Q2 validates rows that WERE parsed and scored
99.95% throughout. Gate **Q4 (era stability, rows-per-report within 2x across
eras)** was added and is now part of the Stage-0 verdict; the old panel scores
5.7x FAIL, the repaired one 1.25x PASS. Repaired totals: 1,224,205 rows,
13,219 reports, 1,028 players.

---

# P&L ADDENDUM 2026-08-26 — read-only. **B does not trade, in either direction.**

Run as the third of a series applying the same economic check to every signal
this program holds. Nothing refitted; `injury_market.build()` called as frozen.
B fires on 1,409 games with both lines present.

## The two variants that must not be conflated

`OUT_late` is defined as the difference between the **earliest** and **latest**
pregame report. The latest report exists ~30 minutes before tip. So betting the
opener on it uses information that **does not exist at the opener** — leakage by
construction, reported only to bound what a latency edge could ever be worth.

| variant | bets | hit | profit | ROI | z | ROI 95% CI |
|---|---|---|---|---|---|---|
| **UPPER BOUND @ opener** (leakage) | 1,408 | 51.14% | −$3,345 | −2.38% | −0.93 | [−7.36%, +2.61%] |
| **ACTIONABLE @ close** | 1,393 | 48.17% | −$11,200 | **−8.04%** | **−3.14** | [−13.05%, −3.03%] |

**Even the unattainable upper bound loses money.** Perfect foresight of late-out
news, acted on at the opener, returns −2.38%. There is no latency race worth
winning here, because the thing you would win does not pay.

The actionable variant loses **significantly** — the ROI interval excludes zero
— and does so in every season: −7.08 / −11.70 / −7.71 / −2.78 / −10.12.

## The flip does not rescue it — vig eats the over-reaction

Betting the close in B's direction losing 8.04% means the market **over-adjusts
downward** on late absences. The natural next thought is to take the other side.
It does not work:

| variant | bets | hit | ROI | z |
|---|---|---|---|---|
| B direction (UNDER) @ close | 1,393 | 48.17% | −8.04% | −3.14 |
| **OPPOSITE (OVER) @ close** | 1,393 | **51.83%** | **−1.05%** | −0.41 |

51.83% against a required **52.381%**. The over-reaction is real but **smaller
than the vig**. Both sides of the market lose. Recorded explicitly so the flip
is not attempted later as an obvious-looking rescue.

## What B actually is — and it is not nothing

```
CLV in B's direction:  +0.7754 pts   t = +7.93   beat the close 55.6%
```

The line genuinely moves toward B's direction between open and close. **That
movement IS Hypothesis B.** B was pre-registered as a decomposition of *market
movement*, and it passes as exactly that: late status changes are a third,
partly-independent source of open→close total movement.

What this addendum establishes is that **the movement is not informative about
outcomes.** The market moves on late outs, moves slightly too far, and the
residual is inside the vig. That is a coherent picture and it is consistent
with Hypothesis A having failed: the market prices injuries correctly — if
anything, marginally over-correctly.

## Disposition — the prereg's own language was right

§9 already stated B "is NOT a tradable edge as it stands" and that converting it
to P&L is "a latency question, not a research one." This addendum sharpens that:
**it is not even a latency question**, because the upper bound available to an
infinitely fast trader is −2.38%.

B stands as a decomposition result. Nothing is traded on it. The
`PREREG_move_injury_combined` extension should be read in light of this: adding
LATE to a movement model may improve the *movement* forecast without improving
the *outcome* forecast, and those are now known to be different things here.

## Series note

Three signals, three economic checks, one pattern: **CLV and P&L are different
endpoints and this program's signals separate them sharply.**

| signal | CLV | outcome P&L |
|---|---|---|
| MOVE_COMBINED | +1.337 pts, t = +16.42 | +2.02%, CI **includes 0** |
| injury B | +0.775 pts, t = +7.93 | **−8.04%**, CI excludes 0 |
| cohesion | n/a (no line-movement claim) | −3.56% |

Only MOVE_COMBINED has an outcome P&L that is even positive, and its interval
still includes zero.
