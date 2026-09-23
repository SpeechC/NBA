# SHOT-VOLUME CHANNEL — PBP POSSESSION-END TYPING (2026-09-13)

Resolves the promotion criterion set in `TOTALS_MAD_DECOMPOSITION.md` §7.1:

> the 0.673-pt edge comes from a forecast with R2 = 0.072 on shots-per-possession.
> Edge scales as sqrt(R2), so reaching the 1.079-pt bar requires **R2 ~ 17.4%**.

**Built, measured, and the criterion is unreachable.** PBP typing does improve the
forecast — OOS R2 on shots-per-possession **0.0605 -> 0.0719**, an 18% relative gain,
the first thing in this project to beat the box-score baseline on this target. It is
not close to enough: **every independent estimate of the team-level information
content of game shots-per-possession lands in 5-9% of R2, and the criterion needs
17.4%.** The channel is capped at roughly 0.6-0.8 points of edge against a 1.079-pt
bar, by an information bound rather than by a failed test.

Scripts `p1_poss.py` … `p8_crew.py`. Build: **1,937,498 possessions, 9,801 games,
197.7 poss/game (98.8 per team)** — reproduces `PACE_DEEP_DIVE.md`'s 98.31.

**Coverage limit that shapes everything below.** The PBP store runs 2017-18 …
2024-25. **It cannot see 2025-26**, the season in which the box-score signal went
negative (beta -31.3). Every in-sample number here is measured on the good era.

---

## 1. THE TYPING

`STARTTYPE` gives possession ORIGIN, so the origin of possession *i+1* is how
possession *i* ended. Recovered end-type mix over 1.94M possessions:

| make | miss | steal | dead ball | FT make | FT miss | period end |
|---|---|---|---|---|---|---|
| 35.2% | 31.2% | 7.5% | 13.3% | 8.7% | 2.1% | 2.1% |

Matches `PACE_DEEP_DIVE.md`'s duration table exactly. Identity check:
`chances = FGA + TOV + shooting fouls = 111.60` against `poss + OREB = 111.49`.

Six structural rates per team-game, each a separate skill:
`q_tov_live` (steals), `q_tov_dead`, `q_shf` (shooting fouls drawn), `m_miss`,
`orb_pct` (OREB **per miss**), `nsf_ch`.

---

## 2. THE STRUCTURAL HYPOTHESIS WAS WRONG, AND IT FAILED BEFORE ANY FITTING

The reason for building this was: OREB per *possession* mixes rebounding skill with
shooting noise, because a rebound requires a miss. Normalising per *miss* should
isolate the skill and forecast better.

**It does not. The two are indistinguishable:**

| | split-half reliability | game-level ICC |
|---|---|---|
| `orb_pct` (OREB per miss) | 0.906 | 0.0961 |
| `orb_poss` (OREB per possession) | 0.906 | 0.0928 |

The miss rate barely varies across teams (CV 10%) next to the rebound rate (CV 28%),
so dividing by it is dividing by a near-constant. **The hypothesis is refuted at the
measurement stage**, and on the outcome test `orb_pct` (t +1.95) does not beat
`orb_poss` either.

Game-level ICC of every structural rate is **4-10%** — that is the share of a single
game's variation in each rate that is team-level at all:

```
q_tov_live 0.043   q_tov_dead 0.041   q_shf 0.061
m_miss     0.067   orb_pct    0.096   nsf_ch 0.047
```

---

## 3. THE TYPING DOES HELP — just not enough

Same target, same 7,980 joined regular-season games:

| forecast of shots-per-possession | R2 (in sample) | R2 (walk-forward OOS) |
|---|---|---|
| box-score rates (the baseline) | 0.0677 | 0.0605 |
| PBP structural composition | 0.0636 | — |
| PBP: OREB per miss alone | 0.0292 | — |
| all 6 PBP rates, free weights | 0.0826 | 0.0716 |
| **PBP rates + box score** | **0.0830** | **0.0719** |

The hand-built structural composition (chances = 1/(1-extension), etc.) is **worse**
than the box-score baseline. Only the free-weights version wins. The mechanism model
added nothing the rates did not already carry — the same result M3 got for pace.

---

## 4. THE CEILING — three estimates, all far below the criterion

The requirement is R2 = 17.4%. How much team-level signal is there to have?

| estimate of the team-level information content | R2 | implied edge | % of bar |
|---|---|---|---|
| shrunken team ratings (ridge on team indicators, CV, per season) | 0.0538 | 0.600 pts | 56% |
| PBP possession-typed forecast, achieved OOS | 0.0719 | 0.694 pts | 64% |
| unshrunken team dummies, fitted in sample (upward-biased) | 0.0887 | 0.770 pts | 71% |
| **REQUIRED to clear the vig** | **0.1740** | **1.079 pts** | **100%** |

Three estimates that bracket the truth from both sides land in **5-9%**. The
criterion is 2-3x above all of them. **The PBP forecast already exceeds the
within-season shrunken-team-rating ceiling** (0.0719 vs 0.0538) because it pools
across seasons — it is extracting essentially all the team-level signal available and
then some. There is not another ten points of R2 sitting unexploited.

Stated precisely: this bounds forecasts built from *team identity*. It is the
relevant bound because shot volume is a team-style quantity.

**And the finer-granularity escape is closed too.** Replacing team-season effects
with **team-month** effects gives a cross-validated R2 of **-0.149** — pure
overfitting, no detectable in-season drift in a team's shot-volume rates. That is
evidence against the lineup-level route, whose whole premise is within-season
variation.

---

## 5. WALK-FORWARD — nothing clears, and the in-sample gains are era selection

**Era selection first**, because it explains why §3's numbers look better than last
session's:

| sample | n | beta | t | edge | % of bar |
|---|---|---|---|---|---|
| all 8 seasons (last session) | 9,407 | +36.42 | +3.46 | 0.673 | 62% |
| **2017-2024 = the PBP era** | 8,246 | +47.75 | **+4.20** | 0.871 | 81% |
| 2025-26 alone | 1,161 | -31.28 | -1.07 | 0.576 | 53% |

Every PBP number is measured on the era where the signal was strongest, and the store
cannot reach the season where it inverted.

**Walk-forward, coefficients fit on prior seasons only, OOS n = 5,777:**

| model | OOS R2 on dev | bet-all | best threshold |
|---|---|---|---|
| box score only | +0.045% | 50.45% (z -2.92) | thr 2.0: 55.03%, n=796, z +1.49 |
| PBP 6 rates | -0.308% | 51.92% (z -0.70) | thr 1.5: 53.78%, n=2,313, z +1.35 |
| PBP + box score | -0.317% | 51.80% (z -0.88) | thr 1.5: 53.49%, n=2,419, z +1.09 |

**No model, at any threshold, reaches significance against break-even.** PBP typing
does lift bet-all from 49.84% to 51.17% (+1.33pp) — a real improvement to a losing
bet. The two predictions correlate +0.69: refinement, not a new signal, the same
verdict `PACE_DEEP_DIVE.md` reached for M1/M2.

---

## 6. THE NEXT CHANNEL, PRICED BEFORE BUILDING IT

`TOTALS_MAD_DECOMPOSITION.md` §7.2 named the FTA-rate channel (10.2% of MAD) as the
untouched one, and it is a refereeing channel — which is exactly the kind of input
that varies within team-season and so is *not* bound by §4.

Priced cheaply here. **`CREW_H` is a single official, not a crew** (81 names), and
`REFEREE & UMPIRE_H` is a second single official (89 names) — and the two columns
**never co-occur** (0 games have both). So one of three officials is observable per
game. Ridge on referee identity, 5-fold CV, n = 7,980:

| target | CV R2 |
|---|---|
| shooting fouls per chance (the FTA channel) | +0.0041 |
| OREB per miss | +0.0050 |
| live-ball turnovers per chance | +0.0003 |
| **the market's total error** | **+0.0008** |

One official explains 0.08% of dev, which maps to **0.51 pts** of edge. If the three
officials' effects were independent and additive, a full crew would give
sqrt(3) x 0.51 = **0.88 pts** — still short of 1.079, and that extrapolation is
generous in every direction. **The referee route should be built only if full crew
assignments can be sourced, and the arithmetic says it probably lands short too.**

---

## 7. VERDICT

**The shot-volume channel is closed by an information bound, not by a failed test.**
It is the largest single contributor to the market's total error (29.8% of Var(dev))
and the market prices it to within ~0.7 points of the vig. Possession-end typing is
the right instrument and it produced the first genuine improvement to the forecast in
this project — 18% relative on the target — and the improvement is worth 0.06 points
of edge on a 0.4-point shortfall.

What was actually learned, beyond the null:

1. **The reliability of a rate does not follow from removing its mechanical
   contamination.** `orb_pct` and `orb_poss` are the same object empirically. Check
   the reliability before building the estimator that assumes the difference.
2. **A hand-built mechanism model lost to free weights on the same inputs** (0.0636 vs
   0.0826), for the second time in this project after M3.
3. **No in-season drift in team shot-volume rates** (team-month CV R2 -0.149). This
   pre-emptively weakens any lineup/RAPM route on this channel.
4. **The team-level information content of game shots-per-possession is 5-9% of R2.**
   That number is reusable: any future totals signal built on a team-style rate faces
   the same bound, and can be priced against the vig before it is built.

**Still open, ranked.** (a) Full three-official crew assignments — the only
identified channel not bound by §4, priced at ~0.9 pts, needs a data source this repo
does not have. (b) Injuries against the shot-volume channel specifically
(`~/data/injury_reports`) — untested here, and the one within-season input the
month-dummy null does not rule out, since injuries are observed rather than inferred
from drift. (c) The 2025-26 sign flip: if the market learned this channel, the
inversion should show up as the line moving *with* `f_spp` in recent seasons — testable
on `TOTAL MOVE` without any new data, and it would convert an alpha-decay guess into
a measurement.

**Do not re-run:** OREB per miss as a distinct skill from OREB per possession; a
structural composition model on these rates; team-month or lineup granularity on
shot volume.

---

# ADDENDUM — DOES `TOTAL MOVE` NOW MOVE WITH `f_spp`? (2026-09-13)

Resolves §7(c). **Yes — and the learning trend is the robust half of the story,
while the closing-line collapse I attributed to decay is not.**

## Method — an exact three-way split of the information

`(T − O) = (T − C) + (C − O)`. With the same regressors in all three
(`f_spp` and the opener level `O`), the betas add exactly:

```
beta[info vs opener]  =  beta[priced in the move]  +  beta[left at the close]
        45.885        =           6.234            +          39.651        (verified)
```

`TOTAL MOVE` verified `== close − open`, sd 3.180, non-zero on 92.6% of games.
n = 9,405 regular-season games with both lines.

## The answer, per era, in points of edge at 1 sd of `f_spp`

| era | info vs opener | **priced in the move** | left at the close | move / opener |
|---|---|---|---|---|
| 2017-2021 | 1.072 | **0.030** (t +0.66) | 1.042 (t +3.82) | **3%** |
| 2022-2026 | 0.534 | **0.167** (t +3.38) | 0.367 (t +1.38) | **31%** |

Pooled `move ~ f_spp + opener`: **beta +6.23, t +3.36**. Trend interaction
`f_spp × season`: **+0.0780, bootstrap 95% CI [+0.0154, +0.1408], P(>0) = 0.994**.

**Not mechanical.** `corr(f_spp, opener) = +0.2914` against
`corr(f_spp, close) = +0.2870` — the difference is −0.004, so there is no
level artefact for the move to inherit, and the opener is controlled anyway.
`f_spp` is prior-only and contains no same-day information, so it cannot be
*responding* to what the market sees. A line that moves toward it is the market
importing information correlated with it.

## The placebo says what "learned" actually looks like

Same split on the pace forecast, which the book has always priced:

| variable | era | opener | move | close | move / opener |
|---|---|---|---|---|---|
| `f_P` pace | 2017-2021 | 1.013 | 0.855 (t **+14.71**) | 0.157 | **84%** |
| `f_P` pace | 2022-2026 | 1.701 | 1.108 (t **+17.07**) | 0.594 | **65%** |
| `f_spp` | 2022-2026 | 0.534 | 0.167 (t +3.38) | 0.367 | 31% |

The book prices pace overwhelmingly between open and close, at t ≈ +15 to +17.
Shot volume is being priced at t +3.4 and from a base of nothing. **The market is
learning it, but it is early in doing so** — 31% against pace's 65-84%.

## CORRECTION TO §5 — the decay half does not survive

I read 2025-26's negative beta as the signal decaying. Splitting the trend
properly:

| specification | move interaction | close interaction |
|---|---|---|
| all 8 seasons | +0.0777 (t **+2.30**) | −0.4776 (t −2.49) |
| excluding 2025-26 | +0.0859 (t **+2.40**) | −0.2651 (t **−1.30**) |
| excluding 2017-18 | +0.1063 (t **+2.96**) | −0.4579 (t −2.29) |

**The move trend is robust to dropping either end season and strengthens. The
closing-residual trend is not — drop 2025-26 and it is t −1.30.** So "the signal
died" was one noisy season; "the market is pricing it" is the established fact.

Correspondingly the learning-vs-weakening split is not 80/20:

| sample | change at the close | reallocated into the move | **learning share** |
|---|---|---|---|
| full | −0.675 | +0.137 | 20% |
| **excluding 2025-26** | −0.345 | +0.165 | **48%** |

Without the wild season it is roughly half learning, half the underlying
relationship weakening. **The instrument is not the cause**: `f_spp`'s forecast
quality on realised shots-per-possession is flat across eras
(R2 0.0613 → 0.0642), so the decline in outcome information is the market or the
game, not a degrading forecast.

## What it means

The closing residual is now **0.367 pts, 34% of the 1.078-pt bar**, down from
1.042 (97%) — and the share the market prices intraday is rising with a CI that
excludes zero. **A signal being learned gets worse from here.** This closes the
shot-volume channel as a *forward* opportunity for a better reason than §4's
information bound: not only is it capped below the vig, the cap is tightening.

## SIDE OBSERVATION — the pace forecast is going the other way

Same split, same code, `f_P` instead of `f_spp`: closing residual
**0.157 pts (t +0.44) → 0.594 pts (t +1.65)**. Rising, and not significant.

Recorded, **not acted on**. `PREREG_2026_27_PROSPECTIVE` D3 binds: this is the
same data the prereg was frozen on (2026-08-30), so noticing it now is exactly
what the freeze exists to prevent trading on. Logged to `CANDIDATES_2027_28.md`.
