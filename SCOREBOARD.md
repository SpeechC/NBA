# Decision scoreboard

No regression coefficients. Every number here is something a bettor experiences. Bets are selected on the signal orthogonal to the closing line.

Break-even at -110 is 52.38%. Coin-flip log loss is 0.69315 and coin-flip Brier is 0.25000; `vs coin` below zero means the model's probabilities beat a coin flip, above zero means they are worse.


## Spreads


**1. Closing line value** (highest power per game)

| variant             |    n |   CLV pts |   CLV lo |   CLV hi |   beat close % |
|:--------------------|-----:|----------:|---------:|---------:|---------------:|
| paper6              | 4052 |    -0.162 |   -0.276 |   -0.048 |         42.646 |
| paper13             | 4052 |    -0.128 |   -0.242 |   -0.014 |         43.09  |
| pace16              | 4052 |    -0.088 |   -0.203 |    0.026 |         43.312 |
| matchup             | 4052 |    -0.109 |   -0.223 |    0.006 |         43.904 |
| matchup+rest+travel | 4052 |    -0.098 |   -0.212 |    0.016 |         43.682 |


**2. Proper scoring rules**

| variant             |   log loss |   vs coin |   Brier |
|:--------------------|-----------:|----------:|--------:|
| paper6              |    0.69471 |   0.00156 | 0.25078 |
| paper13             |    0.69422 |   0.00107 | 0.25053 |
| pace16              |    0.69419 |   0.00105 | 0.25052 |
| matchup             |    0.69376 |   0.00061 | 0.25031 |
| matchup+rest+travel |    0.69412 |   0.00097 | 0.25048 |


**3. Win rate and ROI**

| variant             |   win % |   win lo |   win hi |   ROI % |   ROI lo |   ROI hi |   P(ROI>0) % |
|:--------------------|--------:|---------:|---------:|--------:|---------:|---------:|-------------:|
| paper6              |   49.53 |    47.99 |    51.07 |   -5.44 |    -8.46 |    -2.43 |         0.05 |
| paper13             |   49.63 |    48.09 |    51.17 |   -5.25 |    -8.17 |    -2.24 |         0    |
| pace16              |   49.48 |    47.94 |    51.02 |   -5.53 |    -8.46 |    -2.66 |         0.02 |
| matchup             |   49.58 |    48.04 |    51.12 |   -5.35 |    -8.41 |    -2.33 |         0.05 |
| matchup+rest+travel |   49.83 |    48.29 |    51.37 |   -4.88 |    -7.8  |    -2.14 |         0.02 |



## Totals


**1. Closing line value** (highest power per game)

| variant             |    n |   CLV pts |   CLV lo |   CLV hi |   beat close % |
|:--------------------|-----:|----------:|---------:|---------:|---------------:|
| paper6              | 4072 |    -0.161 |   -0.278 |   -0.045 |         44.032 |
| paper13             | 4072 |    -0.237 |   -0.353 |   -0.12  |         42.927 |
| pace16              | 4072 |    -0.196 |   -0.312 |   -0.08  |         43.026 |
| matchup             | 4072 |    -0.217 |   -0.333 |   -0.101 |         42.854 |
| matchup+rest+travel | 4072 |    -0.2   |   -0.316 |   -0.083 |         42.78  |


**2. Proper scoring rules**

| variant             |   log loss |   vs coin |   Brier |
|:--------------------|-----------:|----------:|--------:|
| paper6              |    0.69353 |   0.00039 | 0.25019 |
| paper13             |    0.6938  |   0.00065 | 0.25032 |
| pace16              |    0.69363 |   0.00048 | 0.25024 |
| matchup             |    0.69341 |   0.00027 | 0.25013 |
| matchup+rest+travel |    0.69338 |   0.00023 | 0.25012 |


**3. Win rate and ROI**

| variant             |   win % |   win lo |   win hi |   ROI % |   ROI lo |   ROI hi |   P(ROI>0) % |
|:--------------------|--------:|---------:|---------:|--------:|---------:|---------:|-------------:|
| paper6              |   50.02 |    48.49 |    51.56 |   -4.5  |    -7.41 |    -1.64 |         0.12 |
| paper13             |   50.66 |    49.13 |    52.2  |   -3.28 |    -6.23 |    -0.28 |         1.62 |
| pace16              |   49.41 |    47.88 |    50.95 |   -5.67 |    -8.53 |    -2.72 |         0    |
| matchup             |   49.61 |    48.07 |    51.14 |   -5.3  |    -8.3  |    -2.39 |         0    |
| matchup+rest+travel |   49.24 |    47.7  |    50.77 |   -6    |    -8.86 |    -3.05 |         0    |

