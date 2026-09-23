# ±15 MAKER HYPOTHESIS — PRE-FREEZE AUDIT (2026-09-13)

Six checks against the captured ladder, all keyed to contemporaneous moneyness `d_t = K − m_t`.
**All six came back unfavourable.** The one that returned favourable (markout) was overturned by
its adversarial verifier. **Recommendation: do not freeze this specification.**

---

## 0. A CORRECTION TO MY OWN PREMISE

I told you only ~4.5 rungs carry a two-sided pregame quote and that a probit fit succeeded on
132 of 429 events. **That was an artifact and I withdraw it.** The candle feed omits minutes in
which nothing happened; a resting Kalshi quote persists until cancelled, so quotes must be
**forward-filled** per rung. Verified on 312,766 gaps: the bar after a gap opens at exactly the
close of the bar before it (100.000% for gaps >3 min).

```
                          bars-only (what I reported)   forward-filled (correct)
usable two-sided rungs              ~4.5                     10.69 (median 11)
P(>=6 rungs, probit-able)            31%                      96.8%
p=0.50 bracketed                    53.1%                     99.3%
```

**This also undermines my σ-reliability result** (`corr(σ_a, σ_b) = +0.4265` → "true σ variation
is 3.6%"), which was computed on the same bars-only snapshots. That number should not be relied
on until recomputed with carry-forward. The centre `m_t` is fine — `corr(m_ff, m_bars) = 0.9956`.

---

## 1. THE ESTIMATE IS LESS THAN HALF WHAT I REPORTED

`band_sensitivity` found a settlement-convention error in the discovery-sample estimate itself.

The +0.97c figure treats the two rungs as mirror-image **strict** tails. **On Kalshi every strike
is a `greater` contract and a total landing exactly on a strike settles NO.** The lower rung is a
`greater` contract, not a `less` contract, so games landing exactly on it belong in the left tail.

```
                                   as I stated it      in Kalshi's actual convention
at exactly d = 15                    +0.97c                  +0.425c  (SE 0.659)
band-averaged {13.5, 15, 16.5}       +1.116c                 +0.312c  (SE 0.641,  z = +0.49)
```

**56% of the estimate at d=15, and 72% across the traded band, was boundary mass that settles
against the lower leg.** z falls from 1.67 to **0.49**.

It does survive the anchor change (opening +1.042c vs closing +0.968c in the old convention), so
moneyness drift was not the problem. The settlement convention was.

**And the per-leg split is unidentified.** Because the benchmark normal is centred on the median,
it forces model-right-tail ≡ model-left-tail, so the paired sum is σ-free but the split between
legs is determined entirely by an unknown σ: at σ=14 the upper leg carries +6.05c, at σ=18.06 it
carries −0.07c, at σ=22 it carries −4.52c. The sum is +0.425c throughout. **A prereg cannot state
a per-leg expectation without first committing to a σ estimator.**

## 2. THE ESTIMAND IS DOMINATED 3:1 BY SPREAD CAPTURE

At the traded moneyness the median bid-ask spread is **6c (upper)** and **5c (lower)**. Half-spread
capture is therefore **3.00c and 2.50c — two and a half to three times the entire discovery-sample
estimate.** Even after the exact fee the pure spread residual (+1.65c / +1.32c) exceeds the skew
being tested.

**This is a liquidity-provision experiment with a skew tilt, not a skew experiment.** Any positive
prospective P&L at these rungs is presumptively spread capture and could not be attributed to the
mechanism.

The fix, and it is the single most valuable thing the audit produced: **preregister a moneyness
control.** Run the identical passive rule at `d_t ∈ [−4.5, +4.5]` on the same events, same
reference time, same posting logic, and make the **contrast** the primary endpoint. Without it the
skew is unidentified.

## 3. FEES ARE HIGHER THAN I QUOTED

I used 1.12c at P=0.20. The measured in-band mid is ~22c, and Kalshi rounds the fee **up to the
cent**: 1.20c per leg unrounded, **2c on a 1-contract order**, 2.40c for two legs.

## 4. FILL RATE — THE BOUND IS LOW, AND THE MECHANISM LEG IS THE THIN ONE

Cannot be estimated without depth or queue data, only bounded above:

| | UPPER (the mechanism leg) | LOWER |
|---|---|---|
| P(any print at/below best bid) over a whole pregame window | **≤ 43.8%** | ≤ 39.7% |
| per-minute | ≤ 0.66% | ≤ 1.29% |
| median in-band minutes with such a print | **ZERO** | ZERO |
| median bid-hitting print size | **1 contract** | 43 contracts |
| median cumulative in-band volume per contract | **1** | 25 |

**The leg the overtime mechanism says should be cleanest has almost no flow to make against** —
a median of 19 contracts traded per in-band rung across the entire 6h pregame window.

## 5. AVAILABILITY — THE PAIRED TRADE EXISTS LESS THAN HALF THE TIME

On an 11-rung 3-point grid spanning C±15, a rung sits in [13.5,16.5] iff `m_t ≤ C+1.5`, and in
[−16.5,−13.5] iff `m_t ≥ C−1.5`. So **both legs ⟺ |m_t − C| ≤ 1.5**:

```
upper leg available   72.1% of pregame event-minutes   (86.4% of events ever)
lower leg available   75.0%                            (87.6%)
BOTH simultaneously   47.1%                            (70.8%)
```

And this is not drift — `m_t − C` has between-event sd **2.645** against within-event sd **0.513**,
so ~93% is a **persistent listing offset fixed at listing**. 13.6% of events never offer the upper
leg at all. Churn is manageable: a 15-min trailing median filter on `m_t` cuts re-placements to 1.4
per event and raises the median in-band spell to 130 min.

## 6. SETTLEMENT EV DOES NOT REPRODUCE, AND THE MECHANISM LEG HAS THE WRONG SIGN

On Kalshi's own prices and settlements at the traded moneyness:

| leg | realised | implied | **realised − implied** | 95% CI | n |
|---|---|---|---|---|---|
| **UPPER** | 21.55% | 23.19c | **−1.64c** | [−6.37, +3.09] | 297 |
| LOWER | 77.57% | 78.17c | −0.60c | [−5.32, +4.12] | 321 |

Both point estimates negative. The upper leg — the one the mechanism predicts should be cleanest —
carries the **opposite sign**, negative in 11 of 12 sensitivity variants. Executable EV is negative
everywhere: buying at the prevailing ask loses −5.95c gross.

The CIs are wide enough to contain +0.97c, but the MDE is **6.9c, about seven times the effect**.
A wide-CI pass is not confirmation.

## 7. THE MARKOUT RESULT WAS OVERTURNED

`markout` reported that the kill condition did not fire: pregame markouts flat, upper leg +0.02c
at +30 min. **Its verifier overturned it on three counts:**

1. The one favourable number (+0.81c on the upper leg at the last pregame bar) is a **spread-
   widening artifact** — the bid *falls* 0.86c while the ask rises 2.50c. The identical +0.72c
   appears on 116,134 minutes where **nothing traded at all**.
2. Measured against realisable prices (buy at bid, exit at bid), **both legs are negative:
   −0.86c upper, −1.38c lower (t = −2.98)**.
3. Its event filter is a function of the outcome: the `|Δm_t|` rule fails on games that blow
   through the top rung, so it **drops right-tail games at 28.5% vs 19.1% (p = 0.031) — it selects
   against the overtime games that are the entire mechanism.**

The lower leg's aggressor-conditioned decay (−0.146c at +15, −0.247c at +30, −0.554c by tipoff) is
the kill pattern at about half the stated magnitude, and it is on the leg whose mechanism is
weakest.

## 8. A SEASON CANNOT DECIDE THIS

Measured in-band contract rates are 0.70 (upper) and 0.75 (lower) per event, so a 1,230-game season
yields ~856 and ~925 contracts:

```
95% CI half-width      +-2.83c (upper)   +-2.66c (lower)
80%-power MDE           4.04c             3.80c
the estimand            +0.312c band-averaged
seasons needed          ~15-17
```

**A single prospective season would report the estimate inside a CI roughly nine times its width.**
A prereg written now would commit a season to a test that can neither pass nor fail.

## 9. A DIRECTION ERROR IN MY OWN WORDING

"Fade the −15 tail" was glossed mechanically as selling YES on the `K = m−15` contract. That is a
bet **on** that tail, not a fade of it. The spec would have to state the lower leg as an explicit
buy/sell of a named contract, not in tail language.

---

## RECOMMENDATION

**Do not freeze. The hypothesis as stated does not survive its own pre-freeze audit.**

What would have to change before this is worth a season:

1. Restate the discovery-sample estimate in Kalshi's settlement convention — **+0.312c, z=+0.49**,
   not +0.97c at z=1.67. At that size it is not distinguishable from zero in the discovery sample.
2. Make the primary endpoint the **moneyness contrast** (|d_t|≈15 vs |d_t|≈0), or the skew is
   unidentifiable against a 3x-larger spread term.
3. Fix the lower-leg direction in contract terms.
4. Commit to a σ estimator if any per-leg expectation is to be stated.
5. Freeze a tipoff source **outside the ladder**, since the natural in-ladder rule selects against
   the mechanism's own games.
6. Accept that the answer needs ~15 seasons, or change the estimand.

**The honest status: the ±15 skew is a discovery-sample curiosity of about a third of a cent, sitting
under a spread three times its size, on a leg whose settlement sign points the wrong way, with a
fill ceiling near 40% and a median of one contract of flow.** The audit did its job — it cost a few
hours instead of a season.
