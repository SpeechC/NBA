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
