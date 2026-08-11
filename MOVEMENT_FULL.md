# Line-movement strategy over the full sample

Burn-in is now applied once across the whole chain instead of four times in sequence. 2019-20 is absent from the source data, so there is a gap between 2018-19 and 2020-21.


Bets graded from **2019-01-01** to **2026-04-12** (7335 games with a prediction).


## Coverage by season

| season                        |   games | first               | last                |
|:------------------------------|--------:|:--------------------|:--------------------|
| NBA 2018-2019 Regular Season  |     682 | 2019-01-01 00:00:00 | 2019-04-10 00:00:00 |
| NBA 2020-2021 Regular Season  |    1015 | 2020-12-31 00:00:00 | 2021-05-16 00:00:00 |
| NBA 2021-2022 Regular Season  |    1166 | 2021-10-27 00:00:00 | 2022-04-10 00:00:00 |
| NBA 2022-2023 Regular Season  |    1163 | 2022-10-26 00:00:00 | 2023-04-09 00:00:00 |
| NBA 2023 In-Season Tournament |       4 | 2023-12-04 00:00:00 | 2023-12-05 00:00:00 |
| NBA 2023-2024 Regular Season  |    1098 | 2023-11-01 00:00:00 | 2024-04-14 00:00:00 |
| NBA 2024 In-Season Tournament |       2 | 2024-12-10 00:00:00 | 2024-12-11 00:00:00 |
| NBA 2024-2025 Regular Season  |    1104 | 2024-10-30 00:00:00 | 2025-04-13 00:00:00 |
| NBA 2025 In-Season Tournament |       4 | 2025-12-09 00:00:00 | 2025-12-10 00:00:00 |
| NBA 2025-2026 Regular Season  |    1097 | 2025-10-29 00:00:00 | 2026-04-12 00:00:00 |


## Strategy performance

|            |    n |   CLV |   CLV lo |   CLV hi |   beat close % |   win % |   win lo |   win hi |   ROI % |   P(ROI>0) % |
|:-----------|-----:|------:|---------:|---------:|---------------:|--------:|---------:|---------:|--------:|-------------:|
| all        | 7311 | 0.594 |    0.52  |    0.668 |         53.456 |  50.677 |   49.531 |   51.823 |  -3.253 |        0.188 |
| |pred|>0.5 | 4092 | 0.966 |    0.866 |    1.066 |         58.266 |  51.784 |   50.252 |   53.313 |  -1.14  |       22.35  |
| |pred|>1   | 1724 | 1.352 |    1.193 |    1.511 |         62.781 |  53.828 |   51.47  |   56.174 |   2.763 |       87.95  |
| |pred|>1.5 |  661 | 1.83  |    1.561 |    2.099 |         68.024 |  53.858 |   50.048 |   57.634 |   2.819 |       77.15  |


## Season by season at |pred| > 1

| season                        |   bets |   win_pct |   clv |   ROI % |
|:------------------------------|-------:|----------:|------:|--------:|
| NBA 2018-2019 Regular Season  |    137 |     50.36 |  1.02 |   -3.85 |
| NBA 2020-2021 Regular Season  |    243 |     56.38 |  1.52 |    7.63 |
| NBA 2021-2022 Regular Season  |    304 |     55.26 |  1.19 |    5.5  |
| NBA 2022-2023 Regular Season  |    237 |     47.26 |  1.19 |   -9.78 |
| NBA 2023-2024 Regular Season  |    264 |     58.71 |  1.92 |   12.09 |
| NBA 2024-2025 Regular Season  |    290 |     51.38 |  1.24 |   -1.91 |
| NBA 2025 In-Season Tournament |      1 |    100    | -3    |   90.91 |
| NBA 2025-2026 Regular Season  |    248 |     55.24 |  1.25 |    5.46 |


Seasons with a winning record: **5 of 8**. Seasons with positive CLV: **7 of 8**.
