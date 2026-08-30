# ORACLE-SUBSTITUTION ATTRIBUTION OF THE WORST DECILE

For each game, substitute the REALISED component into the structural form and
measure how much closer it moves us to the bookmaker's opener.
`oracle_attribution.py`. n = 4,717, worst decile 472, |e0| >= 6.20.

**Caveat, stated first:** realised pace did not cause the opener. Realised values
are used as *evidence about whether the book's pregame latent estimate was better
than ours*. A single game is weak evidence; persistence strengthens it.

Note the mean improvements are all **negative** (actual pace −1.30, actual
efficiency −5.20 in the worst decile) — as they must be, since the opener
forecasts an *expected* total and one game is a noisy draw. **The per-game
classification, not the mean, carries the information.**

## SHARE OF WORST-DECILE SQUARED ERROR BY MECHANISM

| mechanism | n | share of games | **share of SSE** |
|---|---|---|---|
| **PACE state** | 145 | 30.7% | **30.7%** |
| pace + efficiency | 66 | 14.0% | 14.7% |
| efficiency BOTH sides | 33 | 7.0% | 7.7% |
| HOME efficiency | 22 | 4.7% | 4.1% |
| ROAD efficiency | 22 | 4.7% | 4.9% |
| efficiency (unsplit) | 10 | 2.1% | 1.5% |
| **NEITHER (book-specific / unexplained)** | 174 | 36.9% | **36.4%** |

**Pace-related: 45.4% of worst-decile squared error. Efficiency-only: 18.2%.
Unexplained: 36.4%.**

This is the statistic requested — not "pace differs in bad games" but
**"45% of worst-decile squared error occurs in games where correcting pace would
have moved us toward the bookmaker."**

### The classification is real signal, not noise

```
share of ALL games where actual-pace substitution improves by >1.0 pt   15.7%
share within the WORST decile                                           44.7%
lift 2.85x
```

## PERSISTENCE — state staleness or one-game shock?

Split by the sign of tonight's surprise (pooled means cancel):

```
tonight FASTER than expected  n=85   this game +3.404   NEXT-3 +1.933  (t=+9.95)
tonight SLOWER than expected  n=126  this game -2.884   NEXT-3 -1.295  (t=-9.73)
```

**The surprise persists — roughly half of it survives into the next three games.**
That is state staleness, not pure realisation noise.

### CORRECTION to my own reading

I first read `corr(dPace, next-3 mean) = 0.768` as evidence of severe staleness.
**That is inflated** — both terms share a common team-level component, so the
correlation is largely mechanical. The honest measure is the **prior-only**
autocorrelation:

```
corr(prior-5 pace surprise, THIS game's surprise) = +0.1036
```

**Mild, not severe.** The staleness is real but an order of magnitude smaller
than the first number suggested.

### And it is worth something, modestly

Adding a prior-only recent-pace-surprise correction:

| model | RMSE | R2 | worst-decile MAE |
|---|---|---|---|
| structural T0 alone | 3.974 | 0.7789 | 8.271 |
| + recent pace-surprise correction | 3.957 | 0.7808 | 8.226 |
| two-way line state (best model) | 3.101 | 0.8652 | 6.653 |
| **+ recent pace-surprise correction** | **3.070** | **0.8678** | **6.583** |

**+0.0026 R2 and a 1% cut in worst-decile MAE** — the first thing outside the
availability family to improve the best model at all.

## THE UNEXPLAINED GROUP — the book was NOT vindicated

For the 174 games (36.4% of worst-decile SSE) where no realised component
explains the gap:

```
mean signed gap (open - T0)   -2.564    the book priced BELOW our model
mean (actual - open)          +4.023    the game came in ABOVE the book
|actual - open| 19.69   vs   |actual - T0| 17.70
```

**Our structural model was closer to the realised total than the opener was.**
The book's deviation from us was not validated by the outcome.

**Heavily selection-contaminated** — these games are chosen for large |open − T0|
within an already-selected worst decile, so regression to the mean cuts in this
direction mechanically. It is suggestive, not evidence.

## What this establishes

1. **Pace is the largest identifiable mechanism in the failure tail** — 45.4% of
   worst-decile SSE, on a classification with 2.85x lift over chance.
2. **The pace state is mildly stale** (prior-only autocorrelation +0.104), and
   correcting it improves the best model by +0.0026 R2.
3. **Efficiency is a minor contributor** — 18.2%, split roughly evenly between
   sides.
4. **Over a third of the tail (36.4%) has no realised-basketball explanation at
   all**, and in those games our model was nearer the outcome than the opener.

**Combined with `ERROR_ATTRIBUTION`** — where injury/roster took 3.87% of overall
residual SSE and every other family took ~0 — the tail now reads as: **pace-state
error (largest identifiable), availability instability (strong flag, small
share), and a large residual the realised game does not explain.**
