# Pace/efficiency extension vs the closing spread

Same paper-faithful recipe (lag-4 designed features, ensemble two-stage selection, XGBoost), walk-forward, graded against the closing line. `matchup` additionally feeds each team's model the opponent's lagged pace/efficiency — the extension the paper lists as future work.

## Ensemble feature ranking, 16 variables (initial training window)

|      |   MARS |   XGBoost |   SGB |   Average Rank |
|:-----|-------:|----------:|------:|---------------:|
| OEFF |      2 |         1 |     1 |           1.33 |
| ORB  |      1 |         7 |     4 |           4    |
| PACE |      8 |         3 |     2 |           4.33 |
| 3PA  |      6 |         4 |     3 |           4.33 |
| BLK  |      4 |         5 |     6 |           5    |
| AST  |      5 |         6 |     7 |           6    |
| 2P%  |     16 |         2 |     5 |           7.67 |
| STL  |      2 |        16 |    10 |           9.33 |
| FT%  |      7 |        13 |     9 |           9.67 |
| PF   |      9 |        12 |    11 |          10.67 |
| 3P%  |     10 |         9 |    15 |          11.33 |
| DEFF |     16 |         8 |    13 |          12.33 |
| FTA  |     16 |        14 |     8 |          12.67 |
| TOV  |     16 |        10 |    14 |          13.33 |
| DRB  |     16 |        15 |    12 |          14.33 |
| 2PA  |     16 |        11 |    16 |          14.33 |


Two-stage selection keeps 7: **OEFF, ORB, PACE, 3PA, BLK, AST, 2P%**

## Variant comparison

|          |    n |   model SD |   margin RMSE |   incr coef |   incr t |   incr p |   win % |   ROI % |   z vs BE |   CLV pts |
|:---------|-----:|-----------:|--------------:|------------:|---------:|---------:|--------:|--------:|----------:|----------:|
| paper6   | 4801 |      2.449 |        15.064 |       0.124 |    1.455 |    0.146 |  48.001 |  -8.362 |    -6.023 |    -0.615 |
| paper13  | 4801 |      2.23  |        15.059 |       0.1   |    1.069 |    0.285 |  48.339 |  -7.716 |    -5.557 |    -0.645 |
| pace16   | 4801 |      2.042 |        15.122 |       0.032 |    0.317 |    0.751 |  48.339 |  -7.716 |    -5.557 |    -0.627 |
| pace_sel | 4801 |      2.16  |        15.123 |       0.033 |    0.347 |    0.728 |  48.53  |  -7.352 |    -5.296 |    -0.63  |
| matchup  | 4801 |      3.411 |        14.772 |       0.238 |    3.626 |    0     |  48.276 |  -7.837 |    -5.645 |    -0.613 |


Closing-line margin RMSE on the same games: see BETTING.md (13.68). Break-even at -110 is 52.38%. `incr t` is the t-statistic on the model's coefficient when actual margin is regressed on closing line + model; |t| > 2 would indicate information the line has not priced.

## Robustness of the matchup signal

Disagreement orthogonal to the line (matchup variant), quintiles:

| quintile | n | home cover % | se |
|---|---|---|---|
| 1 most anti-home | 946 | 48.63 | 1.63 |
| 2 | 945 | 48.78 | 1.63 |
| 3 | 945 | 49.63 | 1.63 |
| 4 | 945 | 50.26 | 1.63 |
| 5 most pro-home | 946 | 51.16 | 1.63 |

Monotone for the first time — but the whole spread is 2.5 points of cover
probability, roughly 1.5 standard errors end to end.

Incremental coefficient by season: +0.162 (t 1.06), −0.151 (t −0.97), +0.058
(t 0.38), +0.278 (t 1.94), +0.370 (t 2.51). Positive in 4 of 5, individually
significant in one.

Betting only large orthogonal disagreement: |ortho| > 1 → 51.42% (n 3454),
> 2 → 52.09% (n 2254), > 3 → 50.62% (n 1377). All below the 52.38% break-even;
not monotone in the threshold. CLV remains −0.61 points.

## Verdict

Pace/efficiency variables slot cleanly into the paper's scheme — OEFF is the
top-ranked feature the moment it is offered, displacing every box-score stat —
but own-team versions add nothing against the line, because a team's own lagged
stats cannot describe a matchup. Giving the model the opponent's lagged
pace/efficiency produces the first statistically real incremental signal
(pooled t = 3.63, monotone quintiles), yet its magnitude is ~1 point of cover
probability at the extremes: real information the line has *mostly* priced,
too small to survive the vig. Flat ROI stays negative in every variant and CLV
stays firmly negative.
