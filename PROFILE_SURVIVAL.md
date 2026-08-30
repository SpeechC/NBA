# CURRENT-PROFILE MATCHUP ANALOGS AND THE SURVIVAL PROBABILITY

Their objection was right on both counts: franchises are not stationary pace
objects, and the earlier analog space was too thin to condition properly.
`profile_survival.py`.

## STEP A — FRANCHISE POOLING IS INVALIDATED FOR THE TAILS

Team-season pace-error statistics (120 team-seasons, median n=78), adjacent-season
persistence:

```
statistic   adjacent-season r   noise ceiling   r/ceiling
SD                   +0.2458           0.382        0.64
Q90                  +0.2283               -           -
MAE                  +0.1621               -           -
Q80                  +0.1445               -           -
p5 (tail rate)       +0.0928               -           -   <- essentially ZERO
   per-season p5:  2022->23 -0.01   2023->24 -0.03   2024->25 +0.32
```

```
Indiana   2022 SD 5.09 p5 34%  2023 4.18 28%  2024 4.01 20%  2025 4.35 27%
Boston    2022 SD 4.12 p5 26%  2023 4.30 18%  2024 4.27 22%  2025 3.51 12%

MEAN within-franchise SD range 0.81   vs   pooled between-team spread 1.07
ratio within/between = 0.75
```

**A franchise moves 75% as much year-to-year as the entire league spans.** SD
persists at 64% of its ceiling — real but moderate. **The tail rate does not
persist at all.** `PACE_ERROR_LEADERBOARD`'s tail column is therefore **not a
usable prior for tonight**, and that document should be read as descriptive only.

## STEPS D/E — the 22-dimensional current-profile analog

Analogs drawn from the 150 nearest **prior** games in a 22-dim contemporaneous
profile space (pace states, transition, TOV committed/forced, FTA rate, control
coefficient, drift, volatility, plus PrefConflict / ControlConflict / TransComp /
TovPressure / StyleDist). Franchise identity is not in the space.

```
n = 942 profile-eligible;  442 scored after burn-in
rich q80: mean 4.895  sd 0.263  range 4.08 - 5.78   (thin space: 5.147, near-constant)
p_survive: mean 0.635   p10 0.500   p90 0.780
```

## IT WORKS — for pace direction

| p_survive band | n | mean pred | **ACTUAL pace dir** | BET hit |
|---|---|---|---|---|
| 45-50 | 42 | 0.484 | 42.9% | 54.8% |
| 50-55 | 69 | 0.528 | 58.0% | 55.1% |
| 55-60 | 79 | 0.580 | 54.4% | 53.2% |
| 60-65 | 65 | 0.627 | 56.9% | 49.2% |
| **>65** | 182 | 0.741 | **72.0%** | 57.7% |

```
corr(p_survive, realised pace direction) = +0.2558   t = +5.55
corr(p_survive, BET win)                 = +0.0719   t = +1.51
```

**The profile-conditioned survival probability genuinely predicts whether our
pace call is directionally right — t = +5.55, with 72.0% realised in the top
band against 74.1% predicted.** This is the first construct in the entire
uncertainty branch that works, and it required exactly what they specified:
current profiles rather than franchise identity, and a similarity space rather
than a regression.

**But it does not predict bet outcomes** (t = +1.51, non-monotone: 54.8, 55.1,
53.2, 49.2, 57.7).

## THE ARITHMETIC THAT EXPLAINS WHY — and it is a hard ceiling

```
pace-error sd 4.0 possessions x 2.30 pts/possession = 9.20 pts of total
sd(actual - open) = 18.2 pts
=> pace is 25.6% of total variance;  efficiency and noise are 74.4%

pace direction right  60% of the time -> residual sd 16.75 pts
                      72%                            16.44
                      90%                            15.97
                     100%                            15.70   (a 13.7% reduction)
```

**Even PERFECT pace foreknowledge removes only 13.7% of the uncertainty in a
totals bet.** Going from 60% to 72% pace-direction accuracy — which the profile
model actually achieves — moves the residual sd from 16.75 to 16.44 points. That
is not enough to change a bet/pass decision at a 52.381% break-even.

**This is the falsifiable stopping point they specified**, reached from the
opposite direction than expected: not because pace confidence is unpredictable,
but because **pace confidence is predictable and still economically irrelevant to
a totals wager.**

## Secondary finding — the rich q80 is INVERTED

```
Q1 pred q80 4.563 -> ACTUAL sd 4.390   coverage 66.7%
Q4 pred q80 5.230 -> ACTUAL sd 3.662   coverage 83.6%
ratio 0.8343   F p = 0.0594
```

Higher predicted uncertainty maps to **lower** realised dispersion, with Q1
badly under-covering. **The magnitude leg fails even though the direction leg
works** — a useful reminder that `P(direction survives)` and `E|error|` are
different objects and the model recovered only the first.

## Status

| step | result |
|---|---|
| A. Franchise pooling | **INVALIDATED for tails** (p5 persistence +0.093) |
| B/C. Current profiles | built, 22-dim, prior-only |
| D. Cross-franchise analogs | built, 150-NN, franchise identity excluded |
| E. Survival probability | **WORKS for pace direction, t = +5.55** |
| F. Wagering test | **FAILS** — t = +1.51, and capped at 13.7% of total variance |

**Caveat:** 442 scored games. The pace-direction result is strong enough to
survive that; the wagering null is consistent with the arithmetic rather than
resting on the sample.

The frozen prereg is unaffected — `PaceGapPoints` enters with no threshold and no
confidence weighting, which this analysis now supports on a firmer basis than
before: not "we could not find a filter" but **"pace can explain at most a
quarter of totals variance, so no pace-based filter can matter much."**
