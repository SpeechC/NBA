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
