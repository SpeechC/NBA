# Are the dev distributions Gaussian? — audit 2026-08-29

Every points→hit-rate conversion in this program uses `φ(0)/σ = 0.3989/σ`,
which assumes normality. That assumption is now tested. n = 9,486 regular-season
games, 5.13% with overtime.

## The answer splits by market

| series | sd | skew | exc. kurtosis | Jarque-Bera p | verdict |
|---|---|---|---|---|---|
| FULL total | 18.06 | **+0.232** | +0.395 | 1.3e-32 | **NOT Gaussian** |
| FULL spread | 13.24 | +0.005 | **+0.498** | 4.9e-22 | **NOT Gaussian** |
| 1H total (resid) | 11.91 | +0.044 | +0.011 | **0.21** | **Gaussian** |
| 1H spread (resid) | 10.77 | −0.004 | +0.100 | **0.14** | **Gaussian** |

**First halves are Gaussian; full games are not.** Both full-game series are
**leptokurtic** — more mass at the centre *and* in the tails, less in the
shoulders. The full total is additionally **right-skewed (+0.232)**, which is
the overtime mixture: 5.13% of games get a one-sided scoring jump. The full
spread is almost perfectly symmetric (skew +0.005) but just as leptokurtic.

1H escapes both because it contains no overtime and fewer garbage-time blowouts.

## A structural fact that matters more than the shape

The win-probability gain from `x` points of edge is a **step function**, not a
smooth curve, because totals and margins land on integers and half-integers:

**FULL TOTAL** — exact empirical gain
```
edge 0.25 -> 1.08pp      edge 1.00 -> 2.30pp
edge 0.50 -> 1.08pp      edge 1.60 -> 4.60pp
                         edge 2.00 -> 4.60pp
```

0.25 and 0.50 points buy **identical** probability; so do 1.60 and 2.00. Key
numbers, not density, decide what a half-point is worth.

## What this does to the conversion — the Gaussian was CONSERVATIVE

Points of edge required to clear −110 (+2.381pp):

| market | Gaussian (used all session) | **EXACT empirical** | error |
|---|---|---|---|
| total | 1.078 | **1.000** | 8% too demanding |
| spread | 0.790 | **0.500** | **58% too demanding** |

The leptokurtic peak means a point at the line is worth **more** than the
Gaussian says — 2.67c vs 2.21c per point on totals, 4.12c vs 3.01c on spreads.
Every edge quoted in this session was therefore **understated**, which is the
safe direction to be wrong but is still wrong.

## Two reasons NOT to simply rescale everything upward

**1. The correction only applies to effects that are AT the line.** The
conversion assumes an effect shifts the whole distribution. `PREREG_cohesion`'s
did not — β = +0.0636 (t = +0.52) near the number against +2.82 in the blowout
tail — so no density is the right one for it, and its realised **−3.56% ROI**
stands. `CrewShock` does qualify: near-number cell 55.49%, so its
1.607 points is genuinely **1.61×** the 1.000 required, not 1.49×.

**2. The Gaussian's conservatism was accidentally offsetting prediction error.**
For MOVE_COMBINED, mean |m| = 1.610 points:

```
Gaussian implied   53.53%      EXACT implied   54.60%      REALISED   53.44%
```

The Gaussian was nearly exact and the empirical CDF **overshoots by 1.2pp**.
The reason: |m| is a *predicted* move, and a noisy prediction of 1.6 points
delivers less than 1.6 points of true edge. The conversion assumes you actually
get the points.

## Practice going forward

- Use the **exact empirical CDF**, not `φ(0)/σ`, and state which market —
  spreads and totals differ by nearly 2× in points-required.
- Never convert a **predicted** quantity as though it were a realised shift;
  report both the conversion and the realised rate, and prefer the realised.
- Check whether the effect sits **at the line** before converting at all.
- 1H work may use the Gaussian; full-game work should not.

---

# Moneylines — audit 2026-08-29

n = 9,486 two-sided closing moneylines, mean overround 4.18%. Vig-free
`p_home = imp(ML_H) / (imp(ML_H) + imp(ML_R))`.

## The book prices margins as Gaussian, and the SCALE is right

Recovering the σ each (spread, ML) pair implies under `p = Φ(−spread/σ)`:

```
book's implied sigma   median 13.20   IQR 12.20 - 14.84
REALISED margin sd                    13.24
```

That is a near-exact match. Whatever the book is doing, its scale is correct.

## But margins are mildly leptokurtic, and σ is near-constant

| \|spread\| | n | sd | skew | exc. kurtosis | JB p |
|---|---|---|---|---|---|
| 0–2 | 914 | 13.84 | −0.063 | +0.376 | 0.050 |
| 2–5 | 3,040 | 13.34 | −0.011 | +0.337 | 7.2e-04 |
| 5–8 | 2,515 | 13.12 | −0.033 | +0.607 | 3.3e-09 |
| 8–12 | 2,039 | 12.93 | +0.048 | +0.543 | 2.5e-06 |
| 12+ | 978 | 13.24 | +0.140 | +0.742 | 2.8e-06 |

Normality is rejected in four of five buckets — mild fat tails throughout.
**σ is essentially flat (12.93–13.84)** and if anything *decreases* slightly
with favourite size, which is the opposite of the naive expectation that
mismatches are more variable.

## The trap: a naive Gaussian map misprices the extremes by more than the vig

| spread bucket | n | ACTUAL win% | Gaussian σ=13.24 | book ML | Gaussian err | ML err |
|---|---|---|---|---|---|---|
| home fav 10+ | 1,219 | 86.05% | 83.24% | 85.86% | **−2.81pp** | −0.19pp |
| fav 6–10 | 1,735 | 73.43% | 72.68% | 74.14% | −0.75pp | +0.71pp |
| fav 3–6 | 1,651 | 64.26% | 63.78% | 63.36% | −0.48pp | −0.90pp |
| fav 0–3 | 1,238 | 54.36% | 56.16% | 54.44% | +1.79pp | +0.07pp |
| dog 0–3 | 970 | 47.32% | 44.56% | 46.41% | **−2.76pp** | −0.91pp |
| dog 3–6 | 1,223 | 37.78% | 37.51% | 38.18% | −0.26pp | +0.40pp |
| dog 6+ | 1,450 | 22.76% | 25.19% | 23.74% | **+2.43pp** | +0.98pp |

Brier: Gaussian 0.20532, book ML 0.20501.

**The Gaussian understates real favourites and overstates real longshots** —
fat tails produce more decisive games than a normal predicts. Max Gaussian
error **2.81pp** against a −110 vig of 2.381pp: **a naive Gaussian
spread→probability map manufactures a phantom edge on big favourites and big
dogs, larger than the hurdle it would have to clear.**

The book's own ML is within **~1pp everywhere**, consistent with `CLOSING.md`'s
"calibrated within 1.2pp". The book is *not* using a naive Gaussian — which is
why `CLOSING.md` also found the book's ML deviation from the spread carries
information (+0.78).

## Rule

**Never convert our own spread estimate to a win probability with a Gaussian.**
Use the empirical spread→win-rate mapping. The error is largest exactly where a
model would most want to bet — the extremes — and it exceeds the vig.

---

# Does the Kalshi totals LADDER reflect each game's distribution? — 2026-08-30

Everything above tested **marginal** calibration ("does 54% mean 54%?"). This
tests **distributional** calibration: does the ladder's implied CDF fit the
individual game? Store: `kalshi_nba_candles.sqlite`, KXNBATOTAL, last pregame
mid on each rung, **424 events** (2025-10-21 → 2025-12-22) joined to actual
totals.

## An error of mine, first

My initial PIT test scored interior games against Uniform(0,1) and returned
"NOT uniform, p = 0.0000" with quintiles [5, 77, 86, 74, 1]. **That was wrong by
construction** — interior games are *truncated* to the ladder's support, so
they cannot be uniform on [0,1]; the quintiles were just the ladder bounds. The
correct test rescales each game's PIT to its own ladder support. Recorded
because the wrong version looked like a decisive finding.

## Result — the ladder is well calibrated, on all three parts

**(a)(b) It prices its own tails:**

```
implied below lowest rung 21.2%    actual 20.8%    gap -0.4pp
implied above highest     23.2%    actual 21.9%    gap -1.2pp
```

**(c) Its interior shape is right.** PIT rescaled to each ladder's own support:

```
n = 243   KS = 0.0434   p = 0.7336   -> UNIFORM
mean 0.4997 (0.5 = unbiased)   sd 0.2990 (0.289 = uniform)
quintiles [50, 56, 38, 46, 53]   even = 49
```

**And it agrees with the sportsbook to within noise:**

```
mean(Kalshi implied line - book close)  -0.004 pts   sd 0.603   corr 0.9955
```

## So: yes — with two real caveats

**Caveat 1 — 12.1% of ladders are INCOHERENT as quoted.** In 52 of 428 events
`P(total > X)` does not fall monotonically in `X` at the mid. I
isotonic-projected them to run the test; **as quoted, one ladder in eight is not
a valid distribution.**

**Caveat 2 — the ladder only spans the central ~57%.** Median strike span is
30 points, with ~21% of mass below the lowest rung and ~23% above the highest.
**43% of games land outside the ladder entirely**, where it says only "above" or
"below" and nothing about how far. It is a well-calibrated middle plus two
lumps, not a full distribution.

## What this settles for the program

1. **The ladder is better calibrated than anything we have built.** Our
   forecaster returned calibration slope **0.43**; the ladder's PIT is uniform
   at **p = 0.73**. The market's distributional forecast is honest where ours
   is 2.3× overconfident.
2. **Efficiency holds at the distributional level, not just the mean.** That is
   a stronger statement than this program had previously established.
3. **It explains the bottom-rung result.** Buying cheap rungs lost 20–25% and
   near-certain rungs 5% *at the ask*, while the bottom rung was −0.67% *at the
   mid*. With the ladder now shown calibrated at the mid, that loss is
   **entirely the spread**, not mispricing — and the favourite-longshot pattern
   is a bid-ask artefact, not a bias to trade.
4. **No cross-venue level arbitrage.** Kalshi and the sportsbook are the same
   number to −0.004 points at corr 0.9955.

## Limits

424 games, one partial season ending at the December CDN wall; the interior PIT
is n = 243. KS at that n has roughly 80% power against a departure of
D ≈ 0.11; observed is 0.043. **Departures smaller than that are not excluded** —
this rules out gross shape error, not subtle miscalibration.

## CORRECTION 2026-08-30 — the "distributionally calibrated" claim is RETRACTED

Challenged on whether a pregame ladder could really match each game's
distribution. It cannot, and my test could not have told the difference.

### The PIT test was near-vacuous

Simulating a ladder whose assumed σ is wrong by a factor k, keeping only the
central 57% and rescaling as I did:

| true/assumed σ | 0.85 | 0.90 | 1.00 | 1.10 | 1.20 | **1.35** |
|---|---|---|---|---|---|---|
| rejection rate | 2% | 5% | 6% | 5% | 5% | **6%** |

**Even a 35% error in σ is rejected 6% of the time — no better than the 5%
false-positive rate.** Rescaling to the ladder's *own* quantiles normalises
away the dispersion being tested. The "KS 0.0434, p = 0.7336, UNIFORM" result
was not evidence of calibration; it was evidence of nothing.

### What DOES have power, and what it actually licenses

The **tail-mass** check is a real test. A σ error changes how much mass falls
outside a fixed strike range:

```
se of the tail fraction at n=424 is 2.4pp; 2-se is 4.8pp
-> it rejects sigma ratios outside roughly [0.90, 1.12]
OBSERVED: implied 43.5% vs actual 42.7%, gap -0.8pp
```

**Honest claim: the ladder's average σ is right to within about ±10%.** That is
all that survives, and it is a statement about the pooled average.

### The per-game question, answered directly — and the answer is NO

Fitting an implied σ per game (the ladder is almost exactly normal: median
corr(z, strike) = **0.99895**):

```
implied sigma   mean 19.51   sd 6.16   IQR 18.08-19.65
realised sd(actual - mu)     18.79          <- pooled average is close
```

But does a wider ladder predict a wider outcome?

```
|actual - mu| ~ implied_sigma    beta +0.1298 (t = +1.46)   corr +0.0711
(if the width carried real per-game information, beta would be ~0.8)
```

| implied σ quartile | mean implied σ | realised sd |
|---|---|---|
| 1 | 17.55 | 18.64 |
| 2 | 18.46 | 19.96 |
| 3 | 19.22 | 17.53 |
| 4 | **22.79** | 18.68 |

**Implied width spans 17.55 to 22.79 — a 30% range — and realised dispersion is
flat and non-monotone across it.** The ladder's per-game width variation is
**quoting noise, not information**.

### Corrected conclusion

The Kalshi totals ladder is **a fixed-shape normal template centred on the
sportsbook's line**:

| component | verdict |
|---|---|
| location | right, inherited from the book (corr 0.9955, −0.004 pts) |
| average width | right to ~±10% (19.51 implied vs 18.79 realised) |
| **per-game width** | **uninformative — β = +0.13, t = +1.46** |
| shape beyond scale (skew, kurtosis) | **untested** |
| coherence | **12.1% of ladders are non-monotone as quoted** |

**It does not reflect each game's distribution. It reflects the average game's
distribution, shifted to each game's line.** Earlier in this document, full-game
totals were shown to be right-skewed (+0.232, from the 5.13% overtime mixture)
and leptokurtic (+0.395) — a normal template captures neither.

### The lesson, which is the same one this session keeps producing

A test can pass because the thing is true, or because **the test cannot fail**.
`PREREG_ref_agency_dispersion` priced its MDE before running and reported a null
honestly. Here I ran a test *after* the fact without pricing its power, got a
clean p-value, and reported it as a finding. **The power calculation belongs
before the test, not after the challenge.**

## IS THE LADDER'S MISPRICING AN OPPORTUNITY? — tested 2026-08-30

The reasoning was sound: if the ladder is a fixed-shape normal template and
real distributions vary, the mismatch is tradeable. Two forms, tested in order.

### Form A — "predict per-game σ better than the ladder" — DEAD ON ARRIVAL

If true σ varies by game and the ladder uses a constant, forecasting σ wins.
**But per-game total variance is essentially unpredictable.** On 9,486 games:

| closing-total quintile | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| sd(dev) | 17.65 | 17.42 | 18.52 | 18.17 | 18.51 |

```
corr(line, |dev|)          +0.0207
|dev| ~ line + |spread|    R2 = 0.00047
fitted |dev| has sd 0.241 points on a mean of 14.29  -> 1.7% of its level
```

`|spread|` quintiles are flat too (18.52 → 17.92), mildly *decreasing*.

**True σ is near-constant, so a constant-σ template is the RIGHT model.** This
also corrects the framing above: the ladder's failure to adapt σ per game is
**not a deficiency** — there is nothing to adapt to.

### Form B — "fade the ladder's own σ noise" — real edge, unreachable

The ladder still quotes σ from 17.5 to 24.9 across quartiles while truth is
~18.8. Fading the wide ones has a genuine edge:

```
ladder sigma 17.5 -> top rung priced 21.5%, true 23.1%   edge -1.6pp
ladder sigma 19.5 -> priced 21.5%, true 20.6%            edge +0.9pp
ladder sigma 24.9 -> priced 21.5%, true 16.9%            edge +4.6pp
```

**But the wide-σ ladders are exactly the untradeable ones:**

| σ quartile | implied σ | median spread | **wing spread** | coherent |
|---|---|---|---|---|
| 1 | 17.52 | 3.78c | 3.96c | 94% |
| 2 | 18.44 | 4.32c | 5.55c | 93% |
| 3 | 19.22 | 6.03c | 7.20c | 94% |
| **4** | **24.87** | **13.16c** | **14.86c** | **70%** |

```
corr(implied sigma, median spread)  +0.5807
corr(implied sigma, wing spread)    +0.5685
```

**Edge +4.6c against a wing half-spread of 7.4c.** Negative, and the top
quartile is only 70% coherent.

### The finding that generalises

**A wide implied σ is not a pricing opinion — it is what a wide, incoherent,
illiquid ladder looks like when you fit a normal to it.** The apparent σ
dispersion is a **liquidity artefact**, not a mispricing.

This is now the third independent instance of one pattern on this venue:

| case | apparent edge | cost | outcome |
|---|---|---|---|
| derivative half-winners | 3–6c | 15–30c spread | dead |
| bottom rung | −0.67% at mid | −5.06% at ask | spread is the entire loss |
| **wide-σ ladders** | **+4.6pp** | **7.4c half-spread** | **dead** |

**On this venue the apparent mispricing is proportional to the spread**
(corr +0.58), which is exactly what you get when the "edge" is measured from
the midpoint of a quote nobody will trade at. **The mid of a 15c market is not
a price.**

**Standing rule added: never quote an edge computed from a mid without also
quoting the spread it sits inside.** Every mid-based edge in this program's
Kalshi work should be read with that attached.

### Form A, RE-TESTED at team level — the first version was mis-specified

Correct objection: regressing |dev| on the **line** and **|spread|** tests
whether dispersion scales with *market summaries*, not whether *these two teams*
produce a wider distribution. Team identity was never in the test. Redone, with
power priced first and an explicit search for exceptions rather than averages.

**Power, stated before the tests.** SE of a sample sd is σ/√(2n). At a median
80 games and sd 17.84, that is **1.406 pts** of noise per team-season estimate;
observed cross-estimate sd is 1.690, implying ~0.94 pts of non-noise dispersion.
**If team variance were perfectly stable, season-to-season correlation would
still only be ≈0.31** — and with 210 team-season pairs the MDE on a correlation
is ≈0.135, so 0.31 is detectable.

**Test 1 — persistence.**
```
adjacent seasons   corr(sd_t, sd_t-1) = +0.0709   perm p = 0.1488
era vs era         corr(sdA, sdB)     = +0.0458   perm p = 0.4095
team SCORING sd, era vs era           = -0.0292
```
Detectable stability is 0.31; observed is 0.07. **Full stability is excluded.**

**Test 2 — the operational test, which does not care why.** Prior-only rolling
60-game team dispersion, combined across the two teams:

| prior-sd quintile | mean prior sd | realised sd(dev) |
|---|---|---|
| 1 | 16.23 | 17.90 |
| 2 | 17.24 | 18.23 |
| 3 | 17.91 | 17.78 |
| 4 | 18.64 | 18.21 |
| 5 | **19.97** | **18.39** |

```
|dev| ~ combined prior team sd    beta +0.126 (t=+1.45)   corr +0.0153
informative prior variance would give beta ~0.8
se(beta) 0.087 -> MDE 0.170, far below 0.8: a WELL-POWERED null
```

A **23% spread in the predictor produces a 2.7% spread in the outcome**, and
non-monotone through the middle.

**Test 3 — the exception search, which is what was actually asked for.**

```
teams in the top 6 of BOTH eras:     1   [Houston]
teams in the bottom 6 of BOTH eras:  2   [Orlando, Phoenix]
expected by chance:                  1.2 each
```

**No team is reliably extreme beyond chance.** There are no exceptions to model.

### Why the premise is right and the conclusion still negative

Teams **do** differ in raw scoring variance. But the ladder is not priced
against raw scoring — it is priced against **the closing total, which is set per
game**. The line absorbs the predictable part. What remains is *residual*
dispersion, and that is homogeneous: every team's `actual − close` has sd near
17.8–18.4 regardless of style.

**The market's per-game line is doing the work a per-game σ would do.** That is
why a constant-σ template is not lazy — it is correct *conditional on the line*.

**This does not close the idea in general.** It closes it for team identity as
the conditioning variable, on total dispersion, at this power. A different
conditioner — one that moves residual dispersion rather than the mean — is not
excluded by anything here. Nothing in this program has found one.

---

# THE VARIANCE CHAIN — team -> matchup -> line -> ladder

Run 2026-08-30 in response to a correct objection: *"are you saying a fast break
team has the same confidence level in total points scored as a solid defense
team?"* No — and the earlier team-persistence framing was the wrong test. This
follows the quantity all the way to the traded instrument.

## Link 1 — teams DO differ, and it partly persists

Team points-scored sd by season, 30 teams x 8 seasons (`matchup_var.py`).
Ordering is roughly a pace ordering: Golden State, LA Clippers, Houston,
Milwaukee at the top (mean ~12.7); Cleveland, Phoenix, Detroit at the bottom
(~11.4).

```
cross-team sd of the sd estimates  1.072
noise floor  se(sd) = sd/sqrt(2n)  0.945    (80 games, sd 11.98)
=> TRUE dispersion 0.507 pts (4% of base)   reliability 0.223
mean adjacent-season r  +0.128   against a CEILING of 0.205 at this noise
```

**Correction to the previous section:** "does not persist" read the raw
correlation without pricing the reliability ceiling. +0.128 against a ceiling of
0.205 is ~62% of what is detectable. **Team scoring variance is real and partly
stationary.** The magnitude is ~4%.

## Link 2 — it does NOT survive the matchup

Leave-one-out team sd (no circularity), terciles, 9,489 games:

| bucket | n | sd(total) | sd(dev) |
|---|---|---|---|
| HH both high-variance | 1,055 | **20.07** | 17.64 |
| LL both low-variance | 939 | **20.02** | 17.44 |
| league | 9,489 | 20.73 | 18.06 |

```
HH/LL sd(total) ratio 1.0021  (SHRUNK prediction 1.0448)  F p=0.9471
HH/LL sd(dev)   ratio 1.0111                              F p=0.7295
POWER: MDE ratio 1.0642 -> UNDERPOWERED for its own prediction; not a knockout
```

Continuous version, all 9,489 games, which has the power the buckets lack:

```
dev^2 ~ combined team dispersion          beta +7.388 (t=+1.55)
dev^2 ~ combined dispersion + LINE  comb  beta +4.677 (t=+0.95)
                                    line  beta +1.209 (t=+2.28)
corr(combined team dispersion, LINE) = +0.2415
```

**The line beats team identity when both compete.** Volatile matchups already
get higher lines; the team estimate adds nothing on top.

*(HH and LL both sit BELOW mixed on sd(total) because mixed matchups pair
unequal teams, spreading their expected totals. An artifact of the unconditional
measure, not a finding — sd(dev) is the honest column.)*

## Link 3 — the line IS heteroskedastic, and I called it flat

```
dev^2 ~ close   beta +1.3301 (t=+2.59)   HETEROSKEDASTIC
top-2 vs bottom-2 decile variance ratio 1.0997 (F p=0.0392)
sd ratio 1.0487   Poisson predicts 1.0656
```

Deciles run 17.58 @ line 206.0 to 19.01 @ 241.5. **The earlier "flat" reading
used the game-level correlation on |dev| (0.02), where per-game noise swamps a
conditional-variance effect.** Real dispersion scales with the line at close to
the Poisson rate.

## Link 4 — SO DOES THE LADDER. The trade does not exist.

1,310 Kalshi ladders (2025-26 only), probit fit `z = Phi^-1(1-mid) = (K-mu)/sig`,
median 11 rungs (`ladder_sigma.py`, `ladder_match.py`):

```
implied_sigma ~ implied_mu   slope +0.06061 (t=+14.09)  CI [+0.05218,+0.06904]
POISSON benchmark                  +0.03962
TRUE, full 9,489-game sample       +0.04030
```

**The hypothesis under test was that the ladder prices a CONSTANT sigma. It does
not.** It scales, decisively, and ~50% more steeply than either benchmark.

Matched to finals, 1,305 games:

```
implied mu vs sportsbook close   corr +0.9968   mean diff +0.125
mean implied sigma 18.218   vs   REALISED sd(total - mu) 18.265
=> ladder too narrow by 0.047 pts (0.3%)
```

| implied-mu quintile | n | mean mu | ladder sig | REALISED sd | ±noise | gap |
|---|---|---|---|---|---|---|
| 1 | 261 | 217.7 | 17.266 | 16.908 | 0.740 | +0.358 |
| 2 | 261 | 225.7 | 18.091 | 18.253 | 0.799 | −0.162 |
| 3 | 261 | 230.3 | 18.509 | 18.329 | 0.802 | +0.180 |
| 4 | 261 | 234.6 | 18.475 | 18.091 | 0.792 | +0.384 |
| 5 | 261 | 241.1 | 18.749 | 19.605 | 0.858 | −0.857 |

**Every gap is inside its own noise band and there is no monotone pattern.**

### Why the over-scaling cannot be traded, stated as power

```
ladder slope implies d(sig^2)/dmu = 2.208;  true/Poisson implies 1.468
observed dev^2 ~ mu   beta +3.044 (t=+1.94)   se 1.567
gap to distinguish 0.740 -> need se < 0.378 -> NOT RESOLVABLE
GAMES NEEDED ~ 22,491   (18 seasons of Kalshi ladders; we have ONE)
```

The point estimate (+3.044) is if anything *steeper* than the ladder prices, but
the standard error admits everything from 0 to 6.

Artifact checks: corr(quoted spread, mu) +0.162, corr(n rungs, mu) +0.032,
corr(probit residual, mu) +0.038. Mild spread/line correlation, nothing that
manufactures the slope.

## Disposition

The premise was right at every link that could be checked and the market absorbs
it at every link that matters. Teams differ in scoring variance (4%, partly
stationary); it does not survive matchup aggregation; residual dispersion scales
with the LINE instead, at the Poisson rate; **and the Kalshi ladder already
scales its sigma with the line and lands within 0.3% of realised dispersion.**

**Nothing here is tradeable, and the binding constraint is data, not logic.**
The one open question — whether the ladder's steeper-than-Poisson slope is an
error — needs ~22,500 ladders. That is a reason to keep collecting Kalshi
ladders through 2026-27, not a reason to trade.

**Method note.** Two power errors of the same kind were made and corrected in
this section: reading a persistence correlation without its reliability ceiling,
and reading a conditional-variance effect off a game-level correlation on
|dev|. Both understated a real effect. Conditional-variance questions must be
tested on `dev^2` with the noise floor priced first.

## Link 4b — THE QUESTION THAT WAS ACTUALLY ASKED

Link 4 tested implied sigma against **the line**. The question was whether the
ladder widens for **high-variance matchups** — a different conditioner, and the
one that matters. Run on `ladder_matchup.py`, regular season only.

**Why this is answerable where Link 4 was not.** Realised variance on 1,151
games is hopeless (Link 4: ~22,491 needed). But implied sigma is a *fitted*
quantity off 11 rungs, not one noisy draw, so **what the ladder BELIEVES is
measured precisely even when what is TRUE is not.**

```
bucket             n_lad   LADDER sigma   mean mu  |  n_all   REALISED sd(dev)
HH both high-var     121        18.344      231.2  |   1006         17.565
LL both low-var      118        18.272      229.6  |    981         17.358
ALL games          1,151        18.299      230.7  |   9,489        18.065

LADDER  HH-LL implied sigma  +0.0719  (t=+0.34, p=0.7352)   MDE 0.4163 pts
REALITY HH/LL sd ratio        1.0119  (F p=0.7087)
```

```
implied_sigma ~ comb + implied_mu    comb +0.0126 (t=+0.32)   mu +0.0426 (t=+8.75)
dev^2        ~ comb + close          comb +4.6775 (t=+0.95)   close +1.2086 (t=+2.28)
```

**The ladder loads on the line and NOT on matchup variance — and neither does
reality.** Same structure on both sides.

### This one IS well powered, unlike Link 4

MDE on the ladder's HH-LL gap is **0.42 pts**. A ladder that naively ADDED team
variances — HH teams measure ~13.2 sd, LL ~10.8, so sqrt(2)*13.2 = 18.7 against
sqrt(2)*10.8 = 15.3 — would show a gap of **~3.4 pts**. Observed +0.07 +- 0.42.
**Naive variance-adding is excluded by ~8x.**

The market maker applies the shrinkage the data demands: measured team variance
is 78% noise (reliability 0.223), so the correct response is to nearly ignore
it, and the ladder nearly ignores it.

### A BUG CAUGHT BY CONTRADICTION — recorded, not buried

The first run of this test reported HH/LL realised ratio **1.2472 (p=0.0000)**,
contradicting `matchup_var.py`'s 1.011. Cause: **the ladder script omitted the
regular-season filter**, pulling in 894 playoff games where the same two teams
repeat 4-7 times and load the buckets. With the filter restored the ratio is
1.0119 (p=0.7087) and the two runs reconcile exactly.

It would have been reported as a real finding had it not contradicted an earlier
result. **The close-range filter excludes zero rows in this master; the
regular-season filter is the one that does the work** — the same universe-filter
class of defect recorded in `PREREG_crewshock_forward` §2.

## Link 5 — PACE. The right variable, and the market is already on it.

`total = pace x efficiency`, and Poisson says variance tracks **possessions**,
not points. Two games with the same 230 total — one at 105 possessions, one at
95 — should carry different sigma, and a ladder priced off the line alone would
give them the same one. Prior-only pace: `shift(1).rolling(20, min_periods=10)`
within season, both teams required (`pace_var.py`, `pace_ladder.py`,
`pace_inter.py`). Regular season, 8,236 games.

**Stage 0 — there is real orthogonal variation, so the test is well posed.**

```
exp_pace mean 98.77  sd 1.771  range 92.3..105.9
corr(exp_pace, closing line) +0.6482 -> R2 0.420, 58% of pace is ORTHOGONAL
residual pace sd given the line = 1.349 possessions
```

### Do high-pace games have wider distributions? YES.

```
dev^2 ~ exp_pace                        +7.703 (t=+2.42)
LADDER high-pace minus low-pace sigma   +0.5300 (t=+7.33, p<0.0001)
```

### And the ladder prices it at the POISSON RATE

```
implied_sigma ~ exp_pace + implied_mu   pace +0.0888 (t=+2.97)  mu +0.0229 (t=+3.55)
POISSON  d(sigma)/d(pace) = v/sigma =        +0.0911
95% CI on pace [+0.0303, +0.1474]  -> Poisson is INSIDE
MDE 0.0585 < 0.0911                -> POWERED to have said otherwise
```

**Point estimate within 2.5% of theory, on a test that could have rejected it.**

**And PACE is the carrier, not the line.** The `mu` coefficient falls from
+0.0426 (Link 4) to +0.0229 once pace enters. The market is conditioning its
dispersion on the physically correct variable and the line was proxying for it.
Monotone within every line tercile: 17.706→17.852, 17.924→18.260, 18.191→18.579.

### The one apparent exception, and why it is not tradeable

Reality and the ladder appear to diverge by line tercile:

| | T1 (low totals) | T2 | T3 (high totals) |
|---|---|---|---|
| LADDER high−low | +0.146 | +0.336 | +0.388 |
| REALITY with OT | −0.554 (t=−1.19) | +0.760 | +1.233 (t=+2.46) |
| REALITY no OT | −0.887 (t=−1.92) | +0.424 | +1.402 (t=+2.86) |

Formal interaction, the single pre-specified version of that 6-look pattern:

```
REALITY  dev^2 ~ pace*close   with OT   ix +0.4168 (t=+1.50)
                              no OT     ix +0.7938 (t=+3.46)  CI [+0.34,+1.24]
LADDER   implied_sigma ~ pace*close     ix +0.0030 (t=+1.30)
```

**Three reasons it does not survive.**

1. **KALSHI SETTLES INCLUDING OVERTIME.** The traded outcome is the with-OT
   row, and there the interaction is **t = +1.50**. The t=+3.46 is on an
   outcome nobody can bet.
2. **The OT exclusion is a precision gain, not a confound removal.**
   `corr(exp_pace, is_ot) = +0.0031` — pace does **not** predict overtime. OT is
   5.0% of games at sd(dev) 19.77 vs 17.10, so dropping it removes variance
   roughly at random in pace and inflates `t` without changing what settles.
3. **It is one season.** No-OT interaction by season: −0.30, −0.16, **+3.35
   (t=+3.26)**, +0.50, −1.05, +0.39, +0.47, +1.54. Positive in 5 of 8; the only
   significant season is **2020**, the bubble. With OT the signs flip harder
   still, with 2020 at +2.40 (t=+2.13) and 2022 at −4.37 (t=−2.61) —
   significant in OPPOSITE directions. This is exactly
   `papers/winkelmann_efficiency_simulations` — efficient markets throw
   significant season-by-season findings most of the time.

### Disposition

**The question was good and the answer is the strongest market result in this
audit.** High-pace games do have wider distributions; the ladder knows it, uses
possessions rather than points to say so, and lands within 2.5% of the Poisson
rate on a powered test. The pace x total interaction is not tradeable: absent on
the traded outcome, and carried by one anomalous season on the untraded one.

Recorded so it is not re-run: the pooled reality test on `dev^2 ~ exp_pace +
close` is **UNDERPOWERED** — Poisson predicts +3.284, MDE is 8.187 (2.5x short).
Reality cannot confirm or refute the pooled pace rate on 8,236 games. Only the
LADDER side is powered, for the Link 4b reason: implied sigma is fitted off 11
rungs, a realised total is one draw.

## Link 6 — EFFICIENCY VARIANCE via SHOT MIX. The first candidate within reach.

Prompted by: the ladder's pace loading is a tell that it may be doing a
*pace-only* job. `total = pace x efficiency`, and Link 5 only tested pace.
(`eff_var.py`, `eff_ladder.py`)

### Stage 0 — 3PA RATE is the first well-measured conditioner in this audit

```
efficiency sd (a VARIANCE)   adjacent-season r +0.1520   noise floor 0.8731 vs sd 1.0154
3PA rate      (a MEAN)       adjacent-season r +0.5941   range 0.262 .. 0.535
```

**A mean escapes the 78%-noise problem that killed every variance estimator
here.** 3PA rate is ~4x more persistent than any dispersion measure tried, and
it is **99% orthogonal** to pace and the line — it is not a proxy for either.

It also carries a computable prediction rather than a fitted one:

```
var per 3PA  9*.36*.64 = 2.074      var per 2PA  4*.53*.47 = 0.996
excess 1.077 per shot converted;  combined FGA 176.8; matchup range 0.183
=> d(sigma)/d(3PArate) = FGA*(v3-v2)/(2*sigma) = 5.31   ~= 0.97 pts of sigma
```

### The ladder prices it, and the test was powered

```
implied_sigma ~ 3PArate + pace + mu   t3r +3.259 (t=+2.98)  pace +0.098 (t=+3.29)  mu +0.023 (t=+3.62)
95% CI on 3PA [+1.11, +5.41]   prediction +5.31 INSIDE    MDE 2.15 -> POWERED
```

**The ladder loads independently on pace AND on shot mix**, both physically
correct, neither a proxy for the other. That is not a market pricing off the
total.

Oddity, flagged not interpreted: `implied_sigma ~ prior_eff_SD + pace + mu`
gives **esd −0.063 (t=−2.41)** — the ladder gives NARROWER sigma to matchups
whose teams were recently more volatile. Since `prior_eff_SD` is ~86% noise it
is probably proxying something else (quality, mean reversion). Not a finding.

### The gap, and the economics of it

The point estimate is 3.259 against a predicted 5.31 — **61% of it**. If that
shortfall is real, sigma is mispriced by 0.375 pts across the 3PA range (1.04%
of sigma):

| rung | ladder P | true P | edge | taker fee | maker fee | net taker | net maker |
|---|---|---|---|---|---|---|---|
| 1.00σ | 15.87c | 16.12c | 0.25c | 0.93c | 0.23c | **−0.68c** | +0.02c |
| 1.50σ | 6.68c | 6.88c | 0.20c | 0.44c | 0.11c | **−0.23c** | +0.09c |
| 2.00σ | 2.28c | 2.39c | 0.11c | 0.16c | 0.04c | **−0.04c** | +0.07c |

**Taking is negative-EV at every rung. Only MAKING is positive, at 0.02–0.09c** —
which puts it inside the already-registered liquidity-provision family, not a
new forecasting edge.

### THE DISTINCTION THAT DECIDES THIS — two different n's

```
resolve whether the LADDER SLOPE differs from 5.31   ~1,101 games  (HAVE 1,002)
resolve whether REALITY matches the prediction       ~18,712 games (~15 seasons)
```

**We are 99 ladders short of the first and 15 seasons short of the second, and
only the second establishes money.** Matching the ladder against 5.31 tests the
ladder against *a binomial model of mine*, not against outcomes. That model
assumes independent shots; real shooting is correlated within a night, which
pushes true variance **above** the binomial figure — so 5.31 is a floor with its
own error bars, and "the ladder is at 61% of it" may be a defect in the
benchmark rather than in the ladder.

### Disposition

**The reasoning was right and produced the best candidate in the audit**: a
persistent, precisely-measured, 99%-orthogonal conditioner that the ladder loads
on less than theory says it should. It is nonetheless **not an established edge**
— the CI contains the prediction, taking is negative-EV at every rung, and the
arbiter (realised outcomes) needs ~15 seasons.

**One operational consequence, and it is cheap:** ~99 more ladders resolves the
slope question. The collector already runs. This is the first item in the audit
where continuing to collect has a defined payoff and a near-term date, which is
a reason to keep the 2026-27 ladder collection running — **not** a reason to
trade, and any trade would require its own pre-registration.

## Link 6b — THE BENCHMARK, MEASURED. My caveat was wrong in direction.

Link 6 rested on a benchmark I *assumed*: `9p(1-p)` per 3PA, which presumes
independent shots. I flagged that real shooting is correlated within a night,
so 5.31 was "a floor with its own error bars." **Measured, that is false.**
(`shot_corr.py`, 18,977 team-games, identity `2*2PM+3*3PM+FTM == PTS` exact on
100.0%.)

### Within-team-season overdispersion — cross-team quality removed

Measured *within* team-season, or cross-team shooting-quality differences
masquerade as within-game correlation.

| shot | p_hat | mean n | phi (dispersion) | **rho (ICC)** | var/attempt | binomial |
|---|---|---|---|---|---|---|
| 3PT | 0.3602 | 34.3 | **0.9883** | **−0.00035** | 2.0499 | 2.0742 |
| 2PT | 0.5346 | 54.1 | 1.0583 | +0.00110 | 1.0532 | 0.9952 |
| FT | 0.7767 | 22.3 | 1.1219 | +0.00571 | 0.1946 | 0.1734 |

**Three-point shooting is essentially exactly binomial — very slightly UNDER-
dispersed.** The "hot night" does not exist at the team-game level for threes.
FT carries the most dispersion (+12%), which is player-mix, not a hot hand.

### A hot night is not hot everywhere

Correlation of standardised within-game residuals:

```
        3PT     2PT      FT
3PT  1.0000 -0.0189  0.0108
2PT -0.0189  1.0000  0.0010
FT   0.0108  0.0010  1.0000
```

**All three cross-channel correlations are ~zero, and 3PT-2PT is NEGATIVE.**
The intuition behind my caveat is not in the data.

### Validation of the rebuilt variance

```
per-team shooting variance, attempts FIXED  -> sd 11.39
DIRECT within-team-season sd of team points -> 11.95   (larger, as it must be: includes attempts)
two independent teams, shooting only        -> 16.10   vs OBSERVED sd(dev) 18.06
```

Both inequalities point the right way; the 18.06 vs 16.10 residual
(sqrt(18.06^2-16.10^2) = 8.19 pts) is pace/attempt variation, line error and OT.
The variance model reproduces the observed scale.

### The corrected benchmark, and what it does

```
excess var per shot converted 2->3   BINOMIAL 1.0790  ->  CORRECTED 0.9967  (0.92x)
d(sigma)/d(3PArate)                  BINOMIAL 5.27    ->  CORRECTED 4.87
LADDER MEASURED +3.259  95% CI [+1.11, +5.41]  -> BOTH benchmarks INSIDE
```

**The correction moves the benchmark DOWN, not up.** The ladder is at **67%** of
the corrected figure rather than 62% of the binomial one, and the residual gap
is `4.87 - 3.259 = 1.61` against `se 1.10` — **t = 1.46, not significant.**

### And the corrected gap is HARDER to resolve, not easier

| benchmark | shortfall | sigma error | n to resolve |
|---|---|---|---|
| binomial (wrong) | 2.01 | 0.368 pts (1.02%) | 1,152 |
| **CORRECTED** | **1.61** | **0.295 pts (0.81%)** | **1,795** |

Link 6's "99 ladders short" was an artifact of the wrong benchmark. The honest
figure is **~1,795 games against the 1,002 held — about 0.6 more seasons**, which
2026-27 does supply. Economics at the corrected gap are marginally worse: taking
negative at every rung (−0.74c to −0.07c), making −0.04c at 1.0σ and +0.05c at
1.5σ and 2.0σ.

### Disposition

**The benchmark is now measured rather than assumed, and the finding is that the
ladder's shot-mix loading is NOT significantly below the physical rate
(t = 1.46).** Link 6's candidate weakens: the gap shrank, its significance is
absent, and the data required grew by 56%.

What was actually gained is a **correct** benchmark and a validated variance
decomposition, plus a substantive negative result worth its own line: **NBA team
three-point shooting is binomial within a season, and shooting channels are
uncorrelated within a game.** Any future variance model in this program should
assume independence rather than fitting a hot-hand term.

**Recorded as a reasoning error:** I hedged Link 6 with a mechanism (within-night
correlation) that I had not measured and that turned out to run the other way.
The hedge was stated as a caution, which made it feel safe, but it was an
unmeasured empirical claim doing load-bearing work.
