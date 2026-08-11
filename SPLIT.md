# The train / holdout contract

```
DEVELOPMENT   2017-18 .. 2023-24    4,582 scored games   2019-03-24 .. 2024-04-14
HOLDOUT       2024-25, 2025-26      2,207 scored games   2024-10-30 .. 2026-04-12
```

Fixed 2026-08-11 and enforced in [`data_split.py`](data_split.py). Import it
rather than filtering by hand:

```python
import data_split as ds
dev, ho = ds.split(panel)          # the split
dev      = ds.dev(panel)           # development only
ds.assert_no_holdout(frame, what="threshold search")   # guard a selection step
```

## Why the boundary is a date, not a season label

`SPLIT_DATE = 2024-07-01`. The obvious implementation — matching season strings
against `("2024-2025", "2025-2026")` — is what `run_holdout.py` originally did,
and it is wrong. The panel carries **ten** distinct season labels, including:

```
NBA 2023 In-Season Tournament     4 games   2023-12-04 .. 2023-12-05
NBA 2024 In-Season Tournament     2 games   2024-12-10 .. 2024-12-11
NBA 2025 In-Season Tournament     4 games   2025-12-09 .. 2025-12-10
```

A label filter puts the 2024 and 2025 tournament games — **6 holdout games** — on
the development side, because their labels match neither literal. The leak is
small and in the harmless direction here (none clears the 1.25 threshold, so no
published number changes), but it is exactly the kind of error that does not
announce itself. A date boundary cannot make it.

## The rules

- **Selection happens on development only.** Features, thresholds, estimator,
  hyperparameters. `assert_no_holdout()` exists to make violations loud.
- **The holdout is read, never fitted on.** Walk-forward training may include
  earlier holdout games when predicting later holdout games — that is the normal
  expanding window and is not selection. What is forbidden is *choosing* anything
  by looking at holdout performance.
- **Every holdout result names its seasons**, separately and pooled. This is
  pre-committed in [PREREGISTRATION.md](PREREGISTRATION.md) so that a good season
  cannot be reported alone.

## Two data-source bugs this codifies against

**1. The stale odds pointer.** `prepare_data.CSV` pointed at `dfMaster_OT.csv`
(ends 2024-06-17) while `movement_full_games.csv` had been regenerated from
`dfMaster_OT_2017-2026.csv`. The join on game id still succeeded — it just filled
**every lagged form feature with NaN for all 2,207 holdout games**, and the
downstream `dropna` deleted them. The run looked clean and reported a panel ending
2024-04-14. Nothing raised.

The pointer had been corrected at runtime in a previous session and never
committed, so the repo silently regressed. It is now committed, and
[`check_data_source.py`](check_data_source.py) detects the condition:

```bash
python check_data_source.py
```

Run it before any backtest. A 60-day gap is normal — the box-score file includes
playoffs, the movement file is regular season only.

**2. `verify_frozen.py` scoring the whole panel.** It compared a dev+holdout ROI
against a dev-only anchor, so adding holdout data would have looked like spec
drift. It now scores development only.

## Anchor vintages

The frozen **feature sets and estimator are unchanged**. The input panel was
rebuilt from the newer export, which moves the reference ROI slightly:

| spec | thr | frozen vintage | current | drift |
|---|---|---|---|---|
| A | 1.25 | +3.18 | **+2.21** | −0.97 |
| A | 2.00 | +16.82 | +12.62 | −4.20 |
| D | 1.25 | +3.13 | **+2.05** | −1.08 |
| D | 2.00 | +20.36 | +18.82 | −1.54 |

Drift is small where n is large and grows where n is thin, which is what a
handful of changed games looks like. `models_frozen.BACKTEST` keeps the original
as the historical record; `BACKTEST_CURRENT` is what the same specs produce
today. All 18 cells verify exactly against `BACKTEST_CURRENT`.

⚠ **The pre-registered anchor was +1.844 CLV, computed on the old vintage.** The
holdout PASS threshold (pooled CLV ≥ +1.2) was met at **+1.740**, so the verdict
is unaffected — but the anchor and the result come from marginally different
panels, and the comparison should be read as approximate.

## Holdout results under the corrected split

Spec A, threshold 1.25 — identical to [HOLDOUT_RESULT.md](HOLDOUT_RESULT.md),
confirming the tournament-game reclassification changes nothing:

| set | n | CLV | 95% CI | beat close | win % | ROI −110 | ROI −105 |
|---|---|---|---|---|---|---|---|
| DEV 2019-2024 | 820 | +1.784 | [1.55, 2.02] | 65.98% | 53.54% | +2.21 | +4.52 |
| HO 2024-25 | 222 | +1.718 | [1.27, 2.17] | 69.37% | 49.55% | −5.41 | −3.26 |
| HO 2025-26 | 220 | +1.761 | [1.28, 2.25] | 67.73% | 53.64% | +2.40 | +4.72 |
| **HO pooled** | **442** | **+1.740** | **[1.41, 2.07]** | **68.55%** | **51.58%** | **−1.52** | **+0.71** |

Spec D pooled at the same threshold: CLV +1.666 [1.33, 2.01], win 49.88%,
ROI −4.78. **A and D remain close on CLV; A is ahead on realised win rate in the
holdout**, consistent with the two specs sharing essentially one signal.

The CLV/win-rate discrepancy noted in [FINDINGS_LATE.md](FINDINGS_LATE.md) §6 is
unchanged by any of this: +1.740 CLV implies ~56.7%, the holdout delivered 51.58%.
