# PREREG — Visitor temporal allocation on Kalshi quarter and half totals

**Written 2026-08. No Kalshi quarter or half PRICE has been examined at any
point.** The only Kalshi metadata inspected for these series is market counts,
listing dates and volume totals (`KXNBA1QTOTAL` 26 markets from 2026-06-08,
`KXNBA2HTOTAL` 18 from 2026-06-11, all zero volume). Prices were never fetched.

---

## 0. Correction to the record, stated first

An earlier session summary of this effect designated the **Q3 leg as primary**
on development strength (+0.735/SD, t=+6.26) and claimed it "clears the taker
hurdle per single SD". A subsequent freshly-examined season contradicts that:

| leg | development | 2024-25 | 2025-26 (fresh) |
|---|---|---|---|
| d_q3 | +0.738 (t=+6.26) | +1.052 (t=+3.39) | **+0.393 (t=+1.23)** |
| d_h2 | +1.272 (t=+7.14) | +1.673 (t=+3.55) | **+0.772 (t=+1.60)** |

The Q3/H2 (late) legs decay **monotonically** across the three windows and are
no longer significant. A gate pre-specified in `q1_visalloc_master.py` requiring
`d_q3` slope > 0 with t > 2 in 2025-26 **FAILED**. The Q3 leg is therefore
DEMOTED to secondary and is not traded under this document.

Consequently the primary legs below (Q1, H1) were selected **after** seeing
2025-26. That season is burned for this hypothesis. **2026-27 is the only clean
prospective test.** This prospect is materially weaker than the earlier summary
represented.

---

## 1. The claim

`poss_vs_eff.py` established that the VISITOR's prior-season road Q3−Q1
orientation predicts BOTH teams' quarter splits out of sample (home t=+5.38,
away t=+5.06, 5/5 seasons). The effect **relocates** points between quarters and
adds none to the full game, which is why it has never been tradeable — the
full-game total does not move, so there is nothing to price against.

A newly listed quarter/half market inherits its price by formula from the
full-game ladder (`share × total`). A relocation effect beats a formula price
by construction, for as long as the formula holds.

---

## 2. Frozen state definition

```
B(team, season) = mean of that team's own (Q3 points − Q1 points)
                  over its ROAD games in seasons STRICTLY BEFORE `season`,
                  pooled, requiring n >= 60 prior road games
```

Attached to a game by its **visitor**. Source: master CSV columns `1Q_R`,
`3Q_R` — **no play-by-play dependency**, so the state is computable through
2026-06-15 and forward. (The PBP parquet ends 2024-25; using it would have made
the state inoperable. This was the operative discovery.)

Standardisation, frozen on development (2017-18…2023-24):

```
B mean = −0.3723      B sd = 1.3377        Bz = (B − mean) / sd
```

Higher B = that visitor's games run **Q3-heavy / Q1-light**.

Reference quintile cuts on development B: `−1.5094, −0.8931, −0.1200, +0.6949`.

---

## 3. Frozen benchmark — the formula price

Quarter shares of the closing full-game total, frozen on development:

| q1 | q2 | q3 | q4 |
|---|---|---|---|
| **0.2528** | **0.2515** | **0.2508** | **0.2409** |

Note these are **not** 0.25 — Q4 is structurally the low quarter (`QUARTERS.md`).
Any implementation using total/4 is wrong.

```
formula_q = share_q × closing full-game total
d_q       = actual quarter total − formula_q
d_h1      = (q1 + q2) − (share_q1 + share_q2) × total
```

Development residual sd: **Q1 8.2214**, Q3 8.1191, **H1 12.0315**.

---

## 4. Effect sizes across all three windows

Points per +1 development SD of B:

| outcome | predicted | development | 2024-25 | 2025-26 (fresh) | verdict |
|---|---|---|---|---|---|
| **d_q1** | NEG | −0.304 (−2.54) | −0.974 (−3.22) | **−0.792 (−2.57)** | **3/3 significant** |
| **d_h1** | NEG | −0.966 (−5.52) | −1.409 (−3.25) | **−1.268 (−2.78)** | **3/3 significant** |
| d_q31 contrast | POS | +1.041 (+6.31) | +2.024 (+4.68) | +1.185 (+2.68) | 3/3 significant |
| d_q3 | POS | +0.738 (+6.26) | +1.052 (+3.39) | +0.393 (+1.23) | **decaying** |
| d_h2 | POS | +1.272 (+7.14) | +1.673 (+3.55) | +0.772 (+1.60) | **decaying** |
| full-game residual | ~0 | +0.345 (+1.31) | −0.042 (−0.06) | −0.890 (−1.28) | **null 3/3** |

The full-game null in all three windows is the load-bearing confirmation that
this is relocation and not a scoring effect — and it is why the full-game market
cannot express it.

---

## 5. Legs traded

**PRIMARY A — Q1 total.** Bet Q1 **UNDER** when `Bz ≥ +1.0`; **OVER** when
`Bz ≤ −1.0`. Series `KXNBA1QTOTAL`.

**PRIMARY B — 1st-half total.** Same direction rule. Series `KXNBA1HTOTAL`.
Traded as an *alternative* expression, never alongside Primary A on the same
game — they are the same state and stacking them doubles cost without doubling
edge.

**SECONDARY, NOT TRADED — Q3 / 2H.** Recorded and monitored only (metric N5).
It re-enters only via a new pre-registration, never by amendment of this one.

**NOT TRADED — the q3−q1 spread.** It is the most robust estimand (3/3
significant) but requires two legs, and the WNBA ladder analysis established
that a two-leg construction pays both spreads and both fees. Combined edge
(+1.185 pts) against two taker hurdles (2 × 0.57 pts) does not clear.

---

## 6. Formula-price trigger — the precondition

The edge exists **only while Kalshi prices quarters by formula.** Before every
bet:

```
trigger:  | kalshi_quarter_mid − formula_q |  ≤  0.5 points
```

If the quoted mid has already moved more than 0.5 points **in the direction B
predicts**, the market has priced the state and **there is no trade**. If it has
moved more than 0.5 points against B's direction, also no trade — that is
information we do not model.

This is the assumption's own kill switch. It must be evaluated per bet and
logged, because metric N2 below is computed from it.

---

## 7. Entry rule and execution

| parameter | value |
|---|---|
| band | `|Bz| ≥ 1.0` |
| coverage | 27.7% of games, **~325 games/season** |
| direction | Q1/H1 against the sign of `Bz` |
| venue | **Kalshi MAKER ONLY** |
| staking | flat, one unit per qualifying game |
| timing | quote resting before tipoff; no in-game entry |

**Maker-only is not a preference, it is the whole trade.** Using the frozen
2¢-median-spread hurdles and the fresh-season Q1 effect:

| | Q1 leg | H1 leg |
|---|---|---|
| 1 point of edge buys | 4.85pp | 3.32pp |
| fresh-season effect per SD | 0.792 pts = 3.84pp | 1.268 pts = 4.20pp |
| **Kalshi maker** hurdle −0.56pp → net | **+4.40pp** | **+4.76pp** |
| Kalshi taker hurdle +2.75pp → net | +1.09pp | +1.45pp |
| bets to establish (maker) | **~1,012 → 3.1 seasons** | **~865 → 2.7 seasons** |
| bets to establish (taker) | ~16,500 → **51 seasons** | ~9,300 → 29 seasons |

Both maker figures clear the `MARKET_SCREENING_RULES.md` G3 four-season gate.
Both taker figures fail it outright. **A fill at the ask voids the trade** — if
the resting order does not fill, the bet is skipped and logged as unfilled, not
chased.

Fill rate is unmeasured: the `candles` table is empty and there is no
order-book history. Metric N3 exists to measure it live.

---

## 8. Monitoring metrics

Computed once per season from `q1_visalloc_master.py` plus a trade log.

| # | metric | healthy | ALERT if |
|---|---|---|---|
| **N1** | `d_q1` slope per season | −0.30 … −0.97 (3/3 windows) | slope ≥ 0, or t > −1.5 |
| **N2** | share of qualifying games passing the §6 formula trigger | (unmeasured; first season sets the baseline) | < 50% — the market has learned |
| **N3** | maker fill rate on resting quarter quotes | (unmeasured) | < 40% — the route is not executable |
| **N4** | full-game residual slope on `Bz` | \|t\| < 1.5, 3/3 windows | \|t\| > 2 — no longer pure relocation |
| **N5** | `d_q3` slope (secondary, untraded) | decaying: +0.74 → +1.05 → +0.39 | recovery to t > 2 = note; further decay = see below |
| **N6** | realized win rate vs the maker break-even | — | outside 45%–60% |

**Escalation, fixed now.** N2 or N3 alerting **once** suspends new bets
immediately — those are preconditions, not performance. N1 alerting once = note
and continue; N1 alerting in **two consecutive seasons** closes the branch. N4
alerting reclassifies the effect and requires a new pre-registration. N6 alone
never suspends. If **N1 joins N5 in decay**, the state itself is dying and the
branch closes regardless of P&L.

---

## 9. What is prohibited

- changing `MIN_PRIOR = 60`, the B definition, the standardisation constants,
  the quarter shares, the `|Bz| ≥ 1.0` band, or the 0.5-point trigger
- promoting the Q3/2H legs by amendment
- trading the q3−q1 spread, or stacking Q1 and H1 on one game
- taker entry at any price
- re-testing on 2017-18…2025-26 in any form — all three windows are spent
- conditioning on team, venue, rest, or CrewShock

## 10. Known weaknesses

1. The late legs are decaying and the reason is unknown. If that reflects a
   league-wide change in rotation timing, the early legs may follow.
2. Leg selection used 2025-26. Only 2026-37 is clean.
3. The formula-price assumption is untested — no Kalshi quarter price has ever
   been observed, by design.
4. Zero liquidity so far in these series. A market with no volume may have no
   fills at any price, which would make N3 fail immediately and end this.
5. Quarter shares drift slowly; they are frozen here, and N4 is the check that
   the drift has not become material.
