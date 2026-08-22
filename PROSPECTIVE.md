# Prospective validation protocol — frozen totals signals

**Written 2026-08 at the close of the signal-engineering phase. The purpose of
this document is to make the 2026-27+ evaluation mechanical: every rule,
metric and alert threshold is fixed here, before any new season is observed.**

## Phase change

Signal engineering on CrewShock is CLOSED. The record that justifies this:

- 6 conditioning attempts (matchup foul pressure, offensive strength,
  possession scaling, FT-value scaling, defensive-foul propensity, bonus
  timing) — all null, main effect unchanged every time
- 2 estimator-construction attempts (lookback windows 30/100/150 + expanding;
  crew-chief seat weighting) — incumbent best on every scale-invariant measure
- 3 adjacent-market probes (2H total, H1 prices, OT premium) — omission
  confirmed where testable, none tradeable
- exogeneity: five independent checks each landing BELOW its own permutation
  null; mechanism fully accounted (75% defensive whistles, FT-mediated,
  bonus channel 15% of scoring effect)

No further historical test of CrewShock is to be run. A seventh conditioning
attempt is specification mining by definition.

## The frozen book — two signals, run side by side

**Signal 1 — CrewShock (officiating).**
Bet the closing full-game total OVER when `CrewShock >= +0.8682`.
Signal from `ref_features.py` unchanged (N=60, min 25, k=78.2, matched league
horizon, equal crew weights). Crew assignments publish mid-morning ET; the
number extends mechanically to new games because the estimator is prior-only.

**Signal 2 — Final week (calendar).**
Bet the closing full-game total OVER in the last 7 days of the regular season
(days_left <= 7). Established in CLOSING.md: 55.29% LOSO, 97.2nd pct
matched-window permutation, 7 of 8 seasons.

The signals are orthogonal (corr −0.0114; ~9 overlap games/season) and the
overlap cell is additive (obs +4.75 residual vs +4.12 predicted). They are
tracked as SEPARATE strategies plus the overlap cell; no combined score is
fitted. Historical reference slate, flat $100 at −110:

```
                       n(8 seasons)   over %   mean e      $
CrewShock Q85 only         1,330      54.40    +1.434   +5,082
final week only              464      56.04    +2.693   +3,182
BOTH                          73      62.50    +4.753   +1,391
union                      1,867      55.12    +1.877   +9,655   (~233 bets/season)
```

## Execution — where the actual leverage is

The signal cannot be improved; the PRICE can. Establishment burden
n = 7.84·0.25/edge², at the pooled 54.82%:

| venue           | break-even | edge    | bets to establish | seasons @233 |
|-----------------|-----------|---------|-------------------|--------------|
| −110            | 52.38%    | +2.44pp | ~3,290            | ~14          |
| −105            | 51.22%    | +3.60pp | ~1,510            | ~6.5         |
| −102            | 50.50%    | +4.32pp | ~1,050            | ~4.5         |
| Kalshi taker    | 51.75%    | +3.07pp | ~2,080            | ~9           |
| Kalshi maker    | 50.00%    | +4.82pp | ~845              | ~3.6         |

Line shopping from −110 to −105 does more than every conditioning test
combined attempted. Timing: bet at/near close — the line historically moves
0.08 points toward the signal open→close and close grading was better
(54.82% vs 54.08%); there is no race when assignments drop.

Staking: flat $100 (frozen convention). Full Kelly at the pooled edge is
~5.1% of bankroll; anything at or below quarter-Kelly (~1.3%) is defensible.
Stake SIZE is an economic choice; stake RULE (flat) is frozen.

## Monitoring — pre-registered metrics and alert thresholds

Computed once per season-end with the existing frozen scripts, unchanged.
These are REVIEW triggers, not automatic actions.

| # | metric (script) | healthy range (history) | ALERT if |
|---|-----------------|------------------------|----------|
| M1 | mechanism `b(pf_rate)` per season, z vs pooled prior (`ref_2526_diag`) | +0.91..+1.46; 2025-26 +0.41, z=−2.48 | z ≤ −2 |
| M2 | forward persistence slope, ≥40-prior refs (`ref_2526_diag`) | 1.43–2.33; 2025-26 1.17 | < 1.30 |
| M3 | market adoption `c_market` per season (`crew_market_trend`) | −0.26..+0.27, never significant | ≥ +0.40 |
| M4 | season win rate, ~175–233 bets (SE ≈ 3.5–3.8pp) | 46.7%–59.6% | outside 45%–60% |
| M5 | final-week over rate | 49.6%–60.0% | < 45% |

Escalation rule, fixed now: ONE alert season = note and continue. The SAME
metric alerting in TWO consecutive seasons = suspend new bets on that signal
and write a closing diagnostic. M4 alone never suspends (it is the noisiest);
M1/M2 are the health of the mechanism and take precedence over P&L in either
direction.

2025-26 already triggered M1 and M2 once (`REFEREE_PROPENSITY_PERSISTENCE_
WEAKENED`). 2026-27 is therefore the decisive season for CrewShock: a second
consecutive M1/M2 alert suspends the signal regardless of P&L.

## Data acquisition — ranked (this is where new signal value lives)

1. **Timestamped injury/availability reports.** The one large omission
   category never tested for lack of data. Fits the exogenous-shock template
   exactly: game-level, published pregame at mandated times, mechanical
   scoring consequence (a rim protector out is a totals shock, not only a
   spread shock). This is the nominated "next independent signal" — as a data
   acquisition, not a feature search.
2. **2025-26+ play-by-play.** Restores M1's defensive-foul decomposition and
   the possession-level monitoring; without it the mechanism check runs on
   box fouls only.
3. **H1 / 2H / live price history.** Converts two confirmed-but-untradeable
   omissions (H2 fouls conditional on H1, p=0.0010; pregame H1) into testable
   markets. Buy only if a source covers ≥2 full seasons.
4. **Reduced-vig venue access.** Not data, but see the table above — it
   dominates everything else per unit of effort.

## What is NOT authorized by this document

- any change to either signal, threshold, or staking rule
- any new historical conditioning or estimator test on CrewShock
- fitting a combined score across the two signals
- reacting to a single alert season
- using monitoring results to re-tune anything retrospectively
