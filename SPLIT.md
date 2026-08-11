# The train / holdout contract

```
DEVELOPMENT   2017-18 .. 2023-24    5,976 scored games   2018-02-22 .. 2024-04-14
HOLDOUT       2024-25, 2025-26      2,207 scored games   2024-10-30 .. 2026-04-12
```

Panel begins **2017-12-06**; total 8,696 games, 8,183 of them scored.

Fixed 2026-08-11 and enforced in [`data_split.py`](data_split.py):

```python
import data_split as ds
dev, ho = ds.split(panel)
ds.assert_no_holdout(frame, what="threshold search")   # guard a selection step
```

## Why the panel starts in December, not at the October tip-off

Three burn-ins sit in front of the first scored game. Two are unavoidable, one
was waste.

| stage | cost | earliest game | avoidable? |
|---|---|---|---|
| lagged box-score features (6 games per team) | ~90 games | **2017-10-25** | **no** — hard floor |
| score model → `dis_open` (`SCORE_MIN`) | ~150 games | 2017-11-22 | only by accepting noise |
| calibration → `dis_open` (`CAL_MIN`) | ~100 games | **2017-12-06** | only by accepting noise |
| ridge walk-forward (`min_train=500`) | 500 games | **2018-02-22** | no — it is the training window |

**The season opener can never be in the panel.** `dis_open` is a walk-forward
model output — the calibrated score model's total minus the opening total — and
2017-18 is the first season in the data. There is nothing earlier to train on.
The lagged features alone rule out anything before 2017-10-25.

The 500-game ridge window is not a loss: those games **are** used, as the initial
training set. They simply have no out-of-sample prediction, which is what
walk-forward means.

### What was actually waste

`movement_full_games.csv` was written after **three** stacked drops, the last of
which was `pred_move` — an XGBoost column that **specs A and D never use**, since
they run their own ridge walk-forward. Paying its 500-game burn-in cost the panel
its entire front end. The file is now written before that drop, with `pred_move`
retained as a NaN-able column.

Combined with the reduced `SCORE_MIN`/`CAL_MIN`, the panel went
**7,335 → 8,696 games** and its start moved **2019-01-01 → 2017-12-06**.

## Why the boundary is a date, not a season label

`SPLIT_DATE = 2024-07-01`. Matching season strings against
`("2024-2025", "2025-2026")` — what `run_holdout.py` originally did — is wrong.
The panel carries ten season labels, including three In-Season Tournament ones
whose strings match neither literal, so **6 holdout games** were being filed as
development. Harmless here (none clears the threshold), but silent. A date
boundary cannot make that error.

## The rules

- **Selection happens on development only.** `assert_no_holdout()` makes
  violations loud.
- **The holdout is read, never fitted on.** Walk-forward training may include
  earlier holdout games when predicting later ones — that is the expanding
  window, not selection. What is forbidden is *choosing* anything by looking at
  holdout performance.
- **Every holdout result names its seasons**, separately and pooled
  ([PREREGISTRATION.md](PREREGISTRATION.md)).

## Guard against source drift

```bash
python check_data_source.py
```

`prepare_data.CSV` and `movement_full_games.csv` must cover the same era. When
the former pointed at the file ending 2024-06-17 while the latter had been
rebuilt from the 2017-2026 export, the join still succeeded — it filled **every
lagged feature with NaN for all 2,207 holdout games**, and `dropna` deleted them.
The run reported a clean panel ending 2024-04-14 and raised nothing. A ~60-day
gap is normal (the box-score file includes playoffs, the movement file does not).

## What the burn-in reduction cost

This is a genuine trade, not a free win. A shorter burn-in means the score model's
early predictions train on ~150 games instead of ~750, so **`dis_open` is
noisier**. Noise in a regressor attenuates the ridge and compresses the prediction
distribution, so **fewer games clear a fixed threshold**:

| spec A, thr 1.25 | before | after |
|---|---|---|
| dev bets | 820 | **453** |
| dev CLV | +1.784 | **+2.000** |
| dev win % | 53.54 | 55.41 |
| holdout bets | 442 | **345** |

Fewer bets, higher CLV per bet. **The threshold is now doing more selecting than
it was when frozen**, which is worth remembering before reading the ladder below
as if 1.25 meant the same thing it used to.

⚠ Anyone who prefers the old behaviour should raise `SCORE_MIN`/`CAL_MIN` back to
1500/300 rather than move the threshold — the threshold is pre-registered.

## Anchor vintages

Feature sets and estimator are **unchanged**. `models_frozen.BACKTEST` keeps the
original as the historical record; `BACKTEST_CURRENT` is today's. All 18 cells
verify exactly against `BACKTEST_CURRENT`.

| spec | thr | frozen | current |
|---|---|---|---|
| A | 1.25 | +3.18 | **+5.78** |
| A | 1.50 | +5.51 | +0.89 |
| D | 1.25 | +3.13 | **+3.41** |
| D | 2.00 | +20.36 | +37.88 |

The thin cells (n=36–38 at threshold 2.00) should be ignored entirely.

## Holdout results

Spec A, threshold 1.25:

| set | n | CLV | 95% CI | beat close | win % | ROI −110 | ROI −105 |
|---|---|---|---|---|---|---|---|
| DEV 2018-2024 | 453 | +2.000 | [1.68, 2.32] | 67.33% | 55.41% | +5.78 | +8.18 |
| HO 2024-25 | 179 | +1.975 | [1.47, 2.48] | 72.07% | 46.93% | −10.41 | −8.38 |
| HO 2025-26 | 166 | +1.771 | [1.22, 2.32] | 68.07% | 53.61% | +2.35 | +4.68 |
| **HO pooled** | **345** | **+1.877** | **[1.504, 2.249]** | **70.14%** | **50.14%** | **−4.27** | **−2.10** |

Spec D pooled at 1.25: CLV +1.670 [1.28, 2.06], win 49.25%, ROI −5.97.

**The pre-registered verdict still PASSES**: pooled CLV +1.877 clears the +1.2
bar, the CI excludes zero, and both seasons agree in sign (+1.975, +1.771). CLV is
*higher* than the +1.740 measured on the previous vintage.

⚠ **And the win rate got worse — 50.14% against 51.58% before.** The CLV/win-rate
divergence flagged in [FINDINGS_LATE.md](FINDINGS_LATE.md) §6 has therefore
**widened, not closed**: +1.877 CLV implies roughly 57.2% by the measured
conversion, and the holdout delivered 50.14%. Extending the panel back to 2017
bought more of the metric that was already passing and none of the one that
was already failing. That is the central unresolved problem in this project, and
nothing in this change touches it.
