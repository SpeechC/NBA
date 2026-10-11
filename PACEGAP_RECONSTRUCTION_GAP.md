# PaceGap: by-season record, and why it does not match the registered figures

## By season — the live path's own record

Reconstructed by running `frozen_models` walk-forward over 1,263 game dates,
exactly the `capture_openers.py` path: `build_states(g, day)` (strictly before
`day`), `team_profiles`, `predict_game`, then
`E_pace = (P_hat − P_book)·EffSum/100`, `bet_flag = |E| ≥ 4.77`, `side = sign(E)`.
8,257 games, 0 games skipped. Sportsbook −110, $100 flat, settled vs the opener.

| season | slate | bets | %slate | hit% | ROI | OVER | UNDER |
|---|---|---|---|---|---|---|---|
| 2018-19 | 1230 | 161 | 13.1% | 54.04% | **+3.16%** | 53.19% / +1.55% | 54.39% / +3.83% |
| 2020-21 | 1080 | 206 | 19.1% | 54.37% | **+3.80%** | 57.41% / +9.60% | 53.29% / +1.73% |
| 2021-22 | 1230 | 200 | 16.3% | 59.50% | **+13.59%** | 66.02% / +26.04% | 52.58% / +0.37% |
| 2022-23 | 1229 | 204 | 16.6% | 54.41% | **+3.88%** | 53.47% / +2.07% | 55.34% / +5.65% |
| 2023-24 | 1162 | 289 | 24.9% | 52.25% | **−0.25%** | 53.80% / +2.71% | 50.00% / −4.55% |
| 2024-25 | 1166 | 285 | 24.4% | 55.44% | **+5.84%** | 54.02% / +3.13% | 57.66% / +10.07% |
| 2025-26 | 1160 | 270 | 23.3% | 54.07% | **+3.23%** | 51.20% / −2.25% | 56.55% / +7.96% |
| **ALL** | 8257 | **1,615** | 19.6% | **54.74%** | **+4.50%** | 55.23% / +5.43% | 54.29% / +3.64% |

z = +1.90, season-block 95% CI **[+2.19%, +8.02%]**, **6 of 7 positive**, worst
season −0.25%. 2017-18 has no signals: the engine needs ≥400 prior-season games
for its a,b fit, so 168 days were correctly skipped.

That is the most consistent record of the four strategies — the only one without
a materially negative season, and the only one whose season-block interval
excludes zero.

## The reconstruction gap — located, not closed

| | registered | my reconstruction |
|---|---|---|
| eligible universe, 2023-25 | 3,488 | **3,488** ✓ |
| pushes | 8 | **8** ✓ |
| BET ALL hit% | 52.47–52.59% | **52.10%** |
| \|E\| ≥ 4.77 — n | 1,056 | **844** |
| — % of slate | 30.3% | **24.2%** |
| — hit% | 53.31% | **53.91%** |
| implied sd(E_pace) | ~4.70 | **4.19** |

**What matches exactly:** the eligible universe (3,488) and the push count (8).
So the game definition is right.

**What differs:** the *magnitude* of E_pace, not its direction. The BET-ALL hit
rate is within 0.45pp, which is about **16 games of 3,480 with a flipped sign** —
the sign agrees on ~99%. But my sd(E_pace) is **0.89×** the registered value, so
the frozen 4.77 threshold selects 24.2% of the slate instead of 30.3%.

## What it is not

- **Not the universe.** 3,488 and 8 pushes match exactly.
- **Not look-ahead in the original.** End-of-season states give sd(E) of
  **7.0–8.6** and 50–61% selectivity — a large overshoot, so the original was
  not using full-season information.
- **Not the a,b fit drifting within a season.** `a` and `b` are constant within
  each season (one distinct value per season), confirming the prior-seasons-only
  fit works as documented. They do drift strongly *between* seasons —
  `a` −4.74 → +19.28, `b` 1.028 → 0.920 — and `sd(E_pace)` tracks that (3.38
  early, 4.26 late), which explains the rising selectivity (13.1% → ~24%) but
  not the gap to the registered figure.
- **Not cleanly a `b` rescale.** Rescaling `b` alone shifts P_book's *level*, not
  its scale, which sends selectivity to 94% and the hit rate to 50%. That test
  was invalid and is discarded.

**Why it cannot be closed:** no script in the repo produces the registered
threshold grid or the "n = 942, one season" discovery figure. Without the
original code the remaining 0.89× scale difference cannot be attributed.

## What actually matters for trading

**The live path is what I reconstructed.** The trader runs `capture_openers.py`
→ `build_states(g, day)` → `predict_game`. So the registered 30.3% / 53.31% do
**not** describe what the trader will do. It will bet about **24% of the slate at
~53.9%** — fewer bets at a slightly better hit rate.

**One concrete consequence.** `nba_live_trader.STRATS["pacegap"]["hit"] = 0.5259`
drives `delta = 1.184 pts`. The live path's measured rate is **54.74%** over
seven seasons, which implies `delta ≈ 2.17 pts`. The trader is therefore
**understating its own edge by roughly 1 point**, which is the conservative
direction — it bets a nearer rung and claims less edge than the signal supports
— but it is wrong, and it is wrong in a way that was invisible until the signal
was reconstructed.

I have not changed the constant. Changing a frozen preregistered parameter on
the strength of a reconstruction that does not reproduce the registered figures
would be the wrong move; the discrepancy needs resolving first.

Scripts: `pacegap_backfill_all.py`, `pacegap_backfill.py`.
