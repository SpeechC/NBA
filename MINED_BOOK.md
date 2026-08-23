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
