# Spreads — the structural attack, and why it fails (2026-08-30)

Tests whether the reverse-engineering that produced the totals pace signal
transfers to the spread market. It does not, for a reason that is mechanical and
worth keeping.

## Prior art — what was already closed

- **The closing spread is an unbiased forecast of margin.** The "line overreacts"
  finding (MZ slope 0.9368, p=0.0015) was **four corrupt cells** — juice and a
  total leaked into `CLOSING SPREAD_H`. Clean: slope **1.0043 (t=+0.22)**, seven
  of eight seasons within |t|<1.2 of unity. (`DATA_DEFECT_spread_column.md`)
- `PREREG_spread_tilt` and `PREREG_spread_curve`: **dead as bets.**
- An early box-score spread model: 48.61% on n=4,740, z=−5.20, ROI −7.20%,
  CLV −0.612. (`BETTING.md`)

## The economic bar

```
sd(margin + spread) = 13.92      required line error = 0.830 pts
sd(actual - open)   = 18.25      required (totals)   = 1.089 pts
```

Spreads are a **25% easier bar** than totals. That is the only thing in this
document that favours spreads.

## Channel 1 — pace. Structurally excluded.

Differentiating the recovered identity:

```
Margin = Pace x EffDiff / 100
d(Margin) = (EffDiff/100) x dPace  +  (Pace/100) x d(EffDiff)
```

The first term is ~zero **because the multipliers differ by ~42x**:

```
EffSum  (totals multiplier):  mean 230.03
EffDiff (spread multiplier):  mean  -0.07,  sd 6.86
```

A pace error multiplies the efficiency SUM for totals and the efficiency
DIFFERENCE for spreads. Measured `E_margin = D x EffDiff/100`: sd **0.135**,
p99 0.485, max 1.016. **Only 2 of 3,488 games (0.06%) reach the 0.830 bar at
all.** Even at 1sd the signal is worth 0.295 pts — 2.8x short. No threshold fixes
this; the distribution does not reach the bar.

Confirmed downstream: beta +2.1855 (t=+1.25), betting the sign 50.56%, ROI −3.48%.

## Channel 2 — efficiency. Has the leverage, has no information.

`Pace/100 ~ 1.0`, so EffDiff error passes into margin ~1:1. The signal is our
predicted margin minus the book's:

```
sig = sP x (sOH - sOR)/100 - (-spread)
```

`Ost`/`Dst` update on **realized** offensive efficiency, not on lines, so this is
a genuine "our ratings vs the book's" test, not line momentum.

**Matched sample, n = 3,488, seasons 2023-2025:**

| | beta | t | information share | beta x sd | required |
|---|---|---|---|---|---|
| pace gap (totals) | +0.2223 | +3.42 | **22.2%** | 1.055 | 1.089 |
| efficiency gap (spreads) | +0.0659 | +0.96 | **6.6%** | 0.226 | 0.830 |

`beta` is the **information share** of the disagreement: 1.0 if the disagreement
were pure information, 0 if pure noise.

```
bet sign(sig):  3,479 bets   hit 49.55%   ROI -5.40%   z = -3.33
```

Not merely unprofitable — **significantly worse than break-even.** Our box-score
ratings are reliably worse than the book's implied ones.

## The finding worth keeping

**The book prices team strength ~3.4x better than it prices pace** (22.2% vs 6.6%
information share in our disagreement). That explains why the only surviving
signal in this programme is a pace signal: bookmakers concentrate effort on the
efficiency differential, which drives the spread — the headline market — and are
comparatively loose on pace, which only reaches the total.

## What is NOT a rescue

Residualizing `sig` against the spread lifts it to beta +0.1425, t=+1.87. This is
**not** carried forward:

- still **1.9x short** of the bar (0.439 pts vs 0.830);
- still **loses money** — 50.62%, z = −2.08;
- `corr(sig, spread) = +0.471`, so the raw signal is largely a systematic fade of
  one side, and removing it leaves too little to matter;
- "control for the spread to revive a dead signal" is the exact move that produced
  the false Link 5 retraction earlier in this programme.

## Sample note

A first cut ran n=4,717 because `sig` does not depend on `P_book` and so retained
the 2022 burn-in season that the pace test drops. Matching the sample moved beta
from 0.0832 to 0.0659. The matched figures are the comparable ones.

## Verdict

**Spreads are closed by this route.** The pace channel cannot reach the bar
(0.06% of games), and the efficiency channel has the leverage but 6.6%
information and a significantly negative economic result. No threshold, subgroup,
or interaction is registered against either — and per the standing rule, none may
be searched for to rescue them.
