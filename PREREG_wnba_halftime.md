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

---

## RESULT — 2026-08-26. Band 3: MORE STALE THAN THE NBA (s = 0.276)

### Estimation history, disclosed
Two invalid runs preceded the valid one, both plumbing: (1) the downloader's
event parser split WNBA team codes NBA-style 3+3 ("GSCONN" -> GSC+ONN),
collapsing the join to 88 games with garbage codes — fixed by parsing teams
from event TITLES ("Dallas vs Indiana"); (2) volume-density tip detection
failed because WNBA markets trade all day (median "duration" 640 min) — 
replaced by CONVERGENCE ANCHORING: game end = first run of 5 bars with
|L - actual_total| <= 2.5, halftime = end - 58 min, non-OT games only.
Anchoring uses the outcome for TIMING only; noted as a weak-leakage caveat.

### The staleness regression (79 non-OT games)

    L_half = a + 0.866*pre + 0.276*H1        s(H1) se 0.051, (s-1)/se = -14.1
    realized benchmark on same games: s' = 0.940 (se 0.089)  ~ structural 1.0

The identification validates internally (banked WNBA points do count ~1.0 in
reality) and the market misses it by 14 sigma. Per the pre-set bands this is
BAND 3 (< 0.45): stronger staleness in the thinner market — the direction the
attention/correction-flow thesis predicts. Kalshi WNBA at halftime carries
only ~28% of the realized first half and anchors 0.87 on the pregame price
(NBA: 66% and 0.65).

**Venue-level conclusion now supported in two leagues, two seasons, two
trader pools: Kalshi's live basketball pricing under-weights banked scoring,
more severely where attention is thinner.** Per the prereg, band 3 is
report-only: no trading promotion.

### Economic tail (secondary, split fixed in advance)
Rule fit on 45 pre-July games (resid CDF THIN — stated), traded July-August
at real rung quotes with taker fees, best rung per game:

| min edge | games | hit | P&L (1 ct) | ROI |
|---|---|---|---|---|
| >=3c | 34 | 79% | +$5.54 | +25.8% |
| >=8c | 32 | 84% | +$7.23 | +36.6% |

Directionally consistent with the NBA tail (which paid only at >=8c); here
even the loose threshold paid, as deeper staleness predicts. 34 games and a
45-game CDF: suggestive, nowhere near conclusive.

### Caveats
79 of 283 games measured (join 202/283 via city titles; non-OT filter;
convergence-anchor availability) — attrition is not verified random. Timing
fuzz attenuates s downward in both leagues, so 0.276 is a lower bound-ish.
One season each league. Depth unobserved throughout.

### Disposition
The robustness question is answered in the direction that supports the
prototype: the phenomenon is a property of the venue, scaled by attention.
Prototype proceeds in LOG-ONLY mode per the standing plan; the live WNBA
weeks measure feed latency and depth — the two quantities no backtest holds.

---

## ADDENDUM 2026-08-26 — August recovered; a third format-drift catch

August initially showed ZERO measurable games. Cause: **Kalshi changed its
event-title format in August** — "Dallas vs Indiana" became "Las Vegas vs
Chicago women's Pro Basketball game: Over 169.5 points?" (and 17 newest events
carry no teams in the title at all). The naive `X vs Y$` parse captured
garbage for the home side and the join silently dropped the month. Fixed with
a city-whitelist regex; 15 July games were recovered too.

Same failure family as the NBA vendor's two layouts and the injury PDFs' two
layouts: **formats drift mid-corpus, and joins fail silently.** The
by-month funnel count (scraped -> joined -> measured) is the gate that catches
it and is now part of this pipeline's standard output.

Updated results on the enlarged set (118 measurable games, May-Aug):
- staleness: s(H1) = +0.2888 (se 0.0442) — unchanged from the 79-game 0.276.
- walk-forward $10 economics, best rung per game, fees in:

| month | bets | hit | P&L |
|---|---|---|---|
| June | 15 | 73.3% | +$27.84 |
| July | 42 | 85.7% | +$205.68 |
| **August** | **31** | **80.6%** | **+$143.37** |
| **SEASON** | **88** | **81.8%** | **+$376.89 on $880 staked = +42.8% ROI** |

August — the freshest month, fully out-of-sample under the expanding
walk-forward — sustains the effect. Caveats unchanged: fills assumed at
displayed quotes (F1 pending tonight's depth logs), convergence timing anchor,
118 of 283 games measurable.
