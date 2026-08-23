# PREREG — one-pass variance audit: where does closing-total error dispersion
# genuinely differ, and does the Kalshi ladder track it?

**Written 2026-08-23, BEFORE any squared error is regressed.** One estimation
pass for stage 1; stage 2 runs only for stage-1 survivors and only on the
already-held Kalshi season. This deliberately REOPENS the dispersion lane in
its one legitimate remaining form: a fixed-list, multiplicity-corrected AUDIT,
not sequential hypothesis generation. Base rates from the nine prior variance
designs (all null) are acknowledged.

## 1. Why raw MAE/RMSE differences are not the target

Variance differences across game classes exist mechanically (possessions, OT
probability) and can be fully priced. A sportsbook total pays nothing for
variance knowledge; only ladder rungs do. The tradable object is therefore a
class where realized dispersion differs AND the ladder's implied dispersion
fails to track it. Stage 1 finds real heteroskedasticity; stage 2 checks
ladder tracking. Only a stage-2 failure is an edge candidate.

## 2. Stage 1 — the fixed conditioner list (12, named now, no additions)

Target: `e = total - closing_total`; test statistic: OLS of `e^2` on the
conditioner (continuous standardized; binary as dummy), development seasons
(<= 2023) where the conditioner exists; permutation inference (within-season,
2,000 reps) on each; **Benjamini-Hochberg at q = 0.10 across the 12**.
Survivors require holdout (2024-25 + 2025-26 pooled) SAME SIGN.

| # | conditioner | type | expectation |
|---|---|---|---|
| 1 | closing total level | cont | POSITIVE CONTROL — must hit or the screen is underpowered |
| 2 | \|closing spread\| | cont | positive control (OT mixture) |
| 3 | prior-only pace sum (expanding, both teams >= 10 prior) | cont | likely duplicates #1 |
| 4 | either team on a back-to-back | bin | open |
| 5 | days into season (fraction) | cont | open |
| 6 | weekend game | bin | open |
| 7 | final 7 days of season | bin | open |
| 8 | walk-forward NC team involved (frozen -5.409 rule) | bin | open |
| 9 | \|MOVE_COMBINED_OOS\| | cont | open (does predicted movement mark uncertain games?) |
| 10 | N_LATE injury count (2020+ subsample) | cont | open |
| 11 | CrewShock magnitude \|.\| (where >= min prior) | cont | open |
| 12 | open->close total movement \|tmove\| | cont | knowable at close; open |

No interactions, no quantile re-cuts, no second list. MAE (|e|) reported
alongside e^2 for description; e^2 is the decision statistic.

## 3. Stage 2 — ladder tracking, survivors only

For each stage-1 survivor: on the Kalshi season (2025-26 through 12-22), does
the closing ladder's implied sd (from the rung distribution) differ across the
class the same way realized dispersion does? PASS (tracked) closes the
conditioner; FAIL (ladder width flat while realized dispersion differs) is an
edge CANDIDATE and gets its own follow-up pre-registration before any P&L
arithmetic. One partial season; power stated with the result.

## 4. Prohibited

- adding, splitting, or re-cutting conditioners after seeing stage 1
- promoting a stage-1 hit without stage 2
- treating positive controls (#1-3) as findings
- any P&L computation inside this document
