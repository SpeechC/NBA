# PREREG — NATIONAL TELEVISION

Written 2026-08-26, BEFORE any outcome variable was touched. Only the
broadcast-structure checks in §2 were run first (`tv_structure.py`); they read
broadcast assignments and closing market columns — no score, no `dev`.

## 0. The claim, and an honest statement of its prior

National TV designation is exogenous to same-day team strength, published
months in advance, and non-team. It has a **mechanical channel to scoring**:
national broadcasts carry longer mandatory timeouts than local ones, so the
players get materially more in-game recovery.

**But this candidate sits awkwardly against the framework that generated it.**
The inattention thesis is that whatever the market focuses on is well priced,
and national TV games are the single most-watched games on the schedule. If the
thesis is right, this should be priced. I am recording that prior *before*
running, so a null cannot be presented afterwards as a confirmation I claimed
to expect.

What makes it worth running anyway is a distinction the framework permits:
**the market's attention is on the teams, not on the broadcast format.** The
question is not whether the market prices the Lakers; it obviously does. It is
whether the market prices a *timeout structure* attached to those games. Those
are separable, and §4's P2 separates them.

## 1. Data

- Outcomes, closing lines: `dfMaster_OT_2017-2026.csv` via `read_master()`.
  **Source file never modified.**
- Broadcasts: ESPN dated scoreboard → `tipoffs_espn_tv.csv` (`fetch_tv.py`).
  `bc_national = 1` iff a broadcast entry carries `market: "national"`.
- `CrewShock`: **frozen** `ref_features.csv`, read-only. Not rebuilt, not
  re-estimated, not re-thresholded.

Split as in `PREREG_quote_path` / `PREREG_tip_time`:

```
development   2017-18 .. 2023-24  (incl. IST 2023)
holdout       2024-25, 2025-26    (incl. IST 2024, IST 2025)
```

## 2. Stage-0 gates — RESULTS IN HAND

| gate | result | verdict |
|---|---|---|
| CONTENT — join to master | **9,676 / 9,676 = 100.00%** | **PASS** |
| RANGE — `bc_national` is binary, plausible share | 21.9–25.5% of full seasons | **PASS** |
| ERA — national share across full seasons | 21.9% → 25.5%, **1.16×** | **PASS** |

### An era caveat that the aggregate gate hides

The *share* is stable but the **composition is not**. The 2025-26 media deal
removed TNT entirely and cut NBA TV:

| season | nat% | NBA TV | ABC | ESPN | TNT | other |
|---|---|---|---|---|---|---|
| 2017-18 | 23.0 | 9.1 | 1.4 | 7.1 | 5.4 | 0.0 |
| 2022-23 | 22.2 | 8.7 | 1.6 | 7.0 | 5.3 | 0.0 |
| 2024-25 | 22.1 | 8.8 | 1.9 | 8.0 | 5.1 | 0.3 |
| **2025-26** | 24.5 | **5.3** | 2.0 | 5.2 | **0.0** | **12.5** |

2025-26 is in the holdout. **Fixed here: the holdout is additionally reported
split 2024-25 vs 2025-26**, so a composition break cannot masquerade as a
result or as a failure.

### Confounding, measured in advance

National games are marquee games, and the size of that is quantified now rather
than discovered later:

```
closing total     national 225.05   local 223.89   (+1.16)
|closing spread|  national   5.63   local   6.53   (−0.90)
weekend share     national  0.225   local  0.296
tip hour (local)  national  18.78   local  18.75   (+0.03)
```

Team exposure is extreme: LA Lakers 52%, Golden State 52%, Boston 45% against
Chicago 10%, Detroit 9%, Charlotte 9%, Orlando 8%.

Two things handle this. First, the target `dev` is *already* residualised
against the market's own view of the game. Second, **controls are fixed here**:
`closing total`, `|closing spread|`, a weekend dummy, and `tip_hour`. Tip hour
is included despite being nearly balanced, because it costs nothing and closes
the channel `PREREG_tip_time` examined.

## 3. Construction

```
national  = 1[any broadcast has market == "national"]
nba_tv    = 1[national AND the only national names match /NBA ?TV/]
marquee   = 1[national AND NOT nba_tv]        (ABC / ESPN / TNT / NBC / Prime / Peacock)
dev       = actual_total  − closing_total
dev_s     = actual_margin + closing_spread
```

`nba_tv` is the key construct. **NBA TV games carry the same national broadcast
format — and therefore the same timeout structure — while attracting a small
fraction of the audience.** It is the largest single national network in the
sample (817 games), so the split is well powered.

## 4. Predictions — fixed

**PRIMARY P1.** Longer mandatory timeouts → more in-game recovery → higher
shooting efficiency for both teams → higher total, unpriced.

```
dev ~ national + closing_total + |closing_spread| + weekend + tip_hour
PREDICTED:  beta_national > 0    (one-sided)
```

Pass requires **both**: P1a permutation p < 0.05 one-sided (5,000 reps,
**Freedman-Lane**, per the inference defect found in `PREREG_tip_time`); and
P1b the §5 incremental bar.

**A significant NEGATIVE coefficient is a FAILURE of the pre-registered
prediction and will be reported as such, not flipped into a finding.** The
competing mechanism — national games are more physical and slower — is
acknowledged here precisely so it cannot be adopted post hoc.

**P2 — MECHANISM vs ATTENTION (the reason this test is worth running).**

```
dev ~ nba_tv + marquee + controls
```

- If the effect is the **broadcast format**, `beta_nba_tv ≈ beta_marquee`.
- If the effect is **attention/marquee status**, they diverge.
- If both are ≈ 0, the branch is null and the distinction is moot.

P2 is **interpretive only**. It has no pass/fail bar and **cannot rescue P1.**

**P3 — CREW ASSIGNMENT (mechanism check, no market).** Does a publicly-known
schedule attribute proxy the confirmed-unpriced crew effect?

```
CrewShock ~ national + controls        (frozen ref_features.csv, read-only)
```

No direction is pre-registered; this is descriptive. **P3 cannot rescue P1**,
and no combination of `national` with `CrewShock` will be constructed or traded
on the strength of a P1 failure. Stated here because the standing rule forbids
rescuing failures by combining with CrewShock.

**SECONDARY P4** — `dev_s ~ national + controls`, no direction pre-registered,
reported two-sided.

## 5. Incremental test — the bar that decides it

Fit on development, score **once** on holdout:

```
model A   dev ~ closing_total + |closing_spread| + weekend + tip_hour
model B   model A + national
```

**Bar: model B's holdout OOS R² exceeds model A's.** Reported for the pooled
holdout and split 2024-25 / 2025-26.

## 6. Inference

- **Freedman-Lane** permutation of the control-residualised target, 5,000 reps,
  within-season blocks. Plain permutation of the regressor is **not** used:
  `PREREG_tip_time` established it understates the null spread when the
  regressor correlates with controls, and `national` correlates with both
  closing columns.
- Four predictions declared; the phantom-book 95th-percentile bar is reported
  for P1.
- No same-game outcome enters any regressor. Broadcast assignments are
  published months ahead.

## 7. Detection burden

If P1 passes, the hit rate against the −110 break-even of 52.38% is reported
with required n from `n = 7.84·p(1−p)/edge²`. If P1 fails, the **minimum
detectable effect** is reported so the null is separable from low power — the
distinction fixed in `PREREG_tip_time` §7 and applied here as standard.

## 8. Known limitations, stated in advance

- ESPN's broadcast field reflects *listed* broadcasters. Late national pickups
  and regional simulcasts may be misclassified; this adds noise, not bias, so
  long as misclassification is unrelated to the outcome.
- The timeout-length mechanism is asserted from league broadcast conventions,
  not measured in our data. We have no per-game timeout durations. A P1 pass
  would therefore be consistent with, but not proof of, the timeout channel.
- `national` is confounded with team identity to a degree no control fully
  removes. `dev` residualises the market's view, which is the best available
  answer, not a complete one.
- Single vendor closing line.

---

# RESULT — run 2026-08-26. Verdict: **P1 FAILS. Branch closes.**

Development n = 7,222 (national 1,655 = 22.9%; NBA TV 649, marquee 1,006);
holdout n = 2,450. Frozen `CrewShock` joined read-only at 99.1% coverage.

## P1 — PRIMARY

```
beta_national = −0.7812  (t = −1.53)   FL sd 0.5150   p1 = 0.9280
```

**Wrong-signed.** The prediction was `> 0`; the point estimate is negative and
does not clear significance two-sided either (t = −1.53). §4 pre-committed that
a negative coefficient is a failure of the registered prediction and would not
be flipped into a finding. **P1 fails.**

## §5 incremental — B wins everywhere, and it still is not a pass

| holdout | n | A | B (+national) | B − A |
|---|---|---|---|---|
| pooled | 2,450 | −0.000429 | +0.000532 | **+0.000962** |
| 2024-25 | 1,225 | −0.003968 | −0.003696 | +0.000271 |
| 2025-26 | 1,225 | +0.002652 | +0.004245 | +0.001594 |

`national` improves holdout OOS R² in **both** seasons, including across the
media-deal composition break. That is more consistent than noise usually
manages, and it is recorded plainly. **It is still not a pass:** §4 required
P1a *and* P1b, and P1a failed on sign. The improvement comes from a
*negative* coefficient — the opposite of the registered hypothesis.

## P2 — mechanism vs attention: INCONCLUSIVE

```
nba_tv    −0.4730 (t = −0.63)   p2 = 0.5309
marquee   −0.9858 (t = −1.57)   p2 = 0.1134
```

Both negative, marquee roughly twice NBA TV. That *leans* toward attention
rather than broadcast format — but neither clears significance and the two are
within a standard error of each other. **The discriminator this test was built
around does not resolve.** Reported as inconclusive, not as evidence for
either mechanism.

## P3 — crew assignment: marginal, and directionally coherent with P1

```
CrewShock ~ national:  −0.0438  (t = −1.92)   p2 = 0.0568
```

National games are assigned crews with **lower** idiosyncratic foul propensity.
Marginal, and pre-registered as descriptive only.

**A coherence worth recording, and worth not over-reading.** Lower CrewShock →
fewer fouls → fewer free throws → lower total, which is the direction P1's
negative coefficient points. Two marginal results and a mechanism that links
them is more than noise usually delivers.

But: I did **not** verify that the magnitudes are mutually consistent, this is
post-hoc pattern-matching across results that individually clear nothing, and
the standing rule forbids rescuing a failure by combining it with `CrewShock`.
**Nothing is traded on this.** Testing it honestly requires a fresh
pre-registration with the negative direction fixed in advance, run on data not
used here — realistically 2026-27.

## P4 — spread

```
dev_s ~ national:  +0.6381  (t = +1.73)   p2 = 0.0850
```

Home teams beat the closing spread by about 0.64 points more in national games.
No direction was pre-registered, so this is two-sided and does not clear.

## §7 — this null IS underpowered, and the escape clause applies

Unlike `PREREG_tip_time`, the observed effect here sits **below** the minimum
detectable effect:

```
FL sd of beta   0.5150 points
MDE (95%)       1.0094 points
observed       −0.7812 points     <- smaller in magnitude than the MDE
```

**We cannot distinguish "national TV is priced" from "there is a ~0.8-point
effect we lack the power to resolve."** Per §7 this is reported as *undetectable
at this sample*, not as evidence of efficient pricing. Resolving it needs
roughly 2–3× the national-game sample, i.e. several more seasons.

## A reporting-formula error, corrected

The points→hit-rate conversion used `1/σ`. The correct factor is the normal
density at the line, **`φ(0)/σ = 0.3989/σ`**; `1/σ` overstates the edge by
2.5×. With σ(dev) = 18.11 the density is 0.0220pp per point, so:

```
MDE      1.0094 pts -> 2.22pp edge -> n = 3,966 games
observed 0.7812 pts -> 1.72pp edge -> n = 6,622 games
```

**This error also affected the trailing hit-rate line in `PREREG_tip_time` §7**
(which additionally assumed σ = 13 rather than the actual 18.11). That
prereg's conclusion was stated in **points** (0.31 per day) and is unaffected;
only its final hit-rate sentence was wrong. Corrected here rather than left
standing.

## Disposition

Branch closes as pre-registered. No re-run with the sign flipped, no
`national × CrewShock` construction, no threshold search.

Three of the four candidates I proposed have now returned nulls. I said I
expected one of the four to clear; that has not happened, and the remaining
candidate (lineup cohesion) should be judged against a worse prior than I gave
it. Two of the three nulls (`quote_path`, `tip_time`) are well-powered and
genuinely closed. **This one is not closed — it is unresolved**, and the
distinction matters: a 0.8-point negative effect on the most-watched games,
mechanically linked to a crew-assignment channel we know is unpriced, is the
most interesting thing any of the three produced.
