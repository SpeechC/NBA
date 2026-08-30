# PACE-ERROR LEADERBOARD AND PER-GAME CONFIDENCE — the bet/pass question

Their objection was right: the previous work asked "is there a general model of
pace variance" when the question is "for tonight's game, do I bet or pass."
`local_analog_confidence.py`.

## 1. THE 30-TEAM LEADERBOARD (prior-only forecast errors, ~315 games each)

Sorted by `Q90(|pace error|)`:

| team | SD | MAE | Q80 | Q90 | >3 | >4 | **>5** | >6 |
|---|---|---|---|---|---|---|---|---|
| Washington | 4.25 | 3.31 | 5.38 | **7.30** | 45.9 | 31.6 | 22.5 | 15.5 |
| Memphis | 4.35 | 3.40 | 5.35 | 7.27 | 46.2 | 35.4 | 24.2 | 14.3 |
| Utah | 4.25 | 3.34 | 5.50 | 7.06 | 46.8 | 35.1 | 23.1 | 15.2 |
| **Indiana** | **4.42** | 3.43 | 5.62 | 6.85 | 46.8 | 37.2 | **27.2** | **17.3** |
| Boston | 4.05 | 3.14 | 4.87 | 6.82 | 41.7 | 29.0 | 19.4 | 13.4 |
| Milwaukee | 3.78 | 2.97 | 4.85 | 6.68 | 39.9 | 28.1 | 18.5 | 11.5 |
| Oklahoma City | 3.82 | 2.97 | 4.64 | 6.07 | 42.3 | 28.2 | 17.0 | 11.2 |
| LA Clippers | 3.82 | 3.01 | 4.84 | 5.86 | 40.8 | 29.1 | 18.0 | 9.5 |
| **Cleveland** | **3.35** | **2.70** | **4.50** | **5.42** | 37.1 | 24.1 | **14.0** | **6.0** |

**The raw spread is far wider than the shrunk model showed: SD 3.35-4.42, and
tail rate P(|e|>5) from 14.0% (Cleveland) to 27.2% (Indiana) — nearly 2x.**
Indiana games carry almost twice Cleveland's tail risk. `P(|e|>6)` runs 6.0% to
17.3%, a **2.9x** spread.

**Their point about tails vs variance is partly borne out:**
`corr(SD rank, P(|e|>5) rank) = +0.887` — high, but Philadelphia moves 14 ranks
between the two orderings, and `corr(SD rank, Q90 rank)` is only **+0.732**.

**Home/road: still noise.** `sd(home SD - road SD) = 0.329` across teams, but with
~157 games per cell the noise-only expectation is **0.32**. Boston's apparent
4.38/3.67 split is exactly what sampling produces. This confirms the earlier
two-way likelihood result from the raw side.

## 2. LOCAL-ANALOG INTERVALS — well calibrated, but they do not discriminate

K = 200 nearest **prior** games in `(p20_H, p20_R, mu5_H, mu5_R, expected pace,
|p20_H - p20_R|)` space, n = 1,473:

| q80 quartile | n | mean q80 | **ACTUAL P(\|e\| <= q80)** | ACTUAL sd(e) |
|---|---|---|---|---|
| 1 | 369 | 4.773 | 76.4% | 4.181 |
| 2 | 379 | 5.058 | 82.1% | 3.913 |
| 3 | 360 | 5.259 | 80.3% | 3.922 |
| 4 | 365 | 5.507 | 81.1% | 4.249 |

**The intervals are well calibrated** (76-82% against a nominal 80%). **But
realised dispersion is flat across them** — 4.18, 3.91, 3.92, 4.25. The q80
varies from 4.77 to 5.51 while the actual error does not. Calibration here comes
from the quantile being roughly constant, not from discriminating regimes.

## 3. THE FINDING THAT EXPLAINS EVERYTHING PRIOR

```
PaceConfidenceRatio = |model pace - book pace| / local q80
mean 0.274      p90 0.559      MAXIMUM band reached: 0.5-1.0
```

**The ratio essentially never exceeds 1.0.** Their worked example — a 3-possession
disagreement against an 80% interval of [−1.8, +1.9], ratio ~1.6 — **does not
occur in this data.**

```
mean |model - book| pace disagreement    ~1.1 possessions
mean local q80 of our own pace error     ~5.15 possessions
```

**Our disagreement with the bookmaker is about a fifth of our own forecast error.**
There is no subset of games where we are individually confident, because the
book's pace and ours never diverge by more than a fraction of our uncertainty.

| ratio band | n | mean \|D\| | mean q80 | PACE dir % | BET hit % |
|---|---|---|---|---|---|
| <0.5 (pass) | 1,267 | 1.09 | 5.15 | 58.6% | 54.2% |
| 0.5-1.0 (weak) | 195 | 3.26 | 5.11 | **78.5%** | **56.9%** |

The higher band **is** better — 78.5% directional pace accuracy and a 56.9% bet
hit rate — but n = 195 and it is the *top* band available, not a confident one.

Neither ranking is monotone:

```
raw |gap| quartile    Q1 56.1%  Q2 53.3%  Q3 53.8%  Q4 55.4%
ratio quartile        Q1 55.8%  Q2 52.2%  Q3 55.4%  Q4 55.2%
```

## What this settles

**The pace-gap signal is real but never individually confident.** `beta = 0.222,
t = 3.42` across ~3,500 games is a genuine edge detected by aggregation — each
individual bet sits deep inside our own forecast noise at a confidence ratio
around 0.27.

**That is why every confidence filter has failed.** There is no high-confidence
subset to select: the filters were searching for a regime that does not exist in
this market. `sigma_P` models, `volx`, hierarchical team effects, home/road
splits and style matchups all failed for the same underlying reason.

**And it reframes the bet/pass question.** The honest per-game output is not
"OVER candidate / PASS" but:

```
model pace 101.5, book-implied 98.5, disagreement +3.0 possessions
our own q80 pace error for comparable states: 5.15
confidence ratio 0.58  ->  the disagreement is inside normal model error
expected edge if the aggregate relationship holds: ~0.7 pts, hit ~52.6%
```

**Every bet this signal produces looks like that.** The edge is real, thin, and
uniform — which is exactly what the frozen prereg tests, with no threshold, as
`H1`.
