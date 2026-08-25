"""
===============================================================================
 LOOK-AHEAD DECOMPOSITION — where the original +25.8% actually came from
===============================================================================
 The cleanest possible test of whether the original profitable backtest
 contained anything real. Hold EVERYTHING constant -- same games, same bets,
 same rungs, same sides, same outcomes, same hit rate -- and change only the
 ENTRY PRICE: the mis-anchored (pre-tipoff) quote the original pipeline used,
 versus the quote at the REAL halftime (ESPN clock).

 RESULT (2026-08-25), 23 bets, 78% hit rate in BOTH columns:

                        anchored (pregame)    true halftime
   mean entry cost            0.622               0.786
   total P&L (1 ct)           +3.69               -0.07
   ROI                       +25.8%               -0.4%

 The market had already moved +0.163/contract between the two moments.
 Claimed edges averaged 0.253. So roughly two-thirds of the "edge" was simply
 the repricing that had ALREADY happened once the first half was played, and
 the remaining third was model noise that the spread consumes.

 The 78% hit rate was never fake -- the model really did predict direction.
 It predicted it because it knew the first-half score. So did the market, by
 halftime, and it had already charged for it. Profit is hit rate measured
 against the price you PAY, and that price was 16 cents higher in reality.

 Read-only. Reproduces from the session transcript's inline run.
===============================================================================
"""
