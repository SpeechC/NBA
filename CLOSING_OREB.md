# OREB possession-extension branch: closed

`OREB_EXTENSION_MECHANISM_CONFIRMED` + `OREB_HYPOTHESIS_FAILED`
+ `SECOND_CHANCE_VALUE_NOT_FORECASTABLE`

## Conclusion

> Offensive rebounding is forecastable and reliably generates second-chance
> scoring, but most of that gross scoring represents recovery following weaker
> first-chance scoring rather than incremental game-level offense. The
> resulting net totals effect is small, unstable, and reverses in the sealed
> holdout, providing no evidence of a closing-total omission.

## The accounting, stated without causal overreach

Realized extensions are themselves outcomes of missed shots, so the
contemporaneous regression embeds selection. The association, not a causal
per-rebound value:

> Possessions containing additional offensive-rebound extensions generate about
> 0.89 gross second-chance points per extension, accompanied by substantially
> lower scoring elsewhere, leaving about 0.24 points of contemporaneous net
> scoring association.

```
per realised extension, development
  second-chance FGA              +0.8064
  second-chance FTA              +0.2682
  GROSS second-chance points     +0.8850
  first-chance points elsewhere  -0.6062      68% offset
  total possessions              -0.1100      not the offset channel
  NET association                +0.2443
```

## Why it fails structurally

A team cannot rebound a made shot. The chain is not
`OREB -> extra points layered on an unchanged process`, it is

```
lower first-chance conversion -> more reboundable misses
                              -> more extensions -> partial recovery
```

The prior-only placebo makes this explicit: expected extensions predict
FIRST-chance points at **-0.572 (t=-2.83)** development and **-1.458 (t=-3.91)**
sealed. The prospective state identifies a different *composition* of scoring,
not a reliably higher *amount*.

## The causal/tradable answer

```
prior-only expected extensions -> ACTUAL total
  development     +0.231  (t=+1.16)
  SEALED 2024-25  -0.451  (t=-1.18)

c_true - c_market
  development     +0.311
  SEALED 2024-25  -0.355     sign reversal
```

Quintiles non-monotone in both windows. Not a threshold, nonlinearity or power
problem — simply not a stable pricing omission.

## Two rescues the data forecloses

**Matchup rescue.** `prior own OREB rate -> realised: beta 0.646, t=28.8`, while
`prior opponent OREB allowed: beta 0.011, t=0.32`. The forecastable component is
almost entirely an offensive team trait, not a matchup against weak defensive
rebounding. Do not build `OREB offense x weak DREB opponent`.

**Team-value rescue.** Second-chance value per extension: game-level prior
correlation r=0.027 (detectable only because n=11,987), season-to-season 0.168.
Too weak for team-specific value; the league prior of 1.0334 pts/extension is
the correct fallback. There is no latent OREB component left to model.

## Method note worth keeping

The first specification built `expected extensions = expected rate x REALISED
possessions`, leaking same-game information and turning the state into a pace
proxy. It produced `c_true = +1.72`, `gap = +1.43` — a result that would have
looked excellent. The pre-specified first-chance placebo exposed it immediately
(+1.83, t=11.21). Corrected, the gap fell to +0.31 and then went negative in
holdout.

A generic feature search would have reported the original number as an OREB
anomaly. The structural chain plus placebo is what prevented it.

## Related: live-ball turnovers are already retired

Tested earlier in the same session (`liveball_additive.py`,
`PREREG_liveball_additive.md`). The mechanism was strong and replicated —
LBPressure -> live-ball TOV per 100 `+0.2185 (t=+12.53)` development,
`+0.1684 (t=+3.28)` sealed; -> points on steal-started possessions
`+0.6187 (t=+10.54)` / `+0.4052 (t=+2.42)`. Steal-started possessions are worth
1.3061 PPP against 1.1145 otherwise.

But the actual total did not move: `-0.0132 (t=-0.08)` development,
`-0.6084 (t=-1.38)` sealed, with the closing residual wrong-signed in both.

The reason is the mirror image of the OREB result. A live-ball turnover does not
*create* a high-value possession, it *converts* one: the stealing team gains
+0.19 PPP on a possession it was going to have anyway, while the team that lost
the ball forfeits a ~1.11 PPP possession and scores zero. Net expectation is
roughly **-0.9 points per live-ball turnover**, not positive. The two-sided
property is why it nets negative, not a reason to expect a totals effect.

Both branches share one lesson: **within-possession or between-possession
reallocation is not the same as incremental scoring**, and only the latter moves
a total.
