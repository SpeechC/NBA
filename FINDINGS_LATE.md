# Late-session findings not covered by the other documents

Everything here was established after the holdout result. Recorded so the repo,
not conversation memory, is the record.

---

## 1. Estimator choice: ridge beats everything (and it validated out of sample)

Nine model families on the totals-movement task:

| model | corr | CLV | beat close |
|---|---|---|---|
| **Ridge (linear)** | **0.294** | **0.746** | **55.4%** |
| RandomForest | 0.249 | 0.673 | — |
| CatBoost | 0.252 | 0.637 | — |
| XGB shallow/regularised | 0.247 | 0.625 | — |
| XGB fixed (used in all earlier work) | 0.236 | 0.605 | 53.3% |
| XGB deep/slow | 0.214 | 0.541 | — |
| LightGBM | 0.212 | 0.500 | — |
| MLP (2 hidden layers) | did not converge in 4.6h; ridge fits in 1.0s |

**The ordering is by regularisation strength, not flexibility.** Every step toward
more capacity made it worse. Re-running the comparison on games before 2023-04-10
only, ridge still wins in the same order — so the choice was not hindsight.

## 2. The CLV → win-rate conversion (the most useful constant in the project)

Measured across thresholds: **each +1.0 point of CLV buys +3.83pp of game win rate.**

| threshold | LINE direction % | mean \|move\| | CLV | GAME win % | ROI −110 | ROI −105 |
|---|---|---|---|---|---|---|
| all | 59.66 | 2.53 | 0.75 | 51.12 | −2.42 | −0.20 |
| 1.00 | 67.96 | 2.79 | 1.47 | 53.02 | +1.22 | +3.51 |
| 1.25 | 70.61 | 2.98 | 1.79 | 53.54 | +2.21 | +4.52 |
| 1.50 | 72.54 | 3.10 | 2.04 | 54.64 | +4.32 | +6.68 |
| 2.00 | 80.15 | 3.57 | 2.82 | 58.99 | +12.62 | +15.18 |

Break-even requires **CLV 1.30 at −110**, **0.99 at −105**, **0.81 on an exchange**.

⚠ **Calling line direction 60% of the time is worth a 51.1% win rate — a loss.**
Direction accuracy on the LINE is not the win rate on the GAME. Break-even needs
roughly **76% direction accuracy at −110**, ~70% at −105.

Selectivity works through two channels: it raises direction accuracy (59.7→70.6%)
AND the mean move on selected games (2.53→2.98).

## 3. Proportional staking — the one improvement that survived screening

Dev-only screen, identical spec-A predictions, only the money allocation changes:

| staking rule | units | ROI % | **season-ROI sd** | profit (u) |
|---|---|---|---|---|
| flat above 1.25 (frozen rule) | 820 | 2.21 | **42.4** | 18.1 |
| flat above 1.00 | 1,275 | 1.22 | 17.8 | 15.5 |
| **linear: max(\|pred\|−0.75, 0)** | 995 | **3.51** | **7.7** | 34.9 |
| linear capped at 2u | 990 | 3.23 | 7.3 | 32.0 |
| quadratic capped at 3u | 1,377 | 3.25 | 7.8 | 44.8 |

All three proportional variants land together (3.2–3.5%, sd ~7.5), which is what a
real effect looks like. The **stability gain matters more than the ROI**: season
swings fall ~80%, and it was season variance that made the flat rule untradeable.

**But it does not create an edge.** On the holdout the same rule gives −1.26%.

## 4. Dollar economics, $100 base bet, quadratic capped staking

| set | seasons | risked/season | profit @−110 | profit @−105 | ROI |
|---|---|---|---|---|---|
| dev (in-sample) | 5 | $27,547 | **+$896** | +$1,541 | +3.25% |
| **HOLDOUT (unseen)** | 2 | $37,348 | **−$471** | **+$366** | −1.26% |

Per-season holdout: 2024-25 **−$2,923**, 2025-26 **+$1,982**.
Mechanics: ~967 bets/season, median stake $17, mean $31, max $300.

**~$37k of risk cycled annually for a result between −$500 and +$900.**

## 5. What "one more feature" would have to deliver

| target | gap | CLV increase required |
|---|---|---|
| break-even at −110 | +0.80pp | **+12%** |
| a real business (3% ROI) | +2.37pp | **+36%** |
| break-even at −105 | −0.36pp | **already there** |

Best CLV gain from any of eighteen feature families: **+2.6%** (ensemble). The
next feature would need to be ~5x better than the best one found.

**The price lever (−110 → −105) is worth 1.16pp — larger than the entire 0.80pp
gap it needs to close.**

## 6. Unresolved: the conversion discrepancy

CLV of 1.740 implies an expected win rate of **56.7%**. The holdout delivered
**51.58%** — **2.1 standard errors below**. Two readings, not distinguishable on
442 bets:

1. the model is already well past break-even and the holdout drew badly (~1 in 25); or
2. the CLV→win conversion is weaker than the linear fit implies, perhaps because
   our CLV concentrates in games where the move overshoots.

This 5-point discrepancy is larger than anything a new feature would address, and
is the better research target.

## 7. Additional null results (families 15–18)

| tested | result |
|---|---|
| **Team identity** (60 dummies; proxy for embeddings) | corr 0.2946→0.2994, CLV **worse** (1.78→1.41). Team effects sd 0.082 vs pace coefficients ~0.74. Kills the embedding case. |
| **pbp possession context** (STARTTYPE, shot mix, 22 features) | corr 0.2946→0.2670 raw. PCA(5/10/20) recovers but never beats baseline, and declines monotonically with components — compression repairing harm, not extracting signal. Also costs 15% of sample. |
| **Season phase** (game number, phase×pace) | corr 0.2946→0.2931. Null. |
| **Move-class segmentation** | No class predicts move magnitude (max quintile spread 14% of mean). Two-stage magnitude×direction fails badly (CLV 0.68 vs 1.80). **Magnitude corr −0.036; direction accuracy 59.9%** — all signal is in the sign, none in the spread. |

## 8. Deep learning: not recommended

The ordering in §1 runs against flexibility; the MLP failed to converge; team
embeddings are ruled out by §7; n=7,335 with ~20 features and ~8% R² is the wrong
regime. The binding constraint is the information set, not the function class.

## 9. Betting-splits data — sources and the timing problem

BetLabs (built for historical splits backtesting), Action Network, VSiN
(DraftKings splits), Sports Insights. Verify before buying: whose book's flow,
bet% AND money%, timestamps, and a join key.

⚠ **The timing problem:** splits exist only after money arrives, and 83.8% of the
open-to-close move has happened by the first repricing. Splits therefore cannot
improve the bet-the-opener strategy much — they support a *different* strategy
(react to flow rather than anticipate it) with a later entry point.

**Cheaper substitute to price first: multi-book line divergence** (e.g. The Odds
API, multi-book snapshots from ~mid-2020). Available at the moment you would bet,
and directly measures where consensus is heading.

---

## 10. Spec re-check on the 2017-start panel — A and D survive

The panel changed materially (7,335 → 8,696 games) and `dis_open` became noisier
when its burn-in was cut, so the spec ranking was re-run rather than assumed.
**Development only** — choosing a spec is selection.

| spec | k | corr | bets | CLV | CLV lo | win% | ROI −110 |
|---|---|---|---|---|---|---|---|
| C (symmetric+pace, 41) | 41 | 0.2632 | 424 | **2.153** | 1.811 | 56.13 | +7.16 |
| **A (frozen, 21)** | 21 | 0.2635 | 453 | 2.000 | 1.676 | 55.41 | +5.78 |
| B (symmetric, 34) | 34 | 0.2610 | 501 | 1.987 | 1.673 | 55.09 | +5.17 |
| **D (frozen, 15)** | 15 | **0.2687** | 456 | 1.976 | 1.667 | 54.17 | +3.41 |
| D_nodis (14) | 14 | 0.2646 | 494 | 1.951 | 1.652 | 52.02 | −0.68 |
| A_nodis (20) | 20 | 0.2612 | 445 | 1.818 | 1.501 | 54.38 | +3.82 |
| market only (2) | 2 | 0.2121 | 35 | 3.757 | 2.257 | 57.14 | +9.09 |
| open_total only (1) | 1 | 0.0108 | 0 | — | — | — | — |

**The top six are statistically indistinguishable** — every CLV interval overlaps
every other. C leads on CLV point estimate, D on correlation, A sits between.
Switching to C on a 0.15 CLV gap with overlapping CIs would be exactly the
noise-chasing pre-registration exists to prevent. **A and D stand**, and they are
the specs with holdout results.

### `open_total` alone predicts nothing

Correlation **0.0108**, zero bets clearing the threshold. The line does not
predict its own movement; all signal comes from the team-form features. This is
a useful sanity check on where the edge originates.

### `dis_open` is nearly free to remove from D

| | CLV | corr | win% |
|---|---|---|---|
| D | 1.976 | 0.2687 | 54.17 |
| D without `dis_open` | 1.951 | 0.2646 | **52.02** |

CLV cost is 0.025 — noise. But `dis_open` is the **most expensive feature in the
pipeline**: it requires an XGBoost score model plus a calibration stage, and its
burn-in is the only reason the panel cannot start at the 2017-10-25 feature
floor. Removing it would delete the most fragile component and recover ~250 games.

⚠ It costs 2.1pp of realised win rate, which is the metric already failing (§6).
Worth investigating, not worth acting on yet — and any such change is a new spec
requiring its own pre-registration, not an edit to D.

---

## 11. Dollar P&L per bet, and the confidence inversion it exposed

`staking.py` + `run_staking.py` write `staking_bets_{A,D}.csv` — one row per game
with `stake_units`, `stake_$`, `won`, `push`, `$won`.

⚠ **The staking formula was reconstructed, not recovered.** It was computed
in-session originally and only its summary statistics were ever written down; no
committed file held it. `min(pred², 3) × $100` matches the recorded $300 cap
exactly but **not** the recorded mean ($52.89 observed vs $31) or median ($22.53
vs $17) stake. The original panel and code are gone, so this cannot be
reconciled. Read these as "this rule on this panel."

### Spec A, $100 unit, priced at −110

| set | bets | risked $ | **$won** | ROI % | win % |
|---|---|---|---|---|---|
| DEVELOPMENT | 5,976 | 273,698 | **+314.82** | 0.12 | 50.03 |
| HOLDOUT 2024-25 | 1,106 | 79,069 | −1,154.67 | −1.46 | 52.80 |
| HOLDOUT 2025-26 | 1,101 | 78,302 | +3,246.73 | +4.15 | 52.97 |
| **HOLDOUT pooled** | 2,207 | 157,370 | **+2,092.07** | +1.33 | 52.89 |

Spec D holdout pooled: **−$148.96** (−0.10%). At −105: A dev +$6,528, holdout
+$5,708; D dev +$5,365, holdout +$3,288.

### Prediction magnitude is not stationary

Mean |pred| by season: 0.274, 0.364, 0.571, 0.611, 0.593, 0.655, 0.704, 0.709.
It climbs monotonically with training-set size, so **the frozen 1.25 threshold is
not a fixed operating point** — it selects 0.3% of games in 2017-18 and 15–16% in
the holdout. Dollar totals are dominated by later seasons for the same reason.

### The confidence ranking inverts out of sample

| thr | DEV n | DEV win% | HOLDOUT n | HOLDOUT win% |
|---|---|---|---|---|
| 0.00 | 5,946 | 50.03 | 2,199 | 52.89 |
| 0.50 | 2,647 | 51.11 | 1,254 | 52.79 |
| 0.75 | 1,581 | 52.12 | 871 | **54.42** |
| 1.00 | 885 | 53.56 | 569 | 53.95 |
| **1.25** | 453 | **55.41** | 345 | **50.14** |
| 1.50 | 193 | 52.85 | 197 | 50.25 |

In development, win rate rises monotonically with confidence — as designed. In
the holdout it **peaks near 0.75 and reverses**, and the frozen threshold sits
past the turn. Spec D shows the same shape (peak 53.45% at 0.75, 49.25% at 1.25).

**This is the best explanation yet for §6.** The model's DIRECTION calls keep
working out of sample — CLV holds at +1.877 — but its CONFIDENCE RANKING does
not. CLV is earned on the sign; the win rate needs the ranking. That is precisely
the pattern of a passing CLV alongside a failing win rate.

It also reframes §11's holdout profit: the quadratic rule makes money **from the
low-confidence games the threshold excludes**, not from the model's best picks.
Not a vindication — the same inversion seen from the money side.

⚠ **0.75 looking better is an observation on holdout data, not a recommendation.**
Re-tuning the threshold on it would burn the holdout, which
[PREREGISTRATION.md](PREREGISTRATION.md) explicitly forbids ("if 1.25 fails but
1.5 works, that is noise, not a discovery"). Testing a lower threshold honestly
needs a new pre-registration and a season nobody has looked at.

---

## 12. Season-specific models and ensembling: tested, rejected

Proposal: 2022-23 lost money across every spec, so train a model on it
separately and ensemble. Three checks, each fatal on its own.

### 2022-23 is an ordinary bad draw, not a regime

Simulating each season's P&L under a CONSTANT edge, using its own stakes and the
pooled 52.94% win rate:

| season | bets | win % | $won | sim mean | sim sd | z | pctile |
|---|---|---|---|---|---|---|---|
| 2018-19 | 117 | 56.41 | +460 | +113 | 1,028 | +0.34 | 62.9 |
| 2020-21 | 309 | 52.10 | −129 | +422 | 2,340 | −0.24 | 40.9 |
| 2021-22 | 380 | 52.63 | +508 | +568 | 2,916 | −0.02 | 48.9 |
| **2022-23** | 367 | 49.59 | **−3,199** | +525 | 2,690 | **−1.38** | **8.2** |
| **2023-24** | 394 | 53.05 | **+5,535** | +589 | 3,064 | **+1.61** | **94.5** |
| 2024-25 | 443 | 54.85 | −817 | +722 | 3,465 | −0.44 | 32.8 |
| 2025-26 | 428 | 53.97 | +3,204 | +697 | 3,434 | +0.73 | 76.5 |

**Season sd is $2,700–$3,500** — larger than most seasons' entire result. z=−1.38
is the 8th percentile; across seven seasons you expect one that low. 2023-24 is
the mirror image at +1.61. **The good season is as much an outlier as the bad
one**, so treating one as signal and the other as earned is incoherent.

### The environment did not differ

| season | over rate % | mean \|move\| | corr(pred,move) | mean open_total |
|---|---|---|---|---|
| 2021-22 | 51.46 | 2.671 | 0.252 | 220.7 |
| **2022-23** | **49.87** | **2.410** | **0.227** | **228.7** |
| 2023-24 | 49.27 | 2.622 | 0.359 | 228.2 |

Every 2022-23 value sits inside the range spanned by other seasons. Nothing would
have flagged it in advance — which is what a real regime requires.

### A and D are the same model

**corr(pred_A, pred_D) = 0.9711**; they call the same direction on **92.5%** of
games. This is why the A+D ensemble only ever bought +2.6% CLV, and why all six
specs share an identical season-by-season P&L pattern. There is nothing to
diversify.

### Also mechanically unnecessary

The walk-forward **already trains on 2022-23** for every later prediction. A
season-specific model cannot be applied to 2022-23 itself without leakage, and
adds nothing for later seasons that the expanding window does not already have.

**Legitimate version of the idea:** key a regime on something observable BEFORE
the games (scoring environment, pace, market behaviour) and let it apply to
whichever seasons match. That is a feature and gets tested like any other.
Selecting on a season label because its outcome is known is not.

---

## 13. Team-level line movement: real, unstable, and backwards

Do some teams draw bigger moves — a market-attention / flow effect? Distinct
from §7's team-identity test (which predicted the SIGNED move) and from the
move-class test (which never stratified by team). `team_moves.py`.

### A spread exists, barely above chance

| top | mean \|move\| | bottom | mean \|move\| |
|---|---|---|---|
| Milwaukee | 2.687 | Detroit | 2.265 |
| LA Lakers | 2.657 | San Antonio | 2.316 |
| Denver | 2.655 | Portland | 2.357 |
| Atlanta | 2.655 | Orlando | 2.379 |

Spread 0.422 pts, sd across teams 0.1053. Permuting team labels 2,000×: null sd
0.0856 ± 0.0111, so observed sits at the **95th percentile** — and the
top-bottom spread only at the **86th**. Marginal on one measure, absent on the
other.

### It does not persist — the decisive result

Year-over-year correlation of a team's mean |move|:

| from → to | corr |
|---|---|
| 2017-18 → 2018-19 | −0.153 |
| 2018-19 → 2020-21 | −0.440 |
| 2020-21 → 2021-22 | −0.059 |
| 2021-22 → 2022-23 | −0.086 |
| 2022-23 → 2023-24 | +0.276 |
| 2023-24 → 2024-25 | +0.300 |
| 2024-25 → 2025-26 | +0.074 |
| **mean** | **−0.013** |

In any season some teams stand out; **which** teams changes every year, sign
included. Nothing carries forward, so nothing is tradable.

This also argues specifically against the FLOW explanation: attention would
persist — the Lakers are always the Lakers. And the leaderboard is not a
big-market list (Milwaukee, Denver, Atlanta). It resembles a high-scoring list,
i.e. pace — which the model already carries, explaining why team dummies added
nothing in §7.

### The ranking is backwards for us anyway

| tercile | mean \|move\| | CLV | win % | $won |
|---|---|---|---|---|
| low \|move\| | 2.697 | **1.396** | **53.52** | **+7,899** |
| mid | 2.803 | 1.484 | 52.65 | +2,449 |
| high \|move\| | 2.945 | 1.284 | 52.68 | +543 |

The teams whose lines move most yield the LOWEST CLV, and nearly all profit sits
in the low-movement tercile. Consistent with move magnitude being unpredictable
(corr −0.036) while direction is not: a large move only helps if the sign was
called right, and we do not call it better in those games.

### Within-season vs across-season (§13 follow-up)

If team profiles change season to season, pooling across seasons is the wrong
unit and a team effect could be real WITHIN a season while vanishing across
them. That is falsifiable. `team_within.py`.

| horizon | mean corr |
|---|---|
| **within season** (first half → second half, same roster) | **+0.089** |
| **across seasons** (matched half-seasons) | **−0.008** |
| null at this sample size | −0.003 ± 0.069 |

Within-season does exceed across-season, which is the ordering roster turnover
predicts — the mechanism is the right shape. But **+0.089 is the 91st percentile
of its null, ~1.3 sd**: not significant. Per-season values run −0.259 to +0.362
with three of eight negative, so even the within-season figure is unstable.

The gap between horizons is +0.097 — the ceiling on what estimating team
profiles fresh each season could recover, and it is inside the noise band before
anything is built.

**Conclusion is stronger than "pooling is the wrong unit": team-level move
magnitude is noise at every horizon tested.** Roster turnover cannot explain the
missing across-season effect because there is no within-season effect to erode.

⚠ Sample-size trap this had to avoid: within-season correlations use ~36 games
per half against 500+ for a pooled season, so they would look worse on precision
alone. The across-season figure is therefore recomputed on half-seasons too, and
still comes out at zero.

### Concentrated team effects, not average ones (§13 follow-up 2)

Valid objection to the tests above: a correlation across 30 teams and a
permutation on the whole distribution both measure AVERAGE structure, and would
read ~zero if the effect were real for four teams and absent for twenty-six.
Different hypothesis, different test. `team_concentrated.py`.

All figures use each team-season's deviation from that season's league mean,
since league |move| drifts 2.04 → 2.80 across the sample.

**No individual team survives correction:**

| | count | expected by chance |
|---|---|---|
| raw p < 0.05 | 1 (San Antonio) | ~1.5 |
| BH FDR q < 0.10 | **0** | — |
| Bonferroni p < 0.05 | **0** | — |

**Consistency at chance:** 2 teams at 7+/8 or 1−/8 seasons above the league
mean, against ~2.1 expected.

**Tail persistence — the most direct test of the hypothesis:**

| | observed | chance |
|---|---|---|
| top-5 in t → still top-5 in t+1 | 6/35 = **17.1%** | 16.7% |
| top-5 → still top-10 | 13/35 = 37.1% | 33.3% |

Permutation null 5.9 ± 2.1, observed 6 — the **44th percentile**. Teams that
stand out in one season are no likelier than random to stand out in the next.

**Why: each team's swing exceeds its own effect.**

| team | mean dev | sd | seasons above |
|---|---|---|---|
| Detroit | −0.225 | **0.312** | 1/8 |
| Denver | +0.180 | **0.250** | 5/8 |
| San Antonio | −0.176 | **0.205** | 1/8 |
| Chicago | +0.157 | **0.269** | 6/8 |
| Milwaukee | +0.134 | **0.374** | 5/8 |

Teams DO stand out in individual seasons — Milwaukee's deviation swings ±0.37 —
but the standing-out is not a property of the team.

⚠ **Power limit:** with 8 seasons per team the minimum detectable effect is
~0.21 points (~8% of the 2.5 mean). A smaller genuine per-team effect would be
missed. This rules out effects large enough to trade, not all effects.

⚠ The strongest candidates are Detroit and San Antonio on the LOW side, which is
not a flow story even if real. The high side (Denver, Chicago, Milwaukee) again
resembles pace rather than market attention.

---

## 14. Mismatch games: the effect was real, backwards, and is now gone

Hypothesis: a strong team facing a weak one is perceived as a blowout, but the
favourite plays "just strong enough to win" — so games under-run expectations.
Framed on the split between what the public sees (**W-L records**) and what the
market prices (**the spread**). `mismatch.py`, `mismatch_oos.py`. Records are
built walk-forward within season; both teams need 10+ games played.

### The perception is true

Mean total rises with mismatch: 223.13 in the closest games to 227.17 in the
biggest. Blowouts really are higher-scoring.

### For TOTALS the direction is the opposite of the hypothesis

| \|spread\| quintile | actual − close | over % |
|---|---|---|
| 1 (1.8) | −0.716 | 46.69 |
| 3 (6.0) | +0.390 | 51.78 |
| 5 (12.8) | **+1.745** | **53.17** |

Mismatches came in **over** the close, not under. The favourite does not coast
enough to suppress scoring below the line; the market set these totals too LOW.

### For SPREADS the hypothesis holds

Favourites failed to cover in big mismatches — 47.7% at |spread| ≥ 10, 46.5% at
W-L gap > 0.45. "Plays just strong enough" is a spread phenomenon, not a totals
one.

### W-L records add nothing beyond the spread

corr(wl_gap, |spread|) = 0.4704. Orthogonalised against the spread, the W-L
quintiles are flat noise (actual−close 0.49, 1.21, 0.06, 1.07, 0.23; over% 50.7,
52.2, 48.2, 51.4, 50.3). **Perception and pricing do not diverge** — the market
has already priced the mismatch, so the public-vs-market gap this test was built
to find does not exist.

### And it has decayed (the actual finding)

| \|spread\| ≥ 12 | n | actual − close | over % | ROI −110 | fav cover % |
|---|---|---|---|---|---|
| **DEV 2017-2024** | 564 | **+3.006** | **55.81** | **+6.55** | **47.73** |
| **HOLDOUT 2024-26** | 350 | +0.947 | 51.58 | −1.54 | **52.33** |

| season | over % | | season | over % |
|---|---|---|---|---|
| 2017-18 | 55.26 | | **2024-25** | **51.55** |
| 2018-19 | 52.17 | | **2025-26** | **51.60** |
| 2020-21 | 58.06 | | | |
| 2021-22 | 56.60 | | | |
| 2022-23 | 57.75 | | | |
| 2023-24 | 55.92 | | | |

**Six of six development seasons above break-even; both holdout seasons below.**
The spread side reverses simultaneously (47.73% → 52.33%). Both halves flip at
the same time.

⚠ 350 holdout games gives a CI of [46.3, 56.8] — wide enough to contain both the
dev and holdout figures, so two seasons **cannot formally separate decay from a
bad run**. But six-for-six then zero-for-two, on totals and spreads at once, is
more than the noise story predicts comfortably. Consistent with
[ALPHA_DECAY.md](ALPHA_DECAY.md): this is a well-known bias, and well-known
biases are the ones that get arbitraged.

---

## 15. Extreme totals: correctly priced, and "3 SD" is untestable

Claim: when a total sits ~3 sd from the season's typical total, neither side
pays. `extreme_totals.py`. The season mean/sd are **walk-forward season-to-date**
(expanding, min 100 games) — using the finished season's statistics would leak.

Two readings, distinguished because they imply opposite trades:
**efficiency** (over% ≈ 50, both sides lose to vig) vs **reversion** (high totals
come in under, low totals over — one side pays).

### 3 SD is too rare to evaluate

| threshold | n | per season |
|---|---|---|
| \|z\| ≥ 2.0 | 549 | ~69 |
| \|z\| ≥ 2.5 | 159 | ~20 |
| **\|z\| ≥ 3.0** | **29** | **~4** |

29 games in eight seasons → over-rate CI [40.7, 76.6]. **Nothing is concludable
at 3 sd.**

### "Both sides lose" is true — and true everywhere

| band | n | over % | ROI over | ROI under |
|---|---|---|---|---|
| z < −2 | 206 | 50.49 | −3.62 | −5.47 |
| −1.5..−1 | 766 | 53.00 | **+1.19** | −10.28 |
| −0.5..0.5 | 2,944 | 50.07 | −4.42 | −4.68 |
| 1..1.5 | 923 | 51.14 | −2.37 | −6.72 |
| z > +2 | 343 | 51.31 | −2.04 | −7.05 |

Both sides lose in **eight of nine bands, including the middle**. That is the
vig, not a property of extremes. At −110 a side pays only if the over rate falls
outside [47.62, 52.38]; no band clears it. The one that nominally does
(−1.5..−1, 53.00%) has CI [49.47, 56.54], straddling break-even.

**The claim is the default state of a vigged market, not a finding.**

### Reversion is cleanly false

| tail | n | actual − close | t | p |
|---|---|---|---|---|
| HIGH z ≥ +2 | 343 | **+0.370** | 0.39 | 0.70 |
| LOW z ≤ −2 | 206 | **+0.461** | 0.40 | 0.69 |

Both tails go slightly OVER, by nearly identical amounts. Reversion requires
opposite signs; these share sign and magnitude.

### |z| predicts nothing

`resid ~ 1 + z + |z|` → multiple correlation **0.0082**, R² **0.00007**. The
flattest result in the project.

⚠ Contrast with §14: the mismatch test found a real +3.0-point development effect
that later decayed. This finds nothing anywhere — no development effect, no
holdout effect, no signal to decay. Extreme totals are simply priced correctly.

---

## 16. Blind partition search: no exploitable region, but a real unconditional bias

Every earlier angle was hypothesis-driven. This inverts it: let a depth-3 tree
search 29 features for regions where **`actual_total − close_total`** departs
from zero, with no basketball prior. `blind_partition.py`.

Target is deliberately bias against the **CLOSE**, not the open-to-close move.
Predicting the move front-runs a correction the market makes anyway — hence real
CLV and no win rate (§11). Bias against the close is what actually pays.

### The search found impressive structure. It is all noise.

| leaf | n | bias | t |
|---|---|---|---|
| 5 | 290 | **−3.993** | −3.73 |
| 11 | 313 | −3.805 | −3.88 |
| 9 | 2,160 | **+2.272** | **+5.86** |
| 4 | 288 | +2.623 | +2.55 |

t = 5.86 on 2,160 games is p < 1e-8 conventionally, with bias double the
break-even. **Refitting the identical tree on 400 shuffled residuals, the largest
leaf bias found on pure noise is 4.179 ± 0.851** — the observed 3.993 sits at the
**38th percentile of that null**. The search finds MORE structure on scrambled
data than on real data.

Holdout confirms: 3 of 7 leaves keep their sign (chance 50%), dev-to-holdout bias
correlation **−0.462**. The strongest leaves reverse.

⚠ **The permutation control is mandatory for any search-based method.** Without
it that t = 5.86 leaf reads as a discovery. A tree evaluating thousands of splits
returns an extreme order statistic; its best leaf is not a hypothesis test.

### The unconditional bias IS real and replicates

| set | n | bias | t | over % | ROI over |
|---|---|---|---|---|---|
| DEV 2017-2024 | 6,489 | **+0.531** | +2.37 | 50.37 | −3.83% |
| HOLDOUT 2024-26 | 2,207 | **+0.579** | +1.53 | 50.75 | −3.11% |
| pooled | 8,696 | **+0.543** | **+2.81** | 50.47 | −3.65% |

Actual totals exceed the close by ~half a point, and the holdout estimate lands
almost exactly on the development one. Among the cleanest replications here.

### And it is still not enough

**Break-even needs |bias| ≥ 1.08 points** — 0.0597 × 18.08, the sd of the TOTAL
residual. (Not 12.7, which is one team's score; that error would understate the
bar by 30%.) The real bias is about **half** what the vig costs.

**Revises the standing description of market efficiency:** the market is not
unbiased. It is biased by ~0.5 points, measurably and repeatably. **The vig band
is simply wider than the bias.** For any cross-sport screen the question is not
"is there bias" but "is the bias more than 0.06 sd", since that is the price of
−110.

---

## 17. CLV in points is the wrong metric — 88% of it is economically inert

A point of CLV only pays when the total lands BETWEEN our entry and the close.
Elsewhere the bet won, or lost, at both numbers: the line value is real and
worthless. `clv_decompose.py`.

⚠ Pushes are dropped at BOTH numbers. A first version dropped only pushes at the
open, which scored a push at the CLOSE as a loss for over-bets and a win for
under-bets. Given how imbalanced our sides turn out to be (below), that mattered.
Figures here are the corrected ones.

### Only ~5.5% of bets are decisive

Spec A, holdout, |pred| > 1.25:

| | n | share of bets | mean CLV | **share of total CLV** |
|---|---|---|---|---|
| decisive (move changed the outcome) | 19 | 5.5% | +3.921 | **11.6%** |
| inert | 324 | 94.5% | +1.747 | **88.4%** |

By distance from our number to the final total:

| distance | n | mean CLV | share of CLV | decisive % |
|---|---|---|---|---|
| 0–2 | 23 | 1.543 | 5.5% | **43.5%** |
| 2–5 | 50 | 1.870 | 14.6% | 16.0% |
| 5–10 | 65 | 1.800 | 18.3% | 1.5% |
| 10–20 | 106 | 1.203 | 19.9% | 0.0% |
| **20+** | 99 | **2.697** | **41.7%** | **0.0%** |

**Blowouts carry the highest CLV of any band and 41.7% of the total, with zero
chance of mattering.** Same mechanism as the forecast-bias/betting-bias split in
`SPORT_SCREENING_BRIEF.md`: a bet pays on which side, not by how much.

### Use realised pp, not points

`realised pp = win% at our number − win% at the close`.

| spec | set | thr | CLV pts | win @open | win @close | **realised pp** | predicted pp |
|---|---|---|---|---|---|---|---|
| A | DEV | 1.25 | 1.963 | 54.81 | 51.01 | **+3.80** | +7.52 |
| A | **HOLDOUT** | 1.25 | 1.867 | 49.85 | **44.90** | **+4.96** | +7.15 |
| D | DEV | 1.25 | 1.969 | 53.76 | 49.78 | +3.98 | +7.54 |
| D | **HOLDOUT** | 1.25 | 1.659 | 48.95 | **44.74** | +4.20 | +6.35 |

**The +3.83pp-per-point conversion overstates by roughly 50%.** Retire it. The
ceiling is the decisive rate (~5.5%), since that is the most games a move of this
size can flip.

### The side composition REVERSES between development and holdout

Fixing the push bug required tracking which side we take, which exposed this:

| spec | threshold | DEV % over | HOLDOUT % over |
|---|---|---|---|
| A | 0.00 | 44.9 | 52.5 |
| A | 0.75 | 32.1 | 55.9 |
| **A** | **1.25** | **23.7** | **59.5** |
| **D** | **1.25** | **21.5** | **61.6** |

**At the operating threshold the model bets ~77% UNDERS in development and ~60%
OVERS in holdout.** Raising the threshold pushes dev further under (44.9 → 23.7)
and holdout further over (52.5 → 59.5) — opposite directions.

This is a mechanical account of the §11 confidence inversion. The model's
high-conviction bets are **not the same kind of bet** in the two periods, so
there is no reason the dev threshold's performance should carry over. It is not
that the ranking degraded; the ranking is selecting a different population.

### Revised diagnosis

A bettor taking our exact sides **at the closing number wins 44.90%** in the
holdout. We add a genuine +4.96pp by entering early and arrive at 49.85%. The
arithmetic is consistent — **the problem is the baseline, not the conversion.**

This replaces the §6 framing. We convert CLV efficiently onto sides that sit
~5pp below fair at the close.

⚠ 44.90% rests on 343 bets (SE 2.7pp), ~1.9 SE below 50%. Development shows
51.01% at the close, so it does not replicate across the split — consistent with
the side-composition reversal above rather than with a stable defect.

---

## 18. Target reframing: aligning the loss with the payoff buys nothing

Every model here predicts `move_total` under squared loss, then gets thresholded
on |pred| and bet by sign — three layers between objective and payoff, with
squared loss treating a 6-point move 36× more seriously than a 1-point move when
both pay identically. The aligned alternative is to train on whether the bet won,
under logistic loss. `target_reframe.py`, development only, matched bet counts.

| top % | model | CLV | win % | ROI −110 |
|---|---|---|---|---|
| 100 | logistic on OUTCOME | 0.356 | **51.24** | −2.17 |
| 100 | ridge on MOVE | 0.597 | 50.03 | −4.48 |
| 30 | logistic | 0.551 | 49.52 | −5.46 |
| 30 | ridge | 1.309 | 52.22 | −0.32 |
| 10 | logistic | 0.811 | 49.16 | −6.15 |
| **10** | **ridge** | **1.827** | **55.22** | **+5.42** |

**The logistic model's confidence is anti-informative** — 51.24% → 49.16% as it
gets more selective, while ridge climbs 50.03% → 55.22%. Spec D matches
(logistic peaks 51.68% vs ridge 54.38%).

The mechanism is in one number: **`p_over` spans 0.430–0.580, sd 0.0196.**
Cross-validated regularisation flattened the model almost completely, which is
the correct response to a target with no learnable structure. "Did the over hit"
is the quantity §16's permutation-controlled blind search found nothing in, and
that the market prices without bias.

**The trade-off, now priced:** the move is predictable (corr ~0.29) but
front-runs a correction the market makes anyway; the outcome pays but cannot be
predicted. Aligning the loss with the payoff does not help because there is
nothing at the payoff end to learn.

**Rules out loss misalignment as a cause of the project's shortfall.** The three
layers of indirection cost nothing.

⚠ Not a translation artefact: the two models agree on side only 59.1% of the
time (corr 0.26 between outputs) — genuinely different, and simply worse.

### Assessment of three techniques from an external CBB notebook

| technique | verdict for NBA |
|---|---|
| Opponent-adjusted team quality (GLM team dummies) | **Inapplicable.** The rationale is unbalanced schedules; the NBA plays a balanced 82-game slate. Already tested as opponent-adjusted features (null), 60 team dummies (CLV 1.78→1.41, worse), and full RAPM (null). |
| Spline margin → win probability | **Adopt, marginal.** The parametric version exists in `clv_probability.py`; empirical vs normal differ by 0.42pp at the operating threshold. Measurement accuracy, not edge. |
| Cauchy / robust loss on blowouts | **Does not transfer** — `move_total` sd is 3.3 against 18.1 for the outcome residual, so there are no blowouts in move space. But its *logic* generated the test above, which is the value it had. |

---

## 19. The Ewing Theory: NOT supported (and a bug that faked it)

Hypothesis: when a team's best player sits, the market over-adjusts and the
short-handed team beats its number. `ewing.py`.

⚠ **An earlier version of this section reported 53.18% cover, t = 2.99,
p = 0.0028 and a 99.4th-percentile permutation result, with cover rates of
59.8% and 63.1% in 2017-19. All of it was a bug.** It is recorded here rather
than deleted because the failure mode is worth keeping.

**The bug.** Home/away was assigned by matching pbp-derived team points to the
box score. Points parsed from event descriptions match exactly only **85.4%** of
the time, so that assignment was wrong on **5.82%** of team-games. Worse, when
both teams matched the same side the pivot produced NaN, and `.astype(bool)`
turns NaN into **True** — i.e. "star absent" — injecting phantom absences.
`HOMEDESCRIPTION` gives a definitive assignment (exactly one team flagged home
in all 9,513 games) and is now used.

### Corrected result: null

Star fixed from the team's first 20 games (leading scorer, ≥10 appearances),
tested on games 21+. Absence split by type, since 33.7% of absences fall after
the star's final appearance and a permanently reorganised team is not an
overreaction candidate.

| situation | n | mean cover | cover % | 95% CI | t | p |
|---|---|---|---|---|---|---|
| **short-handed: TEMPORARY** | 1,618 | −0.168 | **49.01** | [46.6, 51.4] | −0.49 | **0.63** |
| short-handed: DEPARTED | 674 | −1.275 | 44.07 | [40.3, 47.8] | −2.54 | 0.011 |
| baseline: both present | 3,284 | −0.152 | 48.69 | [47.0, 50.4] | −0.66 | 0.51 |

Permutation null −0.164 ± 0.269 against an observed −0.168 — the **49.8th
percentile.** By season: 47.40, 52.82, 44.39, 50.83, 48.12, 51.90, 47.46. No
effect anywhere, and no 2017-19 spike.

**Temporary star absences produce no ATS edge in this data.**

### The unexpected result: fade the DEPARTED team

Teams playing after permanently losing their star cover only **44.07%**, so
backing the opponent wins **55.93%** against a 52.38% break-even.

| season | departed cover % | fade wins % |
|---|---|---|
| 2017-18 | 45.74 | 54.26 |
| 2018-19 | 47.37 | 52.63 |
| 2020-21 | 37.04 | 62.96 |
| 2021-22 | 46.81 | 53.19 |
| 2022-23 | 45.00 | 55.00 |
| 2023-24 | 43.66 | 56.34 |
| **2024-25** | 40.48 | **59.52** |

**Seven of seven seasons below 50%, six of seven clearing break-even, and the
two most recent are the second and third strongest.** Unlike §14 and every other
edge found here, it does not decay. Plausible mechanism: teams that lose a star
for the season also rest others, tank, and play out the string — the market
prices the absence but not the organisational response.

⚠ **Exploratory.** This is a post-hoc subgroup of a failed test, n = 674 total
and ~70–130 per season. It needs its own pre-registration, an independent
absence definition (RAPM-based rather than points-based), and a clean holdout
before it means anything. Recorded as the most promising untested lead, not as
a finding.

### What this cost, and the lesson

Two hours and a confidently-reported false positive, caught only because a
follow-up question about the star definition prompted a check of the absence
rate. **The permutation control did not catch it** — the bug corrupted the data
before the control ran, so the control faithfully confirmed a real pattern in
corrupted data. Controls validate inference, not data construction. Join keys
and side assignments need their own assertions, which `home_team_map()` now has.
