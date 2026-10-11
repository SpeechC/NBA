# By-season records on a TAKER basis (2026-10-11)

Every by-season table produced earlier in this thread was **sportsbook −110**,
which is neither maker nor taker on Kalshi. Restated here on the taker basis,
per the standing rule that every P&L/ROI figure must say which it is.

## What this is, precisely

**A translation, not a measurement.** Kalshi books exist only for 2025-26, so
2017-2024 cannot be measured on a Kalshi basis and never will be — settled
markets are purged from the API and were not collected. What *is* measured is
the cost difference, from 14,284 real rungs: the board's mean nearest-strike ask
is **0.507** and the Kalshi fee there is **0.018**, giving an outlay of
**c = 0.525** against −110's effective 0.5238.

Each season's realised hit rate is then repriced as `ROI = (h − c)/c`. The
translation is near-linear — the SB-to-taker gap is **−0.21 to −0.26pp** across
hit rates from 48% to 60% — so it adds almost no new assumption beyond `c`.

Hit rates are the nearest-line analogue, which `TRADER_VS_BACKTEST.md` showed
reproduces the backtest to within 0.42pp (crewshock) and 0.00pp (final7).

## The table

| season | crewshock n / taker | final7 n / taker | move n / taker | pacegap n / taker |
|---|---|---|---|---|
| 2017-18 | 92 / **−10.97%** | 62 / **+10.59%** | — | — |
| 2018-19 | 216 / **+4.93%** | 62 / **+7.52%** | — | 161 / **+2.93%** |
| 2020-21 | 141 / **+1.31%** | 68 / **−10.36%** | — | 206 / **+3.56%** |
| 2021-22 | 205 / **+12.42%** | 63 / **+2.80%** | 422 / **+4.72%** | 200 / **+13.33%** |
| 2022-23 | 194 / **+9.96%** | 67 / **+13.71%** | 369 / **−8.11%** | 204 / **+3.64%** |
| 2023-24 | 138 / **+0.76%** | 69 / **+24.23%** | 327 / **+6.59%** | 289 / **−0.48%** |
| 2024-25 | 166 / **+13.60%** | 67 / **+13.71%** | 335 / **+3.49%** | 285 / **+5.60%** |
| 2025-26 | 238 / **−3.96%** | 69 / **+4.90%** | 334 / **+2.65%** | 270 / **+2.99%** |
| **ALL** | **1390 / +4.42%** | **527 / +8.43%** | **1787 / +1.79%** | **1615 / +4.26%** |

For reference the −110 figures were +4.66%, +8.68%, +2.02%, +4.50%. **The taker
basis costs about 0.24pp of ROI** — it does not change any sign or any
conclusion.

## Sensitivity to the one assumption

| outlay c | break-even | crewshock | final7 | move | pacegap |
|---|---|---|---|---|---|
| 0.511 | 51.1% | +7.28% | +11.40% | +4.58% | +7.12% |
| 0.518 | 51.8% | +5.83% | +9.89% | +3.17% | +5.67% |
| **0.525** | **52.5%** | **+4.42%** | **+8.43%** | **+1.79%** | **+4.26%** |
| 0.532 | 53.2% | +3.04% | +7.00% | +0.45% | +2.89% |

A 2.1¢ swing in the nearest-line outlay moves every strategy's ROI by about
4pp, which is larger than most of the differences between strategies. **The
outlay assumption matters more than the choice of strategy**, and 0.525 is the
measured board mean rather than a guess.

## The one season that is actually measured

2025-26 is the only season with real books. Measured there with the live
configuration (nearest-line rung, all gates, bounds anchor): crewshock
**+1.34%**, final7 **+6.46%**. The translation above gives −3.96% and +4.90%
for the same season.

The gap is the **`MIN_EDGE` gate**, which declined 44 of 236 crewshock games and
lifted its hit rate from 50.42% to 52.60%. The translation deliberately does
**not** model the gates, because `MIN_EDGE` is in the no-backtest column and its
2.2pp hit-rate lift is within an se of 3.3pp. Treat the translated rows as the
ungated, backtest-faithful figure.

## What does not change

- **crewshock** +4.42%, 6 of 8 seasons positive, worst **−10.97%**
- **final7** +8.43%, 7 of 8 positive, worst **−10.36%**
- **move** +1.79%, 3 of 5 positive, worst **−8.11%**
- **pacegap** +4.26%, 6 of 7 positive, worst **−0.48%** — still the most
  consistent, and still the one whose registered figures are unreproducible
  (`PACEGAP_RECONSTRUCTION_GAP.md`)

Every strategy still has at least one badly negative season, and the taker
adjustment is an order of magnitude smaller than that season-to-season variation.

Script: `backtest_by_season.py` for the hit rates; the translation is in this
document.
