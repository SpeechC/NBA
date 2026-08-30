# STAGE D — LATENT MARKET RATINGS RECOVERED FROM THE LINES

**Terminology fixed:** in `P(T>K) = 1 - Phi((K-mu)/sigma)`, sigma is **expected
total-score dispersion**, never the betting spread.

**Architecture, restated:** Kalshi does not create the expected total. It
inherits mu from the sportsbook and constructs a probability ladder around it.
Stage A is **frozen** — the ladder transformation is solved sufficiently. The
research target is the sportsbook centre.

**Hypothesis tested:** the remaining centre-line error is not a missing box-score
feature. It is that we were feeding the wrong *estimates* of pace, offence and
defence. The linemaker maintains latent recursively-updated team states.

## The model — no box scores at all

```
impH = base + Off[H] + Def[R] + hfa          impH = (open_total + M)/2
impR = base + Off[R] + Def[H] - hfa          impR = (open_total - M)/2

for each game, IN CHRONOLOGICAL ORDER:
    PREDICT first:  pred_total = impH_hat + impR_hat
    then UPDATE:    Off[H] += k*eH ; Def[R] += k*eH
                    Off[R] += k*eR ; Def[H] += k*eR
    at each season boundary:  Off *= lambda ; Def *= lambda
```

`(k, lambda)` tuned on **2017-2021 only** and applied unchanged to 2022-2026.
Selected **k = 0.30, lambda = 0.6**. Every prediction precedes its own update.

## RESULT — the latent system beats the full basketball model

| model (HELD-OUT 2022-2026) | RMSE | MAE | R2 | ≤1pt | ≤2pt |
|---|---|---|---|---|---|
| last observed implied points (crudest) | 7.675 | 6.071 | 0.0789 | 13.1 | 23.6 |
| D1 own-rating only, **no opponent adjustment** | 6.129 | 4.898 | 0.4126 | 12.8 | 25.5 |
| Stage B M6 full (all box-score blocks) | 4.508 | 3.544 | 0.7444 | 18.1 | 35.7 |
| Stage B best: struct + recent state | 4.569 | 3.602 | 0.7498 | 17.6 | 34.4 |
| **D2 two-way latent ratings — LINES ONLY** | **3.336** | **2.574** | **0.8259** | 25.5 | 47.8 |
| **struct + recent + latent ratings** | **3.174** | **2.448** | **0.8504** | 26.7 | 50.2 |

**A rating system using ZERO box-score data beats every basketball model built in
this programme** — RMSE 4.508 -> 3.336, a **26% reduction**. It also beats Stage
1's *in-sample* 3.508 while being honestly held out.

## The gain is the OPPONENT ADJUSTMENT, not line autocorrelation

```
crudest persistence (last implied points)   R2 0.0789
own-rating only, no Def state               R2 0.4126
two-way Off/Def                             R2 0.8259
```

**The two-way decomposition doubles R2 over a one-way rating and is 10x the
crude persistence baseline.** The latent structure is genuinely offence-versus-
defence, not a team-level trend.

## The recovered ratings are real basketball

2024-25 end-of-season latent **offensive** ratings, points above league base,
derived from betting lines alone:

```
top:  Oklahoma City +7.88   Memphis +6.03   Indiana +5.80   Atlanta +5.69
bot:  Charlotte -9.44   Brooklyn -9.21   Miami -6.35   New Orleans -5.61
cross-team sd:  OFF 4.133   DEF 4.079
```

These are the correct teams. Nothing in the fit knows a box score.

## The recovered update rule

```
k = 0.30       the market moves ~30% toward each new observation
lambda = 0.6   ~60% of a team's rating carries across the off-season
```

`k` is a genuine interior optimum: dev R2 peaks at 0.8700 (k=0.30) / 0.8717
(k=0.40) and test R2 falls monotonically beyond — 0.8259, 0.8180, 0.7980,
0.7349, 0.5635, and **−17.46 at k=1.0**. The system is not degenerating into
"quote the last line."

## What this does and does not establish

**Establishes:** the linemaker's state is a **recursively-updated two-way
offence/defence rating**, its update rate is ~0.30 per game, and it retains ~60%
across seasons. The Stage 1 hierarchy is now explained — Four Factors added
nothing because their information is *already inside* the latent rating, and the
large M6 "recent state" jump was a crude proxy for the state we have now
recovered properly.

**Does not establish** how the market forms those ratings from basketball. D2
takes the market's own prior output as input, so it recovers the **form and
update rate** of the linemaker's state, not the basketball inputs feeding it.
Explaining the ratings themselves from box scores is the next question.

**Still short of reconstruction:** 26.7% within 1 point and 50.2% within 2, on a
target measurable to ±0.58 points. Better than anything prior, and not yet the
~70%-within-1 that would signal a recovered process.
