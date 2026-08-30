# NBA betting literature — PDF store, built 2026-08-29

22 PDFs, 20.7 MB. Searched on "NBA betting", "NBA market inefficiencies",
"NBA profit" and adjacent terms. **Triaged by what is NEW to this program**,
because ~11 papers were already read and summarised into memory and should not
be re-litigated.

## TIER 1 — NBA-specific, and plausibly a NEW idea for us

| file | what it is | why it matters here |
|---|---|---|
| `causal_hangover_arxiv2412.21181` | Santucci, Lax, **supervised by Guido Imbens** (Stanford), 2024 | **Nightlife in the visiting city → team performance**, with a claimed profitable betting strategy. A *visitor-side exogenous shock* — the same shape as CrewShock, and a genuinely new mechanism we have never tested. Causal-inference pedigree. **Highest priority.** |
| `wolfers_nba_betting_jqas2008` | Larsen, Price, **Wolfers** — "Racial Bias in the NBA: Implications in Betting Markets", JQAS 2008 | An **officiating-crew composition** channel with an explicit betting implication. Nearest published relative of CrewShock. |
| `price_remer_stone_subperfect_game_ssrn1377964` | **Price, Remer & Stone — "Sub-Perfect Game: Profitable Biases of NBA Referees"**, Oct 2010 / JEMS 2012, 34p *(user-supplied)* | **Read the correction below — "profitable" means profitable for the LEAGUE, not a betting edge.** Its value here is the identification design and one cross-reference to our own unexplained Q4 result. |
| `humphreys_point_spread_shading_nba` | Humphreys 2010, RDES | Point-spread **shading** and behavioural bias — large home underdogs, win streaks. We killed the streak leg (Byrnes & Farinella, 49.75% OOS); the **home-underdog shading** leg is untested here. |
| `ml_edge_nba_escholarship` | UCLA MS thesis, 90p — "Beating the Book: A Machine Learning Approach to Identifying an Edge in NBA Betting Markets" | Longest NBA-specific applied treatment in the store. Read for feature ideas and for how it handles the vig. |
| `lust_nba_spread_efficiency_thesis` | Lust, Miami University | Direct NBA point-spread efficiency test. |
| `covid_sports_betting_arxiv2109.07581` | Qureshi (MIT) & Zaman (Yale) | Claims **16.7% profit betting NBA underdogs during COVID**. Regime-specific and almost certainly not live, but the *magnitude* is a useful calibration for what a real dislocation looks like. |
| `winning_team_covers_arxiv1902.10067` | Mateos (MIT) | "Does the winning team always cover the spread" — 1990-present. |
| `beating_the_house_arxiv1910.08858` | Ramesh (Federal Reserve Board), Mostofa (Rice) | Single pricing model across NFL/NBA/NCAAF/NCAAB/WNBA. |

| `ssrn_4705918` | **Walsh & Joshi (Univ. of Bath), SSRN 4705918 — "Machine learning for sports betting: should model selection be based on accuracy or calibration?"** *(user-supplied, preprint, not peer reviewed)* | **NBA moneyline, single-season betting experiment on published odds.** Claims selecting models on **calibration** rather than accuracy turns **−35.17% ROI into +34.69%**, and that Kelly only works with a calibrated model. See the standing note below before citing the magnitude. |

### CORRECTION — Price, Remer & Stone is NOT a betting-edge paper

I relayed this earlier as "the canonical referee-bias-**is-profitable** paper."
That is the common framing and it is **wrong**. The paper contains no betting
strategy, no wagering test, and no point-spread analysis. "Profitable" refers
to the **league's** revenue: *"All three biases are plausibly profit-enhancing
for the league. Home favoritism increases the home court advantage, which
likely increases ticket demand... Biasing calls in favor of teams losing during
games keeps games close and more competitive, likely improving television
viewership."* Gambling appears only as motivation, via the Donaghy scandal.

**What it is actually worth to us — two things.**

**1. The identification design, which is transferable.** They separate referee
bias from player behaviour by exploiting **variation in referee discretion over
turnover types**: *discretionary* turnovers (travelling, offensive fouls —
always a whistle with the ball in play) versus *non-discretionary* ones (bad
passes, lost balls — no whistle needed). The non-discretionary series is a
**player-behaviour control** for the discretionary one. That is a clean
within-game treatment/control, and it is a **positive-control design we could
adopt** — `CLOSING_REFEREE`'s retired "live-ball turnover composition" test was
reaching for the same contrast without framing it this way.

**2. A candidate mechanism for a result we could not explain.** They find refs
favour **teams losing during games**. `QUARTER_WINNER_AUDIT` records, as an
unexplained Stage-1 mechanical fact, that trailing teams gain **+1.65 points of
Q4 margin at deficits of 12+, monotone in the deficit, 8 of 8 seasons**. We
attributed that to garbage time. Price/Remer/Stone offer a second, independent
channel — officiating that keeps games close. Both can be true, and the two are
separable with the DTO/NTO contrast on our own play-by-play.

Note it does **not** duplicate or threaten CrewShock: their biases are
**game-state** biases (home, trailing in game, trailing in series); CrewShock is
**crew identity** — an official's idiosyncratic foul propensity, matched to the
league level over the same calendar span. Different constructs entirely.

### On the Walsh & Joshi ROI claim — read the caveat first

The **direction** is one this program already agrees with and has paid for
twice: `PREREG_cohesion` passed on points and lost 3.56% because the effect was
not at the line, and `DISTRIBUTION_AUDIT` shows a naive Gaussian
spread→probability map misprices the extremes by 2.81pp, **more than the
2.381pp vig**. Both are calibration failures, not accuracy failures. Walsh &
Joshi is the cleanest published statement of the principle.

The **magnitude** should not be carried over. A +34.69% single-season ROI is
roughly seven times the best figure anywhere in this program (CrewShock,
+4.66% pooled, CI still including zero), it is one season on one book, the
paper is a **preprint that has not been peer reviewed**, and
`Winkelmann 2024` — already in memory — shows efficient markets throw
"significant" season-level findings more than 75% of the time. Treat the
principle as adopted and the number as unverified.

## TIER 2 — methodology, staking, and meta

| file | note |
|---|---|
| `optimal_betting_strategies_arxiv2107.08827` | Uhrín et al., experimental review of staking. Tests on basketball among others. |
| `chu_wu_swartz_modified_kelly` | Chu, Wu, **Swartz** — same SFU group as the Moya 2012 staking paper already in memory. |
| `kelly_bayesian_eval_arxiv2602.09982` | Kelly betting as **Bayesian model evaluation** — a way to grade forecasts sequentially. Possibly useful as a monitoring endpoint. |
| `wharton_betting_selection_sizing_kelly` | Quarter-Kelly beat full Kelly over 10,275 bets. |
| `luiss_optimal_kelly_thesis` | Kelly applied to sports and equities. |
| `ml_sports_betting_review_arxiv2410.21484` | 63p **systematic review** — mine its bibliography for anything this search missed. |
| `matchfixing_inplay_arxiv2605.30209` | **Winkelmann** et al. — same author as the efficiency-simulation paper already in memory, which is our meta-explanation for the whole literature. |
| `inplay_aft_football_arxiv2605.16066` | Market-calibrated accelerated-failure-time in-play model (football). Method transfers. |

## TIER 3 — other sports / adjacent, kept for method not content

`nfl_moneyline_efficiency_cmc`, `nyu_finding_inefficiency` (NFL pick'em),
`cfb_betting_market_efficiency_aea` (Sinkey & Logan), `football_betting_efficiency_cbs_thesis`,
`weak_form_efficiency_robbins`, `anchoring_affect_gaming_markets` (playoff-positioning anchoring).

## WANTED — found but blocked, worth another route

| paper | why | blocker |
|---|---|---|
| **Price, Remer & Stone, "Sub-Perfect Game: Profitable Biases of NBA Referees"** (JEMS 2012) | The canonical referee-bias-is-profitable paper. Direct ancestor of CrewShock. | OSU repository 404, ResearchGate wall |
| **"A Simple Trading Rule for Beating the NBA Sports Market"** (SSRN 2149603) | Claims NBA **totals lines are biased early each season**, 56.72% vs the close. Directly testable on our data and adjacent to the `final7` / `pre_asb3` calendar windows. | SSRN 403 |
| **"Inefficient Forecasts at the Sportsbook: Real-Time Betting Line Movement"** | Open→close line movement across multiple books. Direct relative of MOVE_COMBINED. | ResearchGate wall |
| Uncertainty-Aware NBA Forecasting (MDPI 2026); XGBoost+SHAP NBA (PMC) | Recent ML | JS-gated PDF endpoints |

## Already in memory — do NOT re-read

Kalshi mention markets (Kim 2026); the 5-paper NBA betting-market set incl.
**Schnytzer & Weinberg 2004**; Song 2020 in-play totals; Moya 2012 staking;
Martín-González 2016 / Zhang 2021 scoring process; Byrnes & Farinella momentum
(**tested and null**: 49.75% OOS, z = −3.15); Winkelmann 2024 efficiency
simulations.
