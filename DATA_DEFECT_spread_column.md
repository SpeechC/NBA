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

---

## UPDATE 2026-08-24 — the gate found two MORE, and they DO hit MOVE_COMBINED

Wiring the range gate into the loaders surfaced two cells I had not found by
hand, in a different column:

| GAME-ID | date | matchup | **OPENING TOTAL_H** | closing total | actual |
|---|---|---|---|---|---|
| 22200314 | 2022-11-30 | Boston v Miami | **109.5** | 225.0 | 255 |
| 22500967 | 2026-03-13 | Portland v Utah | **136.5** | 235.5 | 238 |

Both are a team total or half total written into the full-game opening total.

**This corrects what I said earlier.** I checked only `CLOSING SPREAD_H`, found
MOVE_COMBINED used `OPENING SPREAD_H`, and reported the forward test
unaffected. That was wrong: `OPENING TOTAL_H` is a MOVE_COMBINED feature, the
bet price, AND the definition of the target `tmove = ot_close - ot_open`.

As the model saw them:

```
22200314   tmove = +115.5     te_open = +145.5
22500967   tmove =  +99.0     te_open = +101.5
legitimate tmove range: -15.5 .. +19.5,  sd 3.18
```

Two rows inflated the TARGET's standard deviation by **11.44%** (3.175 ->
3.538) and sat 30+ sigma out. `te_open` feeds `hse`/`ase`, which feed 20-game
rolling means for both teams, so a +145 outlier contaminates tens of downstream
feature rows, not two.

### Remediation

Range gates now applied at load in `prepare_data.sanitize_market()` /
`read_master()`, and wired into `opening_line_error_decomposition.load()`,
`move_combined_live._load_master()`, `dis_open_live.build_panel()` and the
inlined copy in `MOVE_COMBINED_2027.py`. Values are scrubbed to NaN; rows are
NOT dropped and **the source CSV is never modified**.

Latent artifact re-frozen on gated data BEFORE the season begins — a data
repair, not a specification change, and permissible only because 2026-27 has
not started:

```
                 K    n_train    in-sample R2
before gate     17      8,426        +0.0307
after  gate     17      8,413        +0.0386
max |beta change| across 18 coefficients: 0.0453
```

K is unchanged at 17, so the PCA structure is stable; the coefficients move
modestly and the in-sample fit improves, consistent with removing 30-sigma
target outliers. `move_combined_latent_2027.pkl.PRE_GATE` is kept for audit.

### The generalised lesson

Three gate types are now needed, and each catches what the others cannot:

| gate | catches | blind to |
|---|---|---|
| CONTENT (null rate, validity) | missing or malformed values | valid floats in the wrong column |
| ERA STABILITY (rows per unit) | systematic under-ingestion | a handful of bad rows |
| **RANGE (physical plausibility)** | **wrong-column leakage** | subtle within-range errors |

And: **a regression on a market column must report its highest-leverage
observations before its coefficient is believed.**
