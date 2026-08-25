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
