# PREREG — TIP TIME AND HOURS OF REST

Written 2026-08-26, BEFORE any outcome variable was touched. Only the
schedule-structure checks in §2 were run first (`tip_time_structure.py`); they
read tip-off times and the vendor rest label only — no score, no total, no
`dev`.

## 0. The claim being tested

This is the **CrewShock template**, applied to the schedule instead of the
officials. CrewShock's finding was: *the market conditions on a coarse,
published variable and ignores the fine variation inside it.*

The NBA rest variable is published, universally displayed, and **coarse**: the
vendor's own column is `TEAM REST DAYS`, a categorical label (`B2B`, `1`, `2`,
`3+`). Every screen a bettor sees reports rest in days. But the physically
relevant quantity is **hours of actual recovery**, and two games both labelled
"B2B" can differ by seven hours depending on the tip times the schedule-maker
assigned months earlier.

Tip time is exogenous to team strength, fixed far in advance, non-team, and
has a mechanical channel to scoring through fatigue and shooting efficiency.

**Hypothesis: the closing line prices rest in DAYS and leaves the HOURS
variation inside each day-stratum unpriced.**

## 1. Data

- Outcomes and rest labels: `C:\NBA2\dfMaster_OT_2017-2026.csv` via
  `read_master()`. **Source file never modified.**
- Tip-off times: ESPN dated scoreboard, fetched to `tipoffs_espn.csv`
  (`fetch_tipoffs.py`, 12,067 games). Event times are UTC; arena-local time is
  derived with the US/Canada DST rule, **Arizona exempted**.
- Arena coordinates and standard UTC offsets: `rest_travel.ARENAS`
  (pre-existing reference data).

Split follows `CLOSING_REFEREE.md`, as in `PREREG_quote_path`:

```
development   2017-18 .. 2023-24  (incl. IST 2023)
holdout       2024-25, 2025-26    (incl. IST 2024, IST 2025)
```

## 2. Stage-0 gates — RESULTS IN HAND (schedule data only)

| gate | result | verdict |
|---|---|---|
| CONTENT — join rate to master | **9,676 / 9,676 = 100.00%** | **PASS** |
| CONTENT — `hours_gap` tracks the vendor rest label | 26.3 / 51.0 / 75.3 / 133.6 h for rest_days 0/1/2/3 | **PASS** |
| RANGE — `tip_hour` local | 12.00 – 22.00, 0 outside [10,24) | **PASS** |
| RANGE — `hours_gap` | min 21.0 h, 0 below 15 h | **PASS** |
| ERA — join rate by season | 1.00× across all 11 seasons | **PASS** |
| ERA — mean tip hour by season | 18.68 – 19.27, sd ≈ 1.4 throughout | **PASS** |

### A correction to my own gate metric

The era gate reports `max/min` ratios. For the *late-tip share* that produced
"4,878,048×" — an artefact of dividing by a near-zero share, not a real era
failure. **For shares near zero the ratio test is inappropriate and
percentage-point differences are used instead.** Late-tip share ranges 0.0% to
0.5% across seasons — a 0.5pp spread, stable. Early-tip share ranges 6.1% to
7.8% in full seasons (the 0.0% is IST 2025, n = 64).

### A construct this killed before it was tested

I had proposed "late West-Coast tips" as a circadian variable. **In arena-local
terms it does not exist**: maximum local tip is 22:00 and only 0.0–0.5% of
games start at or after 21:00. A 10:30pm ET game is a 7:30pm *local* game. The
late-tip construct is dropped — it has no variation to test.

What survives is the **visiting team's body clock**, which does have real
variation and is the mechanism behind the "Voulgaris visitor effect":

```
body_hour_away = tip_hour_local + (away_std_offset − home_std_offset)
```

A Pacific team at a 19:00 Eastern tip is playing at 16:00 body time.

### The variation the primary test actually has to work with

| stratum | n | IQR | p5–p95 spread |
|---|---|---|---|
| rest_days = 0 (B2B) | 3,424 | 24.0 – 25.0 h | **7.0 h** |
| rest_days = 1 | 11,942 | 47.0 – 49.0 h | 10.5 h |
| rest_days = 2 | 2,813 | 71.0 – 73.0 h | 10.5 h |
| rest_days = 3+ | 843 | 96.0 – 191.5 h | 122.0 h |

Stated plainly as a **power risk, in advance**: within the strata where fatigue
actually bites (0 and 1), the usable variation is 7–10 hours. This is a
narrow-variation test and may be underpowered regardless of whether the effect
is real. §7 fixes what will be reported if so.

The 3+ bucket has enormous hidden variation but is physiologically the least
plausible place for a recovery effect, and conflates rest with mid-season
breaks. **The primary is restricted to rest_days ∈ {0, 1, 2}**, fixed here.

## 3. Construction

Per team-game: `hours_gap` = hours between this tip and that team's previous
tip, within season. Per game:

```
H_sum   = hours_gap_home + hours_gap_away          (primary regressor)
H_diff  = hours_gap_home − hours_gap_away          (secondary, home-side)
body_a  = tip_hour_local + (off_away − off_home)   (secondary)
early   = 1[tip_hour_local < 17]                   (secondary)
```

Targets, as used throughout this program:

```
dev   = actual_total  − closing_total       (primary)
dev_s = actual_margin + closing_spread      (secondary, home-side)
```

**Controls, fixed here.** Every specification includes rest-day stratum dummies
for BOTH teams — the within-stratum contrast is the entire point — plus
`tz_shift` and `travel_km` from `rest_travel`. `hours_gap` is mechanically
entangled with westward travel (a team moving west gains clock hours), so
omitting the travel controls would test a confound rather than the hypothesis.

## 4. Predictions — fixed, one-sided

**PRIMARY P1.** More recovery hours → less fatigue → higher scoring, and the
closing total has not priced it.

```
dev ~ H_sum + rest-stratum dummies + tz_shift + travel_km
PREDICTED:  beta_H_sum > 0        (one-sided)
```

Pass requires **both**:
- **P1a** `beta_H_sum > 0` at within-season block-permutation p < 0.05
  one-sided (5,000 reps);
- **P1b** the §5 incremental bar.

**P1 FAILS** if `beta_H_sum ≤ 0` or the permutation p ≥ 0.05. On failure the
branch closes: no alternative strata, no re-introduction of the 3+ bucket, no
threshold search on hours, no switch of target from total to spread.

**SECONDARY P2** — `dev_s ~ H_diff + controls`, predicted > 0 (home side).
**SECONDARY P3** — `dev_s ~ body_a + controls`, predicted **> 0**: the later
the visitor's body clock reads relative to a normal tip, the worse the visitor,
the better the home margin.
**SECONDARY P4** — `dev ~ early + controls`, predicted **< 0** (afternoon games
score lower).

**P2–P4 cannot rescue P1.** If P1 fails the branch closes regardless.

## 5. Incremental test — the bar that decides it

As in `PREREG_quote_path` §5, significance alone is not a result. Fit on
development, score **once** on holdout:

```
model A (incumbent)   dev ~ rest dummies + tz_shift + travel_km
model B (candidate)   model A + H_sum
```

**Bar: model B's holdout out-of-sample R² exceeds model A's.**

## 6. Inference

- Within-season block permutation, 5,000 reps; `H_sum` permuted within season
  blocks. Naive OLS SEs reported but not relied on.
- Four pre-registered predictions are declared, so the phantom-book 95th
  percentile bar is reported for P1.
- No same-game outcome enters any regressor. Tip times are known months in
  advance; the rest label is a pregame column.

## 7. Detection burden and the underpowered case

The tradeable quantity, if P1 passes, is reported as a hit rate against the
−110 break-even of 52.38%, with required n from `n = 7.84·p(1−p)/edge²`.

**Stated in advance:** given 7–10 h of usable variation, a null here is
ambiguous between "no effect" and "too little variation to detect one." If P1
fails, the report will give the **minimum detectable effect** at the observed
variation and sample, and describe the result as *undetectable at this
variation* rather than as evidence of efficient pricing. That distinction is
fixed now so it cannot be chosen after seeing the answer.

## 8. Known limitations, stated in advance

- ESPN tip times are *scheduled* times. Actual tips run a few minutes late and
  broadcast overruns are not captured. This adds noise, not bias.
- `hours_gap` uses the previous game's *tip*, not its final buzzer. Game
  durations vary (overtime especially), so recovery time is measured with
  error of roughly ±20 minutes, more for OT games.
- The vendor rest label is more accurate than date arithmetic (see
  `rest_travel` docstring) but games removed from the file create itinerary
  holes; those rows carry NaN travel and drop from the controlled spec.
- Single vendor closing line.

---

# RESULT — run 2026-08-26. Verdict: **P1 FAILS. Branch closes.**

## Confirmatory run, exactly as pre-registered (`tip_time.py`)

Development n = 2,233 (see the coverage defect below); holdout n = 657.

| prediction | beta | t | perm p (1-sided) | verdict |
|---|---|---|---|---|
| **P1** `H_sum → dev` (predicted **> 0**) | **−0.00799** | −0.08 | 0.6785 | **FAIL — wrong sign** |
| P2 `H_diff → dev_s` (> 0) | −0.09414 | −0.58 | 1.0000 | null |
| P3 `body_a → dev_s` (> 0) | +0.08441 | +0.65 | 0.2541 | null |
| P4 `early → dev` (< 0) | −0.26832 | −0.18 | — | null |

§5 incremental, scored once on holdout: A (rest + travel) OOS R² −0.007973 vs
B (+`H_sum`) −0.008127, **B − A = −0.000154. A wins.**

**P1 fails on sign before any p-value is consulted**, and fails §5. Per §4 the
branch closes.

## Two execution defects, reported not substituted

**1 — Coverage.** `rest_travel` sets travel to NaN wherever the master's
itinerary has a hole. Requiring it on both sides left **54.8% per side and
n = 2,233 of 6,631** — a 66% loss to a *control*, the same stacked-attrition
pattern as the `tpa_s` episode.

**2 — Inference.** The pre-registered plain within-season permutation is
**invalid for a regressor mechanically correlated with the controls**:
permuting `H_sum` decorrelates it from `tz_shift`/`travel_km`, so the null
spread is understated. Observed perm sd 0.019 against a naive SE of ≈0.100 — a
5× disagreement. It shows most starkly in P2, where the permutation reports
p₂ = 0.0002 for a coefficient whose naive t is only −0.58. **The P2 permutation
p-value above is not trustworthy and is not interpreted.**

Neither defect is repaired in the confirmatory result. Both are addressed in a
labelled addendum (`tip_time_robust.py`) whose only effect is to make the null
**harder to reach**, never easier.

## Addendum — complete itinerary + Freedman-Lane (NOT confirmatory)

The ESPN schedule is complete (12,067 games, including those the master
dropped), so travel is rebuilt with **no holes: coverage 1.000 both sides,
n = 6,612**. Inference uses Freedman-Lane permutation of the control-residualised
target, whose null sd (0.0066) now agrees with the naive SE.

| prediction | beta | t | FL p (1-sided) |
|---|---|---|---|
| **P1** `H_sum → dev` (predicted > 0) | **−0.00319** | −0.29 | 0.2102 |
| P2 `H_diff → dev_s` | −0.01040 | −0.76 | 0.7944 |
| P3 `body_a → dev_s` | +0.02133 | +0.24 | 0.3999 |
| P4 `early → dev` | +0.72663 | +0.82 | 0.2076 |

**P1 is wrong-signed in both specifications.** Every secondary is null.

§5 on complete controls returns B − A = **+0.000354 ("B wins")**. This is
**not** a pass and is not reported as one: §4 requires P1a *and* P1b, P1a fails
on sign, and the gain is 3.5e-4 on a base where **both** models score negative
OOS R² — i.e. both are worse than predicting the holdout mean. Adding a
wrong-signed insignificant regressor moved a noise term.

## §7 — this is a WELL-POWERED null, and the escape clause does not apply

§7 fixed in advance that a null at narrow variation must be reported as
*undetectable*, not as efficient pricing. At the improved coverage that
qualification is **not** needed:

```
MDE (95%)   0.0129 pts/hour = 0.371 pts per 1 SD of H_sum (28.7h)
                            = 0.310 pts per DAY of extra recovery
observed    −0.0032 pts/hour = −0.077 pts per day
```

We can exclude, at 95%, a within-stratum recovery effect larger than **0.31
total points per day-equivalent of hours**. Stated precisely: this bounds the
*within* rest-day-bucket hours effect, not the across-bucket day effect, which
the stratum dummies absorb.

## What Stage 0 killed before it was tested

The proposed "late West-Coast tip" circadian variable **does not exist in
arena-local terms**: maximum local tip is 22:00 and only 0.0–0.5% of games
start at or after 21:00, because a 10:30pm ET game is a 7:30pm *local* game.
Dropped at §2 with no test run. Recorded because the intuition is a natural one
and will recur.

## Two plumbing bugs the guard caught

The first execution returned **0 rows** and printed a full slate of clean-looking
nulls. Cause: `gid` round-trips through CSV as int64 while the master keeps it
as a string, so index alignment silently produced all-NaN. A `JOIN FAILURE`
assertion was added that aborts when a key column falls below an expected floor;
it immediately caught a second, independent bug — `add_rest_travel` maps
`game_id` against the master's **native int64** `GAME-ID`, so casting it to
string beforehand yielded all-NaN travel.

**A void run that reports plausible nulls is the most dangerous failure mode in
this program.** The assertion is the mitigation and should be standard in new
tests.

## Disposition

Branch closes. No alternative strata, no re-introduction of the 3+ bucket, no
hours threshold search, no switch of target. The schedule-maker's fine
variation in recovery hours is **priced, or too small to matter, at a bound of
0.31 points per day.**

`hours_gap` and `tip_hour` are left in `tip_time_panel.csv` and the complete
no-hole travel features in `tip_time_robust.complete_travel()`; the latter are
a strict improvement over `rest_travel`'s hole-flagged version and are
available to any future test that needs travel controls.
