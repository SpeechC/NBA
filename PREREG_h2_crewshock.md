# Pre-registration: does the second-half total price CrewShock?

**Written after a coverage and construction audit, before any outcome was
examined.** `CrewShock`, `LeagueFoulState`, the N=60 estimator and the +0.8682
threshold are frozen and are not rebuilt, retuned or re-thresholded.

## Why this market

Two facts already established make the 2H total the natural next venue.

1. **The fouls are in the second half.** H2 carries 21.55 fouls against H1's
   18.44 (53.9% share) and 24.05 FTA against 19.99 (54.6%). More than half of
   the CrewShock foul channel lands after halftime.
2. **The 2H line is set by a rule with no referee term.** `bench_priced.py`
   established `2H ≈ 4.62 + 0.4925*pregame_total - 0.0330*H1_total`, R² = 0.78.
   The audit confirms the book is close to `pregame_total - realized_H1`
   (mean difference −0.090). A mechanical transformation that discards a
   knowable variable is the SPORT_SCREENING_BRIEF template.

The full-game close incorporates 4.6% of CrewShock. A formulaic derivative,
posted quickly and traded thinner, is unlikely to do better.

## Audited coverage — stated before the test, not after

```
                 games  2H line   PBP    USABLE
2017-18           1230    80.3%  100%     80.3%
2018-19           1230    81.1%  100%     81.1%
2020-21           1080     0.0%  100%      0.0%   <- no 2H lines at all
2021-22           1230     9.4%  100%      9.4%
2022-23           1230    64.6%  100%     64.6%
2023-24           1162    52.6%  99.8%    52.5%
2024-25           1166    50.3%  100%     50.3%
2025-26           1161    25.1%    0%      0.0%   <- no play-by-play

usable 4,093    development 3,506    SEALED HOLDOUT 2024-25 only, 587 games
```

Two seasons are effectively absent from development and 2025-26 cannot be used
at all. The sealed holdout is **one season, 587 games**. This is stated in
advance so the result is not later described as more validated than it is.

## The market's standing bias — the economic bar

```
2H over rate, all usable games      46.54%   (push 1.76%)
mean residual (actual H2 - line)    -0.607
non-OT games only                   47.07%,  -0.500   (so NOT an OT artifact)

by season:  -1.09  -0.79  (+0.44)  -0.25  -0.64  -0.12
over %:     43.62  46.24   51.72   49.43  46.89  46.68
```

The book subtracts realized H1 from a full-game number, but H2 scores less than
H1 (109.87 vs 112.45), leaving a persistent under lean that has shrunk over
time. **Any OVER strategy on this market starts roughly 5.7pp below the 52.38%
break-even.** The primary test is therefore the pricing coefficient, not an
over-rate strategy, and no economic claim will be made unless the coefficient
survives first.

## Primary hypothesis

```
H2Residual = actual H2 points - posted 2H line

H2Residual = a + bR*CrewShock + bL*LeagueFoulState + X'b + eps      bR > 0
```

X is the halftime state the book demonstrably observes: pregame closing total,
pregame closing spread, realized H1 points, realized H1 margin. The sign is
fixed here and will not be revisited.

## The sharpened test — the one that would matter

The book sees the first half before posting. If CrewShock only predicted H2
fouls through information already visible in H1, a competent book could back it
out. So the decisive question is whether crew propensity predicts second-half
fouls **conditional on realized first-half fouls**:

```
H2Fouls = a + bR*CrewShock + c*H1Fouls + bL*LeagueFoulState + X'b + eps
```

`bR > 0` here means the crew's tendency is not exhausted by what the first half
revealed. That is a stronger omission than the pregame one, and it is the
result that would justify pursuing this market.

## Market versus true

```
2H line       ~ a + c_market*CrewShock + X'b
actual H2     ~ a + c_true  *CrewShock + X'b
gap = c_true - c_market,  hypothesised > 0
```

## Inference

The existing 7-day-block crew permutation, rebuilding CrewShock from scratch on
each reshuffle, is the inference of record. Naive t-statistics on
referee-derived regressors are reported but not relied upon.

## Success criteria, all required

1. `bR > 0` on development with the predicted sign
2. `bR > 0` on the sealed 2024-25 season — same sign, magnitude not required to
   reach significance on 587 games
3. the conditional-on-H1-fouls specification also gives `bR > 0`
4. `c_true > c_market`
5. the development coefficient beats the time-local crew permutation

## Falsification and stopping

If `bR` is null or wrong-signed on development, stop. Do not re-window, do not
re-threshold, do not switch to the 2H spread, and do not substitute the
first-half total. If the coefficient survives but the −5.7pp standing bias
leaves the strategy unprofitable, the correct conclusion is
`H2_OMISSION_CONFIRMED_BUT_UNTRADEABLE`, not a search for a better entry.

## Classifications

- `H2_TOTAL_OMITS_CREWSHOCK` — coefficient and pricing gap both confirmed
- `H2_OMISSION_CONFIRMED_BUT_UNTRADEABLE` — science holds, standing bias wins
- `H2_TOTAL_PRICES_CREWSHOCK` — c_market ≈ c_true
- `H2_EXHAUSTED_BY_FIRST_HALF` — unconditional effect present, conditional null
- `H2_DATA_INSUFFICIENT` — coverage or line-quality problems dominate
