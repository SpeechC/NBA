# Are 1H markets worth pursuing? — assessment 2026-08-29

Prompted by `DISTRIBUTION_AUDIT.md`: 1H residuals are the only Gaussian
distributions in this program. Does that make the market worth working?

## The market structure is the most favourable we have found

Source: `/mnt/c/NBA/nba_draftkings_totals_historical.csv` — DraftKings, **967
rows, 927 with a 1H close, 2023-10-24 → 2024-03-07 (one PARTIAL season)**. It
carries open *and* close for both full game and 1H, **plus actual prices**.

| | overround | median price | sd | value of 1 point | points needed |
|---|---|---|---|---|---|
| FULL GAME | 4.74% | −110 / −110 | 17.46 | 2.28c | **1.072** |
| **FIRST HALF** | **4.74%** | **−110 / −110** | **11.53** | **3.46c** | **0.682** |

Three things here are genuinely good:

1. **The 1H market carries IDENTICAL juice to the full game.** 4.74% overround,
   −110/−110 median both sides. Every other derivative this program has priced
   was punitively wide — the Kalshi half-winner quoted 30c against a 3–6c edge.
   1H is not that.
2. **The residual is Gaussian** (JB p = 0.223 on the joined sample), so the
   modelling and inference machinery applies cleanly, unlike full-game totals.
3. **A point of edge is worth 1.51× more** — same vig against a 34% smaller sd
   means the bar falls from 1.072 points to **0.682**.

## But the data cannot support a test, and that is decisive

**857 joined games. One partial season.**

| to establish | bets needed (80% power) | vs our dataset |
|---|---|---|
| 1pp edge | 19,600 | **23×** |
| 2pp edge | 4,900 | **6×** |
| 3pp edge | 2,178 | **3×** |
| 5pp edge | 784 | 1× |

Only an implausible 5pp edge is detectable in what we hold. Anything realistic
needs three to twenty-three times more 1H line history than exists here.

## And the two tests already run against this market both failed

From `CLOSING.md`, both against this same DK H1 file:

| test | sports side | market side |
|---|---|---|
| visitor pace allocation | t = **7.57**, λ = 0.777 | **t = 0.35 vs DK H1** |
| FG → H1 allocation | book's deviation informative, t = **6.28** | β = 1.25 stable, **untradeable (47.4%)** |

A strong pace signal died against the 1H line, and the allocation model hit
47.4% — decisively losing.

## The one bias present is smaller than the vig

```
mean 1H dev  -0.468 points   ->  the DK 1H total sits HIGH by about half a point
UNDER wins   50.48% of decided bets   vs   52.36% needed
```

Real in the mean, and it does not reach the line. The same shape as the injury
over-reaction (48.17% / 51.83%, both sides losing) and the cohesion tail
problem: **a mean effect that never becomes a cover.**

## Verdict

**The market is attractive; our data is not.** The binding constraint is data
acquisition, not market structure — which is the opposite of every other
derivative this program has examined, where the market itself was the wall.

**This is a purchasing decision, not a research one.** The DK file carries
`api_cost_close` / `api_remaining_after_close` fields — it was a paid odds-API
pull. Three additional seasons of 1H closes would give roughly 3,700 games,
enough to detect about a 2.3pp edge. That is the threshold question, and it
should be answered before any further 1H modelling.

**Do not run more 1H tests on the 857 games.** Two have already failed on them,
and a third would be an eighth pass over a sample that cannot resolve anything
smaller than 5pp.
