# 2P / 3P CONVERSION STABILITY, AND THE HOME-ROAD QUESTION (2026-08-31)

3P conversion (38.7%) and 2P conversion (29.3%) together are **68.0%** of the team
margin-error contribution variance (`MONEYLINE_SOURCE_ATTRIBUTION.md`). This asks
how stable those rates actually are — overall, by venue, and team by team.

Method throughout: **observed cross-team dispersion against the binomial noise
floor.** A team-season carries ~2,800 2PA and ~1,760 3PA, so sampling error is
large enough that raw dispersion badly overstates real differences.

n = 19,352 team-games, 8 seasons, regular season only.

## League baselines

```
3P%  0.3603   34.3 attempts per team-game
2P%  0.5348   54.1 attempts per team-game
```

## Team-season reliability — 2P is a much firmer property than 3P

| split | obs sd | binomial sd | TRUE sd | reliability |
|---|---|---|---|---|
| **3P% all games** | 0.0152 | 0.0092 | 0.0121 | **0.635** |
| **2P% all games** | 0.0238 | 0.0076 | 0.0226 | **0.899** |
| 3P% home only | 0.0181 | 0.0130 | 0.0126 | 0.483 |
| 3P% road only | 0.0175 | 0.0130 | 0.0117 | 0.446 |
| 2P% home only | 0.0246 | 0.0107 | 0.0221 | 0.809 |
| 2P% road only | 0.0256 | 0.0107 | 0.0233 | 0.826 |

Roughly **90% of observed 2P% spread is real; only ~64% of 3P% spread is.** This
is the season-level counterpart of the 20-game block result (2P EB weight 0.3157
vs 3P **0.0000**) and explains it.

## THE HOME-ROAD QUESTION — a league constant, not a team property

The home shooting boost is real and sizeable:

```
3P%  home 0.3632  road 0.3572   +0.61pp
2P%  home 0.5401  road 0.5310   +0.91pp
```

**But it does not vary by team beyond noise.**

| differential | mean | obs sd | binomial sd | TRUE sd | reliability |
|---|---|---|---|---|---|
| 3P home − road | +0.0061 | 0.0183 | **0.0184** | **0.0000** | **0.000** |
| 2P home − road | +0.0091 | 0.0160 | 0.0152 | 0.0052 | 0.106 |

For 3P the observed spread is **smaller than the binomial floor** — there is no
team-specific home three-point effect at all. For 2P there is a trace (0.106).

And it does not persist:

```
year-to-year correlation, 180 team-season pairs
  3P home-road DIFFERENTIAL   +0.0409
  2P home-road DIFFERENTIAL   -0.0011
```

**No team is reliably better at home than the league average is.** "This team
shoots well at home" is a real league effect misattributed to a specific club.

## Team-by-year 2P stability — and a trend that must be removed first

The league 2P% rose steadily as midrange attempts were eliminated:

```
2017 0.5103  2018 0.5195  2020 0.5303  2021 0.5326
2022 0.5479  2023 0.5453  2024 0.5452  2025 0.5501      +3.98pp over the span
```

Almost every team rises with it, so raw year-to-year correlation is inflated by a
common trend. De-trended against the league in the same season:

| | raw | DE-TRENDED |
|---|---|---|
| 2P% year-to-year | +0.5929 | **+0.4909** |
| 3P% year-to-year | +0.4083 | **+0.4684** |

The trend **inflates** 2P persistence and **suppresses** 3P persistence — 3P% has
been roughly flat league-wide while attempt volume rose, so the common component is
smaller there.

De-trended within-team movement:

```
within-team sd across seasons  1.68pp
binomial noise floor           0.76pp
TRUE year-to-year drift        1.50pp per season
```

Cross-team reliability of de-trended within-season rates: **2P 0.849, 3P 0.606**.

Full team x season 2P% table is reproducible from `shoot.py`; the spread across
teams within a season is ~2.0pp and a team moves ~1.5pp per year for real.

## What this means for the wagering question

It **explains** the earlier results rather than reopening them.

2P conversion is a genuine, persistent, ~85%-reliable team property that drifts
~1.5pp a year. That is exactly why it carried a non-zero block-level EB weight
(0.3157) when 3P carried none. But a property this legible is not private
information: the frozen state engine already tracks it with an 8.6-game half-life,
and the prospective test against the **book's** error was null
(t = +0.17 on margin, −0.50 on the moneyline).

The home-road result is a **new null of record**: there is no team-specific
home-court shooting effect to condition on. The league effect (+0.91pp 2P,
+0.61pp 3P) is already in every team's overall rate and in the market's home-court
adjustment.

**No change proposed to any frozen component.**

---

# GATE P1 — IS 2P SHOCK PERSISTENCE HETEROGENEOUS BY TEAM? (2026-08-31)

The level results above say nothing about the **transition law**. Two teams both
projecting 54% from two could differ in how much a +5pp run carries forward: a
genuine temporary state for one, pure realization for the other. A single
league-wide filter treats them alike. **That is the untested object — `rho_i`, not
`mu_i`.**

Gating, pre-stated: (1) does true heterogeneity survive shrinkage; (2) can it be
estimated prospectively and does it improve 2P forecasting; (3) only then, does
the book miss it. **If 1 or 2 fails, close without looking at moneyline ROI.**

## Construction

2P surprise `s = 2P%_actual − forecast`, where the forecast is a **prior-only
two-way** state (league + own offence + opponent interior defence, 15-game
half-life, 0.42 offseason carry). n = 19,352 team-games; forecast RMSE 0.0700.

`rho_i` is the within-team-season AR(1) coefficient of `s`.

## Result — heterogeneity is at the noise floor

```
pooled game-level rho        +0.0148   se 0.0072   t +2.05
observed sd of rho_hat        0.1165
sampling-noise sd             0.1129
TRUE sd (EB)                  0.0287    reliability 0.0608
|t| > 2 team-seasons          13 of 240   (chance expectation ~12)
rho_hat range  min -0.295  median -0.006  max +0.324
```

Observed dispersion barely exceeds the noise floor, and the count of "significant"
team-seasons matches chance exactly.

## And the trace cannot be estimated prospectively

Tested on the horizon specified — current state, not franchise identity:

| | correlation |
|---|---|
| H1 -> H2 within season | +0.0688 |
| ~20-game quarters, pooled consecutive | **+0.0053** |
| q1->q2 / q2->q3 / q3->q4 | −0.0731 / +0.0123 / +0.0959 |
| season to season | −0.0096 |

The half-season `rho` estimate has **reliability 0.0066** — 99.3% noise at that
sample size. At the 20-game horizon, consecutive-block persistence-of-persistence
is **+0.005**.

## Economic magnitude, had it been real

```
2sd spread in rho, applied to a large 5pp 2P surprise:
  0.287pp of next-game 2P%  =  0.310 points of margin
frozen bet threshold: 4.77 points
```

**6.5% of the threshold at two standard deviations.**

## Why this is consistent with the earlier block result

The 20-game block analysis found 2P with EB weight 0.3157 and next-block
r = +0.1799, which looks like it contradicts a game-level `rho` of 0.015. It does
not. A 20-game mean averages away most of the per-game sampling noise and exposes
the **slow drift in the level**; the game-to-game **shock** barely persists at all.

**The persistence lives in the level, which the state engine already tracks at an
8.6-game half-life — not in the shock, where a team-specific correction would have
to operate.**

## Verdict

**Gate P1 fails. Gates 2 and 3 were not run**, per the pre-stated rule: no 2P
forecasting model, no `beta_2P x rho` interaction, no moneyline ROI. Heterogeneity
is 6% reliable, unidentifiable at any usable horizon, and worth 0.31 points at
2sd if it were real.
