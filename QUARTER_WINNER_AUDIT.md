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

---

## ADDENDUM 2026-08-26 — the SYNTHETIC Q4 market (user's construction)

Stage 2 failed on venue availability, but buying the TOTAL after Q3 is a
synthetic Q4 bet: three quarters are banked, so `L_q3 - Q123` is the market's
implied Q4 scoring. That venue does exist and does trade. Tested on the WNBA
in-game candles, 119 non-OT games, end-of-Q3 window fixed before running
(conv-38..-26 min, target -32; WNBA plays 10-minute quarters).

### It is mostly the SAME staleness, measured later

    L_q3 = a + 0.767*pre + 0.354*Q123        se 0.038,  (s-1)/se = -17.1

Kalshi gives three banked quarters only **35%** weight — versus 28% at
halftime. So the post-Q3 price is the halftime finding continued, not a new
phenomenon: the market never catches up to the scoreboard at any checkpoint.
Implied Q4 averages 42.12 against a realized 43.76 (**+1.64 points low**),
which is the same direction and roughly the same size as the halftime lag.

### The garbage-time asymmetry does NOT show through

The Stage-1 mechanism predicts the gap should GROW with the Q3 lead (bigger
lead -> more garbage time -> trailing team pads -> higher Q4). It does not:

| Q3 lead | n | implied Q4 | actual Q4 | gap | t |
|---|---|---|---|---|---|
| 0-6 | 45 | 44.15 | 43.78 | -0.37 | -0.3 |
| 6-12 | 26 | 40.16 | 45.38 | +5.22 | +2.6 |
| **12+** | **48** | **41.28** | **42.85** | **+1.57** | **+1.1** |

Non-monotone, and the largest-lead bucket — where Stage 1's effect is
STRONGEST (61.1% at 20+ in the NBA) — shows the weaker gap. The 6-12 cell at
t=2.6 is one bucket of three on 26 games; with the neighbours at -0.3 and
+1.1 it reads as noise, and promoting it would be exactly the cell-picking the
program's phantom-book work exists to prevent.

### Verdict

The synthetic Q4 market is a real, tradable venue — the user was right that it
exists where the explicit quarter market does not. But what it contains is the
ALREADY-KNOWN in-game staleness, not a separately priced garbage-time
omission. It therefore inherits that finding's fate: the halftime version of
this exact edge failed on execution, and nothing here suggests the post-Q3
version would fare differently, on a venue with the same ~15c in-game spreads.

Closed as a distinct candidate. The staleness result itself already stands
recorded in PREREG_kalshi_halftime.md s7 (the checkpoint trajectory), where
Q3 was measured at s=0.629 in the NBA — consistent with the 0.354 here, given
the WNBA is the thinner market.

---

## CORRECTION 2026-08-26 — my Stage-2 gate was wrong twice

The user pushed on whether spread/quarter ladders exist. Enumerating
`/series` (rather than guessing tickers) shows they largely DO:

```
KXNBA3QWINNER      NBA 3rd Quarter Winner
KXWNBA1QWINNER     Women's 1st Quarter Winner        477 markets
KXWNBA1HWINNER     Women's 1st Half Winner           500 markets
KXWNBA2HWINNER     Women's 2nd Half Winner           498 markets
KXNBA2HSPREAD      Pro Basketball 2nd Half Spread    (listed; no live markets)
```

**Error 1 — I probed guessed tickers.** Stage 2 tested KXNBA4QWINNER / KXNBAQ4
/ KXNBAQUARTER and concluded "no NBA quarter markets exist." The actual ticker
is KXNBA3QWINNER, and half-winner and 2H-SPREAD series exist too. Enumerating
the series index is the correct discovery method and costs one call.

**Error 2 — the "zero volume" was an API artifact.** I read
`volume: 0 / max 0 / zero-vol 200/200` as a dead market. But the same field
returns `None` for **KXWNBATOTAL** — the ladder we independently know traded
heavily all season (median 3,743 contracts in the halftime window, measured
from CANDLES). The listing and single-market endpoints simply do not populate
volume/open_interest/liquidity for this account or these series; my summing
turned `None` into 0.

**Volume must be measured from CANDLE data, never from the market listing.**
That is how the totals depth was measured correctly earlier in this thread;
I failed to apply the same standard when gating quarter markets.

### Status of the branch

REOPENED as untested rather than closed. What the corrected gate establishes:
the venues exist and quote two-sided (2-12c spreads on active markets, touch
sizes $3-$1,749). What remains genuinely unknown: whether they TRADE, which
requires fetching their candles — the same method that answered it for totals.

The Stage-1 mechanical finding is unaffected: trailing teams outscore leaders
by +1.65 at leads >= 12, monotone, 8/8 seasons.

The standing rule survives and is sharpened: verify a derivative market
exists, trades and has depth before modelling — but verify EXISTENCE by
enumerating the series index, and verify TRADING from candles, not from a
listing field that may be null.
