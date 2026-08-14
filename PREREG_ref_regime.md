# Pre-registration: league foul regime vs referee identity shock

**Written before any outcome was examined.** Supersedes the CrewFoul signal used
in Test 1 and `ref_shock.py`, which had two defects found by the permutation:

1. **Horizon mismatch.** A referee estimate accumulated over an entire career
   was demeaned against a trailing 500-game league level. That mismatch let
   temporal drift back into the signal.
2. **Sample-dependent features.** `CrewFoul` was recomputed on whatever rows
   survived control filtering, so missing controls could change the feature
   itself.

The permutation also showed a null mean of +0.405 rather than zero, indicating
the signal was partly carrying a league-wide foul climate rather than referee
identity. That is not a nuisance to remove. It is a second, economically
distinct hypothesis, and both are estimated here simultaneously.

```
total error  =  league foul regime effect  +  referee identity effect  +  eps
```

## Feature construction — built ONCE on the complete universe

Every referee state is computed on all regular-season games that have officials
and foul data, strictly prior-only, written to `ref_features.csv`, and only then
merged into whatever regression sample the controls permit. Analysis-sample
filtering can never touch feature estimation.

### Referee identity, matched horizons

```
N = 60                         an official's last 60 games, roughly 1.3 seasons
ref_mean(r,t)   = mean pf_rate over r's last N games before t   (min 25)
span(r,t)       = [date of the oldest game in that window,
                   date of r's previous game]
lg_matched(r,t) = mean pf_rate over ALL league games in that same span
RefEffect(r,t)  = (ref_mean - lg_matched) * n / (n + k)
CrewShock_t     = sum of RefEffect over the three officials
```

The league term is measured over the *identical calendar period* as the referee
term, so both see the same foul climate and the difference is identity only.
`k` is the empirical-Bayes constant from develop, frozen.

### League foul regime

```
LeagueFoulState_t = (trailing 200-game league mean pf_rate)
                  - (trailing 1230-game league mean pf_rate)
```

Both prior-only. Positive means the league is currently being called more
tightly than its own recent norm.

## The three primary tests

**1. Continuous coefficient gap, both states at once**

```
closing total ~ a + cm_L*LeagueFoulState + cm_C*CrewShock + X'b
actual  total ~ a + ca_L*LeagueFoulState + ca_C*CrewShock + X'b
H0: ca_C - cm_C = 0      and      ca_L - cm_L = 0
```

X is the same 11 prior-only team controls as `ref_shock.py`.

**2. Time-local crew permutation.** Crews are randomized within disjoint 7-day
blocks inside a season, so the league foul climate is held fixed while referee
identity is randomized. Season-wide permutation is the wrong null: it mixes
January crews with April foul environments and manufactures the very temporal
component being separated out. **The null mean of the CrewShock gap must come
back near zero** — that is the check that the test measures what it claims.

The crew permutation leaves `LeagueFoulState` untouched, so it is not a valid
null for the league coefficient. That one gets a moving-block bootstrap over
calendar time instead, to respect serial correlation.

**3. Frozen extreme regime.** `CrewShock >= develop Q85` is primary; Q90 is
reported as secondary. Declared here because the earlier decile inspection was
exploratory: the top-decile p=0.018 in `ref_shock.py` came from looking at the
bucket shape first, so it motivates this threshold rather than establishing
anything.

Season-by-season coefficients are **diagnostics, not hypothesis tests**.

## Success criteria

1. permutation null mean for the CrewShock gap is near zero (construction valid)
2. `ca_C - cm_C > 0` with time-local permutation p < 0.05
3. same sign in develop and holdout
4. frozen Q85 regime holdout over rate clears 52.38%

The league coefficient is reported alongside on equal footing. A result where
the league regime is mispriced and referee identity is not — or the reverse —
is as informative as both being mispriced, and the point of running them
together is that the previous design could not tell them apart.
