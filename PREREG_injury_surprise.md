# PREREG — Late Injury Surprise: information content, importance scaling,
# prior-status categories, and aggregation

**Written 2026-08-23, BEFORE any surprise state is joined to any line.**
Estimated EXACTLY ONCE. Covers items 1, 2, 4 and 5 of the Information-Arrival
v2 program in one document because they are nested: surprise requires prior
status, importance scales surprise, the categories ARE the conditioning set
that produces the surprise estimate, and aggregation sums the result.

Does NOT modify `PREREG_injury.md`, `PREREG_move_combined.md`,
`PREREG_move_injury_combined.md`, or the frozen `MOVE_COMBINED` signal.
Hypothesis A stays retired; Hypothesis B stays as recorded.

## 0. Two program items are NOT in this document, because they are already answered

**Item 3 (timing/latency) was executed** as `PREREG_injury_absorption.md`,
verdict ABSORBED ON PUBLICATION. It cannot be run at +1/+5/+15/+30 MINUTE
horizons: `OUT_late` first appears a median 8.5h before tip, with 168 events
within 6h, 2 within 3h and **zero within 1h**. At hourly horizons JUMP was
+0.045 (t=+0.29) and the 1h residual -0.441 points (~1.0c against a 3.0c
round-trip spread). Re-running it is not proposed.

**Item 6 (`tpa_s`) rests on a false premise that originated with me**, and the
correction itself needed a second correction. Both are recorded here because
the first version of this section was also wrong.

TRACED TO SOURCE, 2026-08-23:

`tpa_s` is DERIVED, not loaded. TPA = three-point attempts, traced to the
literal columns `3PA_H` / `3PA_R` in `dfMaster_OT_2017-2026.csv`:

```
ref_shock.py:86    extra[f"tpa_{s}"] = n(f"3PA_{s}") / n(f"FGA_{s}")   per side
ref_shock.py:101   shift(1).rolling(W=20, min_periods=10) within (season, team)
ref_shock.py:113   tpa_s = m_tpa_h + m_tpa_a                            summed
```

Team/game-level throughout, never player-level: a team box-score ratio (three
point RATE, share of FGA that are threes), then a prior-only team rolling
mean, then summed across the two teams. It sits in `rsk.CTRL` as one of five
totals-relevant style controls (pace, oeff, deff, ftr, tpa). **Raw missingness
is ZERO** — `3PA` and `FGA` are complete in all 9,489 games.

ERROR 1. "`tpa_s` missing on 2,379" was the LAST LINE of an eleven-line list
that `tail -32` truncated. All 11 CTRL columns are absent on exactly the same
3,845 games. I reported the survivor of my own output clipping as a finding,
then explained it with a merge-collision story that was also false (none of
the CTRL columns exist in `OLE.load()`, so nothing collides).

ERROR 2. I then attributed the loss to the `rolling(20)` team-form controls.
That is the MINORITY of it. There are two stacked early-season warm-ups:

| decile of season | 1 | 2 | 3 | 4 | 5 | 6-10 |
|---|---|---|---|---|---|---|
| survives `cmm.build()` | 0% | 0% | 30.7% | 99.4% | 100% | 100% |
| survives `rsk.build()` | 0% | 0% | 0% | 6.8% | 88.1% | 100% |

- `crew_matchup.build()` loses **2,563 games (67% of the loss)** via its own
  `W, MINP = 20, 10` rolling (crew_matchup.py:60) and
  `dropna(subset=["M","CrewFoul","mu_state"])` (line 70) — the REFEREE
  estimator's warm-up, upstream of any control;
- the CTRL rolling then loses **1,282 more (33%)**, NaN whenever EITHER team
  has fewer than 10 prior games that season.

Net 9,489 -> 6,926 -> 5,644 (59.5%), uniform in every season.

CONSEQUENCE for item 6: there is no missingness mechanism to audit by team,
player, status or source. It is deterministic by calendar position — both
stages are prior-only warm-ups deleting the first ~35% of every season.
Nothing is absent from the data; the estimators cannot yet be formed. Fixing
`tpa_s` would recover nothing (it is not binding and its inputs are complete),
and removing the CTRL warm-up alone recovers only 1,282 of 3,845. Full
recovery would require prior-season carryover in the REFEREE estimator, which
is frozen. This document sidesteps it entirely by carrying no `rsk.CTRL`.

## 1. Prior status and the surprise estimate

For each player-game with a late OUT, `prior_status` = that player's status in
the report immediately PRECEDING the first report showing `Out`, in the frozen
five-way alphabet plus one:

```
Questionable | Doubtful | Probable | Available | UNLISTED
```

`UNLISTED` = the player appears in no earlier report for that game.

```
P(OUT | prior_status)  = among all player-game-reports carrying that status,
                         the fraction whose FINAL pregame status is Out,
                         estimated STRICTLY HISTORICALLY: only report-days
                         earlier than the current game date contribute
                         (expanding, minimum 200 prior observations per cell,
                         else the cell is dropped)
SurpriseOUT            = (1 - P(OUT | prior_status)) * 1(OUT_late)
```

Expanding rather than development-frozen so that no future information enters
any row, including in the holdout.

## 2. Importance, and the shock

```
MIN_SHARE   frozen definition (PREREG_injury.md s2): trailing within-season
            share of team minutes, shift(1), min 10 prior games
InjuryShock = SurpriseOUT * MIN_SHARE
```

`MIN_SHARE` is used because it is the low-missingness importance measure. No
value-adjusted variant is run: the `tpa_s` premise for it is void (section 0).

Game-level states, summed over BOTH teams, over all late-OUT players holding a
valid `MIN_SHARE`:

```
N_LATE = count of late-OUT players
S_LATE = sum of SurpriseOUT
I_LATE = sum of InjuryShock          <- the headline state
```

Note these are UNRESTRICTED by role, unlike the frozen `OUT_late` of Hypothesis
B, which is SALIENT-restricted (top-3 minutes). The frozen state is retained
as an incumbent control so the comparison is like-for-like.

## 3. Specification

```
tmove = a + bR*MOVE_RIDGE_OOS + bL*MOVE_LATENT_OOS + bO*OUT_late_frozen
            + bS*S_LATE            (model S)
tmove = ... + bI*I_LATE            (model I, the headline)
```

Sample: control-free, 2020-21..2024-25, both movement signals present
(5,078 games). Development 2020-21..2023-24; holdout 2024-25 reported
separately, with its single-season power stated.

## 4. Predictions

- `bS < 0` and `bI < 0`: more surprising, more important absences move the
  total further DOWN.
- Surprise buckets (terciles of `SurpriseOUT` among treated games) are
  MONOTONE in mean movement.
- Importance buckets (quartiles of `MIN_SHARE`) are MONOTONE in mean movement.
- Prior-status categories, prespecified and reported in this fixed order,
  never reordered after seeing results:
  `Questionable->Out`, `Doubtful->Out`, `Probable->Out`, `UNLISTED->Out`.
- Aggregation: two meaningful absences move roughly twice one. Tested as a
  linear-vs-threshold contrast on `N_LATE` in {1, 2, >=3}, NOT by searching a
  breakpoint.

## 5. Decision rule, fixed before estimation

`I_LATE` (or `S_LATE`) is INFORMATIVE only if ALL hold:
- coefficient negative with |t| >= 2 on development;
- SAME SIGN on holdout;
- within-season permutation p < 0.05 on development (5,000 reps, state
  permuted across games within season);
- surprise buckets AND importance buckets both monotone on development;
- incremental R2 over {ridge, latent, `OUT_late_frozen`} reported (no
  threshold imposed — the question is direction and displacement, not size).

SEPARATE, and the point of the exercise: if `I_LATE` absorbs most of
`OUT_late_frozen`'s coefficient (|bO| falls by >= 50% and loses |t| >= 2), the
conclusion recorded is that the market reacts to surprise-weighted importance
rather than to the raw late-OUT event. If `OUT_late_frozen` survives
undiminished, the conclusion is that raw occurrence is what matters and the
refinement adds nothing.

## 6. Prohibited

- estimating more than once, or re-estimating after seeing any cell
- tuning the status alphabet, the 200-observation floor, bucket counts,
  window lengths, or any sign after outcomes are observed
- role definitions of any kind — defensive anchor, rim protector, sixth man,
  archetypes. Hypothesis A is retired and is not reopened through this door.
- injury type, severity, or body part
- promoting anything into `MOVE_COMBINED`
- any tradability claim: `PREREG_injury_absorption.md` closed that on Kalshi,
  and nothing here reopens it

## 7. Known risks, recorded in advance

1. `SurpriseOUT` and `MIN_SHARE` may be negatively correlated in practice —
   stars are watched and therefore rarely UNLISTED, so the most surprising
   absences may be the least important ones. If so `I_LATE` is a product of
   two opposing factors and may be weaker than either. This is a real
   possibility, not a defect, and will be reported as measured.
2. The frozen `OUT_late` is SALIENT-restricted while the new states are not,
   so part of any incremental signal is simply broader coverage rather than
   surprise content. The `N_LATE` term is included to absorb pure count
   effects and make that separable.
3. One holdout season (1,009 games in this sample). Stated on every holdout
   line.
4. Prior status is observed at hourly report granularity; a status that
   changed twice inside one hour is seen once.
