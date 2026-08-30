# PREREG — FOUL DIFFERENTIAL IN Q4, AND THE FREE-THROW CHANNEL

Written 2026-08-30, BEFORE any outcome was regressed. Only the structural
checks in §2 were run first — foul-type inventory and clock format. No slope,
no test statistic computed.

## 0. Why this needs its own registration

`PREREG_dto_nto_q4` found the officiating channel real (dDTO ~ D at
t = +7.49) but small: the whole turnover pathway explains **22.2%** of the
+1.65-point Q4 comeback effect, leaving **+1.283 points (77.8%) in
non-turnover channels.** §5 of that document explicitly refused to add fouls,
because Price/Remer/Stone avoid them deliberately and widening post hoc is the
move this program forbids. So fouls get their own prereg, and the reason P/R/S
avoided them has to be handled rather than ignored.

**Why fouls are the obvious place for the residual:** `CLOSING_REFEREE` traced
CrewShock's entire mechanism through free throws — +0.834 defensive fouls →
+1.159 FTA → +0.926 FTM → **+0.813 total points**, with made free throws
accounting for 114% of the scoring effect and no residual pace component. If a
referee channel moves scoring in this league, it moves it through the line.

## 1. The confound P/R/S were avoiding, and how it is handled

Fouls carry a confound turnovers do not: **the trailing team deliberately fouls
to stop the clock.** That runs *opposite* to the hypothesised bias and is
concentrated exactly in our high-deficit cell.

It is handled by **exclusion on the event code**, not by inference. The data
labels intentional fouls explicitly:

```
EXCLUDED   28  Personal Take Foul        (6,994 Q4 events)
           6   Away-From-Play Foul       (266)
           11,16,17  Technicals          (different phenomenon)
           14  Flagrant                  (different phenomenon)

KEPT       1  P.FOUL   2  S.FOUL   3  L.B.FOUL
           4  OFF.Foul 26 Off.Charge 27 Personal Block
```

`PCTIMESTRING` is elapsed seconds (Q4 = 2160–2880), so a **last-3:00 exclusion
(≥ 2700) is reported as a robustness check** on top of the code-based one.

## 2. Construction — same panel, same orientation

Source and join as `PREREG_dto_nto_q4`. Orientation is **leading minus
trailing** for anything the leader commits, so a positive slope in `D` means
the referee channel favours the trailing team, exactly as before.

```
D          = |Q3 lead|
dFOUL      = FOUL_clean_leading - FOUL_clean_trailing      (Q4)
dNTO       = NTO_leading - NTO_trailing        (bad pass + lost ball; the
                                                player-behaviour control,
                                                unchanged from the DTO test)
Y_f        = dFOUL - dNTO                                  <- diff-in-diff
dFTA       = FTA_trailing - FTA_leading        (the trailing team's line advantage)
dFGA       = FGA_trailing - FGA_leading        (shot-volume control)
```

**The control is deliberately the same `dNTO` used for turnovers.** All fouls
require a whistle, so there is no "non-discretionary foul" — which is precisely
why P/R/S used turnovers. `dNTO` remains the only whistle-free measure of
player sloppiness available, and reusing it keeps this test comparable to the
one it extends.

## 3. Predictions — fixed

**P1 PRIMARY — the foul difference-in-differences, one-sided.**

```
Y_f = dFOUL - dNTO  ~  D + season dummies        PREDICTED: beta_D > 0
```

Freedman-Lane block permutation, within-season, 5,000 reps, p < 0.05 one-sided.

**P2 — the scoring channel, which is what actually matters.**

```
dFTA ~ D + dFGA + season dummies                 PREDICTED: beta_D > 0
```

`dFGA` is the shot-volume control: a trailing team that simply shoots more will
draw more fouls mechanically. A positive `beta_D` **net of shot volume** is the
whistle.

**P3 MAGNITUDE — the decisive test, as in the turnover version.** Convert the
fitted `dFTA` at D ≥ 12 to points at the league free-throw rate and compare to
the **+1.283-point residual** left by `PREREG_dto_nto_q4`. A statistically
clean channel that explains a trivial share is reported as trivial.

**P0 CONFOUND CHECK, reported first.** Take fouls (28) by deficit bucket, and
P1/P2 re-run excluding the last 3:00. If the code-based exclusion is doing the
work it should, the two agree.

## 4. Fixed readings

- **P1 or P2 significantly NEGATIVE** is a failure of the registered
  prediction — most likely residual intentional fouling — and is reported as
  such, never reframed.
- **P1 passes, P3 trivial →** the channel is real and does not matter. That is
  a legitimate and likely outcome, and it is stated now so it cannot be spun
  later.
- P2 is not conditional on P1: the free-throw channel is the economically
  relevant one and is read on its own terms.

## 5. What is NOT permitted

No alternative foul-code membership to move a result. No alternative deficit
threshold — D ≥ 12 is inherited from `QUARTER_WINNER_AUDIT`. No substitution of
a different player-behaviour control for `dNTO`. If P1 and P2 both fail, **the
foul channel closes** and the +1.283-point residual is attributed to shooting
and personnel, which this family of tests cannot reach.

## 6. Prior

`CLOSING_REFEREE` showed a referee effect running entirely through free throws,
which argues for a real channel. Against that, the intentional-fouling confound
sits in the same cell as the effect, and `PREREG_dto_nto_q4` already showed the
whistle channel to be **statistically strong but economically small**. I expect
**P1 to pass and P3 to be small** — under a third of the residual.

---

# RESULT — run once, 2026-08-30. **Both pass decisively. The magnitude is not trustworthy.**

8,083 games, D ≥ 12 on 3,359.

## P0 CONFOUND CHECK — the confound runs the *opposite* way to my fear

| D | take fouls/gm | dFOUL | dNTO | dFTA |
|---|---|---|---|---|
| 1–5 | **0.935** | +0.170 | +0.001 | +0.074 |
| 6–11 | 0.772 | +0.278 | +0.110 | −0.018 |
| 12–19 | 0.641 | +0.582 | +0.114 | +0.337 |
| 20+ | **0.312** | +1.531 | +0.213 | **+2.071** |

Coded take fouls **fall** as the deficit grows — 0.935 to 0.312. Intentional
fouling lives in *close* games, not blowouts, which is the reverse of the
worry in §1. The code-based exclusion is therefore doing less work than
expected in the cell that matters.

## P1 and P2 — both pass, overwhelmingly

```
P1  Y_f = dFOUL - dNTO ~ D          +0.04746  (t = +10.91)  FL p1 = 0.0002
    component  dFOUL ~ D            +0.05545  (t = +15.33)
P2  dFTA ~ D | dFGA                 +0.09264  (t = +15.72)  FL p1 = 0.0002
```

The foul channel moves at **4.7× the turnover channel's slope** (+0.0555 vs
+0.0117) and is far better estimated.

## P3 MAGNITUDE — and this is where it breaks

```
dFTA +0.09264 per point of deficit  ->  +1.809 FTA at D = 20
                                    ->  +1.393 points at FT% 0.77

= 108.6% of the +1.283 residual        = 84.4% of the whole +1.65 effect
```

**A channel that explains 108.6% of the residual it was meant to explain is not
a triumph — it is evidence the estimate is contaminated.** Something in this
number is not the referee.

## The robustness check identifies the contamination

Excluding the last 3:00 of Q4:

| | full Q4 | no last 3:00 | change |
|---|---|---|---|
| P1 `Y_f ~ D` | +0.04746 (t=10.91) | +0.03116 (t=8.28) | −34% |
| P2 `dFTA ~ D` | +0.09264 (t=15.72) | **+0.04747** (t=10.05) | **−49%** |
| points | +1.393 | **+0.714** | 108.6% → **55.6%** of residual |

**Half the free-throw effect lives in the final three minutes**, after coded
take fouls were already removed. So teams foul intentionally through *ordinary*
personal fouls that the data records as type 1, and the code-based exclusion in
§1 was incomplete. Both predictions survive the exclusion at t > 8, so the
channel is real; the *size* was inflated.

## What cannot be separated here, stated plainly

Even the conservative +0.714 points cannot be attributed to officiating alone.
Three mechanisms produce the same signature and this design does not
distinguish them:

1. **Residual intentional fouling** — demonstrated above, and only partly removed.
2. **Bench personnel.** In blowouts the leading team's reserves play, and
   reserves foul more per minute. `dNTO` controls for *sloppiness*, not for
   *foul-proneness*.
3. **Shot location.** A trailing team driving more draws more contact.
   `dFGA` controls shot *volume*, not where the shots come from.

## Disposition

**The residual is localised, the attribution is not.** The +1.283 points that
`PREREG_dto_nto_q4` could not explain lives in the **free-throw channel** — that
much is established at t > 10 under every specification tried. What share
belongs to referees rather than to end-game tactics and bench personnel is
**not identified by this design**, and no number in this document should be
quoted as the referee share.

Combined picture of the +1.65-point Q4 comeback effect:

| channel | points | share | confidence |
|---|---|---|---|
| turnovers (DTO + NTO) | +0.367 | 22.2% | clean |
| free throws | +0.714 to +1.393 | 43–84% | **real, size contaminated** |
| everything else | remainder | — | untested |

## A gap in this prereg, recorded rather than repaired

§4 fixed what a significantly *negative* result means. It did not fix what an
**implausibly large positive** one means. That case occurred — 108.6% of the
target residual — and the reading is fixed now: **an effect exceeding the
quantity it was introduced to explain is a contamination signal, not a
finding.** Same class of omission as `PREREG_roadtrip_foul`, which had no rule
for "P3 fails and P1 passes."

## §5 holds

No re-specification of the foul codes, no alternative threshold, no substitute
control. Separating referee from personnel needs an identification this family
does not have — most plausibly a within-referee-crew comparison holding the
game state fixed, which would be a new pre-registration and a different design.
