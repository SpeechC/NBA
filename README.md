# Replication: "Hybrid Basketball Game Outcome Prediction Model by Integrating Data Mining Methods for the NBA"

Chen, W.-J., Jhou, M.-J., Lee, T.-S. & Lu, C.-J. (2021). *Entropy* 23(4), 477.
https://doi.org/10.3390/e23040477

## What the paper does

Predicts a **team's final score in a single game** (a regression target, not win/loss)
from that team's own recent box-score history.

1. **Data** — every 2018–19 NBA regular-season game, split into two team-game rows
   (home and away). 13 predictors + score.
2. **Normalise** — min-max each of the 13 variables to [0, 1].
3. **Designed features** — for game-lag `l ∈ {1..6}`, each feature is the mean of the
   normalised variable over the team's previous `l` games. The first 6 games of each
   team's season are dropped so all six lag settings share one sample set.
4. **Single-stage models** — ELM, MARS, XGBoost, SGB, KNN on all 13 features.
5. **Two-stage models** — rank features by an ensemble of MARS + XGBoost + SGB
   importances, average the ranks, keep the top 40% (6 of 13), refit all five models.
6. **Evaluate** — 10-fold CV MAPE; Wilcoxon signed-rank tests for significance.

**Paper's headline result:** T-XGBoost at game-lag 4, MAPE 0.0818, RMSE 11.4753.
Every model bottoms out at lag = 4. Selected features: DRB, 2P%, FT%, ORB, AST, 3PA.

## The 13 variables (Table 1)

| | Variable | Derived from `dfMaster.csv` |
|---|---|---|
| V1 | 2PA | `FGA - 3PA` |
| V2 | 2P% | `(FG - 3P) / (FGA - 3PA)` |
| V3 | 3PA | `3PA` |
| V4 | 3P% | `3P / 3PA` |
| V5 | FTA | `FTA` |
| V6 | FT% | `FT / FTA` |
| V7 | ORB | `OR` |
| V8 | DRB | `DR` |
| V9 | AST | `A` |
| V10 | STL | `ST` |
| V11 | BLK | `BL` |
| V12 | TOV | `TO` |
| V13 | PF | `PF` |
| Y | Score | `PTS` |

## Files

| File | Purpose |
|---|---|
| `prepare_data.py` | Long-format team-game panel, min-max normalisation, lagged designed features |
| `mars_elm.py` | MARS (earth-style) and ELM implementations — see deviations below |
| `run_experiment.py` | Full scheme: Tables 2–7 and Figure 3 |
| `results_*.json` | Machine-readable output |
| `run_*.log` | Full console transcript |

## Running

```bash
/home/dpope/nba_env/bin/python run_experiment.py "NBA 2018-2019 Regular Season"
```

## Deviations from the paper

These are forced by the data and the toolchain, and matter when comparing numbers.

**1. Seasons available, and each is short.** `dfMaster.csv` holds 7299 games from
2017-10-17 to 2024-06-17. Season labels live in **two** columns — `DATASET_H` covers
2017-18 and 2018-19, `BIGDATABALL\nDATASET_H` covers 2020-21 onward — and
`prepare_data.season_label()` coalesces them. Six regular seasons are present;
**2019-20 is absent entirely**. Playoffs, play-in and In-Season Tournament games are
excluded, matching the paper's regular-season design.

| Season | Games in file | Full season | Team-games | Modelled samples |
|---|---|---|---|---|
| 2017-18 | 1169 | 1230 | 2338 | 2158 |
| 2018-19 *(paper's season)* | 1163 | 1230 | 2326 | 2146 |
| 2020-21 | 1024 | 1080 | 2048 | 1868 |
| 2021-22 | 1172 | 1230 | 2344 | 2164 |
| 2022-23 | 1145 | 1230 | 2290 | 2110 |
| 2023-24 | 1067 | 1230 | 2134 | 1954 |
| pooled | 6740 | — | 13480 | 12400 |

**Overtime games have been removed from this file.** No row has a populated `OT1_H`,
and the per-season shortfall matches the NBA's overtime rate almost exactly:

| Season | Present | Full season | Missing |
|---|---|---|---|
| 2017-18 | 1169 | 1230 | 61 (5.0%) |
| 2018-19 | 1163 | 1230 | 67 (5.4%) |
| 2020-21 | 1024 | 1080 | 56 (5.2%) |
| 2021-22 | 1172 | 1230 | 58 (4.7%) |
| 2022-23 | 1145 | 1230 | 85 (6.9%) |
| 2023-24 | 1125* | 1230 | 105 (8.5%) |

\* includes 58 In-Season Tournament games, which are regular-season games but carry
their own dataset label.

So the sample is not randomly incomplete — it systematically excludes the
highest-scoring games. Two consequences:

* **For the replication:** the target variable is truncated at the top, which removes
  the hardest-to-predict games and makes our RMSE mildly flattering relative to the
  paper's (which included overtime). Our 11.7–12.3 vs the paper's 11.48 would widen
  slightly if overtime games were restored.
* **For any betting backtest:** it is fatal for totals. Closing totals were set for
  games that *could* go to overtime; grading them on an overtime-free subsample is
  ex-post selection. Measured on this file, the closing total goes OVER only
  **47.95%** of the time (n = 6707, mean actual − closing = **−0.82 pts**, ~3.9 SE),
  a bias that is an artifact of the missing games rather than a market inefficiency.
  Closing spreads are unaffected — home ATS cover is 49.69%, mean bias −0.03 pts —
  because dropping overtime games removes near-zero margins symmetrically.

Teams therefore have 63–81 games rather than 82 (72 in the shortened 2020-21), and
the paper's 2018-19 run has 2146 samples against its 2280. The gaps also shift which
games count as a team's "previous 4", so lag features average over *available* prior
games, not strictly consecutive ones.

Game numbering and min-max normalisation are both done **within season**, so lag
windows never straddle a season boundary and league-wide scoring drift across
2017–2024 does not distort the normalisation.

**2. R packages replaced.** The paper ran R (earth, gbm, elmNN, kknn, XGBoost via
caret). This replication is Python:

| Paper | Here |
|---|---|
| `earth` 5.3.0 (MARS) | `mars_elm.Earth` — degree-1 hinge basis, forward stepwise + GCV backward pruning, penalty 2, `nk = min(200, max(20, 2p)+1)`; importance = `nsubsets` |
| `elmNN` 1.0 (ELM) | `mars_elm.ELM` — random input weights/biases, radial-basis activation, Moore–Penrose pseudoinverse output weights |
| `gbm` (SGB) | `sklearn.GradientBoostingRegressor`, gbm defaults: 100 trees, depth 1, shrinkage 0.1, bag fraction 0.5 |
| `kknn` (KNN) | `sklearn.KNeighborsRegressor(weights="distance")`, k tuned 3–15 |
| `XGBoost` + caret | `xgboost.XGBRegressor` with an inner 3-fold grid over depth/rounds/eta |

`py-earth` has no Python 3.12 build (its `setup.py` uses the removed
`configparser.SafeConfigParser`), which is why MARS is reimplemented rather than
installed.

**3. M5P has no scikit-learn equivalent.** Table 5's M5P regression tree is
approximated by a pruned `DecisionTreeRegressor` (leaf-size tuned). M5P fits linear
models at the leaves, so this proxy should be somewhat *worse* than real M5P.

**4. Wilcoxon test input.** The paper does not state what it pairs. Here the test
pairs **per-sample absolute percentage errors** from the 10-fold out-of-fold
predictions, which is the natural reading of "comparing the signs and ranks of
prediction values". The paper's reported Z statistics (e.g. −10.859) are not
reproducible from any 6-value or 2280-value pairing we can identify, and its
statistics are inconsistent with its own p-values (Z = −1.017 with p = 0.007), so
treat the direction of these tests as comparable and the magnitudes as not.

**5. Hyperparameter grids.** The paper says caret tuned XGBoost and ELM but gives no
grid. Grids here are stated explicitly in `run_experiment.py`.

## Results

See `RESULTS.md`.
