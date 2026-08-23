# PREREG — cross-rung consistency of the Kalshi totals ladder

**Written 2026-08-23, BEFORE any pairwise rung comparison is computed.** One
descriptive pass, run once. Deductive standards: violations are counted and
sized per instance, not tested against a statistical threshold. No decision
rule promotes anything to a strategy from this document.

## 1. The invariant

Every rung is `P(total > K)` (strike_type `greater`). For strikes K1 < K2,
`Yes(K2)` implies `Yes(K1)`, so any coherent quote set must satisfy

```
P(total > K1) >= P(total > K2)          (survival monotone in strike)
```

A violation in EXECUTABLE prices is a static dominance arbitrage: buy
`Yes(K1)` at its ask, sell `Yes(K2)` at its bid. The position pays 0 outside
(K1, K2], pays +$1 inside it, and can never lose — so if

```
bid(K2) - ask(K1) > 0                    ("hard cross")
```

the trade locks a riskless credit plus a free lottery ticket on the interval.

## 2. Definitions, fixed now

- **Hard cross**: same event, same minute bar, both rungs two-sided quoted
  (bid>0, ask>0), K2 > K1, and `bid(K2) > ask(K1)`. Gross edge =
  `bid(K2) - ask(K1)` cents.
- **Net cross**: gross minus taker fees on both legs,
  `0.07*p*(1-p)` per contract per leg at the leg's own price. Only net > 0
  counts as a free lunch.
- **Soft violation**: `mid(K2) > mid(K1)` (mid = (bid+ask)/2). Not executable;
  reported separately as a coherence measure, never as an edge.
- **Adjacent** = neighbouring quoted strikes in that minute; non-adjacent
  pairs are scanned too but reported separately.
- **Persistence**: consecutive-minute run length of the same crossed pair in
  the same event. A 1-minute instance is treated as presumptively artifactual
  (see 3); runs >= 3 minutes are the interesting class.

## 3. The measurement caveat, stated before counting

Candle bars are NOT synchronous order-book snapshots. `yes_bid_close` of rung
A and `yes_ask_close` of rung B in the same minute may have been quoted up to
59 seconds apart; a quote that moved between those instants can create an
apparent cross that never existed simultaneously. THEREFORE every count in
this document is an UPPER BOUND on true synchronous arbitrage, and the
persistence classification is the primary defence: a cross that stands for
several consecutive bars is unlikely to be a within-minute sequencing
artifact. Depth is also unobserved — candles carry no size, so dollar figures
assume ONE contract per instance and are floor estimates per instance but
unknowable in aggregate capacity.

## 4. Outputs, fixed now

1. Counts: minutes scanned, minutes with any hard cross, distinct crossed
   pairs, adjacent vs non-adjacent split.
2. Magnitude: distribution of gross and net cents per instance.
3. Persistence: run-length distribution; the >= 3-minute class listed
   game-by-game.
4. Timing: crosses by hours-to-tip.
5. Same-rung sanity: any bar with bid > ask on ONE rung is a data error and
   is counted separately, never as arbitrage.
6. Economic upper bound: sum of net cents over instances at 1 contract each,
   stated with the section-3 caveats attached.

## 5. Prohibited

- promoting any count into a trading strategy from this document
- filtering, re-windowing, or re-defining after seeing the counts
- treating soft violations as money
- writing to `kalshi_nba_totals.sqlite`

## 6. Interpretation grid, fixed now

- Many hard crosses, mostly 1-minute, net ~ 0 -> the ladder is coherent and
  the candle asynchrony explains the residue. Expected outcome.
- Persistent (>=3 min) net-positive crosses in size-bearing hours -> a real
  microstructure defect worth its own follow-up prereg (with order-book data,
  not candles).
- Systematic soft violations without hard crosses -> quoting noise inside the
  spread; relevant to the maker strategy's quoting model, not an edge.

---

## 7. RESULT — run once, 2026-08-23. Verdict: LADDER COHERENT (grid row 1)

1,256,843 bars; 1,240,283 two-sided; **0 same-rung bid>ask data errors**;
203,749 (event,minute) ladders with >= 2 quoted rungs.

### Hard crosses — effectively nonexistent

| quantity | value |
|---|---|
| low-leg instances | **49** (0.022% of ladder-minutes) |
| adjacent-pair instances | 38 |
| gross cents | mean 2.59, median 1, max 18 |
| net > 0 after both legs' taker fees | **14 instances** |
| total net at 1 contract each | **$0.57 over the whole 62-date window** |
| run lengths | 39 x 1-min, 1 x 2-min, 1 x 3-min, 1 x 5-min |
| runs >= 3 min with net > 0 | **0** (both long runs net NEGATIVE: -2.24c, -2.37c) |

The persistence test — the pre-stated defence against bar asynchrony — kills
everything: the only two crosses that outlived a bar were fee-negative, and
the 1-minute residue at ~1c gross is exactly the sequencing artifact section 3
predicted. **The quoted Kalshi totals ladder admits no static dominance
arbitrage.** Fifty-seven cents of theoretical upper bound over two months does
not merit a follow-up.

### Soft inversions — the useful number

**8.63% of rung-minutes carry a mid inversion** (72,502 adjacent), with
adjacent inversion sizes of mean 7.8c, median 5c, p95 25c — while hard crosses
are ~absent. Large mid incoherence with zero executable crosses means the
inversions live entirely INSIDE wide spreads on thin rungs: the mids are
noise, the bid/ask bounds are coherent.

Two standing consequences, both descriptive:

1. **Mid-based estimators inherit this noise on thin rungs.** The L(t)
   median-crossing estimator (absorption and day-move studies) uses mids; its
   >= 4-rung / bracketed-crossing rules concentrate it near the money where
   spreads are tight, which now looks like the right design choice, but any
   future use of WING mids should treat them as +/- 5-25c objects.
2. **For the maker strategy:** resting mid-referenced quotes on thin rungs
   would be quoting against noise ~9% of the time. Quote placement should
   reference the bid/ask bounds of adjacent rungs (which ARE coherent), not
   mids.

Per section 5, nothing here is promoted to a strategy; the two consequences
above are design notes, not edges.
