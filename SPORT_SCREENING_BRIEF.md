# Cross-Sport Market Screening — project brief

**Drop this into the new project as `CLAUDE.md` or alongside it. It is
self-contained: it assumes no knowledge of the NBA project it came from.**

Take `screen_market.py` with you. It implements Stage 1 and runs on any sport.

---

## 1. Objective

Find sport × market cells where the closing line is **biased enough to beat the
vig**, and rank them by how fast that bias can be confirmed.

This is a **market-selection** project, not a modelling project. The prior
project spent months building models for one market and the single most valuable
number it produced was that moving from −110 to −105 was worth more than every
predictive feature discovered across twenty-one feature families combined.
**Where you bet dominates how well you predict.** Screen first; model only in a
market the screen says is worth modelling.

---

## 2. The decision rule

For each sport × market, from a line history:

```
resid  = actual − line          (actual = total points, or margin + spread)
b      = mean(resid)            the bias
σ      = sd(resid)              the noise
```

The market is beatable **only** if the empirical win rate of the better side
exceeds the break-even rate implied by the price:

| price | break-even | notes |
|---|---|---|
| −110 | 52.38% | standard US sides/totals |
| −105 | 51.22% | reduced juice |
| −102 | 50.50% | exchange, after commission |
| dime line (MLB/NHL ML) | ~50.5–51% | varies with favourite price |

**Rank on `edge_pp` = best_side_% − break_even_%.** Positive is a candidate;
anything ≤ 0 is dead at that price.

### ⚠ Do not rank on b/σ

An earlier version of this rule compared `b/σ` against `z_vig = Φ⁻¹(break-even)`
and called a market beatable when the ratio exceeded 1.0. **That rule is wrong
and will produce false positives.** A binary bet depends on probability mass
*near the line*, not on the mean. Fat tails — blowouts that were already going
over — inflate `b` without moving a single game across the number.

Measured on NBA totals: `b/σ ÷ z_vig` at −102 reads **2.28**, implying a
comfortable edge. The empirical best side is **50.38%** against a 50.50%
break-even — no edge at all. `screen_market.py` reports both and labels which to
believe. Keep `b/σ` as a diagnostic for cross-sport comparison; never as the
decision.

### Detection time is a hard constraint

Games needed to detect a bias of the observed size at 80% power:

```
n_required = 7.84 / (b/σ)²
```

Because both terms scale with the sport, this is sport-independent: **a bias
exactly at the −110 break-even size needs ~2,200 games to establish.** Half that
size needs ~8,800.

| sport | games/season | seasons to confirm a break-even-size bias |
|---|---|---|
| **College basketball** (D-I) | ~5,500 | **0.4** |
| **MLB** | 2,430 | **0.9** |
| Soccer (top-5 European) | ~1,750 | 1.3 |
| NHL | 1,312 | 1.7 |
| NBA | 1,230 | 1.8 |
| College football | ~800 | 2.8 |
| NFL | 272 | **8.1** |

**This must be read against decay.** In the prior project a genuine +3.0-point
bias in mismatch games ran for six seasons and then vanished. A market needing
eight seasons to confirm an edge cannot confirm one before it dies. **NFL is
structurally unscreenable on this basis** despite being the most popular market.

---

## 3. What makes a sport attractive

In priority order.

**1. Volume.** Drives everything. It is the only lever that shortens detection
time, and detection time is what decides whether an edge is confirmable before
it decays. This alone puts college basketball first.

**2. Price.** The vig is the denominator and it varies more across sports than
bias does. MLB and NHL moneylines quote dime lines — roughly 2% hold against
4.5% for −110 — which cuts the required edge by a factor of 4–5. Screen every
market at the price **you can actually get**, not at −110 by convention.

**3. Attention asymmetry.** Bias survives where modelling attention is thin.
Look for: lower divisions, women's competitions, secondary markets (first half,
team totals, alternate lines), early-season games, and leagues where the book is
pricing off a generic model rather than a bespoke one.

**4. Low σ relative to bias.** Helpful, but do not screen on it directly — it is
already inside `edge_pp`. Note the ambiguity that caused confusion in the prior
project: *irreducible outcome variance* being high is bad for you (it dilutes any
bias), while *market model error* being high is good (it is the bias). They are
different quantities that both get called "low accuracy."

**5. Data availability.** A market you cannot get five years of closing lines for
cannot be screened, however attractive in theory.

### The structural tension

**Bias and liquidity are inversely related.** Markets with surviving
inefficiency are thin — low limits, wide prices, and your own bet moves them.
Markets deep enough to absorb real money have been modelled by everyone. The
screen will surface edges you cannot fund. Record the **limit** alongside the
edge, and treat `edge_pp × available_limit` as the real ranking, not `edge_pp`.

---

## 4. Traps that will fool you

Every one of these cost real time in the prior project.

**Pooled figures hide decay.** Always plot bias **by season**. The mismatch edge
was six good seasons then two dead ones; pooled over ten years it looks robust.
A candidate is only interesting if the by-season plot is stable *and the recent
seasons are still positive*.

**Search methods manufacture significance.** A depth-3 regression tree on 29
features found a leaf with a +2.27 point bias on 2,160 games at **t = 5.86**
(p < 1e-8). Refitting the same tree on 400 *shuffled* targets produced a larger
leaf bias 62% of the time — the observed result sat at the **38th percentile of
its own null**. Out of sample the strongest leaves reversed, correlation −0.46.
**Any search-based method needs a permutation null built in from the start.** A
tree's best leaf is an extreme order statistic, not a hypothesis test.

**Multiplicity across cells.** 20 sports × 3 markets = 60 tests; ~3 clear
p < 0.05 on noise. Use Benjamini-Hochberg across the whole screen. In the prior
project, testing 30 teams individually produced exactly 1 nominal hit against
~1.5 expected — and 0 survived correction.

**Rare conditions are untestable.** A filter firing on 0.3% of games yields ~4
games/season; eight seasons gave n=29 and a confidence interval 36 points wide.
Prefer conditions that fire on **5–10%** of games. The one real edge found fired
on ~11%.

**Predicting line movement is not profit.** The prior project could predict the
direction of the open-to-close move ~60–70% of the time and earned +1.9 points
of CLV — with **no win rate**, because the move being predicted *is the market
correcting itself*. Front-running a correction that happens anyway produces CLV
and no money. **Screen against the CLOSE.** If you screen against the opener,
you are measuring how beatable the opener is, which is a different and much less
valuable question.

**Confidence ranking can fail even when direction works.** In the prior project,
development win rate rose monotonically with model confidence (50.0% → 55.4%),
while in holdout it peaked early and *reversed* (54.4% → 50.1%). Direction calls
survived out of sample; the ranking did not. If you build a model, validate the
ranking separately from the direction.

**Persistence is a cheap pre-filter.** Before modelling anything, check whether
the candidate effect predicts *itself* from one period to the next. Team-level
line movement looked real cross-sectionally (95th percentile of its permutation
null) but had a year-over-year correlation of **−0.013**, swinging from −0.44 to
+0.30. If an effect cannot predict itself, it cannot predict anything. This test
costs one line of code and would have killed several ideas faster than modelling
did.

---

## 5. Protocol

**Stage 0 — acquire.** For each sport, get ≥5 seasons of: date, teams, closing
line (total and spread), final score. That is the whole requirement.

**Stage 1 — screen.** Run `screen_market.py` on every sport × market × price.
Output the ranked table plus a by-season bias plot for each cell. Cheap, fast,
no modelling. Most cells die here.

**Stage 2 — conditional bias.** For surviving cells only, test pre-registered
conditional filters (large spreads, extreme totals, rest, travel, scheduling
spots). Permutation-controlled. Pre-register the filter list **before** looking.

**Stage 3 — decay check.** Plot the candidate's bias by season. Reject anything
whose recent two seasons are flat, regardless of pooled significance.

**Stage 4 — holdout.** Hold out the most recent full season in every market,
untouched through Stages 1–3. Write the pass/fail criteria down before looking
at it.

**Only then** consider building a model — and only for the specific market and
condition that survived.

---

## 6. Data sources (verify before relying on any of these)

**Historical line archives**
- `sportsbookreviewsonline.com` — free per-season spreadsheets with open/close
  spread and total plus scores, for NBA/NFL/MLB/NHL/NCAAB. Closest to the
  required schema.
- OddsPortal — broad league coverage including lower-tier soccer.
- Covers.com, SportsDatabase (SDQL) — free query interfaces.
- Kaggle / GitHub — many scraped datasets, variable quality.

**Package-based (highest quality)**
- `nflfastR` (R) — `spread_line`, `total_line` back to 1999. Clean, but NFL's
  272 games/season makes it the worst screening target.
- `hockeyR`, `pybaseball`, Retrosheet — free scores/schedules; join lines
  separately.

**Live pricing**
- The Odds API free tier (~500 requests/month) — enough to sample current prices
  across books, which is how you populate the *price* column honestly rather
  than assuming −110.

⚠ Free sports-data sources churn. Verify each is live before planning around it.

---

## 7. Calibration anchors from the prior project

Use these to recognise what null and non-null look like.

| quantity | value |
|---|---|
| NBA totals bias vs close | +0.515 pts on σ 18.16, t = 2.74 |
| …as a win rate | best side 50.38% vs 52.38% break-even → **no edge** |
| NBA sides bias | −0.167, t = −1.19 → **no bias at all** |
| a *real* conditional edge (since decayed) | +3.0 pts, 55.8% overs, 6 seasons |
| feature families tested, all null | 21 |
| best model R² on game totals | ~7.6% |
| value of −110 → −105 | +1.16pp win rate |

**The market is not unbiased — it is biased by about half a point, repeatably.
The vig band is simply wider than the bias.** That is the correct mental model,
and it means the screen's question is never "is there bias" but "is the bias
bigger than the price."

---

## 8. Deliverables

1. `screen_market.py` pointed at every sport acquired, with a committed ranked
   table and per-season bias plots.
2. A short `FINDINGS.md` recording every cell tested — **including the nulls**,
   with their numbers. Nulls are the majority of the value and are what stop the
   same ground being re-covered.
3. A pre-registration for any cell advancing to Stage 4, written before the
   holdout is touched.
4. An explicit recommendation: which market, at which price, with which limit,
   and what the expected edge and its confidence interval are.

## 9. Stopping rules

- No cell clears `edge_pp > 0` at an obtainable price → **report that and stop.**
  It is a legitimate and valuable result.
- A cell clears but needs > 4 seasons to confirm → deprioritise; decay will
  likely beat you.
- A cell clears but limits are too small to matter → record it and move on.

**Do not start modelling to rescue a market the screen rejected.** That is what
the prior project did for months, and the screen would have said no in an
afternoon.
