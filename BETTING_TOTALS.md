# Totals and spreads on the complete file (overtime restored)

Closing totals now go over 50.08% of the time (47.95% on the overtime-free file), so totals are legitimately gradable for the first time. Same harness, same variants, both markets.

## Totals

|                     |    n |   model SD |   RMSE |   line RMSE |   incr coef |   incr t |   incr p |   win % |   ROI % |   z vs BE |   bucket 1 |   bucket 5 |   bucket spread |   CLV pts |
|:--------------------|-----:|-----------:|-------:|------------:|------------:|---------:|---------:|--------:|--------:|----------:|-----------:|-----------:|----------------:|----------:|
| paper6              | 5238 |      3.754 | 19.973 |      18.095 |      -0.089 |   -1.219 |    0.223 |  50.203 |  -4.158 |    -3.132 |     50.193 |     51.838 |           1.644 |    -0.895 |
| paper13             | 5238 |      4.577 | 19.728 |      18.095 |      -0.042 |   -0.655 |    0.512 |  49.874 |  -4.786 |    -3.604 |     50.58  |     50.87  |           0.29  |    -0.895 |
| pace16              | 5238 |      5.166 | 19.544 |      18.095 |      -0.026 |   -0.436 |    0.663 |  49.719 |  -5.081 |    -3.827 |     52.805 |     48.936 |          -3.868 |    -0.889 |
| matchup             | 5238 |      6.414 | 19.217 |      18.095 |      -0.008 |   -0.138 |    0.89  |  50.261 |  -4.047 |    -3.048 |     51.934 |     50.58  |          -1.354 |    -0.823 |
| matchup+rest+travel | 5238 |      6.288 | 19.248 |      18.095 |      -0.049 |   -0.863 |    0.388 |  50.203 |  -4.158 |    -3.132 |     53.095 |     49.807 |          -3.288 |    -0.871 |


## Spreads

|                     |    n |   model SD |   RMSE |   line RMSE |   incr coef |   incr t |   incr p |   win % |   ROI % |   z vs BE |   bucket 1 |   bucket 5 |   bucket spread |   CLV pts |
|:--------------------|-----:|-----------:|-------:|------------:|------------:|---------:|---------:|--------:|--------:|----------:|-----------:|-----------:|----------------:|----------:|
| paper6              | 5238 |      2.189 | 14.704 |      13.402 |       0.086 |    0.973 |    0.33  |  49.252 |  -5.974 |    -4.489 |     50.826 |     48.494 |          -2.332 |    -0.617 |
| paper13             | 5238 |      2.135 | 14.697 |      13.402 |       0.085 |    0.934 |    0.35  |  49.407 |  -5.677 |    -4.266 |     48.202 |     47.425 |          -0.777 |    -0.638 |
| pace16              | 5238 |      1.82  | 14.767 |      13.402 |      -0.018 |   -0.173 |    0.863 |  49.446 |  -5.603 |    -4.21  |     51.02  |     49.271 |          -1.749 |    -0.637 |
| matchup             | 5238 |      2.966 | 14.482 |      13.402 |       0.182 |    2.6   |    0.009 |  49.543 |  -5.417 |    -4.071 |     48.202 |     49.757 |           1.555 |    -0.629 |
| matchup+rest+travel | 5238 |      3.07  | 14.432 |      13.402 |       0.211 |    3.088 |    0.002 |  50.165 |  -4.23  |    -3.179 |     48.202 |     50.632 |           2.43  |    -0.62  |


Break-even at -110 is 52.38%. `incr t` is the t-statistic on the model when actual is regressed on the closing line plus the model; |t| > 2 indicates information the line has not priced. `bucket 1/5` are over rates in the extreme quintiles of disagreement orthogonal to the line — a real edge shows a wide, monotone spread.

## Verdict

**Totals carry no information the closing line lacks.** Across all five variants the
incremental t-statistic sits between −1.22 and −0.14 — not one is close to
significant, and the coefficients are *negative*, i.e. the model's total, after
calibration, is if anything mildly contrarian noise. The model's total RMSE
(19.2–20.0) is worse than the closing line's 18.10 in every variant. Orthogonal
disagreement quintiles do not order consistently: the bucket spread is +1.6, +0.3,
−3.9, −1.4, −3.3 across variants, flipping sign, which is what pure noise looks
like. ROI runs −4.0% to −5.1% and CLV is −0.82 to −0.90 points, worse than on
spreads.

**Spreads remain the only market with a real signal**, and the finding survives the
restored data: the matchup model is significant (t = +2.60) and matchup+rest+travel
more so (t = +3.09, p = 0.002), with the only positive, monotone-ish bucket spreads
in the table (+1.6 and +2.4). Both are still unprofitable — ROI −5.4% and −4.2%,
CLV −0.62.

**This inverts the prior.** Totals were expected to be the easier target on the
reasoning that a combined scoring environment is easier to forecast than a
difference. The data says the opposite, and the reason is visible in the RMSE
column: the market's own total error (18.10) is larger than its margin error
(13.40), because team scores within a game are positively correlated and the sum
inherits that shared variance while the difference cancels it. Totals are the
harder quantity, and the model has less to add there, not more.

The order to test them in should therefore have been spreads first. That is now
done on complete data, and the conclusion from the overtime-free file is unchanged:
opponent context produces genuine incremental information against the spread, at
roughly a tenth the magnitude required to clear the vig.
