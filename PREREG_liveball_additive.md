# Pre-registration: live-ball turnover composition as an additive component

**Written before any outcome was examined.**

## Split — 2024-25 is sealed

```
development     2017-18 .. 2023-24     seven seasons
sealed holdout  2024-25                ONE untouched test
2025-26         UNAVAILABLE            play-by-play ends at 2024-25
```

2024-25 is used for nothing except the final outcome read: no feature definition,
no window selection, no sign selection, no threshold, no model selection.

## Recovered definitions — frozen, not re-created

From `/mnt/c/NBA2/build_nba_advanced_sidecars.py`, verified in source:

```python
is_tov      = (EVENTMSGTYPE == 5)                                    # line 355
is_live_tov = is_tov & upper.str.contains(r"\bSTEAL\b")              # line 362
EV_LIVE_BALL_TOV = sum per (GAME_ID, ADV_EVENT_TEAM_ABBR)            # line 446
ADV_START_AFTER_STEAL = STARTTYPE contains r"\bSTEAL\b"              # line 548
```

`PLAYER1` identifies the acting team for turnovers, so `EV_LIVE_BALL_TOV_H`
counts turnovers the HOME team **committed**. Verified empirically:
`corr(PBP_START_STEAL_SHARE_H, EV_LIVE_BALL_TOV_R) = +0.9778` against
`+0.0097` for the home-side version.

No new live-ball definition is created.

## Coverage rule

Games lacking successful possession context are **excluded entirely**. Missing
possession data is never read as zero turnovers or zero possessions, and such
games never enter a team's rolling history. Development coverage is 100% in
every season except 2023-24 at 99.83%, against a required floor of 95%.

## The state, frozen

```
W = 20 games, min_periods = 10, within season, shift(1)     strictly prior-only

LBTO_off(i,t) = sum(live-ball TOV committed by i) / sum(i's possessions)
                over i's prior W games
LBTO_def(j,t) = sum(live-ball TOV committed by j's opponents)
                / sum(those opponents' possessions), over j's prior W games

LBPressure = z(LBTO_off_home) + z(LBTO_def_away)
           + z(LBTO_off_away) + z(LBTO_def_home)
```

Standardisation uses **development-only** means and standard deviations, frozen
before 2024-25 is touched. A standardised additive form is used deliberately
rather than a product: it is interpretable and not driven by extreme values.

## Direction, specified in advance

Higher `LBPressure` means more live-ball turnovers, hence more steal-started
possessions, which are worth measurably more than ordinary ones (1.2996 PPP
versus 1.1121 in raw possession data). So `LBPressure` is an **OVER** signal.

```
beta_L > 0
```

A sign reversal is failure. The sign will not be revisited.

## The chain

```
LBPressure -> realised live-ball turnovers per 100 possessions
           -> realised steal-started possession share
           -> realised points on steal-started possessions
           -> ACTUAL total
```

separately

```
LBPressure -> CLOSING total
```

The market-omission statistic is `c_true - c_market`.

## The additive test

```
Residual = actual_total - closing_total
Residual = a + bR*CrewShock + bL*LBPressure + bLg*LeagueFoulState + X'b + eps
```

`CrewShock`, `LeagueFoulState` and the +0.8682 threshold are loaded from
`ref_features.csv`. They are not rebuilt, retuned or reinterpreted. X is the
same 11 full-coverage team controls used in the final referee identification.

## Evaluation hierarchy — a single sealed season cannot prove an edge

Significance in 2024-25 is **not** required for an effect of +0.3 to +0.5 points.
A candidate advances only if all of:

1. the mechanism works strongly in development
2. the development residual coefficient has the predicted sign
3. the specification is frozen before 2024-25 is examined
4. the 2024-25 coefficient retains the same sign
5. `bR` remains materially unchanged
6. `|corr(LBPressure, CrewShock)|` stays small, preferably < 0.10
7. the economic combination improves the expected closing residual in holdout,
   even where win-rate significance is weak

Classification:

- strong mechanism + same-sign 2024-25 residual -> `ADDITIVE_CANDIDATE_AWAITING_FORWARD_OOS`
- mechanism works but holdout residual reverses -> `NO_ADDITIVE_EDGE`
- mechanism itself fails -> `STRUCTURAL_HYPOTHESIS_FAILED`

No threshold search. If an economic test follows it uses development Q85 of the
fitted additive score, matching the selectivity of the frozen CrewShock strategy.
