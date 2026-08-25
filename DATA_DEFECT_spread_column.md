# DATA DEFECT — four corrupt cells in CLOSING SPREAD_H

Found 2026-08-24 while decomposing the omnibus Mincer-Zarnowitz detection.

## The rows

| GAME-ID | date | matchup | OPENING SPREAD_H | **CLOSING SPREAD_H** | what the value actually is |
|---|---|---|---|---|---|
| 22200232 | 2022-11-18 | Utah v Phoenix | +1.5 | **-110.0** | the juice (ML -104/-108) |
| 22200385 | 2022-12-09 | Utah v Minnesota | -2.5 | **+112.0** | juice, sign-flipped |
| 22200457 | 2022-12-19 | New Orleans v Milwaukee | +1.5 | **+110.0** | juice |
| 22300027 | 2023-11-17 | Charlotte v Milwaukee | +7.5 | **+243.0** | the TOTAL, in the spread field |

The other |S| > 20 rows are GENUINE blowout lines (-20.5 to -24.5, moneylines
-2400 to -9000) and must not be filtered out.

## What they cost

The omnibus (FINDINGS_LATE.md s21) reported a Mincer-Zarnowitz spread slope of
**0.9368, chi2 = 13.01, p = 0.0015**, interpreted as "the line OVERREACTS — a
10-point favourite behaves like a 9.37-point favourite, so underdogs are
undervalued at the extremes," and sized at ~0.95 points ≈ 2.45pp at |S| = 15.

Removing these four cells:

| window | with | without |
|---|---|---|
| ALL | 0.9368 (t = -3.40) | **1.0043 (t = +0.22)** |
| development | 0.8926 (t = -4.89) | 0.9870 (t = -0.57) |
| holdout | 1.0404 (t = +1.15) | 1.0404 (unchanged) |
| 2022-23 | 0.5301 (t = -10.76) | 0.8715 (t = -2.31) |

Per season afterwards: 0.9404, 0.9968, 1.0287, 1.0200, 0.8715, 1.0438,
1.0528, 1.0292 — seven of eight within |t| < 1.2 of unity.

**The detection was four cells. The NBA closing spread is an unbiased forecast
of margin (slope 1.0043).** A price and a total leaked into a spread column and
produced a p = 0.0015 "market inefficiency" with a plausible-sounding
mechanism attached.

## Why it evaded everything

Leverage. OLS slope weights by squared deviation from the mean, so a single
point at pred = 112 against |pred| <= 24 everywhere else carries roughly
(112/7)^2 ~ 250x the influence of a typical game. Four such points moved the
pooled slope by 0.067 and manufactured a t of -3.40.

No content check would catch it: -110, 112 and 243 are all valid FLOATS, all
plausible values for SOME betting column, just not this one. The era-stability
gate would not catch it either — it is four rows, not a systematic era shift.

## The gate this adds

**RANGE gates on every market column, keyed to what the quantity can physically
be.** Not null-rate, not era stability — plausible RANGE:

    |spread|  <= 30      (largest genuine NBA line in 9,489 games is 24.5)
    total     in 150..300
    moneyline outside -100..100 excluded, |ML| <= 20000

and, because leverage is the mechanism, **any regression on a market column
must report its highest-leverage observations** before the coefficient is
believed.

## Scope of contamination

12+ scripts read `CLOSING SPREAD_H`. Any that regress on it, take its |value|,
or bucket by it are affected to some degree; effects on MEANS are tiny (4 of
9,489) but effects on SLOPES and on |S| BUCKETS can be large. `heavy_favs.py`
and `cond_variance.py` are the most exposed by name and should be re-checked.

MOVE_COMBINED uses OPENING SPREAD_H (clean in these rows) and totals, so the
frozen 2026-27 forward test is NOT affected. Verified: all four corrupt values
are in the CLOSING column; the OPENING values (+1.5, -2.5, +1.5, +7.5) are
normal.
