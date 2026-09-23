# NBA TOTALS — PROJECT CLOSED (2026-09-14)

Closed by decision after the ±15 maker hypothesis failed its own pre-freeze audit. This file is
the index: what was closed and on what number, what transfers to other work, and the two things
deliberately left alive.

**One thing this does NOT close.** `PREREG_2026_27_PROSPECTIVE.md` was frozen on 2026-08-30 and
remains to be evaluated exactly as written when the season runs. D3 binds: nothing discovered in
this session touches it. Closing the research is not cancelling the frozen evaluation.

---

## 1. WHAT IS CLOSED, AND THE DECISIVE NUMBER

| line of attack | verdict | decisive evidence |
|---|---|---|
| **Signed-total forecasting** | closed | 10 ML families, **every one loses money**; the 3-column market-only control loses LEAST (−$14,567 vs −$32,031). Adding information costs money. XGB/CatBoost early stopping picks ~0 trees |
| **Latent-state / factor exposures** | closed | forecastable at **27.0% OOS R²**, worth **−0.13%** against the close (z −3.63) |
| **Shot-volume channel** | closed by an information bound | team-level info content **5–9% R²** against the **17.4%** required; capped ~0.7 pts under a 1.12-pt bar |
| **Team-specific residual effects** | closed | joint **F = 1.056, p = 0.384** on 30 team dummies |
| **Error persistence (unattributed)** | closed | betting the prior error **−$22,480** (z −2.81); fading it **−$43,915** (z −5.48) |
| **Pregame conditional dispersion** | closed | 4 operationalizations; LightGBM AUC **0.4910 and ordered backwards** (z −2.08); residual volatility t +0.27 given the close |
| **Long-strangle selection** | closed | needs a **20.9%** σ gap; the best measured effect is 8.1% and Kalshi prices it to **0.01pp** |
| **Far-rung skew trade** | closed | the rungs do not exist — ladder is a fixed 11-strike, 3-pt grid at C±15; ±35 listed in **3 of 1,324 events** |
| **±15 maker hypothesis** | closed | estimate is **+0.31¢ not +0.97¢** (Kalshi settles `greater` on both rungs; 72% was boundary mass); spread capture **3×** it; settlement sign wrong on the mechanism leg; **15–17 seasons** to resolve |

## 2. RESULTS THAT TRANSFER

These are the outputs worth more than the nulls. Each is reusable outside this project.

1. **The mechanism-test bar is price-dependent and was understated.** Measured from the juice in
   the file: **1.12 pts for totals** (was 1.079 assumed), **0.81 for spreads** (was 0.79). Only
   30% of spreads and 44% of totals are actually at −110, and the distribution skews against the
   bettor. Every result previously scored at the assumed bar is 2–4% worse than reported.
2. **The closing total is a MEDIAN forecast of a right-skewed distribution.**
   `P(dev>0 | no push) = 0.5047`, CI [0.494, 0.515], every season's CI containing 0.500 while the
   mean is positive in 7 of 8. **Mean forecast errors need not become directional win-rate edges** —
   check the median before believing any mean bias.
3. **79% of Var(dev) is irreducible shot-outcome sampling.** 2P% 93.9%, 3P% 97.5%, FT% 84.0%.
   MAD floor 12.81 against an observed 14.29: a pre-game model can remove at most **1.48 pts**.
4. **Team-level information content of a game-level rate is 5–9% of R².** Reusable as a
   pre-build screen: price any team-style signal against it before writing the code.
5. **Never rank principal components by eigenvalue.** `Var(E) = Σ(1'v_k)²λ_k`; PC6 was 4.0% of
   shock variance and 26.4% of the pricing error while PC5 was 10.8% and 0.4%.
6. **Shocks differenced against an adaptive team engine cannot persist by construction.** Team
   lag-1 autocorrelation +0.018 on engine residuals vs +0.341 on raw levels. Use a fixed league
   baseline or the test is guaranteed-null for a mechanical reason.
7. **Overtime inverts the tail asymmetry, it does not merely add to it.** Regulation-only
   `P(>K)/P(<−K)` is 0.88/0.87/0.86 at K=20/25/30 against 1.12/1.17/1.30 including OT.
8. **Kalshi ladder quotes must be forward-filled.** The candle feed omits minutes where nothing
   happened; a resting quote persists until cancelled. Bars-only gives ~4.5 usable rungs,
   forward-filled gives **10.69**. Verified on 312,766 gaps at 100.000%.
9. **Kalshi settles `greater` on every strike** — a total landing exactly on a strike settles NO.
   Both rungs of a nominal strangle are `greater` contracts, not a `greater`/`less` pair.

## 3. DATA DEFECTS CATALOGUED

- **3 games fail `PTS = 2·FG + 3P + FT`** (22201146, 22201187, 22500029) while
  `TOTAL_PTS = PTS_H + PTS_R` still holds, so the mirror check misses them.
- **`CREW_H` is a single official, not a crew** (81 names); `REFEREE & UMPIRE_H` is a second (89),
  and the two **never co-occur** — one of three officials is observable per game.
- **The 2019-20 season is absent** from `dfMaster_OT_2017-2026.csv` entirely. Eight seasons, not nine.
- **The PBP store stops at 2024-25**, so it cannot see the season in which the shot-volume signal
  inverted.

## 4. DELIBERATELY LEFT ALIVE

Small, honest, and not worth capital today.

1. **The late-season OVER pocket.** Last 7 days of the regular season: 407 bets, 56.51%,
   **+$3,157** at $100 flat, 5 of 6 winning seasons, **z = +1.65**. Not significant, ~$395/season,
   and the base rate is against it (the six best-looking rules traded forward lost **−$28,820**).
   The one test that would promote or kill it: **is the bias carried by games with an eliminated
   team?** That is a pregame-observable trigger from the standings and needs no new data.
2. **In-play dispersion.** Everything here tested *pregame* conditioning. In-play is a different
   information set and was never touched.

Also recorded and not acted on: **`CANDIDATES_2027_28.md` C4**, the pace closing-residual drift
(0.157 → 0.594 pts, t +1.65), found as a placebo on the same data the prereg was frozen on.

## 5. WHY IT CLOSED

Not "we didn't find it yet." A measured gap between what is knowable and what is required:

```
required to clear the vig on a total          1.12 points
best signal ever measured against the close   0.85 points (joint, in-sample; ~0 walk-forward)
team-level information ceiling                5-9% R2 against 17.4% needed
irreducible share of the error                79%
```

Three independent confirmations of the same conclusion — an information bound, ten model families
scored on P&L, and a market-microstructure audit — arriving from different directions at the same
place. The forecasting question is answered. The venue question is answered. What remains is a
third of a cent under a spread three times its size.
