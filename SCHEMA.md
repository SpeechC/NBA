# NBA Betting Model — Data Schema & Context

Reference doc for an agent picking up this project cold. Describes what data
exists, its grain, how the pieces join, and the traps.

**Last updated:** 2026-08-10
**Changes this revision:** odds coverage corrected (starts 2017-18, not 2018-19;
two seasons missing entirely) · GAME-ID join verified empirically · team
name→ID mapping built · overtime-file trap documented · closing-spread
contamination documented · new §10 empirical benchmarks · new §11 negative
results already established.

---

## 1. Project goal

Build an NBA model and test it against historical closing lines. **The objective
is closing-line value (CLV), not moneyline win probability** — CLV has far lower
variance than P&L and is the leading indicator of a real edge.

Working assumption, stated up front: NBA markets are efficient and this most
likely shows no edge. A clean negative result is a valid outcome. Do not tune
until something looks profitable — that's how you manufacture overfitting.

Six seasons of testing against full-game closing lines have already produced a
negative result (see §11). The live hypothesis is now **totals line movement**,
where a real but sub-vig signal exists.

---

## 2. Data sources

| Source | What | Grain | Coverage | Cost |
|---|---|---|---|---|
| shufinskiy/nba_data `nbastats` | stats.nba.com play-by-play | event | 1996-97 → 2024-25 | free |
| shufinskiy/nba_data `pbpstats` | pbpstats.com possession data | possession | 2000-01 → 2024-25 | free |
| `nba_on_court` package | derives on-court lineups from pbp | event | any pbp | free |
| BigDataBall | team box scores + **odds** | game | **2017-18 → 2023-24, with gaps** | paid |

**In use: 2017-18 through 2024-25 — 8 seasons, 10,206 games, ~4.8M event rows.**

### ⚠ The joinable window is 6 seasons, not 8

pbp covers 8 seasons; odds cover 6. Verified row counts in the odds file:

| season | odds rows |
|---|---|
| 2017-18 | 1,312 |
| 2018-19 | 1,312 |
| **2019-20** | **0 — absent entirely** |
| 2020-21 | 1,171 |
| 2021-22 | 1,323 |
| 2022-23 | 1,320 |
| 2023-24 | 1,314 |
| **2024-25** | **0 — absent entirely** |

Two consequences. Odds start a season *earlier* than previously documented
(2017-18 is free). And 2019-20 — the bubble season, the worst COVID distortion —
cannot enter any market-tested model, which removes that concern for joined work
but not for pbp-only work.

### Dead ends — do not retry

- **stats.nba.com / data.nba.com direct API calls fail from this machine.**
  403 from data.nba.com, non-JSON body from stats.nba.com. `nba_api` and
  pbpstats `source="web"` do not work here. Everything must come from
  pre-downloaded files.
- **The pbpstats `data.zip` archive is abandoned** — `Last-Modified` 2023-04-11,
  709 MB, stops mid-2022-23 (881 of 1,230 regular season games, no playoffs).
  Superseded by the shufinskiy pipeline. If `c:\NBA2\data\response_data` still
  exists it can be deleted.
- **2025-26 is not available from any free source.** BigDataBall only. Not
  currently needed.

---

## 3. File layout

```
c:\NBA2\
  dfMaster.csv                   # ⚠ OVERTIME GAMES REMOVED — do not use
  dfMaster_OT.csv                # complete odds file — use this one
  nba_data\                      # shufinskiy CSVs (downloaded)
    nbastats_2017.csv            # regular season, start year
    nbastats_po_2017.csv         # playoffs
    pbpstats_2017.csv
    pbpstats_po_2017.csv
    ...through 2024
  out\                           # built parquet
    pbp_lineups_2017-18_rg.parquet
    pbp_lineups_2017-18_po.parquet
    ...
    notes_<season>_<rg|po>.csv
```

Season files are named by **start year**: `2022` = the 2022-23 season.

**Working copies belong on the Linux filesystem, not `/mnt/c`.** That mount is
`drvfs` (the WSL2 Windows bridge) and is ~11x slower on every read. Converting to
Parquet on the Linux side is another ~2x, and column-pruned scans ~21x total.
`pbp_ingest.py` handles both.

---

## 4. Key conventions

### Game IDs — 10-char zero-padded strings, NEVER integers

```
0021800764
││└┴─────── 18    = season start year (2018-19)
│└───────── 2     = season type
└┴───────── 00    = league (00 NBA, 10 WNBA, 20 G-League)
     └────── 00764 = sequential game number
```

Season type digit: `1` preseason, `2` regular season, `3` all-star,
`4` playoffs, `5` play-in.

CSV round-trips strip the leading zeros. Always read as string or re-pad:

```python
df["GAME_ID"] = df["GAME_ID"].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(10)
```

### ✅ The odds ↔ pbp GAME_ID join is verified

BigDataBall stores the id as an integer with the `00` league prefix stripped;
`zfill(10)` restores the stats.nba.com form. **Confirmed across all 7,752 rows**:
every one yields prefix `00`, and the type digit decodes correctly —
7,226 type-2 (regular), 502 type-4 (playoff), 24 type-5 (play-in). Round-trip
check: `0021700001` → regular season 2017-18 game 1, row date 2017-10-17. ✓

Helper: `team_mapping.game_id()` / `team_mapping.decode_game_id()`.

### Player and team IDs

stats.nba.com integer IDs throughout (e.g. Curry = 201939). Stable across
seasons; the join key between every source. Player *names* are not unique and
must not be used as keys.

### Season strings

Two formats coexist. Source filenames use start year (`2022`); output files and
season columns use `2022-23`. Convert deliberately.

---

## 5. Schemas

### 5.1 `nbastats_*.csv` — event grain, 34 columns

~470 rows per game. Raw stats.nba.com PlayByPlayV2.

| Column | Notes |
|---|---|
| `GAME_ID` | see ID conventions above |
| `EVENTNUM` | sequence within game; sort key |
| `EVENTMSGTYPE` | event category — see codes below |
| `EVENTMSGACTIONTYPE` | subtype, meaning depends on EVENTMSGTYPE |
| `PERIOD` | 1-4 regulation, 5+ overtime |
| `WCTIMESTRING` | wall clock |
| `PCTIMESTRING` | game clock remaining in period, `MM:SS` **string** |
| `HOMEDESCRIPTION` / `NEUTRALDESCRIPTION` / `VISITORDESCRIPTION` | free text; exactly one usually populated. **Join key to pbpstats.** |
| `SCORE` | `"102 - 99"` string, only on scoring events, else null |
| `SCOREMARGIN` | string, `"TIE"` for 0 — not numeric |
| `PERSON1TYPE`, `PLAYER1_ID`, `PLAYER1_NAME`, `PLAYER1_TEAM_ID`, `PLAYER1_TEAM_CITY`, `PLAYER1_TEAM_NICKNAME`, `PLAYER1_TEAM_ABBREVIATION` | primary actor |
| `PERSON2TYPE`, `PLAYER2_*` | secondary actor (assist, rebounder, fouled player) |
| `PERSON3TYPE`, `PLAYER3_*` | tertiary actor |
| `VIDEO_AVAILABLE_FLAG` | ignore |

**`EVENTMSGTYPE` codes** (confirm with `value_counts()` before relying on any
single one):

| Code | Event | | Code | Event |
|---|---|---|---|---|
| 1 | made field goal | | 8 | substitution |
| 2 | missed field goal | | 9 | timeout |
| 3 | free throw | | 10 | jump ball |
| 4 | rebound | | 11 | ejection |
| 5 | turnover | | 12 | period start |
| 6 | foul | | 13 | period end |
| 7 | violation | | | |

Gotchas: `PCTIMESTRING` and `SCOREMARGIN` are strings. Free throws are separate
rows from the foul that caused them. And-1s are a made FG plus a foul plus an FT,
all separate rows.

### 5.2 `pbpstats_*.csv` — possession grain, 19 columns

~200 rows per game (both teams combined).

| Column | Notes |
|---|---|
| `GAMEID` | **note: no underscore**, unlike nbastats `GAME_ID` |
| `PERIOD` | |
| `STARTTIME` / `ENDTIME` | clock remaining at possession start/end |
| `STARTTYPE` | how the possession began — the distinctive value here |
| `STARTSCOREDIFFERENTIAL` | score margin from offense's perspective at start |
| `OPPONENT` | defending team abbreviation |
| `FG2A`, `FG2M`, `FG3A`, `FG3M` | possession totals |
| `OFFENSIVEREBOUNDS`, `TURNOVERS` | |
| `SHOOTINGFOULSDRAWN`, `NONSHOOTINGFOULSTHATRESULTEDINFTS` | |
| `EVENTS` | text of all actions in the possession |
| `DESCRIPTION` | text of one action — the join key |
| `GAMEDATE`, `URL` | |

`STARTTYPE` is categorical (`OffAtRimMiss`, `OffLiveBallTurnover`, `OffDeadBall`,
…). **Enumerate the actual set with `value_counts()`** — the vocabulary is not
formally documented.

### 5.3 `pbp_lineups_<season>_<rg|po>.parquet` — built output

**Event grain.** 63 columns. Column order pinned: nbastats columns, then
possession columns, then `PLAYER1`-`PLAYER10`.

Measured on 2017-18 regular season:

| Metric | Value |
|---|---|
| rows | 562,110 (input row count preserved exactly) |
| games | 1,230, 0 dropped |
| rows with 10 distinct on-court players | 100.00% |
| games with any possession data | 90.6% |
| rows with `STARTTYPE` populated | 76.7% |
| events/game | median 454, min 355, max 604 |

Possession columns are sparse, and that is expected. Two separate effects:

- **~9% of games have no possession data at all.** `left_join_nbastats()` changed
  the row count for those games, so the build fell back to unmerged play-by-play
  and nulled the possession columns rather than dropping the game. Listed in
  `notes_<season>.csv` with reason `merge_rowcount`.
- **Within a merged game, only ~85% of rows get possession fields.** Possession
  data attaches to event rows corresponding to an action. Substitutions,
  timeouts, period start/end have no counterpart and stay null. Possession
  attributes are **NOT** filled down across every event in the possession.

**Implication for aggregating to possession grain:** do not group and take first
value — most rows in a possession are null. Either forward-fill within
`(GAME_ID, PERIOD)` after sorting by `EVENTNUM`, or use non-null `STARTTYPE` rows
as possession boundaries and assign membership from there. Verify either approach
against a known game before trusting it.

Stored at event grain because it can always be collapsed and never un-collapsed.

`PLAYER1`-`PLAYER10` are **not** split home/away by position — they are 10 IDs in
arbitrary order. Determine team membership by joining player IDs to team via
`PLAYER1_TEAM_ID` or a roster table.

**Free validation target:** the odds file carries `POSS_H`/`POSS_R` per game.
Reconstructed possession counts should match to within a possession or two. Most
projects don't get ground truth for possession parsing — use it.

### 5.3b `notes_<season>_<rg|po>.csv`

One row per game that had any issue. Columns: `game_id`, `reason`, `dropped`.

- `dropped == True` → game absent from the parquet (only from a
  `players_on_court()` failure; none observed in 2017-18)
- `dropped == False` → game IS in the parquet, but with null possession columns

**Open question:** whether the ~9% of games missing possession data are random or
systematic (clustered by date, team, or arena). If systematic, possession-derived
features carry a selection bias. Not yet checked.

### 5.4 BigDataBall odds file — game grain

Wide format, one row per game, home fields suffixed `_H` and road `_R`.
**Covers 2017-18 → 2023-24 with two seasons missing entirely (see §2).**

#### ⚠ Use `dfMaster_OT.csv`, not `dfMaster.csv`

`dfMaster.csv` has **all overtime games removed** — 380 games, 5.3% of the
regular season. This is not random: OT games average a **245.5** total vs 221.8
for regulation games, so the file systematically excludes the highest-scoring
outcomes. Consequences, measured:

| | `dfMaster.csv` | `dfMaster_OT.csv` |
|---|---|---|
| seasons complete? | 4.7–8.5% short | 1230/1230, 1080/1080 ✓ |
| OVER rate vs closing total | **47.95%** | **50.08%** ✓ |
| mean(actual − closing total) | −0.82 | +0.44 |

Grading totals on the OT-free file is ex-post selection and manufactures a fake
~0.8-point under bias. Spreads are unaffected (dropping OT removes near-zero
margins symmetrically: home ATS cover 49.29%).

#### Betting columns

| Column | Notes |
|---|---|
| `GAME-ID` | ✅ joins via `zfill(10)` — verified, see §4 |
| `TEAM_H`, `TEAM_R` | full city names. ✅ mapping table now exists (`team_mapping.py`) |
| `OPENING SPREAD_H`, `OPENING TOTAL_H` | clean |
| `CLOSING SPREAD_H` | ⚠ **4 contaminated rows** (values −110, 110, 112, 243 — juice and totals leaking in). Filter `abs(spread) <= 25`. Uncleaned they inflate market margin RMSE from **13.06 → 13.46** and make the *opening* line look more accurate than the closing line, which is backwards. |
| `CLOSING TOTAL_H` | clean; filter `between(150, 300)` defensively |
| `MONEYLINE_H`, `MONEYLINE_R` | American odds. Positive values may appear without `+` (`711` = `+711`) |
| `LINE MOVEMENT #1/2/3_H` and `_R` | ⚠ **spread and total swap columns row by row.** Recover by magnitude: `abs(v) > 100` is a total, `abs(v) <= 30` is a spread. Format is `"-4.5 -15"` (number + juice) or `"215.5o15"`. Coverage after recovery: totals 63%, spreads 99%. |
| `OPENING ODDS_H` / `CLOSING ODDS_H` | spread quote with juice; second token is the price |
| `MAIN REF_H`, `CREW CHIEF_H` | ⚠ **entirely empty** (0 non-null) |
| `CREW_H` | referee name; covers 2017-2022 only (4,770 games), null thereafter |
| `STARTING LINEUPS_H` | ⚠ **degraded — a single player name per game**, 181 distinct values across 2,456 games, 2022-24 only. Cannot support a personnel model. |
| `TEAM REST DAYS_H/_R` | categorical, conflates rest with density: `B2B`, `1`, `2`, `3+`, `3IN4`, `3IN4-B2B`, `4IN5-B2B`, `5IN6-B2B2B`. **More accurate than date arithmetic** — see §7. |
| `F_H`, `F_R` | final scores |
| Box score | `FG/FGA/3P/3PA/FT/FTA/OR/DR/TOT/A/PF/ST/TO/BL/PTS`, plus `POSS`, `PACE`, `OEFF`, `DEFF` |
| `DATASET_H` **and** `BIGDATABALL\nDATASET_H` | ⚠ **season labels live in two columns.** The first covers 2017-19, the second 2020-24. Coalesce: `df["DATASET_H"].fillna(df["BIGDATABALL\nDATASET_H"])`. Using only the first silently drops 4,811 rows. |

Verified identities: `PTS = POSS × OEFF / 100` exactly; `DEFF_H` equals the
opponent's `OEFF`. The 2023-24 In-Season Tournament games carry their own label
(`NBA 2023 In-Season Tournament`, 58–64 games) and are regular-season games — a
`"Regular Season"` string filter drops them.

**CSV parsing:** the header row contains embedded newlines inside quoted fields,
which defeats DuckDB's dialect sniffer *and* makes `wc -l` undercount. Use an
explicit dialect with `strict_mode=false`. `pbp_ingest.reader()` cascades through
the options automatically.

---

## 6. Joining

```
nbastats.GAME_ID ─┬─ pbpstats.GAMEID          (via description text, lossy)
                  ├─ odds.GAME-ID              ✅ VERIFIED: zfill(10)
                  └─ PLAYER*_ID → roster/team mapping

odds.TEAM_H (name) ──> stats.nba.com team_id   ✅ BUILT: team_mapping.py
```

`team_mapping.py` maps all 30 franchise names → abbreviation → `team_id`, zero
unmapped. **No relocations or renames inside the 2017-2025 window** (Brooklyn
2012, New Orleans 2013, Charlotte 2014 all predate it), so a single static table
is safe.

⚠ The `team_id` values are asserted from reference knowledge, not derived from
the files. Run `team_mapping.verify(pbp_path)` against real pbp — it checks them
against `PLAYER1_TEAM_ID`/`PLAYER1_TEAM_ABBREVIATION` — before using as a join
key.

---

## 7. Known problems — read before modeling

**COVID seasons distort home-court advantage.** 2019-20 was cut short and
finished in the Orlando bubble (64-75 games/team, neutral-site, no crowd).
2020-21 was 72 games with arenas empty or capacity-limited. Fit per season, add a
crowd-status indicator, or exclude. Note 2019-20 has **no odds at all**, so it
cannot contaminate market-tested work; 2020-21 can and does.

**Overtime removal in `dfMaster.csv`.** See §5.4. The single most damaging trap in
this dataset — it silently biases every totals result.

**Closing-spread contamination.** 4 rows. See §5.4.

**Rest days: trust the label, not the dates.** `TEAM REST DAYS` was computed on
the full schedule before OT games were stripped, making it *more* accurate than
anything derivable from date gaps in the OT-free file. Date-derived rest agrees
with the label on only 92.9% of team-games, and **every disagreement is in one
direction** (derived rest too high) because the previous game is missing. Use the
date gap only as a *detector*: where derived rest exceeds the label, a game has
been removed and the team's previous *location* is unknown — which matters for
travel features. On the complete file this drops from 8.1% to 2.6% of team-games.

**The pbpstats merge is text-based and lossy.** `left_join_nbastats()` keys on
event description strings because possession rows carry no event ID. The author's
own wording is "almost no errors." Always check what fraction of `STARTTYPE` is
populated after merging.

**Lineup assignment can fail.** `players_on_court()` infers period starters by
walking substitution events. Validate that every event row has 10 distinct
non-null player IDs before trusting lineup-based features.

**Season length varies.** 1,230 regular season games normally; 1,059 in 2019-20;
1,080 in 2020-21. Never hardcode 82 games or 1,230.

**Play-in games exist from 2020-21** (type `5`) and are neither regular season nor
playoffs. The odds file has 24 of them, so inclusion is a real choice, not a data
constraint.

---

## 8. Modeling notes

**Walk-forward only.** Any team rating must be computed from games strictly
before the game being predicted.

**Account for burn-in once, across the whole chain.** Nested stages each consume
sample: a score model (2,000 team-games) feeding a calibration (800) feeding a
movement model (2,000) consumed ~4,700 of 7,200 games and silently reduced a
5-season backtest to 1.2 seasons — which flipped the apparent result. Run the
chain in one pass and print the first prediction date at every stage.

**Orthogonalize any signal against the line before bucketing it.** A model
forecast minus the line is typically ~−0.94 correlated with the line itself, so
bucketing raw disagreement sorts games by *how big a favourite is*, not by how
much the model disagrees. Regress the forecast on the line and use the residual.

**Regression is a screening tool, not a scoreboard.** Squared error on margin
rewards predicting blowouts; a bet only cares which side of one number the game
lands on. A t-statistic of +3.09 coexisted here with probability forecasts that
lose to a coin flip. Adjudicate on decision metrics.

**Metric priority:** (1) CLV and beat-the-close rate — continuous, highest power
per game, hardest to fool; (2) log loss and Brier vs the *no-vig* closing line;
(3) win rate and bootstrapped ROI with intervals; (4) Kelly growth last, since
sizing never creates edge.

**Sizing.** Fractional Kelly (¼ or less). A model with real but noisy edge
estimates loses a bankroll at quarter-Kelly across a few thousand bets while
maintaining a 58% win rate. Relevant here: our own edge estimate moved 0.9
percentage points on a rounding-level pipeline change.

**Realistic ceiling.** Documented professional edges are a few percent ROI over
thousands of bets. Anything showing 15%+ ROI in backtest is a bug.

**Multiplicity.** ~15 strategy variants have already been evaluated on this
sample. Pre-register the next test; picking the best-looking variant is exactly
the error that produced the source paper's non-replicating headline claim.

---

## 9. Environment

- Windows, Anaconda env `Core`, Python 3.11 (build side)
- WSL2 Linux venv at `/home/dpope/nba_env` (analysis side): pandas 3.0.5,
  numpy 2.5.2, scikit-learn 1.9.0, xgboost, scipy, pyarrow 25.0.0, duckdb 1.5.5,
  polars 1.43.2
- Spyder IDE; scripts are plain `.py` with a config block at top, no argparse
- Multiprocessing uses spawn — parallel code must run as a script
- No network access to nba.com from Python; GitHub and S3 work
- **BLAS oversubscription:** running N processes each spawning 12 BLAS threads
  thrashes a 12-core box (~10x slowdown observed). Pin `OMP_NUM_THREADS=1` and
  take parallelism from running seasons side by side.

---

## 10. Empirical benchmarks — the numbers to beat

Measured on the complete odds file, regular season, cleaned.

| Quantity | Value |
|---|---|
| **closing total RMSE** | **18.09** |
| **closing margin RMSE** | **13.06** |
| opening total RMSE | 18.46 |
| opening margin RMSE | 13.22 |
| SD of a team's game score | 12.72 |
| RMSE of "team's season-to-date average" | 12.32 (R² = 6.2%) |
| best replication model, team score | 12.23 (R² = 7.6%) |
| best model, game total | 19.31 |
| best model, game margin | 14.43 |
| spread movement SD (close − open) | 1.98 |
| total movement SD | 3.09 |

**Read the third and fourth rows together.** A whole ML apparatus buys 1.4
percentage points of R² over a running average. That ceiling explains every
downstream negative result.

**CLV → ROI conversion.** On totals (residual SD ~18), CLV of C points buys
roughly C/18 sigma of edge. Break-even at −110 is 52.38% and requires **~1.35
points of CLV**; at −105, ~0.69 points. Each percentage point of win rate is
worth ~1.91% ROI, so 52.65% → +0.51% and 53.59% → +2.31%.

**Quarter structure** (regulation games, share of closing total): Q1 0.2525,
Q2 0.2518, Q3 0.2502, **Q4 0.2419**. Scoring drifts down; quarters are not
fungible quarters of the total.

---

## 11. Negative results already established — do not redo

Six seasons, walk-forward, graded against closing lines.

| Tested | Result |
|---|---|
| Paper's box-score model (13 lagged features) vs spread/total | No edge. Probability forecasts lose to a coin flip (log loss 0.6934–0.6947 vs 0.69315). |
| Opponent pace/efficiency added | First statistically real signal (t = +3.09) but ~1/10th the magnitude to clear vig. |
| Rest, travel, back-to-backs | Real on scoring (B2B −1.3 pts, 4-in-5 −2.6) — **fully priced**. Joint mean t² = 0.49 across 13 schedule variables (noise gives 1.0). |
| Home stands / road trips | Apparent 2.04-pt effect is home-court advantage in disguise. Within venue: +0.26 deep in a home stand, +0.19 deep in a road trip. Nothing. |
| Referees (`CREW_H`) | Real on fouls and FTA (p < 0.001) — **fully priced** (excess total p = 0.281). |
| Longer / decayed lag windows (10, 20, ewm) | No improvement over lag 4 for movement prediction. |
| Opponent-adjusted pace × efficiency (ridge) | Beats every lagged-mean alternative on accuracy (19.81) but **not** the incumbent (19.31), which already carries opponent features. |
| Within-game mean reversion | None. Scoring is mildly *persistent* (AR(1) +0.048). First half → second half is **−0.0004**. 97.8% of a quarter's deviation is noise. |
| Line-movement momentum | corr(early move, later move) = **0.010**. By the 3rd intermediate quote, 96.5% of the final move has happened. Staged modelling is dead. |
| Totals **outcome** prediction | All variants \|t\| < 1.3, sign-flipping buckets. Nothing. |

**The one live signal:** totals **line movement**. CLV +0.588 overall
(CI [0.502, 0.674], n=5,112) and +1.357 at \|pred\|>1, **positive in 5 of 5
seasons**, scaling monotonically with predicted magnitude. But win rate is 52.85%
against a 52.38% break-even — ROI +0.89%, P(ROI>0) ≈ 62%, and season ROI swings
−10.5% to +10.0%. Real information, ~half the magnitude needed at −110; viable at
−105 or on an exchange (+3.2% to +4.6% on the same bets).

Feature importance in that model: only three inputs clear the noise floor —
the model's disagreement with the opening total, own pace, and **opponent pace**.
Which is why possession-level and personnel data are the next lever: pace is
what the signal runs on.
