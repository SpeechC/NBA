# Market-column audit — dfMaster_OT_2017-2026.csv

Full sweep of all 27 market-ish columns, 2026-08-24, after four corrupt cells
in `CLOSING SPREAD_H` were found to have fabricated an omnibus detection.

## Verdict: the corruption is EXACTLY six cells, in two columns

| column | corrupt cells | value | should be |
|---|---|---|---|
| `CLOSING SPREAD_H` (+ `_R` mirror) | 4 | -110, +110, +112, +243 | a spread |
| `OPENING TOTAL_H` (+ `_R` mirror) | 2 | 109.5, 136.5 | a full-game total |

Nothing else. Scans of every other column returned either clean or a FALSE
POSITIVE from my own gate (below). Derived `TOTAL MOVE` inherits the two
opening-total errors and needs no separate gate.

## Consistency checks all PASS — and that is the warning

```
OPENING/CLOSING SPREAD_H + _R = 0     0 violations
OPENING/CLOSING TOTAL_H = _R          0 violations
TOTAL_PTS = PTS_H + PTS_R             0 violations
TOTAL MOVE = close - open             0 violations
```

**The vendor wrote each corrupt value into BOTH sides.** Mirror-column
consistency therefore cannot detect this class of error — it is internally
consistent corruption. Only a physical-plausibility RANGE check finds it.

## Three of my own flags were FALSE POSITIVES — recorded so they are not repeated

**1. `LINE MOVEMENT #1/2/3` and `OPENING/CLOSING ODDS` are POLYMORPHIC, not corrupt.**
Each field holds whichever line moved — a spread OR a total:

| column | n | spread-like (\|v\|<=30) | total-like (150-300) | neither |
|---|---|---|---|---|
| `LINE MOVEMENT #1_H` | 6,270 | 5,569 | 701 | 0 |
| `OPENING ODDS_H` | 2,283 | 1,438 | 845 | 0 |
| `CLOSING ODDS_H` | 1,729 | 886 | 842 | 1 |

Perfectly bimodal, zero values in between. Applying a spread range gate flagged
701-725 games per column as "corrupt"; they are nothing of the kind. **These
columns need type detection before use, and no naive gate.** (The CBB file
stores the same thing as text — `'u139.5 -114'`, `'-30.5 -110'` — which makes
the polymorphism explicit.)

**2. `MONEYLINE_H/R` is CLEAN.** I flagged 511 games for "both moneylines same
sign". That was wrong: both NEGATIVE is a normal pick'em (-105/-115). Both
POSITIVE would be an arbitrage and there are **zero**. Overround: median 4.17%,
range 2.43-6.93%, no negative values.

**3. `SPREAD_TO_LINE` is a derived residual, despite the name.** It equals
`actual total - CLOSING total` on **10,383 of 10,383** rows exactly. The five
values beyond +/-70 are all overtime games (actual totals 290, 301, 310, 329,
351). Legitimate.

## Also noted

`MODEL1_SPREAD` (range 2,584-7,505) and `MODEL2_SPREAD` (63-294) are not
spreads. MODEL2 looks like a total. Vendor model columns with misleading names;
unused by this project, and not to be trusted on name alone.

## Gate set now installed (prepare_data.sanitize_market)

```
OPENING/CLOSING SPREAD_H   [-30, 30]      largest genuine line seen: 24.5
OPENING/CLOSING TOTAL_H    [150, 300]
MONEYLINE_H/R              |ML| in [100, 20000]
```

Deliberately NOT gated: the polymorphic columns, `SPREAD_TO_LINE`, and the
MODEL columns. Gating a polymorphic or derived column produces exactly the
false positives catalogued above.


## Addendum 2026-08-25 — `HALFTIME_H/R` is NOT the halftime score

corr with the true quarter-sum halftime total: **-0.056**. Coverage 27%,
sd 5.8 (a real H1 total has sd ~12.5). It is a captured LINE-like object whose
season coverage matches PREREG_h2's "2H line" table. Use `1Q_+2Q_` sums for
halftime scores. Same trap class as MODEL1_SPREAD: the name is not the
semantics.
