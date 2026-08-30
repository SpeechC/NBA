# ROSTER-STATE RECONSTRUCTION — the targeted experiment

Replaces the scalar injury covariate with a reconstructed available-roster state,
**strictly pre-open** (each team's PREVIOUS game's final report — the only
unambiguously knowable set, per `INJURY_TIMING_AUDIT`). `roster_state_build.py`.

## Construction — minutes reallocation is the substantive change

```
HEALTHY  : distribute 240 team-minutes over the full roster by prior minutes, cap 38
AVAILABLE: same reallocation over the AVAILABLE roster only
roster_off = (available offence) - (healthy offence)
```

Plus rotation-structure features: top-8 players out, rotation-minutes-out share,
lineup continuity (overlap of expected available top-8 with the normal top-8),
substitutions required.

**The key statistic: `roster_off` averages −1.14 points against VORP's 5.60
gross.** Minutes reallocation absorbs most of the raw loss — the remaining
players simply play more. **A scalar burden cannot represent that**, which was
the whole premise.

## RESULT — better representation, but Group A does NOT collapse

n = 3,137, Group A = 216 games:

| model | RMSE | R2 | **Group A MAE** | worst-decile MAE |
|---|---|---|---|---|
| baseline (no availability info) | 3.206 | 0.8767 | **7.074** | 6.911 |
| + SCALAR injury burden (knowable) | 3.142 | 0.8814 | **6.759** | 6.723 |
| + roster offence delta only | 3.132 | **0.8823** | 6.805 | 6.755 |
| + FULL roster-state reconstruction | 3.138 | 0.8818 | 6.762 | 6.757 |
| + roster state AND scalar | 3.143 | 0.8813 | 6.759 | 6.764 |

**Group A MAE falls 7.074 -> 6.76-6.81, about 4-5%, and the roster reconstruction
is no better there than the scalar it replaced.** The pre-registered criterion —
does Group A collapse — is not met.

The reconstruction *is* a better representation overall:

```
explaining the baseline error, ALL games:
  v_prior_g (scalar)     -0.0540 (t= -8.87)   R2 0.0370
  roster_off_g           +0.0956 (t= +9.84)   R2 0.0451   <- better
```

but the improvement is +0.0009 of model R2 (0.8814 -> 0.8823), not a step change.

## Within Group A, availability explains 3-4x more than it does overall

```
v_prior_g            -0.1990 (t=-4.78)   R2 0.1255
cont_min             +15.224 (t=+4.48)   R2 0.1123
roster_off_g         +0.2770 (t=+4.37)   R2 0.1074
top8_out_g           -1.2389 (t=-4.31)   R2 0.1047
rot_min_out_share_g  -8.0292 (t=-4.05)   R2 0.0934
ALL roster features together             R2 0.1513
```

Against R2 0.037-0.045 across all games. **Group A really is availability-driven**
— the diagnosis holds. **Caveat: Group A is selected on large |error|, so these
in-sample R2 values are optimistic** and are not comparable to the chronological
OOS model figures above.

But 15% of Group A's error explained still leaves 85%, and it converts to only a
4-5% MAE reduction out of sample.

## What was NOT implemented — and it is the part they flagged as most likely

Their proposal had four components beyond minutes reallocation. **None are in
this build:**

- per-player **defensive** value (only offence, via points-per-minute)
- per-player **pace** contribution
- **lineup-combination / rotation interaction** term
- **opponent-specific** interaction

They wrote: *"That final interaction term is probably where the depth-erosion
result is pointing."* **That term remains untested**, and the depth-erosion
finding (Group A has LOWER concentration, more players out, more starters out)
is exactly the case where combinations rather than individuals should matter.

## Honest status

**Three availability representations have now been tried** — scalar burden,
eight-way disaggregation, and minutes-reallocated roster state. All three:

```
move pooled R2 by  +0.005 to +0.006
move Group A MAE by  -4% to -5%
leave the high-injury dispersion ratio near 1.17
```

**The diagnosis is robust and repeatedly confirmed: Group A is availability-driven
and the information is pre-open knowable.** What has not worked, three times, is
converting that into accuracy through any *team-aggregate* representation of who
is missing.

The remaining untested candidate is genuinely different in kind — modelling
**lineup combinations** rather than summed player values — and it is the one the
depth-erosion signature points at. It is also substantially more work than
anything attempted so far, and on this evidence should be costed against an
expected gain of the same order unless combinations behave differently from sums.
