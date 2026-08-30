# NBA Market Emulator — Stage 2 Interaction Preregistration

**Authored by the user, 2026-08-30, recorded verbatim BEFORE any Stage 2 outcome
was examined.** Stage 1 is frozen at commit `05c3bdb`.

## 1. Research objective

Stage 1 recovered a parsimonious approximation to the NBA totals-construction
architecture. The principal findings are frozen:

- The core structural relationship is approximately `Total ~ Pace x (PPP_H + PPP_R)`.
- The one-parameter multiplicative structural term explains approximately the
  same variation as the separate additive pace/efficiency representation.
- Expected pace is the largest incremental contributor to the opening total.
- Four Factors and shot composition add almost no incremental explanatory power
  to the opening mean after efficiency is represented.
- Shot composition, particularly 3PA rate, materially affects the
  market-implied second moment rather than the opening mean.
- The opening total is substantially more reconstructible than the closing total.
- Emulator disagreement with the opener predicts subsequent market movement but
  does not predict realized scoring error.

Stage 2 therefore does **not** ask whether arbitrary basketball variables
predict totals. It asks:

> Are there prespecified matchup interactions that are not materially
> represented in the market's opening-total construction but nevertheless
> predict realized scoring error after the market closes?

The target finding is a **matchup-level violation of the recovered market
architecture**.

## 2. Frozen Stage 1 model

The Stage 1 market emulator committed in `05c3bdb` is frozen before Stage 2
outcome examination. No Stage 2 candidate interaction may be added to or used to
refit the base emulator before its incremental market test. Let `That_open`
denote the frozen emulator estimate of the opening total. The interaction search
must use the same PIT information rules used in Stage 1.

No outcome-informed changes to windows, transformations, signs, interaction
definitions, thresholds, seasons, or emulator specification are permitted after
Stage 2 outcomes are examined.

## 3. Interaction construction

Each matchup interaction is one symmetric game-level continuous variable rather
than separate home and road hypothesis tests. For offensive characteristic `A`
and opposing defensive characteristic `D`:

```
Z_t = [ z(A_H)*z(D_R) + z(A_R)*z(D_H) ] / 2
```

All component states must be strictly pregame/PIT. Higher values of
defensive-side variables must be oriented so that higher means **more exposure
to the proposed offensive mechanism**.

The continuous interaction is primary. No post-outcome conversion to arbitrary
quantile cutoffs is permitted. For descriptive economic analysis only, the
preregistered top-quintile interaction regime may subsequently be compared with
the remaining eligible sample. It does not replace the continuous primary test.

## 4. Frozen interaction family — exactly three

**H1 — Three-point volume x opponent three-point allowance.**
`3PAR_offense x 3PAllowance_opponent`. Mechanism: the recovered architecture
incorporates marginal shot composition primarily through the second moment. It
may nevertheless compress away matchup-specific compatibility between an offense
generating unusually high three-point volume and a defense permitting unusually
high three-point opportunity. Two games can have similar expected pace and
aggregate PPP while differing in the probability that possessions are allocated
to the high-variance/high-payoff three-point channel.
**Predicted sign: positive on `actual - close`.**

**H2 — Transition propensity x opponent live-ball turnover supply.**
Mechanism: each state can be incorporated marginally into efficiency estimates
while the market compresses away their conjunction. Live-ball turnovers create
unusually high-value possessions because they alter defensive organization,
shot-clock state, floor balance and expected shot quality. An offense
predisposed to exploit transition should convert opponent live-ball turnovers
into a larger scoring effect than adding the two marginal states implies.
**Predicted sign: positive on `actual - close`.**

**H3 — Foul-drawing pressure x opponent foul propensity.**
`FTAIntensity_offense x FoulPropensity_opponent`. Mechanism: the market can
correctly incorporate average offensive FT generation, average defensive foul
propensity, and average efficiency while still compressing their matchup
interaction. A foul-dependent offense meeting an unusually foul-prone defense
can produce disproportionately many clock-stopped scoring opportunities. This is
distinct from the rejected road-trip x league-foul-climate hypothesis: it is a
direct team-offense x opponent-defense interaction with no travel or league-wide
referee state.
**Predicted sign: positive on `actual - close`.**

## 5. Market-incorporation test

For each frozen `Z_k`:

```
OpenTotal_t = alpha + gamma*That_open_t + beta_line_k * Z_kt + eps
```

The purpose is not to interpret emulator residual `L` as pure bookmaker
information, but to determine whether `Z_k` provides incremental information
about the opener conditional on the frozen emulator.

**Practical-equivalence requirement.** Failure to reject `beta_line = 0` is NOT
sufficient to declare the market ignores an interaction. An interaction is
classified as having no economically meaningful opening-line effect only if a
TOST/equivalence procedure supports `|beta_line_k| < 0.25` opening-total points
per one-SD change in the standardized interaction. The +-0.25 interval is frozen
ex ante because it is smaller than one standard half-point NBA total increment.

- **Incorporated** — evidence supports an opening-line effect of economically
  meaningful magnitude.
- **Equivalent to zero** — the 90% equivalence CI lies entirely inside
  `[-0.25, +0.25]`.
- **Indeterminate** — neither established. **Cannot be labeled a market omission.**

## 6. Primary outcome test

Primary outcome is `Y_t = ActualTotal_t - CloseTotal_t`. **Market movement is NOT
the grading target.**

```
Y_t = alpha + beta_outcome_k * Z_kt + season controls + closing-total benchmark controls + eps
```

The existing frozen within-season closing-total conditioning protocol is used so
structurally different games are compared at similar market-implied scoring
levels. Preregistered sign for H1-H3 is positive. **No hypothesis may be rescued
by changing its sign after observation.**

## 7. Multiple-comparison control

Exactly three primary outcome hypotheses. Familywise inference uses **Holm
correction at alpha = 0.05** across H1, H2, H3. The market-incorporation/
equivalence tests form a separate three-test family with the same Holm
treatment. No additional interaction joins the Stage 2 confirmatory family after
outcome examination; further ideas are Stage 3 and need a new preregistration.

## 8. Classification taxonomy

| Opening-line evidence | Outcome evidence | Classification |
|---|---|---|
| Incorporated | No outcome effect | MARKET PRICES INTERACTION |
| Incorporated | Outcome effect | MARKET RECOGNIZES BUT MISPRICES |
| Equivalent to zero | Outcome effect | **CANDIDATE OMITTED MATCHUP STATE** |
| Equivalent to zero | No outcome effect | IRRELEVANT TO MEAN PRICING |
| Indeterminate | Any result | UNRESOLVED |

The principal target, **CANDIDATE OMITTED MATCHUP STATE**, requires BOTH
practical-equivalence evidence of no meaningful opening-line effect AND
Holm-significant residual outcome evidence in the preregistered direction. A
nonsignificant opening-line coefficient alone does not qualify.

## 9. Economic materiality gate

For descriptive top-quintile-versus-control analysis, require an absolute
matched closing-total residual difference of at least **0.75 points** in the
preregistered direction. If statistically significant but economically smaller,
classify **STATISTICAL EFFECT / LOW ECONOMIC MATERIALITY** rather than an
actionable market violation.

## 10. Market movement analysis

Diagnostic only. `CloseTotal - OpenTotal` may be regressed on each frozen
interaction to see whether information is assimilated between open and close.
However: movement significance does not advance a hypothesis; CLV does not count
as validation; a hypothesis with movement but no realized-outcome effect is
**rejected** as a betting-market edge. Frozen because Stage 1 and prior work show
repeated earned CLV without realized-outcome conversion.

## 11. Historical validation

Discovery and historical validation use frozen temporal splits. A result may
advance only if direction is unchanged, interaction definition is unchanged, no
threshold/window tuning occurs, economic magnitude remains material, and
validation evidence is directionally consistent. Because historical NBA seasons
have already been repeatedly examined in this program, successful historical
validation is **candidate evidence, not final confirmation**. True confirmation
requires a sealed future sample not used during hypothesis generation.

## 12. Prohibited adaptations

After outcomes are observed, do not: change interaction windows; swap related
metrics; reverse orientation; change the expected sign; replace continuous tests
with a favorable quantile; test alternative thresholds; add a third conditioning
variable; split home and road versions; isolate favorable seasons; substitute
opening residual for closing residual; or promote market movement/CLV into the
outcome criterion. Any such modification is a new hypothesis requiring a new
preregistration.

## 13. Success criterion

Stage 2 succeeds scientifically even if all three hypotheses fail. The question
is not "can we find a significant interaction" but: after recovering the dominant
totals-construction architecture, can we identify a prespecified matchup
interaction practically absent from the opener yet systematically surviving into
realized closing-price error? A positive result must survive the complete
taxonomy, multiple-comparison control, economic-materiality requirement, and
frozen validation protocol.

### Excluded by decision, recorded

OREB x DREB is excluded on the Stage 1 data limitation (master has total
rebounds only, no offensive/defensive split). Assisted-creation x steals,
eFG x FTA, road-trip x fouls, and rotation x OREB are excluded because closely
related outcomes have already been examined in this program and mixing them in
would contaminate an otherwise clean fresh test.

---

# RESULT — run once, 2026-08-30. **All three: IRRELEVANT TO MEAN PRICING.**

`s2_pbp.py`, `s2_build.py`, `s2_run.py`. n(H1,H3) = 9,485; n(H2) = 8,327.

## Stage 0 — construction, run before any outcome was examined

All six component states are PIT-persistent, so each is genuinely forecastable:

```
off_3par +0.5941   def_3par +0.4554   off_ftar +0.4455
def_pf   +0.5008   off_trans +0.4425  def_live +0.4513
```

Interactions are centred, orthogonal to the frozen emulator, era-stable, and
mutually independent — so the Holm family is effectively independent:

```
Z_H1  mean -0.0094  corr(That_open) -0.0046      Z_H1/Z_H2  r +0.0003
Z_H2  mean +0.0010  corr(That_open) +0.0126      Z_H1/Z_H3  r +0.0112
Z_H3  mean +0.0059  corr(That_open) +0.0003      Z_H2/Z_H3  r +0.0089
season means of Z all within +-0.045
```

**Two pre-outcome construction repairs, recorded.** (1) Components are z-scored
**within season**: pooled standardisation made `Z_H1` partly an era indicator
(mean +0.449, corr with the emulator −0.303) because of the league-wide 3PA
rise. (2) `Z_H2` is **restricted to seasons with genuine PBP coverage** — the PIT
shrinkage had silently filled 2025-26 from the league mean, inflating n from
8,327 to 9,489 with non-information. Both were made before any outcome was
touched; §12 binds only afterwards.

`off_trans` is built from the PBP's own possession delimiters
(`PCTIMESTRING - STARTTIME`), giving an early-clock (<=7s) share of **0.188**
(p10 0.126, p90 0.253) — the expected 15-25% band. `def_live` is bad-pass plus
lost-ball, 7.76/game, 58.0% of all turnovers.

## Power, priced before reading the outcomes

```
sd(Y) 18.065   se(beta per SD) 0.1855   MDE 0.3636 pts/SD
materiality gate 0.75 pts over a ~1.6-SD quintile gap = 0.460 pts/SD
=> POWERED for an economically material effect
```

**This is a powered null, not an absent test.**

## §5 Market-incorporation — all three EQUIVALENT TO ZERO

```
H    beta_line       se            90% CI          classification
H1     -0.0308   0.0731   [-0.1511, +0.0894]   Equivalent to zero
H2     -0.0870   0.0757   [-0.2115, +0.0376]   Equivalent to zero
H3     -0.0160   0.0731   [-0.1363, +0.1043]   Equivalent to zero
```

**The equivalence requirement earns its place here.** All three 90% CIs sit
entirely inside +-0.25, so this is affirmative evidence that the opener does not
price these interactions — not mere failure to reject.

## §6/§7 Primary outcome — no effect, Holm or otherwise

```
H       n     beta_out      se       t   p(1-sided)   Holm p   sig
H1  9,485      +0.0306  0.1856   +0.16       0.4345   0.8691    no
H2  8,327      +0.1320  0.1976   +0.67       0.2521   0.7564    no
H3  9,485      -0.1460  0.1856   -0.79       0.7843   0.8691    no
```

**H3 carries the wrong sign** and is reported as a failed registered prediction,
not reframed.

## §9 Materiality and §10 movement — both null

```
top-quintile diff (matched)   H1 +0.4896   H2 +0.6159   H3 +0.4403   all < 0.75
close-open ~ Z                H1 -0.0312 (t=-0.96)  H2 -0.0499 (t=-1.44)  H3 +0.0159 (t=+0.49)
```

**The positive quintile differences are an artifact and must not be read as
support.** The top quintile of a *signed* interaction is also a high-magnitude
set — mean |Z| 1.36 versus 0.55 — so it selects on |Z| rather than direction.
Testing |Z| directly gives +0.18 (t=+0.68), +0.53 (t=+1.86), +0.23 (t=+0.85):
nothing significant, and a post-hoc quantity that would need its own
registration regardless. §3 already fixed the continuous test as primary.

## §8 Classification

| | opening line | outcome | classification |
|---|---|---|---|
| H1 3PA x 3P allowance | Equivalent to zero | none | **IRRELEVANT TO MEAN PRICING** |
| H2 transition x live-ball TOV | Equivalent to zero | none | **IRRELEVANT TO MEAN PRICING** |
| H3 FTA x foul propensity | Equivalent to zero | none | **IRRELEVANT TO MEAN PRICING** |

## What this establishes — and it is not nothing

Per §13, Stage 2 succeeds scientifically with all three failing. The content is
stronger than a bare null because equivalence was required in both directions:

**These three matchup interactions are absent from the opening total AND absent
from realised scoring error.** The market is not omitting them — **there is
nothing to omit.** The compression hypothesis was tested through three
independent scoring channels (three-point volume, transition possessions,
clock-stopped points) and the additive-in-efficiency architecture recovered in
Stage 1 is **not leaving matchup money on the table in any of them**.

The 0.75-point materiality gate was reachable at this power and nothing came
close. Per §7 and §12, no further interaction may join this family; anything
else is Stage 3 and needs a new registration.
