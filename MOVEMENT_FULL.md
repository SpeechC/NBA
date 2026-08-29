# Line-movement strategy over the full sample

Burn-in is now applied once across the whole chain instead of four times in sequence. 2019-20 is absent from the source data, so there is a gap between 2018-19 and 2020-21.


Bets graded from **2018-02-22** to **2026-04-12** (8183 games with a prediction).


## Coverage by season

| season                        |   games | first               | last                |
|:------------------------------|--------:|:--------------------|:--------------------|
| NBA 2017-2018 Regular Season  |     365 | 2018-02-22 00:00:00 | 2018-04-11 00:00:00 |
| NBA 2018-2019 Regular Season  |    1165 | 2018-10-24 00:00:00 | 2019-04-10 00:00:00 |
| NBA 2020-2021 Regular Season  |    1015 | 2020-12-31 00:00:00 | 2021-05-16 00:00:00 |
| NBA 2021-2022 Regular Season  |    1166 | 2021-10-27 00:00:00 | 2022-04-10 00:00:00 |
| NBA 2022-2023 Regular Season  |    1163 | 2022-10-26 00:00:00 | 2023-04-09 00:00:00 |
| NBA 2023 In-Season Tournament |       4 | 2023-12-04 00:00:00 | 2023-12-05 00:00:00 |
| NBA 2023-2024 Regular Season  |    1098 | 2023-11-01 00:00:00 | 2024-04-14 00:00:00 |
| NBA 2024 In-Season Tournament |       2 | 2024-12-10 00:00:00 | 2024-12-11 00:00:00 |
| NBA 2024-2025 Regular Season  |    1104 | 2024-10-30 00:00:00 | 2025-04-13 00:00:00 |
| NBA 2025 In-Season Tournament |       4 | 2025-12-09 00:00:00 | 2025-12-10 00:00:00 |
| NBA 2025-2026 Regular Season  |    1097 | 2025-10-29 00:00:00 | 2026-04-12 00:00:00 |


## Strategy performance

|            |    n |   CLV |   CLV lo |   CLV hi |   beat close % |   win % |   win lo |   win hi |   ROI % |   P(ROI>0) % |
|:-----------|-----:|------:|---------:|---------:|---------------:|--------:|---------:|---------:|--------:|-------------:|
| all        | 8145 | 0.57  |    0.501 |    0.639 |         53.196 |  50.804 |   49.718 |   51.889 |  -3.01  |        0.275 |
| |pred|>0.5 | 4242 | 0.904 |    0.807 |    1.002 |         57.17  |  50.943 |   49.438 |   52.446 |  -2.745 |        3.3   |
| |pred|>1   | 1587 | 1.343 |    1.178 |    1.509 |         63.471 |  52.552 |   50.092 |   55.002 |   0.327 |       55.375 |
| |pred|>1.5 |  512 | 1.914 |    1.606 |    2.223 |         70.37  |  54.297 |   49.968 |   58.577 |   3.658 |       80.275 |


## Season by season at |pred| > 1

| season                        |   bets |   win_pct |   clv |   ROI % |
|:------------------------------|-------:|----------:|------:|--------:|
| NBA 2017-2018 Regular Season  |     74 |     52.7  |  0.95 |    0.61 |
| NBA 2018-2019 Regular Season  |    173 |     52.6  |  0.8  |    0.42 |
| NBA 2020-2021 Regular Season  |    140 |     52.14 |  1.62 |   -0.45 |
| NBA 2021-2022 Regular Season  |    223 |     51.57 |  1.25 |   -1.55 |
| NBA 2022-2023 Regular Season  |    207 |     49.76 |  1.17 |   -5.01 |
| NBA 2023-2024 Regular Season  |    254 |     55.91 |  1.87 |    6.73 |
| NBA 2024 In-Season Tournament |      1 |    100    | 16.5  |   90.91 |
| NBA 2024-2025 Regular Season  |    272 |     51.84 |  1.26 |   -1.04 |
| NBA 2025 In-Season Tournament |      1 |    100    | -3    |   90.91 |
| NBA 2025-2026 Regular Season  |    242 |     52.89 |  1.42 |    0.98 |


Seasons with a winning record: **6 of 10**. Seasons with positive CLV: **9 of 10**.

---

# P&L RE-CHECK 2026-08-26 — read-only, frozen signal untouched

Run after the `cohesion` branch showed a statistical pass that did not trade.
Nothing here modifies the estimator, weights, thresholds or rule. Reproduces
`PREREG_move_combined` exactly (53.44% / +2.02% at ≥1.0; 54.42% / +3.90% at
≥1.5), so the artifacts are intact.

## The contrast with cohesion is the point

| | MOVE_COMBINED | cohesion |
|---|---|---|
| evaluated on | **covers** (sign of actual−line) | points, then assumed to convert |
| points of edge required at −110 | 1.071 | 0.775 |
| points of edge available | **1.610** (mean \|m\| at ≥1.0) | 0.412 / 0.575 |
| ratio available/required | **1.50×** | 0.53–0.74× |
| implied hit rate | 53.58% | 51.27% |
| **realised hit rate** | **53.44%** | 50.51% |
| realised ROI | **+2.02%** | −3.56% |

**MOVE_COMBINED does not have the cohesion pathology.** For a totals bet the
cover *is* the sign of (actual − line), so this signal was always measured on
the tradeable quantity. And realised 53.44% lands almost exactly on the implied
53.58% — the model behaves as the arithmetic of a stale opener says it should.

The tail diagnostic (outcome-conditioned, diagnostic only) shows no
concentration pathology either: near the number 53.37%, middle 50.34%, blowout
tail 56.62%. With ~595 bets per cell (se 2.05pp) these are mutually
indistinguishable — the split is uninformative rather than damning, which is
itself the answer: the edge is not confined to already-decided games the way
cohesion's was.

## But the P&L is still NOT statistically established

```
|m| >= 1.0   n=1,787  hit 53.44%  ROI +2.02%
             hit 95% CI [51.12%, 55.76%]  ->  ROI 95% CI [-2.40%, +6.45%]  INCLUDES 0
             z vs break-even +0.90   one-sided p = 0.1849

|m| >= 1.5   n=814    hit 54.42%  ROI +3.90%
             hit 95% CI [50.99%, 57.86%]  ->  ROI 95% CI [-2.66%, +10.46%]  INCLUDES 0
```

Season by season at ≥1.0: **54.98 / 48.24 / 55.96 / 54.33 / 53.89** — 2022 lost
7.91% ROI over 369 bets. Equity path at ≥1.0: final +$3,618 against a **max
drawdown of −$4,073 (41 units)**, 20% of the path below zero, worst point
−$1,373. The confirmatory ≥1.5 cell is smoother (max drawdown 28 units, 3%
below zero) but on half the bets.

**This is exactly what `PREREG_move_combined` §2 fixed in advance:** ROI at
53.44% needs ~17,500 bets ≈ 49 seasons to establish, so ROI "can never be the
decision variable; it is secondary by necessity, not choice."

## The primary endpoint is the one that IS established

```
CLV at |m| >= 1.0   n=1,792   mean +1.3367 pts   t = +16.42
                    beat the close 62.2%, tied 6.3%
  2021 +1.116 (t=+6.86)   2022 +1.067 (t=+6.32)   2023 +1.827 (t=+9.29)
  2024 +1.390 (t=+7.10)   2025 +1.381 (t=+7.24)
```

**Positive in all five seasons, including the season that lost money.** That is
the whole argument for CLV as the endpoint: 2022 returned −7.91% ROI while
still beating the close by +1.067 points at t = +6.32. The signal was right
about the number and wrong about the outcomes, which is what a real edge looks
like over 369 bets.

## A second arithmetic error, caught and corrected here

My first pass computed the ROI confidence interval as `2.1·hit − 1`. The
correct multiplier is `1 + 90.909/100 = 1.90909`. The wrong version reported
the ≥1.0 ROI CI as [+7.36%, +17.10%] — excluding zero and implying an
established edge. **The correct CI is [−2.40%, +6.45%], which includes zero.**
Same family of slip as the cohesion §7 error: the point estimates were right
and the conversion to a decision quantity was not.

## Disposition — unchanged, and that was already the right call

`PREREG_move_combined` already excludes live capital on this signal at a −110
venue, on the grounds that the net edge at the decision threshold is ~1.1pp,
inside single-season noise. This re-check confirms the number (+1.06pp realised
at ≥1.0) and adds that the ROI interval includes zero. **Nothing changes.**

The signal is real where it was claimed to be real — CLV, t = +16.42, five
seasons out of five. It is unproven where it was always going to be unproven,
and the prereg said so before the P&L existed.

---

# AGENT REPORT 2026-08-29 — the incumbent re-proposed as a discovery

The structural research agent flagged the movement chain's control column as
"the single largest effect anywhere in 114 outcome looks" and stated it "has
never been graded as a wager." **The effect size claim is right. The
never-graded claim is wrong**, and the inference built on it is the error this
program corrected twice on 2026-08-26.

## It has been graded, pre-registered, and re-checked

| subset | n | CLV | t | **realised hit** | **realised ROI** | z |
|---|---|---|---|---|---|---|
| all games | 5,158 | +0.618 | +13.23 | 51.10% | **−2.45%** | −1.84 |
| selective \|m\| ≥ 1.0 | 1,792 | +1.337 | +16.42 | 53.44% | **+2.02%** | +0.90 |

`PREREG_move_combined.md` §2 fixed CLV as the primary endpoint **precisely
because** ROI at 53.44% needs ~17,500 bets ≈ 49 seasons, and §9 already
excludes live capital at −110. The agent's figures (CLV 0.655 / 1.424 on
n = 2,072 / 696) track ours closely but sit on roughly a third of the data —
two seasons against five.

## The CLV → implied-ROI step is not valid, and we have the counterexample

The agent converts CLV to an implied win rate to an implied ROI (+3.5%).
**CLV and outcome P&L are different endpoints and this program has a decisive
case where they diverge in sign:**

```
injury Hypothesis B:  CLV +0.775 pts, t = +7.93   ->   P&L -8.04%, CI EXCLUDES 0
```

Strong CLV with significantly negative realised P&L, simultaneously. A line
moving toward you is not a game landing on you. Here the realised 53.44% is
actually *better* than the CLV-implied 52.97% — the conversion is noisy in both
directions, which is the point: it is not a substitute for grading.

## What the agent got right, and what it earned

The effect *is* the largest thing in the program, and that is exactly why it is
the incumbent — everything else has been measured against it. The agent
rediscovered its own control. That is a real observation about the search, not
a new asset.

Its four-item recommendation was good. Two were already done (bet-level ROI;
season-by-season stability, in `MONITOR_SEASON_PNL.md`). One was genuinely
undone and is now done:

**Block-bootstrap inference on the selective subset** — the naive binomial CI
assumes independent bets, but bets on a night share a league state and bets in
a season share a regime:

| method | ROI 95% CI | P(ROI > 0) |
|---|---|---|
| naive binomial | [−2.40%, +6.45%] | — |
| block bootstrap **by night** (629 blocks) | [−2.37%, +6.43%] | **81.0%** |
| block bootstrap **by season** (5 blocks) | [−3.52%, +5.57%] | **76.4%** |

Night-level clustering barely widens the interval — within-night correlation is
small. Season-level clustering widens it more, because there are only five
blocks. Either way the interval includes zero and P(ROI > 0) is 76–81%.

## The one item still open, and it is the one that matters

**Is the opener transactable?** MOVE_COMBINED bets AT THE OPENER by
construction. Every number above assumes you can get that number. This program
has died on execution before — the Kalshi derivatives quoted 15–30c against
edges worth 3–6c. Nothing here establishes that the opening total is available
in size, or at −110, or at all. That is an execution study, not a research one,
and it has never been run.

**Disposition unchanged.** No capital. The agent's proposal to characterise
rather than search is sound; two of its four items were already answered, one
is answered above, and the fourth is the real question.
