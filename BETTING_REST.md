# Rest and travel added to the matchup model

Rest is parsed from the file's `TEAM REST DAYS` label (accurate: computed before overtime games were stripped). Travel is computed from the sequence of hosts, with arena coordinates as external reference data. Where the itinerary has a hole from a removed overtime game, travel is set to NaN and XGBoost learns a default direction.

## Variant comparison

|                     |    n |   model SD |   margin RMSE |   incr coef |   incr t |   incr p |   win % |   ROI % |   z vs BE |   CLV pts |
|:--------------------|-----:|-----------:|--------------:|------------:|---------:|---------:|--------:|--------:|----------:|----------:|
| matchup             | 4801 |      3.411 |        14.772 |       0.238 |    3.626 |    0     |  48.276 |  -7.837 |    -5.645 |    -0.613 |
| matchup+rest        | 4801 |      3.543 |        14.729 |       0.243 |    3.799 |    0     |  48.784 |  -6.868 |    -4.947 |    -0.604 |
| matchup+travel      | 4801 |      3.47  |        14.762 |       0.251 |    3.891 |    0     |  48.932 |  -6.585 |    -4.743 |    -0.592 |
| matchup+rest+travel | 4801 |      3.696 |        14.751 |       0.205 |    3.349 |    0.001 |  48.784 |  -6.868 |    -4.947 |    -0.593 |


Closing-line margin RMSE on these games is 13.68; break-even at -110 is 52.38%. `incr t` is the t-statistic on the model's coefficient when actual margin is regressed on the closing line plus the model.

## Why rest and travel add nothing: the market already prices them

Regressing *excess margin* (actual margin − closing line) on the schedule
variables directly, over 6,239 games:

| term | coef | se | t |
|---|---|---|---|
| constant | −0.089 | 0.191 | −0.47 |
| rest differential (home − away days) | +0.169 | 0.189 | +0.89 |
| travel differential (per 1000 km) | −0.005 | 0.154 | −0.03 |

Neither is significant. Cover rate by rest differential is flat and non-monotone
(−1: 51.1%, 0: 49.6%, +1: 48.0%, +2: 53.7%), with the extreme buckets holding
only 26–49 games.

This is the expected result. Rest and travel are the most public information in
the sport — the schedule is known months ahead, and every line-setter adjusts for
back-to-backs. Recovering them from the data confirms they are real effects on
*scoring* (a team on a back-to-back scores 109.79 vs 111.15, a 1.4-point drop),
but they carry no information the closing line has not already absorbed.

## Verdict

Rest and travel improve raw margin accuracy trivially (RMSE 14.772 → 14.729 with
rest, → 14.762 with travel) and leave the economics unchanged: ROI stays between
−6.6% and −7.8%, and CLV stays at roughly −0.60 points in every variant. The
incremental-information t-statistic does not meaningfully improve on the matchup
model's +3.63, which means the schedule variables are not adding a *new* channel
of information — they are partly re-encoding what opponent pace/efficiency
already captured.
