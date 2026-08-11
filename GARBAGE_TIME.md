# Garbage-time adjustment: a clean negative

Possession-level garbage-time flagging, garbage-time-adjusted team ratings, and a
pre-registered test of whether they improve the market-facing model. They do not.

## The flag

Bill James safe-lead criterion — lead minus 3, plus half a point if the leading
team has the ball, squared against seconds remaining. **Published, with no free
parameters**, deliberately: a threshold fitted on this data would be one more
researcher degree of freedom in a project that has already spent ~15 variants.

It behaves exactly as garbage time should:

| period | possessions flagged |
|---|---|
| Q1 | 0.00% |
| Q2 | 0.02% |
| Q3 | 1.46% |
| **Q4** | **22.59%** |

5.85% of possessions overall; 83.9% of games contain at least one, but the median
game is only 2.4% flagged and the 95th percentile 23.9% — a handful of decided
possessions in most games, a quarter of the game in blowouts.

Flagged possessions score **1.099 points per possession against 1.154 in
competitive play** — a 4.8% efficiency drop. The behavioural change is real.

## The test

Three feature sets, one primary metric, all reported.

| set | total RMSE | line RMSE | gap | CLV all | CLV \|pred\|>1 |
|---|---|---|---|---|---|
| A odds-file OEFF/DEFF/PACE | **19.232** | 18.046 | +1.186 | **+0.601** | +1.351 |
| B pbp-derived, all possessions | 19.268 | 18.046 | +1.223 | +0.515 | +1.234 |
| C pbp-derived, competitive only | 19.271 | 18.046 | +1.225 | +0.497 | +1.300 |

**B vs A** — the pbp reconstruction matches the vendor box score and adds nothing
(19.268 vs 19.232, a 0.04 difference). That is a successful *validation*: our
OEFF correlates **0.9898** with the odds file's at team-game level, mean
difference −0.14. The pipeline is right; it is simply not better.

**C vs B** — garbage-time adjustment changes RMSE by **0.003**. Nothing.

## Why it fails, quantitatively

The adjustment is nearly a constant, and walk-forward calibration absorbs
constants.

| | value |
|---|---|
| mean OEFF adjustment per team-season | +0.309 |
| SD of that adjustment across teams | 0.749 |
| SD of team OEFF itself (the signal) | 3.933 |
| **adjustment as a share of between-team spread** | **19.0%** |
| garbage share across teams | 5.29% ± 1.16% |

Every team plays roughly the same fraction of garbage time (5.29% ± 1.16%), so
removing it shifts almost every rating by almost the same amount. What little
variation remains is **correlated +0.645 with team OEFF itself** — meaning the
adjustment is mostly re-measuring team strength, not cleaning it. Garbage time is
partly *informative*: the teams who play the most of it are the very good and the
very bad.

## What this closes

The cheapest pbp win is not a win. Possession-level reconstruction reproduces the
vendor box score to a correlation of 0.99 but does not beat it, and stripping
decided possessions moves nothing. The gap to the closing line (+1.19 on totals)
is not caused by contaminated efficiency measurement.

That redirects effort rather than ending it. The remaining pbp-specific lever is
the one that was always the real argument for this data: **personnel** — who is
actually on the floor, which stint-level lineup data supports and which no
team-level rating, however cleanly measured, can express.
