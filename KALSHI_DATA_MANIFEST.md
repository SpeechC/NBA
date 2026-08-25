# Kalshi data directory — manifest (updated 2026-08-26)

| file | league | series | content | status |
|---|---|---|---|---|
| `kalshi_nba_totals.sqlite` | **NBA** | KXNBATOTAL | curated events/markets, 2 snapshots per market, carries `tipoff_ts` + `pregame_*` enrichment | **READ-ONLY** — the fetcher's market refresh NULLs the enrichment columns (see repo DATA_DEFECT notes). `.bak-20260823` is the audit backup. |
| `kalshi_nba_candles.sqlite` | **NBA** | KXNBATOTAL | 1-min candles, 2025-10-21..2025-12-22, 4,719 markets / 429 games. Lookback runs from market CLOSE, so bars cover the LIVE GAME as well as pregame. | complete |
| `kalshi_wnba_candles.sqlite` | **WNBA** | KXWNBATOTAL | 1-min candles, 2026-04-30..2026-08-26, ~2,623 markets / 298 events, in-game bars included | fetching / complete |
| `nba_totals_*.csv` | NBA | KXNBATOTAL | ladder exports from the curated DB | static |

Rows are additionally self-labeling: every `markets` row carries
`series_ticker` (KXNBATOTAL vs KXWNBATOTAL) — join through it, never assume a
file's league from memory. Do NOT point `download_nba_totals.py` at
`kalshi_nba_totals.sqlite`; new fetches always go to fresh candle DBs.

Related non-Kalshi WNBA file (repo side):
`nba_entropy_replication/wnba_2026_halves.csv` — basketball-reference quarter
scores for the 2026 WNBA season, scraped 2026-08-26.
