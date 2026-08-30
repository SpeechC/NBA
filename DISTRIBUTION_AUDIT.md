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
