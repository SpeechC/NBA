"""
===============================================================================
 MODEL-FREE CONTROL — the last surviving economic cell is an overs regime
===============================================================================
 On the ESPN true clock, one cell still showed profit: WNBA best-rung >=8c,
 21 trades, 86% hit, +24% ROI (2026-08-05..20, the only walk-forward-tradeable
 window after the 80-game warmup). 18 of its 21 bets were YES.

 Control: in the SAME games, at the SAME timestamps and quotes, buy YES at
 EVERY rung asked 45-88c — no model at all. Result: 96 bets, 75% hit vs 66%
 break-even, +13.1% ROI, because 75% of quoted mid-range rungs resolved OVER
 in that fortnight. A no-skill rule captures over half the cell's return; the
 remainder is best-rung selection plus a 16-cell search (2 clearing zero is
 chance). The cell is a hot-overs stretch, not an edge.
===============================================================================
"""
# Analysis preserved from the audit session transcript (2026-08-25); rerun by
# reproducing the snippet in the commit message / session log. Kept as a
# documented negative control alongside halftime_econ_audit.py.
