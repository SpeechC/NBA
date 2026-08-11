# Is within-game scoring rate mean reverting?

**What is measurable.** The file has points by quarter, not possessions by quarter — `PACE`/`POSS` are game-level only. Quarter-1 points correlate **0.51** with combined offensive efficiency but only **0.23** with game pace, so this is closer to a scoring-efficiency test than a pace test. Pace specifically cannot be resolved with this data.


Regulation-only games: 6846 (excludes 380 overtime games, whose 4th quarter is conditioned on the score being tied).


## Quarter shares of the closing total

|    |   mean pts |     SD |   share of closing total |
|:---|-----------:|-------:|-------------------------:|
| q1 |    56.2016 | 8.6852 |                   0.2525 |
| q2 |    56.0555 | 8.5775 |                   0.2518 |
| q3 |    55.6865 | 8.5288 |                   0.2502 |
| q4 |    53.8329 | 8.9371 |                   0.2419 |


Scoring drifts *down* through the game — Q4 averages 53.8 vs Q1's 56.2 — so each quarter is benchmarked against its own share, not a flat quarter of the total.


## Correlations between quarter deviations

|      |    d_q1 |    d_q2 |   d_q3 |    d_q4 |
|:-----|--------:|--------:|-------:|--------:|
| d_q1 |  1      |  0.0602 | 0.0316 | -0.0302 |
| d_q2 |  0.0602 |  1      | 0.0042 | -0.0038 |
| d_q3 |  0.0316 |  0.0042 | 1      |  0.0739 |
| d_q4 | -0.0302 | -0.0038 | 0.0739 |  1      |


## Does Q1 predict later quarters?

|                                 |    coef |     se |       t |      p |
|:--------------------------------|--------:|-------:|--------:|-------:|
| d_q2 on d_q1                    |  0.0599 | 0.012  |  4.9906 | 0      |
| d_q3 on d_q1                    |  0.0311 | 0.0119 |  2.6137 | 0.009  |
| d_q4 on d_q1                    | -0.0321 | 0.0128 | -2.5024 | 0.0124 |
| rest of game (Q2+Q3+Q4) on d_q1 |  0.0589 | 0.0217 |  2.7106 | 0.0067 |
| 2nd half on 1st half            | -0.0004 | 0.0125 | -0.0331 | 0.9736 |


Pooled quarter-to-quarter AR(1) slope: **+0.0477** (t = 6.71).


## Variance decomposition

Mean covariance between different quarters (the shared, persistent game-level component): **1.53**

Mean variance of a single quarter's deviation: **68.99**

Share of a quarter's variance that is persistent game-level signal: **2.2%**; the remaining **97.8%** is quarter-specific noise.


## The live-betting version (all games, overtime included)

Regressing (actual points after Q1 − pre-game expectation for that stretch) on the Q1 deviation:

|       |   coef |     se |      t |      p |
|:------|-------:|-------:|-------:|-------:|
| const | 0.4096 | 0.1864 | 2.1982 | 0.028  |
| slope | 0.0733 | 0.0227 | 3.2223 | 0.0013 |


A game running **+10** over its pro-rated pace after one quarter is expected to finish the remaining three quarters **+0.73** points relative to expectation (t = 3.22).

## Verdict

**No. Scoring rate is mildly persistent, not mean reverting.** Every forward-looking
slope from Q1 is positive except Q1→Q4, and the pooled quarter-to-quarter AR(1) is
**+0.048 (t = 6.71)**. A fast start predicts a *slightly* fast remainder, not a
compensating slowdown.

The single negative coefficient, Q1→Q4 at −0.032 (t = −2.50), is the only thing
resembling reversion and is most likely a blowout artefact rather than a pace
mechanism: a high-scoring first quarter is associated with larger leads, and fourth
quarters of decided games slow down (starters rest, the trailing team stops fouling
once it is out of reach). It is not evidence that the game "corrects" itself.

**The cleanest summary is the half-to-half result: −0.0004 (t = −0.03).** The first
half tells you nothing whatsoever about the second half, once both are measured
against the pre-game line.

**Why the effects are so small: 97.8% of a quarter's deviation is quarter-specific
noise.** Only 2.2% of the variance is a persistent game-level component. There is
very little "this is a fast game" signal to detect, because most of what looks like
a fast quarter is simply variance in a 56-point sample.

### For live betting

A game running +10 over its pro-rated pace after one quarter is expected to finish
the remaining three quarters **+0.73 points** relative to expectation. Directionally
that says nudge the live total *up*, which is the opposite of the common instinct to
take the under after a hot start — but 0.73 points is far too small to bet on.

One thing this data cannot answer: whether the *live* market over-reacts. If books
move the remaining total by more than 0.073 points per point of Q1 deviation, then
the under would be correct — not because the game mean reverts, but because the line
overshot. Testing that needs in-game line history, and this file has only pre-game
opening and closing numbers.

### And the caveat that matters most

This is scoring, not pace. Quarter points correlate 0.51 with combined offensive
efficiency and only 0.23 with game pace, so most of what is measured here is
shooting variance rather than tempo. True pace mean reversion — possessions per
quarter — is untestable without quarter-level possession counts, which would need a
play-by-play source.
