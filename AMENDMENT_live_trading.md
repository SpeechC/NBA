# AMENDMENT — live capital, 2026-27 (recorded 2026-09-12, pre-first-game)

**This reverses a constraint that three documents state as structural.** It is
recorded here in full, before any game is played, so that the reversal is dated
and its costs are on the record rather than discovered in April.

## 1. What is being reversed

| document | text being amended |
|---|---|
| `PREREG_crewshock_forward.md` §1 | "NO CAPITAL. This is structural." |
| `CREWSHOCK_LIVE_OPS.md` | "This pipeline places no bets… none is to be added. That is structural, not a setting." |
| `OPERATIONS_2026_27.md` | "**No component places bets.**" |
| `PREREG_crewshock_forward.md` §6 | "No capital in 2026-27 under any outcome." |

Superseded by: **capital is deployed in 2026-27 on all three strategies**, via
`nba_live_trader.py` against Kalshi `KXNBATOTAL`.

`crewshock_live.py`, `prospective_log.py`, `move_combined_live.py` and
`frozen_models.py` are **unmodified**. No threshold, shrinkage constant,
team-state definition, historical window or trading rule has been touched. The
new code reads what those modules already write and does not compute a signal of
its own — if it did, the thing being traded would no longer be the thing that
was backtested.

## 2. The costs, stated plainly

**a. It weakens the 2026-27 prospective test.** D3 forbids interim looks at
wagering performance because a mid-season look invites threshold search. Live
trading makes an *approximately* correlated quantity visible every day. The
mechanical separation is real — `evaluate_season.py` grades
`prospective_log.csv` against `open_total` at a notional stake, refuses to run
before 2027-04-15, and is imported by nothing in the live path — but the
operator will still see correlated results and cannot un-see them. **This is a
real cost being accepted, not a technicality being routed around.** The April
reads should be reported with this amendment cited.

**b. The evidence does not support confidence.** Every one of the three has an
ROI confidence interval that includes zero:

| strategy | forward hit | ROI 95% CI | n |
|---|---|---|---|
| CrewShock | 54.21% (holdout) | [−0.36%, +9.67%] | 1,390 |
| MOVE_COMBINED | 53.44% (fully OOS) | [−2.40%, +6.45%] | 1,787 |
| PaceGap | 52.59% | t = +3.42 | prospective, untested |

CrewShock's most recent season (2025-26) **lost 3.74% on its largest-ever bet
count**, and that is the season whose mechanism weakened (`b_fouls` 0.4775 vs a
prior-seven range of 0.79–1.36). PaceGap has never been traded at all.

**c. One season cannot settle it either way.** `PREREG_winkelmann` records that
efficient markets produce season-level "significant" findings more than 75% of
the time. A profitable 2026-27 is not evidence the edge is real, and a losing
one is not evidence it is not.

## 3. What changed in the economics, and why it changed the design

The signals were measured against sportsbook lines at −110. Kalshi is a
different instrument and the translation is not neutral.

**Raw signal is not a points edge.** `E_pace ≥ 4.77` does not mean the total is
4.77 points light; the realised hit rate at that threshold inverts to 1.18
points. Each strategy's edge is therefore taken from its own published hit rate:

```
delta = (hit - 0.5) * 18.244 / phi(0)
```

`SIGMA_REF = 18.244` is not a new estimate — it is implied by the mechanism
constant used throughout this programme (1.089 points needed to beat −110) and
reproduces it to 1.0888. Nothing is fitted; sigma is read off the live ladder.

```
crewshock  1.925 pts     move  1.573 pts     pacegap  1.184 pts
```

**Taking destroys two of the three.** Measured against 14,471 archived pregame
NBA rungs (median spread 2¢, p25 1¢, p75 3¢ in the 35–65¢ band), EV per contract
in cents:

|  | edge pp | TAKE s=1 | TAKE s=2 | TAKE s=4 | MAKE s=1 | MAKE s=2 | MAKE s=4 |
|---|---|---|---|---|---|---|---|
| crewshock | 4.27 | +2.01 | +1.51 | +0.51 | +3.01 | +3.51 | +4.51 |
| move | 3.49 | +1.23 | +0.73 | −0.27 | +2.23 | +2.73 | +3.73 |
| pacegap | 2.63 | +0.37 | −0.13 | −1.13 | +1.37 | +1.87 | +2.87 |

PaceGap is negative-EV as a taker **at the median spread**. Crossing a 2¢ board
costs 2.76pp against −110's 2.381pp — Kalshi is the *worse* venue for a taker.
Resting a bid earns the half-spread instead of paying it, which turns a wider
book from a penalty into a premium.

**So the default execution is passive, and that is a design consequence of a
measurement, not a preference.** `--take` exists and is gated by the same
`MIN_EDGE`, which refuses most of what it is offered.

**The three strategies cannot share a clock.** Kalshi settles on the actual
total against a fixed strike; a sportsbook wager settles against a line. This
programme already established that a ladder's implied mu *is* the closing total.
Therefore:

- **MOVE_COMBINED** forecasts open→close movement and is graded at the opener.
  Once the market has moved, its edge is spent. It must fill **early**.
- **PaceGap** also settles at the opener. **Early.**
- **CrewShock** is graded at the close, so a **late** fill is the faithful one.

Trading all three at one convenient hour would quietly convert two of them into
different strategies with no backtest.

## 3a. Two scope restrictions found by dry-running the stack

Both were caught by an end-to-end dry run on a simulated board, and both
restrict trading to the regime the backtests actually cover. Neither is a
threshold tune: no strategy's own threshold, window or rule is altered.

**One position per game, across all three strategies.** The first dry run put
75 contracts on a single ticker — CrewShock, PaceGap and MOVE_COMBINED all
fired OVER on the same game, and the per-game cap was being applied per
*signal*. They are not independent: PaceGap and MOVE_COMBINED both key off the
opener and both carry pace/efficiency state. Sizing correlated bets as if they
were independent is how a position limit fails. **Each backtest is one wager per
game and there is no measured result for the sum of three**, so the highest
published edge claims a contested game (CrewShock 1.925 > MOVE 1.573 > PaceGap
1.184) and the others stand down. This is a deterministic ranking by the only
quantity that was actually measured.

**Stale-opener guard.** If the market has moved *against* the signal by more
than that strategy's whole edge, the trade is declined. The failure this
prevents is subtle and would have been invisible: with the opener at 231.5, a
market at 229.0 and PaceGap saying OVER, mu_hat sits 3.7 points above the market
and the computed edge **rises to +6.8¢** — the model looks best exactly when its
reference is most stale. Taking it is a bet that the market's move was wrong,
and this programme measured the opposite: the market moves +0.544 pts/sd on
injury news (t = +16.16, `INJURY_TIMING_AUDIT`) and
`MONEYLINE_IMPULSE_RESPONSE` found no residual book error at any horizon from 1
to 20 games. We have no result for that regime, so we decline it rather than
price it.

This guard is also why the fill windows in §3 matter operationally rather than
theoretically: a late PaceGap or MOVE_COMBINED run will mostly find the market
has drifted and will simply decline, which is correct but silent. The daily
count of declines belongs in the operational review.

## 4. Position limits

`MAX_CONTRACTS_GAME 25`, `MAX_CONTRACTS_DAY 300`, `MAX_NOTIONAL_DAY $200`,
`MIN_PRICE/MAX_PRICE 0.12/0.88`, `MAX_SIGMA_DIST 1.1σ`, one rung per game per
strategy. `DRY_RUN` is the default and `--arm` is the only way past it. A kill
switch at `~/data/NBA_TRADING_HALT` stops everything.

At ~800 signals a season and these caps the maximum annual turnover is roughly
$36k of premium. **The calibration predicts +1.4¢ to +4.5¢ per contract; on
~20,000 contracts that is $280–900 for the season, against a confidence
interval that spans zero.** The correct expectation is a small number of either
sign.

`MIN_EDGE` is 1¢, deliberately **below** the uncertainty in `delta` itself. It
is there to reject rungs with no edge, not to certify the ones that pass. A
larger value would not be a risk control — it would be a filter tuned until
something traded.

## 5. Two things that must be true before UNDER trades

1. **The NO-side order schema is unverified.** `buy_yes` has placed real orders;
   `buy_no` has not. `side="ask"` is inferred from the `"bid"`=BUY-YES
   convention, not observed. Until `nba_live_trader.py --verify-no-side` prints
   PASS against a demo fill and `NBA_NO_SIDE_VERIFIED=1` is set, every UNDER is
   refused. **CrewShock is OVER-only and is unaffected** — it can arm first.
2. **Resting orders must be cancelled before tip.** NBA totals trade *in-play*.
   A pregame bid left open is a free option sold to whoever is watching the
   game: it fills precisely when the score has moved against it. `--cancel` runs
   as its own cron entry, not as a tail of the placement run, so that a failed
   placement still gets its cancels.

## 6. What is NOT amended

- D3 still binds the **research** evaluation. No hit rate by threshold, no
  alternative thresholds, no Over/Under splits, no team or month breakdowns.
  `nba_dashboard.py` shows none of these and `nba_daily.py status` still
  computes none.
- `evaluate_season.py` still refuses to run before 2027-04-15.
- The settlement rule for the prospective test is still `open_total`
  (Amendment 6). Kalshi P&L settles on the actual total against a strike and is
  a **different number**; it does not substitute for the April read.
- Amendment 7's standing constraint holds: `open_ml_h`/`open_ml_r` may be
  reported and reconciled but may not enter any 2026-27 decision rule.
- Every season-end endpoint in `OPERATIONS_2026_27.md` still comes due.
