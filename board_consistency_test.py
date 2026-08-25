"""
===============================================================================
 CROSS-BOARD CONSISTENCY — does Kalshi's full-game board agree with its 2H board?
===============================================================================
 At halftime H1 is a KNOWN CONSTANT, so the identity
     L_full  =  H1 + L_2H
 must hold by arithmetic, not forecast. Any violation is a model-free,
 same-venue, same-fee two-legged trade. Our gamma work said the full-game
 board underweights H1; if the 2H board prices H2 cleanly the error shows up
 here directly.

 Data: KXWNBA2HTOTAL harvested 2026-08-25 (444 events / 1,626 markets /
 226,153 candles) joined to KXWNBATOTAL and the ESPN true halftime clock.
 2H boards only launched ~2026-08-05, so the overlap is 27 games.

 RESULTS (2026-08-25):

 1. THE BOARDS AGREE. gap = L_full - (H1 + L_2H): mean -0.16 pts, median
    -0.19, sd 1.25, and |gap| > 3 pts in 0% of games. There is no
    internal arbitrage -- something (a maker, or arbitrageurs) keeps the two
    boards aligned.

 2. IT DOWNGRADES THE GAMMA FINDING AGAIN. The gap's H1 coefficient is
    -0.052 (se .024, t=-2.1), NOT the -0.14 the full-board regression
    implied. This is a CLEANER estimate of the full board's error: both
    boards are read by the same estimator, at the same instant, on the same
    games, so measurement biases largely cancel -- and the 2H board has no
    H1 to underweight by construction. It corroborates the attrition caveat
    in nba_stress_test.py: the true error is nearer 0.05 than 0.14.

 3. THE 2H BOARD IS UNTRADEABLE. Spread at halftime: full-game 1.8c,
    2H 28.9c. It narrows from 41-60c pregame but stays ~20x the edge.
    Edge 0.052 x 9.9 sd = 0.52 pts = 1.3c against an 18.8c two-leg round
    trip. edge/cost = 0.07. Dead by a factor of 14.

 4. THE FINDING WORTH CARRYING FORWARD: the WNBA full-game board is quoted
    1.8c wide at halftime, against 14.3c measured on NBA Oct-Dec 2025. If
    NBA spreads have since tightened toward WNBA levels, the taker
    arithmetic that killed the NBA trade changes materially -- a 0.14 error
    is 4.3c against a ~2.7c round trip at 1.8c spreads. The NBA spread data
    is 8 months stale; re-measure it in October before concluding anything.

 Read-only.
===============================================================================
"""
