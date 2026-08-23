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
`OUT_late` designation for that game appears in a report.

**AMENDMENT, recorded 2026-08-23 BEFORE estimation.** The weight definition
first written here was not reproducible and is replaced. `pbp_lineups_all.parquet`
contains NO 2025-26 data (nothing at or after 2025-09), so `MIN_SHARE`,
`BLK36` and `SALIENT` cannot be computed within-season for this window — and
the frozen `OUT_late` of `PREREG_injury.md` is SALIENT-restricted, so the
frozen state itself is not reproducible for 2025-26. I fixed the weight before
checking coverage; that was an error, and this records the correction rather
than silently substituting.

Replacement, PIT-safe (uses only pre-2025-26 information):

```
w(player) = mean MIN_SHARE over that player's last 20 games of 2024-25
            (prior season carryover; 0 if the player has no 2024-25 history)
treatment(game) = sum of w over the game's OUT_late players
treated  = treatment > 0        control = no OUT_late event at all
```

A continuous carryover weight is used rather than a carried-forward top-3
SALIENT flag because roster churn between seasons makes a hard salience cut
fragile, while a continuous weight simply downweights marginal players.

This is a DEVIATION from the frozen state and is flagged wherever the result
is reported. It affects the treatment MAGNITUDE only; the EVENT definition and
timing come entirely from the injury panel, which is complete for this window
and needs no PBP. Rookies and players without 2024-25 history carry w=0 and so
cannot make a game treated — biasing toward the null, not toward a finding.

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
- monotone in the treatment weight (heavier weighted absences move more),
  evaluated on the carryover weight defined in section 4 with its deviation
  flagged.

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

---

## 10. RESULT — estimated once, 2026-08-23. Verdict: ABSORBED ON PUBLICATION

Implied lines reconstructed on 108,663 minute-observations over 429 games.
530 games in window (327 treated, 203 control); **219 measurable** (158
treated, 61 control) after requiring a usable `L(t)` both before and after
`t0` and an event-ticker match.

### JUMP — the official report does not visibly move the Kalshi line

| | treated | control | difference |
|---|---|---|---|
| `L_0 - L_pre` | -0.045 (n=158) | -0.090 (n=61) | **+0.045 (t=+0.29)** |

Prediction 6a (`JUMP < 0`) is NOT confirmed. Publication of the official report
produces no detectable repricing relative to control.

### RESIDUAL — small, mostly insignificant, far below the economic bar

| k | treated | n_t | control | n_c | difference | t | >= 1.0 pt? |
|---|---|---|---|---|---|---|---|
| 1h | -0.286 | 134 | +0.156 | 47 | **-0.441** | **-2.38** | no |
| 2h | -0.220 | 141 | -0.169 | 52 | -0.051 | -0.28 | no |
| 4h | -0.260 | 152 | -0.126 | 52 | -0.135 | -0.65 | no |
| 8h | — | 7 | — | 3 | insufficient | | |

The 8h horizon is censored to near-nothing exactly as section 4 pre-stated
(median `t0` is 8.5h before tip), and its emptiness is not evidence of
anything.

### Monotonicity — fails, with the wrong sign

| k | slope on carryover weight | t |
|---|---|---|
| 1h | +0.126 | +0.71 |
| 2h | +0.134 | +0.68 |
| 4h | +0.045 | +0.23 |

Heavier weighted absences do not move the line more. All three slopes are
positive (the prediction is negative) and none is distinguishable from zero.

### Verdict against the section 7 rule

The rule required ALL of: negative at |t| >= 2, magnitude >= 1.0 point, and
monotone in the weight. Only the 1h cell satisfies the first. It fails the
second (0.441 points) and the third (slope +0.126, wrong sign). Every other
horizon fails the first as well.

**ABSORBED ON PUBLICATION.** The scientific result from Hypothesis B stands
unchanged; the trading interpretation is closed. Per section 8 no further
horizon, weighting or subset is searched.

Economic scale, to make the size concrete: 1 point of total is about 2.2c of
win probability at the money. The 1h difference of 0.441 points is therefore
worth roughly **1.0c against a 3.0c median round-trip spread** — under water
before fees, even taking it at face value.

### What the null actually says, and what it does not

The informative surprise is `JUMP ~ 0`. Hypothesis B established that
`OUT_late` predicts open->close movement in the sportsbook line at t=-9.95 /
-5.58. Here the official report's publication moves the Kalshi ladder by
nothing measurable, and almost nothing remains afterwards. The natural reading
is that the information reaches the market BEFORE the official report
timestamp — beat reporters, team sources, warmups — so by the time the PDF
posts, the price already reflects it. The official report is a RECORD of the
information event, not the information event itself.

This does not overturn Hypothesis B. It bounds where that movement is
capturable: not at or after the official publication instant, on Kalshi, in
this window.

Limitations that constrain the strength of this null, beyond those in
section 9: (i) 219 of 530 games measurable, so this is not the full window and
attrition is not verified to be random; (ii) control arm is only 61 games;
(iii) hourly `t0` biases toward "absorbed" by construction, as pre-recorded —
a true jump inside the hour before the stamp would be attributed to `JUMP`,
and `JUMP` is measured as zero, which weakens even that escape route;
(iv) Kalshi 2025-26 is a different market AND a different season from the
sportsbook 2020-24 panel on which the channel was established.
