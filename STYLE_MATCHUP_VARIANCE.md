# STYLE-CONDITIONED MATCHUP PACE VARIANCE — the model predicts the structure, the data does not deliver it

Their objection was correct: team main effects are structurally unable to detect
style-interaction heterogeneity, because a team predictable against one style and
not another averages to zero. Built and tested. `style_matchup_variance.py`.

## What was built

Prior-only team style states: mean pace, transition share (PBP early-clock),
turnover rate committed and forced, FTA rate, plus a **pace-control coefficient**
`b_i` from regressing each team's game pace on the opponent's pace preference
(low |b| = imposes its own tempo), heavily shrunk.

Matchup features: `PrefConflict = |P_H - P_R|`,
`ControlConflict = PrefConflict x |b_H| x |b_R|`, `TransComp`, `TovPressure`,
`FtrSum`, `StyleDist`, plus both teams' volatility.

**NOT built** (data absent): OREB rate (master has total rebounds only),
possession-duration SD, explicit early/late-clock split, pace-when-ahead/behind,
and the pair random effect was tested only as M3.

## RESULT — style features do not beat team effects, or a constant

Held-out log-likelihood:

```
season   n      M0       M1 team   M2 style   M3 both    M2-M1
2024    942   -2627.2   -2626.3   -2631.9   -2631.9    -5.60

M1-M0 +0.91    M2-M0 -4.69    M2-M1 -5.60    M3-M2 -0.03
```

**M2 loses to M1 by 5.60 nats and to a CONSTANT by 4.69.** Adding the pair random
effect (M3) changes nothing (−0.03).

Quintiles of the M2 prediction:

```
Q1 pred 3.408 -> ACTUAL 4.006      Q4 pred 3.837 -> ACTUAL 3.883
Q2 pred 3.621 -> ACTUAL 3.620      Q5 pred 4.007 -> ACTUAL 4.182
Q3 pred 3.739 -> ACTUAL 3.927
Q1 4.006 -> Q5 4.182   ratio 1.0438   F p = 0.5571   DOES NOT SEPARATE
```

All style coefficients are tiny on the log-variance scale: ControlConflict
+0.0414, TovPressure +0.0410, FtrSum +0.0360, TransComp +0.0297, and
**StyleDist −0.0576 — negative**, i.e. more stylistic distance predicts *less*
pace variance, backwards from the mechanism.

## THE DIAGNOSTIC — the model generates the hypothesised structure and it evaporates

```
predicted matchup sd:  min 2.812   max 4.366   range 1.554 possessions = 3.57 pts
their hypothesis:            3.3 -> 4.8        range 1.5   possessions = 3.45 pts

mean WITHIN-team range across opponents   0.794 possessions
between-team spread of medians            0.118 possessions
ratio 6.71   -> the model says matchup structure DOMINATES team structure
```

**The model produces almost exactly the structure hypothesised** — a ~1.55
possession spread across matchups, with within-team variation 6.7x the
between-team variation. Boston's predicted sd ranges 3.04 to 3.78 across
opponents; Denver's 3.26 to 4.37.

**And none of it verifies.** Predicted quintile spread is 3.408 -> 4.007 (0.60
possessions); realised is 4.006 -> 4.182 (0.18), non-monotone. **The model
delivers under a third of the spread it forecasts, in the wrong order.**

That is the signature of overfitting, not of a signal we are failing to extract —
consistent with M2 scoring *worse than a constant* out of sample.

## LIMITATION — this is one held-out season

```
n = 1,885 usable, seasons 2023-2024;  ONE evaluable held-out season (942 games)
```

The PBP transition data ends 2024-25 and the prior-only style states consume a
season of history, so the panel collapses. **This is weak evidence.** The
likelihood differences are a few nats, and one season cannot settle a hypothesis
of this shape.

**What it does establish:** on the data available, style-matchup features add
nothing and actively hurt, and the large matchup structure they generate does not
correspond to realised dispersion.

**What it does NOT establish:** that style-conditioned pace uncertainty is absent.
Four of their specified inputs could not be built, and a single held-out season
is thin. The honest verdict is **no supporting evidence, on a test too small to
be decisive.**

## Consequence

The betting interaction is **not** reopened. Their condition was that a materially
better matchup model produce real separation (e.g. 3.3 vs 4.8) before one final
frozen test. **The model produces that separation in prediction and fails to
deliver it in realisation (p = 0.5571)**, so the condition is not met.

The three-level decomposition now reads:

```
Var(PaceError) = Team (+0.91 nats, negligible)
               + MatchupStyle (-5.60 nats, WORSE than team effects)
               + PairSpecific (-0.03, nothing)
               + Noise (everything else)
```
