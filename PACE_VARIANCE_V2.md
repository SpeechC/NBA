# PACE VARIANCE, DONE PROPERLY — a partial reversal

Their critique of `PACE_SIGNAL` §1 was correct on all three counts: I used
un-residualised errors, judged the model by R2 on a hopelessly noisy target, and
never tested state ambiguity. Redone. `pace_variance_v2.py`.

## STEP 1 — residualise the drift first

```
var(raw pace error)  16.081
var(u) after drift removal  15.999      only 0.5% removed
```

**The drift contamination they worried about is negligible** — drift is ~0.5% of
pace-error variance. The premise that mixing drift into rolling SDs was corrupting
the volatility estimate is not supported; there was almost nothing to mix in.

## STEP 2 — variance model on `u`, judged by CALIBRATION not R2

| predicted sigma tercile | n | pred sigma | ACTUAL sd(u) | sd(u/sigma) | P(\|u\|>5) |
|---|---|---|---|---|---|
| low | 691 | 3.546 | 4.060 | 1.172 | 22.0% |
| mid | 691 | 3.827 | 4.047 | 1.057 | 20.0% |
| high | 691 | 4.127 | 4.184 | 1.014 | 23.4% |

```
ACTUAL sd(u) 4.060 -> 4.184   ratio 1.030   F-test p=0.4313   DOES NOT SEPARATE
tail rate 22.0% -> 23.4%
```

**A fitted linear model on `u^2` still fails**, on their own calibration metric,
not on R2.

## BUT — sorting on a single PRIOR-ONLY feature DOES separate

No fitting; just rank games by a pregame feature and measure realised dispersion:

| feature | lo sd(u) | hi sd(u) | ratio | F-test p | verdict |
|---|---|---|---|---|---|
| **volx = Vol_H x Vol_R** | 3.807 | 4.126 | **1.0836** | **0.0098** | **SEPARATES** |
| ewv_g (EWMA variance) | 3.893 | 4.135 | 1.0621 | 0.0527 | marginal |
| sd10_g | 3.918 | 4.144 | 1.0576 | 0.0718 | no |
| **Dp_g = \|P5 − P20\| (STATE AMBIGUITY)** | 3.967 | 4.063 | **1.0243** | **0.4406** | **no** |
| clash = \|P20_H − P20_R\| | 4.033 | 3.965 | 0.9830 | 0.5802 | backwards |

```
POWER: MDE 0.2436 pts = 6.1% of sd.  The volx effect is 8.4%. Powered.
```

## The revision, stated precisely

**My claim "pace uncertainty is not forecastable" was too strong and is
withdrawn.** The correct statement:

> A small but statistically real component of pace-error variance is
> forecastable, carried by the **interaction of the two teams' prior pace
> volatility** (sd(u) 3.807 -> 4.126, p = 0.0098). A linear model fitted on `u^2`
> does not extract it.

**But their specific hypothesis is NOT supported.** They argued the epistemic
quantity — confidence in the latent pace state, measured as short-vs-long
disagreement — should beat historical volatility. **`Dp_g` is the WEAKEST of the
volatility measures (ratio 1.0243, p = 0.4406)**, and the pace-preference clash
runs backwards. **Plain volatility wins; state ambiguity does not separate at
all.**

## Two cautions on the positive result

**The quintile split is non-monotone and marginal:**

```
volx quintile   1      2      3      4      5
sd(u)         3.911  3.772  4.101  3.951  4.229     Q5/Q1 ratio 1.0812, p=0.0519
```

Terciles give p = 0.0098; quintiles give p = 0.0519 and a non-monotone middle.
**An effect that depends on the binning is not robust.**

**And the magnitude is small in the space that matters:**

```
d(total)/d(pace) = EffSum/100 = 2.30
Q1 pace sd 3.911 -> 9.02 pts of total uncertainty
Q5 pace sd 4.229 -> 9.75 pts
difference +0.73 pts
```

**0.73 points of forecastable spread in total uncertainty, against a total sd of
~18.** Real, and roughly a 4% modulation of the quantity a bettor would size on.

## CONSEQUENCE FOR THE FROZEN PREREG — a decision is needed NOW

`PREREG_2026_27_PROSPECTIVE` freezes `sigma_P` as the 5-feature linear model.
**That is the specification just shown NOT to separate realised dispersion
(p = 0.4313).** The secondary `<220 x high sigma` hypothesis therefore rests on a
gate that does not work.

**No 2026-27 data exists, so revising the frozen definition is legitimate — but
only now, and only recorded explicitly.** Two options:

1. **Replace** `sigma_P` with the `volx` tercile split (the only specification
   that separates), and re-freeze.
2. **Keep** the registered definition and accept that the secondary hypothesis
   is testing a gate with no demonstrated discriminating power.

**Recommendation: option 1**, because the secondary hypothesis is only meaningful
if the uncertainty split is real, and `volx` is the only version of it that has
survived a test. Whichever is chosen must be written into the prereg before
2026-10-20.
