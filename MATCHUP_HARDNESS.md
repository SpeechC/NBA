# IS BOOKMAKER PRECISION MATCHUP-DEPENDENT? (2026-09-13)

A different question from the one that failed. Not *"can we rank individual games by future
|error|?"* (AUC 0.4998, closed) but *"are there stable classes of matchup where the estimate
is intrinsically less precise, even if we cannot pick the game?"* — the credit-risk framing:
you may not know which BBB defaults while knowing BBBs vary more than AAs.

**Answer: no. NBA totals have no BBB-vs-AA classes.** Across eleven matchup archetypes the
realised residual sd ranges **17.5 to 18.6** — a 6% band — and an exhaustive interaction
search finds nothing beyond what random splits produce.

n = 9,218 games with all archetype variables. Baseline sd(dev) 18.055.
se(sigma) per quintile 0.297 pts, so a 1-point spread is 3.4 se — this search is **not
underpowered for the economically relevant size.**

---

## GATE 1 — does residual sd vary materially across matchup classes?

| archetype | sd Q1 | sd Q5 | Q5/Q1 | **VarRatio** | Levene p |
|---|---|---|---|---|---|
| pace mismatch | 17.69 | 18.62 | 1.053 | **1.109** | 0.204 |
| closing total | 17.58 | 18.50 | 1.052 | 1.107 | 0.135 |
| foul environment | 17.80 | 18.29 | 1.027 | 1.055 | 0.962 |
| combined 3PA exposure | 17.59 | 17.87 | 1.016 | 1.031 | 0.577 |
| combined 3PA volatility | 18.20 | 18.39 | 1.010 | 1.021 | 0.730 |
| combined scoring volatility | 18.29 | 18.36 | 1.004 | 1.008 | 0.523 |
| combined efficiency volatility | 17.95 | 17.90 | 0.997 | 0.995 | 0.513 |
| off/def style mismatch | 18.12 | 18.07 | 0.997 | 0.994 | 0.965 |
| **\|Close − Open\|** | **18.21** | **18.13** | **0.995** | **0.991** | 0.316 |
| combined shooting volatility | 18.05 | 17.54 | 0.972 | 0.945 | 0.198 |
| \|spread\| | 18.56 | 17.90 | 0.964 | 0.930 | 0.417 |

**Max VarRatio is 1.109**, against an "interesting" bar of 1.70 (σ 16.5 vs 21.5) and the
structural taking bar of 1.29. **Not one Levene p is below 0.13** — the heterogeneity is not
even statistically present, let alone economically material.

## THE NEW TEST — market-revealed difficulty does NOT persist past the close

`Var(D | |Close − Open|)` gives **VarRatio 0.991**. Flat, marginally inverted.

**Games that required substantial pregame price discovery do not have larger subsequent
closing-line error.** This is the clean version of the distinction that mattered: the move is
doing its job. Difficulty is real before the close and **resolved** by it. Market uncertainty
does not survive price discovery.

(Note this is a *dispersion* test. `KALSHI_NBA_TOTALS_FINDINGS` #10 already tested MOVE as a
*level* signal — best state MOVE≥2 & |s|>9 gave +8.32% ROI over 7/7 discovery seasons and
**−10.8% out of sample.**)

## THE INTERACTION SEARCH — the additive-model objection, tested exhaustively

Every pair of archetypes, each cut at its median, four cells, max VarRatio across cells, with
a permutation null on the **max** so the search is priced:

```
observed MAX over 55 pairs x 4 cells:  1.165   (pace mismatch x closing total)
permutation null on the max:  mean 1.143   95th 1.183   99th 1.205   ->   p = 0.167
```

**The interaction search finds nothing beyond what random splits produce.** The concern that
a 563-feature additive model might miss an interactive phenomenon is answered directly: the
interaction is searched here, not assumed away, and it is empty.

## GATE 2 — and the little there is does not persist

Define the buckets on 2017-18..2021-22, test on 2022-23..2025-26:

| archetype | discovery VarRatio | **holdout** | |
|---|---|---|---|
| pace mismatch | 1.167 | **0.973** | does not hold |
| combined 3PA exposure | 1.099 | **0.804** | does not hold |
| closing total | 1.045 | 1.197 | "holds" — but see below |
| foul environment | 1.007 | 1.117 | "holds" — but see below |

The two that "hold" both went **up** out of sample from a discovery value near 1.0, which is
the signature of noise rather than persistence. And the closing-total effect is the one
already known and already priced: the Kalshi ladder scales sigma on mu at slope +0.06061
(t = +14.09), implied sigma 18.218 vs realised 18.265.

**Gate 3 (does Kalshi widen for these classes?) does not need running — there is no
heterogeneity to compare against.** For the record it has partly been run anyway:
`KALSHI_NBA_TOTALS_FINDINGS` #6-#9 are 14 group-level tests of Var(Z)=1 conditioning on 3PA,
pace, pace conflict, foul environment and spread magnitude. Two of fourteen exceeded |z|=2,
both in pace — the one where Kalshi already widens sigma by +4.78% against a +4.79% realised
excess.

---

## VERDICT

The question was worth asking and is distinct from the failed game-level test. The answer is
that the precision of the closing total is **not** materially matchup-dependent. Every class
sits within a 6% sd band, nothing is statistically significant, the best candidate inverts out
of sample, and an exhaustive interaction search returns the permutation null.

## WHAT REMAINS GENUINELY UNTESTED

Two of the dimensions on the original list could not be built from this data, and both are
better measures than anything above:

1. **Cross-book disagreement.** `SD(Total_DK, Total_FD, Total_Circa, ...)` is the most natural
   definition of a hard matchup — uncertainty revealed by independent pricing systems rather
   than inferred from basketball. **dfMaster carries ONE book.** The `LINE MOVEMENT #1/2/3`
   columns are sequential quotes of the same market, not other books. This is blocked on data,
   not on evidence, and it is the one measure that would deserve a fresh look if multi-book
   totals could be sourced.
2. **Lineup / availability uncertainty.** `~/data/injury_reports` exists and has never been
   used as a *dispersion* state — only as a level signal, where it was priced between open and
   close (0.963 → 0.419). Whether games with high pregame roster uncertainty have wider
   residuals is untested.

Neither changes the classification of the trading programme. Both are cheap if someone wants
to close the question completely rather than on eleven proxies.
