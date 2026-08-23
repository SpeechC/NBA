# MINED BOOK — unrestricted generation, frozen selection, empirical FDR

Protocol (frozen in mined_book.py before execution): mine dev <= 2023-24 over
45 cells (24 binary conditions + 21 pairs with n>=900) x {Over, Under}, bet at
the close, -110, pushes void. Selection: dev win% >= 53.5, n >= 600, win%>50
in >= 5 of 6 dev seasons, top 15 by win%. Holdout 2024-25 + 2025-26 (glimpsed
status per cell recorded). FDR: 200 permuted-dev pipelines, phantom books
evaluated on REAL holdout.

## Result, 2026-08-23 — ONE seat qualified

**4-in-6 schedule congestion (either team) x last 20% of season -> OVER**

| window | n | win% |
|---|---|---|
| development (6/6 seasons > 50%) | 770 | 54.55% |
| holdout 2024-25 + 2025-26 | 293 | 56.66% |
| pooled | 1,063 | ~55.1% (~+5.2% ROI at -110) |

FDR calibration: phantom pipelines qualify 0.2 cells on average (p95 = 1);
phantom books score mean 50.02% on the real holdout (p95 = 55.03). The real
book sits at the **97th percentile** of the noise distribution.

Caveats recorded: (1) the late-season component was GLIMPSED -- the program
already knew late-season scoring runs high (the wing rule skips selling overs
in the final week for this reason), so the holdout is not virgin for that
half of the cell; the congestion interaction is the new part. (2) One cell at
the 97th percentile is p ~ 0.03 against the honest mined null -- notable, not
conclusive. (3) ~130 bets/season: one season of paper logging gives t ~ 0.6
vs the vig, so 2026-27 confirms direction, not significance.

Disposition: seat #5 on the 2026-27 prospective watch list (paper only),
joining MOVE_COMBINED, CrewShock, the second-line curve, and maker-kappa.
Mechanism note (written post-hoc, flagged as such): late-season fatigue and
effort withdrawal on congested schedules degrade defense first.

## Pass 2 — wider inventory, 2026-08-23

Alphabet widened 24 -> 47 conditions (roadtrips, homestands, rest patterns,
win/loss streaks, signed-spread states, big line moves, tilt matchups,
referee foul-state and experience, injury counts, calendar months); pairs AND
triples admitted at the same dev n>=600 economic floor. Result: **90 cells**
total (47 singles, 41 pairs, 2 triples) — the floor, not imagination, is what
bounds the space: most new conditions are too sparse to pair and stay
tradable.

Outcome: the SAME single seat qualifies, and nothing else.

  4in6_either & late_season -> OVER   dev 54.55% (770)   holdout 56.66% (293)

FDR on the wide space: phantom pipelines qualify 0.7 cells on average (p95=2),
90 of 200 produce a book, phantom books score 50.25% mean / 53.90% p95 on the
real holdout. The real book sits at the **99th percentile**.

Interpretation: widening the search did not add seats and did not dilute the
survivor — it sharpened its calibration (97th -> 99th). Within this alphabet
and the bettable-volume floor, the mined space is SATURATED at one seat.
Further widening requires either dropping the volume floor (which breaks
bettability by our own criterion) or new data alphabets (timestamped feeds,
order flow, lineup announcements) rather than more transformations of what we
hold.

## Pass 3 — the large scan (3,527 cells), 2026-08-23

~80 conditions (sharp + dense median splits), all pairs and triples above the
dev n>=600 floor: **67 singles, 730 pairs, 2,730 triples**. Identical frozen
selection and FDR machinery.

Result: 114 qualifying cells (phantom mean 32.5, p95 70). Top-15 book by dev
win%: **holdout 52.46% seat-weighted, 52.06% deduped over 1,312 game-bets —
below the 52.38% break-even and at the 86th percentile of phantom books
(p95 = 53.73). THE PASS-3 BOOK FAILS ITS OWN CALIBRATION.**

Two diagnostics worth recording:

1. **The winner's curse, demonstrated in one table.** The pass-1/2 survivor
   (4in6 x late-season, dev 54.55, holdout 56.66) did NOT make the pass-3
   book: 3,527 cells produced fifteen cells with HIGHER dev win% (55.1-57.0),
   which displaced it -- and those fifteen then scored 52.5% on holdout. The
   bigger the scan, the higher the dev bar noise sets, and the more the
   selection favours overfit cells over robust ones. Search size DEGRADED the
   book (99th -> 86th percentile).
2. **The dev-era mirage in the book: 9 of 15 seats contain `tmove_pos`**
   ("line moved up -> bet over at close"), a close-underreaction claim the
   error-decomposition already refuted at the season scale (latent state vs
   closing error corr -0.0002). Its dev-window strength did not carry: those
   seats' holdout results scatter 49.8-61.9 around ~52.

Disposition: pass 3 book NOT adopted. Seat 5 stands on its own pass-1/2
calibration (unique qualifier, 99th percentile), unaffected by pass 3 (its
cell's numbers are unchanged; it merely lost a dev-win% beauty contest to
noise). The scaling conclusion is now empirical: in this data, mined yield
does not grow with search size -- noise does.

## Pass 3b — variant 2: threshold 53.0, full-portfolio evaluation, 2026-08-23

Operator-chosen after variant 1 failed -> meta-multiplicity acknowledged in
advance; pre-set bar raised to the 97.5th phantom percentile.

Threshold 53.0 admits **216 qualifying cells** (phantom mean 60.8, p95 119).
Top-15 book unchanged by construction (52.46%, 86th pctile). The new object:

| book | seat-weighted | **deduped (unique game-bets)** | phantom pctile |
|---|---|---|---|
| FULL portfolio (216 seats) | 52.53% on 60,657 | **50.11% on 4,073** | 93rd (bar: 97.5) |

**FAIL, decisively.** Two diagnostics:

1. **Seat-weighting was recounting, not pooling.** 60,657 seat-bets deduplicate
   to 4,073 games -- overlapping cells re-bet the same shared core ~15x. The
   52.53% seat-weighted figure is the same lucky games counted repeatedly;
   deduped, the portfolio is a coin flip (50.11%).
2. **The excess dev structure is real but non-stationary.** 216 qualifiers vs
   a phantom p95 of 119 means the dev window genuinely contains more
   >=53%-win% cells than scrambled data -- concentrated in the tmove_pos
   family -- and that structure simply does not exist in 2024-26. A dev-era
   regime feature, not a selection artifact and not a live edge.

Disposition: variant 2 not adopted. No further pass-3 variants: iterating
thresholds/book-definitions after failures is operator-level selection that
the phantom machinery cannot price. The mined program closes at: seat 5
(pass 1-2, 99th pctile) on the paper list; large-scan yield zero.
