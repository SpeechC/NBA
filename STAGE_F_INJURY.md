# STAGE F — INJURY AND LINEUP DATA, ACQUIRED AND INCORPORATED

Source already on disk: **14,327 official NBA injury-report PDFs** parsed to
`injury_status_panel.csv` — **1,224,205 rows**, 2020-12-22 to 2025-12-22, with
**`report_ts` timestamps** (median 19 distinct report stamps per game date).
`injury_features_build.py`, `injury_incorporate.py`.

## Construction and match diagnostics

Importance weighting uses each player's **prior-season points per game**, shrunk
to the league mean, so an absence is measured in **expected points removed**
rather than a headcount. Status weights: Out 1.0, Doubtful 0.75, Questionable
0.35, Probable 0.10.

**Name matching was the known failure mode** (the CrewShock "JT Orr" lesson: an
unmatched name silently zeroes a signal). First pass matched 89.89%, and the
misses were one systematic pattern — glued suffixes (`WilliamsIII,Robert`,
`DukeJr.,David`) invisible to a word-boundary regex. After repair:

```
player name match   97.25%   (residual = players who never appear in PBP, who score ~0)
team name match     96.9%
games with BOTH teams covered   5,634 of 9,487   (2020-12 onward)
mean players Out 3.41   mean expected points removed 32.74
sd of the CHANGE vs previous game 12.69 pts
LATE news (last report - first report) nonzero on 54.8% of team-games
```

Both **level** and **change** are built: a season-long absentee is already inside
the latent rating, so only the *news* is marginal information.

## FORECAST GAINS — small on the opener, four times larger on the close

Held-out 2022+, injury-covered sample (n = 3,583):

| target | model | RMSE | R2 |
|---|---|---|---|
| OPENING | M6 + D2 + D4 | 3.119 | 0.8566 |
| OPENING | **+ injury** | 3.092 | **0.8605** (+0.0039) |
| CLOSING | M6 + D2 + D4 | 3.638 | 0.8278 |
| CLOSING | + injury early | 3.524 | 0.8393 |
| CLOSING | **+ injury early + late** | 3.462 | **0.8452** (+0.0174) |

**Injury data helps the CLOSE 4.5x more than the OPENER** — exactly as expected
if the news arrives after the opener posts.

## THE INNOVATION TEST — every sign correct, and injury is now the dominant channel

On the D4 state, team-game panel, back-to-backs excluded (n = 8,925):

```
own injury LEVEL         -0.0215 (t=-21.7)     more of YOUR scoring out -> lower quote
opponent injury LEVEL    +0.0081 (t= +8.1)     opponent depleted        -> higher quote
own injury CHANGE        -0.0206 (t=-12.7)
late-report news         -0.0098 (t= -4.4)

recent scoring surprises only    R2 0.0150
INJURY features only             R2 0.0703      <- 4.7x stronger
BOTH                             R2 0.0885      overlap -0.0032 (independent channels)
```

**On the D4 state — which already absorbs the scoring channel — injury is by far
the strongest remaining explainer of market revisions**, and it is essentially
orthogonal to recent performance.

## Error concentration — helps where we are wrong, hurts where we are right

```
baseline-error decile     base |err|   +injury |err|   change
 1 (best games)                0.187           0.667   +257.0%
 8                             3.325           3.121     -6.2%
 9                             4.266           4.107     -3.7%
10 (worst games)               6.788           6.423     -5.4%
overall                        2.386           2.383     -0.1%
```

**Directionally right — 4-6% error reduction in the worst deciles — but it adds
noise to games already predicted well, netting to zero.** `corr(|error|, injury
level) = +0.1265`.

## THE CEILING, and why the opener gain is necessarily small

The game-level innovation *is* the state model's residual. So explaining the
innovation completely would mean reconstructing the opener exactly, and
explaining 8.85% of it buys only 8.85% of the residual variance:

```
sd(innovation) 2.165 pts  ->  residual after both channels 2.067 pts
STILL UNEXPLAINED: 91.2% of the market's between-game revision
```

Stage E's wall was 92.4% with scoring alone on the D2 state. With a better state
and real injury data it is **91.2%**. The wall moved by roughly one point.

## Honest verdict

**The data is real, correctly signed, and the best single explainer of market
revisions in the programme — and it does not move the forecast much.** The
opener goes 0.8566 -> 0.8605.

**What would plausibly improve it, in order:**
1. **Replacement quality and projected minutes.** Current weighting is raw prior
   PPG; losing a 25-ppg scorer backed by a good sixth man is not the same event.
2. **Filtering the report.** It lists two-way and G-League players whose absence
   carries no information, inflating the level feature.
3. **True opener timestamps.** "Earliest report" is a proxy; without opener times
   we cannot confirm which reports preceded the number.

**What this does NOT support:** the earlier reading that the unexplained residual
is *mostly* injuries and lineups. Injuries are measurable, significant, and
account for ~7% of the revision. **91% remains unexplained**, and it is now known
not to be recent scoring (Stage E), not team dispersion, not Four Factors, and
not — on this construction — injury reports either.

---

# STAGE F.2 — REPLACEMENT QUALITY AND PROJECTED MINUTES

The raw feature weighted absences by prior PPG, which treats losing a 25-ppg
scorer backed by a good sixth man the same as losing one backed by nobody. Fixed.
`vorp_build.py`, `vorp_features.py`, `vorp_test.py`.

## Construction

**Real minutes, not a proxy.** `lineup_stints.csv` gives `STINT_SECONDS` with all
five player slots; melting and summing yields 215,181 player-games (mean 21.8
min, p50 22.3, only 0.03% above 50). Joined to `player_game_pts` at 90.2%.

```
projected minutes / points   prior-only expanding mean, shrunk k=8 to prior season
player rate                  ppm = projected points / projected minutes
REPLACEMENT LEVEL            mean ppm of AVAILABLE players ranked 9-12 by projected minutes
VORP                         sum over absent players of
                               (ppm_player - ppm_replacement)+ x projected_minutes x status_weight
```

Roster = players appearing for that team in the prior 30 days, latest prior state.

```
VORP (net points lost)   mean  5.60   sd  6.78   p90 14.74   max 79.0
RAW  (gross points out)  mean 22.22   sd 17.71
replacement ppm 0.4024   minutes out 44.0
corr(VORP, RAW) = 0.8494   -> replacement quality is NOT redundant
```

**5.6 net points is a plausible figure; the raw 22.2 was not** — it counted the
full production of players a replacement partly covers.

## VORP dominates the raw feature on every target

Held-out 2022+, n = 3,181:

| target | model | RMSE | R2 |
|---|---|---|---|
| OPENING | baseline M6 + D2 + D4 | 3.203 | 0.8551 |
| OPENING | + injury RAW | 3.159 | 0.8597 |
| OPENING | **+ injury VORP** | **3.132** | **0.8615** |
| OPENING | + both | 3.143 | 0.8613 |
| CLOSING | baseline | 3.689 | 0.8286 |
| CLOSING | + injury RAW | 3.505 | 0.8458 |
| CLOSING | **+ injury VORP** | **3.440** | **0.8509** |

## And it nearly DOUBLES the innovation signal

```
RAW gross points out     R2 0.0440   raw  -0.0227 (t=-21.2)   opp +0.0077 (t=+7.2)
VORP net of replacement  R2 0.0795   vorp -0.0897 (t=-29.5)   opp +0.0190 (t=+6.3)
VORP + change            R2 0.0803                            d_vorp -0.0137 (t=-3.0)
both                     R2 0.0816   raw collapses to -0.0032 (t=-2.3)
```

**VORP raises the innovation R2 from 0.0440 to 0.0795 — an 81% improvement — and
once VORP is in, the raw feature is essentially dead** (coefficient falls from
−0.0227 to −0.0032). The replacement adjustment is not a refinement; it is what
makes the injury signal work.

Signs remain correct throughout: own absences lower the quote, opponent absences
raise it.

## Status

**Best opener forecast: R2 0.8615** (this sample, n=3,181; coverage limited to
2020-12 to 2025-04 by the injury and stint files).

The honest picture is unchanged in shape but improved in degree: injury
information is real and now well measured, it explains ~8% of the market's
between-game revision, and it moves the opener forecast by ~0.6 R2 points.
**Roughly 92% of the revision remains unexplained.**

**Remaining hygiene, unaddressed:** two-way and G-League players still enter the
report (the replacement construction mitigates but does not remove this), and
true opener timestamps still do not exist, so "earliest report" remains a proxy
for what preceded the number.
