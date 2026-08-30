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

## 12. Phase split — feed walled everywhere (addendum 2026-08-26)

`wnba_feed_check.py` from the OPERATOR'S machine: all WNBA CDN endpoints
return the same 3,817-byte WAF page seen from the sandbox; stats.wnba.com
times out. The score feed is walled on both networks. The Kalshi API works on
both. Therefore the component splits:

**PHASE A — Kalshi-only continuous logger (buildable now, no score feed).**
Polls ladder + orderbook every 30s across each game window and writes the
append-only JSONL. Halftime is located POST-HOC by the convergence anchor
(validated on 79 games) and scores join next day from basketball-reference
(proven scrape). This delivers M1 (depth) at full fidelity and M3
retrospectively. M2 (feed latency) is out of scope for Phase A by
construction.

**PHASE B — score feed for the live trigger.** Required only for M2 and any
future trading variant. Candidate: ESPN's public scoreboard API (untested
from the operator's machine; blocked from the sandbox). NOTE: the NBA October
version may not share this problem at all — cdn.nba.com responded normally
from the sandbox while cdn.wnba.com did not.

Flip conditions F1-F4 unchanged; F2 simply cannot be evaluated until Phase B
exists, which is itself a gate.

## 13. Relocation to D:\Kalshi — addendum 2026-08-25 (per the change rule)

The prototype moved to its own home on the operator's machine, mid-capture on
2026-08-25. Sections 1-10 are unchanged; this records the operational facts:

- Runner: `D:\Kalshi\code\WNBA_Observer.py` (a path-edited copy of this
  repo's `wnba_monitor.py`), executed by the Windows Anaconda `Core` python.
  curl_cffi 0.16.2 was installed into the Anaconda base and `Core`
  environments on 2026-08-25; no other dependency changed.
- Support files copied beside it into `D:\Kalshi\`: `kalshi_client.py`,
  `kalshi_credentials.json` + `credentials\kalshi_private_key.pem`,
  `wnba_deploy_rule.json`, `wnba_deploy_residuals.npy`. The frozen rule and
  residual CDF are byte-identical to the repo copies (s11).
- **`D:\Kalshi\wnba_monitor\` replaces `C:\NBA2\wnba_monitor\` as the
  canonical log location (amends s6).** Append-only discipline unchanged.
- The 2026-08-25 capture spans the migration in three segments, all now in
  the canonical directory, none ever rewritten:
  `monitor_20260825.jsonl` (Phase-A logger, WSL, 12:18-12:26Z),
  `monitor2_20260825_wsl.jsonl` (v2 on WSL, 12:28-12:48Z, stopped at
  hand-over), `monitor2_20260825.jsonl` (v2 on Windows, 12:47Z onward).
  The ~1-minute overlap is benign duplication; graders read all segments.
- Date correction: the "2026-08-26" datestamps in s11-s12 and in
  PREREG_wnba_halftime.md were in fact written 2026-08-25 (git commit
  timestamps are authoritative). Recorded here rather than edited.

## 14. Outcome capture — addendum 2026-08-25 (per the change rule)

**Disclosure: s6's settlement row was never implemented.** From first run
until this addendum the monitor wrote only `header`, `feed_err` and `ladder`
rows, and queried markets with `status=open` — so a settled market left the
query the moment its game ended and no outcome was recorded for any game. M3
and F1-F3 were therefore ungradeable, silently. Fixed now; no logged data is
lost, because every ladder row and would-trade row was retained and outcomes
attach retrospectively.

Two layers, deliberately separated:

- **In-session (`wnba_monitor.py`).** A settlement pass runs each loop BEFORE
  the open-markets check — the only point that can still see a game whose
  market has already closed. On a joined game reaching `Final` it writes one
  `settlement` row: realized total, finals, H1, OT count, pre_L, and every
  would-trade row recorded that session graded win/loss and P&L. The idle
  stop is held open while any joined game is unsettled, so the last game of
  a night cannot be lost to an early exit. Would-trade rows now also carry
  resting depth at the quoted rung (M1 at exactly the qualifying price).
- **Next-day (`wnba_reconcile.py`, new).** Read-only over the JSONL; never
  writes into the logs. Prefers the monitor's settlement row, falls back to
  basketball-reference finals, and reports anything with neither as
  UNRESOLVED rather than dropping it. This is what survives a restart,
  crash, or a monitor that exits before the final.

**Canonical grading rule, fixed here and implemented in exactly one place**
(`wnba_reconcile.canonical_trade`): per threshold, the FIRST poll at or after
halftime that produced would-trade rows, and within that poll the single
best-edge rung — "best rung per game", matching the prereg's economic tail.
No lookahead: a fatter edge later in the game is not reachable. Verified by
test: a later 20c row is correctly ignored in favour of the 9c row available
at the halftime poll.

**Settlement direction is empirical, not assumed.** YES pays iff
`realized_total > floor_strike` — checked against 1,345 settled 2026 markets
at 100% agreement. Every strike is a .5, so ties cannot occur.

**The bref fallback is validated end to end**: it resolves 283/296 season
events (96%), and on those the finals reproduce Kalshi's own settlements on
**2,543 of 2,543** settled strikes. The 13 misses are season-edge dates
(pre-2026-05-08, plus 06-30 / 07-16 / 07-25) absent from the scraped file,
not a systemic join failure. `wnba_bref_scrape.py` must be re-run to extend
coverage past 2026-08-24.

**Depth units are left open, deliberately.** The API serves only
`orderbook_fp` with `*_dollars`, and the sizes are not integers, so they are
dollar amounts rather than contract counts. Both the raw figure and a
contracts estimate are logged. F1's bar is 5 contracts and observed depth is
three orders of magnitude above it under either reading, so the ambiguity
does not gate grading; it is recorded rather than resolved by guess.

**Nothing here changes the deployed rule.** s4's freeze stands: coefficients
and residual CDF are untouched, no refit occurs mid-run, and this component
remains OBSERVER with no order-placement code. The panel this produces
(pre_L, H1, realized_total per game) is also the training triple an adaptive
rule would consume. That comparison is a SEASON-END exercise on the frozen
season's data, or a design decision for the NBA spec (s10) — not a live
refit, which would make M3 unanswerable by grading each game against a
different model.

## 15. Dashboard publication + post-game results — addendum 2026-08-25

**The dashboard is now published to S3, and the target bucket is PUBLIC.**
`s3://kalshi-strat/dashboard.html` (us-east-1) carries a `PublicReadWebsite`
policy granting `s3:GetObject` to `Principal: "*"`, has every public-access
block disabled, and serves static website hosting with `dashboard.html` as
the index document — i.e. the page is world-readable at
`http://kalshi-strat.s3-website-us-east-1.amazonaws.com/` to anyone who has
the URL. That configuration predates this change and is the operator's
standing choice; it is recorded here because of WHAT the page now contains:
live per-rung edges, the would-trade recommendations, the realized results,
and the frozen rule's coefficients in the header line. Publishing is a
display convenience, so anyone wanting the signal without the exposure
should either drop the rule line from the published copy or replace the
public policy with presigned URLs. No credentials or log data are uploaded —
only the rendered HTML.

- Push happens each poll after render, keyed `dashboard.html`, written
  `text/html; charset=utf-8` with `no-cache, no-store, must-revalidate` so
  the hosted copy is never served stale against the page's 30s refresh.
- Identical content is skipped by md5, so a quiet ladder costs no requests.
- `publish()` NEVER raises. boto3 missing, credentials absent, bucket gone,
  network down — each degrades to a logged line and the loop keeps polling.
  Logging is the component's job; publication is not allowed to interrupt it.
  Verified against a nonexistent bucket: returns "error", does not crash.
- Toggle with `PUBLISH_S3 = False`; bucket and key are module constants.
- Credentials come from the machine's ambient AWS config
  (`C:\Users\rando\.aws`), never from this repo. boto3 was installed into the
  Anaconda `Core` environment for this.

**Post-game WIN/LOSS cards.** Once a game finalizes its markets leave the
`status=open` query and the game used to vanish from the dashboard entirely.
Settled games now persist as result cards showing the matchup, final score,
realized total, and — where a wager was recommended — a per-threshold table
with a result column and P&L, a per-game WIN/LOSS badge, and a session
tally. Games that concluded with no recommendation say so explicitly rather
than being omitted, so an empty night is distinguishable from a broken one.
The dashboard also keeps rendering and publishing after every market closes,
which is exactly when those cards are worth reading.

The cards use the SAME canonical selection as the grader of record —
`wnba_reconcile.canonical_trade`, imported rather than reimplemented — so
the live display and the season panel cannot tell different stories. If that
import fails the monitor degrades to listing every graded row and says so;
grading of record is unaffected either way. Cards are in-memory and do not
survive a restart; `wnba_reconcile.py` remains the durable record.

**The acting boundary (s5) is unchanged.** Publishing a view of observations
is not acting on them: there is still no order-placement code, the Kalshi
client is still GET-only, and `COMPONENT_ROLE = "OBSERVER"` is still written
into every log row and shown on the page.

## 16. Arming window + late-start guard — addendum 2026-08-26

Two defects found on night 1 (2026-08-25, see `NIGHT_2026-08-25.md`), both
fixed before the second slate. Neither changes the frozen rule, the residual
CDF, the thresholds or the canonical grading; both narrow WHEN the rule is
allowed to speak.

**1. Arm only inside the halftime break.** The rule armed on
`(halftime or period >= 3)` while `E = a + b*pre + c*H1` uses the FIRST-half
total and never updates. It therefore stayed armed for the rest of the game
comparing a halftime snapshot against a market that had absorbed live
scoring. On CHI@CONN it showed a 22c "edge" in Q3 while a time-updated
version of this same model sat 0.6 pts from the market — the market had
correctly priced 10 points scored in 72 seconds. Replayed over night 1, the
old predicate armed on 408 polls and the new one on 81: **80% of armed polls
were post-halftime drift.** All 81 retained polls are inside the break
(26-28 per game, consistent with a 15-minute break at 30s polling).

The grader of record was never affected — `wnba_reconcile.canonical_trade`
takes the EARLIEST armed poll — so this changes no historical result. It
removes noise from the log and stops the dashboard asserting edges that are
an artefact of a stale E.

**2. Late-start guard on `pre_L`.** `pre_L` freezes at the first poll where a
game reads live and is never recomputed, so starting the monitor after tip
would capture a MID-GAME ladder and label it "pregame", silently poisoning E
for that game all night. The monitor now freezes `pre_L` only when the game
is still in period 1 with no points on the board; otherwise it writes one
`pre_L_missed` row and leaves the game unarmed for the session.

Replayed over night 1: all three games had a qualifying fresh poll, so every
`pre_L` would still have been captured, and nothing would have been flagged
missed. The guard is protective without being restrictive when the monitor is
started before tip — which remains the operating instruction.

**New row type:** `pre_L_missed` {event, period, away_pts, home_pts, note}.
An unarmed game is a recorded fact, not a silent gap.

## 17. Rolling pregame line — addendum 2026-08-29 (per the change rule)

s16's late-start guard froze `pre_L` only when a game read live in period 1
with no points on the board. That predicate was validated on night 1, where
all three games happened to produce a qualifying poll. Four nights of data
show it does not hold: at a 35s poll and with WNBA teams typically scoring
inside 20 seconds, **the 0-0 window is a coin flip.**

| game | polls in period 1 | polls at 0-0 |
|---|---|---|
| 26AUG27WSHPHX | 47 | 3 |
| 26AUG28PDXATL | 42 | 3 |
| 26AUG27GSNY | 42 | **0** |
| 26AUG28CONNIND | 46 | **0** |
| 26AUG28WSHLA | 42 | **0** |
| 26AUG28TORLV | 39 | **0** |

Four of six games were disqualified on poll cadence alone. This was never a
data problem: CONN@IND sat on the board with a quoted ladder for a full day
before tip and still never received a line. The monitor was healthy
throughout — 8h continuous on the night of 28 Aug, zero polling gaps over
90s, dashboard rewritten every poll. What was frozen was the *content*: three
of four games showed "model arms at halftime" all night, including through
their own halftimes, because `pre_L` was never captured.

**The change.** `pre_L` is a PREGAME quantity, so it is now taken from the
pregame board rather than from a moment defined relative to tip. Every
pre-tip poll overwrites a provisional line (`pre_prov`, median crossing on
the current ladder); the last one standing is frozen the instant the game
reads live and is never recomputed thereafter. The old tip-time capture is
retained as a fallback for a monitor started between tip and the first
basket (`source: "tip_0_0"`).

**The s16 guard is retained unchanged in effect.** With no pregame
provisional AND the game already under way, the monitor writes one
`pre_L_missed` row and leaves the game unarmed for the session. A monitor
started mid-game still cannot mislabel a live ladder as pregame — which was
the whole point of s16.

**Replay over all four logged nights (9 games):**

| | old rule | s17 |
|---|---|---|
| `pre_L` captured | 2 / 9 | **9 / 9** |
| unarmed for want of a line | 7 | 0 |

Critically, on the two games where both rules fire the value barely moves —
WSH@PHX 165.30 → 165.68, PDX@ATL 178.64 → 178.86. **The fix changes the
availability of the measurement, not the measurement.** That is the
condition under which widening a capture window is legitimate rather than a
silent redefinition, and it is stated here so it can be checked.

Sample rate for the remaining ~6 weeks goes up roughly 4.5x. No historical
result changes: `wnba_reconcile.canonical_trade` remains the grader of
record, and no already-graded trade had its `pre_L` altered.

**New row type:** `pre_L_frozen` {event, pre_L, source, period, away_pts,
home_pts}, where `source` is `pregame_last` or `tip_0_0`. A captured line is
now a recorded fact with a stated provenance, symmetric with `pre_L_missed`.
`pre_L_missed`'s note text changes to reflect the new predicate.

**Standing caveat, unchanged by this addendum.** Raising the sample rate
raises the rate of *observations*, not of edge. Through four nights the
ledger is 5 graded entries, and the only game in which the model materially
disagreed with the market and was right is PDX@ATL (E 181.03, market L
177.67, realized 184). s17 buys statistical power to settle the question
sooner; it is not evidence for either answer.

### s17 AMENDMENT — same day, before the rule ran live

s17 above claims: "The fix changes the AVAILABILITY of the measurement, not
the measurement." **That claim is too strong and is corrected here.** It holds
for the VALUE of `pre_L` (the two overlapping games move 0.38 and 0.22 pts).
It does NOT hold for the trade that value selects.

Replaying WSH@PHX 27 Aug through both capture rules:

| `pre_L` | E | canonical trade @3% | result |
|---|---|---|---|
| 165.30 (`tip_0_0`, as graded live) | 161.37 | NO @171.5, cost 0.8494 | WIN +0.151 |
| 165.68 (`pregame_last`, s17) | 161.58 | YES @153.5, cost 0.7824 | **LOSS −0.782** |

A **0.38-point** change in an input flips the canonical trade and swings P&L
by **0.93 per contract**. The cause is not s17: `p_over` interpolates a step
function over the 79 stored residuals, so probability moves in jumps of
1/79 = 1.27pp. At halftime the top four rung-edges routinely sit inside one
such step of each other and of the 3% threshold, so "best edge" is decided by
rounding noise, not by conviction. s17 merely exposed it.

**Consequence for the record.** Already-graded trades are unaffected in fact —
`canonical_trade` reads logged `would_trade` rows and no log was rewritten —
but they are now known to be less determinate than they looked. The two live
wins are one input-perturbation away from being one win and one loss.

**No change is made to the rule on this basis.** The rule is frozen (s4) and
was fit on those 79 residuals; re-specifying `p_over` after seeing outcomes is
exactly the move the freeze exists to prevent. This is recorded as a measured
property of the frozen rule, to be carried into any successor: **a
best-edge-across-rungs selector needs a probability model with resolution
finer than the spacing between competing edges, and this one does not have
it.** A successor should either smooth `p_over`, or select on a criterion
robust to 1.27pp jitter (e.g. require a margin over the runner-up rung), or
size across qualifying rungs rather than picking one.

## 18. Shadow variant `market_sigma` — addendum 2026-08-29 (log-only)

**Status: LOG ONLY. The frozen rule (s4) is unchanged and remains the graded
rule of record.** This adds a parallel book written to its own row type. It
does not touch arming, `would_trade`, `canonical_trade`, the dashboard, or
any flip condition. Nothing about the forward test is altered.

### Why — the diagnosis, which uses no outcomes

The frozen `p_over` interpolates the 79 stored fit residuals, whose sd is
**8.4 pts**. The halftime ladders the monitor is already logging imply
**12.0**. Realised out-of-sample error over the first 9 games is **10.0**.

| sigma | source | P(total > E + 15) |
|---|---|---|
| 8.4 | model, in-sample fit | 0.037 |
| 10.0 | realised, n=9 | 0.067 |
| 12.0 | market-implied | 0.107 |

A too-narrow CDF makes every wing look cheap *mechanically*. The consequence
is visible in where the rule bets: over the 9 games, **24 of 53 qualifying
rungs sat on games where model and market agreed on the LINE to within 1.5
pts.** On CHI@CONN the two were 0.2 pts apart and the rule still fired six
rungs. Those are not line bets — they are bets that the model's distribution
is narrower than the market's, which is the one thing now known to be wrong.

This diagnosis is derived **entirely from quotes**. The model's sigma and the
market's sigma are both observable before any game finishes. That is what
makes it legitimate to act on at n=9, and it is the standard this programme
should hold future changes to: *if a proposed change needs the P&L to justify
it, at this sample size it is fitting noise.*

### The variant

Location from the model, scale from the market:

    mu    = E = a + b*pre_L + c*H1        (frozen rule, unchanged)
    sigma = the ladder's own implied width
    P(over K) = 1 - Phi((K - mu) / sigma)

`sigma` comes from `market_scale()`: a totals ladder is a sampled survival
function, so `K = mu + sigma * Phi^-1(1-p)` and a weighted regression of
strike on probit recovers both, with no bracketing requirement. This is
`implied_line.probit_line` inlined, with `_ndtri` written out, so the monitor
acquires no scipy dependency on the Windows host. **Zero free parameters and
nothing fitted to any outcome.**

### Replay over the 9 logged games (structure, not P&L)

| | frozen | shadow |
|---|---|---|
| qualifying rungs @3% | 53 | 33 (−38%) |
| games with no trade | 0 | **4** |

The four silent games are exactly the four with `|E − mkt_mu| < 1.5`. The
variant declines to bet when it has no view the market does not already hold,
which is the intended behaviour and the reason for building it.

**The P&L of this variant is deliberately NOT offered as justification.** At
n=9 the frozen rule's own ROI is −9.8% with a bootstrap CI of [−54%, +29%],
its sign flips with the threshold examined (−9.8% at 3c, −12.7% at 5c, +1.2%
at the 8c decision cohort), and a model-free control that buys every rung on
both sides loses 4.4% — so most of the headline loss is venue cost, not the
model. Nothing about profitability is yet measurable in either direction.

### Decision rule for the shadow, recorded now

The shadow may be PROPOSED as a successor rule only after the logged season,
and only on: (i) the same F1-F4 conditions in s9, evaluated on its own book;
and (ii) a head-to-head on games where BOTH fire, so the comparison is not
an artefact of the shadow's smaller, differently-selected sample. Absent
both, the shadow's role is diagnostic and it is discarded with the prototype.

**New row type:** `shadow` {variant, event, E, mkt_mu, mkt_sigma,
model_sigma, n_rungs_fit, n_frozen_rungs, would_trade[]}, one per armed poll.

## 19. Poll cadence restored to spec, M2 remeasured — addendum 2026-08-29

### The cadence was out of spec

§2 specifies 20s in-game polling. The deployed monitor was running
`POLL_S = 30`, drifted in during the dashboard work and never reconciled.
Observed cadence was ~35s (30s sleep + ~5s of work), because the sleep ran
after the work rather than being measured from the top of the loop.

Two changes: `POLL_S = 20`, and the sleep is now
`max(0, POLL_S - (time.time() - loop_t0))` at all three sleep sites, so
POLL_S is the actual period rather than period-plus-work. Measured against
860 logged loops: median work 2.0s, p95 4.4s, max 4.9s, so 20s leaves 15.1s
of headroom; request rate at the observed worst case is 2.6 req/s against
§2's 8 req/s ceiling.

### The old M2 result was an artefact and is withdrawn

Comparing our halftime stamp to the next repricing WE observe measures our
own poll grid. Over 9 games it returned 9/9 "ahead" with leads of 34, 36, 34,
36, 35, 35, 35, 34, 34 seconds — one poll interval, every time. **A censored
measurement that always passes is not a measurement**, and the apparent F2
pass it produced is withdrawn.

### M2 remeasured against ground truth (`m2_latency.py`)

`espn_clocks_wnba.csv` gives the real halftime buzzer per game and
`kalshi_wnba_candles.sqlite` gives 1-minute bars per rung, so the MARKET's
reaction time can be measured with no reference to the monitor at all — over
**250 games** rather than 9.

Time from halftime buzzer to the ladder's first movement:
**median 32s, p10 9s, p90 57s.** The market has effectively finished
reacting inside a minute (98% of games).

| our detection latency | ahead in | F2 (>=80%) |
|---|---|---|
| 10s (POLL_S=20, mean) | 87% | PASS |
| 20s (POLL_S=20, worst) | 71% | FAIL |
| 15s (POLL_S=30, mean) | 80% | PASS |
| 30s (POLL_S=30, worst) | **53%** | **FAIL** |
| 60s | 2% | FAIL |

**At the cadence actually deployed for the first four nights we were ahead of
the market in barely half of games** — the opposite of what the self-referential
measurement reported. At 20s we pass on the mean case and fail on the worst.
Clearing F2 on worst-case detection requires `POLL_S <= 15s`.

**Two limitations, both cutting against us.** Candles are 1-minute bars, so a
movement is located to its containing bar, biasing measured market latency
upward. And the score feed's own lag is unmeasured and adds to our detection
latency. Every figure above is an **upper bound on how far ahead we are.**

This is the M2 the spec asked for: not "did we see it first in our own log"
but "are we ahead of the marginal trader". The answer is: at 30s, no; at 20s,
marginally; and the honest number needs the feed lag measured before F2 can
be called either way.

## 20. TERMINAL VERDICT — measured, not tradable (2026-08-30)

Invoking §9: *"Failing any -> the prototype's verdict is 'measured, not
tradable', which is a complete and successful outcome for this component."*
That is the verdict. It is recorded here with the numbers that produce it.

### Flip conditions

| | condition | result | |
|---|---|---|---|
| F1 | depth >=5 contracts at the would-trade price in >=50% of >=8c halftimes | 8/8 games, median 92-10,289 contracts | **PASS** |
| F2 | our halftime stamp precedes the ladder's first reprice in >=80% of games | 58% at POLL_S=20; **74% even at POLL_S=0** | **FAIL** |
| F3 | >=8c would-trades hit within 10pp of 84% (i.e. >=74%) | 22/33 = **66.7%** | **FAIL** |
| F4 | user says go after seeing the season summary | not reached | — |

Two of three fail. No live-trading variant may be proposed. Per §5 this
component ends its life as it began: `COMPONENT_ROLE = "OBSERVER"`, with no
order-placement code ever written.

### F2 fails structurally, not for want of engineering

`m2_latency.py` (288 games): the ladder's first post-buzzer movement comes at
a **median of 32s**, p10 8s. `feed_lag.py` (10 monitored games against ESPN
play-by-play): the WNBA scoreboard endpoint reports halftime **17.6s** after
the real buzzer.

    detection latency = feed lag (17.6s) + U(0, POLL_S)

| POLL_S | detection (mean) | ahead in | F2 |
|---|---|---|---|
| 30 (as first deployed) | 33s | 49% | FAIL |
| 20 (s19) | 28s | 58% | FAIL |
| 10 | 23s | 67% | FAIL |
| **0 (instantaneous)** | **18s** | **74%** | **FAIL** |

F2 needs detection within 14s. **The feed lag alone is 17.6s, so no poll
cadence whatsoever clears the bar.** This is not a tuning problem; it is a
property of the score feed. Beating it would require a faster source of
halftime truth than cdn.wnba.com, which is a different component with
different economics, not a parameter change here.

### The three measurements

**M1 DEPTH — delivered, and the most valuable output of the component.**
40,701 rung-polls. Depth at the touch is ample (F1 passes 8/8). Adverse
selection is ~0 (+0.09c at 1min, the only significant horizon). **The FEE is
the binding constraint on making**, not adverse selection: 1.74c fee against
1.81c half-spread earned, net +0.06c/contract. This needed live order books
and no statistical power, and it transfers to any Kalshi venue work.

**M2 LATENCY — delivered, and it disqualifies taker strategies here.** See
above. Note the method: the monitor's own logs could not answer this
(comparing our stamp to the next reprice WE see returned 9/9 "ahead" with
leads of exactly one poll interval, s19). The answer came from ESPN buzzers
plus historical candles — data already on disk.

**M3 CALIBRATION — answered in the negative, and unreachable in the
affirmative.** The >=8c cohort hits 66.7% against a 74% bar. The cause was
identified from quotes alone (s18): the frozen CDF's sd is 8.4 pts where the
ladders imply 12.0 and realised error is 10.0, so the model prices its wings
as if it were 30% more certain than it is. Ten games of P&L: canonical @3%
-1.28 on 7.28 staked = **-17.5%, CI [-59%, +22%]**. Every threshold/mode cell
is negative, which is a mild hardening; the CIs remain useless and always
would have been. Resolving a realistic effect needs ~1,180 games. **M3 could
never have passed within one WNBA season, and that should have been computed
at freeze time.**

### What is inherited by the NBA version, and what is not

§10 says the October NBA version changes only ticker, endpoint, quarter
arithmetic and rule. That inheritance is **withdrawn for the signal and
retained for the instrument.**

- **Not inherited: the premise.** The NBA halftime under-reaction was closed
  on the full 2025-26 season (1,114 games, probit estimator): r2>=0.95 gap
  -0.022, economically absent against a 1.06-1.25pt round trip. An NBA
  halftime monitor would be instrumentation for a signal already disproven.
- **Not inherited: the pipeline's relevance to the one live signal.**
  CrewShock is pregame and referee-based; it needs assignment scraping at
  publication and a single market snapshot, not 20s in-game ladder polling.
- **Inherited: the venue facts** (M1), **the estimator** (`implied_line`),
  **the measurement method** (ground truth beats self-reference), and the
  operating discipline of §5.
- **Carried forward as an open question:** F2's structure. If NBA halftime
  repricing is faster than WNBA's 32s -- likely, given attention and money --
  then any in-game NBA taker strategy inherits a *worse* latency problem, and
  should be checked with `m2_latency.py` against NBA data before anything is
  built.

### What the component is still worth running for

Nothing that requires checking nightly. The frozen line-momentum shadow
ledger and the s18 shadow book close on their own at season end. The monitor
may keep running as a background tape; its P&L is not evidence and should not
be read as such.

### Honest accounting of process errors

Recorded because the method is the deliverable: (1) the original s=0.276
staleness finding was an anchor artefact, self-caught; (2) "NBA data cannot
be backfilled" was wrong -- `/historical/markets` serves it; (3) the WNBA
over-bias was attributed to attrition and survived the fix, so that
attribution was wrong; (4) s17's "availability not the measurement" claim was
too strong and was amended same-day; (5) the first M2 was a censored
self-comparison that could only ever pass; (6) a missing POR->PDX team-code
mapping silently dropped 38 games from the M2 sample until caught. Five of
six were found by adversarial re-testing rather than by the result looking
wrong, which is the argument for doing it.

## 21. M2 run on NBA — the open question from s20, closed (2026-08-30)

s20 carried one question forward: *"NBA halftime repricing is likely faster
than WNBA's 32s, so any in-game NBA taker strategy inherits a WORSE latency
problem -- check with `m2_latency.py` before building."* Done.
`m2_latency.py` now takes a league argument; WNBA output is byte-identical to
s19's, so the refactor is inert.

**1,210 NBA games** (2025-26, KXNBATOTAL vs ESPN play-by-play buzzers) against
288 WNBA:

| | WNBA | NBA |
|---|---|---|
| games | 288 | 1,210 |
| median first move after buzzer | 32s | **30s** |
| p25 | 17s | 15s |
| p10 | 8s | 6s |

The prediction was right in direction and small in size: NBA reprices ~2s
faster at the median, ~2s at every quantile. **Attention and money buy
surprisingly little speed** -- an order of magnitude more volume moves the
halftime reprice by under 7%.

**It does not matter, because the feed lag dominates in both leagues.**
Applying the WNBA-measured 17.6s (see caveat below):

| POLL_S | detection | WNBA ahead | NBA ahead | F2 |
|---|---|---|---|---|
| 20 | 28s | 58% | 55% | FAIL |
| 10 | 23s | 67% | 62% | FAIL |
| **0** | **18s** | **74%** | **70%** | **FAIL** |

F2 needs detection within 14s (WNBA) or **12s (NBA)**. A 17.6s feed lag
exceeds both. **No poll cadence clears F2 in either league**, and NBA is the
harder of the two.

**CAVEAT, stated plainly: the NBA feed lag is NOT measured.** 17.6s is the
cdn.wnba.com figure and is carried across as a planning assumption on the
grounds that the two feeds share a vendor and architecture. It has never been
checked. Measuring it requires an NBA score feed running against live games
with ESPN buzzers for the same nights -- roughly a night's work in October,
and `feed_lag.py` already does the arithmetic. **That measurement is the
gate: if cdn.nba.com turns out to deliver halftime inside ~12s, the
conclusion here reverses.** Until it is taken, the NBA in-game taker case is
assumed dead by inheritance, not proven dead.

**Consequence for October.** No in-game NBA halftime component should be
built. This costs nothing that was planned: the NBA halftime under-reaction
is already closed (1,114 games, r2>=0.95 gap -0.022), and CrewShock -- the
one validated signal -- is pregame, where a 17.6s feed lag is irrelevant
because the assignment publication, not a buzzer, starts the clock.

## 22. What passing F2 would have been worth — addendum 2026-08-30

s20 failed the prototype on F2, a statement about SPEED. It left the prior
question unasked: **if we had been fast enough, was there anything to take?**
`halftime_reprice.py` answers it. The finding is stronger than s20's and
should be read as superseding its framing: **F2 was not the binding
constraint.**

### The feed is ahead of the market; our polling is not

Restating s20/s21 in the right order. The feed reports halftime at buzzer
+17.6s; the market first moves at +30s (NBA) / +32s (WNBA). **The feed leads
the market by ~13s and beats it in 74% of games unaided.** F2 failed because
a 20-30s poll interval was stacked on top. The cheap fix was never a faster
feed but adaptive polling -- 1s cadence inside the last two minutes of Q2 --
which recovers essentially the whole POLL_S=0 bound. That fix was never made,
and s22 is the reason it should not be.

### The prize is real, and it is not the usual artefact

Ladder movement across halftime, rungs quoted 25-75c pre-buzzer:

| pre-buzzer spread | n (NBA) | \|move\| | cost | net | zero-vol |
|---|---|---|---|---|---|
| **<=2c (tight)** | 941 | **3.97c** | 2.40c | **+1.57c** | 4% |
| 2-5c | 1,731 | 3.91c | 3.55c | +0.36c | 8% |
| 5-10c | 1,257 | 4.65c | 5.30c | -0.65c | 22% |
| >10c (wide) | 2,489 | 8.12c | 21.01c | -12.89c | 55% |

WNBA matches (+1.70c tight, n=565). **This is NOT the wide-spread artefact**
that killed the ladder-residual work: the tight, liquid rungs (1-4% zero
volume) move as much as the wide ones. Something real happens at halftime.

### The bar, which is the finding

The net above assumes the DIRECTION is known. Solving
`(2q-1)*|move| = cost`:

> **A halftime latency strategy must call the direction of the reprice
> correctly 78.9% of the time (WNBA) / 80.2% (NBA) merely to break even.**

Four times in five, on a 4c move, against a 1.6c fee and a 1c half-spread.

The obvious signal fails outright. Fading the pre-buzzer 5-minute drift --
the stale-mid-reverts theory -- gives beta +0.008 (WNBA) / -0.005 (NBA),
correlation +-0.02, and trading it returns **-2.38c / -2.33c per contract,
which is exactly the transaction cost**. Gross edge of precisely zero.

**Why this should have been expected.** At the buzzer the market's quote
already contains essentially all of H1 -- the book watched the half happen.
The reprice is not the market learning the score; it is a book re-opening
after a lull. There is no stale FACT to pick off, which is what a latency
strategy requires.

### Consequence, and it generalises

Speed on this venue buys the right to pay the fee sooner. Combined with the
M1 result (adverse selection ~0), the picture is coherent: **nobody is
picking off Kalshi halftime with speed, because speed alone is not worth
anything here.** There is no latency war to lose and no free money to win.

This strengthens s20 rather than softening it. The prototype did not fail
because it was 15 seconds too slow; it would have failed at zero latency,
because it never had the 80% directional signal that alone converts speed
into money. **Any future in-game taker proposal, in any league, must clear
the directional bar BEFORE any engineering is spent on latency.**

### Open question, recorded not closed

The mean SIGNED move on mid-range tight rungs is **-2.14c (WNBA) / -1.47c
(NBA)**, not zero -- a genuine martingale violation on ~1,500 observations.
Untested hypothesis: microstructure, with bids pulled harder than asks across
the break dragging the MID without either tradeable price moving (which is
also why every |move| figure here is an upper bound on taker capture). It is
recorded as an anomaly, not a signal; confirming it needs fill-level or
full-depth data this component does not have.
