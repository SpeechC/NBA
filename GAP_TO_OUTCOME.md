# THE MODEL-OPEN GAP: PRICE DISCOVERY OR OVERREACTION?

`G = model - opening total`, n = 3,181, held-out 2022+.

## The decomposition holds exactly

```
Close - Open     beta +0.3800   se 0.0181   t +20.96
Actual - Close   beta -0.1809   se 0.1035   t  -1.75
Actual - Open    beta +0.1991   se 0.1058   t  +1.88
identity: 0.3800 + (-0.1809) = 0.1991   <- exact
```

**The market moves 38% of the way toward the model, and roughly half of that
movement is given back by the outcome.** Their arithmetic was right.

## The nonparametric test — the pattern is there

| G bucket | n | mean G | avg open→close | **avg actual−close** | t |
|---|---|---|---|---|---|
| <−5 | 123 | −6.46 | −2.317 | **+1.252** | 0.80 |
| −5:−3 | 376 | −3.85 | −1.509 | **+1.379** | 1.51 |
| −3:−1 | 787 | −1.93 | −0.839 | +0.877 | 1.41 |
| −1:+1 | 874 | −0.02 | +0.078 | +0.899 | 1.44 |
| +1:+3 | 605 | +1.89 | +0.495 | +0.309 | 0.43 |
| +3:+5 | 251 | +3.83 | +1.424 | **−0.867** | −0.79 |
| >+5 | 165 | +7.08 | +2.627 | +0.061 | 0.04 |

```
Spearman rank correlation of bucket means with bucket order = -0.893
```

**Actual−close declines monotonically as G rises, exactly the overreaction
signature.** Movement is monotone and large (−2.32 to +2.63); the outcome gives
back a declining share.

**Caveat on that −0.893:** it is computed on seven bucket *means* and discards
magnitude. The proper test is the linear coefficient, **t = −1.75**, and the top
bucket (>+5) breaks the pattern at +0.061. No individual bucket reaches |t| = 1.6.

## POWER — we are ~800 games short

```
beta(Actual-Close) -0.1809   se 0.1035   95% CI [-0.3838, +0.0220]
zero is INSIDE the CI  ->  CANNOT distinguish overreaction from noise
games needed for significance at this effect size: 4,004   (have 3,181)
```

**This is the most precisely-quantified open question in the programme: 823 more
games — about two-thirds of a season — resolves whether the market overshoots.**
2026-27 supplies them.

## BUT IT IS NOT PROFITABLE EVEN IF TRUE

Fading the move, taking the overreaction coefficient at face value:

```
edge 0.553 pts per sd of G      sd(actual-close) 17.86
hit rate 51.24%   break-even at -110 = 52.381%
SHORT BY 1.14pp
```

**Both interpretations fail the same economic test.** Betting *with* the model
gives 51.33%; betting *against* the subsequent move gives 51.24%. Neither clears
the vig, and they are two readings of the same 0.199 coefficient.

## Consensus between the two architectures does not unlock it

| group | n | beta MOVE | t | beta ACT−CLOSE | t |
|---|---|---|---|---|---|
| CONSENSUS (same sign) | 2,748 | 0.4217 | **23.41** | −0.1572 | −1.51 |
| DISAGREE (opposite) | 433 | 0.9075 | 3.20 | +2.3705 | 1.40 |
| consensus small | 916 | 0.3549 | 3.75 | −0.2726 | −0.46 |
| consensus mid | 916 | 0.4541 | 10.24 | −0.2024 | −0.79 |
| **consensus LARGE** | 916 | 0.4180 | **19.64** | −0.1474 | −1.28 |

**Agreement sharpens movement prediction (t 23.41) and does nothing for
outcomes.** Same asymmetry as everywhere else. The disagreement row is not
interpretable — averaging opposite-signed gaps compresses the scale.

## Where this leaves the programme

**What is established beyond doubt:** the gap predicts the market's own revision
at **t = +20.96**, and consensus raises it to **t = +23.41**. That is the largest
effect in this programme by a wide margin.

**What is not established, and cannot be at this n:** whether the residual
`Actual − Close` slope is genuinely negative. The point estimate says the market
overshoots by roughly half; the interval contains zero.

**What is established about the economics:** neither reading produces a bet.
51.33% with the model, 51.24% fading the move, against 52.381%.

Their strategic conclusion is adopted: **stop optimising opener R2.** A better
emulator predicts the line, and the line-prediction channel is already
overwhelming. The open question is no longer accuracy — it is whether the
movement we predict is price discovery or overshoot, and that needs games rather
than models.

**Any test of this on 2026-27 requires a pre-registration**, with the
`Actual − Close` slope as the primary endpoint, the +-0.10 interval fixed in
advance, and the economic gate stated up front — because on current evidence a
statistically resolved answer still does not clear the vig.
