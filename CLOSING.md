# NBA closing-market branch: final state

## What is actionable

**Final 7 days of the regular season — bet the game total OVER.**

| | |
|---|---|
| out-of-sample rate | **55.29%** (LOSO window selection, 454 bets) |
| matched-window permutation | 97.2nd percentile (null 50.10% ± 3.46) |
| distribution | central shift — median +2.50, trimmed +2.58, skew +0.10 |
| market correction open→close | **2.4%** of a +3.05 point error |
| seasons above break-even | 7 of 8 (only failure: 2020-21, when April was not the end) |
| volume | ~67 bets/season, ~$6,700 risked at $100 flat |
| expected | **+$447/season**, sd ~$777, ~28% of seasons lose |
| to establish at 80% power | **24 seasons** |

Entry timing is irrelevant — the over rate is 56.00% at the opener and 56.93% at
the close, and the line moves +0.074. No race, no stale-number risk.

## What is NOT established

**Pre-All-Star 3-day window.** 60.47% over, +2.82 residual, 6 of 8 seasons, and
it survived its own matched-window null at p = 0.0006. But it was selected as the
best of seven pre-specified regimes, and the **family-wise max permutation gives
p = 0.0712** — it does not clear correction for that search. Also note the tested
window is 3 days, not a week; a 7-day version was never specified or run and
should not be adopted post hoc.

Treat it as the strongest untested lead, not a second strategy. Combined with the
final week it would be ~88 bets/season, but one leg is unvalidated.

⚠ And the falsification failed: ordinary games before a 4+ day team rest show
**nothing** (49.92% / 50.34%, p = 0.32). So the "anticipated cessation of
competition" mechanism is not supported, and both calendar windows currently lack
a working explanation.

## What was measured as real and found priced

| structure | sports side | market side |
|---|---|---|
| visitor pace allocation | t = **7.57**, λ = 0.777, persistence +0.43 | t = **0.35** vs DK H1 |
| rematch pace persistence | r = **0.51**, t = 11.4 | c* = 0.102 vs c_DK = 0.0666; gap t = **0.76** |
| H1/H2 asymmetry | +2.49 pts, t = **14.1** | live 2H line adjusts in the right direction |
| spread → moneyline | R² = 0.916 | book's deviation informative, **+0.78** |
| FG → H1 allocation | — | book's deviation informative, t = **6.28**; β = 1.25 stable, **untradeable (47.4%)** |
| market bias vs close | +0.543 pts, t = 2.81 | needs 1.08 to clear the vig |
| spread slope | 0.9368, ~3.4 se from 1 | ~1.6pp, below the 2.38pp hurdle |
| margin variance ~ \|spread\| | t = **5.59** | moneyline calibrated within 1.2pp everywhere |

**Predictability of basketball is not predictability of market error.** Every
structure above is strongly real. None survives against `actual − closing price`.

## What to preserve

1. **The three-stage architecture.** Sports signal → market response → tradable
   residual. It killed the rematch idea in one run.
2. **Reverse-engineering the book.** Recovering c* = 0.102 against c_DK = 0.0666
   is far stronger evidence than "our model cannot beat the line."
3. **Derivative pricing is not `f(primary)` alone.** It is
   `f(primary) + book-specific information`, and that discretionary component is
   informative rather than noise — demonstrated twice.
4. **Stage 1.0, the knowability audit.** Three look-ahead errors this project,
   each producing the best numbers on screen before being caught, none detected
   by any statistical control.

## The conclusion, stated at its defensible width

> Across the public-data structures we could identify and test cleanly,
> DraftKings' NBA closing markets absorbed the economically relevant information
> well enough that no residual edge survived transaction costs.

Not "the NBA cannot be beaten." A statement about these markets, at this book,
using public historical data.

## Next

Change market, not features. The target keeps the ingredients that made these
experiments clean — strong underlying state, observable price — and weakens the
efficiency prior: less-liquid sports, less-liquid derivatives, newly introduced
markets, or states requiring difficult data engineering.

Carry the rule: **do not build a strategy until a variable predicts a market
residual out of sample.**
