# SECOND LINE — closing strategy: market-making the Kalshi NBA totals ladder

**Written 2026-08 at the close of the Kalshi research phase. This document does
what `PROSPECTIVE.md` did for the betting signals: freezes the strategy, its
preconditions, its rollout gates and its monitoring metrics before any further
data is seen. It authorizes measurement, then paper quoting. It does not
authorize live capital — that requires the Stage gates below to pass, in
order.**

---

## 1. The strategy in one paragraph

Quote a two-sided market ("the second line") on all rungs of the Kalshi NBA
full-game totals ladder, from a fair-value curve that corrects four measured
defects in the incumbent quoter's pricing function. Collect the bid/ask spread
and the maker fee asymmetry from crossing flow; earn the pricing tilt on top.
This is a market-making business with a pricing edge, not a betting strategy:
the bet is not "we know where the total lands", it is "our probability curve is
closer to the truth than the one currently quoting these order books, and we
get paid the spread while proving it."

## 2. Why now — the evidence base

Every component was measured in this project, most of it this phase:

**The incumbent is one algorithm, and we know its model.** All eleven rungs sit
on a single smooth Gaussian (fit RMSE 0.02 z-units; rung deviations MORE
uniform than chance, 3rd percentile of the bootstrap null). Its mean is the
sportsbook close (corr 0.9921; disagreement pure noise). Its variance is the
right level-scaled sd. Its quotes trail its reference: the closing snapshot
retains ~5% of the book's daily move (t = −8.24), asymmetrically (down-moves
leave 3x the staleness of up-moves — the first retail signature found in this
data).

**The pricing stack** (per-fill contributions, all measured):

| component | size | evidence |
|---|---|---|
| spread capture | ~1–1.8pp/fill | median 2c, mean 3.6c spread (14,471 rungs) |
| fee asymmetry | ~1.3pp/round trip | maker fee = 25% of taker (schedule, verified) |
| OT-mixture shape | +0.75pp ATM, every game | deductive: regulation residual is exactly Gaussian (skew +0.066, kurt −0.002 after removing OT points) while the ladder is symmetric; projection slope +1.43 ± 1.26 consistent with 1; log-loss improves with zero fitted parameters |
| CrewShock (frozen) | ~+3pp on ~236 games/season | 8-season slate; **weak in 2025-26 (M1/M2 alert)** |
| final week (frozen) | ~+6pp on ~69 games | 55.07% over in 2025-26, on top of 8-season history — M5 healthy |
| staleness defense | avoids −2 to −10pp on move days | t = −8.24; book moves ≥1pt on 84% of days |

**The nulls are load-bearing.** Eight dispersion tests, team-mean and team-sd
calibration (true between-team variance ≤ 0 by method of moments), the
matchup-distribution race (R² 0.0007, both horses dead) — together these
certify that the WIDTH we quote (the ladder's own level-scaled sd) cannot be
exploited by a counterparty. A maker's worst structural failure is a variance
error; we proved there is no variance error available to make.

**The pool.** 781M contracts ($781M notional) traded on 2025-26 regular-season
NBA totals; ~634k contracts per game (median 517k). Mostly live; the pregame
slice alone is plausibly $60–80M/season. Scale is not the constraint.

**The backtest bracket.** Executable-taker bound +0.2% to +2.4% ROI (positive
in all three ablation legs, none significant — as expected at these edge
sizes); 100%-fill maker bound +8.4% to +9.7% (t ≈ 4, but the fill assumption
does most of the work). Truth is between; the candles locate it.

## 3. The fair-value curve, frozen

```
mu    = sportsbook closing total (live-tracked, see §5)
        + 1.434 if CrewShock >= +0.8682          (frozen ref_features.py)
        + 2.693 if days_left <= 7                (frozen final-week rule)
sd    = the ladder's own fitted sd               (calibrated; do not model)
shape = OT mixture: p_OT = 5.24%, empirical OT-points distribution
        (E[J] = 24.3, sd 9.8), from 2017-18..2024-25 -- refit each summer
        from completed seasons only
S(K)  = (1 - p)*Phibar((K - m0)/s0) + p * mean_j Phibar((K - m0 - j)/s0)
        with m0, s0 matching the ladder's mean and variance exactly
```

Explicitly excluded from the curve, with reasons of record:
- the +0.509 league mean over-bias (sub-hurdle; ablation L2 showed it REDUCES
  the maker bound by ~1.3pp — it trades spread capture away for a weak tilt)
- any team, matchup, pace, 3PA, rotation, rest or dispersion adjustment
  (eight nulls; `matchup_dist.py` R² 0.0007)
- any change to the two frozen signals' thresholds or magnitudes

## 4. What the small edges do in a making context

1. **Tilt** — fills are +EV on average instead of coin flips.
2. **Selection** — quote asymmetrically: tight on the side our curve wants
   filled, wide on the side it does not.
3. **Inventory preference** — the frozen signals are expressed PASSIVELY: on a
   CrewShock game we lean quotes Yes-ward and get PAID to accumulate the
   position a bettor pays to take. Passive expression of a validated signal is
   strictly cheaper than active.

## 5. The precondition — defense before offense

Quoting makes us the incumbent. The measured staleness (5% residual at the
close; book moves ≥1pt on 84% of days, sd 4.4pts ≈ 10pp) is a portrait of the
current maker being picked off. One unhedged pick-off (~4–10pp) eats roughly a
week of spread capture (~2–4pp/fill).

**Hard precondition: a live sportsbook-line feed, and quote withdrawal/reprice
on reference moves faster than the cross-venue arbitrageurs.** Without this,
the strategy is negative regardless of pricing quality. The defense is the
business; the tilt is the margin.

## 6. Staged rollout with gates

**Stage 0 — MEASURE (now; no capital).** Run the candles extraction
(1-minute bid/ask/size, T−180 → close, all 14,787 markets; resumable via
`fetch_log`). Deliverables: fill-probability estimates at the bid by depth and
time-to-tip; adverse-selection cost around book moves ≥1pt; the incumbent's
reprice latency (our competitive benchmark); lifetime of the 4%-at-close
inversions.
**GATE G0:** estimated net edge per fill (spread + tilt − adverse selection)
> 0 with the measured fill rate > 20%. Quantified by `kalshi_composite.py`
($100/line, 100 contracts/side): the composite earns +5–7% ROI (~$4k–22k per
season, ~$8–10k working capital) at adverse-selection tilt κ=0 and the
**break-even is κ ≈ 0.057** — the business dies if more than ~53% of one-sided
fills land on the eventual losing side. G0 therefore requires the candles- or
paper-measured effective κ (after quote-pulling defense) to come in **below
0.05**. Fail → the strategy closes here and the research reverts to the
`PROSPECTIVE.md` betting book alone.

**Stage 1 — PAPER QUOTE (2026-27 season start; no capital).** Run the curve
live; log every quote we would have posted and mark fills against observed
trades/quote-crossings. Minimum 300 games before evaluation.
**GATE G1:** realized paper edge per fill within 2 se of the Stage-0 estimate,
AND pick-off frequency on book moves < 25% of move events.

**Stage 2 — SMALL LIVE (only after G1).** Maker-only, position caps per game
and per night, kill-switch on feed outage (all resting orders pulled if the
book feed is stale > 10 seconds). Flat sizing; no compounding until an edge is
established at the realized fill rate.

## 7. Monitoring metrics (Stage 2), pre-registered

| # | metric | ALERT if |
|---|---|---|
| S1 | fill rate on resting quotes | < half the Stage-0 estimate |
| S2 | realized edge per fill vs modeled | < modeled − 2 se over any 500-fill window |
| S3 | pick-off share of fills (fills within 60s before an adverse book move ≥1pt) | > 25% |
| S4 | inventory P&L on CrewShock-leaned games | M1/M2 alerts govern — a second consecutive mechanism alert removes the CrewShock lean (the shape and calendar components continue) |
| S5 | shape component: realized ATM No-side hit rate vs mixture prediction | outside the mixture's 95% band over a season |
| S6 | operational: feed staleness events, quoting errors | any unhedged loss > 20x the mean fill edge |

Escalation: S1/S2/S3 alerting in the same 500-fill window suspends quoting;
S6 suspends immediately pending a written post-mortem. Resumption in either
case requires a new gate pass, not a judgment call.

## 8. Relation to the frozen betting book

`PROSPECTIVE.md` is unchanged and runs in parallel. The frozen signals appear
here only as quote tilts; their thresholds, magnitudes and monitoring (M1–M5)
are governed there. If CrewShock is suspended there (a second consecutive
M1/M2 alert — 2026-27 is decisive), its lean is removed here the same day; the
second line continues on spread + fees + shape + calendar.

## 9. Known unknowns, ranked by leverage

1. **Fill rate and adverse selection** — worth the entire +1% to +9% bracket.
   Answered by Stage 0/1 at zero capital cost.
2. **The incumbent's identity and latency** — if the incumbent is Kalshi's own
   designated MM program or a sophisticated firm, the staleness we measured
   may close before we arrive. Stage 0 measures whether it is still there in
   the candles.
3. **Live (in-game) flow** — most of the volume, entirely unmodeled here. Out
   of scope for this document; a live-quoting extension requires its own
   pre-registration and a possession-level pricing model.
4. **Competition** — the moat is effort, not information. A third algorithm
   can do to us what we do to the incumbent. The durable components are the
   fee seat and operational quality; the tilt components decay on their own
   schedules (CrewShock is already in question).
5. **Plumbing** — everything measured says the pricing is right; nothing
   measured says the operation can be run well. That is what Stages 0–1
   de-risk before a dollar is quoted.

## 10. What is NOT authorized

- live quoting before G0 and G1 pass, in that order
- taker execution of the stack (fails every establishment gate; the staleness
  snipe is a separate strategy requiring its own pre-registration after the
  candles arrive)
- quoting the WNBA or any sub-4-season-establishment market (G3 screening rule)
- any addition to the fair-value curve not pre-registered with its own frozen
  spec (this includes re-adding the mean over-bias, and any quarter/half-market
  quoting — `PREREG_q1q3_visalloc.md` governs those separately)
- discretionary overrides of gates, alerts or kill-switches
