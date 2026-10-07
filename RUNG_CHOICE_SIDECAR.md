# Rung-choice sidecar — settling rung selection out of sample (2026-10-07)

**Reporting only. It does not change what the trader buys.**

## Why

The trader buys the **max-edge** rung. That rule's advantage was measured in
maker framing on synthetic boards where the pricing model was correct by
construction — `maker_figure_provenance.py` draws truth and market from the same
normal with the same σ, so maximising modelled EV had to win. On real 2025-26
books as a taker it did **worse** than simply buying the rung nearest the line:

| | max-edge | nearest-line |
|---|---|---|
| crewshock | −7.89% | **−4.73%** |
| final7 | −1.81% | **+5.96%** |

But the paired test over one season is **not significant** (t +0.79 and +1.16),
so the rule is unproven rather than refuted. Logging both choices settles it
out of sample at zero cost and zero risk.

## What is logged

Three rules per signal, to `~/data/nba_rung_choice.csv`:

| rule | definition |
|---|---|
| `maxedge` | highest taker edge among gated candidates — **what is actually traded** |
| `nearline` | nearest strike to the reference line, **among gated** candidates |
| `nearline_all` | nearest strike to the line among all in-band candidates, **gate bypassed** |

22 columns: timestamps, strategy, game, event, direction, `ref_line`, `mu_hat`,
`mu_mkt`, `sigma_mkt`, candidate counts, and per rule the ticker, strike,
`offset_pts`, price, `p_model`, `edge`, plus `is_traded`, `rules_agree` and
`would_gate`.

`nearline_all` exists because **testing found a flaw in the first version.**
`nearline` is the nearest rung *that passes `MIN_EDGE`*, and on a ladder where
the at-the-line rung fails that gate it falls back to something far away — a
synthetic check put it **+3.50 points out** while the true nearest was +0.50.
The variant that performed best in `RUNG_SELECTION_TAKER.md` was nearest-line
with the gate bypassed ("nearest-line, always": crewshock −4.67%, final7
+4.97%), which is also the faithful translation of a sportsbook strategy that
always bets the line. `would_gate` records whether each logged rung was
tradeable.

## Why it cannot affect trading

- Written to a **separate file**. `_log()` writes `FILL_COLS` and calls
  `writeheader()` only when the file is new, so adding columns to the live
  fills CSV would have misaligned every subsequent row against the existing
  header. Nothing in the trading path reads the sidecar.
- `gate()` for the counterfactuals is evaluated against a **copy** of the cap
  state, so no budget is consumed by a rung that is only recorded. Asserted in
  test: state unchanged.
- The sidecar is built from `cands` **before** the placement loop and does not
  mutate it. Verified in test that the `maxedge` row is exactly the rung the
  placement loop takes.
- It runs on dry runs too, so the shadow season accumulates the comparison
  whether or not anything is armed.

## Verification

| check | result |
|---|---|
| both/all three rules recorded per signal | ✓ 3 rows |
| cap state untouched by counterfactuals | ✓ |
| `maxedge` row == rung the placement loop takes | ✓ |
| header written once, rows append | ✓ |
| all 22 columns present | ✓ |
| `nearline_all` flagged `would_gate=0` when it fails `MIN_EDGE` | ✓ |

Full end-to-end through `run_nba_trader.sh` could not be exercised: the `late`
phase hard-stops on the absent BigDataBall feed, so no live signals reach the
rung code until the feed exists. The helper and the writer are unit-tested; the
integration points (`rung_rows` accumulation, `_log_rungs` flush, summary line)
are in place and will exercise on the first real slate.

## How it gets settled

Each row carries the `ticker`, so settlement joins from Kalshi settlements or
from the boxscore actual total against `strike`. After a season of signals the
paired comparison runs on genuinely out-of-sample data with the event as the
unit of inference — the test that one season of 2025-26 could not support.

Code: `nba_live_trader.py` — `RUNGLOG`, `RUNG_COLS`, `_rung_choice_rows()`,
`_log_rungs()`.
