> **SUPERSEDED 2026-08 by `PREREG_spread_curve.md`**, which specifies this
> mean tilt jointly with the game-varying `p_OT` shape adjustment. Both key
> off |closing spread| and they compound on close games, so they are frozen
> together. Retained for the record; do not implement from this file.

# PREREG — expected-margin (|spread|) tilt for the SECOND_LINE fair-value curve

**Written 2026-08. This authorizes a candidate addition to the second-line
pricing curve, subject to the gates below. It does NOT authorize a bet, and it
does NOT enter the curve until G1 passes.** `SECOND_LINE.md` §10 requires any
curve addition to carry its own frozen spec; this is that spec.

---

## 0. Status and honesty statement

This effect was **discovered post hoc**, in a single exploratory regression,
while generating rules/structure candidates. It was not pre-specified. Both
development and holdout have been examined. It is therefore a **candidate**, and
the only clean test is 2026-27 forward.

**The holdout is materially weaker than development.** That is stated first
because it is the main reason for caution:

| window | slope on \|spread\| | t | n |
|---|---|---|---|
| development 2017-18..2023-24 | **+0.1825** | **+3.62** | 7,162 |
| holdout 2024-25 + 2025-26 | **+0.0864** | **+1.02** | 2,327 |
| pooled | +0.1595 | +3.70 | 9,489 |

Half the magnitude, not significant. Per-season slopes are positive in all eight
seasons, but 2024-25's is **+0.0029 (t=0.02)** — effectively nil. This is the
same development-strong / holdout-weak profile as several hypotheses this
project has already discarded, and it is not being promoted to a bet for
precisely that reason.

## 1. The claim and its mechanism

Two rules-driven effects push the same way, so the total's error is a monotone
function of the market's own expected margin:

- **Close games run UNDER.** Late in a tight game both teams milk the clock —
  deliberate half-court possessions, timeouts, no transition. Possessions are
  lost. (The intentional-fouling effect pushes the other way and is smaller;
  the net is negative. My original stated mechanism had this sign backwards and
  the data corrected it.)
- **Blowouts run OVER.** Garbage time raises pace and removes defensive
  intensity.

Realized, pooled:

| \|spread\| | mean e (actual − closing total) | over % |
|---|---|---|
| 0–3 | **−0.623** | 46.55 |
| 3–6 | +0.411 | 49.78 |
| 6–9 | +0.657 | 50.59 |
| 9–13 | +1.172 | 51.34 |
| 13+ | **+1.996** | 53.26 |

## 2. Frozen specification

Fit on **development only**:

```
tilt(game) = 0.1825 * ( |CLOSING SPREAD_H| - 6.1142 )      [points of total]
```

Applied additively to the second-line fair-value mean, alongside the existing
frozen components (CrewShock +1.434, final week +2.693). Magnitude across the
|spread| distribution:

| \|spread\| percentile | value | tilt |
|---|---|---|
| p5 | 1.5 | **−0.842** |
| p25 | 3.0 | −0.568 |
| p50 | 5.5 | −0.112 |
| p75 | 8.5 | +0.435 |
| p95 | 13.0 | **+1.257** |

At the measured 2.2pp-per-point conversion that is **−1.9pp to +2.8pp** of
probability tilt. If the holdout slope (+0.0864) is the truth rather than
development's, the tilt roughly halves to −0.40 / +0.59 points.

**Nothing else is frozen or permitted**: no non-linear form, no interaction with
the total level, no separate close-game and blowout coefficients, no
re-estimation on any window that includes holdout data.

## 3. Why a curve tilt and not a bet

As a **bet** it is dead. The most favourable cell — under on |spread| < 3 —
hits **52.94%** (pushes excluded, n=1,936) against a 52.38% break-even. That is
0.56pp of edge, requiring ~62,000 bets to establish. Rejected outright under
`MARKET_SCREENING_RULES.md` G3.

As a **maker curve tilt** the bar is different in three ways: the hurdle is
≈ −0.06pp rather than +2.38pp, the tilt applies to *every* game rather than a
selected subset, and it changes which side of our own spread we want filled
rather than requiring us to pay to take a position. A sub-hurdle mean effect is
worthless to a bettor and usable to a quoter.

## 4. Gates

**G0 — sign persistence (2026-27, no capital).** Refit the slope on 2026-27
alone. PASS requires slope > 0. A negative slope closes this permanently.

**G1 — magnitude (2026-27).** PASS requires the 2026-27 slope ≥ +0.05, i.e. at
least the weak holdout magnitude. Only on G1 does the tilt enter the live
curve, and it enters at the **holdout** coefficient (+0.0864), not the
development one — the conservative of the two estimates.

**Until G1 passes, the tilt is logged in paper quoting only** (Stage 1 of
`SECOND_LINE.md`), where its contribution to per-fill edge is measured
separately from the rest of the curve.

## 5. Monitoring, once live

| # | metric | ALERT if |
|---|---|---|
| T1 | 2026-27 slope on \|spread\| | ≤ 0 |
| T2 | per-fill edge attributable to the tilt vs modeled | < modeled − 2 se over 500 fills |
| T3 | close-game cell (\|spread\| < 3) mean e | > 0 for a full season (sign flip) |

T1 or T3 alerting once removes the tilt from the curve; it does not suspend the
rest of the second line. Re-entry requires a new pre-registration.

## 6. Known weaknesses

1. Post-hoc discovery, both windows seen. 2026-27 is the only clean test.
2. Holdout attenuation to roughly half, and not significant.
3. |spread| correlates with team quality, so part of the gradient may be a
   team-strength artifact rather than an endgame/garbage-time mechanism. The
   frozen spec does not attempt to separate them — it prices the observed
   relationship, and G0/G1 test whether that relationship persists, not whether
   the stated mechanism is the true cause.
4. `GARBAGE_TIME.md` established that garbage-time *adjustment of team ratings*
   is worthless (RMSE change 0.003). That is a different claim from this one —
   here garbage time is a mechanism for a market error, not a correction to a
   rating — but it is a caution that the garbage-time channel has already
   failed once in this project.
