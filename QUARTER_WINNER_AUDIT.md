# Quarter-winner mechanics — Stage 1 PASS, Stage 2 FAIL (2026-08-26)

Two-stage by design, in the order the Kalshi halftime failure taught: prove
the mechanical fact first (free), then gate on EXECUTION before building any
model. The gate stopped this one.

## Stage 1 — the mechanical fact is real and strong (9,216 games, 8 seasons)

Trailing team's Q4 margin, by size of its deficit after three quarters:

| Q3 deficit | n | trailing team's mean Q4 margin | t | trailing team wins Q4 |
|---|---|---|---|---|
| 1-4 | 1,703 | -0.127 | -0.7 | 49.2% |
| 4-8 | 1,953 | +1.103 | 6.5 | 53.6% |
| 8-12 | 1,678 | +1.196 | 6.3 | 55.7% |
| 12-16 | 1,331 | +1.448 | 6.5 | 57.6% |
| 16-20 | 958 | +1.459 | 5.8 | 59.6% |
| **20+** | **1,593** | **+1.945** | **9.6** | **61.1%** |

Monotone in deficit size, exactly as the garbage-time mechanism predicts, and
**positive in all 8 seasons** at leads >= 12 (55.7%-62.8%, pooled 59.5%, mean
margin +1.65). The 1-4 bucket sitting at ~50% is the mechanism's own control:
close games have no garbage time and show no effect.

This is one of the strongest raw regularities the program has measured. It is
also, almost certainly, common knowledge among anyone pricing quarter markets
— which is why Stage 2 exists.

## Stage 2 — EXECUTION GATE: the market does not exist to trade

Series discovery across the plausible tickers:

```
KXNBA4QWINNER / KXNBAQ4 / KXNBAQUARTER   none
KXNBAHALF / KXNBA2H / KXNBA1H / KXNBAQ1  none
KXWNBA4QWINNER                           200 markets, ALL finalized
                                         volume: median 0, max 0, 200/200 at ZERO
                                         active now: 0
```

**Kalshi lists no NBA quarter or half markets at all**, and its WNBA
quarter-winner series has never traded a single contract across 200 settled
markets. There is no venue here. A model built on Stage 1 would have had
nowhere to express itself.

## Verdict and the process point

Branch closed on execution, not on the mechanism. Recorded because the
sequencing is the lesson: the halftime-staleness work built a model, a
backtest, a dashboard and a monitor before execution reality was tested, and
execution is what killed it. Here the same gate cost one API call and ran
BEFORE any modelling.

**Standing rule: for any derivative-market candidate, verify the market
exists, trades, and has depth BEFORE building anything on the underlying
regularity.**

Not closed: the same mechanical fact expressed on a venue that does trade
quarters (sportsbook quarter lines are not in our data and would need
acquisition). Its prior should be poor — a 60% regularity this visible is the
kind of thing a quarter-line maker prices first — but the gate that failed
here was availability, not efficiency.
