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
