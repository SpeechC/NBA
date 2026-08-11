# Line-movement strategy over the full sample

Burn-in is now applied once across the whole chain instead of four times in sequence. 2019-20 is absent from the source data, so there is a gap between 2018-19 and 2020-21.


Bets graded from **2018-02-22** to **2026-04-12** (8183 games with a prediction).


## Coverage by season

| season                        |   games | first               | last                |
|:------------------------------|--------:|:--------------------|:--------------------|
| NBA 2017-2018 Regular Season  |     365 | 2018-02-22 00:00:00 | 2018-04-11 00:00:00 |
| NBA 2018-2019 Regular Season  |    1165 | 2018-10-24 00:00:00 | 2019-04-10 00:00:00 |
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
| all        | 8145 | 0.57  |    0.501 |    0.639 |         53.196 |  50.804 |   49.718 |   51.889 |  -3.01  |        0.275 |
| |pred|>0.5 | 4242 | 0.904 |    0.807 |    1.002 |         57.17  |  50.943 |   49.438 |   52.446 |  -2.745 |        3.3   |
| |pred|>1   | 1587 | 1.343 |    1.178 |    1.509 |         63.471 |  52.552 |   50.092 |   55.002 |   0.327 |       55.375 |
| |pred|>1.5 |  512 | 1.914 |    1.606 |    2.223 |         70.37  |  54.297 |   49.968 |   58.577 |   3.658 |       80.275 |


## Season by season at |pred| > 1

| season                        |   bets |   win_pct |   clv |   ROI % |
|:------------------------------|-------:|----------:|------:|--------:|
| NBA 2017-2018 Regular Season  |     74 |     52.7  |  0.95 |    0.61 |
| NBA 2018-2019 Regular Season  |    173 |     52.6  |  0.8  |    0.42 |
| NBA 2020-2021 Regular Season  |    140 |     52.14 |  1.62 |   -0.45 |
| NBA 2021-2022 Regular Season  |    223 |     51.57 |  1.25 |   -1.55 |
| NBA 2022-2023 Regular Season  |    207 |     49.76 |  1.17 |   -5.01 |
| NBA 2023-2024 Regular Season  |    254 |     55.91 |  1.87 |    6.73 |
| NBA 2024 In-Season Tournament |      1 |    100    | 16.5  |   90.91 |
| NBA 2024-2025 Regular Season  |    272 |     51.84 |  1.26 |   -1.04 |
| NBA 2025 In-Season Tournament |      1 |    100    | -3    |   90.91 |
| NBA 2025-2026 Regular Season  |    242 |     52.89 |  1.42 |    0.98 |


Seasons with a winning record: **6 of 10**. Seasons with positive CLV: **9 of 10**.
