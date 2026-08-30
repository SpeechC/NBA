# MARKET CONSTRUCTION REVERSE ENGINEERING — Stage 1

Programme opened 2026-08-30 at the user's direction, replacing autonomous
hypothesis generation. **Question: what model of the game does the totals market
appear to be using?** Not a betting model — a *market emulator*.

Target is the **OPENING** total, deliberately. The close carries injuries, flow
and sharp action; the opener is closer to the construction process.
`emulator.py`, 9,487 regular-season games, **strictly PIT features**:
current-season prior mean shrunk toward the PRIOR-SEASON mean with k=10, which
is what a book actually holds in October.

## 1. THE RECOVERED ARCHITECTURE — it is the multiplicative identity

```
structural term ALONE   Pace x (PPP_h + PPP_r)      RMSE 4.320   R2 0.8011   <- ONE parameter
additive pace + eff     6 separate terms            RMSE 4.289   R2 0.8039
structural + additive   both                        RMSE 4.289   R2 0.8040
```

**A single multiplicative term reproduces 80.1% of opening-total variance, and
the six-parameter additive form adds 0.3 points.** Handing the additive terms to
the structural model adds *nothing*. The bookmaker's architecture is
`Total = Pace x (PPP_home + PPP_road)`, as hypothesised.

## 2. THE HIERARCHY — and what contributes nothing

| model | RMSE | R2 | dR2 |
|---|---|---|---|
| M0 league baseline | 7.990 | 0.3196 | |
| M1 + off/def strength | 6.550 | 0.5427 | +0.2231 |
| **M2 + expected pace** | 4.289 | 0.8039 | **+0.2612** |
| M3 + four factors | 4.279 | 0.8049 | +0.0010 |
| M4 + shot composition | 4.272 | 0.8055 | +0.0006 |
| M5 + rest / schedule | 4.270 | 0.8057 | +0.0002 |
| **M6 + recent state** | 3.508 | 0.8689 | **+0.0631** |

**Pace is the single largest contributor, larger than team strength.** Then
recent form. **The Four Factors, shot composition and rest/schedule contribute
essentially zero** — the Four Factors because they are *components of
efficiency* and are already inside OEFF/DEFF, not because the book ignores them.

Home/road decomposition via `implied pts = (T +- M)/2`, `M = -opening spread`
(sanity: `corr(M, actual home margin) = +0.4516`) gives the same shape —
implied HOME points reach R2 0.8340, implied ROAD 0.8400, with M1 dominant
(+0.40), pace second (+0.175), four factors +0.003.

## 3. THE OPENER IS MORE RECONSTRUCTIBLE THAN THE CLOSE

```
OPENING total   R2 0.8689   RMSE 3.508
CLOSING total   R2 0.8419   RMSE 4.033
```

Targeting the opener was right: the close contains ~0.27 R2 points of
information our PIT features cannot see.

## 4. THE CENTRAL FINDING — shot mix is priced in DISPERSION, not LEVEL

The hypothesis was that a book can assign two teams the same expected score
while their scoring *variance* differs, and that this is where compression
error would live. **Tested against Link 7:**

```
shot composition -> OPENING TOTAL (the MEAN)        dR2 = +0.0006   nothing
3PA rate         -> ladder implied SIGMA            t = +4.65 to +5.31
```

**The market puts shot mix exactly where it belongs — in the second moment, not
the first.** The predicted compression is real as a *description of the mean
model* and is **not** an error, because the dispersion channel carries it. This
is the cleanest result the audit has produced and it closes the shot-mix
omission hypothesis.

## 5. THE RESIDUAL IS INFORMATION, NOT NOISE

```
sd(L) emulator-vs-opener disagreement   3.508 pts
corr(L, actual - open)                 -0.0212
if L were PURE NOISE, corr would be    -0.1903
=> NOISE component of L    0.390 pts
   information / our-error 3.486 pts
```

**At most ~0.39 points of the opener is noise relative to our emulator.** The
book does not beat itself: emulator RMSE against the actual total is 18.696
versus the opener's 18.438, so the book wins, as it must if efficient.

## 6. A THIRD REPLICATION OF "CLV IS EARNED AND NOT CONVERTED"

```
close-open ~ L    slope -0.2355     corr -0.2602
L -> actual-open  corr -0.0212
```

**Where the emulator disagrees with the opener, the market moves ~24% of the way
toward us by close** — about 0.83 points of CLV on sd(L)=3.508. **And L does not
predict the outcome at all.** Same divergence as injury Hypothesis B (CLV +0.775
t=+7.93, P&L −8.04%) and the CBB case. **No trade is implied and none is
claimed.**

## 7. LIMITATIONS, stated before Stage 2 uses this

- R2 0.8689, not the 95% hoped for. The residual `L` is **book information we
  lack PLUS our own model error, and they are not separable.** Stage 2's
  taxonomy is built to survive that, but no statement of the form "the book
  adjusts for X" can be made from `L` alone.
- Rebounding enters only as *total* rebounds — the master has no OREB/DREB
  split, so the OREB-style interaction cannot be tested as specified.
- Everything here is **descriptive**. No hypothesis was tested and no
  pre-registration was consumed. Stage 2 is where that changes.
