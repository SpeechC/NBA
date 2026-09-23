# THERE IS A SYSTEMATIC ERROR — IT IS IN THE THIRD MOMENT (2026-09-13)

> **CORRECTION, same day, after the ladder gate.** Two claims below need amending and the
> trade is dead. See §6 at the end. In short: (a) "the book prices the median" should be
> "the closing total is approximately a median forecast of a right-skewed distribution" —
> now established literally, P(dev>0 | no push) = 0.5047, CI [0.494, 0.515]; (b) "overtime
> makes it permanent" should be "overtime makes positive skew structural; whether Kalshi
> continues to price it with a symmetric model is an empirical question"; and (c) **the
> rungs where the mispricing is measurable do not exist** — Kalshi's deepest captured rung
> is |t| = 1.456 and the gaps are at |t| = 1.92-2.20.

Prompted by a direct challenge: *are you sure we cannot find a systematic error even if we
cannot attribute it?* The answer is **no, I was wrong** — but the error is not where every
previous test looked.

---

## 1. THE BOOK PRICES THE MEDIAN, NOT THE MEAN

```
mean dev   +0.5317   se 0.1862   t +2.86   <- a REAL, significant systematic error
median dev  0.00 exactly
over-rate   0.4993
```

A +0.53-pt mean *should* give 51.17% overs. It gives 49.93%. **The book is centred on the
median and the mean is displaced by right skew.** That single fact explains every
mean-based finding in this project that failed to convert into a hit rate.

| stratum | n | mean | **median** | over% | skew |
|---|---|---|---|---|---|
| ALL GAMES | 9,405 | +0.532 | **0.00** | .4993 | +0.231 |
| highest total decile | 871 | +0.890 | **−0.50** | .4891 | +0.389 |
| close mod5 = 1.0 | 795 | +1.556 | +1.00 | .5044 | +0.436 |
| both teams B2B | 464 | +0.484 | **0.00** | .4957 | +0.084 |
| April (ex-COVID) | 632 | +3.128 | +2.50 | .5633 | +0.124 |
| blowout \|spread\|≥10 | 1,797 | +1.562 | +1.50 | .5242 | +0.129 |
| pick'em \|spread\|≤2 | 1,350 | −0.372 | −1.50 | .4652 | +0.378 |

Note the split: the high-total decile has a **positive mean and a negative median** — pure
skew, untradeable. April and the spread strata genuinely move the median, which is why they
were the only things that ever converted.

## 2. WHAT IS NOT THERE — the unattributed-error battery

Everything you would run if you wanted a directional error with no mechanism attached:

| test | result |
|---|---|
| team fixed effects on dev (30 dummies) | **joint F = 1.056, p = 0.384** — null. Max \|t\| 3.10 (Utah) is the expected max of 30 draws |
| does a team's own prior error predict its next? | prior-5/10/20/40: t = +1.31, +0.91, +0.86, +0.77 — **null** |
| game level, both teams' priors + close | beta +0.031, t +0.94, edge 0.187 pts vs a 1.12 bar |
| bet the sign of the prior error | **−$22,480**, z −2.81 |
| FADE the prior error | **−$43,915**, z −5.48 |
| key numbers (whole vs half, mod 5) | nothing; over-rates .479–.525 with no pattern |
| the 5 unused box-score columns (A, ST, BL, PF, DR) | **joint p = 0.839**, R2 0.00029, combined edge 0.309 pts, betting it −$27,444 |

**The pricing error is white noise in its first moment.** It does not persist, it is not
team-specific, and it is not in the box-score columns the earlier work had not touched.

## 3. WHAT IS THERE — the ladder prices a normal and the truth is skewed

`LADDER_ASSUMPTION.md` established that Kalshi's NBA ladder is **one normal curve**,
`P(T>K) = 1 − Φ((K−mu)/sigma)`, per-rung MAE 0.909c, implied sigma 18.218 vs realised
18.265. **The centre and the width are right. A normal has zero skew. The residual has
+0.231.**

Empirical tail frequency vs what that normal implies:

| rung K | normal P(dev>K) | **actual** | normal P(dev<−K) | **actual** | paired gap | **z** |
|---|---|---|---|---|---|---|
| 20 | 14.05c | 13.60c | 12.78c | 12.17c | +0.15c | +0.31 |
| 25 | 8.77c | 8.44c | 7.87c | 7.24c | +0.30c | +0.77 |
| 30 | 5.14c | 5.16c | 4.55c | **3.98c** | +0.59c | +1.94 |
| **35** | 2.82c | **3.31c** | 2.46c | **1.89c** | **+1.05c** | **+4.55** |
| **40** | 1.44c | **1.97c** | 1.24c | **0.79c** | **+0.98c** | **+5.76** |
| 45 | 0.69c | **1.06c** | 0.58c | **0.39c** | +0.56c | +4.56 |

**The normal underprices the over tail and overprices the under tail, monotonically, at
every distance beyond ±25.** At ±40 the true over-tail is 1.4x the normal's and the true
under-tail is 0.6x. `P(dev>+40)/P(dev<−40) = 2.50`.

The trade is symmetric and needs no forecast: **buy the far OVER rung, sell the far UNDER
rung.** The edge is derived from a shape mismatch, not fitted to outcomes.

## 4. WHERE THE SKEW COMES FROM — it is overtime, almost entirely

```
OT games: 5.17% of the sample, mean dev +22.83 in them vs -0.68 in regulation
OT alone contributes +1.215 pts of mean -- 229% of the observed +0.532
skew EXCLUDING OT games: +0.067   (vs +0.231 including)
P(dev>30)/P(dev<-30) excluding OT: 0.86   (vs 1.30 including) -- it REVERSES
```

Overtime is a one-sided event: it can only add points. Nothing symmetric subtracts them.
That is the entire mechanism, and it means the mispricing is **structural and permanent**,
not a behavioural bias that gets arbitraged away.

**A prediction I made from that mechanism, which the data rejects.** If OT drives the skew
and OT is likeliest in close games, the far-tail asymmetry should be largest in pick'ems.
It is the opposite:

| | P(OT) | skew | P(dev>30)/P(dev<−30) |
|---|---|---|---|
| \|spread\| ≤ 3 | **0.0627** | +0.334 | **0.94** |
| \|spread\| 3-8 | 0.0532 | +0.223 | 1.36 |
| \|spread\| > 8 | **0.0396** | +0.158 | **1.62** |

OT drives the *third moment* (skew is highest in close games) but not the *far tail* (the
ratio is highest in blowouts). Two mechanisms, not one — OT for moderate overshoots,
something else in blowouts (garbage time, foul-fests, running clock) for the far tail. **That
is unresolved and it matters, because it decides which games to put the trade on.**

## 5. WHY THIS IS STILL PROBABLY NOT MONEY

Sized at the ±30 pair: 0.59c edge on 9.7c of premium (6% relative), which at 100 contracts
across 1,230 games is **$72,437 a season gross**. Every one of the following is larger than
the edge:

1. **The tick.** 1c minimum on a 4-5c contract is 20-25%. A 0.59c edge at ±30 is
   **sub-tick** — you cannot express it. Only ±35/±40, at ~1.0c, clear the tick at all.
2. **The fee.** ~7% of contract value. Held to settlement it is paid once, not twice, which
   is the one thing working in this trade's favour versus
   `kalshi-nba-microstructure`'s round-trip verdict — but it is still 0.1-0.3c.
3. **Depth.** Outer rungs are the thinnest part of the book. `kalshi-fill-test-result`:
   wide books have the edge and no size (10 contracts).
4. **The rungs may not exist.** The ladder is **~11 strikes**. If they span ±25 points there
   is no ±35 or ±40 rung to trade, and those are the only ones whose gap clears the tick.
   **This is the first thing to check and it is a yes/no gate on the whole idea.**
5. **sigma is unconditional here.** The ladder sets sigma per game. If it widens sigma on
   games where the tail is fat, the gap shrinks. Untested against live quotes.

## VERDICT

**There is a systematic, permanent, mechanistically-explained error in the closing total —
and it is entirely in the skew.** The first moment is white noise (nine null tests above);
the third moment is off by 4-6 standard errors at the far rungs and cannot be arbitraged
away because overtime is structurally one-sided.

It is worth ~1c per paired contract at ±35/±40, which is the same order as the tick, the fee
and the spread. **The next step is not more statistics — it is checking the live ladder for
whether ±35 and ±40 rungs exist and what the book looks like there.** That single check
decides whether this is a trade or a curiosity.


---

# 6. CORRECTION AND CLOSURE (2026-09-13, later the same day)

## 6.1 The median claim, established literally

Handling exact pushes, overall and by season:

| season | n | P(dev>0) | P(push) | **P(>0 \| no push)** | 95% CI | mean dev |
|---|---|---|---|---|---|---|
| ALL | 9,405 | .4993 | .0106 | **.5047** | [.494, .515] | **+0.532** |
| 2017-18 | 1,150 | .4913 | .0130 | .4978 | [.468, .527] | +0.487 |
| 2018-19 | 1,230 | .4951 | .0114 | .5008 | [.472, .529] | +0.730 |
| 2020-21 | 1,080 | .4954 | .0111 | .5009 | [.471, .531] | −0.008 |
| 2021-22 | 1,230 | .5008 | .0163 | .5091 | [.481, .538] | +0.334 |
| 2022-23 | 1,227 | .5020 | .0122 | .5083 | [.480, .537] | +0.966 |
| 2023-24 | 1,162 | .4888 | .0120 | .4948 | [.465, .524] | +0.162 |
| 2024-25 | 1,166 | .5223 | .0086 | .5268 | [.498, .556] | +0.989 |
| 2025-26 | 1,160 | .4983 | **.0000** | .4983 | [.469, .527] | +0.530 |

**Every season's CI contains 0.500 while the mean is positive in seven of eight.** The
defensible statement is the one to use: *the closing total is approximately a median
forecast, the realized scoring distribution is positively skewed, and mean forecast errors
therefore need not translate into directional win-rate edges.*

(Note 2025-26 has **zero pushes** — every closing total that season was a half-point.)

## 6.2 The OT severity test — confirmed in aggregate, one bucket resists

Regulation-only tail ratio `P(dev>K | Reg) / P(dev<−K | Reg)`, against the same ratio
including OT:

| K | including OT | **regulation only** |
|---|---|---|
| 20 | 1.12 | **0.88** |
| 25 | 1.17 | **0.87** |
| 30 | 1.30 | **0.86** |
| 35 | 1.75 | 1.07 |
| 40 | 2.50 | 1.28 |

**Removing overtime does not merely shrink the asymmetry — it inverts it.** In regulation
the LEFT tail is fatter. Frequency × severity is the whole story out to K=30, exactly as
predicted.

By spread bucket, regulation only:

| spread | OT rate | mean dev \| OT | P(>35\|OT) | from OT | from REG | **reg tail ratio** |
|---|---|---|---|---|---|---|
| ≤3 | .0627 | +20.56 | .2297 | .0144 | .0191 | **0.75** |
| 3-5 | .0602 | +24.59 | .2521 | .0152 | .0167 | 1.14 |
| 5-8 | .0474 | +23.66 | .2679 | .0127 | .0174 | 0.91 |
| >8 | .0396 | +23.14 | .2523 | .0100 | .0263 | **1.61** |

Severity is flat (+20.6 to +24.6), so the mechanism is frequency-driven, not
severity-driven — the specific selection story (a big favourite that reaches OT has already
absorbed a huge surprise) is **not** supported: OT games in blowouts are no more extreme
than OT games in pick'ems.

The >8 bucket's 1.61 does survive OT removal (71 over vs 44 under, z=+2.51 on one of 12
cells, Bonferroni 2.86 — does not clear). **And `KALSHI_NBA_TOTALS_FINDINGS.md` §3.7 has
already diagnosed it**: the blowout tail finding *relocates to the mean* — blowout mean
Z=+0.0852 (t=+3.36) = 1.54 pts; re-standardising collapses the tail gap to z=+0.78 with KS
on shapes p=0.43. **It was a level effect misread as dispersion, and mine is the same
effect.**

## 6.3 The skew is real — and my sigma-heterogeneity worry was wrong

I suspected the tail gap might be an artefact of comparing a pooled empirical distribution
to a single normal, when Kalshi fits sigma per game. Checked, using the ladder's own rule
(`sigma = 18.218 + 0.06061·(close − mean close)`):

```
                pooled dev   standardised Z   N(0,1)
skew                 0.231            0.230      0
excess kurtosis      0.401            0.368      0
sd                 18.0592           0.9916      1
```

**The skew survives standardisation almost exactly.** It is a genuine shape property, not
a mixing artefact.

## 6.4 THE GATE FAILS — the rungs do not exist

`KALSHI_NBA_TOTALS_FINDINGS.md`, 12,128 captured rungs:

```
p50 |t| 0.453   p90 0.859   p99 1.097   MAX 1.456   deep (|t| >= 1.5): ZERO
```

My proposed trade, converted to the units the venue actually lists:

| rung | \|t\| | listed? | gap I measured |
|---|---|---|---|
| ±25 | 1.37 | **yes** (beyond p99) | +0.30c, z +0.77 — inside noise |
| ±30 | 1.65 | **no** | +0.59c, z +1.94 |
| ±35 | 1.92 | **no** | +1.05c, z +4.55 |
| ±40 | 2.20 | **no** | +0.98c, z +5.76 |

**Every rung where the mispricing is measurable is a contract Kalshi has never listed, and
the deepest rung that exists is where the gap is inside noise.** The gate is not "thin
book" or "fees eat it" — the instrument does not exist.

And the repo's structural argument is stronger than my statistical one: the smallest sigma
error that could pay round-trip taking cost is Var ≈ 1.29, which registers at **z ≈ +7.9**.
Nothing above z=+2.63 exists in nine seasons. Combined with sd(Z) = 1.0045 across 8
calibration buckets and the inverted results in #5 and #9, **the tail class is closed.**

## 6.5 What survives

1. **The median result** (§6.1) — new, clean, and the correct framing for every mean-based
   finding in this project.
2. **The OT inversion** (§6.2) — regulation is left-tailed and overtime flips it. A real
   decomposition of where the skew comes from.
3. **The skew is a genuine shape property** (§6.3), surviving per-game standardisation.

None of it is a trade on this venue. It would become one only if Kalshi listed past
|t| = 1.5, which is a product decision, not a market inefficiency.

---

# 7. THE LADDER, READ FROM THE LISTING ITSELF (2026-09-13)

§6.4 cited `KALSHI_NBA_TOTALS_FINDINGS.md`'s "max |t| 1.456" from **quoted** rungs. Read
instead from `kalshi_nba_totals.sqlite`'s `markets` table — what Kalshi actually **listed**,
quoted or not — the picture is sharper and two of my statements need correcting.

## 7.1 The product: a fixed 11-strike grid, 3 points apart, ±15 from centre

```
1,324 events, 14,787 listed markets, 2025-10-21 .. 2026-06-13 (a full season incl. playoffs)
strikes per event   mean 11.2   median 11   min 11
strike spacing      3.0 points
half-span (centre -> deepest strike)   median 15.0   p90 15.0   MAX 42.0
1,296 of 1,324 events (97.9%) have EXACTLY half-span 15.0
```

| rung | \|t\| at σ=18.2 | events listing it |
|---|---|---|
| ±15 | 0.82 | **97.9%** |
| ±25 | 1.37 | 1.4% (19 events) |
| ±30 | 1.65 | 0.8% (11) |
| ±35 | 1.92 | **0.2% (3)** |
| ±40 | 2.20 | **0.1% (1)** |

The available `|t|` grid is **0.16, 0.33, 0.49, 0.66, 0.82** and nothing else. You cannot
target a `|t|` even if you wanted to.

## 7.2 CORRECTION — I mis-centred the benchmark, and it flipped the sign

I built the reference normal around the **mean** (+0.532). §6.1 established the ladder
centres on the **median** (0.00). Re-centring:

| K | \|t\| | gap vs mean-centred normal | **gap vs median-centred normal** | listed? |
|---|---|---|---|---|
| 3 | 0.16 | −2.14c (z −2.96) | +0.18c (z +0.25) | yes |
| 6 | 0.33 | −1.67c (z −2.38) | +0.55c (z +0.79) | yes |
| 9 | 0.49 | −1.65c (z −2.47) | +0.43c (z +0.64) | yes |
| 12 | 0.66 | −1.44c (z −2.29) | +0.45c (z +0.71) | yes |
| **15** | **0.82** | −0.70c (z −1.20) | **+0.97c (z +1.67)** | **yes, 97.9%** |
| 18 | 0.99 | +0.08c | +1.51c (z +2.88) | 1.4% |
| 24 | 1.32 | +0.41c | +1.38c (z +3.37) | 1.4% |
| 35 | 1.92 | +1.05c | +1.41c (z +6.10) | 0.2% |
| 40 | 2.20 | +0.98c | +1.18c (z +6.95) | 0.1% |

**The −1.5 to −2.1c I reported near the money was my benchmark being off-centre by 0.53
points, not a shape error in the ladder.** Correctly centred, the gap is positive and
monotone from ±6 outward — and, importantly, **it does not first appear beyond the board.
It is already +0.97c at ±15, the deepest routinely listed rung.**

## 7.3 What that leaves — and it is the maker question, specifically

At ±15 the contracts price near 20c. Kalshi's fee is `0.07 · P · (1−P)` ≈ **1.12c per
contract** at P=0.20, and the paired trade needs two legs. **Fee ≈ 2.24c against a 0.97c
edge — taking is dead by more than 2x**, which is the same verdict
`KALSHI_NBA_TOTALS_FINDINGS.md` reached generically (buy-YES-everything −3.706c/ct).

So the finding does not resurrect a taking trade. What it does is turn that document's §4
("the maker side is untested across every family") from a general gap into **one specific,
pre-specifiable hypothesis**:

> Rest bids on the OVER at the outermost listed rung (+15) and offers on the UNDER at
> (−15), on the ladder's fixed 3-point grid. Theoretical edge +0.97c per paired contract,
> z = +1.67 on one season, monotone in `|t|` and mechanistically grounded in a structurally
> one-sided overtime tail.

**Caveats that must travel with it.** z = +1.67 is not significant. It rests on a single
captured season. The outer rungs are the thinnest part of the book, and
`kalshi-fill-test-result` measured that wide books have the edge and no size. And the whole
thing is contingent on Kalshi continuing to price the ladder with a symmetric model —
overtime makes the skew structural, but the *mispricing* is a product choice that can change
without notice.

That is a preregistration candidate, not a trade. It needs its own frozen spec, forward
collection of outer-rung depth, and a maker-fill assumption that is measured rather than
assumed.
