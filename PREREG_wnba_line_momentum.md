# PREREG — WNBA halftime LINE MOMENTUM (shadow ledger, log-only)

**DRAFT written 2026-08-25, before any game in the test window. Not frozen
until David signs off; if games run before freezing, they count only if the
rule text was unchanged.**

## 0. Provenance — stated against ourselves
Third candidate pattern found on the 2026 season data in one day, after two
died (the staleness artifact; the August overs cell). It is EXPLORATORY and
this document exists so the remaining ~47 games can adjudicate it
prospectively. Source: `halftime_dispersion_test.py` — regressing
(total − L_half) on (E − L_half) with E the naive pre/H1 fair value gives
kappa = −1.0 (se .32, t=−3.1 with month FE, stable across season halves).
Interpretation: the halftime line's deviation from naive fair value carries
real information (in-half events the two-variable model cannot see) and is
UNDERWEIGHTED — the outcome continues past the line in the line's own
direction, roughly point-for-point. Noise biases (LOO-E attenuation; shared-L
measurement error, which pushes kappa positive) work AGAINST the finding.
NBA shows NO such pattern (kappa +0.25 ± 0.24, sign-unstable) — this is
registered for the WNBA only.

## 1. The rule, fixed now
At the FIRST monitor poll at or after real halftime (score feed trigger, the
monitor's existing halftime detection):
- E  = frozen deployment rule (wnba_deploy_rule.json — unchanged, s4/s11).
- L  = median-crossing line on that poll's logged ladder (frozen estimator).
- dev = L − E.
- If dev >= +3: shadow-buy YES at the crossing rung's logged ask.
  If dev <= −3: shadow-buy NO at the crossing rung's logged bid.
  |dev| < 3: no entry. Secondary bands reported, not promoted: 2 and 5 pts.
- Cost = quote + 0.07·q·(1−q) taker fee. One entry per game. OT included.

## 2. Endpoints, fixed now
- PRIMARY: directional hit rate of the dev side at the 3-pt band vs the
  cost-implied break-even of the actual entries (~55% at mid-priced rungs).
- Net P&L per contract with fees at logged quotes.
- The OPPOSITE ledger (the deployed fade rule's would-trades, already logged)
  graded on the same games — kappa < 0 predicts it hits BELOW 50% in-band.

## 3. Decision, fixed now
~47 games remain; expected in-band n ≈ 12–20. That cannot reach significance;
the season yields a DIRECTION CHECK only:
- hit >= 60% in-band: pattern survives; write the NBA-October variant's
  prereg only if NBA data then shows kappa < 0 too (it currently does not).
- hit in (45%, 60%): unresolved; archive, revisit only with a second season.
- hit <= 45%: dead; record and close.
No threshold may be re-chosen after results; the 3-pt band is primary
regardless of which band looks best.

## 4. Boundary
Shadow ledger graded from the monitor's append-only JSONL by
`wnba_reconcile.py` at season end. NO trading: the component remains
OBSERVER (spec s5); this prereg authorizes measurement only.
