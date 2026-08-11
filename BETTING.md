# Walk-forward test: the paper's score model vs the closing spread

Totals are excluded because overtime games are missing from the source file; see README. Spreads and moneylines are unaffected.

Walk-forward games graded: **4814** (2018-12-29 to 2024-04-14)

## 1. Margin accuracy, out of sample

|                          |   RMSE |    MAE |
|:-------------------------|-------:|-------:|
| closing line             | 13.675 | 10.601 |
| model (calibrated)       | 15.056 | 12.071 |
| naive 4-game scoring avg | 16.716 | 13.293 |

## 2. Does the model add information the closing line lacks?

Regression of actual margin on the closing line and the model:

|               |    coef |   std err |       t |      p |
|:--------------|--------:|----------:|--------:|-------:|
| intercept     | -0.0906 |    0.2592 | -0.3495 | 0.7267 |
| market margin |  0.8956 |    0.0278 | 32.2126 | 0      |
| model margin  |  0.1293 |    0.0822 |  1.5735 | 0.1157 |


If the market has already priced everything the model knows, the **model margin** coefficient is 0 and the **market margin** coefficient is 1. Observed: model +0.1293 (t = 1.57, p = 0.116), market +0.8956.

## 3. Model-market disagreement vs outcome

Signal = calibrated model margin − closing market margin. Positive means the model likes the home team more than the market does.

| bucket   |    n |   home_cover_pct |   se |
|:---------|-----:|-----------------:|-----:|
| < -6     |  860 |            49.88 | 1.7  |
| -6 to -3 |  783 |            51.21 | 1.79 |
| -3 to +3 | 1486 |            52.22 | 1.3  |
| +3 to +6 |  625 |            48.8  | 2    |
| > +6     |  986 |            45.23 | 1.59 |


A monotone rise in home cover % across buckets is what a real edge looks like.


**Diagnostic — what the signal actually measures**

|                                   |   value |
|:----------------------------------|--------:|
| SD of calibrated model margin     |   2.531 |
| SD of closing market margin       |   7.479 |
| corr(model margin, market margin) |   0.322 |
| corr(signal, market margin)       |  -0.941 |


The model's margin varies over a range only 34% as wide as the market's, so the difference between them is dominated by the market number: corr(signal, market margin) = -0.94. Bucketing on the signal therefore sorts games mostly by *how big a favourite the home team is*, not by how much the model disagrees. That is why the bucket table trends opposite to the regression coefficient in section 2 — the buckets are picking up favourite/underdog effects. Section 2 is the trustworthy test, because it holds the market line fixed.


**Corrected test — disagreement orthogonal to the line, quintiles**

| obucket        |   n |   home_cover_pct |   se |
|:---------------|----:|-----------------:|-----:|
| most anti-home | 948 |            49.37 | 1.62 |
| 2              | 948 |            48.73 | 1.62 |
| 3              | 948 |            50.63 | 1.62 |
| 4              | 948 |            50.42 | 1.62 |
| most pro-home  | 948 |            49.47 | 1.62 |


This is the version of the bucket test worth reading: it asks whether the part of the model's opinion that the line does *not* already contain predicts covers.

## 4. Betting the model's side, flat stakes at -110

|                        |    n |   win % |   ROI % |
|:-----------------------|-----:|--------:|--------:|
| all games              | 4740 |   48.61 |   -7.2  |
| signal bucket > +6     |  986 |   45.23 |  -13.65 |
| signal bucket +3 to +6 |  625 |   48.8  |   -6.84 |
| signal bucket < -6     |  860 |   50.12 |   -4.32 |
| signal bucket -6 to -3 |  783 |   48.79 |   -6.86 |
| |signal| > 3           | 3254 |   48.06 |   -8.24 |
| |signal| > 6           | 1846 |   47.51 |   -9.3  |


Break-even at -110 is **52.38%**. Overall 48.61% on n = 4740 (z = -5.20 vs break-even), ROI -7.20%.

## 5. By season

| season                        |    n |   win_pct |   ROI % |
|:------------------------------|-----:|----------:|--------:|
| NBA 2018-2019 Regular Season  |  653 |     47.63 |   -9.08 |
| NBA 2020-2021 Regular Season  |  947 |     47.62 |   -9.08 |
| NBA 2021-2022 Regular Season  | 1086 |     49.72 |   -5.07 |
| NBA 2022-2023 Regular Season  | 1064 |     50.38 |   -3.83 |
| NBA 2023 In-Season Tournament |    2 |     50    |   -4.55 |
| NBA 2023-2024 Regular Season  |  988 |     47.06 |  -10.15 |

## 6. Closing line value

Betting the model's side at the **opening** number, the line then moved in our favour by **-0.612** points on average (n = 4740, 31.4% of bets got positive CLV). Sustained positive CLV is the strongest single sign of a real edge.

## 7. Moneyline

Model win probability from the calibrated margin with sigma = 15.17 points, against the de-vigged market probability.

|             |    n |   win % |   ROI % |
|:------------|-----:|--------:|--------:|
| |edge| > 0% | 4710 |   33.18 |   -6.1  |
| |edge| > 2% | 4356 |   32.02 |   -6.09 |
| |edge| > 5% | 3860 |   30.23 |   -6.19 |


**Calibration of the model's home-win probability**

| decile         |   n |   predicted |   actual |
|:---------------|----:|------------:|---------:|
| (0.185, 0.478] | 471 |        44.1 |     46.3 |
| (0.478, 0.504] | 471 |        49.3 |     50.5 |
| (0.504, 0.525] | 471 |        51.5 |     51   |
| (0.525, 0.542] | 471 |        53.3 |     52.4 |
| (0.542, 0.557] | 471 |        55   |     50.5 |
| (0.557, 0.571] | 471 |        56.4 |     58   |
| (0.571, 0.587] | 471 |        57.9 |     59.7 |
| (0.587, 0.607] | 471 |        59.7 |     63.5 |
| (0.607, 0.636] | 471 |        62   |     63.5 |
| (0.636, 0.861] | 471 |        67   |     63.3 |
