# Per-strategy profitability before 2025-26 (2026-10-07)

**Basis: sportsbook −110, $100 flat. NOT taker, NOT maker.** Kalshi books exist
only for 2025-26, so no taker replay is possible for any earlier season — a
taker figure needs an executable ask and there isn't one. Labelled on its face
per the standing rule.

Seasons 2017-18 … 2024-25 (the file has no 2019-20). final7 uses the window
reconciled against `monitor_season_pnl.py` (`days_left <= 7`, eight calendar
days).

## CrewShock — bet OVER at the close, threshold 0.8682

| season | bets | hit% | P&L | ROI |
|---|---|---|---|---|
| 2017-18 | 92 | 46.74% | −$991 | −10.77% |
| 2018-19 | 216 | 55.09% | +$1,118 | +5.18% |
| 2020-21 | 141 | 53.19% | +$218 | +1.55% |
| 2021-22 | 205 | 59.02% | +$2,600 | +12.68% |
| 2022-23 | 194 | 57.73% | +$1,982 | +10.22% |
| 2023-24 | 138 | 52.90% | +$136 | +0.99% |
| 2024-25 | 166 | 59.64% | +$2,300 | +13.86% |
| **TOTAL** | **1,152** | **55.73%** | **+$7,364** | **+6.39%** |

z = **+2.29**, ROI 95% CI **[+0.92%, +11.86%]** — excludes 0. 6/7 seasons positive.

## final7 — bet OVER every game in the window

| season | bets | hit% | P&L | ROI |
|---|---|---|---|---|
| 2017-18 | 62 | 58.06% | +$673 | +10.85% |
| 2018-19 | 62 | 56.45% | +$482 | +7.77% |
| 2020-21 | 68 | 47.06% | −$691 | −10.16% |
| 2021-22 | 63 | 53.97% | +$191 | +3.03% |
| 2022-23 | 67 | 59.70% | +$936 | +13.98% |
| 2023-24 | 69 | 65.22% | +$1,691 | +24.51% |
| 2024-25 | 67 | 59.70% | +$936 | +13.98% |
| **TOTAL** | **458** | **57.21%** | **+$4,218** | **+9.21%** |

z = **+2.09**, ROI 95% CI **[+0.86%, +18.38%]** — excludes 0. 6/7 seasons positive.

## MOVE_COMBINED — |m| ≥ 1.0, bet the sign, settles vs the OPENER

| season | bets | hit% | P&L | ROI |
|---|---|---|---|---|
| 2021-22 | 422 | 54.98% | +$2,091 | +4.95% |
| 2022-23 | 369 | 48.24% | −$2,918 | −7.91% |
| 2023-24 | 327 | 55.96% | +$2,236 | +6.84% |
| 2024-25 | 335 | 54.33% | +$1,245 | +3.72% |
| **TOTAL** | **1,453** | **53.34%** | **+$2,655** | **+1.83%** |

z = **+0.73**, ROI 95% CI **[−2.91%, +6.69%]** — **includes 0**. 3/4 seasons
positive. Starts 2021-22 because `MOVE_COMBINED_OOS` is NaN for the 2017-18
burn-in folds and the first joint season.

## PaceGap — not reconstructed

Its signal is `E_pace` from the frozen engine and no per-game historical export
exists; rebuilding it means running `frozen_models` walk-forward. The published
figure is **pooled over 2023-2025 and cannot be split** to exclude 2025-26:
n = 3,480, hit 52.59%, ROI +0.39%, CI [50.93%, 54.25%].

## Internal consistency check

| | pre-26 bets | + 2025-26 | = published 8-season |
|---|---|---|---|
| crewshock | 1,152 | 238 | **1,390** ✓ |
| final7 | 458 | 69 | **527** ✓ |

Both reconcile exactly, and final7's per-season counts match the published
table season by season — independent confirmation that the window
reconciliation is correct.

## Three caveats, and the first is the one that matters

**1. Dropping the worst season and then reading the significance is not valid.**
Excluding 2025-26 moves crewshock from +4.66% to +6.39% and final7 from +8.68%
to +9.21%, and both ROI intervals go from *including* zero to *excluding* it.
That improvement is the mechanical consequence of removing the season that
hurt, chosen **because** it hurt. The z of +2.29 and +2.09 are post-hoc and
should not be treated as evidence of an edge. The honest use of this table is to
ask whether 2025-26 looks anomalous — not to form an expectation.

**2. −110 overstates slightly.** 53% of totals are not at −110 and the juice
skews against the bettor; the measured hurdle is 1.12 pts of line error against
the 1.089 that −110 implies. In hit-rate terms the bar moves from 52.381% to
about 52.45% — small.

**3. The rung-vs-line translation is the big one.** A −110 wager settles against
the **line**; Kalshi settles a **rung**. The 2025-26 taker replay measured the
rung hit rate running **5–10pp below** the line hit rate (crewshock 43.60% vs
49.29%, final7 44.93% vs 55.07%), because for an OVER the max-edge rung sits
above the line. None of the ROIs above survive that translation intact.

## The uncomfortable shape of the evidence

- The seasons where the strategies look good — 2017-18 to 2024-25 — have **no
  Kalshi books**, so they can never be priced as a taker.
- The one season with Kalshi books — 2025-26 — is the season the strategies did
  **badly** (crewshock 49.29% against an assumed 54.21%, the season
  `MONITOR_SEASON_PNL.md` flags for `b_fouls` 0.4775 vs a prior range of
  0.79–1.36).

Those two facts cannot be reconciled with existing data. Only forward
collection of Kalshi books against live signals resolves it, which is what the
2026-27 shadow season is for.

Script: `profitability_pre_2025_26.py`.
