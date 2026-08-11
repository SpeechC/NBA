# Is this sport a modelling candidate?

An ordered decision procedure for **totals** and **moneylines**. Run the gates
in sequence. Any FAIL stops the sport; do not proceed to the next gate, and do
not model to rescue a gate that failed.

Thresholds are calibrated on markets actually measured (NBA 8 seasons, NCAAB
2023-24), not asserted from theory.

---

## The checklist

| # | gate | statistic | pass |
|---|---|---|---|
| 0 | Data | seasons of closing lines | ≥ 5 |
| 1 | Price | obtainable price / hold | see G1 |
| 2 | **Totals decision** | `edge_pp` | > 0 |
| 2′ | **Moneyline decision** | `ROI` | > 0 |
| 3 | Detection | seasons to confirm | ≤ 4 |
| 4 | Conditional | permutation null-of-max | > 95th pct |
| 5 | Decay | recent 2 seasons | same sign |
| 6 | Capacity | limit at that price | fundable |

---

## G0 — Data

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

## G5 — Decay

Plot by season. **Reject if the recent two seasons are flat**, regardless of
pooled significance. A real edge in the prior project ran six seasons then
vanished; pooled over ten it still looks robust.

## G6 — Capacity

Record the **limit** alongside the edge. Rank on `edge × limit`, never `edge`.
Bias and liquidity run opposite, so an unranked table puts the unfundable
markets on top.

---

## Stopping rules

1. Nothing clears G2 or G2′ at an obtainable price → **report and stop.** A
   clean null is the majority of the value.
2. Clears but needs > 4 seasons → deprioritise.
3. Clears but limits are trivial → record and move on.
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
