# Data dictionary — dfMaster_OT_2017-2026.csv

Definitions established by testing the columns against known quantities, not by
reading the names. Several names do not describe their contents.

Verified on the regular-season subset (n = 9,489) unless stated.

---

## 1. The swap pattern — affects five column families

Several paired `_H`/`_R` columns carry **either a spread or a total**, and which
one lands in which column **changes row by row**. Recover by magnitude:
`abs(v) > 60` is a total, `abs(v) <= 30` is a spread.

Affected: `LINE MOVEMENT #1/2/3`, `OPENING ODDS`, `CLOSING ODDS`, `HALFTIME`.

Evidence: `OPENING ODDS_H` token 0 has range −21.5 … 258.5 — both scales present
in one column. It equals `OPENING SPREAD_H` on only **61.7%** of rows; the rest
are totals.

## 2. `LINE MOVEMENT #1 / #2 / #3` (_H and _R)

**Sequential quotes of the FULL-GAME market**, in time order. Not quarter lines,
not period lines.

| test | result |
|---|---|
| mean value (totals) | 222.8 / 222.7 / 222.8 — full-game scale (a 1Q total would be ~56) |
| mean distance to closing total | open 2.41 → #1 0.78 → #2 0.66 → #3 0.60 |
| corr with closing total | open 0.956 → #1 0.993 → #2 0.995 → #3 0.996 |

Monotone convergence on the closing number proves these are repricings of one
market. **They carry no timestamps** — order is known, elapsed time is not.

Format is `number [juice]`, e.g. `-4.5 -15`, sometimes `215.5o15`.

Coverage after magnitude recovery: **spread path 99.1%, total path 43.7%.**

## 3. `HALFTIME_H` / `HALFTIME_R`

**Halftime-posted betting lines** (spread and total, swapping between columns).
**NOT halftime scores.**

| candidate | corr with HALFTIME_H |
|---|---|
| full-game closing spread | **−0.749** |
| 2H margin | −0.234 |
| **home halftime score** | **−0.023, 0 exact matches in 8,627 games** |

Values range −16.0 … 221.5; a score cannot be negative. `_H` and `_R` correlate
with the game spread at −0.749 / +0.734, i.e. the same line from opposite sides.

For actual halftime scores use `1Q_H + 2Q_H` (mean 57.00) and `1Q_R + 2Q_R`.

## 4. `OPENING ODDS` / `CLOSING ODDS` (_H and _R)

**The quoted number plus its juice**, as a string: token 0 is the line, token 1 is
the price (mean ≈ −10, i.e. −110 written as `-10`). Subject to the swap pattern.

**This is the only place price/juice appears.** The numeric `SPREAD` and `TOTAL`
columns carry no price. Given that −110 vs −105 is the single largest lever on
profitability, these strings are the most valuable unused data in the file.

## 5. `OPENING/CLOSING SPREAD_H`, `OPENING/CLOSING TOTAL_H`

Clean numerics, 100% populated, half-point ticks, **no swap**. These are the
columns to use. Home perspective: a spread of `-4.5` means home favoured by 4.5.

⚠ `CLOSING SPREAD_H` contains **4 contaminated rows** (−110, 110, 112, 243).
Filter `abs(spread) <= 25`. Uncleaned they inflate market margin RMSE from 13.06
to 13.46 and make the opener look more accurate than the close.

## 6. `MONEYLINE_H` / `MONEYLINE_R`

**Closing moneyline only** — there is no opening moneyline anywhere in the file.
American odds; positives may appear without a `+`. Two-way hold ≈ 4.18%.

## 7. `TOTAL MOVE`

**= closing total − opening total.** Verified: 100.00% exact match, 0 mismatches.
Redundant with a direct computation.

## 8. `SPREAD_TO_LINE` — ⚠ CONTAINS THE RESULT

**= actual total − closing total.** Verified: **corr 1.0000, 100.0% exact match.**

Despite the name it has nothing to do with spreads (corr with actual margin
0.003). It is the settled totals result and **must never be used as a feature** —
any model containing it will appear extraordinarily accurate and be worthless.

## 9. `MODEL1`, `MODEL2`, `MODEL1_SPREAD`, `MODEL2_SPREAD`, `MATCHUP_PACE`

**User-created features** (87% coverage). Definitions belong to their author;
recorded here are the observed properties only.

| column | mean | sd | range | corr w/ actual total | corr w/ total move |
|---|---|---|---|---|---|
| MODEL1 | 4,447 | 413 | 2,880–7,760 | 0.253 | 0.065 |
| MODEL2 | 399 | 24 | 296–544 | 0.273 | 0.041 |
| MODEL1_SPREAD | 4,223 | 408 | 2,659–7,505 | 0.243 | 0.059 |
| MODEL2_SPREAD | 174 | 20 | 63–294 | 0.075 | −0.087 |
| MATCHUP_PACE | 176 | 5 | 158–214 | 0.220 | 0.100 |

Scale note: none is on a spread scale, and `MATCHUP_PACE` at 176 matches neither
single-team pace (~99) nor combined (~197). All correlate 0.44–0.56 with the
closing total, so they track what the market prices, but all fall below the
closing line's own 0.49 against the actual total.

## 10. `TEAM_*_STD_*`

**`STD` = season to date, NOT standard deviation.** Rolling season-to-date means:
`TEAM_PACE_STD_H` ≈ 98.6, `TEAM_PTS_STD_H` ≈ 112.5, `TEAM_OEFF_STD_H` ≈ 113.5 —
all level-scale.

## 11. `DATASET_H` and `BIGDATABALL\nDATASET_H`

**Two season-label columns.** The first covers 2017-19, the second 2020-26.
Coalesce: `df["DATASET_H"].fillna(df["BIGDATABALL\nDATASET_H"])`. Using only the
first silently drops thousands of rows.

## 12. `GAME-ID`

Stored as an 8-digit integer with the `00` league prefix stripped. Restore with
`.astype(str).str.replace(r"\.0$","",regex=True).str.zfill(10)` to join to
stats.nba.com ids. Verified: all rows resolve to 10 chars, prefix `00`.

## 13. `TEAM REST DAYS_H` / `_R`

Categorical, conflating rest with schedule density: `B2B`, `1`, `2`, `3+`,
`3IN4`, `3IN4-B2B`, `4IN5-B2B`, `5IN6-B2B2B`.

**More accurate than deriving rest from dates** — it was computed on the complete
schedule. Date-derived rest agrees on only 92.9% of team-games, and every
disagreement is in one direction.

## 14. Columns that are empty or degraded

| column | state |
|---|---|
| `MAIN REF_H`, `CREW CHIEF_H` | **entirely empty** (0 non-null) |
| `CREW_H` | referee name, **2017-2022 only** (~4,770 games) |
| `STARTING LINEUPS_H` | **a single player name**, 181 distinct values, 2022-24 only — cannot support a lineup model |

## 15. Overtime

`OT1_H` … `OT5_R` populated for overtime games only (5.11% of rows).

⚠ A sibling file `dfMaster.csv` has **all overtime games removed**. It looks
entirely normal but drags the over rate to 47.95% and manufactures a fake under
bias. Always verify OT games are present — `accept_new_data.py` gates on this.
