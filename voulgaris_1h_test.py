"""
===============================================================================
 THE VOULGARIS TEST — is Kalshi's 1H board a naive transform of the full board?
===============================================================================
 Voulgaris's signature edge: books derived half/quarter lines MECHANICALLY
 from the full-game number, and the transform ignored how scoring actually
 distributes. Internal consistency (quarter_consistency_test.py) does NOT
 close this: coherent boards can share the same wrong split.

 RESULTS (2026-08-25), pregame 1H board vs realized H1, last bracketed
 pregame bar (median 1 min before tip):

 1. THE SPLIT IS NOT NAIVE. Market-implied H1 share = 0.501 of the full-game
    line vs realized share 0.495 (WNBA halves are nearly symmetric:
    H1 86.0 / H2 87.6 on 283 games). No fixed-ratio error at the share
    level. The classic NBA version of the edge (H1 > H2 by ~6 pts, so a
    50/50 split misprices both halves) does not exist in the WNBA's shape.

 2. EXPLORATORY LEVEL BIAS, one month only: on the n=34 games with a
    bracketed pregame 1H ladder (ALL August -- earlier boards were unquoted
    pregame), mean(H1 - L_1H) = -3.80 pts (se 1.64, t=-2.3), median -5.28;
    blind 1H UNDER hits 65%. Economics IF real: 1H slope 3.4c/pt, spread
    6.4c, round trip 4.9c = 1.4 pts -> edge/cost ~2.6, which would clear.

 3. HONESTY GATE: this is the ~6th exploratory pattern examined today on
    this season; a lone t=-2.3 in a single month, on a board whose liquid
    sample only begins in August, is EXACTLY the shape of thing that has
    died all day (cf. the August overs cell). It earns a forward shadow
    test on the remaining ~47 games, not a claim. The cheap enabler either
    way: poll the 1H/2H boards alongside KXWNBATOTAL for the rest of the
    season, so October's NBA version inherits the collection.

 Read-only.
===============================================================================
"""
