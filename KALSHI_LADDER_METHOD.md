# TWO METHOD RULES FOR ANY KALSHI LADDER WORK (2026-09-13)

Extracted from `MAKER_PREFLIGHT_VERDICT.md` because both are infrastructure lessons that
outlive the strategy that produced them. Either one, ignored, manufactures false findings.

---

## RULE 1 — A NOMINAL RUNG IS NOT AN ECONOMIC STATE VARIABLE

Never index a ladder analysis by "the +15 contract", "the third rung from the edge", or any
static strike label. The correct coordinate is **moneyness**:

```
z_{i,t} = (K_i − m_t) / sigma_t
```

where `m_t` and `sigma_t` are recovered from the ladder itself at time `t` — probit-fit
`Phi^-1(1 − p_i)` on `K_i` across the rungs (median fit r2 **0.9968** on NBA totals; require
≥6 usable rungs and drop degenerate fits).

**Measured cost of ignoring this on KXNBATOTAL:**

```
the nominal +15 rung, at the last pregame bar:
   median EFFECTIVE K_t   14.3
   outside [12,18]        32.2% of events
   inside [12,18] for the whole tip-6h..tip window   only 47.2% of events; NEVER in 10.8%

|fair price at the true K_t − fair price at a nominal 15|:  median 3.07c
   larger than a 0.97c candidate edge in  81.3%  of events
   larger than the 2.24c two-leg taker fee in  62.8%
```

`sigma_t` is stable (within-event change tip-6h → last pregame: median −0.26). **All of the
instability is `m_t`.** A static strike label is therefore mis-stating moneyness by a full
grid step or more, a third of the time, and the error is several times the size of any edge
worth hunting.

Two corollaries:

- **Validate `m_t` against settlement.** On NBA totals, P(actual > `m_t`) = **0.519** versus
  0.542 against the ladder's geometric centre — `m_t` is the better median estimate and the
  listing centre is measurably stale.
- **Check whether the grid is censored.** KXNBATOTAL is a fixed 11-strike grid, 3 points
  apart, ±15 from centre, in 97.9% of 1,324 events; only 2.1% ever list more. When `m_t`
  drifts, the intended moneyness **falls off the end of the board and no rung replaces it**.
  Paired legs stop being symmetric: mismatch mean 4.84 pts, P(>3 pts) = 0.608.

## RULE 2 — CANDLE BARS ARE EMITTED ONLY WHEN THE TOP OF BOOK CHANGES

A missing minute means *the quote is unchanged*, **not** *there is no quote*. Any
cross-ladder aggregation must **forward-fill state per ticker** before combining rungs.

```
read raw          the pregame ladder looks 2-3 rungs deep
forward-filled    it is 11 rungs deep in 96.4% of minutes
validation        across 312,766 bar gaps, the next bar's yes_bid_open/yes_ask_open equals
                  the pre-gap close in 99.999% of cases
effect            minutes with >=6 usable rungs go from 35.6% to 97.4%
```

Skip the ffill and you will conclude the outer ladder is illiquid or unquoted when it is in
fact two-sided in **100.0%** of pregame minutes (one exception in ~440,000 bars). This is
exactly the shape of bug that manufactures false liquidity, false depth and false
availability findings.

**Also:** these candles cover the LIVE GAME as well as pregame — the fetch lookback runs
back from market close — and there is no reliable tipoff column. Any pregame statistic must
infer tipoff and state the rule. Three agents did so independently here and converged
(ladder-velocity regime switch ~35x; validated against the NBA :00/:10/:30/:40 ET slot grid
and a ~146-151 min tip-to-close interval).

**Local fast copies** (the /mnt/c originals are drvfs and very slow):
`/home/dpope/data/kalshi_local/kalshi_nba_candles.sqlite` and `..._totals.sqlite`.
