# Power audit of the session's tests — 2026-08-30

Triggered by the retraction in `DISTRIBUTION_AUDIT`: a PIT test was reported as
a finding when it had **no power** — it could not reject a 35% σ error. This
audits every test run this session for the same two failure modes:

- **(a) a NULL reported without knowing what it could detect**
- **(b) a PASS from a test that could not fail, or whose specification flattered it**

## Which preregs priced power BEFORE running

| document | MDE section | priced *before* | verdict |
|---|---|---|---|
| `PREREG_quote_path` | thin | no | failed on **sign** — power not required |
| `PREREG_tip_time` | yes | no | null, MDE computed, **correctly** called well-powered |
| `PREREG_national_tv` | yes | partial | null, **correctly** called underpowered/unresolved |
| `PREREG_cohesion` | yes | method only | passed; observed 0.412 > MDE 0.340 |
| `PREREG_roadtrip_foul` | yes | no | "passed" p=0.0486 with observed **below** the MDE — flagged at the time |
| **`PREREG_dto_nto_q4`** | **NONE** | no | **PASSED — audited below** |
| **`PREREG_foul_q4`** | **NONE** | no | **PASSED — audited below, PROBLEM FOUND** |
| `PREREG_ref_agency_dispersion` | yes | **YES** | null, MDE stated in advance |
| `PREREG_probabilistic_forecaster` | yes | **YES** | failed; power decided the endpoint |
| `DISTRIBUTION_AUDIT` PIT | none | no | **RETRACTED — zero power** |

Only the last two preregs priced power in advance. Both were written after the
lesson began to land.

## AUDIT 1 — `PREREG_dto_nto_q4`: SOUND, and if anything understated

```
observed beta +0.00659 (t=+2.05)    block-null sd 0.00321
one-sided MDE = 1.645 x 0.00321 =   +0.00528
observed EXCEEDS the MDE  -> adequately powered
Y ranges -8 to +10, unbounded in sign -> the test could have failed
```

**Scale check.** DTO is 1.34/game, NTO **4.06**/game — NTO is 3.0× larger. In a
raw-count difference `Y = dDTO − dNTO`, a common proportional shock to both
enters as **negative**. So the raw-count DD is **conservative** here.
Rate-matching confirms it:

```
raw-count    Y  ~ D   t = +2.05
rate-matched Yn ~ D   t = +5.33      <- STRONGER when scale-matched
```

**Verdict: passes the audit.** The conclusion stands and was understated.

## AUDIT 2 — `PREREG_foul_q4`: A SECOND PROBLEM, and it is the mirror image

Power is not the issue (t = +8.28 to +15.72). **The specification is.**

FOUL is **7.42**/game against NTO **2.72**/game — FOUL is 2.7× *larger*, so the
base-rate asymmetry **reverses**. A common proportional shock now enters
`Y_f = dFOUL − dNTO` as **positive**. The raw-count DD is **inflationary** here,
not conservative:

```
raw-count    Y_f  ~ D   t = +8.28
rate-matched Yfn  ~ D   t = +3.33      <- much weaker when scale-matched
```

The effect survives and stays significant, but **the raw-count specification
flattered it**, and this is *independent* of the intentional-fouling
contamination already recorded there. Two separate inflations in one test.

**The general lesson: a raw-count difference-in-differences is only unbiased
when the two series have comparable base rates.** `dto_nto_q4` happened to be
biased in the safe direction; `foul_q4` was not. Neither prereg noticed, because
neither priced the specification.

## What changes

- `PREREG_dto_nto_q4`: nothing. Conclusion stands.
- `PREREG_foul_q4`: the free-throw channel is still real and still the location
  of the residual, but its DD statistic was inflated by base-rate asymmetry on
  top of end-game contamination. **Its magnitude was already declared
  untrustworthy; this is a second reason, not a new verdict.**
- `DISTRIBUTION_AUDIT` PIT: already retracted.

## Standing requirement, added

**Every prereg must state, before the run:**
1. the **MDE** for its primary, computed on the inference method actually used;
2. for any constructed contrast, whether the construction is **scale-matched**,
   and which direction an unmatched one biases;
3. what result would constitute a test that **could not fail**.

Three of this session's nine preregs would have failed requirement 1, and two
of them passed their primary. That is the base rate this requirement exists to
change.
