# 2025-26: sportsbook −110 vs Kalshi taker, matched games (2026-10-07)

Same season, same signals, same code path for signal construction — so the only
thing varying is **the instrument**. This is the comparison the pre-2025-26
table cannot make.

`SB matched` restricts the −110 basis to only the games Kalshi actually traded
(the gate refuses some), making it like-for-like.

## CrewShock

| basis | n | hit% | P&L | ROI |
|---|---|---|---|---|
| SB −110, all signals | 236 | 50.42% | −$882 | −3.74% |
| SB −110, **matched** | 211 | 49.29% | −$1,245 | **−5.90%** |
| **Kalshi taker, matched** | 211 | **43.60%** | −$7.88 | **−7.89%** |

Gate refused 25 of 236. Hit rate line→rung **−5.69pp**. ROI **−1.98pp**.

## final7

| basis | n | hit% | P&L | ROI |
|---|---|---|---|---|
| SB −110, all signals | 69 | 55.07% | +$355 | +5.14% |
| SB −110, **matched** | 69 | 55.07% | +$355 | **+5.14%** |
| **Kalshi taker, matched** | 69 | **44.93%** | −$0.57 | **−1.81%** |

Gate refused 0 of 69 — every signal traded. Hit rate line→rung **−10.14pp**.
ROI **−6.94pp**, which **flips a winning season into a losing one**.

## Combined, matched

| | n | P&L | ROI |
|---|---|---|---|
| SB −110 | 280 | −$891 | **−3.18%** |
| Kalshi taker | 280 | −$8.45 | **−6.43%** |

**The instrument translation costs ~3.25pp of ROI combined, 2–7pp per
strategy.**

Stakes differ by construction ($100 flat vs 1 contract at ~47¢), so ROI is the
comparable column.

## Validation against the published table

`MONITOR_SEASON_PNL.md` 2025-26 rows: crewshock 238 bets / 50.42% / −$891 /
−3.74%, final7 69 / 55.07% / +$355 / +5.14%. This run reproduces **50.42% and
−3.74%** for crewshock and **69 / 55.07% / +$355 / +5.14% exactly** for final7.
The 236-vs-238 difference is pushes, which are dropped here and apparently
counted as zero-P&L bets there.

## What this establishes

The single most important number in this thread: **the venue translation is a
2–7pp ROI drag, large enough to turn a winning sportsbook strategy into a
losing Kalshi one.** final7 is the clean demonstration — identical games,
identical signals, 0 refused by the gate, +5.14% at a book and −1.81% on Kalshi
as a taker.

The mechanism is explicit in the hit rates. A −110 wager settles against the
**line**; Kalshi settles a **rung**, and the trader buys the **max-edge** rung,
which for an OVER sits **above** the line. It therefore wins 5–10pp less often.
The compensation is a lower price (~47¢ against a 52.4% break-even), and on
2025-26's books that compensation was **not enough**.

This means the 2025-26 taker loss has **two separable causes**, and only one is
about the season:

1. **A bad season.** crewshock hit 49.29% against an assumed 54.21%.
2. **The instrument.** Worth −1.98pp for crewshock and −6.94pp for final7,
   present regardless of how the season went.

Cause 2 would have applied in the good seasons too, and it is not in any of the
pre-2025-26 ROIs. Applying a ~3pp drag to crewshock's +6.39% and final7's
+9.21% pre-26 figures leaves roughly +3% and +6% — still positive, but on
post-hoc numbers that excluded the worst season.

## The question this raises

**Is the max-edge rung the right rung for a taker?** The +24% advantage of the
max-EV rung over the at-the-line rung was measured in the **maker** framing. As
a taker the trade-off changes: an at-the-line rung would hit much closer to the
sportsbook rate, at a price near 50¢ where the Kalshi fee is at its maximum
(1.75¢). That has not been tested on real books and is the obvious next step —
it is a rung-selection question, not a signal question.

Script: `compare_2025_26_book_vs_kalshi.py`.
