# Monitor signals — season-by-season P&L, 2026-08-29

$100 flat at −110 (win +$90.91, loss −$100, push $0). Break-even 52.381%.
`ROI = 1.90909·hit − 1`. Read-only; nothing refit. Reproduced by
`monitor_season_pnl.py`.

## READ THE SELECTION COLUMN BEFORE THE ROI COLUMN

The four signals are **not equally trustworthy**, and the table below ranks them
in almost exactly the reverse of their evidential standing. Every ROI interval
is computed as if the strategy had been specified in advance. Two of them were
not.

| signal | how it was chosen | honest forward number |
|---|---|---|
| **MOVE_COMBINED** | walk-forward, refit each season on prior seasons only | **53.44%** — the table figure IS out-of-sample |
| **CrewShock** | threshold = development Q85; dev/holdout split respected | **54.21% on holdout** (54.82% pooled is part in-sample) |
| **final7** | window chosen by LOSO on this same data | **55.29% OOS** — not the 56.93% below |
| **pre_asb3** | **best of seven pre-specified regimes**; family-wise p = 0.0712 | **none** — the 60.47% is selection-biased and it fails correction |

`pre_asb3` shows the best ROI in this document and is the least believable
number in it. Its "ROI 95% CI excludes 0" is the naive interval that ignores the
search that produced the window; the family-wise permutation is the honest test
and it does not clear.

---

## 1. CrewShock — FROZEN, threshold 0.8682 (close, bet OVER)

| season | bets | hit | profit | ROI | vs BE |
|---|---|---|---|---|---|
| 2017-18 | 92 | 46.74% | −$991 | −10.77% | −5.64pp |
| 2018-19 | 216 | 55.09% | +$1,118 | +5.18% | +2.71pp |
| 2020-21 | 141 | 53.19% | +$218 | +1.55% | +0.81pp |
| 2021-22 | 205 | 59.02% | +$2,600 | +12.68% | +6.64pp |
| 2022-23 | 194 | 57.73% | +$1,982 | +10.22% | +5.35pp |
| 2023-24 | 138 | 52.90% | +$136 | +0.99% | +0.52pp |
| 2024-25 | 166 | 59.64% | +$2,300 | +13.86% | +7.26pp |
| **2025-26** | **238** | **50.42%** | **−$891** | **−3.74%** | −1.96pp |
| **TOTAL** | **1,390** | **54.82%** | **+$6,473** | **+4.66%** | +2.44pp |

z = +1.82, ROI 95% CI **[−0.36%, +9.67%] — includes 0**. Six of eight seasons
positive. 2025-26 is the season whose mechanism weakened (`b_fouls` 0.4775 vs a
prior-seven range of 0.79–1.36) and it also has the **most bets ever**, 238 —
the frozen-threshold selectivity problem recorded in
`PREREG_crewshock_forward` §8.

## 2. final7 — VALIDATED (close, bet OVER every game in the window)

| season | bets | hit | profit | ROI | vs BE |
|---|---|---|---|---|---|
| 2017-18 | 62 | 58.06% | +$673 | +10.85% | +5.68pp |
| 2018-19 | 62 | 56.45% | +$482 | +7.77% | +4.07pp |
| 2020-21 | 68 | 47.06% | −$691 | −10.16% | −5.32pp |
| 2021-22 | 63 | 53.97% | +$191 | +3.03% | +1.59pp |
| 2022-23 | 67 | 59.70% | +$936 | +13.98% | +7.32pp |
| 2023-24 | 69 | 65.22% | +$1,691 | +24.51% | +12.84pp |
| 2024-25 | 67 | 59.70% | +$936 | +13.98% | +7.32pp |
| 2025-26 | 69 | 55.07% | +$355 | +5.14% | +2.69pp |
| **TOTAL** | **527** | **56.93%** | **+$4,573** | **+8.68%** | +4.55pp |

z = +2.09, ROI 95% CI [+0.53%, +16.83%]. **56.93% is the in-sample close
figure** — it matches `CLOSING.md` exactly, and that document's honest
out-of-sample number is **55.29%** under LOSO window selection. Seven of eight
seasons positive; the only loss is 2020-21, when April was not the end of the
season.

## 3. pre_asb3 — NOT VALIDATED (close, bet OVER every game in the window)

| season | bets | hit | profit | ROI | vs BE |
|---|---|---|---|---|---|
| 2017-18 | 20 | 70.00% | +$673 | +33.64% | +17.62pp |
| 2018-19 | 19 | 68.42% | +$582 | +30.62% | +16.04pp |
| 2020-21 | 25 | 56.00% | +$173 | +6.91% | +3.62pp |
| 2021-22 | 23 | 73.91% | +$945 | +41.11% | +21.53pp |
| 2022-23 | 18 | 44.44% | −$273 | −15.15% | −7.94pp |
| 2023-24 | 22 | 59.09% | +$282 | +12.81% | +6.71pp |
| 2024-25 | 24 | 50.00% | −$109 | −4.55% | −2.38pp |
| 2025-26 | 21 | 61.90% | +$382 | +18.18% | +9.52pp |
| **TOTAL** | **172** | **60.47%** | **+$2,655** | **+15.43%** | +8.08pp |

**Do not read this as the best strategy here.** It is 172 bets — about 21 a
season — chosen as the best of seven regimes, and the family-wise max
permutation gives p = 0.0712. Six of eight seasons positive, but two of the
eight are negative and the whole record rests on ~21 bets a year. Display-only
in the monitor.

## 4. MOVE_COMBINED — FROZEN, |m| ≥ 1.0 (**opener**, side = sign(m))

| season | bets | hit | profit | ROI | vs BE |
|---|---|---|---|---|---|
| 2021-22 | 422 | 54.98% | +$2,091 | +4.95% | +2.60pp |
| 2022-23 | 369 | 48.24% | −$2,918 | −7.91% | −4.14pp |
| 2023-24 | 327 | 55.96% | +$2,236 | +6.84% | +3.58pp |
| 2024-25 | 335 | 54.33% | +$1,245 | +3.72% | +1.95pp |
| 2025-26 | 334 | 53.89% | +$964 | +2.89% | +1.51pp |
| **TOTAL** | **1,787** | **53.44%** | **+$3,618** | **+2.02%** | +1.06pp |

z = +0.90, ROI 95% CI **[−2.40%, +6.45%] — includes 0**. The lowest ROI in this
document and **the only figure that is fully out-of-sample by construction**.
Five seasons only; the walk-forward signal does not exist before 2021-22. Its
registered endpoint is CLV (+1.337 pts, t = +16.42, positive in all five
seasons **including** the one that lost 7.91%).

## They overlap — do NOT add the tables together

The three close-graded OVER signals fire on the same games:

```
crew & final7      73 games
crew & pre_asb3    31 games
final7 & pre_asb3   0 games   (disjoint by construction)
```

Summing the three tables double-counts **104 games**. Deduplicated, one bet per
game:

```
UNION of the three:  1,986 bets   55.49%   +$11,782   ROI +5.93%
```

MOVE_COMBINED is separate — it bets at the **opener**, can take the UNDER, and
is not merged into that union.

## What a season actually looks like

Roughly 175–240 CrewShock bets, ~67 final-week games, ~21 pre-break games and
~350 MOVE_COMBINED bets. At $100 flat that is ~$60k risked for an expected few
thousand, with single-season swings of ±$3,000 on individual legs. Every
interval above except `final7`'s and `pre_asb3`'s includes zero, and those two
are the ones whose windows this data selected.
