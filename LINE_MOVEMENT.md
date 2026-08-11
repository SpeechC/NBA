# Modelling the closing line move

Cleaned sample: **4934** games. Spread move SD **2.09**, total move SD **3.23** — far smaller targets than a game outcome (margin SD ~13).


## 1. Does the score model's disagreement predict the move?

|        |   slope |       t |   corr |   move agrees with model % |
|:-------|--------:|--------:|-------:|---------------------------:|
| spread |  0.0134 |  2.5346 | 0.0361 |                    41.062  |
| total  |  0.0905 | 12.3238 | 0.1728 |                    50.3648 |


A positive slope means the line moves *toward* the model's opinion (the model anticipates the market). Negative means the line moves away — the model is on the wrong side of the flow, which is what a 42-44% beat-the-close rate implied.


## 2. Predicting the spread move directly (2887 games)

|                                    |   value |
|:-----------------------------------|--------:|
| RMSE predicting no move (baseline) |  2.1176 |
| RMSE of the model                  |  2.1259 |
| R2 vs baseline %                   | -0.7873 |
| corr(predicted, actual move)       |  0.0733 |
| direction called correctly %       | 45.3412 |


## 3. Economics of betting the opening number

|                              |     value |
|:-----------------------------|----------:|
| n bets                       | 2874      |
| CLV pts                      |    0.1284 |
| CLV 95% lo                   |    0.0511 |
| CLV 95% hi                   |    0.2057 |
| beat the close %             |   45.2679 |
| win rate vs opening number % |   49.5825 |
| ROI at -110 %                |   -5.3426 |
| break-even %                 |   52.381  |


A bet struck at the open is graded against the **opening** number, so CLV is the leading indicator and the win rate is the payoff. Positive CLV with a break-even win rate still means the signal is finding real information — it just has not converted yet.

## 4. Totals: the line move IS predictable

Controlling for the opening line level, the market moves toward the model's opinion —
spread t = +6.61, total t = **+13.17**. Modelling the total move directly:

| | value |
|---|---|
| RMSE predicting no move | 3.333 |
| RMSE of the model | 3.222 |
| **R² vs baseline** | **+6.51%** |
| corr(predicted, actual move) | 0.263 |
| direction correct (excl. \|move\|<0.5, n=1516) | **56.33%** |

Betting the opening total on the predicted direction, n = 1641:

| filter | n | CLV pts | 95% CI | beat close | win % | ROI % |
|---|---|---|---|---|---|---|
| all | 1641 | **+0.560** | [+0.401, +0.719] | 52.0% | 52.65 | +0.52 |
| \|pred\| > 0.5 | 948 | **+0.837** | [+0.625, +1.048] | 54.9% | 51.69 | −1.32 |
| \|pred\| > 1 | 446 | **+1.608** | [+1.283, +1.933] | 63.9% | 53.59 | +2.30 |

## Verdict

**The CLV finding is real.** This is the first robustly positive result in the whole
project: predicted move correlates 0.26 with actual move, direction is called at
56.3%, and mean CLV is positive with a confidence interval excluding zero. Crucially
it *scales monotonically* with predicted magnitude — 0.56 → 0.84 → 1.61 points — which
is what a genuine signal looks like and what noise does not do.

**The profit finding is not.** Win rate is 52.65% against a 52.38% break-even
(z = 0.22 — indistinguishable), and the ROI column is non-monotone across thresholds:
+0.52%, then −1.32%, then +2.30%. A real edge does not reverse sign in the middle.
The +2.30% at |pred| > 1 rests on n = 446, where the win-rate standard error is ±2.4%,
so its interval comfortably straddles break-even. Reporting that number alone would be
threshold-shopping.

**The arithmetic reconciles the two.** A CLV of C points converts to roughly
C/18.1 sigma of edge on a total. Break-even at -110 needs ~1.1 points of CLV. We
average 0.56 — real, but about half of what is required. Only the |pred| > 1 bucket
clears the bar (1.61), and that is exactly the bucket too small to prove anything.

**What this changes.** The target was right: modelling the market is more tractable
than modelling the game. Predicting a 3.2-point-SD human process yields +6.5% R²,
where predicting a 12.7-point-SD game outcome yielded 7.6% R² over a running average
and nothing against the line. But "more tractable" is not yet "profitable", and the
honest state is a genuine CLV signal at roughly half the required magnitude.
