# OPERATING SPEC — WNBA halftime monitor (log-only prototype)

**Status: LOG-ONLY. This component observes and records; it does not trade.**
It is the program's first component that runs live against a market with
funded credentials, so the boundary between observing and acting is governed
here, in writing, before any code runs.

Frozen 2026-08-26. Changes require a new dated section, never edits.

## 1. Purpose

Three measurements no backtest contains, gathered on live WNBA halftimes
(remaining 2026 regular season + playoffs), as the dress rehearsal for the
NBA version in October:

  M1  DEPTH     resting order-book size at mispriced rungs at halftime —
                the number every economic table so far has had to assume
  M2  LATENCY   timestamp of our score feed's halftime vs the ladder's first
                subsequent repricing — are we ahead of or behind the marginal
                trader?
  M3  LIVE CALIBRATION  do live-computed edges reproduce the backtest's
                hit-rate ladder (79-84% on the >=3c tail) on virgin games?

## 2. Scope and cadence

- Series: KXWNBATOTAL only. Discovery each day from the events endpoint.
- Active window per game: T-30min .. game end (tip from the schedule feed).
- Poll cadence: ladder + orderbook every 20s in-game, every 60s pregame.
  (~8 req/s ceiling is 40x this; rate limit is not a constraint.)
- Runs unattended on game days; absence of games -> no-op exit.

## 3. Inputs, with fallbacks

| input | primary | fallback | note |
|---|---|---|---|
| schedule + tips | cdn.wnba.com schedule JSON | manual CSV | endpoint blocked from the dev sandbox; MUST be validated from the operator's machine before first run |
| live score + period | cdn.wnba.com scoreboard/boxscore | none — log the gap | halftime = period 2 marked final |
| ladder + orderbook | Kalshi GET /markets, /markets/{t}/orderbook | — | authenticated, existing client |
| pregame `pre` | last ladder L before tip (own capture) | — | corr .992 with book close (NBA measurement) |

## 4. Frozen decision inputs

- Efficient rule: E = a + b*pre + c*H1, coefficients FIT ONCE on the full
  scraped 2026 season at deployment, written into the log header, never
  refit mid-run. Residual CDF likewise (empirical, same fit set; its
  thinness is a recorded limitation).
- L(t): the frozen median-crossing estimator, >=4 two-sided rungs, bracketed.
- Edge: edge_YES = p_true - ask - 0.07*ask*(1-ask); edge_NO symmetric on bid.
- WOULD-TRADE thresholds logged at 3c / 5c / 8c (the pre-existing grid).
  Thresholds are labels on log rows, not knobs; nothing branches on them.

## 5. The acting boundary (the point of this document)

- The codebase for this component contains NO order-placement call. Not
  disabled — ABSENT. The Kalshi client is used for GET endpoints only.
- A module-level constant `COMPONENT_ROLE = "OBSERVER"` is written into every
  log row. Any future trading variant is a NEW component under a NEW spec.
- Credentials remain the existing read-capable key. If Kalshi offers
  read-only API scopes, downgrade the key used here.

## 6. Log format (append-only JSONL, one file per date)

Every poll: {ts_utc, event_ticker, game_state{period, clock, away_pts,
home_pts, feed_ts}, ladder[{strike, bid, ask, bid_size, ask_size}], L,
E, edges[{strike, side, edge}], would_trade[{threshold, strike, side,
cost}], component_role}
Plus one settlement row per game after finalization: realized total,
would-trade outcomes graded at each threshold.
Files sync to C:\NBA2\wnba_monitor\ and are never rewritten.

## 7. Grading and reporting

Weekly (manual or scheduled): a one-page summary — games covered, feed
uptime, M1 depth distribution at qualifying rungs, M2 latency distribution,
M3 would-trade ledger vs the backtest ladder. No mid-season threshold
changes regardless of results; the season grades ONCE at its end.

## 8. Failure modes, decided now

- Score feed outage: log the gap, keep polling the ladder, mark affected
  games UNGRADEABLE for M2/M3. Never substitute a slower feed silently.
- Schedule postponement: game absent from scoreboard -> skip, log.
- Ladder unbracketed (blowout): L undefined -> log raw ladder anyway (M1
  still measured), mark L null.
- Crash: systemd/Task-Scheduler restart; JSONL append means no corruption;
  a monitor gap is a logged fact, not a failure to hide.

## 9. Flip conditions — recorded now so they cannot be invented later

A live-trading variant (separate component, separate spec, explicit user
authorization) may be PROPOSED only if the logged season shows ALL of:
  F1  depth: >= 5 contracts resting at the would-trade price in >= 50% of
      >=8c qualifying halftimes
  F2  latency: our feed's halftime timestamp precedes the ladder's first
      post-half repricing in >= 80% of games
  F3  calibration: graded would-trades at >=8c hit within the backtest
      band (no worse than 10pp below 84%)
  F4  the user says go, in writing, after seeing the season summary.
Failing any -> the prototype's verdict is "measured, not tradable", which is
a complete and successful outcome for this component.

## 10. NBA inheritance

The October NBA version changes exactly: series ticker, score-feed endpoint,
quarter length (12 min -> window arithmetic), and the frozen rule/CDF (NBA
history, already computed). Everything else — including this spec's acting
boundary and flip conditions — carries verbatim with league-appropriate
numbers.

## 11. Deployment rule — frozen 2026-08-26 (addendum per the change rule)

Fit on the ENTIRE season to date (user direction; the July split served only
the honest backtest). Two candidate fits were compared before freezing:

| fit | pre semantics | n | b(pre) | c(H1) | resid sd |
|---|---|---|---|---|---|
| rejected | deep-pregame L (first hour, ~10h pre-tip) | 151 | 0.226 | 1.275 | 14.32 |
| **FROZEN** | last pre-tip L (matches live capture) | 79 | see json | ~0.9 | ~8-9 |

The 151-game fit was rejected for TRAIN/SERVE SKEW: its noisy `pre` proxy
attenuates b and inflates the residual (errors-in-variables), while the live
monitor captures the sharp last-pre-tip L. Rule + empirical residual CDF live
in `wnba_deploy_rule.json` / `wnba_deploy_residuals.npy`; both are written
into every log header. CDF thinness (n=79) remains a recorded limitation; it
grows as the monitor itself accumulates matched games, but the rule is NOT
refit mid-run per section 4.
