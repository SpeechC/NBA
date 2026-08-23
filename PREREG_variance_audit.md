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

---

## 5. RESULT — stage 1 run once, 2026-08-23. Survivors: NONE. Stage 2 moot.

| conditioner | n_dev | slope(e2) | perm p | holdout slope | RMSE by class |
|---|---|---|---|---|---|
| level (pos. control) | 7,162 | +12.7 | **0.0165** | +23.6 | 17.52 / 18.54 / 18.33 |
| \|spread\| (pos. control) | 7,162 | -2.6 | 0.66 | -0.6 | 18.45 / 17.88 / 17.98 |
| pace_prior | 6,222 | +11.5 | 0.076 | +17.2 | 17.85 / 17.86 / 18.46 |
| b2b_either | 7,162 | +7.3 | 0.22 | +14.3 | 17.99 / 18.43 |
| season_frac | 7,162 | +3.0 | 0.62 | -3.7 | |
| weekend | 7,162 | -0.8 | 0.89 | -0.5 | |
| final_week | 7,162 | +5.1 | 0.40 | +11.5 | 18.09 / 18.69 |
| nc_involved | 6,222 | +0.1 | 0.99 | -2.8 | 18.06 / 18.07 |
| \|MOVE_COMBINED\| | 3,145 | -13.9 | 0.12 | +18.4 | |
| n_late | 4,069 | +11.5 | 0.14 | -1.6 | |
| \|CrewShock\| | 7,162 | -1.4 | 0.81 | -9.3 | |
| \|tmove\| | 7,162 | +5.3 | 0.35 | -3.7 | |

BH q=0.10 over 12 requires min p <= 0.0083; the best cell (level, p=0.0165)
does not clear it. **No conditioner survives.**

### The two readings, both recorded

1. **The positive-control clause fires.** Level — the mechanically guaranteed
   heteroskedasticity — reaches only p=0.0165 and fails the correction. Per
   section 2's own standard, the screen is UNDERPOWERED for effects of the
   size that actually exist: the level terciles differ by ~1.0 point of RMSE
   (17.5 vs 18.5) and even that is barely visible in 7,162 games, because e^2
   inference inherits the enormous kurtosis of an sd-18 error.
2. **Nothing bigger exists.** Across every class of every conditioner, RMSE
   spans 17.5 to 18.7 — a +/-3% band around 18.1. No pregame-computable class
   among the 12 separates realized dispersion by more than ~1 point.

### Why the dispersion program kept failing, now visible in one table

Game-total error is dominated by irreducible within-game shooting noise
(sd ~18), which is nearly context-free. Conditioners move the small
predictable component; the noise floor swamps them. There was never much
conditional-variance structure to find — the nine prior nulls were the
correct answer, not missed detections.

The one confirmed variance-relevant structure — the OT mixture — is
consistent with this table rather than contradicted by it: a 5.24% one-sided
24-point jump adds ~31 to a variance of ~327 (about +4.6% RMSE), a TAIL-SHAPE
effect that RMSE barely sees. Dispersion structure in this market lives in
tail mass, not in second moments, and the tradable expression of it is
already specified in the second-line curve. That avenue remains the only one.
