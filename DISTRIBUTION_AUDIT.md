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
