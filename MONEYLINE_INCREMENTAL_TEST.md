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

## THE CONCLUSION, SCOPED TO WHAT THE DATA CAN SUPPORT

**No exploitable residual team- or matchup-specific moneyline information remains
in CLOSING prices.** Persistent basketball states exist — turnover surprises carry
a 2-game half-life and are still detectable 8 games out, FT generation and 2P
conversion persist too — and the closing market incorporates them at every horizon
from 1 to 20 games.

**Whether a very early moneyline price briefly underreacts cannot be established
from the historical dataset, because opening moneylines were never captured.** The
only moneyline in `dfMaster` is the closing one. The injury work shows the market
does move materially between open and close (+0.544 pts/sd on injury news,
t = +16.16), so the gap is real rather than hypothetical.

Amendment 7 captures `open_ml_h` / `open_ml_r` prospectively from 2026-27 so this
loophole can be closed with executed quotes rather than a synthetic price. Those
fields are **observation only** and may not enter any registered test.

## Economic backtesting is NOT available at the open

The data carries opening spread, closing spread, and **only a closing moneyline**.
Historical opening-moneyline ROI therefore cannot be reconstructed from executed
prices. A synthetic `p_open = F(OpenSpread)` is defensible for signal research —
the transform is timestamp-stable, sigma@6 = 12.47 open vs 12.85 close — but it is
a modelled price, not a quote. **No claim of realised opening-moneyline ROI may be
made from it.** Capture actual opening and subsequent moneyline prices
prospectively in 2026-27 before any economic claim.

---

# THE CONDITIONAL TEST — local analogs, not pooled coefficients (2026-08-30)

The pooled result establishes `E[beta] ~ 0`. It does **not** establish
`beta(X) = 0` for every current matchup. If 15% of the slate carried a true +5pp
edge and 85% carried zero, the average is 0.75pp — far under the 2.00pp MDE, and
invisible to the pooled test. This is the totals progression run literally:
**generic average effect -> current team profiles -> conditional model bias.**

## Construction

```
n = 4,554 -> 3,354 evaluated (1,200-game burn-in)
23 current-profile features, ALL prior-only:
   offence/defence/pace states, four drift states,
   3PA rate, OREB%, TOV%, FT rate -- own and allowed, both teams,
   rest state
standardised on the BURN-IN WINDOW ONLY (no outcome use, no full-sample leak)
K = 200 nearest prior matchups by Euclidean distance on the standardised profile
franchise identity is NOT a feature -- analogs cross teams and seasons freely
```

Within each game's analogs, strictly from games that precede it:

```
m_M(X)            = mean(ActualMargin - M_hat)          local model bias
delta(X), beta(X) = OLS of (Win - p_mkt) on [1, D_M]    local market value
```

Empirical-Bayes shrinkage weights: **m_M 0.154, delta 0.077, beta 0.160.** The
estimator itself reports that ~85% of the raw local variation is noise.

## A. Current-profile conditional bias

| OOS regression | beta | t |
|---|---|---|
| `e_M ~ m_M(X)` (beta = 1 if calibrated) | +2.7762 | +1.86 |
| `e_M ~ raw analog mean` (unshrunk) | +0.4269 | +1.86 |
| **`e_M ~ simple drift benchmark`** | **+0.0835** | **+2.32** |

**The elaborate local-analog estimator is beaten by the trivial drift benchmark.**
Neither reaches significance after any multiplicity allowance, and beta = 2.78
against a calibrated value of 1.0 says the shrinkage is badly mis-scaled anyway.

```
margin RMSE   M_hat 14.3098  ->  M_hat + m_M(X) 14.3039   (-0.0060)
the BOOK on the same games                       13.7366
gap to close 0.573 pts;  m_M(X) delivers 0.006  = 1.04% of the way
```

## B. Current-profile conditional market value

```
predicted incremental probability: sd 0.0059, range [-0.032, +0.034]
(Win - p_mkt) ~ predicted:  beta +0.8500  se 1.2892  t +0.66
```

**The ranking does not work.** Deciles of predicted incremental probability
against actual `Win - p_mkt`:

| decile | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| predicted | −0.0104 | −0.0046 | −0.0026 | −0.0013 | −0.0002 | +0.0009 | +0.0021 | +0.0034 | +0.0054 | +0.0114 |
| **actual** | −0.0336 | +0.0075 | +0.0236 | −0.0412 | +0.0111 | **−0.0586** | −0.0084 | −0.0175 | +0.0368 | −0.0062 |

Monotone in the prediction, unrelated in the outcome. Top minus bottom decile
**+0.0273, t = +0.81**. The largest |t| is decile 6 at −2.39 — the middle of the
ranking, which is what noise looks like.

Feeding the correction back through the offset probit changes nothing:

```
D_M   (raw)                 beta -0.00414   t -0.69
D*_M  (profile-corrected)   beta -0.00375   t -0.62
```

## The economic question, answered directly

Does the method ever **find** a tradeable game? Break-even needs **2.09pp**.

| predicted edge | games | % of slate | mean predicted | ACTUAL `Win - p_mkt` | t |
|---|---|---|---|---|---|
| > 2.09pp (the bar) | **15** | 0.4% | +0.0243 | **−0.1692** | −1.89 |
| > 1.50pp | 59 | 1.8% | +0.0192 | +0.0568 | +1.06 |
| > 1.00pp | 169 | 5.0% | +0.0146 | +0.0586 | +1.82 |

**The top decile's own predicted edge is 1.14pp — below the 2.09pp bar.** The
method almost never claims a tradeable game, and the 15 times it does, those games
went the *wrong* way. The positive figures at 1.0-1.5pp are threshold search on
the outcome column, are non-monotone against the 2.09pp row, and are recorded here
only so they are not rediscovered later as a finding.

## Verdict

The conditional step that rescued the totals work has now been run on the
moneyline, in the same form, and returns nothing: the local-analog bias closes
**1%** of the gap to the book, and the local disagreement coefficient cannot rank
outcomes.

**Untested and honestly outstanding:** eFG states, rim rate and shot-location
profiles (these need the PBP store — the one job that stack could still do), and
roster continuity/availability inside the analog vector. Adding them does not
change the structural obstacle: **two-thirds of margin error is shooting
efficiency, and shooting is binomial** (phi 0.9883, rho -0.00035, measured). A
richer description of style cannot make a random variable forecastable.
