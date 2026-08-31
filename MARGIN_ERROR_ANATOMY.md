# MARGIN ERROR ANATOMY — which structural input is wrong (2026-08-30)

Steps 1, 2 and the matchup-interaction battery of the moneyline directive, plus
the decisive test the sequence builds toward. Diagnostic, not forecasting.

**Result: the margin channel is closed, and for a reason we had already
measured.** The input that dominates margin error is the one that is
structurally unforecastable.

## Setup, and a defect corrected first

```
margin = gpace * (OEFF_H - OEFF_R) / 100      identity holds: corr 0.999958, MAE 0.027 pts
```

**HCA defect.** The state engine computes `sOH = LO + Off[H] + Def[R]` with **no
home-court term** — states are venue-symmetric. Mean model margin is **−0.078**
against an actual **+1.940**, so `M_hat` omitted **2.018 points** of HCA. Without
it, **74.5% of games signalled ROAD**; with a prior-only expanding HCA, 48.5%.

This corrupted the sign test in `SPREAD_EFFICIENCY_GAP.md` (the regression was
safe — it carried an intercept). **Corrected result: 49.49%, ROI −5.52%, versus
49.55% / −5.40% before. The conclusion is unchanged.** HCA is absorbed
symmetrically into the efficiency forecasts (`delta = 50*hca/sP`) so that
substituting a realised OEFF — which already contains the venue effect — is
apples-to-apples.

Baseline margin model: RMSE **13.953**, bias −0.320. The book: RMSE **13.587**.
Our model is worse than the book before any of this begins.

## STEP 1 — oracle decomposition of the worst decile

Worst decile of |margin error|, n = 472, mean |e| **29.69 pts** (vs 10.92 overall).

| substitute the ACTUAL value of... | SSE remaining | share of worst-decile SSE |
|---|---|---|
| nothing (baseline) | 433,271 | — |
| **pace** | 431,783 | **0.3%** |
| home offensive efficiency | 147,643 | 65.9% |
| road offensive efficiency* | 141,637 | 67.3% |
| all three (full oracle) | 1 | 100.0% |

Per-game dominant mechanism, worst decile: road efficiency **52.3%**, home
efficiency **46.2%**, multiple 1.5%, **pace 0%**. Full sample: road 34.8%, home
33.7%, unexplained 28.8%, **pace 1.9%**.

\* One realised OEFF cannot separate road offence from home defence. Same on the
other side. This is an identification limit of the decomposition, not an omission.

Shares exceed 100% because in a blowout both efficiency errors push the same
direction, so fixing either captures most of the gap.

**This is the mirror image of totals.** Pace was the productive channel there and
is worth **0.3%** here — consistent with the measured 42x multiplier difference
(`EffSum` ~230 for totals, `EffDiff` ~0 for margin).

## STEP 2 — is the recurring efficiency miss offence or defence?

Neither. It does not recur. Prior-only 10-game state drifts, n = 4,654:

```
predicting eps_H (home offence error)    R2 0.0005   own-offence t -0.28   opp-defence t -1.43
predicting eps_R (road offence error)    R2 0.0000   own-offence t +0.19   opp-defence t -0.30
margin error ~ all four state drifts     R2 0.00084  no |t| >= 2
```

For totals the analogous drift (`mu5`) predicted pace error at **t = +2.20** —
that persistence is what made `m(X)` viable. Here the channel is flat.

**We had already measured why.** From the ladder assumption test: 3PT shooting is
essentially exactly binomial, `phi 0.9883`, `rho -0.00035`, with cross-channel
correlations under 0.02. No hot hand, no hot night. Pace is a stylistic choice a
team repeats; efficiency is shooting, which is noise by construction.

## SECTION 6 — basketball-specific matchup cross-terms

Prior-only 15-game profiles, no market inputs, n = 4,557:

| cross-term | beta (pts per sd) | t |
|---|---|---|
| 3PA rate x opponent 3P defence | −0.1629 | −0.79 |
| OREB% x opponent DREB% | −0.0971 | −0.47 |
| TOV% x opponent TOV forced | −0.1927 | −0.93 |
| FT rate x opponent FT allowed | +0.3768 | +1.82 |

Joint R^2 **0.00111** against a margin-error sd of 13.97. Nothing survives, and
`x_ftr` at face value delivers 0.377 pts/sd against an **0.812-pt** bar — under
half, so it fails the mechanism test regardless of significance.

## THE DECISIVE TEST — can anything predict the BOOK's error?

Everything above predicts *our* error. Only the book's error pays.

| feature | beta pts/sd | t |
|---|---|---|
| road-defence drift | +0.4913 | +2.44 |
| road-offence drift | −0.2645 | −1.31 |
| home-defence drift | −0.2178 | −1.08 |
| home-offence drift | +0.1634 | +0.81 |
| all four cross-terms | — | \|t\| < 1.2 |
| our own disagreement `D_M` | +0.2249 | +1.12 |

```
JOINT R2 on the book error   0.00288      (null expectation k/n = 8/4557 = 0.00176)
best achievable edge         0.730 pts of sd, IN SAMPLE
required to beat -110        0.812 pts
bet sign(our model - book)   4,548 bets   hit 49.34%   ROI -5.80%
```

The single t = +2.44 is one of nine tests; Holm requires |t| > 2.77. The joint
model is barely above its null expectation, and even fitted in-sample it does not
reach the bar.

## AVAILABILITY — a real effect, killed by timing

Injuries looked like the exception. They are not.

```
does inj_diff predict...                    beta pts/sd        t
  OUR model error (has no injury input)         +2.2605    +9.78
  the OPENING-spread error                      +0.9627    +4.23
  the CLOSING-spread error                      +0.4187    +1.86   <- not significant
  line move (close - open) ~ inj_diff           +0.5441   +16.16   <- the book doing its job
  closing error ~ LATE-breaking news only       -0.1306    -0.58
```

**0.963 − 0.544 = 0.419, exactly.** The book prices injuries; it does so between
the open and the close. Measured against the opener the effect clears the bar and
looks like a 4-sigma edge — it is entirely information timing, the same artefact
`INJURY_TIMING_AUDIT.md` caught before. Against the close it is neither
significant nor large enough to matter.

## Verdict on the sequence

Steps 3-5 (rich current-team profiles, `m_M(X)`, OOS test) are predicated on
conditional bias existing in the margin forecast. **Three named feature families
have now been tested against the book's error — state drift, basketball matchup
interactions, and availability — and all are null.** Building a richer estimator
on top of them has nothing to estimate.

**Untested, and the only genuinely new material:** shot-location / rim-rate
profiles, which require the PBP store, and style-susceptibility splits
(performance against strong/weak defences). Neither changes the structural
problem: 66% of worst-decile margin error is shooting efficiency, and shooting is
binomial.

**The pricing layer was never the obstacle.** `MONEYLINE_EMULATOR.md` shows the
spread → probability transform is calibrated to 0.42pp. The obstacle is the
expected margin, and the input that dominates its error is random.
