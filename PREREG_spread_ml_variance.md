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
