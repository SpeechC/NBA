# Cross-market σ-consistency scan — NULL (2026-09-24)

**Question.** A game's spread and its moneyline imply the same quantity,
P(home margin > 0), through different contracts. Under a normal margin
distribution that is `Φ(−S_h/σ)`. Does the pair disagree, with σ *estimated from
the board* rather than chosen? Prompted by the Oracle-7 NFL model, whose entire
published edge column is `Φ(market_line / 11.3)` — the power ratings never enter
a traded number.

**Kill condition, stated in advance:** if implied σ across rungs is tight,
there is nothing here.

## 1. Kalshi has no history to test

Kalshi lists all three series: `KXNBAGAME` (winner, one market per team,
`strike_type='structured'`), `KXNBASPREAD`, `KXNBATOTAL`. `KXNBAWINMARGIN`
exists as a ticker but has zero events, ever.

Settled **events** are retrievable — 1,448 `KXNBAGAME` and 1,324 `KXNBASPREAD`
covering all of 2025-26. Their **markets are purged**: `/markets` returns 0 for
every settled NBA event on every status filter, and `with_nested_markets`
returns `[]`. This is the same purge that took 26JUN/26APR/26MAR from
KXFEDMENTION and pre-2026-07-08 from the Trump series.

Our local `kalshi_nba_totals.sqlite` / `kalshi_nba_candles.sqlite` hold
`KXNBATOTAL` only. **There is no historical Kalshi spread or moneyline board
anywhere, and none can be obtained.** Any Kalshi-native test is forward-only.

## 2. The sportsbook proxy, 10,383 games, 2017-2025

Closing spread and closing moneyline pair from `dfMaster_OT_2017-2026.csv`,
proportional de-vig (median overround 1.0417).

Implied σ is **not** flat — it slides monotonically with the spread:

| \|spread\| | n | implied σ | de-vigged P(fav) | fav win rate |
|---|---|---|---|---|
| 2–4 | 2251 | 14.89 | .5689 | .5695 |
| 4–6 | 2105 | 13.66 | .6360 | .6318 |
| 6–8 | 1789 | 12.79 | .7012 | .7065 |
| 8–10 | 1304 | 12.20 | .7636 | .7600 |
| 10–13 | 1219 | 11.84 | .8280 | .8195 |
| 13+ | 710 | 12.24 | .8883 | .9042 |

**The curvature is the market being right, not wrong.** The de-vigged moneyline
matches the realised win rate in every bucket. A constant-σ normal is simply the
wrong link function, and the book declines to use one.

This is exactly the error Oracle-7 would monetise: at a 3-point spread its
σ=11.3 differs from the market's ≈14.9 by 3.6 points of σ, which manufactures
edge out of a link-function choice.

## 3. Residual, and where it comes from

Single σ reconciling the whole board: **12.274** (outcome σ is 13.595).

| mapping | residual sd | \|resid\|>2pp |
|---|---|---|
| constant-σ normal | 1.96pp | 35.0% |
| flexible spread→P map, leave-one-season-out | **1.38pp** | 13.4% |

Half the apparent disagreement was my own constant σ. Half-point spread rounding
alone accounts for 0.40pp.

Brier against the actual result: de-vigged moneyline **.20889**, spread with
flexible map .20899, spread with constant σ .20912. **The moneyline is the
better forecast; the spread cannot improve on it.**

## 4. It does not pay

Back the side the residual favours, at the **real** moneyline, vig included:

| \|resid\| ≥ | n | bets/season | win rate | model expected | ROI | z |
|---|---|---|---|---|---|---|
| 0.00 | 10383 | 1298 | .5318 | .5432 | −2.56% | −2.11 |
| 0.01 | 6917 | 865 | .5352 | .5503 | −2.63% | −1.83 |
| 0.02 | 3602 | 450 | .5097 | .5359 | −2.33% | −1.08 |
| 0.03 | 1019 | 127 | .4318 | .4714 | −1.58% | −0.31 |
| 0.05 | 59 | 7 | .3390 | .4390 | −26.96% | −1.46 |

Negative at every threshold, and the realised win rate sits **below** the spread
model's expectation at every threshold. When the two markets disagree, the
moneyline is right. The residual is the model's error, not the market's.

## 5. Execution closes it independently

Live `KXNBAGAME` books for opening night (2026-10-20), read 2026-09-24:

```
BOSDET   DET .52 x50  / .54 x1046   2c     BOS .40 x18 / .48 x549   8c
PHINYK   PHI .37 x10  / .38 x10     1c     NYK .60 x77 / .62 x5     2c
OKCSAS   OKC .45 x225 / .49 x535    4c     SAS .53 x25 / .55 x261   2c
```

Quoted spreads 1–8¢, overround 0–4¢. **The quoted spread alone exceeds the
entire residual distribution**, whose sd is 1.38pp. Also `KXNBASPREAD` has zero
open events while `KXNBAGAME` has been open since 2026-08-20 — the two legs are
not simultaneously quoted far ahead, so even a forward test would be a game-day
scan.

## Verdict

Closed. The kill condition fired on its own terms: once σ is estimated rather
than chosen, the two markets agree to ~1.4pp, the residual predicts the outcome
with the **wrong sign**, and the quoted spread is wider than the whole signal.

**What transfers:** the spread→win-probability link in NBA is not constant-σ
normal; implied σ runs 14.9 at short spreads to 11.8 at long ones. Any future
work converting a spread to a probability must use the empirical map, not a
fitted σ. Scripts: `screen_cross_market_sigma.py`,
`screen_cross_market_sigma_refine.py`.
