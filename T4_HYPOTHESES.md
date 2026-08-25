# T4 — HYPOTHESES (statement only; NOT a prereg, NOT frozen)

Written 2026-08-25 after `target_prefilter.py` (board qualifies) and
`t4_feasibility.py` (WNBA calendar half is underpowered). These are stated so
they can fail, and so a later prereg can be written against them once the
feasibility conditions in §5 are met. Nothing here fixes a decision band; the
CBB Phase-2 ruling forbids setting a bar before power is known.

---

## H0 — the meta-hypothesis (why T4 is a target at all)

**A market prices information in proportion to the ATTENTION it receives,
not in proportion to its predictive value.**

Referee assignments are published, free, and known before tip — and nobody
whose job is the total is reading them. This is the same structure as the
crewshock discovery and the Voulgaris frame: do not compete on the question
the market is concentrating on. H0 is not directly testable; it is the reason
H1–H3 are worth testing, and it is what the whole target list inherits.

Corollary already measured: the pregame full-game board is the cheapest
surface in the program (1.0c spread, 2.2c round trip = **0.9 points of
total**). H3's bar comes from this number, not from a significance test.

---

## H1 — EXISTENCE: crews have a persistent, estimable effect on scoring

**Statement.** WNBA officiating crews differ persistently in foul-calling
propensity, and that difference propagates to the total through free-throw
attempts and possession count.

**Stated mechanism-first, deliberately.** The screen showed sd(total) = 20.9
points is what crushes every design. Fouls and possessions carry far less
variance, and the original crewshock finding was foul-based. So H1 is tested
on FOULS/FTA first and only then translated to points — testing on points
directly is the underpowered path.

**Measured as.** Crew (and individual-referee) effects on fouls per game and
FTA per game, controlling for team pace and the pregame line.

**Falsified if** the observed spread of crew means sits inside its own
sampling floor — the identical test that killed the Voulgaris bench-side
claim in CBB (`Var_true` below the sampling floor ⇒ no real dispersion).
This test must be run BEFORE any pricing work: if crews do not differ, H2
and H3 are moot.

---

## H2 — UNPRICED: Kalshi's pregame total does not move with the assignment

**Statement.** The pregame line does not incorporate crew identity.

**The natural experiment.** Assignments are published on the morning of the
game. That gives a clean before/after: if the line does not move across the
publication moment in a way correlated with crew rating, it is unpriced.
This is a far better test than a cross-sectional regression, because it does
not require a powered coefficient — only a detectable move, or its absence,
at a known timestamp.

**Falsified if** the line moves with crew rating at publication (then it is
priced, and there is no edge regardless of H1).

**Prerequisite not yet met:** we do not know Kalshi's line-setting behaviour
relative to assignment publication time, nor the publication time itself for
the WNBA.

---

## H3 — ECONOMIC: the unpriced remainder clears the cost bar

**Statement.** For an identifiable subset of crews, |true crew effect −
amount priced| exceeds **0.9 points of total**.

**Falsified if** no crew's effect exceeds that bar with confidence.

**Power reality, stated in advance.** With ~250 games per official across a
decade of WNBA, a single referee's mean effect is estimable to roughly
**±1.3 points**. Against a 0.9-point bar, this is a "find the few extreme
crews" strategy, never a systematic one. If H1's crew dispersion turns out to
be ~1 point, H3 fails on arithmetic and no sample fixes it.

---

## H4 — CLOSED: calendar shocks (WNBA)

**Was:** matinees, back-to-backs, travel and rest move the total in ways the
line does not price.

**Status: CLOSED on WNBA data**, `t4_feasibility.py`. Minimum detectable
effects against the 0.9-pt bar: matinee 9.7 pts (**11x**), B2B 14.7 pts
(**16x**), rest differential 2x, road trip 3x. Only 59 games carry a Kalshi
pregame line. The measured B2B gap of +12.3 points sits BELOW its own 14.7
detection floor and is therefore not evidence of anything.

**Survives only as:** CONTINUOUS calendar variables (rest differential,
travel distance, schedule density) on the full 8-season NBA panel, where the
per-sd MDE is 0.60 pts (0.7x the bar) — the only powered design found. That
is an NBA-thread question, not a WNBA one.

---

## 5. What must be true before this can be preregistered

1. **H1 passes its sampling-floor test on fouls** — crews genuinely differ.
2. **Crew data is assembled** — bref WNBA boxscores DO list officials
   (verified 2026-08-25; ESPN does not, official.nba.com is NBA-only), and
   `wnba_bref_scrape.py` already fetches those exact pages, so this is a
   regex away and is retroactively backfillable across seasons.
3. **Assignment publication time is known**, so H2's before/after test has a
   timestamp to hang on.
4. **The crew effect size is known well enough** to say whether H3's 0.9-pt
   bar is attainable — per the CBB ruling, the bar is checked before it is
   set, not after.

Until 1–4 hold, T4 is a hypothesis, not a study.
