# NBA referee branch: final state

Closed after the lookback-window test retained the incumbent estimator.
Companion to `CLOSING.md`, which closed the earlier closing-market branch.

## The finding

> The NBA totals market incorporates broad shifts in the league's officiating
> environment but does not incorporate the idiosyncratic component of the
> specific crew assigned to today's game. Crew assignments are published
> mid-morning; the closing total moves about 4.6% of an effect it could observe
> hours in advance.

Stated at its defensible width: the evidence is consistent with referee
assignment producing a systematic shift in foul adjudication and scoring
conditional on observably similar pregame basketball states. It is not a
randomized experiment and does not establish intent or causation in that sense.

## The frozen artifacts — do not modify

| file | what |
|---|---|
| `ref_features.csv` | the feature table: `CrewShock`, `LeagueFoulState`, per game |
| `ref_features.py` | the estimator that produced it |
| `ref_regime.py` | the identification that separated the two states |
| `ref_final.py` | concentration, mechanical chain, season P&L |

```
CrewShock   idiosyncratic crew foul propensity, matched horizons
            N = 60 prior games per official, min_periods 25
            minus the league level over the SAME calendar span
            shrunk by n/(n+k), k = 78.2 estimated on development
            summed over the three officials
LeagueFoulState  trailing 200-game league mean minus trailing 1230-game mean
Frozen threshold   CrewShock >= +0.8682   (development Q85)
Split       development through 2023-24; holdout 2024-25 and 2025-26
```

Strictly prior-only: an official's effect at game t uses only that official's
games strictly before t.

## What was established

**Mechanism, fully traced.** Per 1 SD of CrewShock, on development:

```
+0.834 defensive fouls -> +1.159 FTA -> +0.926 FTM -> +0.813 total points
```

Made free throws account for 114% of the scoring effect: the channel is
entirely free-throw-mediated, with no residual pace or tempo component.

- 75.2% of the incremental whistles are defensive fouls, 11.7% offensive
- the defensive-vs-offensive contrast survives time-local permutation at
  z = +5.54, p = 0.0033
- the effect is broad across officials: all 101 leave-one-referee-out refits
  stay positive, range [+0.737, +1.015] against a full-sample +0.879
- applied symmetrically: home 0.5089 / away 0.4911

**Non-pricing.** `c_market` is statistically zero in every window; `c_true` is
+0.78 to +1.09. Development gap +0.708 (t=2.49), pooled +0.706 (t=2.92). The
time-local permutation null is correctly centred (mean −0.024) and gives
p = 0.0100 pooled, p = 0.0170 development, p = 0.2318 holdout.

**Exogeneity, five independent checks, all landing below their own nulls.**

| check | observed | null | verdict |
|---|---|---|---|
| assignment R² on 34 team states | 1.179% | 1.326% | below null |
| max \|r\| with 34 states | 0.0362 | 0.0493 | below null |
| team response-slope dispersion | 0.086 | 0.124 | below null |
| tail balance, max \|SMD\| | 0.1551 | 0.1621 | below null |
| individual HIGH/LOW ref assignment | 0.0539 | 0.0436 | FW p = 0.1421 |

R² of `CrewShock` on the team controls is 0.00240. HIGH-foul and LOW-foul
referee games are indistinguishable on every pregame team state (max SMD
0.1308, FW p = 0.2249) and then diverge substantially once played (max SMD
0.4102, FW p = 0.0005).

## Economics — real, replicated, under-powered

Bet OVER when `CrewShock >= 0.8682`. Flat $100 risk at −110
(win +$90.91, loss −$100, push $0). Full universe:

```
DEVELOPMENT   998 bets   55.07%   +$5,064   ROI 5.14%
HOLDOUT       405 bets   54.21%   +$1,409   ROI 3.49%
POOLED      1,403 bets   54.82%   +$6,473   ROI 4.66%

max drawdown $2,573   longest losing streak 9   longest winning streak 13
grading at the OPEN instead: 54.08%, +$4,536, ROI 3.25%
```

Profitable in six of eight seasons; the two losses are the first (2017-18,
−$991) and the last (2025-26, −$891). Establishing the +2.44pp edge needs about
3,294 bets — roughly 19 seasons at ~175 a year. **The science is stronger than
the economics.**

## What was tried and failed

Everything below is retired. Do not revive without new data.

| test | result |
|---|---|
| crew × matchup foul pressure | additive, not superadditive; every interaction null |
| CrewShock × offensive strength | `bO` wrong sign in development, pooled +0.0055 |
| RefExposure = CrewShock × possessions | correct units, 0.9997 correlated, no gain |
| RefFTValue, RefScoringShock | 0.99 collinear; anti-confound coefficients sign-flip |
| A/D underreaction residual | wrong sign, anti-confound gate fails |
| live-ball turnover composition | mechanism strong, no Over direction (net −0.9 pts/TOV) |
| visitor × crew half allocation | allocation channel ~200x too small to detect |
| market learning over time | `c_market` flat at zero in all eight seasons |
| lookback windows 30/100/150 + expanding | N=60 best on all six scale-invariant measures |

## Why 2025-26 was weak

`b_fouls` drops to +0.503 (t=1.71) against +0.95 to +1.48 in all seven prior
seasons; z = −2.48 vs pooled, p = 0.0132. Diagnosed as
`REFEREE_PROPENSITY_PERSISTENCE_WEAKENED`: the forward persistence slope falls
to 1.17 against a 1.43–2.33 range and stays low under ≥60-prior-game
restriction. Affirmatively **not** thin priors (deepest histories in the
sample, median 372 prior games, shrinkage at ceiling) and **not** compressed
heterogeneity (widest game-level CrewShock spread on record). One season only —
monitor, do not act.

## Rules carried forward

1. Frozen-threshold permutation nulls are broken when the statistic's spread
   changes under the null. Use matched-size tails. This bit twice.
2. Horizon mismatch between a referee estimate and its league baseline lets
   temporal drift back in. Match the calendar span.
3. Build features once on the complete universe and merge afterwards. Never let
   analysis-sample filtering touch feature estimation.
4. Naive t-statistics on referee-derived regressors are not trustworthy; the
   7-day-block crew permutation is the inference of record.
5. Coefficients on differently-scaled variables are not comparable. Use
   scale-invariant measures.
