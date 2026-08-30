# INJURY TIMING AUDIT — was the injury feature using future information?

**Partly yes. Audited rather than defended.** `injury_timing_audit.py`.

## What the code was actually doing

```python
inj[inj.ts == inj.groupby(["gd","team"]).ts.transform("min")]   # EARLIEST report
```

The earliest NBA injury report for each team-game. Timing of that report
relative to an assumed 7pm tip:

```
lead time (hours before tip)   p10 2.0   p50 23.0   p90 26.0
posted the DAY BEFORE the game   57.9%
posted ON the game day           42.1%      <- almost certainly AFTER the opener
```

**42% of the reports I used were posted on game day, with a 10th percentile lead
of two hours.** Opener timestamps do not exist in this data, so the contamination
could not be ruled out by inspection. It had to be measured.

Also relevant: **37.8% of team-games gain a NEW "Out" after the first report**
(mean 0.57 players), and only 4.8% remove one.

## THE INFORMATION-SET LADDER — their Model A / Model B, measured

Three strictly-ordered information sets, same base model, n = 2,990:

| information available | RMSE | R2 |
|---|---|---|
| NONE (baseline line-state) | 3.211 | 0.8719 |
| **STRICTLY KNOWABLE** (team's PRIOR game, final report) | 3.150 | **0.8765** |
| first report this game (timing uncertain — what I used) | 3.121 | 0.8788 |
| **final report** (definitely post-open = ORACLE) | 3.112 | **0.8795** |

```
forecastable gain (prior only)  +0.0047
timing-uncertain gain           +0.0069
ORACLE gain                     +0.0076
INFORMATION-TIMING COMPONENT    +0.0029   = 39% of the total injury gain
```

**So roughly a third of my reported injury gain was not forecastable.** The
correction is real and I should have measured it before reporting +0.008.

### But the ceiling they hypothesised is NOT there

Their proposed test: *"Suppose R2_forecast = .87 and R2_oracle = .90 — then that
last three points is an information-timing problem."*

**Measured: R2_forecast = 0.8765, R2_oracle = 0.8795. The gap is 0.0029, not
0.03.** Perfect foreknowledge of every injury report buys three-tenths of one
percentage point. **Information timing is not what holds the model at 0.87.**

*(Caveat: this oracle is perfect INJURY information only, not everything the
bookmaker knew. It bounds the injury-timing channel, not all timing.)*

## GROUP A CLASSIFICATION — was the shock knowable?

For the 206 games both architectures fail on:

| | A both bad | D both good | diff | t |
|---|---|---|---|---|
| prior-game burden (**KNOWABLE**) | 15.40 | 11.86 | +3.53 | **+3.77** |
| first-report burden | 15.45 | 9.32 | +6.13 | |
| final-report burden (oracle) | 20.40 | 13.62 | +6.79 | |
| **NEW since prior game** | **+0.05** | **−2.54** | **+2.60** | **+4.30** |
| NEW after the first report | 4.95 | 4.30 | +0.65 | **+1.08** |

**The strongest Group A discriminator is knowable, and the late-breaking one is
not significant.**

- Burden already visible at the **previous game** separates A from D at t = +3.77.
- **Change since the prior game** is the single best discriminator, t = +4.30 —
  and it is knowable at the first report.
- **News arriving after the first report does NOT discriminate** (t = +1.08).

The "NEW since prior game" pattern is worth reading carefully: Group D averages
**−2.54** (teams getting healthier between games, the normal case) while Group A
averages **+0.05** (burden holding or growing). Group A games are ones where the
roster **failed to recover** — a condition visible before the line opened.

## Conclusion, which inverts the hypothesis

**Group A is not a forecast-uncertainty ceiling. It is a representation failure
on information we largely possess.**

The evidence:
1. Information timing accounts for only +0.0029 of R2 — a floor, not a ceiling.
2. Group A is discriminated by **knowable** burden (t=+3.77) and **knowable
   change** (t=+4.30).
3. Post-first-report news does **not** discriminate Group A (t=+1.08).

So ~0.87 should **not** be treated as near the ceiling for a genuine pre-opening
forecast. We hold information that identifies these games at t > 3.7 and cannot
convert it — the same conclusion the disaggregation test reached from the other
side. **The bottleneck is how availability enters the model, not when we learn
it.**

That leaves their per-absence state reconstruction as the live hypothesis, now
with a stronger warrant: the information it would consume is demonstrably
available before the line opens.

## Standing correction

All previously reported injury gains used the first-report feature and are
**~32% optimistic**. The forecastable figures are: opener +0.0047 (not +0.008),
and any downstream claim resting on the larger number should be read down
accordingly.
