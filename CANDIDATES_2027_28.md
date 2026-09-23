# 2027-28 CANDIDATES — things deliberately NOT acted on in 2026-27

Nothing in this file may touch the frozen 2026-27 rule. Each entry records what
was measured, at what strength, and what would have to be true to promote it.
Entries are ranked by current evidential weight, **not** by how interesting they
were when first raised.

`PREREG_2026_27_PROSPECTIVE` D3 still binds: anything noticed in-season is
recorded here and does not touch the frozen evaluation.

---

## C1. M1 — exact PBP possessions as the pace input  *(strongest)*

**Selected on a pre-stated criterion**, `PACE_DEEP_DIVE.md`.

```
n = 5,778 (2020+)          RMSE(PBP)   MAE(PBP)
M0  BDB vendor pace          4.0683     3.2525
M1  exact PBP pace           3.9071     3.0996     <- wins, and in all 7 seasons
M2  off/def duration         3.9757     3.1712
M3  + origin mix             3.9723     3.1688
```

M1 wins decisively and in **every** season. The vendor's formula
`FGA − OREB + TO + 0.44·FTA` uses fixed coefficients, so it mismeasures pace for
teams with unusual OREB/FTA profiles — and the BDB−PBP gap is style-correlated
(OREB −0.3513 t −20.57, FTA −0.2799 t −11.12, PF +0.2743 t +10.74). The original
pace signal could in principle have been partly a measurement artefact
correlated with style.

**To promote:** a full prior-only rebuild of the state engine on M1 pace, with
the trading rule re-derived rather than transplanted. **Blocked on** PBP coverage
for the live season — the store runs 2017-10-17 .. 2025-04-13, and the CDN does
not serve 2017-18.

---

## C2. Possession-only threshold  *(weak — demoted 2026-09-13)*

Threshold on `|D_poss|` instead of `|E_pace| = |D_poss·EffSum/100|`.

**Result: directionally positive, statistically indistinguishable, 97.7%
overlap.**

```
|E_pace| >= 4.77   1,614 bets   54.83%   ROI +4.68%
|E_poss| matched   1,614 bets   55.20%   ROI +5.39%
difference +0.37pp = +6 net wins on 74 swapped games, z = +1.39, p = 0.163
```

**Why it is weak rather than merely unproven.** It was raised on the belief that
`E_pace` is majority-efficiency and therefore misnamed. The exact decomposition
refutes that: `E_pace` is **99.38% possession channel, 0.10% efficiency**
(`PURIFIED_PACE.md` §2). So this is a 0.6%-of-variance change to the selection
variable, and the two rules are nearly the same object. Direction is identical by
construction, since `EffSum > 0`.

**To promote:** it would need to separate on data that did not generate it —
which, at 2.3% of selections, one season cannot supply. Realistically this is a
note against re-deriving the threshold, not a candidate for a rule change.

---

## C3. Opponent-purified pace  *(CLOSED — do not reopen)*

**Closed 2026-09-13.** The frozen update `Pst[hh] += aP*ep; Pst[aa] += aP*ep` is
the exact online gradient of the additive purified model, so the engine is
already the purified estimator and beats every batch variant of it
(MAE 3.115 vs 3.209 equal-weight LS, 3.140 exponentially-weighted LS;
corr +0.968). See `PURIFIED_PACE.md` §1.

Recorded here because the equal split **looks** naive and will invite an
opponent-adjustment rewrite that would break the gradient.

---

## HOW TO USE THIS FILE IN APRIL 2027

Read it once, alongside `OPERATIONS_2026_27.md`'s season-end table. Do not
promote an entry because the season went well — C1 is the only one selected on a
criterion stated before the data were seen, and it is the only one whose
promotion path does not run through this season's outcomes.

---

## C4. Pace closing-residual drift  *(observation only — do NOT act)*

`SHOT_VOLUME_PBP.md` addendum, 2026-09-13. Running the open/move/close information
split on `f_P` as a placebo produced an unlooked-for result:

```
                       opener    move (t)        close (t)     move/opener
f_P  2017-2021          1.013   0.855 (+14.71)   0.157 (+0.44)     84%
f_P  2022-2026          1.701   1.108 (+17.07)   0.594 (+1.65)     65%
```

The pace forecast's **closing** residual rose from 0.157 to 0.594 pts while the
share the market prices intraday fell from 84% to 65%.

**Not significant** (t +1.65), found while running a placebo for a different
variable, and measured on the **same data the 2026-27 prereg was frozen on**
(2026-08-30). D3 binds: recorded here, touches nothing.

**To promote:** it must reproduce prospectively on 2026-27 with the frozen rule
untouched. If H1 passes this season, this is a candidate explanation to test —
not evidence for it, and not a reason to alter the frozen evaluation.
