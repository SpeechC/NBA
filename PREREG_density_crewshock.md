# PREREG — SCHEDULE-DENSITY FATIGUE × CREWSHOCK

Written 2026-08-29. **NOT AUTHORISED TO RUN ON HISTORICAL DATA.** §1 explains
why. It is registered now so the criteria are fixed before the 2026-27 data
that could test it exists.

## 0. What was asked, and what is registered instead

The proposal's step 3 was **road-trip fatigue × whistle-prone assigned crew**.
That exact test is **barred**, for three independent reasons:

1. **It is the named prohibition.** The standing rule is "do not rescue
   failures via thresholds, interactions, alternative windows, or **combining
   with CrewShock**." `PREREG_roadtrip_foul` failed hours ago. Swapping
   `LeagueFoulState` → `CrewShock` is that move exactly.
2. **It cannot work.** `PREREG_roadtrip_foul` P3 failed on the **road-trip**
   leg: `home_FTA ~ road_trip_game` = **−0.0537 (t = −1.29)**, the wrong sign.
   Road-trip depth does not generate opponent free throws. Replacing the *foul*
   variable cannot repair a mechanism whose *fatigue* variable is inert.
3. **CrewShock interactions are a retired family.** `CLOSING_REFEREE.md` lists
   four, all dead, under "do not revive without new data" — and its summary of
   the family is **"additive, not superadditive; every interaction null."**

**What is registered instead** swaps the fatigue leg, not the foul leg, because
the fatigue leg is the one that failed. `STREAKS.md` established — before this
week and independently of any failure — that NBA teams *do* tire, just not from
travel:

```
is_4in5   costs 2.57 points of own scoring
is_b2b    costs 1.30
is_3in4   costs 0.83
road_trip_game  +0.19    <- no effect to interact with
```

**This is still variable substitution following a failure, and that is stated
plainly rather than hidden.** The defence is that `STREAKS.md` ranked density
above travel on evidence that predates this test. That is a real defence and
not a complete one, which is why §1 forbids a historical run.

## 1. NOT AUTHORISED ON HISTORICAL DATA

All eight historical seasons have now been used — by `STREAKS.md`, by
`CLOSING_REFEREE`, and by `PREREG_roadtrip_foul` this week. An interaction from
a **0-for-4 family**, reached by substitution after a failure, tested on the
same games for the eighth time, is exactly the search this program's
phantom-book discipline exists to catch.

**This test runs on 2026-27 forward data or not at all.** Running it on
2017–2026 requires an explicit, recorded override from the user, and the result
would carry that caveat permanently.

Earliest honest run: **after the 2026-27 regular season**, roughly 1,230 games,
~200 with `CrewShock` firing.

## 2. States — both frozen, neither rebuilt

- `is_b2b`, `is_3in4`, `is_4in5`: `rest_travel.add_rest_travel`, computed on
  the **full two-sided panel** (a road-only panel fires the streak condition on
  97.6% of games — the error caught in `PREREG_roadtrip_foul` §2).
- `CrewShock`: **frozen** `ref_features.csv` / `crewshock_live.py`, read-only.
  k = 78.247119, N = 60, MINN = 25, threshold 0.8682. Never re-estimated.
- `DENSE = 1[is_b2b OR is_3in4 OR is_4in5]` for **either** team. Fixed here;
  no alternative combination is permitted.
- Target `dev = actual_total − closing_total`.

## 3. Predictions — fixed now

**P3 POSITIVE CONTROL — runs FIRST and gates everything.**

```
opponent_FTA ~ DENSE + controls          PREDICTED: > 0
opponent_pts ~ DENSE + controls          PREDICTED: > 0
```

Does a fatigued team concede more free throws? **This is the exact test the
road-trip version failed.** If density fails it too, the whole
fatigue→contact→free-throws family is dead and no interaction is worth running.
**P3 is reported before P1 is computed.**

**P1 PRIMARY — the interaction, one-sided.**

```
dev ~ DENSE + CrewShock + DENSE*CrewShock + closing_total + season dummies
PREDICTED:  beta_interaction > 0
```

Pass requires **both**: block-permutation p < 0.05 one-sided over contiguous
CrewShock-regime blocks; **and** the effect positive in **at least 4 of 5**
seasons of whatever window is eventually used. The second condition exists
because `PREREG_roadtrip_foul` cleared p = 0.0486 on a coefficient that was
positive in only 2 of 5 seasons and driven 45% by one of them.

**P2 SECONDARY — the tradeable form.** Mean `dev` in the (DENSE ∧ CrewShock ≥
0.8682) cell minus matched controls, same season, closing total ±3. Reported
alongside P1 **because `PREREG_roadtrip_foul` showed the tradeable estimand can
be a quarter of the headline coefficient** (+0.4361 vs +1.6462).

## 4. Fixed readings, including the one my last prereg lacked

- **P3 fails → the branch closes.** Not "P1 becomes uninformative" — closes.
  Two failures of the same free-throw control across two fatigue variables is a
  dead mechanism.
- **P3 fails and P1 passes → NOT A FINDING.** `PREREG_roadtrip_foul` hit this
  case and had no rule for it. Fixed now: a P1 pass without its mechanism is an
  unexplained regularity, not the registered hypothesis.
- **P1 significant and negative → a failure**, reported as such, never
  reframed.

## 5. What is NOT permitted

No alternative density combination, no alternative CrewShock threshold, no
reintroduction of `road_trip_game` or `days_away`, no rotation concentration,
no third interaction term. If P1 fails, **the fatigue × officiating family is
closed permanently** — that will be six dead tests in it, and the correct
inference is that the channel is additive, as `CLOSING_REFEREE` already said.

## 6. Inference and detection burden

Block permutation over contiguous CrewShock-regime blocks, never game-level;
`PREREG_roadtrip_foul` §2 showed a slow officiating state yields ~35 blocks
from ~1,775 games, and a game-level standard error there is wrong by
construction. MDE computed on the **block** standard error and reported whether
or not P1 passes. Points → hit-rate uses `φ(0)/σ`, compared to break-even,
never added to it.

## 7. Prior, stated in advance

**I expect this to fail.** Four CrewShock interactions are already dead, the
family verdict is "additive, not superadditive", and the one fatigue variable
with a real first-order effect has never been shown to move opponent free
throws. It is registered because it is the last version of the idea with a
live mechanism, and because a pre-registered failure on fresh data is worth
more than an unregistered success on used data.
