# PREREG — intraday absorption of late-OUT information in the Kalshi totals ladder

**Written 2026-08-23, BEFORE any line is reconstructed from the candle store.**
Estimated EXACTLY ONCE. Supersedes the minute-scale design sketched in
`PREREG_move_injury_combined.md` section 7, which section 9 of that document
refuted on timing grounds (`OUT_late` first appears a median 8.5h before tip;
zero events within 1h).

Horizons fixed by instruction: **1, 2, 4, 8 hours after the report.**

---

## 1. The question

Hypothesis B established that late OUT information is a third, partially
independent channel in open->close total movement. That is a decomposition
result over a whole day. It cannot say whether any of the movement remains
available once the report is PUBLIC.

This document asks exactly one thing:

> Of the total price response to a late OUT designation, how much occurs AFTER
> the report is observable, at horizons of 1, 2, 4 and 8 hours?

## 2. Data

- Line path: `kalshi_nba_candles.sqlite`, 1-minute bars, 2025-10-21..2025-12-22,
  1,256,843 rows / 4,719 markets / 429 games / 62 dates.
- Tipoff and rung geometry: `kalshi_nba_totals.sqlite` (**read-only** — see the
  pipeline hazard in `PREREG_move_injury_combined.md` section 9).
- Events: `injury_status_panel.csv`, `OUT_late` per the frozen definitions in
  `PREREG_injury.md` section 2.

This is the 2025-26 season, which is EXCLUDED from the A/B/combined analysis
windows by the Q1 resolution. That is deliberate and not a contradiction: the
exclusion was for a season-long pricing test needing unskewed composition,
whereas this is an intraday microstructure measurement on individual events.
It is nonetheless a DIFFERENT season from the one the channel was established
on, and no result here revises Hypothesis B.

## 3. Line reconstruction, fixed now

At each minute bar, each rung `i` gives a mid `p_i = (yes_bid + yes_ask)/2` for
`P(total > floor_strike_i)`. Define the implied line `L(t)` as the **median**:
the strike at which the survival curve crosses 0.5, by linear interpolation
between the two bracketing rungs.

Frozen requirements for a usable `L(t)`:
- at least 4 quoted rungs at that minute, both-sided (`bid>0` and `ask>0`);
- the crossing must be BRACKETED (a rung above 0.5 and a rung below 0.5) — no
  extrapolation beyond the quoted ladder;
- monotonicity enforced by sorting on strike; non-monotone mids are averaged,
  not discarded.

The median is chosen over a mean because it needs only the local rungs around
the crossing, so it is robust to the ladder's ends being unquoted. No
alternative estimator will be tried after seeing results.

## 4. Event and measurement

Unit of observation = **one game**, at the first minute `t0` at which ANY
`OUT_late` designation for that game appears in a report. Treatment magnitude
= the frozen MIN_SHARE-weighted `OUT_late` sum for that game.

`t0` resolution is the report stamp (hourly); the publication instant is taken
as the stamp.

```
L_pre  = last usable L(t) strictly BEFORE t0            (pre-report state)
L_0    = first usable L(t) at or AFTER t0               (your earliest entry)
L_k    = usable L(t) nearest to t0 + k, k in {1,2,4,8}h, tolerance +/-15 min

JUMP     = L_0 - L_pre        -- response already gone by the time you can act
RESIDUAL = L_k - L_0          -- the only economically available quantity
```

**Censoring, pre-stated:** any horizon whose target time falls at or after
tipoff is DROPPED, not clipped. With a median `t0` of 8.5h before tip, the 8h
horizon will be heavily censored and its `n` will be far smaller than the 1h
horizon's. Every horizon reports its own `n`. A shrinking `n` across horizons
is expected and is not evidence of anything.

## 5. Control arm (required — without it intraday drift masquerades as absorption)

For every treated game, a matched control: a game on the SAME date with NO
`OUT_late` event, assigned the same pseudo-`t0` clock time, measured
identically. The reported estimate is the **difference** treated minus control
at each horizon. A raw treated-only drift is not interpretable, because the
whole ladder drifts intraday for reasons unrelated to injuries.

## 6. Predictions

`OUT_late` lowers the total (bI < 0 in both prior estimates). Therefore:

- `JUMP` < 0 — the market reacts on publication;
- if the channel is fully absorbed on publication, `RESIDUAL_k` ~ 0 at all k;
- if absorption is gradual, `RESIDUAL_k` < 0, growing in |k|.

## 7. Decision rule, fixed before estimation

TRADABLE at horizon k requires ALL of:
- `RESIDUAL_k` negative with |t| >= 2 against the control arm;
- |`RESIDUAL_k`| >= **1.0 point** of total (about 2.2pp of win probability at
  the money, sd 18.08) — below this the 3.0c median spread plus fees eats it;
- monotone in the treatment weight (heavier weighted absences move more).

Anything else is recorded as **ABSORBED ON PUBLICATION** — the scientific
result stands, the trading interpretation is closed, and no further horizon,
weighting or subset will be searched.

## 8. Prohibited

- estimating more than once, or after inspecting any P&L
- adding horizons beyond {1,2,4,8}h, or re-cutting after seeing the result
- alternative line estimators, alternative event definitions, or dropping the
  control arm
- writing to `kalshi_nba_totals.sqlite`
- any claim about seasons other than 2025-26 from this estimate

## 9. Known limitations, recorded in advance

1. `t0` is hourly, so `JUMP` absorbs up to an hour of true reaction and
   `RESIDUAL` is correspondingly conservative. This BIASES TOWARD "absorbed"
   and cannot manufacture a false positive.
2. Roughly the top decile of events first appears >12h before tip, outside the
   candle lookback; those games lose `L_pre` and are dropped.
3. One partial season, 62 dates, 327 candidate game-matchups before censoring.
4. Kalshi is not the sportsbook. A result here constrains Kalshi execution
   only; the book may absorb on a different schedule.
