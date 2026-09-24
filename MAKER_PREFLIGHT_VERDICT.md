# PRE-FREEZE AUDIT OF H-MAKER — DO NOT FREEZE (2026-09-13)

Six independent checks against the 1-min ladder capture (429 events, 1,256,843 bars,
2025-10-21..2025-12-23) before writing the preregistration.

**Five economic/statistical checks reject the maker hypothesis; the execution markout
diagnostic passes but cannot rescue it.**

That distinction matters. **The strategy died because there was no underlying mispricing
left to capture, not because the execution layer destroyed a good signal.** Passive fills
were not followed by toxic-flow decay — which is a positive finding about this venue's
microstructure and should be carried forward, not buried in a "6/6" tally.

## THE PRIMARY CLOSURE REASON, STATED ONCE

> **[WITHDRAWN 2026-09-24 — OVERSTATED. See `KALSHI_REPEATED_LADDERS.md`.**
> The curvature below (quadratic −7.09e−05, t = −6.09) was computed at **mid**,
> which is not an executable price, and was not tick-aware. `KXNBATOTAL` is
> `linear_cent`: with ±0.5¢ of slack — the grid's own rounding unit — normal
> feasibility rises from 30.1% to 66.6%, so exact-containment failure is not
> evidence of curvature. Curvature may still exist but must be established
> against the discrete quote grid from executable bounds. The verdict of this
> document — DO NOT FREEZE — rests on four other independent failures and
> stands.]**
>
> ~~Kalshi already embeds the same right-skew curvature we thought we were exploiting.~~

H-MAKER assumed the counterfactual *"truth is skewed, Kalshi is normal."* The correct
counterfactual is *"truth is skewed, and Kalshi already knows it."* Fit the body and
examine the residual curvature directly and the venue is adding **+1.01c of paired skew —
essentially the entire historical +0.97c phenomenon.**

Everything in sections 2-6 is corroborating evidence. None of it is the reason.

The audit cost an afternoon and prevents committing the 2026-27 season to a test that
could not have succeeded.

---

## 1. THE PREMISE IS MEASURABLY FALSE

H-MAKER rests on *"Kalshi prices the ladder as ONE NORMAL, and a normal has zero skew."*
I took that from `LADDER_ASSUMPTION.md`'s per-rung MAE of 0.909c and never tested curvature.

```
per-event probit points are NOT collinear:
    quadratic coefficient  -7.09e-05  +/- 1.16e-05   t = -6.09

Kalshi's ladder ALREADY prices  +1.01c  [+0.68, +1.35]  of PAIRED SKEW
relative to its own body-fitted normal (interior 9 rungs, endpoints excluded so the
benchmark is independent of the quotes being tested) — and the departure is MONOTONE in K,
exactly as the hypothesis says the truth is.
```

**The venue has already taken the trade.** The residual is `0.97c claimed − 0.45–1.10c
already quoted = −0.13c to +0.52c, sign not established.**

Measured directly against Kalshi's own quotes at K=15: **paired gap −0.43c, 95% CI
[−6.54, +5.69].** Negative point estimate, CI covering everything.

## 2. THE TEST IS UNRUNNABLE — 28 SEASONS, NOT ONE

Per-game sd of the paired endpoint outcome is **64.5c**.

```
428 games (what we have)   95% CI  +/- 6.1c around a claimed 0.97c effect
1,324 games (one season)   95% CI  +/- 3.5c            se 1.77c
80% power on +0.97c        34,763 games  =  28.3 NBA seasons
```

A "run 2026-27 and see if it's positive" criterion cannot resolve a 0.97c effect. The
markout agent reached the same conclusion from the P&L side: per-game sd 50.0c, so one
season gives **t = 0.70** on a true +0.97c gross edge and **t = 0.31** on a +0.42c net edge.

## 3. THE DIRECTION MAY BE BACKWARDS

At mid, against its own realised settlement frequency, **the +15 rung is 1.21c RICH and
the −15 rung is fair.** The hypothesis's paired structure **loses 1.26c at mid** on this
sample. The point estimate has the wrong sign.

## 4. "+15" IS NOT A STABLE OBJECT — your K_t concern, confirmed and worse

Recovering `m_t` per event-minute by probit fit (median fit r2 **0.9968**; `m_t` validated
against settlement — P(total > m_t) = **0.519** vs 0.542 for the geometric centre, so the
listing centre is stale):

```
at the last pregame bar, the nominal +15 rung sits at:
    median effective K_t  14.3     outside [12,18] in 32.2% of events
    inside [12,18] for the WHOLE tip-6h..tip window in only 47.2% of events; NEVER in 10.8%

|fair price at true K_t − fair price at a nominal 15|:  median 3.07c, mean 3.76c
    P(that error > 0.97c, the claimed edge)  =  0.813
    P(that error > 2.24c, the two-leg fee)   =  0.628

fair value TRAVEL under a resting order:
    over tip-6h..tip   median 4.65c   moves more than the whole edge in 99.7% of events
    over tip-30m..tip  median 1.84c   ... in 79.1% of events
```

And **the ladder is censored at ±15** — only 28 of 1,324 events (2.1%) ever list more than
11 strikes. When `m_t` drifts, the true +15 point falls off the grid and there is no rung
to replace it. The nominal pair is not a symmetric pair: leg-distance mismatch
**mean 4.84 pts, P(mismatch > 3 pts) = 0.608.**

Sigma does *not* drift (within-event change tip-6h → last pregame: median −0.26). All the
instability is `m_t`.

## 5. CAPACITY CAPS IT AT $300–500 A SEASON

```
median PAIRED pregame capacity at the endpoints:  40 contracts per game
top 10% of games hold 68.5% of all capacity (and are the flow most likely to be informed)
defensible frozen size S = 25 pairs; at 50% capture the mean fill is 14.6 pairs
=> roughly $300-500 GROSS per 1,230-game season at the full theoretical edge
```

Fees, at the *measured* endpoint prices (23c median mid, not the assumed 20c):
**1.15–1.30c per taker leg = 118–134% of the entire 0.97c edge.** Both legs must be maker
*and* the all-in maker fee must be under **0.485c/contract** (k < 0.028 vs the 0.07 taker
rate). Maker fee treatment on KXNBATOTAL is not determinable from this data.

## 6. THE ONE CHECK THAT PASSED, AND WHAT IT COST

**Markouts are FLAT, not decaying** — by the pre-stated decision rule, passive execution
survives:

| horizon | OVER buy-at-bid | UNDER sell-at-ask |
|---|---|---|
| +1 min | +2.684c | +2.967c |
| +5 min | +2.627c | +2.913c |
| +15 min | +2.688c | +2.884c |
| +30 min | +2.672c | +2.985c |

No monotone decay. But the pure adverse-selection term (referenced to the pre-trade mid) is
**−0.25 to −0.32c per leg, t = −4.4 to −6.6 ≈ −0.50c per pair — about 52% of the claimed
edge**, and the whole trade lives inside a 5.9–6.4c spread.

The other robust positive: **endpoints are two-sided in 100.0% of pregame minutes** (one
exception in ~440,000 bars). The market genuinely exists. It is just 5–6c wide with 40
contracts in it.

---

## VERDICT

**Do not write the preregistration.** The reason is singular: **the venue already prices
the skew.** Freezing a spec on the raw 0.97c would freeze it on a number Kalshi has already
taken.

Corroborating, in descending order of force:

| | finding |
|---|---|
| 1 | residual after what is already quoted: **−0.13c to +0.52c, sign unestablished** |
| 2 | direct quote-vs-settlement at ±15 shows no edge; **the +15 side looks rich (1.21c)** |
| 3 | `K_t` drift is several times the hypothesised edge, and the ladder ends at ±15 so intended moneyness **cannot be continuously maintained** |
| 4 | one prospective season is severely underpowered (**28.3 seasons** for 80% power) |
| 5 | capacity is trivial (**~$300-500/yr**) relative to the effort |
| — | adverse selection at 0.25-0.32c/leg is *not* catastrophic, but consumes a meaningful fraction of any residual |

## PROJECT CLASSIFICATION — NBA TOTALS

**Closed for trading.**

> Signed-return predictability is absent. Pregame conditional dispersion is either absent
> or already priced. Structural right skew is real and largely caused by overtime — but
> Kalshi already prices that skew into the ladder. The residual mispricing is statistically
> unestablished, operationally unstable because of moneyness drift, and economically too
> small for the available capacity.

**Kept alive as research, not as a trading programme:** the continuous-residual shape
analysis. Its ~0.54c standard error makes it the right estimator for characterising *how
accurately Kalshi prices higher moments over time*. It becomes interesting again only if
the venue's curvature changes, the ladder design changes, or a new market exposes deeper
tails.

That is a stronger endpoint than "we could not find a model." The anomaly was found, its
physical mechanism identified, the correct market-implied comparison discovered, and the
market shown to have already incorporated it.

## A METHOD ERROR TO CARRY FORWARD

Candle bars are emitted **only when the top of book changes**. Read raw, the pregame ladder
looks 2–3 rungs deep; forward-filled per ticker it is 11 rungs deep in 96.4% of minutes
(verified: across 312,766 bar gaps the next bar's open equals the pre-gap close 99.999% of
the time). **Any future code that reads these candles without a per-ticker forward-fill will
mis-measure the ladder.**

## IF ANYONE REOPENS THIS

The binary-settlement route is the wrong estimator, and there is a 6x better one. Estimating
the skew on the **continuous residual** gives se 0.129 on 360 games → **se ≈0.54c** on the
paired gap, against 3.4c for the binary route. That is a 40x reduction in the games needed.
It still does not make the ±15 pair tradeable — capacity and the already-priced skew are
independent blockers — but it is the only version of this question that is answerable at all.

**What this audit could never see:** book depth, queue position, trade direction, and the
maker fee. All four must be measured live before any size, and no historical analysis of
this dataset can substitute.
