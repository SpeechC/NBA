# Team totals — what is testable without posted lines, tested (2026-08-25)

## The decomposition that frames the market

    posted_TT_error = (posted_TT - implied_split) + (implied_split - actual)

The vendor file carries NO posted team-total lines (all TEAM_* columns are
rolling stat aggregates), so only the second component is testable today.
And that component is an exact linear combination of the full-game total and
spread errors: hse = (te + se)/2, ase = (te - se)/2. Unconditionally it is
spanned by two exhaustively-tested nulls; the only non-trivial content is
FAVORITE-SIGNED conditioning and the mean-vs-median skew.

## Audit result (gated data, dev/holdout, favorite-signed, by |S|)

1. **The |S| gradient in team errors is the KNOWN spread-tilt, split in half.**
   fav_err + dog_err reproduces te by |S|: close games run under (~-0.7 at
   |S|<3), blowout lines over (+2.6 at |S|>=12, dev). This is exactly the
   |spread| tilt already pre-registered into the second-line curve spec —
   re-derived, not discovered.
2. **No stable favorite/dog asymmetry.** The garbage-time story (favorites
   coast, dogs pad) predicts dog_err > fav_err in blowouts. Dev top bucket:
   fav +1.43 vs dog +1.17 (wrong order); holdout: fav +1.02 vs dog -0.51
   (reversed). Nothing survives both windows.
3. **The OT trap holds at team level — fourth confirmation.** OT adds
   +0.4/+0.7 to team-error MEANS; no-OT means are negative; medians sit near
   zero and "score > implied" rates live in a 46-55% noise band. A team-total
   line posted at the implied mean would grade ~50/50 despite positive mean
   error.

## Conclusion

The implied-split component is EMPTY beyond what the program already holds.
**The entire candidate edge in team totals lives in `posted_TT -
implied_split` — the book's actual splitting rule — which requires posted
prices we do not have.** This is the cleanest possible acquisition case:

- §20 step 1 (recover the rule) needs one season of posted team totals;
- §20 step 2's candidate omissions are ALREADY IN THE FREEZER: the OT
  mixture's one-sided team-level mass and the |spread| tilt are precisely the
  corrections a mechanical `TT = (total -/+ spread)/2` rule would omit — and
  we know their sizes.

## Capture spec (2026-27, alongside the daily openers routine)

For each game, once at open and once near tip: posted team total and juice,
both teams, same book as the totals capture. ~30 seconds of additional daily
capture; one season yields ~2,400 posted pairs — enough to recover the rule
(step 1 is R², not a small-effect hunt) and test both frozen corrections
against its residual.
