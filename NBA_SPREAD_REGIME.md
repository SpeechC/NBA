# Kalshi NBA board width — the venue question, measured (2026-08-25)

Harvested `KXNBAGAME` / `KXNBASPREAD` / `KXNBATOTAL` for 2025-10→2026-06
(34,450 markets, 12.47M one-minute candles) into `kalshi_nba_triangle.sqlite`.
This settles whether Kalshi is a cheaper venue than a −110 sportsbook for the
already-frozen totals signals in `PROSPECTIVE.md`.

## Pregame bid-ask width, NBA totals board (priced 20–80c region)

| month | games | bars | median | round trip | in points | vs book 1.08 |
|---|---|---|---|---|---|---|
| 2025-10 | 80 | 82,562 | 4.0c | 3.75c | 1.45 | worse |
| 2025-11 | 218 | 338,025 | 3.0c | 3.25c | 1.25 | worse |
| 2025-12 | 198 | 397,372 | 3.0c | 3.25c | 1.25 | worse |
| 2026-01 | 236 | 737,141 | 3.0c | 3.25c | 1.25 | worse |
| **2026-02** | 166 | 354,259 | **2.0c** | 2.75c | **1.06** | **better** |
| 2026-03 | 239 | 409,246 | 2.0c | 2.75c | 1.06 | better |
| 2026-04 | 144 | 241,445 | 2.0c | 2.75c | 1.06 | better |
| **2026-05** | 38 | 108,990 | **1.0c** | 2.25c | **0.87** | **better** |
| 2026-06 | 5 | 17,887 | 1.0c | 2.25c | 0.87 | better |

Round trip = half-spread + 1.75c fee; points = round trip / 2.59 c-per-point.

## Findings

1. **The board crossed the book in February 2026** and has stayed there.
   Feb-onward median is 2.0c across 1.13M bars = 1.06 points, just inside the
   book's 1.08.
2. **It reached 1.0c by May–June** — the WNBA level, and the structural floor
   (0.87 points), because at that width the 1.75c fee is 78% of the cost.
   May/June are playoffs (38 and 5 games), so treat 1c as demonstrated for
   high-attention games, not yet as the regular-season norm.
3. **Width is board-specific, not venue-wide.** The NBA moneyline was 1.0c in
   every month from the start; the totals board took until February to get
   there. "Kalshi is tight" is false as a generalisation — moneyline 1.0c,
   totals 1–4c, half/quarter 9–65c, team totals 39c.

## What it is worth on the frozen book

CrewShock (+1.434 pt residual): 1.33x the bar at the book, 1.35x at Kalshi's
current 2.0c, **1.65x** if the regular season settles at 1.0c.
Final-week (+2.693 pt): 2.49x at the book, 2.54x at Kalshi now.

So the venue gain is **~2% today and up to ~24% if the 1c regime holds**. Real,
worth having, and NOT transformative — the fee floor caps it. This is an
execution-venue question and therefore outside `PROSPECTIVE.md`'s prohibition,
which fences new historical conditioning/estimator tests on the signal itself.

## The measurement to repeat in October
Regular-season width at the 2026-27 open. If it opens at 1.0c rather than
retracing to 3-4c as it did in Oct 2025, the 1.65x case is live from day one.
