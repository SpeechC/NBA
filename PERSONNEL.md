# Player-level impact: the personnel thesis, tested

Stint-level RAPM built, validated, and tested against the closing line. It does
not improve on team-level ratings, and — the decisive result — **look-ahead
knowledge of exactly who played is worth nothing over knowing who played
recently.** That prices the injury feed at approximately zero.

## The model works

Ridge-regularised RAPM on 512,630 stints, each contributing two observations
(one per offensive team), weighted by possessions:

    PPP100 ~ intercept + home + sum(off_i for i in O) + sum(def_j for j in D)

Face validity on 2022-24, players with 1,500+ minutes:

| top by off − def | | best defenders (most negative def) |
|---|---|---|
| Nikola Jokić +7.60 | | Draymond Green −5.79 |
| Draymond Green +7.29 | | Franz Wagner −4.89 |
| Joel Embiid +7.23 | | Brook Lopez −4.49 |
| Derrick White +6.88 | | OG Anunoby −4.49 |
| Shai Gilgeous-Alexander +6.44 | | Alex Caruso −4.28 |
| Giannis Antetokounmpo +6.32 | | Victor Wembanyama −3.95 |

Bottom: Jordan Nwora, James Wiseman, Doug McDermott. Jokić first is what every
public RAPM produces. The stint reconstruction carries real signal.

A sign trap worth recording: the target is points scored **by the offence**, so a
good defender has a **negative** coefficient. Total impact is `off − def`. Adding
them instead ranks Gobert, Wembanyama and Draymond Green among the league's worst
players, which is how the error announces itself.

## The test

Two projections through the same walk-forward harness as sets A/B/C, 108 RAPM
refits on a trailing two-season window:

  * **D — actual minutes.** Weighted by minutes actually played that night.
    **LOOK-AHEAD**; never a backtest result. It measures the ceiling: strictly
    better than anything a real-time feed could deliver.
  * **E — lagged minutes.** Weighted by minutes in recent games. Known before
    tip, honestly tradable, one game late to any absence.

### A flaw in the first run, and its correction

The first version gave D and E only the four RAPM features and **no pace** —
while the team-level baseline had it. Since a total is possessions × efficiency,
that handicapped them badly. Adding lagged pace was worth ~0.48 RMSE, and without
that correction the negative result would have been overstated.

| set | n | total RMSE | line RMSE | gap |
|---|---|---|---|---|
| D RAPM actual minutes | 4,635 | 19.669 | 17.975 | +1.693 |
| **D RAPM actual + pace** | 4,316 | **19.195** | 17.930 | **+1.265** |
| E RAPM lagged minutes | 3,816 | 19.734 | 17.979 | +1.755 |
| **E RAPM lagged + pace** | 3,706 | **19.255** | 17.991 | **+1.264** |
| A team-level baseline | 4,995 | 19.232 | 18.046 | +1.186 |

(Sample sizes differ, so `gap` — RMSE relative to the closing line on the same
games — is the comparable column.)

## What it says

**RAPM adds nothing over team-level lagged ratings.** Gap +1.265 against the
baseline's +1.186. Player-level impact estimation, done properly and validated,
lands exactly where a lagged team average lands.

**Perfect personnel knowledge is worth nothing.** D and E are indistinguishable:
gap **+1.265 vs +1.264**. Knowing precisely who played and for how many minutes
buys no accuracy over knowing who played in recent games. Since D is strictly
better than any live injury feed could be — a feed tells you who is expected to
play, D knows who did — **the feed cannot rescue this approach.** That was the
question the D/E split was built to answer, and it answers it cleanly.

**Do not buy the injury data.** The recommendation from several turns ago —
that personnel was the remaining lever and a live availability feed the natural
purchase — is withdrawn on this evidence.

## Why

The market prices personnel immediately and accurately; a star's absence is the
most public information in the sport. Our RAPM projection is not a better
personnel model than the one already embedded in the opening total, and
team-level lagged ratings absorb most of what is knowable anyway — a team that
lost a star scores less in its recent games, which a lag-4 average already sees.

This closes the pbp thesis. Possession reconstruction validated (corr 0.99 with
the vendor box score), garbage-time flagging validated and worthless, lineup
extraction validated (100% 5/5) and worthless. Three well-motivated hypotheses,
each tested once and reported regardless of outcome.

The only signal in this project remains totals **line movement**: CLV +0.588
overall, +1.357 selective, positive in five of five seasons, against a ~1.35-point
break-even at −110 — real, and about half the magnitude needed at standard juice.
