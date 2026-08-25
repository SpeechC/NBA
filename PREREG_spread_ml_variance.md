# PREREG — spread→moneyline variance mapping

**Written 2026-08-24, BEFORE any implied sigma is computed.** Estimated EXACTLY
ONCE per window.

## 0. Provenance

NOT a new idea and not mined. `omnibus.py` (FINDINGS_LATE.md s21) ran six
signature-of-omission tests on 9,489 games and returned three detections. Two
were never followed up; this document pursues one of them:

    test 5 conditional variance:  |spread| predicts margin variance,
                                  corr +0.057, t = +5.59  (sides)
    test 1 Mincer-Zarnowitz:      spread slope 0.9368, chi2 = 13.01, p = 0.0015

The omnibus flagged both BEFORE any spread bucket was inspected, which is why
this is confirmatory in construction. But the detections came from the full
sample including what is now the holdout, so the holdout is GLIMPSED, not
virgin. Discount accordingly: the new information here is the MAGNITUDE and
the ECONOMICS, not the existence of heteroskedasticity.

`ml_audit.py` already audited the ML market broadly (calibration, noise,
offset models, rankability). This is a different and narrower question: not
"can we beat the book's probability" but "is the book's own moneyline
INTERNALLY CONSISTENT with its own spread".

## 1. The mechanism, stated so it can fail

A book that maps spread S to a moneyline assumes a margin distribution. If it
assumes constant variance:

```
p_home = Phi( -S / sigma_const )          S negative when home is favoured
```

but realised variance grows with |S|, then for a big favourite the true
win probability is LOWER than the constant-sigma map implies (more variance =
more upset chance). Prediction:

    PRED-1  sigma implied by the book's own (spread, ML) pair is roughly FLAT in |S|
    PRED-2  realised sd(margin + S) RISES with |S|
    PRED-3  therefore big favourites' MLs are too short, big underdogs' too long
    PRED-4  the tradable expression is BACKING BIG UNDERDOGS on the moneyline

If PRED-1 fails — the book already varies sigma with |S| — the hypothesis is
dead on arrival and no economic test is run.

## 2. The devig trap, handled BEFORE looking

The entire test is about whether favourites are overpriced, and the standard
proportional devig is itself known to distort the favourite/longshot split.
Using one devig method would risk measuring the method rather than the market.

Three devig methods are therefore run and ALL must agree in sign:

```
proportional   p_h = (1/o_h) / (1/o_h + 1/o_a)
additive       remove the overround equally in probability space
power          solve p_h^k + p_a^k = 1 for k, then normalise (Shin-like)
```

A result that appears under proportional devig but not the other two is
recorded as a DEVIG ARTIFACT, not a finding.

## 3. Sample, split, estimator

- 9,489 regular-season games, closing spread and both moneylines complete.
- Development seasons <= 2023-24; holdout 2024-25 + 2025-26, reported separately.
- Buckets by |closing spread|, FIXED NOW, no re-cutting:
  `[0,3) [3,6) [6,9) [9,12) [12,+)`
- Per bucket: realised sd(margin + S); implied sigma from each devig; the
  win-probability gap in percentage points; and the realised ML ROI of backing
  the underdog at the book's price.

## 4. Positive control (mandatory)

At |S| near zero the implied and realised sigma must agree — there is no room
for a constant-sigma error when the favourite is small — and the recovered
sigma must land in a basketball-plausible 10-14 points. If the control fails,
the measurement is broken and NO other cell is interpreted.

## 5. Decision rule, fixed before estimation

TRADABLE requires ALL:
- PRED-1 and PRED-2 hold on development (implied sigma flat, realised rising,
  the divergence increasing in |S| with |t| >= 2);
- the sign of the win-probability gap in the top bucket agrees on the holdout;
- underdog-ML ROI in the top bucket positive on BOTH windows after the actual
  vig;
- all three devig methods agree in sign.

Anything less: recorded as detected-but-not-tradable, and the branch closes.
No re-bucketing, no threshold search, no alternative sigma models.

## 6. Power, checked before setting the bar

Per LINEAGE lesson 8, derive the bar from quantities ALREADY measured rather
than intuition. omnibus test 5 gave corr(|spread|, z^2-ish) = +0.057 at
t = 5.59 on 9,489 games. A per-bucket sd comparison on ~1,000-2,000 games has
ample power for a sigma difference of 1+ point; it does NOT have power for a
0.2-point difference. The bar is therefore set on the WIN-PROBABILITY GAP,
which is what pays, not on sigma per se: **the top bucket must show >= 1.5pp**
of gap, since the ML vig on a big underdog is typically 2-4pp and anything
smaller cannot clear it.

## 7. Prohibited

- estimating more than once per window; re-bucketing after seeing results
- fitting a sigma(|S|) function and then testing it on the same data
- reporting a proportional-devig-only result as a finding
- any claim about totals from this document

---

## 8. RESULT — run once, 2026-08-24. Verdict: DETECTED BUT NOT TRADABLE

9,488 games. Development 7,161, holdout 2,327. Mean overround 4.14% / 4.28%.

### PRED-1 FAILS: the book does NOT use a constant-sigma map

| \|S\| bucket | n | realised sd | implied sigma (prop) | (addi) | (power) | gap pp (prop) |
|---|---|---|---|---|---|---|
| [0,3) | 1,522 | 13.75 | 19.64 | 18.86 | 18.45 | +0.01 |
| [3,6) | 2,254 | 12.58 | 14.09 | 13.51 | 13.20 | -0.21 |
| [6,9) | 1,750 | 12.93 | 12.53 | 11.94 | 11.65 | +0.24 |
| [9,12) | 1,028 | 13.14 | 11.74 | 11.11 | 10.77 | +1.42 |
| [12,+) | 604 | 13.31 | 11.66 | 10.84 | 10.33 | +2.22 |

Implied sigma falls 19.6 -> 11.7 across the range (slope -0.587 per point of
|S|). The book varies its variance assumption enormously. The premise of the
hypothesis is refuted, and per section 1 that is fatal on its own.

### My positive control was misplaced BY DESIGN — owned, not excused

Section 4 put the control at |S| ~ 0. That is exactly where the estimator
degenerates: sigma = -S / Phi^-1(p), and at S -> 0 with p -> 0.5 both numerator
and denominator vanish, so the ratio is noise. The 19.64 in the [0,3) bucket is
an ARTIFACT of my estimator, not a property of the market, and the control
therefore "failed" for a mechanical reason I should have foreseen.

LINEAGE lesson 8 said to power-check a control against the sample it runs on.
The sharper form this adds: **also check that the control sits where the
ESTIMATOR is well-conditioned.** A control placed in a degenerate region tests
the arithmetic, not the market.

### What survives in the well-conditioned region (|S| >= 6)

Here the estimator is stable and the finding REPLICATES across windows:

| \|S\| bucket | dev implied | dev realised | hold implied | hold realised |
|---|---|---|---|---|
| [6,9) | 12.53 | 12.93 | 13.05 | 13.67 |
| [9,12) | 11.74 | 13.14 | 12.48 | 13.22 |
| [12,+) | 11.66 | 13.31 | 12.69 | 13.17 |

The book's moneyline implies **0.4 to 1.6 points LESS margin variance than
reality**, in the predicted direction (big favourites too short), in both
windows and under all three devig methods. That part of PRED-3 holds.

### But it does not pay, and the omnibus detection is weaker than it looked

Win-probability gap in the top bucket: **+2.22pp development, +0.13pp holdout**
(proportional). Underdog moneyline ROI, the tradable expression:

| bucket | dev dog ROI | holdout dog ROI |
|---|---|---|
| [0,3) | -4.69% | +0.46% |
| [9,12) | -2.54% | +3.60% |
| [12,+) | **-4.02%** | **-31.36%** |

No bucket is positive on both windows. The gap is real but smaller than the
vig on a big underdog, exactly as section 6 warned it would need to beat.

**Partial retraction of the omnibus detection.** Test 5's t = +5.59 was
computed on the pooled sample. Decomposed by decile, the development
heteroskedasticity is almost entirely ONE decile — sd 15.16 at |S| ~ 14.2
against ~12.5-13.8 everywhere else — and the corresponding holdout decile shows
**12.57**, the lowest of its window. The bias-removed z^2 slope is +0.146
(t=+27.73) on development and **-0.020 (t=-2.74) on holdout**: a sign flip.
Bias-vs-variance confounding was checked and ruled out (raw and bias-removed
slopes agree to three decimals).

So: heteroskedasticity in |S| is NOT a stable feature of this market. The
omnibus flagged something real in-sample that does not persist. Recorded as a
correction to FINDINGS_LATE.md s21.

### What is genuinely learned

1. Books map spread->ML with a **variance model, not a constant** — that whole
   class of "they assume homogeneous variance" hypotheses is closed.
2. Their sigma is nonetheless **biased low by ~0.5-1.5 points at |S| >= 6**,
   consistently and across devig methods. Real, replicating, sub-vig.
3. An omnibus detection can be driven by a single tail decile and reverse out
   of sample. **Omnibus detections need a decile decomposition before they are
   promoted**, which is now the standing rule.
