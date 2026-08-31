# MONEYLINE — SOURCE ATTRIBUTION OF THE 20-GAME TEAM ERROR (2026-08-30)

The block atlas established that a 20-game team margin-error contribution is real
(`w_EB = 0.4386`) and does not carry forward. This asks **what creates it** — the
margin analogue of the decomposition that exposed pace for totals.

## Exact decomposition, no substitution ordering

Two identities, both verified on 4,554 games:

```
OE = 100*[ V*(r3*3*p3 + (1-r3)*2*p2) + ftr*pft ]      MAE 0.00828
V  = 1 + orb - tov - 0.44*ftr                          MAE 0.02080
```

`V = FGA/POSS`, `r3 = 3PA/FGA`, `p3/p2/pft` conversion, `ftr = FTA/POSS`,
`orb/tov` per possession. The second identity lets the shot-volume channel be
split into rebounding, turnovers and free-throw generation **exactly**, so no
component is buried inside another.

First-order attribution around each team's prior-only (K=15) component forecast,
with an explicit interaction residual and a `state_lvl` term for the gap between
that rolling forecast and the frozen state engine. **The attribution closes to
MAE 0.000000.**

## Where the team error comes from

Game-level sd of the team contribution: **13.929 pts**.

| source | kind | var share | EB weight | next-block r | t |
|---|---|---|---|---|---|
| **3P conversion** | REALIZATION | **38.7%** | **0.0000** | −0.1375 | −2.73 |
| 2P conversion | REALIZATION | 29.3% | 0.3157 | +0.1799 | +3.71 |
| FT conversion | REALIZATION | 2.5% | 0.0000 | −0.1856 | −3.69 |
| shot mix (3PA rate) | structural | 0.1% | 0.2125 | +0.0526 | +1.14 |
| offensive rebounding | structural | 8.7% | 0.1006 | +0.0564 | +1.10 |
| **turnovers** | structural | 7.9% | **0.4747** | **+0.3643** | **+7.42** |
| **FT generation** | structural | 1.8% | **0.3676** | **+0.3356** | **+6.82** |
| interactions | — | 4.5% | 0.0000 | −0.0255 | −0.52 |
| state-engine level | MODEL | 6.5% | 0.8710 | +0.5765 | +12.08 |

```
REALIZATION 70.5%   |   STRUCTURAL 18.4%   |   MODEL level 6.5%
```

**This is mostly Outcome 1, with a real Outcome 2 minority.** Shooting realization
is 70.5% of the variance, and its dominant piece — 3P conversion at 38.7% — has an
empirical-Bayes weight of **exactly zero** and mean-reverts (r = −0.14). But
turnovers and FT generation genuinely persist block to block, at r = +0.36 and
+0.34 with EB weights near 0.4.

## A baseline caveat that governs the offence/defence split

The attribution baseline is each team's **own** trailing component average, with no
opponent adjustment. That makes the split mechanical:

| source | EB off | r off | EB def | r def |
|---|---|---|---|---|
| 3P conversion | 0.0000 | −0.4798 | 0.1528 | +0.0319 |
| 2P conversion | 0.0000 | −0.4542 | 0.5188 | +0.4630 |
| turnovers | 0.0000 | −0.4569 | 0.6780 | +0.5783 |
| FT generation | 0.0000 | −0.3729 | 0.5258 | +0.5081 |
| state-engine level | 0.7757 | +0.0862 | 0.9422 | +0.8023 |

Own-offence deviations mean-revert at r ~ −0.45 — that is regression to your own
trailing mean, arithmetic not basketball. Opponent-offence-against-you persists at
r up to +0.58 because **your defence is a real, persistent property the baseline
omits.** So the persistent structural sources may be measuring opponent adjustment
the market already prices, rather than model error. Only the prospective test can
separate those.

## PROSPECTIVE TEST — the separator

State frozen at the end of block `b`, applied to block `b+1` only. Target is the
**book's** margin error, n = 3,349 games.

| source (prior block) | beta margin | t | beta moneyline | t |
|---|---|---|---|---|
| 2P conversion | +0.0092 | +0.17 | −0.00266 | −0.50 |
| offensive rebounding | +0.0990 | +0.88 | +0.00067 | +0.06 |
| **turnovers** | −0.1523 | **−1.66** | −0.00737 | −0.81 |
| **FT generation** | +0.1573 | +0.72 | +0.02539 | +1.18 |
| shot mix | −0.4712 | −0.54 | −0.09108 | −1.30 |
| state-engine level | −0.0193 | −0.33 | +0.00070 | +0.12 |

```
joint (all six): R2 0.00139   sd(fitted) 0.507 pts   vs the 0.812 pt bar
```

**Nothing reaches |t| = 2 on either target**, and the strongest single term
(turnovers) is negative. The caveat above is confirmed: turnover and
foul-drawing persistence is real basketball that the book already prices, not an
error we can trade.

## The answer, stated properly

Previously: *"efficiency dominates margin errors, and efficiency is largely
random."* That was coarse. What the decomposition establishes:

**Of the real, temporary, 20-game team-specific margin error:**
- **70.5% is shooting realization**, of which the largest single piece is 3P
  conversion at 38.7% of variance with an EB weight of **exactly 0.0000** — it is
  pure noise at the block level and mean-reverts thereafter.
- **18.4% is structural** (possession generation and free-throw generation). Two
  of those components — turnovers and FT generation — **do persist**, at r ~ +0.35.
- **6.5% is our state engine's level**, the most persistent term of all
  (r = +0.58), which is the engine's opponent adjustment working, not failing.
- **None of it predicts the book's error one block forward.**

For totals the decomposition exposed **pace** as a structural mechanism the market
mispriced. For margin the corresponding structural mechanisms exist — turnovers
and foul drawing — but the market already has them. The mechanism that dominates
margin error is 3P conversion, and it is the one component with zero persistence
at any horizon.

## Untested

Rim-rate and shot-location splits of the 2P channel. 2P conversion is the one
realization component with non-trivial persistence (EB 0.3157, r = +0.18), which
is what shot-quality drift would look like — but its prospective coefficients are
t = +0.17 (margin) and t = −0.50 (moneyline), so any rim-rate refinement would
have to overturn a null, not extend a signal.
