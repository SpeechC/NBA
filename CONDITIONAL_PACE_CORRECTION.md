# m(X): THE CONDITIONAL PACE-ERROR CORRECTION

Their reframing — stop estimating confidence, estimate the **conditional bias** of
our own pace forecast given the current matchup profile:

```
m(X_t) = E[e_t | X_t]          e_t = PaceActual - PaceForecast
D*_t   = D_t + m_hat(X_t)      D_t = PaceForecast - PaceBook
```

**Structurally immune to the defect that killed `p_survive`:** `m(X)` is fit on
profile features only — no opener, no book-implied pace, no `|D|`.
`conditional_pace_correction.py`. n = 942, one held-out season.

## 1. m(X) CARRIES REAL INFORMATION

```
e ~ m_hat:
  drift only (mu5_H, mu5_R)     beta +0.6641 (t=+2.20)   R2 +0.00514
  FULL 22-dim profile           beta +0.5202 (t=+2.62)   R2 +0.00723
```

**Both significant, and the full profile beats drift alone on its own terms.**
A perfectly calibrated `m` would give `beta = 1.0`; at 0.52-0.66 the predictions
are over-dispersed and would benefit from shrinkage.

**This is a genuine pass** — unlike `p_survive`, nothing here is mechanically
induced by the edge.

## 2. D* IMPROVES ON D, MODESTLY

| signal | → ActualPace − BookPace | t | pace hit | → ActualTotal − Open | t | bet hit |
|---|---|---|---|---|---|---|
| D (raw) | 0.8163 | +11.14 | 59.66% | 0.3005 | +2.10 | 50.96% |
| D* drift | 0.8050 | +11.38 | 60.08% | 0.3139 | +2.27 | 50.53% |
| **D\* full** | 0.7915 | +11.32 | **60.62%** | 0.2638 | +1.92 | **51.49%** |

```
edge per bet:  D 0.673 pts  ->  D*drift 0.728  ->  D*full 0.765   (+14%)
```

**Pace-direction hit rises 59.66% -> 60.62% and edge per bet rises 14%.** Real
but small.

## 3. THE CAVEATS, and they are load-bearing

**All three are BELOW break-even on this subsample** (50.96 / 50.53 / 51.49 vs
52.381%). But the raw `D` scores **50.96%** here against **52.59%** on the
canonical full sample — **this 942-game single-season slice is not
representative**, and the economics cannot be judged from it.

**Drift and full profile are 67% collinear**, and with both in the model neither
clears significance:

```
e ~ m_drift + m_full:   drift +0.2497 (t=+0.62)   full +0.4102 (t=+1.54)
corr(m_drift, m_full) = +0.6672
```

So the full profile's advantage over drift alone is **suggestive, not
established**. Much of `m(X)` may simply be the drift term already known to work.

## VERDICT — and it differs from p_survive

| construct | mechanically confounded? | information test | recommend registering? |
|---|---|---|---|
| `p_survive` | **YES** — 93% collinear with \|D\| | fails once residualised (t = −0.51) | **NO** |
| **`m(X)`** | **NO** — never sees D | **PASSES (t = +2.62)** | **YES, as secondary** |

**Recommendation: register `D* = D + m(X)` as a secondary prospective hypothesis
for 2026-27**, with the 22 profile features, ridge lambda = 20, and the
chronological fit **frozen exactly as built now**. Grounds:

1. it passes an information test that does not depend on the wagering outcome;
2. it is structurally clean, unlike every prior uncertainty construct here;
3. its economic evaluation requires a season this dataset cannot supply.

**Frozen specification:**

```
PROFILE (22): pace_H/R, trans_H/R, tov_H/R, tovf_H/R, ftr_H/R, ctrl_H/R,
              mu5_H/R, ewv_H/R, sP, PrefConflict, ControlConflict,
              TransComp, TovPressure, StyleDist
FIT         : ridge lambda=20 on standardised features, target = dPace,
              chronological (train on all prior seasons), intercept unpenalised
USE         : D* = D + m_hat(X);  PaceGapPoints* = D* x EffSum/100
ENDPOINT    : ActualTotal - Open ~ PaceGapPoints*, one-sided positive
COMPARISON  : reported against the H1 primary using the SAME games
```

**Primary H1 is unchanged.** `D*` is registered as a *comparison*, not a
replacement: if it does not beat `D` prospectively, `D` stands.

**And their broader point is now on record:** the correct object was never a
variance forecast or a confidence score. It was a **conditional mean correction**
— which is why it survived when the others did not.
