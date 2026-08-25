"""
===============================================================================
 DO SPORTSBOOKS PRICE GAMMA CORRECTLY AT HALFTIME?
===============================================================================
 DESIGN. Kalshi quotes a FULL-GAME total, so its halftime line loads H1 at
 1+gamma. A book quotes a SECOND-HALF total, which should load H1 at gamma
 itself. Both therefore sit on one comparable scale.

 THE IDENTIFICATION TRAP. If gamma is truly ~0, a correctly-priced HALFTIME
 line and a line merely POSTED PREGAME both show a ~0 coefficient on H1. A
 null is ambiguous, so timing must be proven before the coefficient means
 anything. Discriminator used: a pregame line cannot know the halftime
 MARGIN. If the line responds to |margin|, it was set after H1 was played.

 RESULTS (2026-08-25), master HALFTIME_H/R 2H totals, n=4,385 (46% coverage):

 1. It IS a 2H total line: mean 110.8 vs mean realized H2 110.4.
 2. It IS set at halftime: |margin| coefficient -0.0252 (t=-4.1), R^2 on pre
    alone only 0.777, and it beats a pregame-only rule at predicting H2
    (RMSE 12.03 vs 12.44). All three say it carries in-game information.
 3. gamma_book  = -0.0352 (se .0036, t=-9.7)   [stable: -0.025 2017-19,
                                                -0.042 2020s]
    gamma_true  = -0.0029 (se .0162)
    gamma_kalshi= -0.1380

 READING. Books price phantom reversion too -- but roughly a QUARTER of
 Kalshi's dose. Book error -0.032, Kalshi error -0.135. On the full-game
 scale that is book s=0.965 vs Kalshi s=0.862.

 ECONOMICS. The cross-market divergence is 0.103 of gamma x sd(H1 surprise)
 ~12.1 = 1.25 points = 3.2c on Kalshi's 2.59c/pt ladder, against a Kalshi
 taker round trip of 8.9c plus the book's own vig (~0.7 pts). Ratio ~0.3:
 dead as a taker, exactly like every other version of this trade.

 CAVEAT THAT CUTS BOTH WAYS. Kalshi's -0.138 rests on the bracketed sample,
 whose attrition biases s DOWNWARD (nba_stress_test.py s C). The book's
 0.965 is a plausible estimate of where Kalshi's true value would sit if the
 dropped games could be included -- i.e. part of the 0.103 gap may be our
 measurement, not their mispricing.

 Read-only.
===============================================================================
"""
