# SORTING TOTALS BY ABSOLUTE ERROR, AND THE ONE SIGNED POCKET (2026-09-13)

Two questions, answered in P&L terms. Regular season, n = 9,405, actual per-game juice,
$100 flat.

---

## 1. CAN WE SORT TOTALS BY ABSOLUTE ERROR? Yes — and it does tilt to high totals

Absolute error in **points**, not percent, as specified.

```
|dev| ~ closing total :  +0.0237 pts of error per point of total   t +2.09
dev^2 ~ closing total :  beta +1.358                               t +2.61
across the observed range (190 to 262) that is 1.72 points of MAD
```

| decile of closing total | n | mean close | **MAD** | sd(dev) |
|---|---|---|---|---|
| D1 | 972 | 206.1 | 14.099 | 17.608 |
| D2 | 939 | 213.7 | 13.965 | 17.695 |
| D3 | 1039 | 217.5 | **13.645** | 17.019 |
| D5 | 908 | 223.5 | 14.386 | 18.183 |
| D6 | 896 | 226.0 | 14.747 | 18.981 |
| D8 | 990 | 231.4 | 14.338 | 17.957 |
| D10 | 871 | 241.5 | **14.766** | 19.024 |

Bottom two deciles MAD **14.033** vs top two **14.592** — a **0.558-point spread, 4.0%
relative.** The Poisson/counting expectation for that range is 6.5%, so the observed
scaling is **slightly LESS than mechanical**: high totals are less accurately priced in
absolute points purely because there are more points to be wrong about, and the game
adds nothing on top of the counting.

**The closing total is not the best sorter — the pace forecast is:**

| sorter | bottom-10% MAD | top-10% MAD | **spread** | corr with \|dev\| |
|---|---|---|---|---|
| **prior-only pace forecast** | 14.210 | **15.187** | **0.977** | 0.0305 |
| close + pace | 14.105 | 15.041 | 0.937 | 0.0273 |
| closing total | 14.099 | 14.766 | 0.667 | 0.0216 |
| \|move\| | 14.345 | 14.442 | 0.097 | 0.0024 |
| \|spread\| | 14.869 | 14.487 | −0.382 | 0.0006 |

Pace beats the line as a width sorter — expected possessions, not expected points, is
what governs how wrong the number can be. Spread magnitude sorts **backwards**.

### What the sort is worth, and where

```
                        MAD    sd     P(|dev|>10)  P(|dev|>20)  P(|dev|>30)
lowest-decile total   14.10  17.61      0.569        0.245        0.078
highest-decile total  14.77  19.02      0.563        0.268        0.108
```

**On a two-way total at -110 the sort earns exactly nothing** — both sides pay the same
whatever the width. And note the near rung is useless: `P(|dev|>10)` is **0.569 vs
0.563**, i.e. identical and slightly backwards, so a ±10 alternate total is not
differentially mispriced at all.

**The value is entirely in the far tail.** `P(|dev|>30)` runs **0.078 vs 0.108 — a 38%
relative difference** that a single league-wide quote cannot serve. That is the only
product this sort pays on: deep alternate totals and the outer Kalshi rungs, where the
price is a function of the width. It is a **variance product, not an over/under**.

---

## 2. THE SIGNED POCKET — late season goes OVER

Sweeping 58 pregame strata for a **directional** bias (the sign of the error, which is
worth more than the magnitude), one survives multiplicity:

```
permutation on the max |t| across all 58 strata, outcomes shuffled within season:
   shuffled max |t|  mean 2.23   95th 2.94   99th 3.34
   observed          3.50 (April)          ->  p = 0.0047   SURVIVES
```

Betting OVER, by window, at actual juice:

| window | n | hit | break-even | **P&L** | ROI | z | winning seasons |
|---|---|---|---|---|---|---|---|
| **last 7 days of season** | 407 | **56.51%** | 52.42% | **+$3,157** | +7.76% | +1.65 | **5/6** |
| last 14 days | 730 | 54.66% | 52.46% | +$3,033 | +4.15% | +1.19 | 4/6 |
| last 21 days | 1,046 | 53.44% | 52.46% | +$1,923 | +1.84% | +0.63 | 3/6 |
| last 30 days | 1,461 | 53.18% | 52.47% | +$1,971 | +1.35% | +0.55 | 5/6 |

Mean dev in the last 21 days is **+1.899 pts** against +0.532 overall.

### A confound I had to remove, and what it exposed

Calendar April is the last two weeks of the season in **seven of eight** years — but the
2020-21 COVID season ran Dec 22 to May 16, so its April games sit **16-45 days from the
end**. That single season is why the calendar and season-relative versions disagree:

```
April, excluding the COVID season : n=468  57.69%  ROI  +9.97%  z +2.28
April 2021 only (mid-season)      : n=239  49.79%  ROI  -5.37%  z -0.87
late season but NOT April         : n=530  50.19%  ROI  -4.35%  z -1.06
```

The effect concentrates in the **final week**, and the days-14-to-21 window loses. So it
is a genuine end-of-season effect, not a calendar artefact — but it is also narrower
than it first looked.

### Why I would not size this yet

1. **It is not significant.** Best z is +1.65 (last 7 days) and +2.28 (April
   ex-COVID, a post-hoc exclusion). The multiplicity permutation passes on the **mean**
   (p=0.0047) and the hit rate does not follow it.
2. **The mean does not convert.** A +2.7-pt mean shift should give 55.97%; realised is
   54.47%, a **1.50pp shortfall**. The bias sits in the tail — blowouts overshooting —
   and a two-way bet cannot collect a tail.
3. **The prize is small.** Last-7-days is ~51 bets a season for **~$395/season at $100
   flat.** At $1,000 a bet that is ~$4k a season on 51 bets, with a z of 1.65.
4. **The wider stratification search failed forward.** Taking the six rules that looked
   best on 2017-2022 and trading them on 2022-2026 lost **−$28,820**. Only one of six
   was even flat. That is the base rate for this kind of search and it is the reason to
   distrust any single survivor.

**Mechanism, untested:** end-of-season rotations — rested starters, deeper benches,
reduced defensive intensity, more garbage time. It predicts more points and it predicts
the effect concentrating in the last week, both of which match. It also predicts the
effect should be stronger for **eliminated** teams, which is testable from the standings
and is the obvious next step: if the over-bias is carried by games with at least one
eliminated team, that is a real mechanism with a pregame-observable trigger. If it is
uniform across playoff-relevance, it is probably noise.

---

## SCORECARD

| question | answer |
|---|---|
| Can we sort totals by absolute error? | **Yes.** ~1 pt of MAD between extreme deciles |
| Does it tilt to high totals? | **Yes** — and pace forecasts it better than the line |
| Is it more than mechanical? | **No** — 4.0% observed vs 6.5% Poisson |
| Is the sort tradeable on an O/U? | **No** — the price does not depend on the width |
| Where is it tradeable? | Far rungs only: P(\|dev\|>30) = 7.8% vs 10.8% |
| Is there a signed pocket? | **One** — last week of the season, OVER |
| Its P&L? | **+$3,157 on 407 bets, 5/6 seasons, z +1.65** — not significant |
