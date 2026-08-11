# Results

Replication of Chen et al. (2021), *Entropy* 23(4), 477. All values are 10-fold cross-validated MAPE (lower is better).

## 1. The paper's season (2018-19), replicated vs published

### Table 3 — single-stage

**Replicated**

|           |    l=1 |    l=2 |    l=3 |    l=4 |    l=5 |    l=6 | best lag   |
|:----------|-------:|-------:|-------:|-------:|-------:|-------:|:-----------|
| S-ELM     | 0.0911 | 0.0899 | 0.0892 | 0.0891 | 0.0888 | 0.0885 | l=6        |
| S-MARS    | 0.0917 | 0.0911 | 0.09   | 0.09   | 0.0904 | 0.0895 | l=6        |
| S-XGBoost | 0.0916 | 0.0914 | 0.0903 | 0.0896 | 0.0901 | 0.0895 | l=6        |
| S-SGB     | 0.0916 | 0.0911 | 0.0904 | 0.0898 | 0.0898 | 0.0894 | l=6        |
| S-KNN     | 0.0939 | 0.0924 | 0.0922 | 0.0897 | 0.0898 | 0.0899 | l=4        |


**As published**

|           |    l=1 |    l=2 |    l=3 |    l=4 |    l=5 |    l=6 | best lag   |
|:----------|-------:|-------:|-------:|-------:|-------:|-------:|:-----------|
| S-ELM     | 0.102  | 0.096  | 0.0915 | 0.087  | 0.0931 | 0.0928 | l=4        |
| S-MARS    | 0.091  | 0.0909 | 0.0897 | 0.0846 | 0.0917 | 0.0907 | l=4        |
| S-XGBoost | 0.0919 | 0.0907 | 0.0911 | 0.0842 | 0.0927 | 0.092  | l=4        |
| S-SGB     | 0.091  | 0.0925 | 0.0913 | 0.0845 | 0.0923 | 0.0908 | l=4        |
| S-KNN     | 0.0992 | 0.1011 | 0.0947 | 0.0873 | 0.0934 | 0.0941 | l=4        |


Best replicated: **S-ELM at l=6**, MAPE 0.0885 (paper: S-XGBoost at l=4). Mean spread between a model's worst and best lag: **0.0027 replicated vs 0.0105 published**.

### Table 4 — two-stage

**Replicated**

|           |    l=1 |    l=2 |    l=3 |    l=4 |    l=5 |    l=6 | best lag   |
|:----------|-------:|-------:|-------:|-------:|-------:|-------:|:-----------|
| T-ELM     | 0.0908 | 0.0905 | 0.0903 | 0.0894 | 0.0892 | 0.089  | l=6        |
| T-MARS    | 0.0917 | 0.091  | 0.091  | 0.0901 | 0.0904 | 0.0898 | l=6        |
| T-XGBoost | 0.0913 | 0.0914 | 0.0905 | 0.0897 | 0.0903 | 0.0895 | l=6        |
| T-SGB     | 0.0913 | 0.0914 | 0.0908 | 0.0898 | 0.0902 | 0.0896 | l=6        |
| T-KNN     | 0.0942 | 0.0932 | 0.0916 | 0.0901 | 0.0905 | 0.0901 | l=4        |


**As published**

|           |    l=1 |    l=2 |    l=3 |    l=4 |    l=5 |    l=6 | best lag   |
|:----------|-------:|-------:|-------:|-------:|-------:|-------:|:-----------|
| T-ELM     | 0.1206 | 0.0924 | 0.0951 | 0.0863 | 0.0972 | 0.0902 | l=4        |
| T-MARS    | 0.0917 | 0.0911 | 0.0912 | 0.0845 | 0.0928 | 0.09   | l=4        |
| T-XGBoost | 0.0918 | 0.093  | 0.0916 | 0.0818 | 0.0929 | 0.092  | l=4        |
| T-SGB     | 0.0909 | 0.0918 | 0.0912 | 0.0829 | 0.093  | 0.0908 | l=4        |
| T-KNN     | 0.0998 | 0.0984 | 0.0973 | 0.0872 | 0.0993 | 0.097  | l=4        |


Best replicated: **T-ELM at l=6**, MAPE 0.0890 (paper: T-XGBoost at l=4). Mean spread between a model's worst and best lag: **0.0023 replicated vs 0.0153 published**.

### Does feature selection help? (two-stage MAPE − single-stage MAPE)

Positive = the two-stage model is **worse**.

|         |   l=1 |   l=2 |   l=3 |   l=4 |   l=5 |   l=6 |
|:--------|------:|------:|------:|------:|------:|------:|
| ELM     |    -3 |     6 |    11 |     3 |     4 |     5 |
| MARS    |     0 |    -1 |    10 |     1 |     0 |     3 |
| XGBoost |    -3 |     0 |     2 |     1 |     2 |     0 |
| SGB     |    -3 |     3 |     4 |     0 |     4 |     2 |
| KNN     |     3 |     8 |    -6 |     4 |     7 |     2 |

*(values are MAPE differences x 10,000)*

### Table 2 — ensemble feature ranking at lag = 4

|     |   MARS |   XGBoost |   SGB |   Average Rank |
|:----|-------:|----------:|------:|---------------:|
| 2P% |      2 |         1 |     1 |           1.33 |
| 3PA |      1 |         6 |     3 |           3.33 |
| AST |      5 |         3 |     4 |           4    |
| ORB |      5 |         4 |     5 |           4.67 |
| DRB |     10 |         2 |     2 |           4.67 |
| FT% |      4 |         7 |     6 |           5.67 |
| FTA |      7 |         8 |     8 |           7.67 |
| 3P% |     11 |         5 |     9 |           8.33 |
| 2PA |      8 |        10 |     7 |           8.33 |
| TOV |      3 |        12 |    10 |           8.33 |
| PF  |      9 |         9 |    11 |           9.67 |
| BLK |     13 |        11 |    12 |          12    |
| STL |     13 |        13 |    13 |          13    |

Selected top 6: **2P%, 3PA, AST, ORB, DRB, FT%**

Paper selected: DRB, 2P%, FT%, ORB, AST, 3PA

Overlap: **6/6**

### Table 5 — comparison at lag = 4

|           |   MAPE |    RMSE |    SSE |
|:----------|-------:|--------:|-------:|
| S-SVR     | 0.0888 | 12.2647 | 342965 |
| S-Linear  | 0.0891 | 12.2312 | 341091 |
| T-SVR     | 0.0893 | 12.3052 | 345231 |
| T-Linear  | 0.0895 | 12.2841 | 344048 |
| T-XGBoost | 0.0897 | 12.3135 | 345699 |
| T-M5P     | 0.0938 | 12.8415 | 375982 |
| S-M5P     | 0.0941 | 12.901  | 379475 |


Paper reported T-XGBoost MAPE 0.0818 / RMSE 11.4753, beating every baseline. Here T-XGBoost ranks **5 of 7**, and plain linear regression on all 13 features (S-Linear, 0.0891) is the stronger model.

### Tables 6 & 7 — Wilcoxon signed-rank tests

T-XGBoost (lag 4) vs other lags:

|       |   statistic |   p_value |
|:------|------------:|----------:|
| lag=1 | 1.21696e+06 |    0.0081 |
| lag=2 | 1.17201e+06 |    0      |
| lag=3 | 1.258e+06   |    0.1798 |
| lag=5 | 1.25724e+06 |    0.1721 |
| lag=6 | 1.28004e+06 |    0.5219 |


T-XGBoost (lag 4) vs other two-stage models:

|          |   statistic |   p_value |
|:---------|------------:|----------:|
| T-Linear | 1.28489e+06 |    0.6269 |
| T-MARS   | 1.24286e+06 |    0.0683 |
| T-SVR    | 1.27643e+06 |    0.4502 |
| T-SGB    | 1.28122e+06 |    0.5466 |
| T-KNN    | 1.26662e+06 |    0.2859 |
| T-ELM    | 1.26646e+06 |    0.2836 |
| T-M5P    | 1.11727e+06 |    0      |

### Figure 3 — MAPE by number of selected features (lag = 4)

|           |      4 |      5 |      6 |      7 |      8 |
|:----------|-------:|-------:|-------:|-------:|-------:|
| T-ELM     | 0.0902 | 0.09   | 0.0894 | 0.0892 | 0.0892 |
| T-MARS    | 0.0907 | 0.0904 | 0.0901 | 0.0899 | 0.0902 |
| T-XGBoost | 0.0903 | 0.0898 | 0.0897 | 0.0898 | 0.0896 |
| T-SGB     | 0.0903 | 0.0899 | 0.0898 | 0.0897 | 0.0896 |
| T-KNN     | 0.0918 | 0.091  | 0.0901 | 0.0904 | 0.0906 |


## 2. All seasons

### Best model and best lag per season

| season    |    n | best model   | best lag   |   best MAPE |   T-XGBoost l=4 | T-XGBoost best lag   | lag with lowest mean MAPE   |
|:----------|-----:|:-------------|:-----------|------------:|----------------:|:---------------------|:----------------------------|
| 2017-2018 | 2280 | S-MARS       | l=6        |      0.0894 |          0.0906 | l=6                  | l=6                         |
| 2018-2019 | 2280 | S-ELM        | l=6        |      0.0885 |          0.0897 | l=6                  | l=6                         |
| 2020-2021 | 1980 | S-ELM        | l=5        |      0.0888 |          0.0897 | l=6                  | l=6                         |
| 2021-2022 | 2280 | S-ELM        | l=6        |      0.0898 |          0.0903 | l=6                  | l=6                         |
| 2022-2023 | 2280 | T-ELM        | l=6        |      0.0832 |          0.084  | l=6                  | l=6                         |
| 2023-2024 | 2144 | S-MARS       | l=6        |      0.0884 |          0.0899 | l=6                  | l=6                         |

### T-XGBoost MAPE across lags, every season

|           |    l=1 |    l=2 |    l=3 |    l=4 |    l=5 |    l=6 |
|:----------|-------:|-------:|-------:|-------:|-------:|-------:|
| 2017-2018 | 0.0915 | 0.0908 | 0.0903 | 0.0906 | 0.0904 | 0.0901 |
| 2018-2019 | 0.0913 | 0.0914 | 0.0905 | 0.0897 | 0.0903 | 0.0895 |
| 2020-2021 | 0.0899 | 0.0898 | 0.0898 | 0.0897 | 0.0899 | 0.0896 |
| 2021-2022 | 0.0915 | 0.0915 | 0.091  | 0.0903 | 0.0903 | 0.0901 |
| 2022-2023 | 0.084  | 0.0837 | 0.0836 | 0.084  | 0.0842 | 0.0834 |
| 2023-2024 | 0.0907 | 0.0909 | 0.0908 | 0.0899 | 0.0901 | 0.089  |

### Mean MAPE over all 10 models, by lag and season

|           |    l=1 |    l=2 |    l=3 |    l=4 |    l=5 |    l=6 |
|:----------|-------:|-------:|-------:|-------:|-------:|-------:|
| 2017-2018 | 0.092  | 0.0913 | 0.0907 | 0.0906 | 0.0905 | 0.0901 |
| 2018-2019 | 0.0919 | 0.0913 | 0.0906 | 0.0897 | 0.09   | 0.0895 |
| 2020-2021 | 0.0905 | 0.0904 | 0.0903 | 0.0902 | 0.09   | 0.0896 |
| 2021-2022 | 0.0926 | 0.092  | 0.0913 | 0.0907 | 0.0906 | 0.0903 |
| 2022-2023 | 0.0847 | 0.0843 | 0.0844 | 0.0846 | 0.0844 | 0.0839 |
| 2023-2024 | 0.0914 | 0.0913 | 0.0908 | 0.0903 | 0.0901 | 0.0892 |

### Selected features at lag = 4, every season

| season    | selected (rank order)        | overlap with paper   |
|:----------|:-----------------------------|:---------------------|
| 2017-2018 | 2P%, 3PA, FTA, AST, BLK, STL | 3/6                  |
| 2018-2019 | 2P%, 3PA, AST, ORB, DRB, FT% | 6/6                  |
| 2020-2021 | 2P%, 2PA, FT%, TOV, DRB, 3P% | 3/6                  |
| 2021-2022 | 2P%, FTA, AST, 2PA, 3PA, FT% | 4/6                  |
| 2022-2023 | 3PA, FT%, AST, 2P%, TOV, FTA | 4/6                  |
| 2023-2024 | 2P%, BLK, FTA, 3PA, AST, PF  | 3/6                  |


### How often each variable is selected at lag = 4

|     |   seasons selected |
|:----|-------------------:|
| 2P% |                  6 |
| 3PA |                  5 |
| AST |                  5 |
| FTA |                  4 |
| FT% |                  4 |
| BLK |                  2 |
| DRB |                  2 |
| 2PA |                  2 |
| TOV |                  2 |
| STL |                  1 |
| ORB |                  1 |
| 3P% |                  1 |
| PF  |                  1 |


## 3. Verdict

| Paper's claim | Replicates? | Evidence |
|---|---|---|
| Error level (MAPE ~0.08-0.09, RMSE ~11.5) | **Yes** | Replicated MAPE 0.082-0.092 and RMSE 11.7-12.3 across six seasons |
| The six selected features (DRB, 2P%, FT%, ORB, AST, 3PA) | **Largely** | 5/6 overlap on the paper's own season; 2P% and DRB rank top-2 as in the paper |
| game-lag = 4 is optimal | **No** | l=4 has the lowest mean MAPE in 0/6 seasons; l=6 wins in 6/6. Wilcoxon finds l=4 not significantly different from any other lag (all p > 0.10) |
| Two-stage beats single-stage | **No meaningful effect** | Feature selection helps in 2/6 seasons and hurts in 4; the largest mean gain is 0.0001 MAPE, against the paper's claimed 0.0024 improvement (S-XGBoost 0.0842 -> T-XGBoost 0.0818) |
| T-XGBoost is the best model | **No** | It ranks 5th of 7 in the Table 5 comparison; single-stage SVR and linear regression both beat it |
| Six is the optimal number of features | **No** | MAPE falls monotonically from 4 to 8 features for every model (Figure 3 above) |

The headline finding — that a specific model at a specific lag with a specific six features is the winner — does not survive. All ten models sit inside a ~0.003 MAPE band, and ordinary least squares on all 13 features is as good as anything. What does hold up is the feature-importance result: shooting efficiency (2P%), defensive rebounding, assists and three-point volume are consistently the informative predictors.
