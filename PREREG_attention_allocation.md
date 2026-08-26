# PREREG — does MOVE_COMBINED's CLV concentrate where attention is scarce?

**Written 2026-08-26, BEFORE any attention split is joined to CLV.**
Estimated EXACTLY ONCE. Does NOT modify `PREREG_move_combined.md`, the frozen
signal, its thresholds, or the 2026-27 forward test.

## 0. Provenance and what this is NOT

Inattention-framework candidate #2. Reasoned, not mined: the program's own
conclusion is that the closing line is an ensemble aggregated through
correction flow, and that flow is FINITE — on a 15-game night, line-setters
and sharps must ration attention. MOVE_COMBINED already exploits the opener
before correction arrives; if correction arrives LAST at the least prominent
game on the largest slate, its CLV should concentrate there.

This is **not a new signal**. It is a bet-SELECTION question about an
already-frozen one. Nothing here can improve MOVE_COMBINED's forecast; it can
only say whether the same forecast is worth more in some games than others.

**THE HAZARD, STATED FIRST.** MOVE_COMBINED is preregistered for a 2026-27
forward test on ALL games clearing |m| >= 1.0. Any result here creates a
temptation to bet a subset next season. That is prohibited by section 6: the
frozen forward test runs unchanged regardless of this document's outcome. A
concentration result would justify a SEPARATE, LATER prereg — never a
mid-flight change to a test already frozen.

## 1. Attention proxies, fixed now, in priority order

```
A1 SLATE_SIZE     number of NBA games that calendar date            (all seasons)
A2 PROMINENCE     rank of the game's summed prior-only team quality
                  (mu_state) within its own date; low rank = obscure  (all seasons)
A3 KALSHI_VOLUME  total contracts traded on that game's ladder,
                  as a DIRECT per-game attention measure         (2025-26 only)
```

A1 and A2 combine into the pre-specified cell:

```
LOW_ATTENTION = SLATE_SIZE >= its development Q67  AND
                PROMINENCE in the bottom half of that date
```

Thresholds frozen on development seasons only. A3 is reported SEPARATELY as
corroboration on its single season and cannot enter the decision (one partial
season, and Kalshi volume is a different venue's attention).

## 2. Endpoints — CLV primary, unchanged from the parent prereg

For every game with |MOVE_COMBINED_OOS| >= 1.0 (the frozen action threshold,
not re-optimised):

```
CLV  = sign(m) * tmove                    points of closing-line value
```

Primary: mean CLV in LOW_ATTENTION vs the rest, difference tested.
Secondary, reported never promoted: win rate and ROI at -110 (the parent
prereg already establishes these need ~49 seasons and are not decisive).

## 3. Sample and split

5,158 games carry the frozen signal (2021-22..2025-26); 1,792 clear |m| >= 1.0
across 629 dates. Development 2021-22..2023-24; holdout 2024-25 + 2025-26,
reported separately. Slate sizes span 1-15 games with the mass at 6-11, so the
split has support at both ends.

## 4. Positive control (bar derived from measured quantities)

The pooled CLV at |m| >= 1.0 must reproduce its known value on this sample:
**mean CLV >= +1.0 points with t >= 5** (the parent prereg measured +1.34 at
t ~ 12.8 over a longer window; +1.0/t>=5 is set safely below that on the
shorter one). If the pooled effect is absent, the harness is wrong and no
attention cell is interpreted.

## 5. Decision rule, fixed now

CONCENTRATION ESTABLISHED requires ALL:
- LOW_ATTENTION mean CLV exceeds the rest by >= 0.35 points on development
  (a quarter of the pooled +1.34, i.e. large enough to matter for selection);
- the difference carries |t| >= 2 on development;
- the holdout difference has the SAME SIGN;
- within-date permutation p < 0.05 on development — the state is permuted
  ACROSS GAMES WITHIN EACH DATE, which holds slate size fixed by construction
  and isolates prominence from any date-level effect.

Anything less: recorded as "CLV is attention-invariant", which is itself a
useful result — it would mean correction flow does not ration the way the
framework assumes, and would weaken the framework's core premise.

## 6. Prohibited

- estimating more than once; re-cutting Q67 or the prominence split after
  seeing results
- trying other proxies (national TV, rest, team market size) after a failure
- **changing the 2026-27 forward test in any way on the basis of this
  document** — the frozen test runs on all qualifying games regardless
- promoting the ROI/win-rate rows
- using A3 (Kalshi volume) in the decision

---

## 7. RESULT — run once, 2026-08-26. Verdict: CLV IS ATTENTION-INVARIANT

1,792 bets at |m| >= 1.0 across 629 dates (dev 1,120 / holdout 672).
Frozen dev Q67 slate size = 10.0; LOW_ATTENTION fires on 317 bets (17.7%).

**Positive control PASSES decisively**: pooled mean CLV **+1.3367, t = +16.42**
— reproducing the parent prereg's +1.34 almost exactly on this sample. The
signal is unambiguously present; the question is only whether it varies.

| window | n low | CLV low | n rest | CLV rest | diff | t |
|---|---|---|---|---|---|---|
| development | 193 | +1.459 | 927 | +1.276 | **+0.183** | +0.67 |
| holdout | 124 | +1.347 | 548 | +1.394 | **-0.047** | -0.13 |

Within-date permutation (development): observed +0.1826, null sd 0.1937,
**p = 0.3615**. All four criteria fail; the holdout difference even flips sign.

**A3 corroboration, barred from the decision and pointing the same way**:
on 2025-26 Kalshi volume, low-volume games CLV +1.411 vs high-volume +1.345,
diff +0.065 (t = +0.17). A DIRECT per-game attention measure, an independent
venue, and the same non-result.

### What this means — and it cuts at the framework

The opener's exploitable error does NOT depend on how much attention the game
receives. The effect is remarkably flat: ~+1.3 points of CLV whether the game
is the marquee matchup on a 3-game night or the 11th game on a 15-game
Saturday, and whether Kalshi traded 10x more contracts on it or not.

Three readings, and the program should hold all of them:

1. **Openers are systematically stale by PROCESS, not by neglect.** A book
   posting an opener is applying a routine at a moment when little correction
   flow has arrived anywhere. The staleness is a property of the TIMING, not
   of how closely that particular game is watched.
2. **Correction flow does not visibly ration across a slate** — at least not
   at a magnitude that reaches opener error. This is a genuine strike against
   the attention thesis's mechanism, in the one place it was directly testable
   with an already-validated signal.
3. **Practically, it is good news for deployment.** MOVE_COMBINED needs no
   game selection: every qualifying bet is worth the same CLV. Simpler,
   higher-volume, no new parameters — and the 2026-27 test runs unchanged,
   as section 6 required regardless of outcome.

### Framework status after two nulls

Referee fatigue died on MECHANISM (unattended input that does not affect the
game). Attention allocation died on PREMISE (attention varies, the edge does
not). Neither touches the framework's successes — CrewShock and MOVE_COMBINED
remain unattended-input/liquid-venue findings — but the sharpened rule is now:
**"unattended" identifies candidate inputs; it does not by itself predict
where within a market the mispricing sits.**
