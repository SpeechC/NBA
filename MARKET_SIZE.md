# Do big betting markets skew the lines?

Yes — but at the **opener**, not the close, and in the opposite direction to the
usual "public money inflates popular teams" story. The residual is about a tenth
of what would be needed to trade.

Market size measured by metro population: objective, external, fixed before
looking at any outcome. 7,221 games.

## Test A — is the CLOSING line biased? No.

| regression | coef | t | p |
|---|---|---|---|
| excess margin ~ log population differential | +0.016 | 0.11 | 0.91 |
| excess total ~ combined log population | −0.105 | −0.53 | 0.60 |

Big-market teams cover at exactly their fair rate. The classic "fade the public
team" edge, documented in the 1980s–90s literature, is not present in 2017-2024.

## Test B — does the line MOVE with market size? Yes, and away from them.

| regression | coef | t | p |
|---|---|---|---|
| **spread move ~ log population differential** | **−0.057** | **−2.70** | **0.007** |
| total move ~ combined log population | +0.046 | 1.36 | 0.17 |

Negative means: the larger the home team's market, the more the line moves
*away* from them between open and close. Monotone across quintiles:

| population differential | mean spread move |
|---|---|
| away much bigger | +0.053 |
| 2 | +0.016 |
| even | −0.005 |
| 4 | −0.080 |
| home much bigger | −0.118 |

At team level, **corr(metro population, line moves toward team) = −0.333**.
Lines drift toward Utah, Atlanta, Sacramento, Minnesota, Indiana; away from
Brooklyn, the Clippers, Chicago, the Lakers.

## The mechanism these three results imply

Books do not wait for public money to arrive and then chase it. They **shade the
opening number toward the popular team in advance**, anticipating the handle.
Sharp money then takes the other side, and the line drifts back. By the close the
shading is gone, which is exactly what Test A shows.

So market size is real and it is priced — just earlier in the cycle than the naive
story assumes. The direction of any exploitable flow is to back the **smaller**
market at the opener, not the larger one.

## Is the residual worth anything? No.

**Naive strategy — always back the smaller market at the open:**

| n | CLV | 95% CI | beat close |
|---|---|---|---|
| 5,128 | **+0.073** | [+0.016, +0.130] | 44.3% |

Statistically positive, and about **10% of the ~0.70 points of CLV** the spread
market requires. It also fails two quality checks: beat-close is below 50%, so the
positive mean rests on a thin tail rather than consistency; and it does not scale
with the population gap (0.082, 0.025, 0.087, 0.101 across quartiles of the gap),
which a genuine mechanism should.

**Added to the movement model:** nothing.

| feature set | corr(pred, move) | CLV | beat close |
|---|---|---|---|
| baseline | 0.0793 | +0.171 | 46.1% |
| + market size | 0.0799 | +0.145 | 45.6% |

Correlation identical to three decimals; CLV slightly worse. Whatever market size
carries, the movement model — which already sees the opening line — has it.

## Verdict

The intuition is half right in an interesting way. Market size demonstrably moves
NBA lines (t = −2.70, monotone, corroborated at team level), but the effect lives
in the opening number as deliberate book shading, is corrected by the close, and
leaves a residual roughly a tenth the size required to trade. It adds nothing to
what we already model.
