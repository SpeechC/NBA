# CrewShock live pipeline — operating runbook

**`crewshock_live.py` still places no bets.** It contains no order-placement
code and none is to be added here; it writes an append-only CSV log. That part
is unchanged.

**What changed (2026-09-12):** a separate module, `nba_live_trader.py`, reads
this log and places Kalshi orders from it. The "no capital in 2026-27"
constraint in `PREREG_crewshock_forward.md` §1 and §6 is **reversed by
`AMENDMENT_live_trading.md`** — read it before running anything armed. The
estimator, threshold (0.8682), shrinkage and team-state definitions are
untouched, and the separation is deliberate: the signal module cannot trade and
the trading module cannot compute a signal.

CrewShock is **OVER-only**, so it needs only the proven YES order path and can
arm before the other two. Governing documents: `PREREG_crewshock_forward.md`,
`AMENDMENT_live_trading.md`.

## Status

| item | state |
|---|---|
| estimator port | **validated**, reproduces `ref_features.csv` at max\|diff\| 1.8e-09 |
| pending path (unplayed games) | **validated**, max\|diff\| 5.2e-10 |
| officials feed | `official.nba.com` API, live, 9/9 games on a test date |
| foul-history feed | BigDataBall season-to-date (`dfMaster_2027.csv`) — **not yet present** |
| first scoreable date | **2026-10-20** (season opener) |

## Daily sequence, once the season starts

```bash
/home/dpope/nba_env/bin/python crewshock_live.py validate
```

Run once before opening night. It must print `OVERALL: PASS`. If it does not,
stop — the port has drifted from the frozen artifact.

```bash
cd /home/dpope/projects/nba_entropy_replication && /home/dpope/nba_env/bin/python crewshock_live.py daily
```

Run **late morning ET**, after assignments post and before tip. Scores today's
slate and appends to `crewshock_live_log.csv`. Add `--date YYYY-MM-DD` to
target another day, `--lines lines.csv` (columns `gid,total`) to record the
total at log time.

```bash
cd /home/dpope/projects/nba_entropy_replication && /home/dpope/nba_env/bin/python crewshock_live.py grade --results results.csv
```

Run the next morning. `results.csv` needs `gid,closing_total,actual_total`.
Appends settled rows to `crewshock_live_ledger.csv`.

## Hard stops — do not work around any of these

1. **`validate` fails.** The port no longer matches the frozen estimator.
2. **Stale history.** If `dfMaster_2027.csv` has not been updated since the
   last slate, official histories are a day behind. Skip the run; do not score
   on stale data.
3. **Zero assignment rows.** The API returns `rows: []` for a bad date format
   as readily as for a genuinely empty slate. The date parameter must be
   `YYYY-MM-DD`; `MM-DD-YYYY` silently returns nothing.
4. **`DATA_GAP` rows.** An official whose name cannot be resolved against the
   history contributes 0, biasing CrewShock toward zero. Those games are
   flagged and never actioned. If gaps appear repeatedly, a new official has
   entered the league or a spelling has changed — reconcile before trusting
   any score involving that crew.

## The one defect this build already caught

`official.nba.com` writes `JT Orr`; BigDataBall writes `J.T. Orr`. Unmatched,
that zeroes an official's entire 60-game history. It mis-scored a real slate by
up to 6.8e-02 before canonical matching was added. **Any new name mismatch
fails the same silent way** — which is why `DATA_GAP` exists and why it blocks
action rather than warning.

## What the season can and cannot decide

Fixed in `PREREG_crewshock_forward.md` §4–§6 and repeated here so it is not
relitigated in April:

- **PRIMARY is the mechanism**, `b_fouls` on ~1,230 games. Intact if
  z ≥ −1.5 (b ≥ 0.775); break confirmed if z ≤ −2.5 (b ≤ 0.568); otherwise
  ambiguous.
- **SECONDARY is `c_market`.** If the market starts pricing CrewShock, the
  branch closes regardless of the mechanism.
- **The P&L is tertiary and cannot settle anything.** At ~200 bets its ROI
  interval is roughly ±6.6pp and will not exclude zero whatever happens. This is
  *more* true now that capital is deployed, not less: a profitable season is not
  evidence the mechanism survived, and M1/M2 remain the endpoints that decide it.
- ~~No capital in 2026-27 under any outcome.~~ **Reversed 2026-09-12** — see
  `AMENDMENT_live_trading.md` §1. The reversal changes nothing about §4–§6
  above; the mechanism test is still primary and the P&L still settles nothing.

## Scheduling

Not yet scheduled. Games begin 2026-10-20. When ready, the `daily` and `grade`
commands above are what a cron entry should call; both are idempotent per date
apart from appending to the log, and both are safe to re-run.
