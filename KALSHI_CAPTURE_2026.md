# KALSHI 2026-27 — capture requirements and FROZEN analysis questions

**Written 2026-08, after the post-freeze validation (`kalshi_mtm.py`,
`SECOND_LINE.md` §11). This freezes the QUESTIONS and the data specification.
It deliberately does not freeze trading rules — we do not yet know the timing
or fill mechanics, and pretending otherwise would be the execution-side
version of specification mining.**

---

## 1. Why this exists

2025-26 established the destination: the frozen MOVE_COMBINED signal forecasts
where the Kalshi tip surface sits relative to the stale sportsbook opener
(slope +0.812, t≈9), the shift is location-only, and by T−1 minute the
exchange has incorporated ~93.5% of it. What one snapshot per game cannot
establish is the PATH — when the repricing happens, and whether passive orders
fill before it does. **Timing + fill mechanics are the entire 2026-27 Kalshi
research problem.** Data collection is therefore part of the experiment, not
infrastructure around it.

## 2. Capture specification

For EVERY NBA totals rung, from first listing through tip:

| field | note |
|---|---|
| event/game identifier, Kalshi ticker, strike | |
| timestamp (UTC) and time-to-scheduled-tip | |
| best Yes bid / Yes ask | |
| best No bid / No ask | if separately represented |
| bid size / ask size | REQUIRED — fills are the question |
| last trade price / size | |
| cumulative volume, open interest | |
| deeper book levels | if the API makes them practical |
| sportsbook OPENING total | same feed as PREREG_move_combined.md |
| contemporaneous sportsbook total | the live reference |
| frozen MOVE_COMBINED value `m` | logged, never recomputed later |
| exact timestamp `t0` when `m` first became computable | the clock starts here |

**Cadence: 30–60 second snapshots**, plus raw order/trade events where the API
exposes them economically. Hourly candles are declared inadequate in advance:
they cannot support fill analysis, and **no maker fill may ever be inferred
from candle highs/lows** (false-fill bias). If only candles are obtainable,
Analyses 2 and 4 remain open — they are not to be approximated.

The per-game sequence of record: `K_t0, K_t0+5m, K_t0+15m, K_t0+30m, …, K_tip`.

## 3. Frozen analysis questions

**PRIMARY (Analysis 2 — timing):**

```
m  ->  mu_Kalshi,tip − mu_Kalshi,t0            (the real, non-counterfactual MTM)
D(h) = (mu_Kalshi,h − mu_Kalshi,t0) / (mu_Kalshi,tip − mu_Kalshi,t0)
```

D(h) reported at 5m / 15m / 30m / 1h / 3h / 6h after t0, conditioned on |m|,
pregame volume and quoted depth. The deliverable is the edge-decay curve: how
long after the signal exists is the repricing still ahead of us.

**SECONDARY (coherence, carried forward):** |m| ↑ ⇒ |Δmu_Kalshi| ↑, and the
K_early question settled directly — is the early surface at S_open, at
S_close, or between; and does Kalshi ever LEAD the book (a separate, later
experiment if observed).

**EXECUTION (Analysis 4 — the harsher standard):** for each hypothetical
passive order derived from `m`, from actual quote/trade history only:

```
P(fill)
E[P_5m − P_fill | fill]        <- adverse-selection check, not just fills
E[P_30m − P_fill | fill]
E[P_tip − P_fill | fill]
```

The outcome matrix that decides everything:

| forecast correct? | passive fill? | interpretation |
|---|---|---|
| yes | yes | potential strategy |
| yes | no | signal real, maker execution fails |
| no | yes | adverse selection — dangerous |
| no | no | economically irrelevant |

## 4. Inference discipline

All rung × horizon inference clustered at the GAME level minimum; date-level
clustering inspected. ~1,000 independent games is the sample size, not
100,000 rung-hours.

## 5. Frozen negatives

- The variance prediction stays at NULL. sd_Kalshi is expected to be unrelated
  to `m` prospectively; only unexpected prospective contradiction reopens it.
- No new Kalshi predictors; no threshold optimization of `m` against Kalshi;
  no rung selection on realized P&L (rung choice is analytic: central rungs
  ~2.2c/point, tails ~1.3c/point).
- `m` enters completely frozen per `PREREG_move_combined.md`:
  deployment `m = 0.0337 + 0.8402·ridge + 0.6869·latent`, latent mapping fit
  once through 2025-26.

## 6. Relation to the other frozen documents

`PREREG_move_combined.md` owns the sportsbook CLV endpoint; this document owns
the exchange path and fill questions; `SECOND_LINE.md` owns the maker
strategy, whose Stage-0 gate (effective κ < 0.05) is measured from exactly
this capture. One data stream feeds all three.
