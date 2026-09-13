# NBA MARKET MODEL — SPECIFICATION, CALIBRATION, ECONOMICS

Consolidated record of the market-emulation stack: what each layer models, how it
is formulated, what it was calibrated against, and what it is worth in dollars.

**Status 2026-08-30.** Layers 1-2 are measurement and are settled. Layer 3 carries
one surviving signal, preregistered and unwagered. **No money has been staked. No
component contains order-placement code.**

---

## 0. ARCHITECTURE — three layers, and where the information actually is

```
LAYER 1   Kalshi ladder      11 contracts  <- one bell curve, 2 parameters
LAYER 2   Sportsbook centre  mu, and the spread          <- WHERE THE INFORMATION IS
LAYER 3   Signal             model - market disagreement <- where the money would be
```

Kalshi does not create the expected total. It **inherits mu from the sportsbook**
and constructs a probability ladder around it. The part of the machine that is
genuinely Kalshi's own is Layer 1's sigma — and it is both the smallest
contributor and the one we can least predict. That asymmetry governs the whole
programme.

---

## 1. DATA — sources, items, spans

### Sources behind every reported figure

| source | path | span | volume |
|---|---|---|---|
| Odds + box scores | `/mnt/c/NBA2/dfMaster_OT_2017-2026.csv` | 2017-10-17 .. 2026-04-12 | **9,487** games with lines, 8 seasons |
| Kalshi totals ladders | `/mnt/c/NBA2/Kalshi/data/kalshi_nba_totals.sqlite` | pregame snapshots | **1,318** ladders, **14,471** rungs |
| Official injury reports | `~/data/injury_reports` (14,327 PDFs) | 2020-12-22 .. 2025-12-22 | `injury_status_panel.csv`, 1,224,205 rows |
| Player-game points | `~/data/player_game_pts.parquet` | 2017-18 .. 2025-26 | 195,017 rows |

### Built, NOT load-bearing — play-by-play

**No reported figure in this document depends on PBP as a statistical input.**
Verified: `canonical_spec.py`, `pace_signal.py`, `oracle_attribution.py`,
`v5_combine.py` and `stageA.py` do not read it. The shot-independence result in
§2.5 — the one place PBP would be the obvious source — is measured on **box
scores** (`shot_corr.py`, 18,977 team-games, identity `2*2PM + 3*3PM + FTM = PTS`
exact).

| source | path | span | volume | actually reaches |
|---|---|---|---|---|
| Play-by-play | `/mnt/c/NBA2/out/pbp_lineups_all.parquet` | 2017-18 .. 2024-25 | 3,609,007 events | a pid -> name lookup in `injury_features_build.py` |
| Transition store | `~/data/pbp_transition_store.csv` | 2017-10-17 .. 2025-04-13 | 18,330 team-games | `m_X` -> `D*_profile` -> secondary endpoint only |
| Live PBP (2026-27) | `cdn.nba.com` liveData, `pbp_feed.py` | forward | corr 0.9868 validated | same secondary endpoint |

Two thin threads keep it in the tree. It supplies the player-id -> canonical-name
map used when building injury features, which reach the spread model and are worth
**+0.0052 R^2** there — any roster directory would serve. And a 3.6M-event
possession reconstruction feeds a transition state that reaches a **secondary**
comparison endpoint which cannot run until 2026-27 games exist.

**Verified by deletion:** removing the transition store entirely leaves `E_pace`,
`bet_flag` and `side` **bit-identical**; only `m_X` and `D_star_profile` go empty.

**Seasons present:** 2017-18, 2018-19, 2020-21, 2021-22, 2022-23, 2023-24,
2024-25, 2025-26. **2019-20 is absent** (COVID). Game counts 1,230 / 1,230 /
1,080 / 1,230 / 1,229 / 1,162 / 1,166 / 1,160.

**Market items used:** `OPENING TOTAL_H`, `OPENING SPREAD_H`, `CLOSING TOTAL_H`,
`CLOSING SPREAD_H`.
**Box items used:** `PTS_H/R`, `PACE_H/R`, `OEFF_H/R`, `TO_H/R`, `FTA_H/R`,
`FGA_H/R`, `POSS_H/R`.

**Data gate.** `prepare_data.read_master()` is the only sanctioned loader. It
scrubs four corrupt `CLOSING SPREAD_H` cells (game-ids 22200232, 22200385,
22200457, 22300027) that contained juice or a total, and two out-of-range
`OPENING TOTAL_H` cells. Those four cells alone manufactured a p=0.0015 "market
overreacts" finding; see §5.2. A hand-rolled season filter previously loaded
2,460 of 9,489 games silently — never bypass the loader.

---

## 2. LAYER 1 — THE KALSHI LADDER (solved)

### 2.1 Formulation

```
P(Total > K) = 1 - Phi( (K - mu) / sigma )
```

Eleven quoted contracts per game are **not eleven opinions**. They are one bell
curve read at eleven points. Given a game's `mu` and `sigma`, every rung price
regenerates.

**Compression: 14,471 quoted prices -> 2,636 numbers (2 x 1,318 games) + one
fixed curve.**

### 2.2 Estimation

WLS is primary; interval/censored fitting is the robustness standard. **Midpoints
are not a primary estimator** — mid-based probit `sigma` is contaminated at
R^2 = 0.47 by quote width via Jensen's inequality (`sigma = 1/b` is convex, so
noise in `b` inflates `E[sigma]`). Correcting this with `phi(z)^2/(w/2)^2` weights
dropped that contamination to R^2 = 0.04, and in doing so **retracted one headline
and un-retracted another**.

### 2.3 Calibration

| model | per-rung MAE | variance explained | rungs inside [bid,ask] |
|---|---|---|---|
| game `mu`, CONSTANT `sigma` (1 param) | 1.108c | 98.82% | 70.1% |
| **game `mu`, game `sigma` (2 params)** | **0.909c** | **99.03%** | **78.2%** |

Ladder set: 1,318 pregame ladders, median 11 rungs, median span 30 pts, mean
quote width 3.60c. Pooled sd of (market − Normal(z)) over all 14,471 rungs =
1.964c; per-rung RMSE 1.969c.

### 2.4 The 99.03% figure does no work — stated because it was over-claimed

`mu` **alone** reaches 98.82%. Rung prices march monotonically downward as the
strike rises, so any sensible downward curve scores in the high nineties; the
metric is saturated before `sigma` is involved. The second parameter earns its
place on the measures that discriminate:

```
per-rung MAE          1.108c -> 0.909c   (18.0% better)
rungs inside [bid,ask] 70.1% -> 78.2%    (+8.1 points)
```

**Real, but an 18% improvement, not a 99% one.**

This also puts Layer 1's own parameter in proportion: `sigma` contributes ~0.2
percentage points of the variance headline and is predictable only to
**OOS R^2 = 0.1385** (`mu` + pace + shot composition; richer models have higher
in-sample R^2 and less than half the OOS). Both facts point the same way — **the
centre is where the ladder's information is, and the centre is imported from the
sportsbook.**

### 2.5 The key assumption, tested

Normality decomposes into four commitments: symmetry, no fat tails, one `sigma`
across strikes (no smile), and continuity of a discrete score. Underneath all
four sits one claim: **the total is a sum of many small, near-independent scoring
events, so the CLT applies.**

**The microfoundation holds.** Measured, not assumed:

```
3PT   phi 0.9883   rho -0.00035        (essentially EXACTLY binomial)
cross-channel:  3PT-2PT -0.019   3PT-FT +0.011   2PT-FT +0.001
```

Shots are independent. No hot hand, no hot night.

**The assumption is nonetheless measurably false:**

```
SKEW +0.2319 (t=+9.22)   EXCESS KURTOSIS +0.3944 (t=+7.84)   JB p<0.0001
```

**And it does not matter, because it is violated only where nothing is priced:**

| \|z\| > | normal % | actual % | ratio | inside ladder span? |
|---|---|---|---|---|
| 1.0 | 31.731 | 30.330 | 0.956 | YES |
| 1.1 | 27.133 | 27.021 | **0.996** | YES — the ladder's edge |
| 2.0 | 4.550 | 4.331 | 0.952 | no |
| 2.5 | 1.242 | 1.381 | 1.112 | no |
| 3.0 | 0.270 | 0.411 | **1.522** | no |

Inside ±1.1 sigma — exactly the span Kalshi quotes — the normal is accurate to a
ratio of 0.996. Skew is symmetric to 0.08pp beyond 1 sigma, but the over side is
1.58x the under at 2 sigma and 2.45x at 2.5 sigma.

**Mechanism.** The CLT governs a sum given a **fixed** number of events. It says
nothing about a **random** number of them. Overtime adds possessions, and only
upward: a game can reach 350 through double OT, but nothing symmetrically drags a
total to 100. The failure is not in the shot process (binomial, as measured) —
it is in the possession count, which the model treats as known.

### 2.6 Standing monitoring item — a prediction made in advance

**If Kalshi widens its ladder beyond ~2 sigma in 2026-27, those rungs are
structurally mispriced on day one.** At 2.5 sigma the normal underprices the over
side by 58%, and that is also where Kalshi's `0.07 * p * (1-p)` fee is smallest —
the one place a shape error could survive costs. Unlike everything else in this
programme, this prediction is derived from measured physics in advance rather than
fitted to data. Committed as `d99d547`.

---

## 3. LAYER 2 — THE SPORTSBOOK CENTRE

### 3.1 Structural identities

```
Total  = Pace x (PPP_H + PPP_R)          EffSum  = OE_H_hat + OE_R_hat
Margin = Pace x (PPP_H - PPP_R)          EffDiff = OE_H_hat - OE_R_hat
```

Two-way decomposition of the opener, both markets at once:

```
M    = -(OPENING SPREAD_H)               implied home margin
impH = (open_total + M) / 2              implied home points
impR = (open_total - M) / 2              implied road points
```

### 3.2 Latent state engine (shared by both markets)

Recursively updated team states, **predict strictly before update**, with
same-day batching (every game on date D predicted before any date-D update):

```
impH_hat = base + Off[H] + Def[R] + hfa
impR_hat = base + Off[R] + Def[H] - hfa

Off[H] += 2*share*k*eH ;  Def[R] += 2*(1-share)*k*eH
Off[R] += 2*share*k*eR ;  Def[H] += 2*(1-share)*k*eR
season boundary:  Off *= lambda ; Def *= lambda
```

Hyperparameters tuned on **2017-2021 only**, applied unchanged to 2022-2026.

### 3.3 TOTALS opener

```
Open = a + b * (sP * EffSum / 100)       a = 19.2817   b = 0.9204
Pace_book = 100 * (Open - a) / (b * EffSum)
```

`a, b` refit each season by OLS on **all prior seasons only**; no in-season
refitting. **`b` must be fitted on the FORECAST product, not the realised one** —
fitting on realised pace x efficiency gave b = 0.231 and inverted to a book pace
of 125 possessions, an errors-in-variables artefact.

Held-out 2022-2026, predicting the opening total:

| model | RMSE | MAE | R^2 |
|---|---|---|---|
| last observed implied points | 7.675 | 6.071 | 0.0789 |
| own-rating only, no opponent adjustment | 6.129 | 4.898 | 0.4126 |
| full box-score model (Stage B M6) | 4.508 | 3.544 | 0.7444 |
| **two-way latent ratings — LINES ONLY** | **3.336** | **2.574** | **0.8259** |
| **+ structural + recent state** | **3.174** | **2.448** | **0.8504** |

A rating system using **zero box-score data** beats every basketball model built
in this programme. `k = 0.30`, `lambda = 0.6`.

### 3.4 SPREAD opener — specification

Dependent variable is the **opening spread** (`M = -OPENING SPREAD_H`).

```
M_hat = (Off[H] - Off[R]) + (Def[R] - Def[H]) + 2*hfa   [+ corrections]

k = 0.20    lambda = 0.5    share = 0.54    hfa half-life = 200 games
update blend:  e = 0.90 * (quote error) + 0.10 * (scoring surprise)
states update on the CLOSE where available (known before the next opener)
corrections: B2B_H, B2B_R, rest differential, win% differential
             fitted on an EXPANDING PRIOR-ONLY window, refreshed every 200 games
```

Held out 2022-23 .. 2025-26 (n = 4,717):

**Ratings layer alone** (no schedule corrections), held out:

| ratings variant | R^2 |
|---|---|
| two-way architecture, spread as DV | 0.8415 |
| + recursive HFA, Off/Def share 0.54 | 0.8463 |
| + update on closes | 0.8481 |
| **+ 90/10 quote/scoring blend** | **0.8560** |

**Full model** (ratings + corrections), held out:

| step | R^2 | RMSE |
|---|---|---|
| ratings(quote-only) + B2B/rest, dev-fit correction | 0.8587 | 2.694 |
| ratings(90/10) + B2B/rest/win%, expanding refit | **0.8689** | **2.595** |
| + injuries *(covered subsample, n = 3,583)* | 0.8674 | 2.543 |

The last row is **not** a regression — it is a different, smaller sample. On that
same covered subsample the model without injuries scores 0.8622, so injuries are
worth **+0.0052**.

Fitted structure: **a back-to-back is worth ~1.3 points of spread**, near
symmetric (−1.308 home / +1.329 road). ~30 points of expected offence removed by
injury is worth ~0.86 points of spread (coefficients −0.0285 home / +0.0241 road).

**Spreads want a 90/10 quote/scoring blend, not the 75/25 that totals want.**
Pushing scoring weight to 25% degrades held-out R^2 from 0.8560 to 0.8349. The
spread market is markedly more self-referential than the totals market.

**Injury timing.** Only the **earliest** report per team-game (`e_*`) is used —
the defensible information set for an *opening* line. The `l_*` (latest) and
`d_*` (delta) features score higher and are excluded: the timing audit found ~39%
of a previously reported injury gain was **not forecastable**.

### 3.5 Why 0.90 was not reached, and what it would take

The target was R^2 0.90 on the opening spread. **Achieved: 0.8689.**

In-sample oracle, fitting team dummies with **perfect hindsight**:

| oracle | R^2 | params |
|---|---|---|
| static ratings, whole season | 0.7929 | 34 |
| ratings shift at midseason | 0.8505 | 64 |
| ratings shift each quarter-season | 0.8901 | 124 |
| ratings shift every ~10 games | 0.9234 | 244 |

**The walk-forward model already beats the first two oracles**, because a
recursive filter tracks strength continuously where fixed dummies cannot. Crossing
0.90 requires resolving team strength at near-game granularity — effectively
reproducing the linemaker's private information.

Where the error concentrates (held-out residual RMSE):

```
games 21-40   2.327          |M| 0-3     2.472
games 41-60   2.529          |M| 6-9     2.709
games 61-82   3.193  <-      |M| 13+     2.986
```

**Late season is the failure mode** — tanking and load management, which
team-level ratings structurally cannot see. Schedule density, 3-in-4 flags and
team-specific HFA were all tested and **rejected**: each improved dev and degraded
held-out. The untried lever is player-level (RAPM) ratings.

**Disclosure.** Hyperparameters were selected on dev (2017-2021) per the Stage D
protocol, but held-out R^2 was displayed across ~10 variants during iteration.
0.8689 is not fabricated, but carries some implicit test-peeking and should be
read as slightly optimistic.

---

## 4. LAYER 3 — SIGNALS AND ECONOMICS

### 4.1 The economic bar (mechanism test, run BEFORE any backtest)

Required line error to beat −110, from `hit ~ 0.5 + phi(0)*edge/sd`:

```
TOTALS    sd(actual - open)   = 18.25 pts   ->  required 1.089 pts
SPREADS   sd(margin + spread) = 13.92 pts   ->  required 0.830 pts
```

### 4.2 SURVIVING SIGNAL — the pace gap (totals)

```
PaceGapPoints  E_pace = (sP - Pace_book) * EffSum / 100
side  = sign(E_pace)     positive -> OVER, negative -> UNDER
bet   if |E_pace| >= 4.77 points
```

**`E_pace` is a possession discrepancy, and `EffSum` is a unit converter.** The
multiplier looks like an efficiency view and is not one. Exactly, on 8,257 games:

```
E_pace = D*Ebar/100 + D*(E-Ebar)/100 = E_poss + E_eff       (identity, 5.3e-15)
  possession channel 99.38% of var | efficiency 0.10% | cov 0.52%
```

The reason is that `E_pace = sP*EffSum/100 - (open - a)/b` identically — a
difference between our total forecast and the rescaled opener — and the book's
efficiency view and ours largely agree, so efficiency differences out. The
*total forecast* alone is 43% pace / 57% efficiency; the *signal* is not.
Dropping the multiplier moves 2.3% of selections and is a null (z = +1.39).
Full workings and the withdrawn "57% efficiency" claim: `PURIFIED_PACE.md`.

**Time period: 2023-10-24 .. 2026-04-12** — three regular seasons (2023-24,
2024-25, 2025-26), n = 3,488 eligible, 8 pushes (0.23%).

```
beta +0.2223   se 0.0650   t +3.42   HC1 t +3.38   95% CI [+0.0948, +0.3497]
bets 3,480     hit 52.59%  ROI +0.39%   se(hit) 0.85pp   CI [50.93%, 54.25%]
```

Delivered edge `beta * sd(E_pace)` = **1.055 pts against a 1.089 requirement.**

### 4.3 Calibration — probability, and the caution that outranks it

```
logit p_win = +0.0388 + 0.01606 * |E_pace|
slope se 0.01155,  t = +1.39            <- NOT SIGNIFICANT
|E| at which p_win = 52.381%:  3.52 points
```

**Stake: $100 flat at −110 — a reporting unit, not a funded position.**

| \|E\| ≥ | model p_win | ACTUAL hit | bets | % slate | ROI | **P/L** | P/L per eligible | z vs BE | p (1-sided) |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 50.97% | 52.47% | 3,488 | 100.0% | +0.16% | **+$558** | +$0.16 | +0.11 | 0.458 |
| 2 | 51.77% | 53.17% | 2,289 | 65.6% | +1.50% | **+$3,434** | +$0.98 | +0.76 | 0.225 |
| 5 | 52.97% | 54.01% | 972 | 27.9% | +3.11% | **+$3,023** | +$0.87 | +1.02 | 0.154 |
| 8 | 54.17% | **56.59%** | 311 | 8.9% | **+8.04%** | **+$2,500** | +$0.72 | +1.50 | 0.067 |
| **4.77 (frozen)** | — | **53.31%** | **1,056** | **30.3%** | **+1.78%** | **+$1,882** | **+$0.54** | +0.60 | 0.274 |

**Break-even sits inside every confidence interval.** Not one row clears 52.381%
at conventional significance; the strongest (`|E| >= 8`) has CI [51.08%, 62.10%].

**ROI and total P/L rank differently.** ROI rises monotonically; P/L peaks at
`|E| >= 2` and falls thereafter. `Profit/AllEligibleGames` ranks 2 > 5 > 8,
inverting the ROI order. A filter can raise ROI while destroying total profit —
only the last two columns separate those cases.

**Decile calibration is non-monotone**, and the monotonicity is binning-dependent:

```
pred  51.09 51.32 51.55 51.79 52.06 52.38 52.71 53.11 53.69 54.97
act   51.29 54.15 49.86 52.87 53.58 53.01 50.00 52.44 52.44 55.01
```

**The threshold landscape is unstable** — the strongest caveat in the programme:

```
bet all      +$563        |E| >= 3     -$309   <- LOSES money
|E| >= 2    +$3,436       |E| >= 4.77 +$1,882
```

**Reconciliation.** The continuous regression gives t=+3.42 while the binary
hit-rate slope gives t=+1.39. Both are correct: **the signal is real in POINTS and
weak in HIT RATE**, because the binary conversion discards outcome magnitude. That
is the honest character of the edge, and it is why `|E| >= 8 -> 56.59%` **must not
be read as a strategy**. The threshold 4.77 was taken from where the fitted
logistic crosses break-even + 0.5pp, deliberately blind to the ROI column.

### 4.4 MONEYLINE — all three avenues closed

The moneyline is a deterministic transform of the closing spread (held-out
MAE 1.42c, R^2 0.9922 on probability), and the market's spread -> probability
mapping is calibrated to **0.42pp** against realised outcomes. Three avenues were
tested and closed. See `MONEYLINE_EMULATOR.md`, `MONEYLINE_INCREMENTAL_TEST.md`,
`MONEYLINE_ERROR_ATLAS.md`, `MONEYLINE_BLOCK_ATLAS.md`,
`MONEYLINE_SOURCE_ATTRIBUTION.md`, `MONEYLINE_IMPULSE_RESPONSE.md`,
`MONEYLINE_VARIANCE_CHANNEL.md`.

| avenue | test | result |
|---|---|---|
| 1. improve the market's expected margin | offset probit, `Phi^-1(p_mkt) + beta*D_M` | beta −0.00409, t −0.79; market offset coefficient +1.0416 (t +0.25 vs 1.0) |
| 2. conditional exceptions by current team/matchup | 120 team-seasons, 480 blocks, local analogs, h=1..20 impulse response | dispersion at or below sampling noise; 280 market tests give 8 at \|t\|>1.96 vs 14 expected |
| 3. improve the width around the market's margin | binomial variance (A0) and matchup covariance (A1) | predicted margin sd 10.98-15.90 ranks realised dispersion **inversely** (−0.31 actual vs +1.95 predicted) |

**What was established positively:**
- Expected margin is highly forecastable; the book is better than our independent
  model (RMSE 13.74 vs 14.02), and gain tuning does not close it.
- Margin error is strongly leptokurtic and the moneyline smile prices that shape
  accurately (3x better than a constant sigma).
- Game-specific distribution WIDTH is far less forecastable than intuition
  suggests; team scoring volatility is largely transitory.
- Scoring covariance is economically large ex post (removes 28% of summed team
  variance) but is not predictable from current matchup profiles.
- Persistent structural states DO exist — turnovers (block r +0.364) and FT
  generation (+0.336) — and the market already reflects them.

**Contrast with totals.** Totals yielded a state variable — PACE — that is both
structurally interpretable and persistent enough to leave prospective information
in the model-book disagreement. Margin's dominant uncertainty sources are 3P/2P
realization and unpredictable game-level covariance: enormous realised variation,
little forecastable conditional variation. That difference is why the same
research process found something in totals and essentially nothing in moneylines.

**Scope.** These results are established against CLOSING moneylines, the only ones
in the dataset. Amendment 7 captures opening moneylines prospectively.

### 4.5 DEAD — spread signals, both channels

**Pace channel: structurally excluded.** A pace error multiplies `EffSum`
(mean 230.03) for totals but `EffDiff` (mean −0.07, sd 6.86) for spreads — a
**~42x smaller multiplier**. Measured `E_margin` sd 0.135, p99 0.485, max 1.016:
**only 2 of 3,488 games reach the 0.830 bar at all.** No threshold can fix a
distribution that does not reach the bar.

**Efficiency channel: has the leverage, lacks the information.**

| | beta | t | information share | beta x sd | required |
|---|---|---|---|---|---|
| pace gap (totals) | +0.2223 | +3.42 | **22.2%** | 1.055 | 1.089 |
| efficiency gap (spreads) | +0.0659 | +0.96 | **6.6%** | 0.226 | 0.830 |

```
bet sign(efficiency gap):  3,479 bets  hit 49.55%  ROI -5.40%  z = -3.33
```

Not merely unprofitable — **significantly worse than break-even.**

**The finding worth keeping:** `beta` is the information share of our disagreement
with the book. **The book prices team strength ~3.4x better than it prices pace.**
That is why the only surviving signal in this programme is a pace signal, and why
it lives in totals rather than spreads.

**Not a rescue:** residualizing against the spread lifts the efficiency gap to
beta +0.1425 (t=+1.87). Still 1.9x short of the bar, still loses money (50.62%,
z=−2.08), and `corr(sig, spread) = +0.471` means the raw signal is largely a
systematic fade of one side.

---

## 5. NULLS OF RECORD

### 5.1 Uncertainty constructs — all removed from the decision rule

Amendments 1-2 of the prospective prereg drop every uncertainty gate:

```
5-feature linear sigma_P     tercile actual sd 4.060/4.047/4.184, F p=0.4313
volx (Vol_H x Vol_R)         main effects +0.877/+0.883, interaction +0.1585 (t=+0.41)
beta(Gap x Vol)              -0.0429 (t=-0.47), CI [-0.220, +0.134]
HH/LL matchup variance       ratio 1.0119, p=0.7087
```

**They may be reported as diagnostics. They may not affect a bet.**

### 5.2 Spread level — unbiased

The "line overreacts" result (MZ slope 0.9368, chi2 13.01, p=0.0015) was **four
corrupt cells**. Clean: slope **1.0043 (t=+0.22)**, seven of eight seasons within
|t| < 1.2 of unity. `PREREG_spread_tilt` and `PREREG_spread_curve` are dead as
bets; an early box-score spread model ran 48.61% on n=4,740 (z=−5.20, ROI −7.20%,
CLV −0.612).

### 5.3 Retracted for cause, recorded so they are not re-derived

- **Playoff contamination** — a missing regular-season filter admitted 894 playoff
  games and produced a spurious HH/LL ratio of 1.247 (p<0.0001) against a correct
  1.0119 (p=0.7087).
- **`p_survive`** — 93% collinear with `|D|` by construction; t=+5.55 was
  arithmetic, not signal.
- **PIT standardisation** — full-season mean/sd scaled a December game with April
  data; rebuilding prior-only cut quintile contrasts from +0.49/+0.44 to
  +0.17/+0.12.
- **Power arithmetic** — MDE used 1.96·SE (50% power) instead of **2.487·SE**
  (80% one-sided).

---

## 6. ECONOMICS SUMMARY

| item | value |
|---|---|
| **Amount wagered to date** | **$0.00** |
| Stake convention | $100 flat at −110 (reporting unit) |
| Break-even at −110 | 52.381% |
| ROI formula | `1.90909 * hit - 1` |
| Discovery period | 2023-10-24 .. 2026-04-12, 3 seasons, n = 3,488 |
| Frozen rule | `|E_pace| >= 4.77`, bet the sign |
| Discovery P/L at that rule | **+$1,881.77** (1,056 bets, 53.31%, +1.78%) |
| Settlement | **`open_total`**, never `close_total` (Amendment 6) |
| Prospective window opens | **2026-10-20** |
| Model version | `2026-08-30-frozen+a5` |

**These are in-sample discovery figures and are labelled "reference only" in the
preregistration. They are not evidence for the strategy.** The earliest real P&L
is the 2026-27 season-level evaluation; interim looks at wagering performance are
prohibited (D3), and `evaluate_season.py` refuses to run before 2027-04-15.

---

## 7. FROZEN vs OPEN

**Frozen — may not be altered before the season-level evaluation:**
Ladder transformation (Layer 1); latent state engine constants (pace HL 5.7,
offence HL 8.6, defence HL 7.4, league HL 496, carry 0.42, share 0.54); `a, b`
refit rule; threshold 4.77; sign convention; push rule; settlement line;
descriptive magnitude bins.

**Open:**

1. **Spread emulator at 0.8689 vs a 0.90 target.** RAPM player-level ratings are
   the untried lever, aimed at the late-season failure mode.
2. **PBP earns its keep nowhere yet.** Deleting the transition store leaves
   `E_pace`, `bet_flag` and `side` **bit-identical**. Roughly 350 lines of feed
   and possession reconstruction serve one secondary comparison whose registered
   default is already the simpler non-PBP option (`use drift if it matches`).
   Whether to keep it is an open call, not a dependency.
3. **CDN transition-store rebuild** would remove a documented +0.63pp level shift
   but costs the store its first two seasons (the CDN does not serve 2017-18).
4. **Ladder-widening monitor** (§2.6) — the one forward prediction in the
   programme.
