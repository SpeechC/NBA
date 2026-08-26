# PREREG — QUOTE-PATH DECOMPOSITION

Written 2026-08-26, BEFORE any outcome variable was touched. Only the
market-structure checks in §2 were run first (`quote_path_structure.py`);
they read betting columns only — no score, no actual total, no `dev`.

## 0. The claim being tested

`MOVE_COMBINED` trades on `tmove = close − open`: a **two-point summary of a
path we actually possess**. `LINE MOVEMENT #1/2/3` are sequential repricings
of the same full-game market, in time order. The question is whether two games
with the *same net movement* but *different paths* carry the same information.

Theoretical prior (not novel; standard microstructure folklore, here tested
rather than assumed): **early movement is sharp money hitting a stale opener;
late movement is steam the book has already absorbed into its number.** If so,
the legs of the path should not carry equal weight, and `MOVE_COMBINED` is
leaving information on the table by summing them.

This is an INCREMENTAL test by construction. It cannot rediscover
`MOVE_COMBINED` — the null is that the decomposition adds nothing to `tmove`.

### Relation to the failed attention test

`PREREG_attention_allocation` measured *public* attention (volume, market
size) and found CLV attention-invariant. The reprice count here measures **the
book's own attention** — how many times it chose to change its number. These
are different constructs and the earlier null does not settle this one. It may
well fail the same way; that would still be informative.

## 1. Data and split

Source `C:\NBA2\dfMaster_OT_2017-2026.csv` via `prepare_data.read_master()`
(market gates applied; **source file is never modified**). Regular season and
In-Season Tournament rows. 2019-20 is absent from the vendor file.

Split follows the referee branch (`CLOSING_REFEREE.md`), the closest analogue:

```
development   2017-18 .. 2023-24  (incl. IST 2023)
holdout       2024-25, 2025-26    (incl. IST 2024, IST 2025)
```

Everything below is fixed on development. The holdout is read once.

## 2. Stage-0 gates — RESULTS ALREADY IN HAND (market columns only)

**Parse.** Leading signed decimal token of each cell (`-4.5 -09` → −4.5,
`215.5o15` → 215.5). Side recovered by magnitude per `DATA_DICTIONARY` §1
(`|v| ≤ 30` spread, `|v| > 60` total). **`_R` carries the away side of the
spread and is negated.** Omitting that negation is a real error I made and
caught here: it drove the spread content gate to corr 0.324 before the fix.

| gate | spread | total | verdict |
|---|---|---|---|
| CONTENT — mean \|quote−close\| falls monotonically | 1.41→0.36→0.33→0.30 | 2.48→0.67→0.61→0.58 | **PASS** |
| CONTENT — corr with close rises | .959→.995→.995→.996 | .949→.994→.995→.996 | **PASS** |
| RANGE — inside [−30,30] / [150,300] | 0 violations | 0 violations | **PASS** |
| ERA — coverage max/min across seasons | q1 1.03×, q2 1.00×, q3 1.02× | q1 1.02×, q2 1.00×, **q3 2.06×** | q3 **FAIL** |

**Consequence, fixed here and not revisited:** `to_q3` coverage collapses to
0.486 / 0.495 / 0.620 in 2020-21 / 2021-22 / 2022-23 against ~1.00 elsewhere.
That is a vendor-recording regime change, exactly the class of defect that
produced the false detections in `MARKET_COLUMN_AUDIT.md`. **Both paths
therefore use `open → q1 → q2 → close` and discard q3 league-wide.** Symmetric
across spread and total, era-stable on every retained column.

**Structural facts that constrain the design:**

- The vendor **fills all three slots regardless of whether the line moved**:
  47% of spread games and 27% of total games show only ONE distinct value
  across the three quote slots. So *slots present* is not a reprice count.
  **Reprice count is defined as the number of DISTINCT values in
  {open, q1, q2, close}** (range 1–4).
- `q1 == close` on 54.6% of spread games and 40.3% of total games. The spread
  is usually at its closing number by the first recorded quote, so the spread
  path has materially less late-leg variation. **The total path is PRIMARY;
  the spread path is secondary.**

## 3. Construction

Per game, on the total (primary) and the spread (secondary):

```
early  = q1    − open
mid    = q2    − q1
late   = close − q2
net    = close − open   ==  early + mid + late        (identity)
churn  = |early|+|mid|+|late| − |net|                 (>= 0; 0 iff monotone)
nrep   = # distinct values in {open, q1, q2, close}   (1..4)
```

Target, the same `c_true − c_market` gap used throughout this program:

```
dev = actual_total − closing_total          (primary)
dev_s = actual_margin − closing_spread      (secondary, home-side)
```

## 4. Predictions — fixed, one-sided where stated

**PRIMARY P1 — the legs are not interchangeable.**

```
dev  ~  early + mid + late
PREDICTED:  beta_early > beta_late     (one-sided)
```

Two conditions, BOTH required to pass:

- **P1a** joint test of the three legs significant at p < 0.05 under
  within-season block permutation (5,000 reps);
- **P1b** `beta_early − beta_late > 0` with permutation p < 0.05 one-sided.

**P1 FAILS** if the joint test is null, or if `beta_early ≤ beta_late`. On
failure the branch closes. No re-tuning, no alternative leg definitions, no
re-introduction of q3, no threshold search.

**SECONDARY P2 — the book's own attention.** Under-reaction to net movement is
larger when the book repriced fewer times.

```
dev ~ net + net x 1[nrep <= 2]      PREDICTED: interaction > 0
```

**SECONDARY P3 — churn (descriptive only).** `|dev| ~ churn`, predicted
positive. This is a **variance** statement and is NOT tradeable on a main line;
it is recorded as description, never promoted to an edge claim.

**P2 and P3 cannot rescue P1.** If P1 fails, the branch closes regardless of
what P2 or P3 do. Stated here so it cannot be relitigated later.

## 5. Incremental test — the bar that actually matters

A significant P1 is necessary, not sufficient. The branch only advances if the
decomposition beats what we already trade, out of sample:

```
model A (incumbent)   dev ~ net              [ + dis_open ]
model B (candidate)   dev ~ early + mid + late [ + dis_open ]
```

**Bar: model B's HOLDOUT out-of-sample R² exceeds model A's.** Fit on
development, scored once on holdout. A development-only improvement is not a
result — it is the expected consequence of adding parameters.

## 6. Inference

- **Within-season block permutation, 5,000 reps** (program standard); naive
  OLS SEs reported alongside but not relied on.
- **Phantom-book FDR**: three pre-registered predictions are declared, so the
  95th-percentile phantom bar from `PhantomMiner` is reported for P1.
- No same-game outcome enters any regressor. Every path variable is a betting
  quote posted before tip.

## 7. Detection burden

If P1 passes, the tradeable quantity is reported as a hit rate against the
−110 break-even of 52.38%, with the required n from
`n = 7.84·p(1−p)/edge²`. An edge that cannot clear that n within the available
sample is reported as undetectable, not as a positive result.

## 8. Known limitations, stated in advance

- **The quotes carry no timestamps.** Order is known, elapsed time is not.
  "Early" and "late" are positional, not clock-based. A finding would say
  *sequence* matters, NOT that a specific hour matters, and must not be
  described in clock terms.
- Single vendor, single book. Path shape may be that book's posting behaviour
  rather than a market-wide phenomenon. Not identifiable here.
- `q1 == close` on 40% of totals means the late leg is exactly zero for a large
  minority; `beta_late` is estimated off the complement and is correspondingly
  less precise.

---

# RESULT — run once, 2026-08-26. Verdict: **P1 FAILS. Branch closes.**

Development n = 7,218 (total) / 7,146 (spread); holdout n = 2,450.

## P1 — PRIMARY, on the total

| | beta | t | leg sd | nonzero |
|---|---|---|---|---|
| incumbent `dev ~ net` | +0.1639 | +2.38 | 3.04 | — |
| leg **early** | +0.1561 | +2.09 | 2.85 | 90% |
| leg **mid** | −0.2643 | −0.90 | 0.73 | 64% |
| leg **late** | **+0.4874** | **+2.17** | 0.95 | 68% |

R² 0.00078 (net) → 0.00141 (legs).

- **P1a PASSES.** Joint R² of the three legs 0.00141 against a within-season
  permutation null of 0.00042 (sd 0.00035), **p = 0.0200**.
- **P1b FAILS, and fails in the predicted direction's exact opposite.**
  `beta_early − beta_late = −0.3314`, one-sided p = **0.9230**. The
  pre-registered prior was that early movement is the informative leg. In this
  sample the **late** leg carries the larger raw coefficient.

Both conditions were required. **P1 fails.**

## §5 incremental test — the decisive one, scored once on holdout

| spec | n | A: `dev ~ net` | B: `dev ~ legs` | B − A |
|---|---|---|---|---|
| bare | 2,448 | **+0.00126** | +0.00084 | −0.00043 |
| + `dis_open` | 2,206 | **+0.00004** | −0.00086 | −0.00090 |

**Model A wins both.** The decomposition is worse out of sample than the net
movement `MOVE_COMBINED` already trades. P1a's development-only R² gain is what
three parameters buy in place of one.

## Secondaries — both null

- **P2** (book attention): `net × 1[nrep ≤ 2]` = +0.1995, **t = +1.06**. Null.
  Reprice counts were well distributed (1: 99, 2: 1,613, 3: 3,545, 4: 1,961),
  so this is a null with power behind it, not an empty cell.
- **P3** (churn): `|dev| ~ churn` = +0.0083, **t = +0.08**. Null. Churn was
  non-zero on 51.8% of games.

## Spread path — null throughout

Joint R² 0.00022 against a 0.00042 null (**p = 0.6679**); no leg reaches |t| >
1.05; the incumbent `net` coefficient is itself insignificant (−0.0777, t =
−0.99). Consistent with §2's structural warning that the spread is already at
its closing number by the first recorded quote on 54.6% of games.

## A design flaw in this prereg, recorded rather than repaired

P1b contrasts **raw** coefficients across legs whose standard deviations differ
by 3×. Standardised, the two legs are nearly identical: early 0.1561 × 2.85 =
**0.445**, late 0.4874 × 0.95 = **0.463**. So the honest reading is not "late
beats early" — it is **no leg heterogeneity worth trading**, which is what the
holdout independently reports.

The right contrast would have standardised the legs. I did not pre-specify
that, and re-running P1b on standardised legs after seeing the result is
precisely the rescue §4 forbids. It is left unrepaired. The §5 incremental test
is scale-free and unaffected by this flaw, and it is the arbiter: **A wins.**

## Disposition

The branch closes. Per §4, P2 and P3 cannot rescue it, and neither reached
significance in any case. No re-tuning, no re-introduction of q3, no
standardised re-run, no threshold search.

**What was learned that survives the null:** the path columns are real,
parseable, era-stable once q3 is dropped, and now documented — but the market's
net movement is a sufficient statistic for the path. `MOVE_COMBINED` is not
leaving information in the sequence. The book's own reprice count is as
attention-invariant as the public's volume was in
`PREREG_attention_allocation`, which was the open question this test was built
to settle; **both attention constructs are now closed, from opposite sides.**
