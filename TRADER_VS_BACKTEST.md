# Does the trader place the bet the backtest measured? (2026-10-07)

**No. One divergence accounts for nearly all of it, and it is the one divergence
with no backtest behind it.**

The backtest is: *for every signal, stake $100 at −110 on the strategy's own
line, win if the actual total beats that line.* No selection, no gate, no rung.

Three things priced on the same 2025-26 games:

| | n | hit% | mean offset | ROI |
|---|---|---|---|---|
| **CREWSHOCK** | | | | |
| BACKTEST — bet the line at −110 | 238 | 50.42% | +0.00 | **−3.74%** |
| **B** — Kalshi, nearest-line rung, always | 236 | **50.00%** | +0.05 | **−4.67%** |
| **A** — TRADER as configured | 236 | **46.19%** | **+1.58** | **−4.13%** |
| **FINAL7** | | | | |
| BACKTEST — bet the line at −110 | 69 | 55.07% | +0.00 | **+5.14%** |
| **B** — Kalshi, nearest-line rung, always | 69 | **55.07%** | −0.07 | **+4.97%** |
| **A** — TRADER as configured | 69 | **46.38%** | **+1.93** | **−1.61%** |

## What this shows

**Kalshi can reproduce the backtest almost exactly.** Buying the nearest-line
rung on every signal gives a hit rate within **0.42pp** of the backtest for
crewshock and **0.00pp** for final7, and an ROI within 0.9pp and 0.2pp. The
venue, the fee, the spread and the strike grid together cost essentially
nothing. **That settles the "is Kalshi a faithful venue" question: yes.**

**The trader does not do that.** It buys the max-edge rung, which sits +1.58 and
+1.93 points off the line, and the hit rate falls 4.2pp and 8.7pp. For final7
that is the whole difference between **+4.97% and −1.61%**.

## The argument, and why it does not need a significance test

Earlier I tested *"does nearest-line outperform max-edge?"* and got t +0.79 and
+1.16 — insignificant, one season. I then built a mechanism on top of that and
had to withdraw it.

**This is a different and stronger argument.** It is not a performance claim.
It is that **nearest-line is the bet that was validated across eight seasons and
max-edge is a bet that was never tested at all.** The eight-season record
(crewshock +4.66%, final7 +8.68%) is a record of betting *the line*. Nothing in
it speaks to a strike 1.9 points away. The burden of proof sits on max-edge, and
it has none.

Where max-edge's justification came from: a 400,000-board simulation
(`maker_figure_provenance.py`) that drew *truth* and *market* from the **same
normal with the same σ**, so the pricing model was correct by construction and
maximising modelled EV had to win. It was also measured at bid+1¢ — a maker
price we are not approved to use.

## Every divergence, classified

| divergence | basis | note |
|---|---|---|
| rung instead of line | **forced** | 3-pt grid; nearest rung averages 0.69 pts off |
| no pushes | **forced** | every strike ends .5 |
| 1 contract vs $100 flat | **forced** | changes the ROI denominator, not the bet |
| reference = Kalshi μ | reasoned | the close is unknowable at 17:00, and μ *is* the close (median 0.001 pts) |
| one trade per game | reasoned | the backtest tables double-count 104 games |
| drift guard | reasoned | declines when the market moved past our own delta |
| **max-edge rung selection** | **NO BACKTEST** | **justified by a synthetic board where the model could not be wrong** |
| MIN_EDGE = 0.01 | **NO BACKTEST** | the backtest bets every signal |
| price band 0.12–0.88 | **NO BACKTEST** | no analogue |
| MAX_SIGMA_DIST = 1.1 | **NO BACKTEST** | no analogue |
| MIN_BOOK_SIZE = 5 | **NO BACKTEST** | no analogue; inert until the taker flip |
| OVER only | config | now verified, so closeable |

Worth noting the gates turn out to be nearly inert once the reference is the
Kalshi centre: **236 of 236** crewshock signals and **69 of 69** final7 signals
passed every gate. (With the sportsbook close as reference it was 211 of 238 —
the gate only bites when the reference disagrees with the market.) So of the
five untested divergences, four currently do nothing, and the fifth —
**max-edge rung selection — does all the damage.**

## Implication

If the intent is to trade the strategy that was backtested, the trader should
buy **the rung nearest the reference line**, not the max-edge rung. That is a
one-line change in `candidates()` selection, and unlike every other change in
this thread it makes the live rule *match* an eight-season validation instead of
departing from it.

Not making that change unilaterally — it is the trade path, and the decision is
whether to trade the validated rule or the optimised one. But the asymmetry in
evidence is now measured: nearest-line reproduces the backtest to within
0.42pp of hit rate; max-edge has no out-of-sample support of any kind.

Script: `trader_vs_backtest.py`.

---

# CHANGE MADE 2026-10-07: `RUNG_RULE = "nearline"`

`nba_live_trader.RUNG_RULE` now defaults to `nearline`, overridable with
`NBA_RUNG_RULE=maxedge`. Verified by inspection and by a unit test on a ladder
constructed so the two rules diverge (max-edge picked +9.50 pts, nearline picked
+0.50; the live selection block chose +0.50).

**One rung is considered, and a failure declines the game.** Under `nearline`
the trader evaluates only the rung nearest the reference line; if that rung
fails the gate the game is **declined rather than substituted** with a farther
strike. Substituting would quietly reintroduce exactly what this rule exists to
prevent — the backtest bets the line or it does not bet.

## 2025-26 under the new rule

| strategy | sig | traded | declined | hit% | mean off | P&L | ROI |
|---|---|---|---|---|---|---|---|
| crewshock | 238 | 192 | 44 | **52.60%** | +0.14 | +$1.33 | **+1.34%** |
| final7 | 69 | 68 | 1 | **55.88%** | −0.07 | +$2.31 | **+6.46%** |

Against max-edge: crewshock **−4.13% → +1.34%**, final7 **−1.61% → +6.46%**.

## Attributing that honestly — two effects, not one

| configuration | crewshock | final7 |
|---|---|---|
| backtest, bet the line at −110 | −3.74% | +5.14% |
| nearline, **no gate** (backtest-faithful) | −4.67% | +4.97% |
| **nearline + MIN_EDGE gate (live)** | **+1.34%** | **+6.46%** |
| max-edge + gate (previous live) | −4.13% | −1.61% |

**The rung change is what brings the rule back to the backtest** — the
gate-free nearline row sits within 0.9pp and 0.2pp of the −110 backtest.

**The extra improvement comes from the MIN_EDGE gate**, which declined 44 of
236 crewshock games and lifted the hit rate 50.42% → 52.60%. That is 2.2pp
against an se of 3.3pp, so it is **within noise**, and `MIN_EDGE` is itself in
the NO-BACKTEST column. **Do not read +1.34% as evidence the gate adds edge.**
The defensible claim is the first one: nearline reproduces the validated bet.

## What is now settled, and what is not

**Settled:** the live rung rule matches the eight-season validation. Of the five
divergences with no backtest, the one that mattered is removed.

**Not settled:** whether `MIN_EDGE` (and the price band, σ-distance and
book-size gates) should exist at all. They are currently near-inert for final7
(1 decline of 69) and materially active for crewshock (44 of 236), and their
effect on crewshock's 2025-26 numbers is favourable but unproven. The
rung-choice sidecar logs all three rules per signal and will settle it on
out-of-sample data.
