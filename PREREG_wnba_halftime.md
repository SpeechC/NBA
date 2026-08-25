# PREREG — WNBA robustness test of the halftime staleness finding

**Written 2026-08-26, BEFORE candles, scores and tips are joined.** One pass.

## 0. Provenance
User-directed robustness test of the NBA finding (PREREG_kalshi_halftime s6-8:
s(H1)=0.63-0.80 vs efficient ~1.0, all game long) on an INDEPENDENT market:
Kalshi KXWNBATOTAL, full 2026 season, 298 events (2026-04-30..08-26), in-game
bars inherited from the 12h-from-close lookback. If the same under-reaction
appears in a different sport, season and trader pool, the finding is a
property of the VENUE'S live pricing, not an NBA quirk — the strongest
possible pre-2026-27 validation available.

## 1. Data and anchoring, fixed now
- Quarter scores + finals: basketball-reference scrape (line-score tables).
- No start times exist on bref for WNBA. Tip is DETECTED from candle activity
  onset and cross-validated against close_ts minus regulation duration on
  non-OT games; games where the two anchors disagree by > 12 min are DROPPED
  (count reported). Halftime window: tip+50..tip+68 min, target tip+58
  (10-minute quarters).
- pre = last usable pregame L (Kalshi's own ladder; NBA corr with book 0.992).
- L(t): the frozen median-crossing estimator, unchanged.

## 2. The regression and benchmarks
    L_half = a + b*pre + s*H1
    Benchmarks: efficient s ~ 1.0 (structural: banked points); frozen s ~ 0.
    Realized check on the scraped season: total ~ pre + H1 (s' expected ~1).

## 3. Decision, fixed now
- REPLICATES: s in [0.45, 0.85] with (s - 1)/se <= -4  -> the NBA finding is
  venue-level; both seasons' evidence pools for the 2026-27 automation case.
- EFFICIENT HERE (s >= 0.85): the NBA result is sport-specific or fragile;
  downgrade its interpretation accordingly.
- FROZEN (s < 0.45): stronger staleness in the thinner market — consistent
  with the attention thesis; report, no promotion.

## 4. Economic tail (secondary, split fixed now)
Efficient rule fit on games BEFORE 2026-07-01; traded on July-August at real
quotes with taker fees, best rung per game, the SAME fixed grid
(3/5/8/12/20c). No threshold chosen after seeing results; the NBA table's
>= 8c line is the pre-stated comparison.

## 5. Positive control (plumbing, valid under both outcomes)
corr(pregame L, bref final-total... ) is NOT valid (hypothesis-free check
needed): instead, corr(pregame L across games, Kalshi's own event strike
median) and the tip-anchor agreement rate; plus pregame L within [120, 200]
for all games. If tip anchors disagree wholesale the measurement stops.

## 6. Prohibited
Re-timing windows after results; alternative anchors after results; promoting
the economic tail; any live trading implication.
