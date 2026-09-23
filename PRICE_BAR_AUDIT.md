# THE BAR IS PRICE-DEPENDENT, AND THE PRICE IS IN THE FILE (2026-09-13)

The standing mechanism-test bar — 0.79 pts for spreads, 1.079 pts for totals — is
computed at **an assumed -110**. `DATA_DICTIONARY.md` §4 flagged the juice strings as
"the most valuable unused data in the file" and "-110 vs -105 is the single largest
lever on profitability." They are still unused. This prices what that omission costs.

## 1. The bar moves more with price than with anything I have found in a signal

`sd(dev) = 18.06` for totals. Points of edge needed = `sd x Phi^-1(break-even)`:

| price | break-even | pts needed (totals) |
|---|---|---|
| -115 | 53.488% | **1.581** |
| -110 | 52.381% | **1.079** |
| -108 | 51.923% | 0.871 |
| -105 | 51.220% | **0.552** |
| -102 | 50.495% | 0.224 |

**-110 to -105 halves the bar.** Every signal measured in this project's totals work
sits in a 0.37-0.88 point band — which straddles those bars. The same signal is dead
at -110, marginal at -108, and profitable at -105.

## 2. The recorded price is not -110 on half the sample

`CLOSING\nODDS_H` is `line juice`, juice in two-digit shorthand (`-05` = -105).
Restricting to rows whose first token is a TOTAL (the column is polymorphic — see
`DATA_DICTIONARY.md` §1), n = 2,779:

```
-110  1,303 (47%)     -112  438     -108  384     -109  333
-115    106           -113   95     -105   90     -118    6
```

**53% of games are not at -110. 29% are priced BETTER than -110.** The project has
been scoring every one of them against a -110 bar.

This cuts both ways and is not a free edge: if a signal's selected games happen to be
the -115 ones, the bar rises to 1.581 and results get *worse*. The point is that the
bar is a per-game quantity that has been treated as a constant.

## 3. What it does to the totals results

Best measured edges, and what they pay (`hit = Phi(edge/sd)`):

| edge | hit rate | ROI at -110 | ROI at -105 |
|---|---|---|---|
| 0.367 (shot volume, 2022-26, at the close) | 50.81% | -3.00% | -0.80% |
| 0.594 (pace `f_P`, 2022-26, at the close) | 51.31% | -2.04% | **+0.18%** |
| 0.673 (shot volume, full sample) | 51.49% | -1.71% | **+0.52%** |
| 0.848 (`f_spp` + `f_P` jointly, full sample, in sample) | 51.87% | -0.97% | **+1.27%** |
| 0.880 (referee crew, extrapolated) | 51.94% | -0.84% | **+1.41%** |

`corr(f_spp, f_P) = -0.0799` — the two signals are essentially orthogonal, so they do
combine: joint edge **0.848 pts full sample, 0.751 pts in 2022-26**. That is 79% and
70% of the -110 bar, and **153% and 136% of the -105 bar**.

## 4. Three reasons this is not a strategy yet

1. **Those are in-sample edges.** Walk-forward, every model in
   `TOTALS_MAD_DECOMPOSITION.md` §4 and `SHOT_VOLUME_PBP.md` §5 lands at 50-52% with
   nothing significant at any threshold. The fitted-prediction trap is documented in
   `TOTALS_MAD_DECOMPOSITION.md` §4 and it inverts exactly this kind of number.
2. **A -105 price and this closing line are probably not available together.** The
   edges are measured against BigDataBall's closing total. Reduced juice usually means
   a sharper book, whose closing number would already contain more of the signal. The
   two levers are not independent, and assuming they are is the same error as pricing
   a fill at the candle ask.
3. **The juice recorded is one side's.** `223.5u -05` prices the under at -105, which
   implies the over near -115. You do not get to choose the cheap side after seeing
   the signal; the side the signal wants may be the expensive one.

## 5. What to actually do

**Re-run the standing mechanism test at the recorded price rather than at -110.**
Free, needs no new data, and it is a per-game bar instead of a constant. Specifically:

1. Parse `OPENING ODDS` / `CLOSING\nODDS` with the §1 polymorphism gate, keep the
   totals-side rows, and attach the price to each game.
2. Recompute every totals result against `sd x Phi^-1(|price|/(|price|+100))` per game.
3. Report the joint distribution of (signal edge, price). The question that decides
   everything is whether the games where the signal is strongest are also the games
   priced near -110 or better — **if the signal concentrates in high-juice games it is
   worth less than measured, and if it concentrates in low-juice games it is worth
   more.** Nobody has looked.
4. Only then ask whether a -105 venue's own closing line still leaves the edge.

**And update the standing screen.** `nba-betting-systems-tested`'s 0.79-pt spread bar
carries the same -110 assumption and should be restated as a function of price.

---

# RESULT — THE RERUN, AND IT GOES THE WRONG WAY (2026-09-13)

§5 is done. **The -110 assumption was mildly optimistic, not conservative. The true
bar is 1.123 pts, 4.1% HIGHER than the 1.078 every result in this project has been
scored against.** The price lever is real — the bar does swing 0.22 to 1.58 pts — but
this book's price distribution does not deliver it.

## The parse, validated

`OPENING ODDS` / `CLOSING\nODDS`: exactly one of `_H`/`_R` holds the total and the
other the spread (crosstab 5,788 / 3,615, plus 3 corrupt both-total rows). The `o`/`u`
marker names the priced side; the juice is two-digit shorthand with the leading 1
dropped (`-05` = -105, `-00` = -100, `+05` = +105).

```
parsed line == CLOSING TOTAL_H  on 99.99% (1 mismatch, the known -110 corrupt cell)
parsed line == OPENING TOTAL_H  on 100.00%
side marker present 76.2%,  juice present 76.1%  -> 7,158 usable games
```

**Only one side is priced per game.** Results are reported exactly where the signal's
side is the recorded one, and with a modelled complement
(`juice_other ~ 2 x (-110.35) - juice_recorded`) elsewhere. The model is an assumption
about the hold split, stated as such.

## Selection checks — clean, with one live finding

```
mean dev by recorded side      over +0.545 vs under +0.352,  t +0.44     clean
P(over) by recorded side       0.498 vs 0.505                            clean
juice ~ |dev| (the outcome)    t -0.84                                   clean, no leakage
match rate by outcome          won 0.524 vs lost 0.528                   clean
juice ~ CLOSING TOTAL          t +6.32   \  the price DOES know about the signal:
juice ~ f_spp                  t +3.84   /  joint F p = 0.0005
```

The last two matter and are new: **higher-total games are priced cheaper**, and
`f_spp` correlates with the total, so the signal is not independent of the price.

## The question that decided it

Is the signal stronger in cheap games or dear ones? Neither, usefully:

| juice bucket | n | edge pts | bar | **edge / bar** |
|---|---|---|---|---|
| ≤ -113 (dear) | 681 | 1.284 | 1.490 | 0.86 |
| -112 / -111 | 1,687 | 0.153 | 1.278 | **0.12** |
| -110 | 3,129 | 0.886 | 1.078 | 0.82 |
| -109 … -102 (cheap) | 1,661 | 0.545 | 0.854 | 0.64 |

**No bucket clears its own bar, and there is no monotone pattern.** The cheap bucket
is the second *worst*.

## Walk-forward, priced per game

Joint `f_spp + f_P`, coefficients from prior seasons only:

| threshold | n | hit | break-even | mean price | **ROI at actual price** | z | ROI at assumed -110 |
|---|---|---|---|---|---|---|---|
| 0.0 | 6,940 | 50.81% | 52.46% | -110.4 | **-3.16%** | -2.76 | -3.00% |
| 0.5 | 4,776 | 51.32% | 52.47% | -110.4 | -2.19% | -1.59 | -2.03% |
| 1.0 | 2,905 | 52.39% | 52.47% | -110.4 | -0.15% | -0.09 | +0.02% |
| 1.5 | 1,591 | 51.60% | 52.48% | -110.5 | -1.68% | -0.70 | -1.49% |
| 2.0 | 774 | 54.01% | 52.48% | -110.4 | +2.95% | +0.85 | +3.10% |

**The actual price is worse than -110 at every threshold.** Nothing is significant.

Why: the juice distribution is asymmetric against the bettor —
**2,368 games priced worse than -110 against 1,662 priced better** (-112 alone is
1,615; -105 is 220).

## The "bet only cheap games" filter fails on sample size

| filter | bets kept | hit | break-even | ROI | z |
|---|---|---|---|---|---|
| price ≥ -110 | 48% (1,397) | 53.33% | 52.14% | +2.27% | +0.89 |
| price ≥ -109 | 25% (712) | 53.09% | 51.91% | +2.26% | +0.63 |
| price ≥ -108 | 13% (374) | 53.21% | 51.73% | +2.82% | +0.57 |
| price ≥ -105 | 2% (56) | — | — | — | — |

**n falls faster than the bar does.** Every ROI is positive and no z reaches 1.
Control: the same filter with a **random** signal gives 50.047% ± 1.243 — the filter
is not itself an edge, which is the right result, but it also cannot supply sample.

## Verdict

The price lever exists and was worth measuring — the bar genuinely ranges 0.22 to
1.58 points and the project had been treating it as a constant. **But the correction
runs against us: the true bar is 1.123, not 1.078, and every totals result in this
project is 4% worse than reported, not better.** The cheap games are neither numerous
enough nor signal-rich enough to harvest.

**What this does NOT close.** These are one book's prices. A genuinely reduced-juice
venue (a -105 market) would have a different price distribution *and* a sharper
closing line, and the two move together. Testing that needs that venue's lines, which
this project does not have — and `kalshi-nba-microstructure` already shows the
exchange analogue: on Kalshi, taking pays the fee twice and only **making** is
positive-EV. **The price lever, if it is anywhere, is in being the maker, not in
shopping for -105.**

**Update the standing screen:** quote the totals bar as **1.12 pts** (measured), not
1.079 (assumed). `nba-betting-systems-tested`'s 0.79-pt spread bar needs the same
correction — the spread-side juice is in the same columns and has not been parsed.

---

# SPREAD SIDE — THE JUICE PARSED AND THE 0.79 BAR FIXED (2026-09-13)

**The corrected spread bar is 0.81, not 0.79.** Same direction as the totals side and
about half the size: the standing screen was optimistic by 2.0%.

## The parse — 100.00% validation

Whichever of `_H`/`_R` does not hold the total holds the spread, and which column it
lands in tells you whether the price is the home or the road side.

```
spread quote found on   9,375 / 9,404 games (99.7%)
parsed line == the matching side of CLOSING SPREAD_H on   100.00%
recorded side   home 5,771   road 3,604
juice present   86.5% of quotes  ->  8,114 team-games priced exactly
```

## Spread juice is far more dispersed than totals juice

| price | n | share | bar (pts) |
|---|---|---|---|
| -120 | 21 | 0.3% | 1.510 |
| -118 | 94 | 1.2% | 1.371 |
| -115 | 782 | 9.6% | 1.158 |
| -114 | 292 | 3.6% | 1.086 |
| -113 | 160 | 2.0% | 1.013 |
| -112 | 1,825 | 22.5% | 0.939 |
| **-110** | **2,441** | **30.1%** | **0.790** |
| -109 | 145 | 1.8% | 0.714 |
| -108 | 1,028 | 12.7% | 0.638 |
| -107 | 101 | 1.2% | 0.561 |
| -106 | 145 | 1.8% | 0.483 |
| -105 | 774 | 9.5% | 0.404 |
| -102 | 127 | 1.6% | 0.164 |

**Only 30.1% of spreads are at -110** (against 43.7% of totals), and the bar ranges
**0.16 to 1.51 points** across games. But the distribution again skews against the
bettor: **40.9% priced worse than -110 against 29.0% better.**

```
sd(cover) = 13.228   (regular season, 4 corrupt spread cells dropped; memory's 13.32
                      includes playoffs — on THIS sample the -110 bar is 0.7899, so the
                      comparison below is like-for-like)

standing screen, assumed -110            0.7899 pts
MEASURED, mean actual price -110.24      0.8057 pts      <-  quote 0.81
```

## The mechanism-test conclusion does not change

Re-scored against each spot's own mean bar (18,808 team-games; convention check —
home cover 49.53%, push 1.68%):

| spot | n | mean cover | t | bar (actual) | **edge / bar** |
|---|---|---|---|---|---|
| 5+ ATS loss streak | 548 | +0.989 | +1.80 | 0.813 | **1.22** |
| home dog +3 to +7 | 1,669 | +0.379 | +1.20 | 0.797 | 0.48 |
| 4+ SU loss streak | 1,707 | +0.377 | +1.17 | 0.810 | 0.46 |
| B2B road favourite | 602 | -0.248 | -0.46 | 0.781 | 0.32 |
| B2B + 3rd in 4 | 2,467 | -0.250 | -0.92 | 0.809 | 0.31 |
| road trip 3+ AND b2b | 621 | +0.179 | +0.33 | 0.788 | 0.23 |
| home dog +3 to +5 | 1,017 | +0.143 | +0.36 | 0.780 | 0.18 |
| road-trip game 4+ | 1,315 | +0.114 | +0.32 | 0.806 | 0.14 |
| B2B (all) | 3,396 | -0.094 | -0.41 | 0.808 | 0.12 |
| road-trip game 3+ | 2,738 | -0.016 | -0.06 | 0.801 | 0.02 |

Only `5+ ATS loss streak` exceeds its bar, at **t +1.80** — the same spot
`nba-betting-systems-tested` already recorded as the one non-significant positive
(53.90%, z +0.72). **Largest linear factor ~0.18 pts against an 0.81-pt bar: 4.5x too
small, against 4.4x at 0.79.** The verdict is unchanged.

## The juice does not mark mispricing

If the book cheapened the side that was actually wrong, the price would predict cover.
On the 8,114 exactly-priced team-games:

```
cover ~ price                       beta -0.0119   t -0.37
cover ~ price + spread + home       price          t -0.40
```

Directionally the recorded side covers *less* at cheaper prices
(-0.058 at < -110, -0.366 at -110, -0.641 at >= -109, none significant), which is the
book doing its job rather than an opportunity — but it is not established, and it is
the opposite of what shopping for -105 would need.

## One cell sits exactly on the multiplicity boundary — a lead, not a finding

Splitting each spot by price and keeping only exactly-priced rows,
`5+ ATS loss streak x price >= -108` gives **n = 49, mean cover +5.58, t +2.74**,
against a bar of 0.506.

It lands precisely where the answer depends on the correction you choose:

```
Bonferroni over the 8 cheap cells actually searched   |t| > 2.73   -> just clears
Bonferroni over all 16 cells (cheap + dear)           |t| > 2.96   -> fails
permutation on shuffled prices, max cov/bar           p = 0.005
```

**Do not read the permutation p as support.** Its statistic is `|mean cover| / bar`,
whose **null mean is 5.01** at these cell sizes — the ratio rewards small bars and does
not penalise small n, so it is not an inference tool here. It agrees with the t-test
once translated (p 0.005 corresponds to |t| ~ 2.95).

n = 49, on the spot that was already the project's single marginal positive, is a lead
to power up rather than a result. **And it cannot be powered up on this data:**
detecting the parent spot's +0.989 at 80% power needs ~1,404 cheap team-games in that
spot; cheap games are 29% of the sample and the spot is 6.8% of it, so that is
~71,000 team-games — **about 19 seasons.**

## Both sides, settled

| screen | standing (assumed -110) | **measured** | change |
|---|---|---|---|
| NBA totals | 1.079 pts | **1.123** | +4.1% |
| NBA spreads | 0.790 pts | **0.806** | +2.0% |

Both corrections run against the bettor, for the same reason: the juice distribution is
asymmetric, with more games priced worse than -110 than better. **Quote 1.12 and 0.81.**
Every result previously scored against 1.079 / 0.79 is 2-4% worse than reported.
