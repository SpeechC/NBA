# STAGE E — WHAT MOVES THE MARKET'S LATENT STATE

Dependent variable is the **market innovation**
`e = MarketImpliedPts - D2 carried-forward prediction`, on a **team-game panel**
(two observations per game). Inputs are **surprises**, never raw performance.
`stageE.py`. sd(e) = 2.04 points.

**Timing safeguard.** No opener timestamps exist, so a conservative rule is
enforced: team-games whose previous game was <=1 day earlier (**17.5%**) are
**excluded** from the primary sample, because the opener may have been posted
before that game finished. Primary n = 14,820; all-rest robustness n = 18,014.

## The update rule IS recovered, with correct signs on both sides

| model | R2 | significant coefficients |
|---|---|---|
| U0 no performance update | 0.0000 | |
| U1 own points surprise | 0.0510 | OffShock **+0.0407** (t=+28.2) |
| U1b + opponent def surprise | 0.0757 | OffShock +0.0391 (+27.4), oppDS **−0.0283** (−19.9) |
| U2 pace + efficiency split | 0.0761 | PaceShock +0.0452 (+15.7), EffShock +0.0379 (+25.1) |
| U3 + eFG surprise | 0.0762 | — |
| U4 + turnover surprise | 0.0762 | — |
| U5 + FTA surprise | 0.0764 | — |
| U7 + rest | 0.0766 | — |

**Both channels behave correctly.** A team scoring above expectation raises its
own next quote (+0.039); an opponent whose defence beat expectation **lowers**
it (−0.028). The negative sign is the right one and confirms the two-sided
structure.

**Pace and efficiency shocks carry nearly the same weight** (+0.045 vs +0.038)
and splitting them adds essentially nothing (0.0757 -> 0.0761). **The market does
not appear to maintain separate pace and efficiency update channels** — at least
not distinguishably.

**Four Factors surprises add nothing** (0.0761 -> 0.0764). This is now the fourth
independent place in the programme where the Four Factors are redundant.

## A DEFECT IN D2 — k = 0.30 is mis-specified

If D2's update rate were right, older shocks would already sit in the carried
rating and add nothing. They add a great deal:

```
lag1 only   R2 0.0757    sh1 +0.0391 (t=+27.4)
+ lag2      R2 0.0976    sh2 +0.0266 (t=+18.9)
+ lag3      R2 0.1090    sh3 +0.0192 (t=+13.8)
+ lag4      R2 0.1139    sh4 +0.0125 (t=+9.0)
```

Coefficients decay at roughly **0.68 per lag**, smoothly and significantly.
**The market's update uses a weighted history of several recent games, and a
single-parameter EWMA at k = 0.30 does not capture it.** Stage D's rating system
works well but its state is too simple; a longer or two-component memory should
fit better. This is a concrete, testable improvement.

## The composed rule — and the market barely moves on one game

```
D2:       rating change    = 0.30  x (quote innovation)
Stage E:  quote innovation = 0.041 x (last-game scoring surprise)
=>        rating change    = 0.012 x (scoring surprise)

a team scoring 10 points above expectation moves its market rating 0.122 points
one sd of scoring surprise (11.3 pts) moves the quote 0.461 pts = 22.6% of an innovation sd
```

## THE DOMINANT FINDING — 92.4% of the revision is NOT recent scoring

```
total sd(e)              2.0407 pts
explained by last game   0.5618 pts
UNEXPLAINED              1.9619 pts   (92.4% of variance)
```

Even with four lags of scoring surprise the model reaches R2 0.1139. **The market
revises each team's quote by about 2 points of sd between games, and recent
box-score performance accounts for under a tenth of it.**

The rest is information this programme does not hold: injuries, lineup and
rotation news, rest decisions, and order flow. This is the same wall met in
Stage B (PIT basketball state reproduces mu worse than the market's own prior
quote) and in `SIGMA_ORIGIN_CHECK` (82% of ladder sigma unexplained), reached
now from a third direction.

## The chain, as it now stands

```
1  Prior market state  +  Update(new information)  =  Current market state
     -> FORM recovered (two-way Off/Def, decaying weights)
     -> INPUT only ~10% recovered; 92% of each revision is non-box-score information
2  mu = Pace* x (PPP_H* + PPP_R*)
     -> architecture confirmed OOS; latent ratings beat box scores by 26% RMSE
3  P(T>K) = 1 - Phi((K - mu)/sigma)                    [Kalshi]
     -> solved; per-rung MAE 0.909c, 78.2% inside the quoted band
```

**Link 3 is solved. Link 2's architecture is confirmed. Link 1's form is
recovered and its inputs are not** — and the binding constraint there is
information the programme does not have, not method.
