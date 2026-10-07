# Taker P&L with the bounds-only anchor — 2025-26 (2026-10-07)

The live configuration exactly as it now stands: **price paid is the ask**, fee
charged, **(μ, σ) from executable bounds only** — no midpoint anywhere — the
reference line per strategy as `signals()` sets it, drift guard, max-edge rung,
`MIN_EDGE` and price band, settled against the actual final total.

| strategy | ref | book | sig | traded | hit% | ask | off | P&L | outlay | **ROI** | feas% |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **crewshock** | Kalshi μ | pregame | 238 | **236** | 46.19% | 0.464 | +1.54 | **−$4.69** | $113.69 | **−4.13%** | 74.2% |
| **final7** | Kalshi μ | pregame | 69 | **69** | 46.38% | 0.454 | +1.98 | **−$0.52** | $32.52 | **−1.61%** | 63.8% |
| move | opener | 09:00 | 179 | **1** | — | 0.490 | +0.00 | +$0.49 | $0.51 | *unusable* | 100% |
| pacegap | opener | 09:00 | — | — | — | — | — | — | — | **not replayed** | — |
| **TOTAL** | | | | **306** | | | | **−$4.72** | $146.72 | **−3.22%** |

Excluding move's single trade — which is one game and tells us nothing — the
total is **−$5.21 on 305 trades, ROI −3.56%**.

`feas%` is how often the bounds identified set was non-empty. The remaining
26% / 36% used the hinge-loss fallback, which is what keeps the anchor always
defined rather than dropping those signals.

## What is and isn't measurable

- **crewshock and final7** cover the full season on the correct book
  (close-settled, filled late → the pregame snapshot). These are solid.
- **move** settles against the opener and fills 09:00 ET, so its correct book is
  the 1-minute candle reconstruction — which exists for only **54 events** and
  overlaps its 179 OVER signals on **one** game. Not measurable.
- **pacegap** cannot be replayed at all: its signal is `E_pace` from the frozen
  engine and there is no per-game 2025-26 export. Verified — no CSV in the repo
  carries an `E_pace` column and `pace_signal.py` writes none. Reconstructing it
  means running `frozen_models` walk-forward across the season.

## Against the other numbers

| | figure | basis |
|---|---|---|
| original projection | **+$6.35, +4.35%** | EV under each strategy's *published* hit rate |
| old mid anchor | crewshock −5.96%, final7 +3.89% | realised, mid-derived reference |
| **new bounds anchor** | **crewshock −4.13%, final7 −1.61%, total −3.22%** | realised, executable-only |
| sportsbook −110, same games | **−3.18%** | matched-game comparison |

Two things follow.

**The venue is neutral.** Kalshi taker **−3.22%** against the sportsbook's
**−3.18%** on the same strategies and season. Within noise of each other, as
the break-even arithmetic predicted (−110 at 52.381% versus a ~50.6¢ contract
plus fee at ~52.5%).

**The loss is the season, not the venue and not the anchor.** The projection
assumed crewshock at 54.21%; the rung hit rate came in at **46.19%** against a
break-even near 52.5%. `MONITOR_SEASON_PNL.md` already flags 2025-26 as the
season crewshock's mechanism weakened (`b_fouls` 0.4775 against a prior-seven
range of 0.79–1.36) with its most bets ever, 238.

## The standing caveat still binds

One season, and the same replay has moved several points of ROI on estimator
details alone — the sportsbook-close reference swung −7.89% → −4.75% purely from
a σ grid step and the hinge fallback. **These numbers cannot adjudicate between
configurations.** What they do establish is that the *currently armed*
configuration, measured honestly at the ask with no midpoint, returned
**−3.22%** on the one season with Kalshi books.

Script: `taker_pnl_new_anchor.py`. Supersedes the per-strategy table in
`TAKER_ECONOMICS_2026_27.md`, which used a mid-derived reference and the
sportsbook close.
