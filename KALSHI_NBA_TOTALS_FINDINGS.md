# KALSHI NBA TOTALS — SYSTEMATIC ERROR SEARCH, RESULTS (2026-09-13)

Trading mission: find a verifiable, historically profitable, executable rule in
Kalshi NBA totals. Data inventory: `NBA_TRADING_DATA_INVENTORY.md`.
Error map: `NBA_TOTALS_ERROR_MAP.parquet`.

**Nine of ten opportunity families are closed. No tradeable rule was found.**
One avenue remains genuinely open and is named in §4.

---

## 1. RESULTS

| family | verdict | decisive evidence |
|---|---|---|
| **#1 stale rung (leave-one-out)** | **NULL** | median book-vs-ladder disagreement **0.38¢**; ≥4¢ on 0.26% of signals, ≥8¢ on 0.00%. After +1¢ and dedup: **6 trades per season** |
| **#2 executable ladder arbitrage** | **NULL** | **0 pregame** occurrences in **17,755,696** ordered pairs; 92 in-game hits are bar-close artifacts (legs moved a median 13¢ *within* the bar vs a 0¢ baseline) |
| **#3 latency after center move** | not run | 1-minute floor (L2); needs forward collection |
| **#4 σ calibration, unconditional** | **NULL** | 8 probability buckets, all \|z\| ≤ 1.56, n=13,712 contracts; **sd(Z) = 1.0045** |
| **#5 close-game right tail** | **NULL, inverted** | close games have a *lighter* right tail (P(Z>0.5) 0.2678 vs 0.3085 Normal), blowouts heavier — backwards from the overtime mechanism |
| **#6 3PA dispersion** | **NULL** | Var(Z) spread z=+0.53, Levene p=0.524, discovery sign **backwards** (−2.20% sd) |
| **#7a pace dispersion** | **NULL — market is right** | dispersion is **real and replicates** (Var 1.0980 z=+2.63 → 1.1687 z=+2.10 OOS) but Kalshi already widens σ by **+4.78%** against a **+4.79%** realized excess |
| **#7b pace mismatch** | **NULL** | z=+1.04, and **flips** out of sample (z=−0.32) |
| **#8 intentional-foul right tail** | **NULL, inverted** | state is the *thinner*-tailed group (excess kurtosis +0.16 vs +0.56); right tail light at 0.5/0.75/1.0 |
| **#9 blowout garbage time** | **NULL, inverted** | backwards on variance, skew **and** kurtosis; Kalshi's σ narrowing matches realized variance **to 0.004** |
| **#10 / center errors** | **FAILS OOS** | best state (MOVE≥2 & \|s\|>9): +2.724 pts, 56.7% OVER, **+8.32% ROI, 7/7 seasons** in discovery → **−10.8% ROI** out of sample |

Across #6–#9: **14 group-level tests** of Var(Z)=1. Two exceeded \|z\|=2 (expectation
under the null 0.7), both in #7a — and that one is the one Kalshi already prices.

---

## 2. THE TWO RESULTS THAT MATTER MOST

**Kalshi's NBA totals ladder is internally coherent and conditionally
well-calibrated.** #1 and #2 required no basketball forecasting at all and both
died: the surrounding rungs almost never imply a target rung is stale (median
disagreement 0.38¢), and there is no arbitrage. #4 then showed σ is
unconditionally calibrated to sd(Z)=1.0045, and #6–#9 showed that conditioning on
3PA, pace, pace conflict, foul environment or spread magnitude **does not open a
σ error**. Where Kalshi moves σ it moves it by the right amount; where it leaves
σ flat, there is nothing to respond to.

**A structural argument closes the dispersion class independent of statistics.**
A dispersion mispricing pays in proportion to \|t\| = \|K−μ\|/σ, and **Kalshi does
not list \|t\|**:

```
12,128 rungs:  p50 |t| 0.453   p90 0.859   p99 1.097   MAX 1.456
bands:  center 6,690 | near 5,073 | far 365 | deep (|t|>=1.5) ZERO
```

Taking the largest measured dispersion error at face value (Var=1.1687), the
implied mispricing over the rungs that actually exist is **1.59–1.87¢/contract**
against a round-trip taking cost of **3.168¢** — about half — and it *shrinks*
with distance (1.34¢ at \|t\|=1.5, 0.34¢ at 2.5), so a deeper ladder would not
rescue it. Inverting: the smallest σ error that could pay taking cost is
**Var ≈ 1.29**, which registers at **z ≈ +7.9**. Nothing above z=+2.63 exists in
nine seasons. **A "buy deep tails" rule on this venue is unfalsifiable, not
falsified — do not preregister one.**

---

## 3. DO NOT RE-RUN

1. **3PA as a dispersion state.** Dead on 7,231 discovery games, sign backwards.
   *Era artifact to record:* league 3PA rose enough that only **18 of 1,005**
   test games land in the frozen bottom-20% bucket — that bucket is extinct, not
   tested.
2. **Stylistic pace conflict.** Does not separate, does not replicate.
3. **Expected pace as a tradeable dispersion edge.** The phenomenon is real —
   *keep it* — but fully priced and worth at most half the round-trip cost.
4. **Endgame intentional-foul fat right tail.** Refuted, not merely unsupported.
5. **Blowout garbage-time fat tail.** Inverted on all three moments. With #5 also
   inverted, **both ends of the spread axis are now closed for tail hypotheses.**
6. **Taking, generically.** Buy-YES-everything −3.706¢/ct; buy-NO-everything
   −1.990¢/ct; and in every family **the exact reverse of the frozen direction
   also loses.** The "we had the sign backwards" rescue is refuted four times.
7. **The #5 one-season blowout tail finding.** It **relocates to the mean** —
   blowout mean Z=+0.0852 (t=+3.36) = 1.54 pts; re-standardising collapses the
   tail gap to z=+0.78, KS on shapes p=0.43. It was a level effect misread as
   dispersion.

---

## 4. WHAT REMAINS OPEN

**The maker side is untested across every family above.** Every number in this
document pays the ask and the fee. This is a null about **taking**. The
programme's own measurement is that taking a 2¢ Kalshi book costs 2.76pp against
−110's 2.381pp, while **resting a bid costs ~0.76pp** — a 2¢/contract swing that
is larger than several of the effects being hunted. `AMENDMENT_live_trading.md`
has the measured table.

Two leads carried forward, **explicitly not trades**:

- **Blowout OVER bias, +1.54 pts** (mean Z +0.0852, pooled t=+3.36, same sign in
  2025). A *level* effect exceeding the 0.79-pt mechanism benchmark, but never
  individually significant in any season (max t=1.91), Kalshi's own Z shows no
  spread slope (t=+1.19), and traded on 2025 rungs it returns **−2.018¢/ct**.
  Sub-vig. Maker-side only, if ever. Winkelmann caution applies in full.
- **\|spread\| ∈ [0,2): Var(Z)=1.1409** (n=674, z=+2.59). Genuine excess
  dispersion in near-pick'em games, but two-sided, **post-hoc** among five
  buckets inspected after #8 resolved, and it needs a venue quoting past 1.5σ to
  be expressible. Requires its own frozen prereg.

#3 (latency after a center move) is unrun and needs the forward collector.

---

## 5. POWER — what this search could and could not see

**Could detect.** Step A MDE: \|Var−1\| ≥ 0.104 in a 20% bucket, ≥0.060 in the
middle 60%; group-spread MDE 0.120–0.147 Var units (≈6–7% of sd). Step C MDE
**1.24¢/ct** naive, **1.85¢/ct** game-clustered. Measured returns of −3.4 to
−5.3¢/ct are **2–4 MDEs below zero — a confident negative, not an underpowered
one.** The search is **overpowered for the economically relevant effect size**:
the minimum tradeable σ error is Var≈1.29 (z≈+7.9) and nothing above z=+2.63 was
found.

**Could not detect.** A true σ error of **1–6%** — which is exactly where every
point estimate sits. Resolving #9's −3.2% variance estimate would need ~115,000
games; eight seasons is 9,489. A right-tail excess below ~3.3pp in P(Z>1). An
edge below ~1.2–1.9¢/ct overall. **Anything at \|t\| ≥ 1.5, at any sample size** —
a venue constraint, not a data constraint. **The maker side entirely.**

**Every TEST number rests on one Kalshi season** (976–1,105 games). se(hit) ≈
2.5pp. That is enough to kill a +8% ROI claim and not enough to confirm a
1-point edge. L3 in the inventory; unfixable by further search.
