# Alpha decay: is the edge reachable?

The frozen models produce +0.746 points of CLV measured from the **opening**
number. That is only bankable if the opening number can actually be struck. This
tests how quickly the value disappears using the three intermediate quotes
recovered from `LINE MOVEMENT #1/2/3`.

Sample: 2,178 games with all three quotes; 346 of them are bets at the frozen
operating threshold (|pred| > 1.25).

## A. Where the value accrues (signal fixed at the open)

| by | CLV captured from open | % of final CLV | still available |
|---|---|---|---|
| **quote 1** | **1.717** | **92.4%** | **0.142** |
| quote 2 | 1.764 | 94.9% | 0.094 |
| quote 3 | 1.815 | 97.7% | 0.043 |
| close | 1.858 | 100.0% | 0.000 |

**92.4% of the edge is gone by the first repost.** By quote 3, 97.7%.

## B. Why the strategy cannot be re-anchored later

Remaining movement collapses after the opener:

| entry point | SD of remaining move | mean \|move\| | P(\|move\| ≥ 1) | P(\|move\| ≥ 2) |
|---|---|---|---|---|
| open | 3.237 | 2.480 | 81.0% | 55.0% |
| quote 1 | **1.098** | 0.784 | 42.5% | 10.9% |
| quote 2 | 0.887 | 0.631 | 36.3% | 5.6% |
| quote 3 | 0.727 | 0.558 | 28.9% | 1.5% |

Refitting the model anchored on quote 1 produces predictions with **SD 0.114 and
a maximum absolute value of 0.486**. At the frozen threshold of 1.25 it generates
**zero bets** — not a small sample, zero. A model cannot predict a move larger
than the moves that remain available.

Dropping the threshold to the only level that triggers at all:

| entry | threshold | n | win % | ROI | CLV |
|---|---|---|---|---|---|
| quote 1 | \|pred\| > 0.25 | 139 | 49.64 | **−5.23%** | +0.158 |

Losing, as expected: 0.158 points of CLV against a ~1.35-point requirement.

## CORRECTION (2026-08-11, on the full 2017-2026 file)

Two things in the original write-up were overstated.

**1. The figure.** 92.4% was measured on the 346-bet subsample at the operating
threshold. On the full file, with 4,202 games carrying opener + all three quotes
+ close, the cumulative capture is **83.8% by quote 1**, 89.8% by quote 2, 94.0%
by quote 3. The direction is unchanged; the magnitude is lower.

**2. The interpretation, which was wrong.** The quotes are ORDERED but NOT
TIMESTAMPED. The file contains no time column for them -- the only time-named
fields, `HALFTIME_H/R`, are second-half betting lines. So this measures position
in a SEQUENCE of repricings, not elapsed clock time.

  * supported: "most of the move has happened by the first repricing"
  * NOT supported: "the execution window is minutes wide"

The opener may sit for six hours before the first move, or six seconds. Nothing
here distinguishes those cases. Most games show only 3-4 distinct line values
across open/q1/q2/q3/close, so these are a handful of repricings rather than a
dense sample of the day.

How long the opener actually survives is unmeasured, and is precisely what live
timestamped logging would establish.

## Verdict

**The edge is real and concentrated in the first repricing.**

Everything the model captures happens in the very first move. This reframes the
project's central question. It was never "is the signal big enough?" — at the open
it is worth 55.5% and ROI +5.9% on the quoted sample. It is **"can you transact at
the opening number?"**

That is now an execution and infrastructure question, not a modelling one:

* **how long the opener stays up before the first repricing — completely unknown
  from this data.** The quotes are ordered, not timestamped. This is the single
  most important unmeasured quantity in the project.
* what limit is available at the opener, which is typically the smallest of the day
* whether an automated pipeline can price and fire before the first move
* whether books tolerate an account that only ever bets openers

None of that can be answered from historical data. It requires logging live
openers with timestamps and available size.

## What this implies for the remaining research queue

Items that raise predictive accuracy — scoring-surprise EWMA, classification at
the threshold, overtime premium, slate common factor — all optimise a quantity
that is only collectable in the first minutes after posting. They are not
worthless, but they are second-order to establishing that the opener is
obtainable at all.

The correct next step is not another model. It is a live logging exercise:
capture openers with timestamps and quoted size for one month, and measure how
long the number survives.
