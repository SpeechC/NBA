# PREREG — is Kalshi's in-game total price stale at halftime?

**Written 2026-08-25, BEFORE any in-game ladder is reconstructed.** One pass.

## 0. Provenance
The user identified that the candle fetch's 12h lookback ran from market CLOSE
(game end, ~2.8h post-tip), so the store holds IN-GAME minute bars for 4,697 of
4,719 markets — an unplanned capture of live pricing for 429 games (2025-10-21
..2025-12-22). FINDINGS_LATE s20 already established the efficient benchmark on
8 seasons of vendor data: actual 2H depends on H1 with coefficient only -0.033,
so the efficient FULL-total price at halftime moves ~0.97 per point of realized
H1. A frozen (stale) price moves 0. The identification is the distance between
those two, on one season. No holdout exists; a 70/30 time split is reported for
stability only.

## 1. Measurement, fixed now
- L(t): the frozen median-crossing estimator (PREREG_injury_absorption s3).
- L_half: usable L nearest T+70min inside [T+63, T+77]. Halftime timing is not
  observed; this window may catch late-2Q or early-3Q for outlier games —
  contamination runs BOTH directions and is a stated limitation, not tunable.
- H1 = HALFTIME_H + HALFTIME_R (vendor). pre = closing total (gated master).

## 2. The single regression
    L_half = a + b*pre + s*H1 + e          PRIMARY: s (the staleness slope)
    Benchmarks: s ~ 0.97 efficient | s ~ 0 frozen.
    Reference regression on the same games: actual_total = a' + b'*pre + s'*H1
    (s' is the realized analogue; its distance from 0.97 measures the s20 rule
    on this season's data).

## 3. Decision rule, fixed now
- s >= 0.80: Kalshi in-game is EFFICIENT in H1; branch closes.
- s <= 0.50: substantial staleness; a follow-up economic prereg is permitted.
- between: reported as-is, no follow-up (one season cannot refine it).
Economic context stated in advance: the in-game median spread is 15c and the
halftime points-per-cent is ~0.35pt/c, so a round trip costs ~5 points of
total. Only staleness leaving 5+ point errors could ever pay; the share of
games with |L_half - efficient| > 5 is reported descriptively.

## 4. Positive control (estimator, well-conditioned region)
corr(L_half, H1 + 0.5*pre) must exceed 0.9 — the halftime price must track the
obvious state. If not, the in-game ladder reconstruction is broken and nothing
is interpreted. (Derived from measured quantities: pregame L tracked the book
at corr .992.)

## 5. Prohibited
Re-timing the halftime window after results; alternative L estimators; any
tradability claim from this document; touching the curated DB in write mode.

---

## 6. RESULT — 2026-08-25. s(H1) = 0.628 (se 0.043): PARTIAL STALENESS, reported as-is

### Estimation history, disclosed in full
Two invalid steps preceded the valid run, neither a look at a favourable
result:
1. **My positive control was hypothesis-contaminated.** "corr(L_half, H1+...)
   >= 0.9" PRESUPPOSES the price tracks H1 — a frozen price fails it with
   perfect plumbing. The legitimate plumbing control (pregame L vs the master
   closing total on the same joined games) passes at **corr +0.9966, mean gap
   0.45 pts, zero mismatches**, and is substituted WITH THIS DISCLOSURE.
   Lesson-8 family, fourth instance: a control must be satisfiable under BOTH
   hypothesis outcomes.
2. **The first run used the wrong H1.** Vendor column `HALFTIME_H/R` is NOT
   the halftime score: 27% coverage, sd 5.8, and **corr -0.06 with the true
   quarter-sum H1**. It is a captured line-like object (its coverage matches
   PREREG_h2's "2H line" table season by season). True H1 = 1Q+2Q both sides,
   100% coverage, sd 12.5. Recorded in MARKET_COLUMN_AUDIT as a naming trap.

### The valid result (n = 111 games with usable halftime ladder)

    L_half = a + 0.649*pre + 0.628*H1        s(H1) se 0.043
    benchmarks: efficient ~ 0.97   frozen ~ 0
    realized on same games: s' = 1.244 (se 0.134), CI covers 0.97

Kalshi's halftime price incorporates about **two-thirds of the realized first
half** and over-weights the pregame prior (b(pre) 0.649 vs the efficient
~0.49). Under-reaction, ~8 sigma from efficient, ~15 sigma from frozen. This
is heavily TRADED staleness, not resting quotes: 425/426 events have volume in
the halftime window (median 3,743 contracts).

Decision per s3: s in (0.50, 0.80) -> **reported as-is, no follow-up** — one
season cannot refine it, and the pre-set bin holds.

### Descriptive economics (pre-specified)
Deviation from the s20-rule efficient price: median |dev| 3.26 pts, **27%
beyond 5 pts** (the ~round-trip cost at 15c spreads), 15% beyond 7. Monotone
in H1 surprise (quartile means -6.0 / -3.0 / -0.1 / +1.8): the price lags in
BOTH directions, more after cold halves. Suggestive that the tail could clear
in-game friction; not a tradability claim, and none is made.

### Limitations
Halftime-timing fuzz (fixed window T+63..77, untunable per s5) biases s in
unknown direction; 111 games; one partial season; the efficient benchmark is
the s20 book rule, itself an estimate.

---

## 7. EXTENSION (exploratory, windows fixed before running) — the full-game trajectory

Same estimator at four checkpoints (fixed wall-clock windows: Q1 T+30-42,
HALF T+63-77, Q3 T+98-112, mid-Q4 T+116-128). Efficient benchmarks estimated
on the FULL 8-season panel: banked points carry s' of 1.00-1.06 (slightly
above 1 because pace persists — a fast quarter predicts a fast rest).

| checkpoint | n | s_kalshi | benchmark | gap | t vs bench | b(pre) |
|---|---|---|---|---|---|---|
| Q1 | 416 | 0.657 (.023) | 1.062 | -0.405 | -17.3 | 0.803 |
| HALF | 379 | 0.657 (.024) | 1.001 | -0.344 | -14.1 | 0.647 |
| Q3 | 359 | 0.629 (.023) | 1.018 | -0.389 | -17.1 | 0.490 |
| mid-Q4 | 333 | 0.737 (.025) | 1.018 | -0.282 | -11.3 | 0.427 |

Balanced panel (301 games measurable at every checkpoint): 61% / 80% / 68% /
78% of efficient — composition, not convergence, explains part of the raw
wiggle.

### Reading
1. **The under-reaction is game-long, not a halftime artifact.** Kalshi
   incorporates ~60-80% of banked scoring at every stage and never converges
   to efficient, at 11-17 sigma per checkpoint.
2. **The prior decays correctly; the score never catches up.** b(pre) falls
   0.80 -> 0.43 across the game while s stays flat — the market unwinds its
   pregame anchor on schedule but persistently under-trusts what has actually
   been scored.
3. This corroborates the halftime headline on a proper sample (s = 0.657 on
   379 games vs 0.628 on the earlier 111, which had been selected on the bad
   HALFTIME column's coverage).

### Attenuation caveat, stated against ourselves
Quarter-end times vary by +/-5-8 minutes around the fixed windows, so some
bars predate the full banked score — mechanically biasing s DOWN. True s is
plausibly 0.75-0.85 rather than 0.63-0.74. Under-reaction survives the
correction; its magnitude is softer than the raw table.

Ladder attrition (416 -> 333 as blowout totals unbracket the crossing) is a
second downward pressure via range restriction; the balanced panel bounds it.

One season; the 2026-27 candle capture inherits in-game bars for free (the
lookback spans the game), so this becomes a two-season question at zero
additional cost.

---

## 8. RETROSPECTIVE ECONOMICS (one pass, fixed grid, real quotes, fees in)

Rule weights and the residual CDF fit on seasons <= 2024-25 only (E[total] =
4.22 + 0.478*pre + 1.0025*H1, resid sd 13.51, empirical tails); 2025-26 is
out-of-sample for the WEIGHTS. The threshold grid itself is retrospective and
is reported in full, losses included. Execution: taker at the ACTUAL quoted
ask/bid of each rung at the halftime bar, taker fee 0.07*p*(1-p), 1 contract
per position (displayed quotes are executable at 1 lot; depth is unobserved).

**Best rung per game (the honest unit), 425 games, 226 with any positive edge:**

| min predicted edge | games | hit% | avg cost | $P&L (1 ct) | ROI |
|---|---|---|---|---|---|
| 3c | 226 | 54.0% | 55.5c | -$3.44 | -2.7% |
| 5c | 176 | 52.8% | 54.6c | -$3.13 | -3.3% |
| 8c | 101 | 57.4% | 52.8c | +$4.68 | +8.8% |
| 12c | 35 | 68.6% | 49.5c | +$6.69 | +38.6% |
| 20c | 11 | 90.9% | 49.6c | +$4.54 | +83.1% |

Calibration overall: predicted edge 6.4c, realized **-0.3c** per contract.
Sides symmetric (YES +0.2c, NO -0.8c).

### The two-sided verdict

1. **The headline staleness does NOT convert to money on average.** The
   under-reaction lives in the MIDS; the executable envelope (ask above,
   bid below, ~15c wide) straddles the efficient price in the typical game.
   This is the ladder-consistency lesson again — mids are noise, bounds are
   coherent — now shown dynamically: the market under-updates its midpoint
   while keeping its quoted bounds wide enough to be roughly unexploitable.
2. **The deep tail is monotone-calibrated and was profitable.** Hit rates rise
   54 -> 57 -> 69 -> 91% with predicted edge — the signal orders reality — and
   everything at >= 8c predicted made money. But: 101/35/11 games, one
   season, retrospective grid, depth unknown, +$5-16 per season AT ONE
   CONTRACT. A micro-edge at best until depth and a second season speak.

### Disposition
No promotion from this table. The natural next step is FREE: the 2026-27
candle capture records in-game bars automatically, so the >= 8c halftime rule
can be paper-logged live alongside the other seats and graded on virgin data.
