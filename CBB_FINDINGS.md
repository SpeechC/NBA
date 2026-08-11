# CBB Stage 1 screen — findings

Data: `C:\NBA\Data\2023-2024_CBB_Box_Score_Team-Stats.xlsx` (BigDataBall,
NCAAB 2023-24). 6,123 regular-season games, **5,588 with closing lines**,
2023-11-06 → 2024-03-17. Code: `cbb_load.py`, `screen_cbb.py`.

**One season only.** Stage 3 (decay) cannot be run. Nothing below may advance
past Stage 1 until more seasons exist.

---

## 1. Headline result

**The prior was right about the bias and wrong about the edge.**

College basketball totals are roughly **twice as biased as the NBA in sd
units** — `b/σ` = 0.0525 vs 0.0283 — and the bias is unambiguous, `t = 3.93`.
The closing total is too low by **+0.86 points on average**.

It still does not clear the vig.

| market | n | b | σ | b/σ | t | best side | @ −110 | @ −105 | @ −102 |
|---|---|---|---|---|---|---|---|---|---|
| **totals (close)** | 5,588 | **+0.864** | 16.44 | 0.0525 | **3.93** | over 50.86% | −1.52pp | −0.36pp | **+0.36pp** |
| **sides (close)** | 5,588 | +0.038 | 11.18 | 0.0034 | 0.25 | home 50.29% | −2.09pp | −0.93pp | −0.21pp |
| totals (OPEN) | 5,273 | +0.829 | 16.52 | 0.0502 | 3.65 | over 51.05% | −1.33pp | — | — |

The single positive cell — totals at −102 — has `edge t = 0.54`. Its 95% CI on
the win rate is **49.55% – 52.17%**, which straddles every break-even in the
table. It is not evidence of an edge.

### The price CBB totals actually requires

Betting the over at the point estimate breaks even at **−103.5**. The 95%
interval on that requirement runs from **+101.8 to −109.1** — i.e. the data
cannot distinguish "needs a plus price" from "profitable at −109."

For contrast the NBA over needs −101.5. CBB is *better*, and still not
obtainable: −103.5 is inside exchange territory, not retail. Median observed
closing price in this file is **−110** for both markets.

---

## 2. Nulls recorded

- **Sides are dead.** `b = +0.038` on σ 11.18, `t = 0.25`. Home teams cover
  50.29%. Detection time **111 seasons**. This is the flattest cell measured in
  either project — flatter than NBA sides (`t = −1.19`). Do not revisit.
- **The opener is not more beatable than the close, materially.** Over rate
  51.05% (open) vs 50.86% (close). Both lose at −110. Screening the opener
  would have produced the same rejection, one decimal place apart.
- **November does not survive its own null.** See §3.

## 3. Early-season cell — tested and rejected

`SPORT_SCREENING_BRIEF.md` §3 names early-season games as an attention-asymmetry
candidate, so this was tested rather than searched for. The by-month table is
suggestive: totals bias falls monotonically Nov → Feb (+1.52 → +0.56) and home
cover% falls 51.77% → 47.01%.

| month | n | totals bias | over % | side bias | home cover % |
|---|---|---|---|---|---|
| 2023-11 | 1,128 | +1.515 | 51.86 | +0.658 | 51.77 |
| 2023-12 | 993 | +0.716 | 50.76 | +0.605 | 52.97 |
| 2024-01 | 1,386 | +0.703 | 51.66 | −0.037 | 50.14 |
| 2024-02 | 1,396 | +0.555 | 50.00 | −0.352 | 48.93 |
| 2024-03 | 685 | +0.961 | 49.49 | −0.858 | 47.01 |

November over rate 51.86%, 95% CI (48.95, 54.78). Edge at −102 is +1.36pp,
`t = 0.92`.

**Permutation result — this is the section that kills it.** Against 2,000
random subsets of the same size, November's over rate sits at the **76.6th
percentile** of its own null. Against the null of the *maximum* across five
months, the best observed month sits at the **15.4th percentile** — the best
month here is *less* extreme than a random best month. This is the
`FINDINGS_LATE.md` tree-leaf failure reproduced in miniature, and it cost
about ninety seconds to establish.

---

## 3b. Where the +0.864 actually lives

The bias is a **tail asymmetry, not a level shift**. Splitting the mean by
where the points come from:

| residual bucket | share of games | contribution to +0.864 |
|---|---|---|
| beyond ±20 | 20.8% | **+0.910** |
| within ±20 | 79.2% | **−0.047** |

Four-fifths of games contribute nothing. The whole effect is that **11.5% of
games finish 20+ over** while only **9.3% finish 20+ under**. Mean +0.864,
median +0.500, 20%-trimmed mean +0.405, skew +0.288 — about half the mean is
manufactured by the right tail.

Totals carry a half-point hook throughout, so residuals are half-integers and
there are **no pushes**; the line moves in clean 1-point steps:

| line shift | over rate | gain |
|---|---|---|
| baseline | 50.86% | — |
| +1.0 pt | 53.10% | +2.24pp |
| +2.0 pt | 55.44% | +2.33pp |

**2.43 pp of win rate per point** (symmetric estimate; 2.24 one-sided; normal
approximation `φ(0)/σ` = 2.43). So beating −110 from a coin flip needs
**~0.98 points of central bias**, −105 needs **0.50**. CBB's central 80%
delivers **−0.083**. It has none of what it needs.

Normal theory applied to +0.864/16.44 predicts a **52.09%** over rate; the
actual is **50.86%**. That 1.24pp gap is the fat-tail artifact, measured.

⚠ A `C = tail/total` statistic was built from this and **rejected as a gate** —
it has no shape-independent threshold, its denominator explodes at low bias,
and it fails to separate a genuine central shift from pure tail loading. See
the warning in `SPORT_SCREENING_BRIEF.md` §2. `edge_pp` remains the only gate.

## 4. Verdict against the stopping rules

Brief §9, rule 1: *no cell clears `edge_pp > 0` at an obtainable price.* The one
cell that clears does so only at −102, is not statistically distinguishable
from zero, and has no limit information attached.

**Report and stop.** Do not model CBB totals on this data.

**CBB is not a market-selection candidate on one season.** The allegiance
prior — the reason it was proposed — is rejected on sides and unconfirmed on
totals. The single open thread is the brand-tier gradient in totals (§4a),
which is an *acquisition* decision (more seasons), not a modelling one.

## 4a. The allegiance hypothesis — tested and rejected

CBB was proposed because college allegiances should bias the line: public money
concentrates on brand-name programs, the book shades toward the popular side,
and the unpopular side is left with value. This is invisible to the
unconditional screen — pooled over a season the popular side is home about as
often as away and the effect cancels, which is consistent with the flat 50.29%
unconditional home cover rate.

Tested directly in `cbb_allegiance.py`, pre-registered: tiers fixed by
conference (POWER6 = ACC/B1G/B12/SEC/BE/Pac-12; MID = A-10, AAC, MWC, WCC, MVC,
CAA, Sun Belt, C-USA, MAC; LOW = the rest), cells declared before running.

**H1: the higher-tier side covers less than 50%. To fade it profitably at −110
its cover rate must be below 47.62%.**

| cell | n | higher-tier cover % | ±95% | z | p |
|---|---|---|---|---|---|
| POWER6 vs LOW | 394 | **52.03** | 4.93 | 0.81 | 0.42 |
| POWER6 vs MID | 203 | **52.22** | 6.87 | 0.63 | 0.53 |
| MID vs LOW | 582 | **50.00** | 4.06 | 0.00 | 1.00 |
| pooled | 1,179 | **51.06** | 2.85 | — | — |

**Rejected, and in the opposite direction to the prediction.** The popular side
covers *more* than half, not less. Benjamini-Hochberg: **0 of 3** rejections.
Permutation on the max |cover − 50%| across cells: observed at the **19th
percentile** of its own null — less spread than chance produces. Even the
favourable end of the pooled CI (48.21%) does not reach the 47.62% needed to
fade, and the unfavourable end (53.91%) does not reach the 52.38% needed to
back. **There is no allegiance effect on the spread in this season.**

### But it may be in the totals instead

The same cut on totals is not flat, and the pattern has a coherent mechanism —
the public bets *overs* in games it watches, not sides:

| cell | n | over % | edge @ −110 |
|---|---|---|---|
| POWER6 vs MID | 203 | 56.16 | +3.78 |
| POWER6 vs POWER6 | 1,005 | **53.73** | **+1.35** |
| MID vs LOW | 582 | 52.23 | −0.15 |
| POWER6 vs LOW | 394 | 50.76 | −1.62 |
| LOW vs LOW | 2,081 | 49.78 | −2.60 |
| MID vs MID | 1,321 | 48.98 | −3.40 |

Marquee games go over; obscure games go under. But it does **not** survive
correction: **0 of 6** BH rejections, and the max sits at the **88.7th
percentile** of its permutation null. A single-df trend test on combined brand
tier gives slope +0.88pp per step, one-sided permutation p ≈ 0.03 — the only
statistic in this project to approach significance — but the ordering is
**not monotone** (brand = 2 reads 49.39%, below brand = 0) because that bucket
mixes marquee mismatches with mid-tier pairings, and the trend variable was
built *after* seeing the cell table. It is post-hoc and does not clear.

Even taken at face value, POWER6 vs POWER6 totals at 53.73% has a 95% CI of
(50.65, 56.81) — the lower bound is below the 52.38% break-even.

**This is the one result in the CBB screen worth re-testing on more seasons.**
It is the only structure in the data that is not flat, it has a plausible
mechanism, and its direction is consistent across all six cells. It is not
established, and must not be modelled on this evidence.

## 4b. Bounding what a model would need

Stage 1 tested the *unconditional* close. Modelling candidacy is a different
question — whether the residual is predictable **conditionally** — and the
screen does not answer it. Tested separately in `cbb_model_test.py`.

### The bar

```
win rate ≈ 0.5 + 0.3183 × ρ ,  ρ = corr(prediction, residual)
```

| price | ρ needed | **R² needed on the residual** |
|---|---|---|
| −110 | 0.0748 | **0.559%** |
| −105 | 0.0383 | 0.147% |
| −102 | 0.0157 | 0.025% |

Note the scale carefully. The CBB closing line already explains **21.3%** of
total variance and **39.4%** of margin variance. The prior project's "best
model R² ~7.6% on game totals" was never in contention — that is far *worse*
than the line. The target is 0.56% of what the line **missed**.

### The test (pre-registered before running; no variants tried)

20 pre-game features — rolling OEFF/DEFF/PACE per side with 5-game burn-in and
`shift(1)` to exclude the current game, their sums and differences, rest days,
games played, the closing line, |closing spread| — Ridge(α=1), first 60% of
games by date as train, last 40% as test, no shuffling. 4,754 games survive
burn-in; 2,852 train / 1,902 test.

| | totals | sides |
|---|---|---|
| OOS R² on residual | **−0.054%** | **−0.152%** |
| OOS ρ(pred, resid) | +0.0219 | +0.0155 |
| bar for −110 | 0.0748 | 0.0748 |
| OOS win rate | 50.68% ±2.25 | 50.84% ±2.25 |
| vs −110 | −1.70pp | −1.54pp |
| permutation percentile | 83.0 | 77.2 |

**Both OOS R² are negative** — the model is worse than predicting the mean.
Neither permutation percentile reaches 95. Strongest single-feature raw
correlation with the residual was 0.049 (`deff_sum`), against a 0.0748 bar for
a full multivariate model.

### Is this powered, or merely inconclusive?

This matters more than the point estimates. On 1,902 OOS games, se(ρ) ≈ 0.0229:

| price | bar ρ | detectable at |
|---|---|---|
| −110 | 0.0748 | **3.3σ — yes, powered** |
| −105 | 0.0383 | 1.7σ — underpowered |
| −102 | 0.0157 | 0.7σ — no |

Observed ρ was 0.96σ (totals) and 0.68σ (sides).

**So this is a genuine negative at −110, not an underpowered one.** An edge
large enough to beat −110 would have shown at better than 3σ and did not. At
−105 and below the test cannot resolve it — detecting the −105 bar needs 5,344
OOS games, more than the whole season provides.

### Verdict

**No at −110. Unresolved at −105 and below.**

Caveat on scope: this establishes that *simple pre-game team form* carries no
exploitable signal, and quantifies how much would be needed. It does not prove
no model can. But the prior on that is poor — 21 feature families were tested
and found null on the NBA, and the strongest raw correlation available here is
under two-thirds of the required multivariate bar.

## 5. What would change the answer

1. **More seasons.** 5,588 games is enough to *detect* a break-even-size bias
   (2,198 required) but one season permits no decay check, which is the test
   that killed the prior project's only real edge. Three to five seasons of the
   same BigDataBall CBB file is the cheapest next acquisition.
2. **Real two-sided prices with limits.** The `CLOSING ODDS` column quotes one
   side only (over *or* under; one team's spread, not both), so the price the
   losing side traded at is unknown and no limit is recorded anywhere. Ranking
   on `edge_pp × limit` is currently impossible.
3. **The markets not in this file.** Everything above is full-game totals and
   sides on D-I. The brief's attention-asymmetry logic points at first halves,
   team totals, and low-major conferences — none of which this dataset contains.
   That is where the screen should go next, not into a model of this cell.

---

## 6. Method notes / gotchas for whoever picks this up

- The workbook is **two rows per game**, Home and Road, and the `CLOSING ODDS`
  cell holds **one market per row** — but *not* Home=spread / Road=total. The
  split is 4,584/1,520 on home rows and 1,701/4,082 on road rows. Assign by
  parsing the cell prefix (`o`/`u` = total, `+`/`-` = spread), never by venue.
  5,586 of 6,123 games carry exactly one quote of each type.
- 509 games have a missing road-team conference: non-D-I guarantee opponents.
  They are real bettable games and were kept.
- `screen()` bets whichever side won more often, so do **not** pass the parsed
  one-sided price into it — it will frequently price the side that wasn't
  quoted. Screen at fixed prices; use the parsed prices only to establish the
  market's price level (median −110, IQR −114 to −108 on totals).
