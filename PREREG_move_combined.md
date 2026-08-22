# PREREG — MOVE_COMBINED: joint ridge + error-latent forecast of the
# opening→closing total movement, 2026-27 forward test

**Frozen 2026-08. New named specification per the `models_frozen.py`
convention; models A and D are unchanged. This authorizes a paper/logging
forward test with CLV as the primary endpoint. It does not authorize live
capital.**

---

## 1. What was found, and the one retrospective economic test

`resid_variance.py` Part 1 established that an error-only latent state
(PCA on 96 prior-bookmaker-residual features) adds movement information beyond
the frozen ridge forecast: joint t = +15.96 / +8.12, prediction correlation
only +0.349. `move_combined_econ.py` then ran EXACTLY ONE retrospective
economic table — combiner weights refit each season on prior OOS seasons only,
fixed threshold grid, no tuning. Results on 5,158 walk-forward games
(2021-22…2025-26):

| \|m\| ≥ | n | win % | ROI % | t vs BE | mean CLV | beat close % |
|---|---|---|---|---|---|---|
| 0.0 | 5,145 | 51.10 | −2.45 | −1.84 | 0.618 | 53.6 |
| 0.5 | 3,230 | 51.70 | −1.29 | −0.77 | 0.993 | 58.1 |
| **1.0** | **1,787** | **53.44** | **+2.02** | +0.90 | **1.337** | **62.2** |
| **1.5** | **814** | **54.42** | **+3.90** | +1.17 | 1.786 | 68.3 |
| 2.0 | 344 | 54.07 | +3.22 | +0.63 | 1.877 | 69.6 |
| 2.5 | 138 | 52.90 | +0.99 | +0.12 | 2.475 | 76.3 |

Ridge alone on the same games: positive ROI only at 1.0/1.5 (+0.49 / +1.96),
negative at 2.0/2.5, and ~62% fewer qualifying bets at each threshold.
Combined season-by-season at ≥1.0: win 54.98 / 48.24 / 55.96 / 54.33 / 53.89
(4 of 5 above break-even; 2022-23 below), CLV positive in ALL five seasons
(+1.07…+1.83).

**Internal consistency check.** Mean predicted |move| in the ≥1.0 bucket is
~1.5 points; at the measured 2.2pp/point conversion that implies ~53.3%
against the observed 53.44%. The model behaves exactly as the arithmetic of a
stale opener implies — the win rate IS the movement forecast, converted.

## 2. Why CLV is the primary endpoint (fixed now)

- ROI at 53.44% needs ~17,500 bets = **~49 seasons** to establish. ROI can
  never be the decision variable; it is secondary by necessity, not choice.
- CLV at ≥1.0 has a historical t ≈ 12.8. One season (~360 qualifying bets)
  gives a CLV standard error of ~0.23 points: E[CLV] of the historical +1.34
  would be detected at t ≈ 6. **CLV is decidable in a single season.**

## 3. Frozen specification

**Components** (both already frozen elsewhere; nothing inside them changes):
- `ridge` = `pred_move` from the `movement_full.py` walk-forward pipeline
  (7-day refits, min 500 games), unchanged.
- `latent` = OLS on principal components (K by cumulative EV ≥ 80%, computed
  in-fold) of the 96-feature error-only state matrix defined in
  `opening_line_error_decomposition.py` (states: score/allowed/total/spread
  opening residuals; transforms: lags 1-3, rolling means 3/5/10/20, rolling
  sds 5/10/20, EWM halflife 5; within-season, strictly prior-only; both teams
  ≥ 10 prior games).

**Deployment convention for 2026-27 — IMMUTABLE.** The entire latent mapping

```
scaler  ->  PCA loadings (and K)  ->  latent OLS coefficients
```

is fit ONCE on all seasons through 2025-26, before the first 2026-27 game, and
**held fixed for the whole season**. No recursive updating, no mid-season
refits, no re-estimation on any window containing 2026-27 observations. The
INPUT state variables (rolling residual features) update naturally as games
complete — they are functions of known past games — but the MAPPING from
states to forecast does not change. Choosing between fixed and recursive
deployment after seeing 2026-27 performance is prohibited; fixed is chosen
now.

**Asymmetry of record.** The ridge component is frozen as a PROCEDURE, not as
parameters: its own spec (`movement_full.py` / `models_frozen.py` PROTOCOL)
mandates 7-day walk-forward refits, and that procedure continues unchanged
through 2026-27. So: ridge = frozen procedure, latent = frozen parameters,
combiner = frozen numbers. All three conventions are fixed here and none may
be revisited during the season.

**Combiner, frozen numerically** (fit on all 6,082 joint-OOS games):

```
m = +0.0337 + 0.8402 * ridge + 0.6869 * latent
```

**Action thresholds, frozen:** the report grid is 0/.5/1/1.5/2/2.5; the
DECISION cells are |m| ≥ 1.0 (primary) and |m| ≥ 1.5 (confirmatory). No other
threshold may be consulted for the verdict.

## 4. Execution convention, frozen (the degree of freedom that must not creep)

- "Opener" = the recorded `OPENING TOTAL_H` of the same BigDataBall feed used
  throughout this project. If the feed changes vendors, the season is
  evaluated but flagged.
- Simulated bet placed AT the recorded opener; pushes void.
- Adverse-execution companion: every table is also computed at opener ±0.5
  toward the bet (the historical grid loses ~2.2pp of win rate per 0.5 points;
  the CLV endpoint is unaffected by execution price and is the reason it is
  primary).
- Price −110 for the secondary ROI endpoint.
- Games qualify only if both teams have ≥ 10 prior games (the latent state's
  own coverage rule); early-season games are out of scope by construction.

## 5. Endpoints and pass criteria (2026-27, evaluated once, at season end)

| rank | hypothesis | PASS |
|---|---|---|
| **P1** | E[CLV] > 0 at \|m\| ≥ 1.0 | t ≥ 2 |
| **P2** | CLV monotone in \|m\| (grid Spearman) | ρ > 0, p < 0.05 |
| S1 | win rate > 52.38% at \|m\| ≥ 1.0 | reported, not decisive |
| S2 | ROI > 0 at −110 at ≥ 1.0 and ≥ 1.5 | reported, not decisive |

P1 AND P2 pass → MOVE_COMBINED is established as a price-forecasting model;
the follow-on question (venue with lower friction than −110) gets its own
pre-registration. P1 fails → the branch closes; no re-tuning, no new windows,
no alternative combiners.

## 6. What is prohibited

- any change to the ridge pipeline, the latent feature list, K-selection rule,
  or the frozen combiner weights
- consulting thresholds outside the frozen grid, or promoting S1/S2 to
  decision status after seeing results
- adding basketball features to the latent state (that is the separate
  second-stage experiment, gated on P1/P2 passing)
- live capital on this signal at a −110 venue (the historical net edge at the
  decision threshold is ~1.1pp — inside the noise of a single season)

## 7. Context of record

The error-decomposition experiment that produced the latent component returned
verdict `MARKET_CORRECTS_STRUCTURE`: the state predicts the line's movement
(t = 12), not the outcome (R² < 0), and the close absorbs it fully
(corr with closing error = −0.0002). MOVE_COMBINED is therefore a
**price-forecasting** specification. Its economic value, if any, lives in
low-friction execution of predicted movement — not in outcome prediction,
which nine dispersion tests and the mean-model history say is closed.
