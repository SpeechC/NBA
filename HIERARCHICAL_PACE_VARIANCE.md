# ARE SOME TEAMS INTRINSICALLY MORE PACE-PREDICTABLE? — YES

The question had not been tested properly. Rolling-window SDs are too noisy to
answer it; a hierarchical model with shrunk team effects is the right instrument.
`hierarchical_pace_variance.py`.

## Model

```
u_t  = PaceActual - Pace_hat - mu_drift_hat            (drift already removed)
u2   ~ alpha + (v_homeTeam + v_roadTeam)/2 + b1*ExpectedPace + b2*Rest
              + b3*SeasonStage + b4*RosterInstability

v_i  : EMPIRICAL-BAYES shrunk team variance effects
       raw s_i^2 = mean(u^2) over team i;  sampling var ~ 2*sigmabar^4/n_i
       tau^2 by method of moments;  w_i = tau^2/(tau^2 + 2*sigmabar^4/n_i)
       v_i = w_i*s_i^2 + (1-w_i)*grand mean
```

**Team effects are estimated from PRIOR SEASONS ONLY**, then applied forward.

## RESULT — it separates, monotonically, prospectively

| predicted-variance quintile | n | predicted sd | **ACTUAL sd(u)** | ±noise |
|---|---|---|---|---|
| 1 | 415 | 3.021 | **3.898** | 0.135 |
| 2 | 414 | 3.590 | 3.950 | 0.137 |
| 3 | 415 | 3.901 | 3.972 | 0.138 |
| 4 | 414 | 4.155 | 4.191 | 0.146 |
| 5 | 415 | 4.522 | **4.456** | 0.155 |

```
Q1 3.898 -> Q5 4.456   ratio 1.1434   F-test p=0.0065   SEPARATES
Spearman(predicted rank, actual sd) = +1.000   PERFECTLY MONOTONE
in total-points space: 8.98 -> 10.27 pts   difference +1.29
```

**This is the clean answer.** Their benchmark was Q1≈3.5 / Q5≈4.5 (ratio 1.286);
we get 3.90 / 4.46 (ratio 1.143) — about half the hoped-for spread, but real,
monotone and significant.

## Why this worked when three earlier attempts failed

```
raw team sd range      3.37 - 4.56   (spread 1.18)
SHRUNK team sd range   3.72 - 4.19   (spread 0.48)
mean shrinkage weight 0.405  ->  60% of each team estimate is pulled to the mean
```

**Most of the raw between-team spread is sampling noise** — shrinkage removes 59%
of it. Rolling-window SDs and the earlier `sigma_P` model used the unshrunk
quantity and were swamped. `tau^2` is 2.35-2.56, so the between-team component is
genuinely non-zero.

```
tightest: Milwaukee 3.72   Cleveland 3.73   Oklahoma City 3.74
loosest : Boston 4.12      Houston 4.17     Toronto 4.19
```

Plausible basketball: structured half-court teams tight, looser transition teams
wide. **Their intuition about rigid tactical style was directionally right.**

## BUT IT STILL HAS NO DECISION VALUE — and the pattern is diagnostic

Testing whether this better `sigma` modulates the pace-gap betting signal
(n = 1,034; the hierarchical `sigma` needs prior-season team effects, so only
2024-25 is evaluable):

```
gap            +0.3005 (t=+2.15)
sigma (z)      -0.0360 (t=-0.06)
gap x sigma    +0.2219 (t=+1.52)      one-sided p(<0) = 0.9362   MDE 0.3622

signal within sigma terciles:
  tight  n=345   beta 0.0541 (t=0.24)   hit 53.6%
  mid    n=344   beta 0.2192 (t=0.91)   hit 52.9%
  loose  n=345   beta 0.6545 (t=2.51)   hit 56.5%
```

**The interaction is POSITIVE — the signal looks STRONGER where pace is less
predictable, the opposite of the hypothesis.**

**This is now the second interaction test, and the two have OPPOSITE SIGNS:**

```
volx (PACE_INTERACTION)          beta -0.0429 (t=-0.47)
hierarchical sigma (here)        beta +0.2219 (t=+1.52)
```

**Neither is significant, and they disagree in direction. That is the signature
of no real modulation**, not of an effect we keep mis-measuring. The `loose`
tercile at 56.5% on n=345 is the kind of cell that has repeatedly failed in this
programme, and it now sits on the *opposite* side of the hypothesis that
generated it.

## Settled position on this branch

| claim | verdict |
|---|---|
| All teams/matchups are equally pace-uncertain | **FALSE** — rejected at p=0.0065, monotone across five quintiles |
| Team pace-predictability persists across seasons | **TRUE** — r = +0.246 against a 0.382 noise ceiling (64% of maximum) |
| We can identify high/low-uncertainty matchups pregame | **YES** — 8.98 vs 10.27 points of total uncertainty |
| The spread is large | **NO** — 0.48 possessions between extreme shrunk teams; 60% of raw spread is noise |
| It should change a bet | **NO** — two interaction tests, opposite signs, neither significant |

**The prereg amendment stands**: uncertainty constructs remain diagnostics, not
decision variables. But the earlier wording that treated the underlying
heterogeneity as disproven was wrong. **The heterogeneity is real, persistent,
identifiable, and small.**
