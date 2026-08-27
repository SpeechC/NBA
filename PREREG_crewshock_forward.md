# PREREG — CREWSHOCK FORWARD TEST, 2026-27

Written 2026-08-26, **before the 2026-27 season exists**. The NBA opens
2026-10-20. Every criterion below is fixed now, when no forward data can be
consulted.

## 0. Why this test exists

`CLOSING_REFEREE.md` closed the research branch with the verdict *the science
is stronger than the economics*. The `2026-08-26` P&L re-check confirmed it:
pooled ROI +4.66%, 95% CI **[−0.36%, +9.67%]** — the best economics in this
program and still short of a 95% bar, needing ~3,294 bets ≈ 19 seasons.

One thing, and only one thing, changed the picture: **2025-26 weakened.**
`b_fouls` fell to +0.4775 (t = 2.21) against +0.79 to +1.36 across the seven
prior seasons, diagnosed `REFEREE_PROPENSITY_PERSISTENCE_WEAKENED`. A single
season cannot separate noise from decay. This forward test exists to get a
second observation on that question **and nothing else.**

## 1. NO CAPITAL. This is structural.

`crewshock_live.py` contains no order-placement code and none may be added.
The pipeline writes a CSV log. **Regardless of what the 2026-27 numbers show,
no capital is deployed on this signal during 2026-27.** The only decisions this
test can produce are: *mechanism intact — keep monitoring*, *mechanism broken —
close the branch*, or *ambiguous — keep monitoring*.

## 2. The estimator is frozen and was verified byte-faithful

```
k    = 78.247119   FROZEN on development. NEVER re-estimated in-season.
N    = 60          official horizon        MINN = 25
SHORT/LONG = 200/1230                      THR  = 0.8682  (development Q85)
universe = "Regular Season" only (IST excluded), closing total in [150,300]
```

`crewshock_live.py validate` reproduces `ref_features.csv` through the live
code path:

```
VALIDATION 1  full reproduction      n=9,489   max|diff| 1.78e-09   PASS
VALIDATION 2  PENDING path, fouls withheld     max|diff| 5.18e-10   PASS
```

## 3. Inputs, and the one that already bit

- **Officials**: `official.nba.com` assignments API, published mid-morning.
  The close is at tip; that gap is the entire edge.
- **Foul histories**: BigDataBall season-to-date, `pf_rate =
  100·PF_H/POSS_R + 100·PF_R/POSS_H`, verified to reproduce the advanced-stats
  sidecar at max|diff| = 0.0.

**A defect found during the build, recorded because it would have been
invisible:** the assignments API writes `JT Orr` where BigDataBall writes
`J.T. Orr`. An unmatched name silently zeroes that official's entire 60-game
history and biases CrewShock toward zero — it mis-scored a real slate by up to
6.8e-02 before it was caught. Canonical matching now resolves it, and any
official who still fails to resolve flags the game **DATA_GAP**, which is never
actioned. Two further API traps are gated: the date parameter must be
`YYYY-MM-DD` (`MM-DD-YYYY` returns zero rows and looks like "no games"), and a
zero-row response is reported, never treated as an empty slate.

## 4. PRIMARY endpoint — the MECHANISM, not the P&L

With ~175–240 firing games per season the P&L standard error is ≈3.3pp against
a claimed +2.44pp edge. **One season cannot say anything about the money.** The
mechanism regression runs on the full ~1,230-game season and can.

```
M1:   pf_rate ~ CrewShock + LeagueFoulState,  2026-27 regular season
      report b_fouls and its t
```

Reference distribution, seven pre-2025-26 seasons (fixed here):

| season | 2017-18 | 2018-19 | 2020-21 | 2021-22 | 2022-23 | 2023-24 | 2024-25 | **2025-26** |
|---|---|---|---|---|---|---|---|---|
| b_fouls | 1.0051 | 1.1572 | 0.9985 | 1.3628 | 1.3241 | 0.7871 | 0.9651 | **0.4775** |
| t | 3.19 | 5.49 | 4.01 | 7.36 | 6.60 | 3.53 | 4.29 | **2.21** |

Prior-seven mean **1.0857**, sd **0.2068**, range [0.7871, 1.3628].
2025-26 sits at **z = −2.94**.

**Decision rule, fixed now.** With `z = (b_2027 − 1.0857) / 0.2068`:

| outcome | verdict |
|---|---|
| **z ≥ −1.5** (b ≥ 0.775) | **MECHANISM INTACT.** 2025-26 was noise. Continue monitoring; still no capital. |
| **z ≤ −2.5** (b ≤ 0.568) | **BREAK CONFIRMED.** Two consecutive seasons below the historical floor. Close the branch and retire the signal. |
| between | **AMBIGUOUS.** Continue monitoring into 2027-28. No other reading permitted. |

No alternative window, threshold, or estimator may be substituted to move a
result across these lines.

## 5. SECONDARY — is anyone else finding it?

```
M2:   c_market on 2026-27 = coefficient of CLOSING TOTAL on CrewShock
      historical: statistically zero in every season
```

The 4.6% headline is the market's non-response. If `c_market` turns
significantly positive, the omission is being priced and the edge is closing
for reasons unrelated to the mechanism. Reported with its t; **a significantly
positive `c_market` is itself sufficient to close the branch**, independent of
M1.

Corroborating and non-decisive: mean `close − open` on firing games. It has
been ~0 (+0.0813, t = +0.94); a drift upward is the same signal as M2.

## 6. TERTIARY — the P&L, reported and NOT decisive

Logged and graded nightly, reported at season end as hit rate, ROI, and a 95%
interval computed with the **correct** `1.90909·hit − 1` multiplier (the
`2.1·hit − 1` slip is on record in `MOVEMENT_FULL.md`). Points-to-hit-rate
conversion uses `φ(0)/σ`, compared to break-even, never added to it.

**Stated in advance:** at ~200 bets the interval will be roughly ±6.6pp of ROI.
It will not exclude zero whatever happens, and no reading of it — good or bad —
alters §4's verdict.

## 7. What gets logged

Nightly, per game: timestamp, gid, date, teams, three resolved officials,
`CrewShock`, `min_prior`, `data_gap`, `fires`, `action`, and the total at log
time if a lines file is supplied. Graded rows append to a ledger with the
closing total and the final. Nothing is overwritten; the log is append-only so
the record cannot be quietly revised.

## 8. Known limitations, stated in advance

- One season adds ~1,230 mechanism games and ~200 bets. This test is powered
  for M1 and **not** for the P&L, by construction.
- The 2026-27 officiating roster turns over; new officials need 25 prior games
  before contributing, so early-season CrewShock is attenuated. This is frozen
  behaviour, not a defect, and is identical to every historical season.
- BigDataBall must land before the next day's run or histories go stale by a
  day. The runbook treats a stale-history run as a hard stop.
- A single vendor's closing total, as throughout.

### A GLOBALLY-TRUE / LOCALLY-FALSE risk, added 2026-08-26

**The frozen threshold is not a frozen selectivity.** `CrewShock >= 0.8682` was
fixed as the development Q85, but the statistic's own spread moves across
seasons, so what the threshold SELECTS does not stay fixed:

| season | 17-18 | 18-19 | 20-21 | 21-22 | 22-23 | 23-24 | 24-25 | 25-26 |
|---|---|---|---|---|---|---|---|---|
| fires | 92 | 220 | 142 | 210 | 195 | 139 | 167 | **238** |
| share | 7.5% | 17.9% | 13.1% | 17.1% | 15.9% | 12.0% | 14.3% | **20.5%** |

Firing share ranges **7.5% to 20.5% (2.74x)**; season CrewShock sd ranges
0.574 to 0.912 (1.59x). `CLOSING_REFEREE` rule 1 already records that a frozen
threshold against a moving spread "bit twice" — it is recorded here as a
FORWARD risk before 2026-27 rather than diagnosed afterwards.

**Consequence, fixed now:** the 2026-27 firing count and share are reported
alongside every result, and a bet count far outside the historical 92-238 band
is a **data/regime flag, not a finding**. The threshold itself is NOT adjusted
under any circumstance — doing so would unfreeze the signal. If selectivity
lands outside the band, M1 is still read on its own §4 rule, and the P&L is
reported with the caveat that its marginal games are not comparable to the
historical set.

**Related, and it makes §6 weaker than it looks:** the P&L's implied precision
assumes independent bets. It has 1,403 firing games across only 843 nights and
104 officials — about 40 firings per official, each driven by the SAME 60-game
estimate. Effective n is below nominal, so "~3,294 bets / ~19 seasons" is the
optimistic bound, not the honest one.
