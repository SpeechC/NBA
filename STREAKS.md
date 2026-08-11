# Days off and home/road streaks

Complete file, 14452 team-games. Itinerary holes: 3.12%.

## 1. Effect on a team's own scoring

Split *within venue*: `home_stand_game`, `road_trip_game`, `days_away` and `streak_signed` are zero for one venue by construction, so a naive median split on them just recovers home-court advantage (~2.0 pts). Each is therefore compared deep-in-streak vs early-in-streak among games at the relevant venue only.

|                 |     n |   deep/high |   shallow/low |   diff |
|:----------------|------:|------------:|--------------:|-------:|
| rest_days       | 14452 |     112.05  |       111.373 |  0.677 |
| is_b2b          | 14452 |     110.438 |       111.739 | -1.301 |
| is_3in4         | 14452 |     110.892 |       111.722 | -0.83  |
| is_4in5         | 14452 |     108.947 |       111.514 | -2.567 |
| travel_km       | 14452 |     110.909 |       111.91  | -1.001 |
| tz_shift        | 14452 |     111.242 |       111.445 | -0.203 |
| road_trip_game  |  7226 |     110.625 |       110.436 |  0.189 |
| home_stand_game |  7226 |     112.713 |       112.458 |  0.255 |
| days_away       |  7226 |     110.844 |       110.263 |  0.581 |
| is_return_home  |  7226 |     112.476 |       112.541 | -0.065 |
| games_last_7    | 14452 |     111.1   |       111.675 | -0.574 |
| games_last_14   | 14452 |     111.325 |       111.678 | -0.352 |
| travel_km_7d    | 14452 |     111.139 |       111.883 | -0.745 |


## 2. Against the closing spread (6781 games)

Excess margin = actual margin − closing line. Each variable enters as a home-minus-away differential.


**Univariate**

|                 |    coef |     se |       t |      p |
|:----------------|--------:|-------:|--------:|-------:|
| rest_days       |  0.1058 | 0.1801 |  0.5872 | 0.5571 |
| is_b2b          | -0.1061 | 0.3142 | -0.3377 | 0.7356 |
| is_3in4         | -0.2466 | 0.2713 | -0.9091 | 0.3633 |
| is_4in5         | -3.5758 | 3.0398 | -1.1763 | 0.2395 |
| travel_km       | -0      | 0.0001 | -0.2532 | 0.8001 |
| tz_shift        | -0.1773 | 0.1482 | -1.1959 | 0.2318 |
| road_trip_game  | -0.0041 | 0.1254 | -0.0326 | 0.974  |
| home_stand_game | -0.0463 | 0.1231 | -0.3763 | 0.7067 |
| streak_signed   | -0.0205 | 0.0855 | -0.2393 | 0.8109 |
| days_away       |  0.002  | 0.0564 |  0.0354 | 0.9718 |
| is_return_home  | -0.0816 | 0.4463 | -0.1829 | 0.8549 |
| games_last_7    | -0.3686 | 0.1977 | -1.8645 | 0.0623 |
| games_last_14   | -0.333  | 0.1556 | -2.1398 | 0.0324 |
| travel_km_7d    | -0      | 0.0001 | -0.4781 | 0.6326 |


**Joint**

|                   |    coef |     se |       t |      p |
|:------------------|--------:|-------:|--------:|-------:|
| const             |  0.0409 | 0.4509 |  0.0908 | 0.9277 |
| d_rest_days       | -0.0439 | 0.2892 | -0.1517 | 0.8794 |
| d_is_b2b          |  0.026  | 0.481  |  0.054  | 0.957  |
| d_is_3in4         | -0.0986 | 0.3381 | -0.2916 | 0.7706 |
| d_is_4in5         | -3.2865 | 3.0618 | -1.0734 | 0.2831 |
| d_travel_km       | -0.0001 | 0.0002 | -0.3665 | 0.714  |
| d_tz_shift        | -0.1828 | 0.149  | -1.2271 | 0.2198 |
| d_road_trip_game  |  0.2028 | 0.3611 |  0.5616 | 0.5744 |
| d_home_stand_game | -0.0759 | 0.1463 | -0.5185 | 0.6041 |
| d_days_away       | -0.092  | 0.1608 | -0.5719 | 0.5674 |
| d_is_return_home  | -0.0867 | 0.5117 | -0.1694 | 0.8655 |
| d_games_last_7    | -0.2218 | 0.2745 | -0.8082 | 0.419  |
| d_games_last_14   | -0.2644 | 0.1929 | -1.3703 | 0.1706 |
| d_travel_km_7d    |  0      | 0.0001 |  0.0604 | 0.9518 |


Mean squared t across the 13 schedule variables: 0.49 (≈1.0 is what pure noise produces; below 1.0 means less structure than chance would generate).


## 3. Against the closing total (6781 games)

|                 |    coef |     se |       t |      p |
|:----------------|--------:|-------:|--------:|-------:|
| rest_days       | -0.1345 | 0.2453 | -0.5484 | 0.5834 |
| is_b2b          | -0.3604 | 0.4279 | -0.8423 | 0.3996 |
| is_3in4         | -0.0262 | 0.3694 | -0.071  | 0.9434 |
| is_4in5         |  4.3574 | 4.1393 |  1.0527 | 0.2925 |
| travel_km       | -0.0002 | 0.0002 | -0.8229 | 0.4106 |
| tz_shift        |  0.2685 | 0.2018 |  1.3301 | 0.1835 |
| road_trip_game  |  0.1683 | 0.1707 |  0.9859 | 0.3242 |
| home_stand_game |  0.0295 | 0.1676 |  0.1757 | 0.8605 |
| streak_signed   | -0.0641 | 0.1165 | -0.5506 | 0.582  |
| days_away       |  0.1294 | 0.0768 |  1.6849 | 0.0921 |
| is_return_home  | -0.3732 | 0.6077 | -0.6142 | 0.5391 |
| games_last_7    |  0.2392 | 0.2693 |  0.8884 | 0.3744 |
| games_last_14   |  0.0105 | 0.212  |  0.0494 | 0.9606 |
| travel_km_7d    | -0      | 0.0001 | -0.2264 | 0.8209 |

## Verdict

**Days off**: already tested previously; retested here on the complete file. Real
fatigue effects on scoring — 4-in-5 costs 2.57 points, a back-to-back 1.30, 3-in-4
0.83 — and none of it survives contact with the closing line (all |t| < 1.2).

**Home/road streaks**: newly tested, and the headline is a confound corrected. A
naive median split makes home-stand depth look worth 2.04 points, but that number
is just home-court advantage, because `home_stand_game` is zero for every road
game by construction. Comparing deep vs shallow *within the same venue*, the
effect nearly vanishes: +0.26 points late in a home stand, +0.19 late in a road
trip, +0.58 for days away from home, −0.07 for returning home from a long trip.
NBA teams do not measurably tire from being on the road per se; they tire from
playing games in quick succession, which the rest variables already capture.

**Against the market**: nothing, in either direction. The joint regression of
excess margin on all 13 schedule variables gives a mean squared t of **0.49** —
*below* the 1.0 that pure noise generates. The best univariate result anywhere is
games-in-last-14 at t = −2.14 (p = 0.032); across 14 variables and two markets
that is 28 tests, where chance alone predicts about 1.4 hits at p < 0.05. We
found one. Nothing here is real.

This closes the schedule as a source of edge. Rest, density, travel distance,
time-zone shifts, road trips and home stands are all either negligible in
magnitude or fully priced. The remaining unpriced information is not in the
calendar.
