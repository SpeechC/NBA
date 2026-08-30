# PREREG — DTO/NTO DECOMPOSITION OF THE Q4 COMEBACK EFFECT

Written 2026-08-30, BEFORE any outcome was regressed. Only the structural
checks in §2 were run first (`dto_nto_build.py`): turnover classification, cell
counts, era stability. No slope, no test statistic was computed.

## 0. The question, and what it can and cannot produce

`QUARTER_WINNER_AUDIT` records an **unexplained mechanical fact**: trailing
teams gain **+1.65 points of Q4 margin at Q3 deficits of 12+**, monotone in the
deficit, in 8 of 8 seasons. We attributed it to garbage time. Price, Remer &
Stone (`papers/price_remer_stone_subperfect_game_ssrn1377964.pdf`) supply a
second, independent candidate: **referees favour teams losing during games.**

Their identification transfers directly. Referees have **varying discretion
over turnover types**:

```
DTO  discretionary      offensive foul (37), traveling (4)      -- always a whistle, ball live
NTO  non-discretionary  bad pass (1), lost ball (2)             -- player-determined, no whistle needed
```

**NTO is the player-behaviour control for DTO.** This is P/R/S's exact
treatment/control pair — "mainly traveling violations and offensive fouls"
against "mainly bad passes and lost balls" — adopted without modification.

**This is a MECHANISM test, not a market test.** There is no line, no `dev`, no
vig and no P&L in it. It cannot produce a betting edge. It can only tell us
*why* the Q4 regularity exists, which matters because
`QUARTER_WINNER_AUDIT` closed on execution cost with the mechanism still
unexplained.

## 1. The discriminator, stated plainly

| if the cause is | DTO differential vs deficit | NTO differential vs deficit |
|---|---|---|
| **garbage time** (players change: benches, effort, sloppiness) | moves | **moves too** |
| **officiating** (refs favour the trailing team) | moves | **does not** |

Player behaviour cannot move a whistle-only category without also moving the
player-only category. That asymmetry is the whole test.

## 2. Construction and Stage-0 — RESULTS IN HAND

Source: `/mnt/c/NBA2/out/pbp_lineups_all.parquet`, regular season, `PERIOD == 4`,
`EVENTMSGTYPE == 5`, deduplicated. Joined to the master for quarter scores via
`team_mapping.csv`.

```
D      = |Q3 lead|                          (the leading team's margin after 3)
dDTO   = DTO_leading - DTO_trailing         (committed in Q4)
dNTO   = NTO_leading - NTO_trailing
Y      = dDTO - dNTO                        <- the difference-in-differences
```

| check | result |
|---|---|
| games with Q4 turnovers and a Q3 leader | **6,779** |
| seasons | 7 (2017-18 … 2024-25; the stint panel ends there) |
| D ≥ 12 | 2,858 games (42.2%) |
| Q4 turnovers per game | DTO 1.34, NTO 4.06 |
| DTO share of DTO+NTO | 24.8% |
| ERA — DTO share by season | 19.5% – 29.6% (**1.52×**) |

The era range is moderate and is a *level* shift, absorbed by season dummies;
the test is on a **slope in D**, not a level.

**Unconditional means, noted now so they cannot be presented later as the
finding:** `dDTO` is positive in all seven seasons (+0.10 to +0.23) and `dNTO`
is smaller (+0.00 to +0.25). The leading team commits more discretionary
turnovers on average. **That is a level, not the tested slope**, and it is not
evidence for either explanation.

## 3. Predictions — fixed

**P0 POSITIVE CONTROL, runs first.** Reproduce the effect being explained on
*this* panel:

```
q4_trailing_margin ~ D        PREDICTED: > 0, and ~ +1.65 pts at D >= 12
```

If the Q4 comeback effect is not present here, the panel is not the right one
and nothing below is interpretable.

**P1 PRIMARY — the difference-in-differences, one-sided.**

```
Y = dDTO - dNTO  ~  D + season dummies
PREDICTED: beta_D > 0
```

`beta_D > 0` means the *discretionary* differential grows with the deficit
faster than the *player-determined* one — the officiating channel. Pass
requires **Freedman-Lane block permutation p < 0.05 one-sided**, within-season
blocks, 5,000 reps.

**P2 — the competing explanation, reported whatever P1 does.**

```
dNTO ~ D + season dummies
```

A large positive `beta_D` here is **garbage time** and is reported as such. P1
and P2 are not mutually exclusive; both channels can be live.

**P3 — MAGNITUDE, and it decides whether any of this matters.** Convert the
fitted net turnover differential at D ≥ 12 into points at ~1.12 points per
possession and compare to the **+1.65** the audit recorded. If the DTO channel
explains a trivial share, the officiating story is real but irrelevant, and
that is the finding.

## 4. Fixed readings

- **P0 fails → nothing below is read.** The panel is wrong.
- **P1 passes, P2 null →** officiating channel supported.
- **P1 null, P2 positive →** garbage time, as originally attributed.
- **Both positive →** both channels live; P3 apportions them.
- **A significant NEGATIVE P1** is a failure of the registered prediction and
  will be reported as such, not reframed.

## 5. What is NOT permitted

The DTO/NTO membership is **fixed at P/R/S's four codes** and will not be
extended to shot-clock, out-of-bounds, backcourt or goaltending turnovers to
move a result. The D ≥ 12 threshold is **inherited from
`QUARTER_WINNER_AUDIT`**, not chosen here, and no alternative threshold may be
substituted. No fouls are added to the turnover measure — P/R/S use turnovers
precisely because fouls carry the free-throw confound.

## 6. Prior

The garbage-time explanation is the incumbent and has a mechanical basis
anyone can see on a broadcast. The officiating channel is a published finding
on different data and a different outcome variable. I expect **P2 positive**
and regard **P1 as genuinely open** — which is why it is worth one run.

---

# RESULT — run once, 2026-08-30. **P1 PASSES. Both channels are live. Neither explains most of it.**

6,779 games, 7 seasons, D ≥ 12 on 2,858.

## P0 POSITIVE CONTROL — PASSES, and exactly

```
q4_trailing_margin ~ D          +0.06293  (t = +5.68)
mean Q4 trailing margin at D>=12   +1.654 pts       audit recorded  +1.65
```

The panel reproduces the effect being explained to three decimals. Everything
below is interpretable.

## P1 PRIMARY — PASSES

```
Y = dDTO - dNTO  ~  D           +0.00659  (t = +2.05)   FL p1 = 0.0216
```

The discretionary differential grows with the deficit **faster** than the
player-determined one. **The officiating channel is supported.**

## P2 — and the asymmetry is large

```
dDTO ~ D  (whistle)             +0.01170  (t = +7.49)   p2 = 0.0002
dNTO ~ D  (player behaviour)    +0.00511  (t = +1.96)   p2 = 0.0520
```

**The whistle channel moves at 2.3× the rate of the player channel**, and is far
more precisely estimated. Garbage time is present but only marginal on its own
terms. Both channels are live; officiating is the larger.

## P3 MAGNITUDE — the decisive result, and it deflates both

At the mean D ≥ 12 deficit of 19.5, at 1.12 points per possession:

| channel | net turnovers | points | share of +1.65 |
|---|---|---|---|
| DTO (whistle) | +0.228 | +0.256 | **15.5%** |
| NTO (player) | +0.100 | +0.112 | 6.8% |
| **turnover pathway, total** | **+0.328** | **+0.367** | **22.2%** |
| **residual — NOT turnovers** | — | **+1.283** | **77.8%** |

**About four fifths of the Q4 comeback effect does not travel through turnovers
at all.** Whatever produces it is most likely shooting, personnel and shot
selection — channels this test cannot see.

## The deficit profile explains why the two stories were confusable

| D | dDTO | dNTO | Y | Q4 trailing margin |
|---|---|---|---|---|
| 1–5 | +0.056 | +0.019 | +0.037 | +0.492 |
| 6–11 | +0.127 | +0.085 | +0.041 | +1.110 |
| **12–19** | **+0.297** | +0.090 | **+0.207** | +1.458 |
| 20+ | +0.316 | **+0.165** | +0.151 | +1.932 |

`dDTO` rises monotonically throughout. `dNTO` stays flat until the deficit
passes 12 and then **doubles in true blowouts**, which is exactly when benches
empty. So `Y` peaks at 12–19 and *falls* at 20+ — **the officiating signature is
cleanest at moderate deficits, and garbage time overtakes it at extreme ones.**
Pooling the two regimes is what made the single "garbage time" attribution look
sufficient.

## Disposition

`QUARTER_WINNER_AUDIT`'s attribution is **revised, not overturned**. Garbage
time is real. So is officiating, and it is the larger of the two measured
channels. But together they account for **22.2%**, so the audit's central fact
remains **mostly unexplained** — and the residual is now localised to
non-turnover channels rather than being open-ended.

**No tradeable implication, and none is claimed.** §0 fixed this as a mechanism
test with no line, no `dev` and no vig in it. `QUARTER_WINNER_AUDIT` closed the
economics separately: the derivative instruments quoted 15–30c against a 3–6c
edge. Understanding the mechanism does not reopen that.

## What this does NOT license

Per §5: no extension of the DTO/NTO code sets, no alternative deficit
threshold, no addition of fouls. In particular the tempting next step — testing
whether *foul* differentials show the same asymmetry — is **not** authorised
here, because P/R/S deliberately avoid fouls (the free-throw confound) and
adding them would be exactly the kind of post-hoc widening §5 forbids. It needs
its own pre-registration.
