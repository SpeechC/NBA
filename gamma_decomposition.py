"""
===============================================================================
 H1 -> H2 CARRYOVER (gamma) — is there momentum or reversion to price?
===============================================================================
 H2 = c0 + c1*pre + gamma*H1. Momentum: gamma>0. Reversion: gamma<0.
 The efficient halftime line loads H1 at s = 1+gamma, so the market-implied
 gamma is s_market - 1. This measures the real one.

 RESULTS (2026-08-25):

 NBA, 9,489 games / 8 seasons:
   gamma = -0.0029 (se 0.0107) — ZERO, at high precision. H2 residual by
   H1-surprise quintile, from a -16pt cold half to a +18pt hot half:
   +0.08 / -0.15 / +0.12 / +0.13 / -0.17 pts. Flat. No momentum, no
   reversion, no nonlinearity (sur^2, surXmargin both zero). c1(pre)=0.483,
   the structural half. Halves are independent given the pregame expectation.

 WNBA 2026, 59 games with a Kalshi pregame line:
   gamma = -0.030 (se 0.115) — same picture, underpowered.

 THE INVERSION: the market is the one that believes in reversion.
   NBA market-implied gamma (s=0.862, measured sample) = -0.14 against a
   reality of -0.003. The under-reaction IS phantom mean-reversion: the
   market expects hot halves to cool and cold halves to warm, and they do
   not. WNBA prices gamma ~ 0, correctly.

 Two small real conditional effects, both inside transaction costs:
   - garbage time: |H1 margin| ADDS scoring, +0.075/pt (se .018, t~4) —
     a 20-pt blowout adds ~1.5 pts of H2. The market's line carries +0.007
     (se .025) on the same variable: unpriced, worth ~1-2 pts at the tails.
   - pace persistence at quarter level: Q2 ~ Q1 coef +0.055 (se .010).

 Read-only.
===============================================================================
"""
