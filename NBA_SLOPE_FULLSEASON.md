# NBA halftime slope — full 2025-26 season, probit estimator (2026-08-26)

First estimate free of both defects: the whole season (`kalshi_nba_triangle.sqlite`,
harvested via `/historical/markets`) and no bracketing selection
(`implied_line.probit_line`). **1,114 games**, against 220–324 for every prior
NBA estimate. Efficient bar = 1.0 (gamma ~ 0 on 9,489 master games); the
realized regression on the *same* games is reported beside each estimate.

| subset | n | s(H1) | benchmark | gap |
|---|---|---|---|---|
| median-crossing (bracketed only) | 830 | 0.880 | 0.906 | −0.026 |
| **probit, ALL games** | **1113** | **0.846** | **0.996** | **−0.151** |
| r² ≥ 0.95 (well determined) | 807 | 0.936 | 0.959 | **−0.022** |
| r² < 0.95 | 306 | 0.758 | 1.039 | −0.282 |
| interpolated | 873 | 0.804 | 0.920 | −0.116 |
| extrapolated | 221 | 1.094 | 1.073 | +0.021 |
| first half of season | 562 | 0.787 | 1.023 | −0.236 |
| second half | 551 | 0.904 | 0.968 | −0.064 |
| tight ladders (≤4c) | 560 | 0.896 | 0.981 | −0.085 |
| wide ladders (>4c) | 553 | 0.783 | 1.012 | −0.229 |

## Reading

**The Aug-26 diagnostic replicates at 3.4x the sample.** Well-determined
ladders give a gap of **−0.022**; badly-determined ones **−0.282**. The
under-reaction is concentrated where the line is least reliably measured,
exactly as the 324-game version indicated.

**Three independent quality proxies agree**, which is what makes this more
than an r² artefact:
- fit quality: −0.022 (good) vs −0.282 (poor)
- quote width: −0.085 (tight) vs −0.229 (wide)
- calendar: −0.064 (second half, when spreads had compressed to 1-2c) vs
  −0.236 (first half, at 3-4c)

Every axis that proxies *measurement precision* orders the gap the same way,
and the season-half split does it with time rather than with any property of
the ladder. As the board tightened through the season the "under-reaction"
shrank by two-thirds. That is the signature of attenuation from noisy line
estimates, not of a market behaviour.

**Extrapolated ladders show a POSITIVE gap (+0.021)** — no under-reaction at
all — which is the opposite of what a real effect concentrated in extreme
games would produce.

## Verdict

The residual −0.022 on 807 well-measured games is 6.1 sigma from 1.0 and so
not literally zero, but it is worth **0.022 x sd(H1 surprise) ~ 0.2 points of
total**, against a round trip of 1.06–1.25 points. Economically absent.

**The NBA halftime under-reaction is closed.** What survives is a small
residual an order of magnitude below transaction costs, and a clear
demonstration that the headline effect this programme chased since inception
was attenuation from imprecise line measurement.
