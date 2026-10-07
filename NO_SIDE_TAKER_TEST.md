# NO side as a taker — tested before arming (2026-10-07)

Requirement: the NO side must be evaluated **from the taker standpoint** before
the trader is armed. Only PaceGap and MOVE_COMBINED ever take the UNDER, and an
UNDER is a NO buy. Two things make NO structurally worse for a taker:

- **Price.** `no_ask ≡ 1 − yes_bid`, so lifting the NO ask pays the **full**
  spread measured on the YES book. There is no separate, tighter NO book
  (identity verified on 470 live markets across 4 series, 0 violations).
- **Depth.** A NO buy consumes the **YES bid** book, and `gate()` enforces
  `MIN_BOOK_SIZE=5` in take mode.

## 1. Live depth — 26OCT07 board, 105 rungs across 5 events

| take side | consumes | size ≥ 5 | median size |
|---|---|---|---|
| YES | `yes_ask` book | 93.3% | 73 |
| **NO** | `yes_bid` book | **84.8%** | **44** |

Inside the 0.12–0.88 price band: NO size ≥ 5 on **85.0%**. Median quoted spread
**3¢**, paid in full by a NO taker.

**Depth is not the binding constraint at 1 contract.** It would be at size.

## 2. Economics on the correct book

| strategy | dir | n | pass% | ask | believed | p_emp | **EV/ct** | ROI |
|---|---|---|---|---|---|---|---|---|
| move | OVER | 17 | 43.6% | 0.476 | +3.48¢ | .5175 | **+2.31¢** | +4.67% |
| move | **UNDER** | 6 | **15.4%** | 0.447 | +2.86¢ | .4872 | **+2.30¢** | +4.95% |
| pacegap | OVER | 9 | 23.1% | 0.473 | +3.26¢ | .5216 | **+3.04¢** | +6.19% |
| pacegap | **UNDER** | 4 | **10.3%** | 0.448 | +2.21¢ | .4838 | **+1.85¢** | +3.98% |

The structural penalty shows up exactly where theory says it should — not in
per-contract EV but in the **pass rate**, which falls from 43.6%/23.1% to
15.4%/10.3%. Paying the full spread means far fewer rungs clear `MIN_EDGE`.

### Season contribution of arming the NO side, 1 contract, taker

| | trades | EV | outlay | ROI |
|---|---|---|---|---|
| **UNDER leg total** | **38** | **+$0.81** | $17.76 | +4.56% |

With an 85% depth haircut applied, and **before** one-trade-per-game claiming,
which cuts it further because UNDER competes with OVER for the same games.

## A correction made while doing this

A first pass on the 1,312 near-close `pregame_*` ladders put **UNDER above
OVER** (+4.66¢ vs +3.59¢ for move), which is structurally impossible. Same
wrong-book defect already corrected once for the OVER side: those are
near-CLOSE books being used for OPENER-settled strategies, so the gate selects
games whose line moved and grading with the unconditional `D_open` distribution
overstates the winning side. For UNDER the bias points the other way — select
games that moved **up**, overstate P(under) — which is precisely why UNDER came
out flattered. On the 09:00 ET book the ordering is correct.

## Verdict

**Arming the NO side is not worth it for the 1-contract live test.** It adds
**under one dollar** of expected season P&L, measured on **n = 10 traded
boards** — badly underpowered — and the schema is still unproven, which costs a
real order to establish.

Note what this is *not* saying: per-contract ROI on the UNDER leg (+3.98% to
+4.95%) is comparable to the OVER leg. NO is not bad economics; there is just
very little of it, because the pass rate collapses. **If size scales up, the
UNDER leg scales with it and should be revisited.**

### Two separable things, only one of which is now settled

| | status |
|---|---|
| NO-side taker **economics** | **tested** — marginal, +$0.81/season |
| NO-side **schema** (`side='ask'` buys NO) | **still unproven** — needs one real order, ~$0.23 |

The trader already refuses every UNDER while `NBA_NO_SIDE_VERIFIED` is unset,
so the live configuration needs **no change**: crewshock, final7, move-OVER and
pacegap-OVER — ~306 trades, +$6.35 expected. Nothing has been armed.

Scripts: `no_side_taker_test.py` (live depth + near-close ladders),
`no_side_taker_opener.py` (09:00 ET book, both directions).
