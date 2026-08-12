# Is this sport a modelling candidate?

An ordered decision procedure for **totals** and **moneylines**. Run the gates
in sequence. Any FAIL stops the sport; do not proceed to the next gate, and do
not model to rescue a gate that failed.

Thresholds are calibrated on markets actually measured (NBA 8 seasons, NCAAB
2023-24), not asserted from theory.

---

## Framing — what question the screen is asking

**Do not ask "what variable predicts outcomes?" Ask "what pricing
transformation is the book simplifying, and where does that simplification
become materially wrong?"**

The first question requires out-predicting a line that already explains 21.3%
of total variance and 39.4% of margin variance, to a tolerance of 0.56% R² on
what it missed. Forty-one feature families have been tested across two projects
against that bar. All null. It is the hard path and there is no evidence anyone
on this project can walk it.

The second question is different in kind. A book does not build a bespoke model
per market — it builds one number and *transforms* it into the rest. Every
transformation is a simplification: a fixed ratio, a constant σ, a lookup
table, a distribution shape assumed from a single point. Simplifications are
right in the middle of their range and wrong at the edges, and **finding the
edge does not require predicting anything.** You compare two prices the book
itself published and check whether the arithmetic between them holds. The book
is the one making the falsifiable claim.

### The transformation catalogue — basketball

| # | transformation | typical simplification | testable with |
|---|---|---|---|
| 1 | power rating → spread | linear, fixed home constant | spread history |
| 2 | **spread → moneyline** | fixed σ normal mapping | spread + ML ✓ *tested* |
| 3 | spread + total → team totals | exact by construction — no error | — |
| 4 | **full game → first half / quarters** | fixed ratio ~0.48–0.52 | 1H lines ✗ |
| 5 | **main line → alternate lines** | one distribution shape, all points | alt lines ✗ |
| 6 | margin σ assumed independent of total | constant σ | spread + total ✓ *tested* |

### Two tested on NCAAB 2023-24 — both hold

**#6 — margin variance vs total.** The premise of a σ error is that higher-total
games have wider margins. They do not: `corr(total, |margin residual|) =
+0.0031, p = 0.83`, and σ across total quintiles runs 12.32 / 10.77 / 11.21 /
10.84 / 11.45 — flat and non-monotone. **The book's constant-σ assumption is
correct, so it isn't a simplification at all.**

**#2 — spread → moneyline.** Mapping the closing spread through `Φ(−spread/σ)`
with σ = 11.06 and comparing to the devigged moneyline, n = 4,924:

| | spread-implied | moneyline |
|---|---|---|
| logloss | 0.57599 | 0.57590 |
| Brier | 0.19628 | 0.19617 |

Disagreement between them has sd of only **2.14pp** — and a half-point of
spread is worth ~1.8pp of win probability at σ = 11, so most of that is the
spread's own quantisation, not a pricing difference. Sorting by disagreement,
the truth sits *between* the two in every bucket and neither dominates.
**The transformation is internally consistent to within the granularity of the
spread itself.**

Both nulls are informative: they say the CBB book is coherent across its
*primary* markets, which is where attention is thickest. That is exactly what
attention asymmetry predicts, and it points the method at rows 4 and 5 of the
catalogue — the derivative markets this file does not contain, where fixed
ratios really are used and nobody is watching.

### Why this belongs in the objective

- It needs **no outcome model**, so it sidesteps the bar that has killed every
  attempt so far.
- A transformation error is **deterministic and repeatable**, not a statistical
  tendency — it recurs every time the formula is applied, so it is far cheaper
  to detect than a bias of the same size. You still need a permutation null to
  price it, but not to see it.
- It generates **pre-registered hypotheses for free.** "The book prices 1H
  total at 0.48× full total; the true ratio in high-pace games is 0.51" is a
  specific, falsifiable claim written before looking — which is what §G4
  demands and what feature hunting can never supply.

---

## The checklist

| # | gate | statistic | pass |
|---|---|---|---|
| 0 | Data | seasons of closing lines | ≥ 5 |
| 1 | Price | obtainable price / hold | see G1 |
| 2 | **Totals decision** | `edge_pp` | > 0 |
| 2′ | **Moneyline decision** | `ROI` | > 0 |
| 3 | Detection | seasons to confirm | ≤ 4 |
| 4 | Conditional bias | permutation null-of-max | > 95th pct |
| 4c | **Conditional separability** | walk-forward bucket spread | > 95th pct |
| 5 | Decay | recent 2 seasons | same sign |
| 6 | **Profitability** | `lifetime_profit` at edge's 95% lower bound | ≥ hurdle |

**Check the G6 floor first.** The minimum viable edge is knowable from
games/season alone, before acquiring any data — it tells you what you are
hunting for, and rules out sports where nothing findable would pay.

---

## G0 — Data

**Acquire for the transformation test, not just the outcome test.** A file with
only main-line closes can answer G2/G2′ and nothing about the framing question
above. Wherever possible also pull **first-half and quarter lines, team totals,
and alternate lines** for the same games — those are rows 4 and 5 of the
catalogue, and they cost nothing extra to screen once held.

**Totals:** `date, closing_total, actual_total`
**Moneyline:** `date, closing_ml_a, closing_ml_b, a_won` — **both sides are
mandatory.** One side cannot be devigged and tells you nothing about fair price.

- Screen the **closing** line, never the opener. The open-to-close move is the
  market correcting itself; predicting it yields CLV and no money.
- **< 5 seasons → PROVISIONAL only.** You can detect at Gate 2 but cannot clear
  Gate 5. Never advance to modelling on a provisional result.

## G1 — Price

Measure the price you can actually get. Never assume −110.

**Totals — break-even:** −110 → 52.38% · −105 → 51.22% · −102 → 50.50%

**Moneyline — hold:** devig both sides (each raw implied probability divided by
their sum); `hold = sum − 1`.

| hold | action |
|---|---|
| ≤ 2.5% | proceed (true dime line) |
| 2.5–4.5% | proceed; required edge roughly doubles |
| > 4.5% | proceed only if calibration bias is large — most sports fail here |

## G2 — Totals decision

Residual `r = actual − closing_total`.

**`edge_pp = best_side% − break_even% > 0` is the only gate.**

Never gate on `b`, `b/σ`, or `b/σ ÷ z_vig`. A binary bet depends on mass near
the line, not the mean; the parametric ratio read 4.23 on NCAAB and 2.28 on NBA
totals, both of which have negative `edge_pp`.

Report as diagnosis, not as gates:

- **central/tail split of `b`** — both totals markets measured put the entire
  bias in the tails (NCAAB central −0.083 of +0.864). Do not build a ratio
  statistic from this; one was tested and failed (no shape-independent
  threshold, exploding denominator, does not separate).
- **`pts needed` vs `central b`** — points of central bias required to beat the
  price. If `central b` is not within ~3× of it, no filter will close the gap.

| market | pp per point | pts to beat −110 |
|---|---|---|
| NCAAB totals | 2.43 | 0.98 |
| NBA totals | 1.72 | 1.39 |

## G2′ — Moneyline decision

Not a residual problem. The decision statistic is **ROI**, not win rate — a 30%
shot at +250 profits and a 70% favourite at −400 does not.

```
ROI = calibration_edge × decimal_odds − vig_drag
      vig_drag = 1 − E[p_fair × decimal_odds]

GATE:  calibration_edge  >  vig_drag / decimal_odds
```

Verified on NCAAB: predicted ROI −2.14% vs actual −2.24%.

**Test one side per game — favourites only.** Stacking both sides makes pooled
calibration identically zero and bucket deviations antisymmetric *by
construction*. Both are artifacts, not findings.

**Drop |price| > 2000** before devigging; proportional devig under-corrects at
long prices, and those games carry no liquidity anyway.

## G3 — Detection

```
totals    n_req = 7.84 / (b/σ)²
moneyline n_req = 7.84 × var(profit) / ROI²
```

Divide by games/season. **> 4 seasons → reject**; decay will beat you.

Moneyline detection is **price-dependent** — profit variance scales with
decimal odds², so `n_req` scales with `d²`. Longshot cells are often
unconfirmable at any realistic sample. **Screen favourites first**, not because
the edge is bigger but because it is confirmable.

Volume and bias size multiply: `n_req` contains no volume term (volume converts
it to calendar time, linearly) while a larger bias cuts it quadratically. The
best cells are high-volume sports' *thin* markets.

## G4 — Conditional filters

- Pre-register the filter list **before** looking at output.
- Every cut needs a **permutation null of the maximum** across cells examined,
  not per-cell p-values.
- Benjamini-Hochberg across the whole screen.
- Filters must fire on **5–10%** of games.
- Persistence pre-filter: if an effect cannot predict itself period-over-period,
  it cannot predict anything. One line of code; kills ideas faster than
  modelling.

## G4c — Conditional separability

**Unconditional bias and conditional separability are two different ways
through the gate. Either one qualifies a sport.** G2/G2′ only see the first: a
market can price correctly on average and still misprice systematically in the
cross-section.

Fit a small, economically motivated, **walk-forward** model (5–15 variables,
one specification, no feature selection). Compute `ê = P̂(win) − P_BE`, sort
games by it, and read realised win rate by bucket.

| separable | nothing there |
|---|---|
| Q1 46% → Q5 56% | Q1 49.7% → Q5 50.3% |

**Passing requires all three:**

1. spread (top − bottom) above the **95th percentile** of a permutation null
   that shuffles outcomes **within season × price strata** — a naive shuffle
   breaks the price structure and inflates apparent separability
2. the top bucket clears break-even at an obtainable price
3. the top bucket's edge clears the **G6 floor**

### ⚠ Walk-forward is not optional

The prior project produced the attractive table in development — win rate rose
monotonically 50.0% → 55.4% with model confidence — and in holdout it **peaked
early and reversed**, 54.4% → 50.1%. Direction generalised; ranking did not.
An in-sample bucket table is worthless. Reproduced on NCAAB:

| bucket | in-sample | walk-forward |
|---|---|---|
| Q1 | 46.37% | 48.10% |
| Q2 | 51.00% | 51.05% |
| Q3 | 50.63% | 52.11% |
| Q4 | 52.37% | 51.05% |
| Q5 | **53.94%** | **51.05%** |
| spread | **+7.57pp** | **+2.95pp** |

In-sample looks like the separable column above. Walk-forward peaks at Q3 and
flattens — 87.1st percentile of its own stratified null, and the top bucket
(51.05%) is *below* the 52.38% break-even. **The gap between those two columns
is the finding.**

### ⚠ Moneylines need a different statistic

On a fixed-price market the raw realised rate is right. On a moneyline it is
not: sorting by `ê` is confounded with price level, because large predicted
edges sit on longshots. On NCAAB this put fair-34% road favourites in the top
bucket and produced a raw spread of **−34.83pp** that measures nothing but the
sort. **Use the calibration deviation `realised − fair`**, which is
price-neutral, and rank buckets on **ROI**.

## G5 — Decay

Plot by season. **Reject if the recent two seasons are flat**, regardless of
pooled significance. A real edge in the prior project ran six seasons then
vanished; pooled over ten it still looks robust.

## G6 — Profitability

Capacity is not "is the limit big enough" — that is unfalsifiable. It is a
dollar figure, and the gate is whether that figure clears your hurdle.

```
usable_seasons  = max(0, edge_life − seasons_to_confirm)
ROI_per_bet     = 1.909 × edge_pp/100                    (at −110)
bets_per_season = games_per_season × filter_fire_rate
lifetime_profit = ROI_per_bet × limit × bets_per_season × usable_seasons
```

**GATE: `lifetime_profit ≥ hurdle`, computed at the LOWER 95% bound of
`edge_pp`, never at the point estimate.** An edge inside its own confidence
interval is a coin flip you are paying vig on.

### The floor: minimum viable edge

`usable_seasons` goes to zero when confirmation takes longer than the edge
lives. That makes a **hard floor on edge size, below which no limit can rescue
the market** — the money never arrives because you are still confirming when
the edge dies. Assuming a 6-season edge life (the one real edge observed in the
prior project):

| sport | games/season | **min viable edge** | implied win rate |
|---|---|---|---|
| College basketball | 5,500 | **0.77pp** | 53.15% |
| MLB | 2,430 | 1.16pp | 53.54% |
| Soccer (top-5) | 1,752 | 1.36pp | 53.74% |
| NHL | 1,312 | 1.57pp | 53.95% |
| NBA | 1,230 | 1.62pp | 54.00% |
| College football | 800 | 2.01pp | 54.39% |
| NFL | 272 | **3.44pp** | 55.82% |

Sensitivity to the assumed edge life:

| sport | life 3 | life 6 | life 10 |
|---|---|---|---|
| College basketball | 1.09 | 0.77 | 0.60 |
| NBA | 2.29 | 1.62 | 1.26 |
| NFL | 4.85 | 3.44 | 2.67 |

**This is the single most useful number in the framework.** It says what you
are hunting for before you start, and it is knowable from games/season alone —
no data required. Anything smaller is not worth finding.

### Required limit

Given an edge at the floor and a filter firing on 10% of games, the limit
needed to clear a $100k/season hurdle:

| sport | bets/season | limit needed |
|---|---|---|
| College basketball | 550 | **$12,400** |
| MLB | 243 | $18,700 |
| NBA | 123 | $26,200 |
| NFL | 27 | **$56,000** |

Low-volume sports are punished twice: they need a bigger edge *and* a bigger
limit per bet to reach the same money. This is the structural tension made
numeric — the markets whose limits are that deep are the ones everyone has
already modelled.

### Applied to NCAAB

The best cell measured was **+0.36pp** (totals at −102). The floor is
**0.77pp**. Confirming a 0.36pp edge needs ~151,000 games — **27.5 seasons**.

**Unusable even if real, at any limit.** That is a stronger rejection than
"not significant": it says the cell could be genuine and still never pay.

---

## Stopping rules

1. Nothing clears G2 or G2′ at an obtainable price → **report and stop.** A
   clean null is the majority of the value.
2. Edge below the G6 floor → **stop, regardless of significance.** It cannot be
   confirmed before it dies, so it never pays at any limit.
3. Clears the floor but `lifetime_profit` < hurdle at the 95% lower bound →
   record the numbers and move on. This is a capital decision, not a
   statistical one.
4. **Never model to rescue a rejected gate.**

---

## Worked verdict — NCAAB 2023-24 (n = 5,588 games with lines)

| gate | result |
|---|---|
| G0 | **FAIL** — one season; provisional only |
| G1 totals | −110 median, IQR (−114, −108) |
| G1 moneyline | **FAIL** — hold **4.65%**, no better than −110 |
| G2 totals | **FAIL** — −1.52pp at −110; +0.36pp at −102 (t = 0.54) |
| G2′ moneyline | **FAIL** — ROI **−2.24%**, CI (−4.11, −0.37) |
| G4 | **FAIL** — 4 cuts, 0 survive permutation; BH 0 rejections |

**Not a modelling candidate.**

The instructive part is *how* it fails. Both markets are **significantly
biased**:

| market | bias | significance | verdict |
|---|---|---|---|
| totals | +0.864 pts on σ 16.44 | **t = 3.93** | best side 50.86% vs 52.38% → no edge |
| moneyline favourites | +1.60pp vs devigged price | **t = 2.45** | ROI −2.24% → no edge |

The moneyline case is the cleanest statement of the whole framework. NCAAB
favourites genuinely beat their fair price — real favourite-longshot bias,
significant at t = 2.45. The gate required **3.09pp**; the market delivered
**1.60pp**. Right sign, **1.93× too small**. Underdogs return −10.65%.

**Across three markets measured: three significant biases, zero edges.** Treat
a significant `t` as the beginning of the question, not the answer. The screen
never asks "is there bias" — it asks "is the bias bigger than the price."

## Anchors — what null looks like

| quantity | value |
|---|---|
| NBA totals | +0.515, t = 2.74 → 50.38% → no edge |
| NBA sides | −0.167, t = −1.19 → no bias at all |
| NCAAB totals | +0.864, t = 3.93 → 50.86% → no edge |
| NCAAB sides | +0.038, t = 0.25 → flattest cell measured |
| NCAAB ML favourites | +1.60pp, t = 2.45 → ROI −2.24% |
| price NCAAB totals needs | −103.5 (CI +101.8 to −109.1) |
| value of −110 → −105 | +1.16pp — more than 21 feature families combined |
