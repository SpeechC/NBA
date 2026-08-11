# Alternative disagreement models

`dis_open` -- the total forecast minus the opening total -- is the largest single
driver of the movement model, so its quality caps everything downstream. Four
alternatives to the paper's construction were built and tested.

## Total-prediction accuracy, common sample

| construction | total RMSE |
|---|---|
| **closing line (the benchmark)** | **18.09** |
| paper-style: sum of two team-score models, lag 4 | 19.31 |
| opponent-adjusted pace x efficiency (ridge) | 19.73 |
| direct total model, lag 4 | 20.19 |
| direct total, lag 10 | 20.21 |
| direct total, lag 20 | 20.21 |
| direct total, exponential decay (half-life 5) | 20.27 |

The opponent adjustment beats every *lagged-mean* alternative, confirming that raw
OEFF/DEFF are schedule-contaminated. But it does not beat the incumbent, because the
score model already carries opponent pace and efficiency as inputs and uses sixteen
more features besides. Every construction remains worse than the closing line.

Longer and decayed windows did **not** help, which is a mild surprise: the
replication found MAPE falling monotonically through lag 6, and all betting work had
been stuck at lag 4 purely because that was the paper's configuration. Predicting
scores accurately and predicting line movement are evidently different tasks.

## Effect on the movement strategy, like-for-like

| variant | n | corr(pred, move) | CLV all | n>1 | CLV>1 | beat close | win % | ROI % |
|---|---|---|---|---|---|---|---|---|
| baseline | 5131 | 0.246 | 0.603 | 1241 | 1.366 | 61.9% | 52.38 | −0.01 |
| baseline + adjusted | 4832 | 0.257 | 0.672 | 1280 | 1.378 | 61.9% | 52.66 | +0.53 |
| adjusted replaces baseline | 4832 | 0.243 | 0.620 | 1156 | 1.349 | 61.3% | 53.29 | +1.73 |

## Verdict

Marginal at best. Adding the adjusted-ratings disagreement lifts overall CLV from
0.603 to 0.672 -- about 11% -- and leaves the selective-threshold CLV essentially
unchanged (1.366 to 1.378). The win rates, 52.38 / 52.66 / 53.29 on roughly 1,200
bets each, differ by well under one standard error (~1.44 points); the spread across
them is noise, not a ranking.

**The ceiling is not in the disagreement model.** Four structurally different
constructions -- direct-total, three window lengths, and a principled
opponent-adjusted pace x efficiency system -- all land in the same place: CLV near
1.35 at the selective threshold, against the ~1.35 required to break even at -110.

A caution on accumulated multiple testing: something like fifteen strategy variants
have now been evaluated on this sample. The +1.73% in the last row is the best of
those, and selecting it because it is the best is precisely the error identified in
the paper's own lag-4 claim. It should be read as break-even until confirmed out of
sample.
