# PREREG — the two |spread|-keyed adjustments to the SECOND_LINE fair-value curve

**Supersedes `PREREG_spread_tilt.md`, which specified only adjustment A.** Both
adjustments key off the same observable (|closing spread|) and both affect the
same fair-value curve, so they are frozen in one document to make their
interaction explicit and prevent double-counting.

**This authorizes nothing live.** Adjustment A is gated on 2026-27 (G1 below).
Adjustment B is a refinement of a component already specified in
`SECOND_LINE.md` and may be deployed immediately, for the reason given in §3.

---

## 1. Why one document

`|spread|` moves the total's distribution in two mechanically distinct ways, and
they are **not** the same adjustment:

| | mechanism | which moment | direction at CLOSE games |
|---|---|---|---|
| **A — mean tilt** | clock milking in close endgames costs possessions; garbage time in blowouts adds them | the **centre** | lowers the fair total |
| **B — shape (p_OT)** | overtime requires a tie, so close games have higher OT probability, and OT adds points one-sidedly | the **skew** | enlarges the Yes overpricing |

Decomposition that establishes they are separate (pooled, 9,489 games):

| \|spread\| | closing | actual | residual | **regulation** | OT rate | OT pts/game |
|---|---|---|---|---|---|---|
| 0–3 | 223.77 | 223.15 | −0.623 | **221.48** | 6.69% | **1.668** |
| 6–9 | 223.81 | 224.47 | +0.657 | 223.25 | 4.81% | 1.214 |
| 13+ | 226.07 | 228.06 | +1.996 | **227.39** | 2.52% | **0.672** |

Regulation scoring rises with |spread| at **+0.35 pts/pt (t=+7.44)**; the OT
contribution falls at **−0.053 (t=−3.83)**. Different moments, opposite signs,
regulation six times larger. A single |spread| coefficient cannot represent both.

**Interaction, stated precisely.** At the money the two adjustments **compound
on close games and partially offset on blowouts**:

| \|spread\| | A: mean tilt | A in pp | B: p_OT | B: ATM Yes overpricing | **combined** |
|---|---|---|---|---|---|
| 1.5 (p5) | −0.399 pts | −0.88pp | 6.34% | −0.97pp | **−1.85pp** |
| 6.1 (mean) | 0.000 | 0.00pp | 5.28% | −0.81pp | −0.81pp |
| 13.0 (p95) | +0.595 pts | +1.31pp | 3.69% | −0.57pp | **+0.74pp** |

A 2.6pp swing across the |spread| distribution, against a maker hurdle of
≈ −0.06pp.

## 2. Order of operations (implementation-critical)

The mixture in `kalshi_shape.py` was constructed to match the ladder's own mean
and variance. With a mean shift now present, the sequence is fixed as:

```
1  read the ladder's fitted (mu_mkt, sd_mkt)
2  mu_fair = mu_mkt
             + 1.434 * 1[CrewShock >= 0.8682]        (frozen, PROSPECTIVE.md)
             + 2.693 * 1[days_left <= 7]             (frozen, PROSPECTIVE.md)
             + tilt_A(|spread|)                      (this document, gated)
3  p = p_OT(|spread|)                                (this document)
4  build the OT mixture around (mu_fair, sd_mkt) with that p, matching those
   moments exactly -- i.e. the shape term never re-centres the curve
5  quote from the resulting per-rung probabilities
```

Step 4 must not re-derive the mean from the mixture, or A would be silently
undone.

## 3. Adjustment A — the mean tilt

**Frozen on development:**

```
tilt_A(g) = b * ( |CLOSING SPREAD_H| - 6.1142 )
```

| coefficient | value | t | use |
|---|---|---|---|
| development | +0.1825 | +3.62 | **not deployed** |
| holdout | **+0.0864** | +1.02 | **the deployment value** |

The conservative estimate is deployed because the holdout is half the
development magnitude and not significant. This is a post-hoc discovery with
both windows seen; 2026-27 is the only clean test. Full caveats carried over
from the superseded document, including that |spread| correlates with team
quality so the mechanism is not identified — only the relationship is priced.

As a **bet** it is dead: under on |spread| < 3 hits 52.94% against 52.38%
break-even, ~62,000 bets to establish, rejected under G3.

## 4. Adjustment B — game-varying p_OT in the shape term

**Frozen on development:**

```
p_OT(g) = clip( 0.066879 - 0.002306 * |CLOSING SPREAD_H|, 0.010, 0.120 )
```

slope t = −3.71. The total level is excluded: its coefficient was +0.000093
(t=+0.36), as it should be, since overtime requires a *tie*, not points.

| \|spread\| | 0 | 3 | 6 | 9 | 13 | 20 |
|---|---|---|---|---|---|---|
| p_OT | 6.69% | 6.00% | 5.30% | 4.61% | 3.69% | 2.08% |

**Corroboration, not a second model:** a purely structural form — the Gaussian
tie density scaled by the measured 1.78× end-game attractor, at the regulation
residual sd of 13.48 — reproduces this within rounding (Brier 0.04993 vs
0.04988 development, identical 0.04460 holdout). Two independent derivations
agreeing is the reason to trust the shape of the curve.

**OT points distribution, frozen (development, n=378):** mean 24.423,
sd 10.201, deciles 15 / 18 / 22 / 29 / 36. Total residual sd 18.122. Refit each
summer from completed seasons only.

**Resulting ATM Yes overpricing** (replaces the flat 0.75pp in `SECOND_LINE.md`):

| p_OT | 2.00% | 3.50% | 5.24% | 7.00% | 9.00% |
|---|---|---|---|---|---|
| overpricing | 0.31pp | 0.54pp | 0.81pp | 1.09pp | 1.40pp |

## 5. Why B deploys now and A does not

B is not a new effect. `SECOND_LINE.md` already specifies the OT mixture; B only
replaces a constant p_OT with the value implied by the game's own spread. The
underlying claim is deductive — regulation scoring is exactly Gaussian (skew
+0.066, excess kurtosis −0.002 once OT points are removed), OT adds ~24 points
one-sidedly, and the ladder quotes a symmetric distribution — and the |spread|
dependence follows from the tie density, not from a fitted regularity.

A is a fitted mean effect with a weak holdout, of exactly the profile this
project has repeatedly discarded. It waits for a clean season.

**Honesty on B's size.** Varying p_OT barely improves prediction of overtime
itself: Brier 0.04999 → 0.04988 (development), 0.04468 → 0.04460 (holdout). It
is a **25% refinement of a 0.8pp correction**, worth ±0.2pp at the extremes.
Real, free, second-order — not a discovery.

## 6. Gates and monitoring

**G1 (adjustment A only).** Refit the |spread| slope on 2026-27 alone. Enter the
curve only if slope ≥ +0.05. A slope ≤ 0 closes A permanently.

| # | metric | applies to | ALERT if |
|---|---|---|---|
| C1 | 2026-27 \|spread\| slope on the total residual | A | ≤ 0 |
| C2 | close-game cell (\|spread\| < 3) mean residual | A | > 0 for a full season |
| C3 | realized OT rate by \|spread\| quartile vs p_OT(g) | B | any quartile off by > 2pp |
| C4 | OT points mean | B | outside 22–27 for a season |
| C5 | per-fill edge attributable to each adjustment | both | < modeled − 2 se over 500 fills |

C1 or C2 removes A from the curve. C3 or C4 reverts B to the flat p_OT = 0.0524.
Neither suspends the rest of the second line. Re-entry requires a new
pre-registration.

## 7. What is prohibited

- deploying A before G1 passes
- any non-linear form, spread×total interaction, or separate close/blowout
  coefficients for either adjustment
- re-estimating either on a window containing holdout or 2026-27 data before
  the gate is evaluated
- letting the shape term re-centre the mean (§2 step 4)
- treating A and B as substitutes, or applying either to the spread or
  moneyline markets — both are specified for the TOTALS curve only
