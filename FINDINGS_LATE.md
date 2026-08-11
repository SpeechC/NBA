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
