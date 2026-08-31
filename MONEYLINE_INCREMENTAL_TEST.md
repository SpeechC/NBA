# MONEYLINE — DOES OUR DISAGREEMENT ADD WIN INFORMATION? (2026-08-30)

The margin-anatomy work showed our model cannot improve margin RMSE. That is not
the moneyline question. **A moneyline pays on crossing zero, not on magnitude** —
an input can be useless for `ActualMargin - M_hat` and still inform `Margin > 0`.
This is the direct test.

**Verdict: null, and adequately powered.** Our disagreement with the book carries
no incremental information about who wins.

## Setup

```
M_hat   = hca + sP*(oeH_hat - oeR_hat)/100      structural basketball model, prior-only states
p_mkt   = de-vigged closing moneyline (multiplicative)
D_M     = M_hat - M_book
n = 4,554 regular-season games, 2022-11-07 .. 2026-04-12
our M_hat sd 6.41 | book sd 7.62 | D_M sd 3.91 | corr(M_hat, book) 0.859
```

## TEST 1 — model-specific calibration, from outcomes

The concern was overconfidence: applying the book's spread->probability curve to a
noisier margin forecast would overstate certainty. **Measured, the effect is small.**

| expected margin | 0 | +3 | +5 | +7 | +10 | +14 |
|---|---|---|---|---|---|---|
| our `M_hat`, fitted on OUTCOMES | 48.3% | 57.9% | 64.5% | 70.7% | 78.7% | 86.2% |
| book spread, fitted on OUTCOMES | 49.4% | 58.0% | 63.8% | 69.8% | 78.5% | 88.6% |
| market PRICE curve (S3) | 50.1% | 57.6% | 64.4% | 71.6% | 81.3% | 89.7% |

Our curve tracks the book's through +10 and flattens only in the tail (86.2% vs
89.7% at +14). Per point of forecast margin, our model is about as informative as
the book's spread. **It is not overconfident — it is simply not additive.**

## TEST 2 — incremental information over the market (the decisive one)

```
Phi^-1(P(win)) = Phi^-1(p_mkt) + beta*D_M          H0: beta = 0

D = M_hat - CLOSING spread    beta -0.00409   se 0.00516   t -0.79
D = M_hat - OPENING spread    beta -0.00257   se 0.00585   t -0.44
                              chi2(1) = 0.63   p = 0.428
```

Sign is negative; magnitude is indistinguishable from zero.

**Free-coefficient sanity check:** letting the market offset take its own
coefficient gives **+1.0416, t = +0.25 against 1.0**, with `D_M` at t = −0.06.
The market probability is exactly calibrated — it cannot be improved by rescaling,
and our disagreement adds nothing on top.

## TEST 3 — structural components

Small, structural, no market inputs inside the terms:

| specification | chi2 | df | p |
|---|---|---|---|
| `D_M` | 0.63 | 1 | 0.428 |
| `D_M + D_pace` | 0.66 | 2 | 0.720 |
| `D_offdiff + D_pace` | 0.97 | 2 | 0.616 |

**Caveat:** individual standard errors in the two-term fits come from a BFGS
inverse Hessian and are not a valid covariance estimate (one reads t = −5.10 and
is an artefact). The likelihood-ratio tests above are the valid statistics.

## First-order probability edge

```
E_ML = (dp/dM)|_{M_book} * D_M
(Win - p_mkt) ~ E_ML:   beta -0.0292   se 0.0586   t -0.50
E_ML sd 0.1137
```

## dp/dM — and a correction to the standard intuition

| \|spread\| | 0 | 1 | 3 | 5 | 7 | 10 | 14 |
|---|---|---|---|---|---|---|---|
| 1 pt of margin is worth | 1.75pp | 2.30pp | 3.15pp | **3.58pp** | 3.55pp | 2.81pp | 1.42pp |

The usual claim is that a point matters most at a pick-em and least on a big
favourite. **Only the second half is right.** A point is worth least at BOTH
extremes and peaks around a 5-7 point spread, because the smile widens sigma
toward zero exactly where `phi(z)` is maximal and the two effects cancel.

The pick-em value sits in the region where sigma is weakly identified (see
`MONEYLINE_EMULATOR.md`), so treat 1.75pp as indicative; the 5-7 point peak is
robust.

## Boundary analysis — near the zero crossing

`(Win - p_mkt) ~ D_M`, by book spread bucket:

| \|book spread\| | n | beta | t |
|---|---|---|---|
| 0-2 | 455 | −0.00181 | −0.23 |
| 2-4 | 922 | −0.00955 | **−2.05** |
| 4-7 | 1,260 | +0.00205 | +0.55 |
| 7-10 | 898 | +0.00051 | +0.14 |
| 10-40 | 1,019 | −0.00105 | −0.45 |

No bucket carries positive information. The single |t| > 2 is **negative** — our
disagreement points the wrong way there — and is one of five tests.

## POWER — the null is informative

```
se(beta) 0.00516  ->  MDE(80%, one-sided) = 2.487*se = 0.01283
a 1sd disagreement (3.91 pts) moves z by 0.0502
  = 2.00pp of win probability at p = 0.5

moneyline overround 1.0418  ->  ~2.09pp of edge per side to break even
```

**The MDE (2.00pp) sits just under the break-even requirement (2.09pp).** The test
had roughly 80% power to detect an effect at exactly the size that would have been
tradeable. This is a null with teeth, not an underpowered shrug.

## Verdict

Three specifications, five spread buckets and the first-order edge all return
nothing, at a power level that would have caught a tradeable effect. **The
moneyline wagering channel is closed**, and it is now closed on the correct
target — the binary win outcome — rather than inferred from margin RMSE.

## Economic backtesting is NOT available at the open

The data carries opening spread, closing spread, and **only a closing moneyline**.
Historical opening-moneyline ROI therefore cannot be reconstructed from executed
prices. A synthetic `p_open = F(OpenSpread)` is defensible for signal research —
the transform is timestamp-stable, sigma@6 = 12.47 open vs 12.85 close — but it is
a modelled price, not a quote. **No claim of realised opening-moneyline ROI may be
made from it.** Capture actual opening and subsequent moneyline prices
prospectively in 2026-27 before any economic claim.
