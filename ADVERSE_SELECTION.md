# Adverse selection, first measurement (M2) — 2026-08-26

From the monitor's depth logs: 40,701 rung-polls across 7 events, 35 strikes.
Fills inferred from depth consumption (size at the touch falls >10% while the
price level holds), then marked out forward against the mid.

## Result

| horizon | inferred fills | markout \| fill | markout \| all | adverse selection |
|---|---|---|---|---|
| 1 min | 1,453 | −0.09c | +0.01c | **+0.09c** CI [+0.01,+0.17] |
| 3 min | 1,445 | −0.02c | +0.03c | +0.02c CI [−0.27,+0.36] |
| 5 min | 1,430 | −0.02c | +0.05c | +0.02c CI [−0.58,+0.61] |
| 10 min | 1,412 | +0.39c | +0.10c | −0.39c CI [−1.40,+0.71] |

**Adverse selection is essentially zero.** Only the 1-minute horizon is
distinguishable from it (+0.09c, CI excludes zero), and even that is a tenth
of a cent. By 3-5 minutes it is +0.02c with intervals swamping the estimate.

The fill inference is doing *something*: `markout | fill` is consistently more
negative than `markout | all` at 1-5 minutes, which is the right sign — prices
drift down slightly after someone sells into a bid. But the magnitude is
negligible.

## The maker ledger (bid side, 5-minute horizon)

```
quoted half-spread earned   +1.81c
adverse selection           -0.02c
fee at mean price           -1.74c
                            ------
net per filled contract     +0.06c
```

**The fee, not adverse selection, is what eats market making here.** At a 1c
median half-spread and a 1.74c fee, the maker's gross capture barely covers
the exchange charge before anyone informed shows up.

Applied to the surviving intra-ladder edge (+1.24c gross), the
adverse-selection charge leaves **+1.22c** — the edge survives its main
theoretical threat and remains the same order as the fee.

## Depth

Resting size at the touch: **bid median $84, ask median $347**. The bid side
is thin. F1 (>=5 contracts at the would-trade price) passes comfortably, but
$84 of resting bid is a capacity ceiling, not a business.

## Caveats

1. **Cancellations are indistinguishable from trades** in this data, so the
   inferred-fill set includes non-fills. That dilutes measured adverse
   selection toward zero — this measurement is OPTIMISTIC for the maker case.
2. **Two nights, 7 events.** Nothing here is a season estimate.
3. The asymmetric depth (bid $84 vs ask $347) means bid-side and ask-side
   making are different businesses; only the bid side is measured above.

## Standing read

Adverse selection was the named threat to the last surviving edge, and on this
evidence it is not the binding constraint — **the fee is**. That reframes the
maker question: it is not "can we avoid informed flow" but "can we capture
more than 1.74c per contract", which on a 1c half-spread board requires the
ladder-residual edge to be real and to persist.
