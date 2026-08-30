# TWO-ARCHITECTURE INTERSECTION — where do BOTH models fail?

Their GPT predictions were unavailable, so **Model B is their architecture
reimplemented**: v5 Layer 1 (structural latent states) + Layer 2 (per-team EWMA
of the structural residual, alpha 0.30, lambda 0.8), same-day safe. Model A is
the two-way line state. **Neither contains injury features** — a clean test.
`model_intersection.py`, `injury_disaggregate.py`.

```
MINE:   two-way line state                  RMSE 3.052  R2 0.8548
THEIRS: structural + market-residual EWMA   RMSE 3.254  R2 0.8372
corr(errA, errB) = +0.8905     corr(|errA|,|errB|) = +0.7863
```

## THE FAILURES ARE COMMON, NOT ARCHITECTURE-SPECIFIC

| group | n | share | chance | mean eA | mean eB | corr(eA,eB) |
|---|---|---|---|---|---|---|
| **A both bad** | 218 | **6.9%** | 1.0% | **−1.412** | **−1.269** | **+0.9878** |
| B mine bad only | 101 | 3.2% | 9.0% | −0.505 | −0.196 | +0.9837 |
| C theirs bad only | 101 | 3.2% | 9.0% | +1.837 | +2.971 | +0.9587 |
| D both good | 2,761 | 86.8% | 81.0% | +0.248 | +0.408 | +0.8444 |

**Group A is 6.9x over-represented; model-specific failures are 2.8x UNDER-
represented.** And the decisive test they specified: **Group A errors share the
same sign (both ≈ −1.3) and correlate at +0.9878.** That is a systematic missing
adjustment, not model noise. Two independent architectures fail on the same
games, in the same direction, by the same amount.

## Group A is DEPTH EROSION, not superstar absence

| feature | A both bad | D both good | t |
|---|---|---|---|
| total VORP | 18.02 | 11.71 | **+6.34** |
| max single absence | 8.72 | 6.28 | +5.77 |
| n players out | 4.30 | 3.68 | +3.48 |
| starters out | 1.91 | 1.29 | +5.15 |
| minutes out | 109.04 | 89.04 | — |
| H-R asymmetry | 9.75 | 6.73 | +4.36 |
| **HHI (concentration)** | **0.74** | **0.79** | **−2.52** |

**HHI is LOWER in the failure group** — against the intuitive prediction. The
games both models miss are **broad availability loss** (4.3 players, 1.9
starters, 109 minutes) rather than one concentrated star absence. A single big
absence is apparently easy for everyone; a reshaped rotation is not.

## BUT DISAGGREGATION DOES NOT FIX IT

Their hypothesis was that scalar burden is too lossy and shape features would
collapse the extra dispersion. Tested directly:

| model | RMSE | R2 | hi-injury \|e\| | **hi-injury sd** | worst \|e\| |
|---|---|---|---|---|---|
| baseline (no injury) | 3.203 | 0.8762 | 2.917 | **3.520** | 6.900 |
| + scalar burden only | 3.098 | 0.8840 | 2.711 | **3.482** | 6.618 |
| + burden, max, count | 3.098 | 0.8840 | 2.717 | 3.488 | 6.612 |
| + FULL disaggregation | 3.100 | 0.8839 | 2.718 | **3.500** | 6.632 |

```
dispersion ratio (hi-injury sd / lo-injury sd)
baseline 1.174   scalar 1.170   FULL DISAGGREGATION 1.178
```

**The scalar burden captures everything. Eight shape features add nothing, and
the dispersion ratio is unmoved.** Explaining the error inside high-injury games:

```
v_sum_g         -0.0575 (t=-3.14)   R2 0.0204   <- the scalar, and the best of them
starters_out_g  -0.2282 (t=-1.98)   R2 0.0082
min_out_g       -0.0073 (t=-2.10)   R2 0.0093
n_out_g         -0.1401 (t=-1.85)   R2 0.0072
v_max_g         -0.0663 (t=-1.63)   R2 0.0056
hhi_g           +0.0565 (t=+0.08)   R2 0.0000   <- concentration carries NOTHING
asym            -0.0114 (t=-0.65)   R2 0.0009
ALL TOGETHER                        R2 0.0241
```

## The corrected claim, and what remains open

**My original wording — "not correctable" — was too strong and they were right to
challenge it.** The defensible statement now, after testing:

> The extra dispersion in high-injury games is not explained by **any summary
> statistic of the absence distribution** — total, maximum, top-two, count,
> starters, minutes, concentration, Herfindahl, or between-team asymmetry.
> Together they reach R2 0.0241 on the error.

**What is NOT refuted, because it was not tested:** their deeper proposal is
structurally different from what I ran. They propose **rebuilding the team state
for the roster that will play**:

```
Off* = OffState - sum_{p in OUT} ExpectedMinutes_p x MarginalOffValue_p + ReplacementValue
```

I added summary covariates **after** the state; they propose changing the state
**itself**, per player, with pace effects included. Given that Group A is depth
erosion — where the *lineup* rather than the *player* is what changed — that is
exactly the case a covariate cannot represent and a re-derived state might.
**It remains the leading untested hypothesis.**

## What this settles

1. **Common missing information is confirmed** — Group A at 6.9x chance, same
   sign, corr +0.9878. Not architecture noise.
2. **It is availability-related** — every injury feature separates A from D at
   t > 3, total VORP at +6.34.
3. **It is depth erosion, not star absence** — HHI *lower* in the failure group.
4. **Summary statistics of absence do not fix it** — dispersion ratio 1.174 ->
   1.178.
5. **Per-absence state reconstruction is untested** and is the only remaining
   candidate identified.
