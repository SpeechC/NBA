# Line-movement strategy over the full sample

Burn-in is now applied once across the whole chain instead of four times in sequence. 2019-20 is absent from the source data, so there is a gap between 2018-19 and 2020-21.


Bets graded from **2019-01-01** to **2024-04-14** (5128 games with a prediction).


## Coverage by season

| season                        |   games | first               | last                |
|:------------------------------|--------:|:--------------------|:--------------------|
| NBA 2018-2019 Regular Season  |     682 | 2019-01-01 00:00:00 | 2019-04-10 00:00:00 |
| NBA 2020-2021 Regular Season  |    1015 | 2020-12-31 00:00:00 | 2021-05-16 00:00:00 |
| NBA 2021-2022 Regular Season  |    1166 | 2021-10-27 00:00:00 | 2022-04-10 00:00:00 |
| NBA 2022-2023 Regular Season  |    1163 | 2022-10-26 00:00:00 | 2023-04-09 00:00:00 |
| NBA 2023 In-Season Tournament |       4 | 2023-12-04 00:00:00 | 2023-12-05 00:00:00 |
| NBA 2023-2024 Regular Season  |    1098 | 2023-11-01 00:00:00 | 2024-04-14 00:00:00 |


## Strategy performance

|            |    n |   CLV |   CLV lo |   CLV hi |   beat close % |   win % |   win lo |   win hi |   ROI % |   P(ROI>0) % |
|:-----------|-----:|------:|---------:|---------:|---------------:|--------:|---------:|---------:|--------:|-------------:|
| all        | 5112 | 0.588 |    0.502 |    0.674 |         53.081 |  50.685 |   49.314 |   52.054 |  -3.238 |        0.938 |
| |pred|>0.5 | 2875 | 0.884 |    0.768 |    0.999 |         56.315 |  50.296 |   48.468 |   52.122 |  -3.981 |        1.188 |
| |pred|>1   | 1230 | 1.357 |    1.173 |    1.54  |         62.024 |  52.846 |   50.052 |   55.626 |   0.887 |       61.662 |
| |pred|>1.5 |  406 | 1.787 |    1.457 |    2.116 |         66.341 |  53.941 |   49.079 |   58.747 |   2.978 |       74.3   |


## Season by season at |pred| > 1

| season                       |   bets |   win_pct |   clv |   ROI % |
|:-----------------------------|-------:|----------:|------:|--------:|
| NBA 2018-2019 Regular Season |    164 |     51.22 |  0.98 |   -2.22 |
| NBA 2020-2021 Regular Season |    256 |     52.34 |  1.37 |   -0.07 |
| NBA 2021-2022 Regular Season |    322 |     54.35 |  0.94 |    3.75 |
| NBA 2022-2023 Regular Season |    226 |     46.9  |  1.35 |  -10.46 |
| NBA 2023-2024 Regular Season |    262 |     57.63 |  2.09 |   10.03 |


Seasons with a winning record: **2 of 5**. Seasons with positive CLV: **5 of 5**.

## Verdict: strong CLV, no profit

**The CLV finding gets much stronger on the full sample.** Mean CLV +0.588 points
with a 95% interval of [0.502, 0.674] on 5,112 bets, and it scales cleanly with
predicted magnitude:

| filter | CLV | beat close |
|---|---|---|
| all | +0.588 | 53.1% |
| \|pred\|>0.5 | +0.884 | 56.3% |
| \|pred\|>1 | +1.357 | 62.0% |
| \|pred\|>1.5 | +1.787 | 66.3% |

Monotone in both columns, and **positive in all five seasons** (+0.98, +1.37, +0.94,
+1.35, +2.09). The model genuinely anticipates where the total will close. That is
not a small-sample artefact — it is the most robust result in this project.

**The profit finding collapses.** At \|pred\|>1, season by season:

| season | bets | win % | ROI % |
|---|---|---|---|
| 2018-19 | 164 | 51.22 | −2.22 |
| 2020-21 | 256 | 52.34 | −0.07 |
| 2021-22 | 322 | 54.35 | +3.75 |
| 2022-23 | 226 | 46.90 | **−10.46** |
| 2023-24 | 262 | 57.63 | **+10.03** |

Two winning seasons out of five, swinging from −10.5% to +10.0%. P(ROI>0) at this
threshold is 61.7% — a coin flip. The +2.30% on 446 bets reported earlier was a
1.2-season artefact of the stacked burn-in; the honest full-sample figure is
**+0.89% on 1,230 bets**.

**Why CLV does not convert here.** CLV is usually treated as the leading indicator
of profit, and it is converting — exactly as theory says, just not to enough. A CLV
of C points on a total whose residual SD is ~18 buys roughly C/18 sigma of edge:
1.36 points → about 0.5 percentage points above break-even → +0.9% ROI. The
conversion is working; the problem is that break-even at -110 already demands ~1.1
points of CLV, so 1.36 leaves almost nothing after the vig. On spreads (residual SD
13.1) the same CLV would be worth more, but the spread signal is weaker to begin with.

**Where that leaves it.** We have a real, five-season-consistent ability to predict
where the total closes, worth about 1.4 points at the selective threshold, against a
requirement of roughly 1.1 points just to break even. That is a genuine finding and a
marginal business — one that any of −115 juice, missed opening numbers, or ordinary
season-to-season variance turns negative.
