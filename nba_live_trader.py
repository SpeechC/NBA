"""Live Kalshi execution for the three 2026-27 NBA totals strategies.

    CrewShock       OVER-only,   settles vs the CLOSE   -> fill LATE  (near tip)
    PaceGap  (S1)   OVER/UNDER,  settles vs the OPENER  -> fill EARLY
    MOVE_COMBINED   OVER/UNDER,  settles vs the OPENER  -> fill EARLY

*** THIS FILE PLACES REAL ORDERS. ***  It reverses the standing "no capital"
constraint in PREREG_crewshock_forward §1, PREREG_2026_27_PROSPECTIVE and
CREWSHOCK_LIVE_OPS. That reversal is recorded in AMENDMENT_live_trading.md,
including the cost it imposes on the 2026-27 prospective test. Read it first.

=============================================================================
WHY THE THREE STRATEGIES CANNOT SHARE A CLOCK
=============================================================================
Kalshi settles on the ACTUAL total against a fixed strike. A sportsbook wager
settles against a LINE. The programme already measured that a Kalshi ladder's
implied mu IS the closing total, so:

  * MOVE_COMBINED forecasts open->close movement and is graded at the OPENER.
    Once the market HAS moved, its edge is spent. Filling at the close captures
    none of it. It must trade early or not at all.
  * PaceGap likewise settles at the opener.
  * CrewShock is graded at the CLOSE, so a late fill is the faithful one.

Trading all three at one convenient hour would quietly convert two of them into
different strategies with no backtest.

=============================================================================
TRANSLATING A SIGNAL INTO A PRICE -- the step that decides everything
=============================================================================
A raw signal is NOT a points edge. E_pace >= 4.77 does not mean the total is
4.77 points light; the realised hit rate at that threshold is 52.59%, which
inverts to about 1.19 points. Feeding raw signal into a ladder pricer would
manufacture edge on every rung and buy the whole board.

So each strategy's edge is taken from its OWN PUBLISHED HIT RATE, inverted
through the normal at the historical dispersion of (actual - line):

    delta = (hit - 0.5) * SIGMA_REF / phi(0)        SIGMA_REF = 18.244

SIGMA_REF is not a new estimate. It is implied by the mechanism constant this
programme has used throughout -- 1.089 points of line error are needed to beat
-110 -- via 1.089 = (0.52381-0.5)*SIGMA_REF/phi(0). Using the same constant
keeps the live hurdle on the same scale as every null already recorded.

*** THE SPORTSBOOK BAR IS 1.12, NOT 1.089 (revised 2026-09-14). ***
PROJECT_CLOSED.md result 1: measured from the juice actually in the file, only
44% of totals are at -110 and the distribution skews AGAINST the bettor, so the
real hurdle is 1.12 pts. SIGMA_REF is left at 18.244 -- it is the sd of
(actual - line) and does not move with the vig -- but every margin below is
against 1.12:

    crewshock 1.925 pts   clears by 0.805
    move      1.573 pts   clears by 0.453
    pacegap   1.184 pts   clears by 0.064      <-- was 0.095 at the old bar

PaceGap is the marginal strategy and its entire margin is 0.064 pts at a
sportsbook. Resting rather than crossing is what makes it viable at all.
Also carry PROJECT_CLOSED result 2: the closing total is a MEDIAN forecast of a
right-skewed distribution, so a mean bias need not become a win-rate edge. The
deltas above are safe from that because they are derived FROM published hit
rates, not from mean errors -- do not reverse that derivation.

Then, per game:   mu_hat = L_reference + side * delta
where L_reference is that strategy's own settlement line (open or close). The
ladder is priced off mu_hat and the market's own sigma, and we take rungs the
market disagrees with. If the market has already moved past mu_hat the edge
goes negative and nothing trades -- which is the correct behaviour, not a bug.

NOTHING HERE IS FITTED. delta comes from a published table, sigma is read off
the live ladder. No threshold in any frozen model is touched.

=============================================================================
WE REST BIDS, WE DO NOT CROSS. THE MEASURED REASON:
=============================================================================
Probability edge at the at-the-money rung is delta*phi(0)/sigma. Against the
real pregame board (14,471 archived NBA rungs: median spread 2c, p25 1c, p75 3c
in the 35-65c band) the per-contract EV in cents is:

                  edge        TAKE (cross ask)         MAKE (rest at bid)
                    pp     s=1    s=2    s=4        s=1    s=2    s=4
    crewshock     4.27   +2.01  +1.51  +0.51      +3.01  +3.51  +4.51
    move          3.49   +1.23  +0.73  -0.27      +2.23  +2.73  +3.73
    pacegap       2.63   +0.37  -0.13  -1.13      +1.37  +1.87  +2.87

**Taking destroys two of the three strategies.** PaceGap is negative-EV as a
taker at the MEDIAN spread; MOVE_COMBINED dies past 3c. Resting a bid earns the
half-spread instead of paying it, which is worth 1c-4c per contract and turns a
wider book from a penalty into a premium. This is the same conclusion the
programme reached on Kalshi microstructure generally -- taking is dead, making
is not -- now quantified for NBA totals specifically.

*** TAKE IS THE DEFAULT, AND THE PARAGRAPH ABOVE IS NOT ACTIONABLE (2026-10-07).
*** WE ARE NOT APPROVED FOR MARKET MAKING ON KALSHI. Resting is the better
business on every number this programme has produced, and that is irrelevant:
liquidity provision is not a permitted activity here, so the maker edge above
cannot be collected. `--make` still exists to reproduce historical maker
figures, but it must never be armed.

Two further reasons the maker number was never as good as it looked, both
independent of approval:
  * NBA totals trade IN-PLAY. A resting pregame bid is a free option sold to
    whoever is watching the game -- it fills precisely when the score has moved
    against it. That is why cancel_stale() exists and runs every 30 minutes
    near tip; it is a position limit, not tidying.
  * The maker projection assumed instant fills with no adverse selection and no
    fill-rate haircut on a synthetic uniform 2c book.

Measured at the ASK on real books, with the empirical OT-skewed outcome
distribution: +$6.35/season at 1 contract over ~306 trades, ROI +4.35%. The
superseded maker figure was $19.70. See TAKER_ECONOMICS_2026_27.md.

Fee is charged on entry only; settlement is free. Fee at 50c on a 25-lot is
1.76c/contract. For reference, -110 costs 2.381pp; crossing a 2c Kalshi board
costs 2.76pp (worse), resting on it costs 0.76pp (much better).

=============================================================================
UNFILLED ORDERS MUST BE CANCELLED BEFORE TIP
=============================================================================
NBA totals markets trade IN-PLAY. A resting pregame bid left open is a free
option sold to whoever is watching the game. `cancel_stale()` runs as its own
cron entry; it is a position limit, not housekeeping.
"""
import os, sys, csv, json, argparse, datetime as dt
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Where the SIGNAL PRODUCERS write. This module may be installed anywhere (a
# copy lives under /mnt/d/Kalshi/nba); the logs it reads do not move with it.
PROJECT_DIR = os.environ.get("NBA_PROJECT_DIR",
                             "/home/dpope/projects/nba_entropy_replication")
if PROJECT_DIR not in sys.path:
    sys.path.append(PROJECT_DIR)
import nba_kalshi as NK

# ---------------------------------------------------------------- calibration
SIGMA_REF = 18.244          # sd(actual - line); implied by the 1.089 constant
PHI0      = 0.3989422804

def delta_points(hit):
    """Published hit rate -> points of line error. The ONLY model input."""
    return (hit - 0.5) * SIGMA_REF / PHI0

STRATS = {
    # hit      = the honest forward number from MONITOR_SEASON_PNL.md, never the
    #            pooled/in-sample one where they differ (CrewShock: holdout).
    # line     = which line the backtest settles against -> when we must fill.
    # sides    = directions the backtest actually took. CrewShock is OVER-only,
    #            so it never needs the unverified NO path and can arm first.
    # prereg   = part of the frozen 2026-27 prospective test. These claim a
    #            contested game ahead of anything discretionary; see run().
    "crewshock": dict(hit=0.5421, line="close", sides=("OVER",), prereg=True,
                      window=("15:00", "23:59"), source="crewshock_live_log.csv"),
    "pacegap":   dict(hit=0.5259, line="open",  sides=("OVER", "UNDER"), prereg=True,
                      window=("06:00", "12:00"), source="~/data/nba_2026_27_prospective_log.csv"),
    "move":      dict(hit=0.5344, line="open",  sides=("OVER", "UNDER"), prereg=True,
                      window=("06:00", "12:00"), source="recommendations/move_combined_{date}.csv"),
    # ---- DISCRETIONARY, NOT PREREGISTERED --------------------------------
    # final7: bet OVER on EVERY game in the last 7 days of the regular season.
    # No per-game signal at all -- the trigger is the calendar.
    #
    # 55.29%, NOT the 56.93% headline. The window was chosen by LOSO on the
    # same data that produced the 56.93%, so that figure is selection-biased;
    # 55.29% is the honest out-of-sample number under that selection. This is
    # the same discipline CrewShock gets (holdout 54.21%, not pooled 54.82%).
    #
    # PROJECT_CLOSED.md keeps it "alive, small, not worth capital today":
    # 407 bets, 56.51%, +$3,157, 5/6 seasons, z = +1.65 -- NOT significant,
    # ~$395/season, and the base rate is against it (the six best-looking
    # rules traded forward lost -$28,820). 2020-21 lost 10.16% when April was
    # not the end of the season. The test that would promote or kill it --
    # is the bias carried by games with an ELIMINATED team? -- HAS NOT RUN.
    "final7":    dict(hit=0.5529, line="close", sides=("OVER",), prereg=False,
                      window=("15:00", "23:59"), source="crewshock_live_log.csv"),
}
# Last 7 days of the regular season, inclusive. Override for a schedule change.
# SEASON GATE. Every strategy here is validated on REGULAR-SEASON games only.
# Preseason boards are listed under the same KXNBATOTAL tickers and are
# indistinguishable to the trader, so without this gate an armed cron would
# trade preseason games on an unvalidated rule. Discovered 2026-10-07, when the
# cron was armed on 2026-10-07 and 5 preseason events were open.
SEASON_START = os.environ.get("NBA_SEASON_START", "2026-10-20")
FINAL7_LAST_REGULAR = os.environ.get("NBA_LAST_REGULAR", "2027-04-11")
FINAL7_DAYS         = int(os.environ.get("NBA_FINAL7_DAYS", "7"))
# days_left <= FINAL7_DAYS, so 7 means EIGHT calendar days. That is the
# validated definition (monitor_season_pnl.py:64), not an off-by-one.
for _k, _v in STRATS.items():
    _v["delta"] = delta_points(_v["hit"])

# ---------------------------------------------------------------- risk limits
DRY_RUN              = True     # --arm is the ONLY way to flip this
NO_SIDE_VERIFIED     = os.environ.get("NBA_NO_SIDE_VERIFIED") == "1"
# 1c, deliberately BELOW the uncertainty in delta itself -- CrewShock's own ROI
# CI is [-0.36%, +9.67%] and MOVE's [-2.40%, +6.45%], so delta is uncertain by
# roughly its own size. A larger MIN_EDGE would not be a risk control, it would
# just be a filter tuned until something traded. It is here to reject rungs with
# NO edge, not to certify the ones that pass.
# WHICH RUNG. "nearline" buys the rung closest to the strategy's own reference
# line; "maxedge" buys the highest modelled edge.
#
# NEARLINE IS THE DEFAULT BECAUSE IT IS THE BET THAT WAS BACKTESTED. The
# eight-season records (crewshock +4.66%, final7 +8.68%) are records of betting
# THE LINE; nothing in them speaks to a strike 1.9 points away. Measured on
# 2025-26 boards, nearest-line reproduces the backtest hit rate to within
# 0.42pp (crewshock, 50.00 vs 50.42) and 0.00pp (final7, 55.07 vs 55.07), while
# max-edge sat +1.58/+1.93 pts off the line and lost 4.2pp and 8.7pp of hit
# rate -- for final7 the difference between +4.97% and -1.61% ROI.
#
# max-edge's only support was a 400,000-board simulation that drew truth and
# market from the SAME normal with the SAME sigma, so the pricing model was
# correct by construction and maximising modelled EV had to win; it was also
# priced at bid+1c, a maker price we are not approved to use. See
# TRADER_VS_BACKTEST.md.
RUNG_RULE            = os.environ.get("NBA_RUNG_RULE", "nearline")
MIN_EDGE             = 0.01
# LIVE TRADING TEST SIZE = 1 CONTRACT.
# The point of the first live season is to prove the plumbing -- auth, signal
# intake, rung selection, resting fills, cancels, settlement attribution --
# not to make money. At 1 contract a full slate risks about $8 and every
# failure mode still surfaces exactly once.
#
# SIZE CHANGES THE FEE. Kalshi charges ceil(0.07*p*(1-p)*n) rounded UP to
# $0.001 on the WHOLE order, so a 1-lot at 50c pays 1.8c/contract where a
# 25-lot pays 1.752c. `candidates()` passes the real order size to fee(), so
# the edge shown is the edge at the size actually being sent -- a 1-contract
# test is charged ~0.05c/contract more than the calibration assumed, which
# matters most for pacegap (margin 0.064 pts).
#
# Raise with the environment, no code edit: NBA_MAX_CONTRACTS=25
MAX_CONTRACTS_GAME   = int(os.environ.get("NBA_MAX_CONTRACTS", "1"))
MAX_CONTRACTS_DAY    = int(os.environ.get("NBA_MAX_CONTRACTS_DAY",
                                          str(max(30, MAX_CONTRACTS_GAME * 12))))
MAX_NOTIONAL_DAY     = float(os.environ.get("NBA_MAX_NOTIONAL_DAY",
                                            str(max(30.0, MAX_CONTRACTS_DAY * 1.0))))
MIN_PRICE, MAX_PRICE = 0.12, 0.88   # sigma is unidentified in the tails
MAX_SIGMA_DIST       = 1.1      # |K - mu| <= 1.1 sigma; LADDER_ASSUMPTION's
                                # validated span (normal ratio 0.996 inside it)
MIN_BOOK_SIZE        = 5        # TAKE only -- a resting bid adds liquidity and
                                # is not constrained by what is already there
IMPROVE_FROM         = 3        # spread in cents at/above which we post bid+1c
                                # to jump the queue; below it we simply join
KILL_SWITCH          = os.path.expanduser("~/data/NBA_TRADING_HALT")
FILLS                = os.path.expanduser("~/data/nba_kalshi_fills.csv")
# Rung-choice sidecar. SEPARATE FILE ON PURPOSE: _log() writes FILL_COLS with
# writeheader() only when the file is new, so adding columns to the live fills
# CSV would misalign every subsequent row against the existing header. This is
# also read by nothing in the trading path.
RUNGLOG              = os.path.expanduser("~/data/nba_rung_choice.csv")
RUNG_COLS = ["ts_utc","mode","strategy","game","event","dir","ref_line","mu_hat",
             "mu_mkt","sigma_mkt","n_cands","n_gated","rule","ticker","strike",
             "offset_pts","price","p_model","edge","is_traded","rules_agree",
             "would_gate"]
FILL_COLS = ["ts_utc","mode","strategy","game","event","ticker","strike","side",
             "count","limit_price","p_model","p_market","edge","mu_hat","mu_mkt",
             "sigma_mkt","ref_line","http","order_id","client_order_id","note"]


# ------------------------------------------------------------ ladder inversion
TICK_SLACK = 0.005     # +/-0.5c: KXNBATOTAL is linear_cent, so a quote cannot
                       # express a probability more finely than half a tick
_MU_GRID = np.arange(-15.0, 15.001, 0.25)      # offset from the strike mean
_SG_GRID = np.arange(9.0, 30.001, 0.25)


def fit_ladder_mid(rungs):
    """*** DO NOT USE. MID-BASED. Retained only so the error stays legible. ***

    This was the live anchor until 2026-10-07. It regressed Phi^-1(1 - p_MID) on
    strike, and because signals() passes ref=None for crewshock and final7,
    `ref = mu_mkt` meant the ANCHOR OF THE ENTIRE BET for both close-settled
    strategies was a midpoint -- not merely the drift guard.

    A midpoint is not a price anyone can trade. Measured against the
    bounds-identified anchor on the 951 fittable 2025-26 ladders it runs
    +0.058 pts high on average with an sd of 0.360 pts, which at 2.187 pp of
    win rate per point is 0.79 pp of probability injected by a number that does
    not exist in the book.
    """
    from scipy.stats import norm
    xs, ys = [], []
    for r in rungs:
        b, a = r.get("yes_bid"), r.get("yes_ask")
        if not b or not a:
            continue
        p = 0.5 * (b + a)
        if not (0.08 < p < 0.92):
            continue
        xs.append(r["strike"]); ys.append(norm.ppf(1.0 - p))
    if len(xs) < 4:
        return None, None
    m, c = np.polyfit(np.array(xs), np.array(ys), 1)
    if m <= 1e-6:
        return None, None
    sigma, mu = 1.0 / m, -c / m
    if not (8.0 < sigma < 40.0) or not (150.0 < mu < 300.0):
        return None, None
    return float(mu), float(sigma)


def fit_ladder(rungs):
    """Recover (mu, sigma) from the EXECUTABLE BOOK. No midpoint anywhere.

    The book is an interval, not a point: a rung with bid b and ask a says only
    that the market's probability lies in [b, a]. So the estimator is the set of
    (mu, sigma) whose implied survival curve sits inside EVERY rung's quote,

        b_j - slack  <=  1 - Phi((K_j - mu)/sigma)  <=  a_j + slack

    with slack = half a tick, because a 1c grid cannot express a probability
    more finely than that. Closed form per rung, so no mu grid is needed in the
    feasible case: the constraint is

        mu  in  [K_j - sigma*Phi^-1(1-b_j),  K_j - sigma*Phi^-1(1-a_j)]

    and a sigma is feasible iff those intervals intersect. The estimate is the
    centre of the feasible region.

    WHEN NOTHING IS FEASIBLE -- and that is about a third of real ladders, since
    no single normal fits inside the quotes -- it falls back to the (mu, sigma)
    MINIMISING THE HINGE LOSS, which is zero inside each quote and quadratic in
    the violation outside it. That keeps the estimator always defined. Returning
    (None, None) there would silently drop a third of all signals for a
    numerical reason, which is a worse failure than an approximate anchor.

    Returns (mu, sigma). Use fit_ladder_detail() when the feasibility flag
    matters -- it reports whether the hinge-loss fallback was needed.
    """
    mu, sg, _ = fit_ladder_detail(rungs)
    return mu, sg


def fit_ladder_detail(rungs):
    """(mu, sigma, feasible). See fit_ladder(). feasible is False when the
    hinge-loss fallback was used, i.e. no normal fits inside the quotes."""
    from scipy.stats import norm
    K, LO, UP = [], [], []
    for r in rungs:
        b, a = r.get("yes_bid"), r.get("yes_ask")
        if b is None or a is None or a <= b:
            continue
        K.append(r["strike"])
        LO.append(min(max(b - TICK_SLACK, 1e-9), 1 - 1e-9))
        UP.append(min(max(a + TICK_SLACK, 1e-9), 1 - 1e-9))
    if len(K) < 4:
        return None, None, False
    K = np.asarray(K, float)
    zL = norm.ppf(1.0 - np.asarray(LO)); zU = norm.ppf(1.0 - np.asarray(UP))
    zL = np.where(np.isfinite(zL), zL, 1e9); zU = np.where(np.isfinite(zU), zU, -1e9)

    lo = (K[None, :] - _SG_GRID[:, None] * zL[None, :]).max(axis=1)
    hi = (K[None, :] - _SG_GRID[:, None] * zU[None, :]).min(axis=1)
    ok = np.where(lo <= hi + 1e-9)[0]
    if len(ok):
        i = ok[len(ok) // 2]
        mu, sg = float((lo[i] + hi[i]) / 2.0), float(_SG_GRID[i])
        if 150.0 < mu < 300.0:
            return mu, sg, True

    mus = K.mean() + _MU_GRID
    z = (K[None, None, :] - mus[None, :, None]) / _SG_GRID[:, None, None]
    p = 1.0 - norm.cdf(z)
    loss = (np.maximum(0.0, np.asarray(LO)[None, None, :] - p) ** 2
            + np.maximum(0.0, p - np.asarray(UP)[None, None, :]) ** 2).sum(axis=2)
    si, mi = np.unravel_index(np.argmin(loss), loss.shape)
    mu, sg = float(mus[mi]), float(_SG_GRID[si])
    if not (150.0 < mu < 300.0) or not (8.0 < sg < 40.0):
        return None, None, False
    return mu, sg, False


def _quote(r, side):
    """(bid, ask) for the side we want to BUY, in dollars.

    A NO buy consumes the YES BID book, so the NO ask is 1 - yes_bid and the NO
    bid is 1 - yes_ask. Getting this backwards prices every UNDER inside-out,
    and the mirrored side is systematically thinner than the quoted one -- a
    correction already on record from the weather work.
    """
    if side == "YES":
        return r.get("yes_bid"), r.get("yes_ask")
    yb, ya = r.get("yes_bid"), r.get("yes_ask")
    return (None if ya is None else round(1.0 - ya, 2),
            None if yb is None else round(1.0 - yb, 2))


def candidates(rungs, mu_hat, sigma, allowed_sides, take=True):
    """Rungs worth buying, in OUR strategy's direction only.

    Direction is a hard gate, not a preference. Letting the pricer take the
    opposite side of a rung because it looks cheap would be a new model with no
    backtest -- the strategy said OVER, so we buy OVER.

    TAKE (default): lift the ask and eat the half-spread. Edge is measured
    against the price we actually pay, which is the only number we are allowed
    to act on -- we are not approved for market making.
    MAKE (--make):  post at the bid, or bid+1c when the spread is wide enough to
    pay for jumping the queue. Retained to reproduce historical maker figures.
    NEVER ARM IT.
    """
    from scipy.stats import norm
    out = []
    for r in rungs:
        K = r["strike"]
        if abs(K - mu_hat) > MAX_SIGMA_DIST * sigma:
            continue                                    # outside the validated span
        p_over = float(1.0 - norm.cdf((K - mu_hat) / sigma))
        for dirn, side in (("OVER", "YES"), ("UNDER", "NO")):
            if dirn not in allowed_sides:
                continue
            bid, ask = _quote(r, side)
            if bid is None or ask is None or ask <= bid:
                continue
            spread_c = round((ask - bid) * 100)
            rng = r.get("ranges") or [(0.0, 1.0, 0.01)]
            tick = NK.tick_at(rng, bid)
            if take:
                px, sz = ask, (r.get("yes_ask_size") if side == "YES"
                               else r.get("yes_bid_size")) or 0
                px = NK.snap(px, rng, up=True)       # never post below the ask
            else:
                # improve by ONE TICK, not one cent: on a sub-cent grid those
                # differ by 10x and the cent version would surrender queue
                # position it did not need to pay for
                px = bid + (tick if spread_c >= IMPROVE_FROM else 0.0)
                px = min(NK.snap(px, rng), NK.snap(ask - tick, rng))
                sz = MAX_CONTRACTS_GAME      # we ADD liquidity; the book does not cap us
            if px <= 0:
                continue
            p = p_over if side == "YES" else 1.0 - p_over
            # Fee is charged on the WHOLE order and rounds to 0.001, so it must
            # be amortised over the size we actually intend to send. Charging the
            # single-contract ceil-to-the-cent would overstate it by 0.25c -- 18%
            # of PaceGap's edge.
            n = max(1, min(int(sz), MAX_CONTRACTS_GAME))
            out.append(dict(ticker=r["ticker"], strike=K, side=side, dir=dirn,
                            price=px, size=sz, p_model=p, spread_c=spread_c,
                            edge=p - px - NK.fee(px, n) / n, take=take))
    return sorted(out, key=lambda d: -d["edge"])


def gate(c, state):
    """Every reason to refuse. Returns None to allow, else the refusal string."""
    if c["edge"] < MIN_EDGE:                 return f"edge {c['edge']:+.3f} < {MIN_EDGE}"
    if not (MIN_PRICE <= c["price"] <= MAX_PRICE):
                                             return f"price {c['price']:.2f} outside band"
    if c["take"] and c["size"] < MIN_BOOK_SIZE:
                                             return f"size {c['size']:.0f} < {MIN_BOOK_SIZE}"
    if c["side"] == "NO" and not NO_SIDE_VERIFIED:
        return "NO-side schema unverified (set NBA_NO_SIDE_VERIFIED=1 after a demo fill)"
    if state["day_contracts"] >= MAX_CONTRACTS_DAY:      return "daily contract cap"
    if state["day_notional"]  >= MAX_NOTIONAL_DAY:       return "daily notional cap"
    return None


def size_for(c, state):
    """Contracts to take. Capped by the book, the game, the day, and the wallet."""
    n = min(int(c["size"]), MAX_CONTRACTS_GAME - state["game_contracts"],
            MAX_CONTRACTS_DAY - state["day_contracts"])
    afford = int((MAX_NOTIONAL_DAY - state["day_notional"]) / max(c["price"], 0.01))
    return max(0, min(n, afford))


# --------------------------------------------------------------- signal intake
def _read_csv(path):
    """Read a signal file, resolving relative paths against PROJECT_DIR.

    NOT against the working directory. The signal producers write into the
    project; this module may be installed elsewhere (a copy lives under
    /mnt/d/Kalshi/nba) and cron sets no useful cwd. Resolving against cwd would
    make every source silently absent -- and an absent source reads as "no
    signals today", which is indistinguishable from a quiet slate and would
    never raise. Override with NBA_PROJECT_DIR.
    """
    path = os.path.expanduser(path)
    if not os.path.isabs(path):
        path = os.path.join(PROJECT_DIR, path)
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return list(csv.DictReader(f))


def signals(day):
    """[(strategy, away, home, side, ref_line_or_None)] for `day`.

    Every strategy is read from the file IT ALREADY WRITES. This module computes
    no signal of its own -- if it did, the thing being traded would no longer be
    the thing that was backtested.
    """
    out = []
    # --- CrewShock: fires -> OVER. ref line is the CLOSE, unknown until tip, so
    #     the market's own mu stands in for it (that is what the close IS).
    for r in _read_csv(STRATS["crewshock"]["source"]):
        if str(r.get("date","" ))[:10] != day:              continue
        if str(r.get("action","")).strip() != "LOG_OVER":   continue
        out.append(dict(strategy="crewshock", away=r["away"], home=r["home"],
                        dir="OVER", ref=None, signal=float(r["CrewShock"])))
    # --- PaceGap: bet_flag on the immutable prospective row, settles at open.
    for r in _read_csv(STRATS["pacegap"]["source"]):
        if str(r.get("date",""))[:10] != day or r.get("bet_flag") != "1":
            continue
        s = int(r["side"])
        if s == 0:                                          continue
        out.append(dict(strategy="pacegap", away=r["TEAM_R"], home=r["TEAM_H"],
                        dir=("OVER" if s > 0 else "UNDER"),
                        ref=float(r["open_total"]), signal=float(r["E_pace"])))
    # --- MOVE_COMBINED: today's recommendation file, settles at open (ot_open).
    for r in _read_csv(STRATS["move"]["source"].format(date=day)):
        if not str(r.get("action","")).startswith("BET"):   continue
        out.append(dict(strategy="move", away=r["away"], home=r["home"],
                        dir=str(r["side"]).upper(), ref=float(r["ot_open"]),
                        signal=float(r["m"])))
    # --- final7: EVERY game in the window, OVER. The trigger is the calendar,
    #     so there is no signal file -- the slate comes from the CrewShock log,
    #     which lists one row per game regardless of whether CrewShock fired.
    #     That also means final7 is only available once assignments have posted,
    #     which is correct: it settles at the CLOSE and belongs to the late run.
    if in_final7_window(day):
        seen = set()
        for r in _read_csv(STRATS["final7"]["source"]):
            if str(r.get("date",""))[:10] != day:           continue
            k = (r["away"], r["home"])
            if k in seen:                                   continue
            seen.add(k)
            out.append(dict(strategy="final7", away=r["away"], home=r["home"],
                            dir="OVER", ref=None, signal=1.0))
    return out


def in_final7_window(day):
    """Is `day` inside final7's window?

    *** THE COMPARISON IS `<=`, NOT `<`, AND THAT IS NOT A STYLE CHOICE. ***
    The validated rule is monitor_season_pnl.py line 64:

        days_left = max(date within the Regular Season label) - date
        final7    = days_left <= 7

    which spans EIGHT calendar days, days_left 0..7. This function used
    `(last - d).days < FINAL7_DAYS` with FINAL7_DAYS=7, i.e. days_left 0..6 --
    SEVEN days. That off-by-one dropped the earliest day of the window and bet
    451 games across 2017-2025 where the validated rule bets 527, **14.4%
    fewer**, so the live rule was not the rule the 55.29% was measured on.

    Reconciliation is exact: `days_left <= 7` on the Regular Season label,
    excluding pushes, reproduces the published per-season counts
    62/62/68/63/67/69/67/69 = 527 on all eight seasons. (Pushes are a
    sportsbook no-action and cannot occur on Kalshi, where every strike is .5.)

    FINAL7_LAST_REGULAR MUST BE THE LAST REGULAR-SEASON DATE, not the play-in
    end. `DATASET_H` labels "Play-In" separately from "Playoffs", and treating
    play-in games as regular season moved the 2025-26 anchor from 2026-04-12 to
    2026-04-17 and shifted the whole window.

    Inclusive of the last day. 2020-21 is the reason this is a hard window and
    not "April": that season ran into May and the rule lost 10.16% when the
    calendar assumption broke.
    """
    try:
        last = dt.date.fromisoformat(FINAL7_LAST_REGULAR)
        d = dt.date.fromisoformat(str(day)[:10])
    except ValueError:
        return False
    return 0 <= (last - d).days <= FINAL7_DAYS      # <= : see docstring


def _abbr():
    """bigdataball name -> abbr. Kalshi uses the SAME 30 codes (verified against
    1,324 archived events), so no second mapping exists to drift."""
    m = {}
    for r in _read_csv("team_mapping.csv"):
        m[r["bigdataball_name"].strip()] = r["abbr"].strip()
    for a in set(m.values()):
        m[a] = a                       # already-abbreviated inputs pass through
    return m


# ------------------------------------------------------------------- execution
def _decline(s, game, ev, note, **extra):
    """A row for a signal we did NOT trade, timestamped like any other.

    Declines carry a ts_utc because the dashboard filters on it: an untimestamped
    decline is invisible, and the decline counts are the only place a mistimed
    cron entry shows up. A late PaceGap run declines its whole slate on the
    stale-opener guard -- correctly, and otherwise silently.
    """
    r = dict(ts_utc=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z"),
             strategy=s["strategy"], game=game, event=ev, note=note)
    r.update(extra)
    return r


def _log_rungs(rows):
    """Append the rung-choice sidecar. REPORTING ONLY -- never consulted by
    candidates(), gate() or run(), so it cannot alter what is traded."""
    if not rows:
        return
    new = not os.path.exists(RUNGLOG)
    os.makedirs(os.path.dirname(RUNGLOG), exist_ok=True)
    with open(RUNGLOG, "a", newline="") as f:
        w = csv.DictWriter(f, RUNG_COLS)
        if new:
            w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in RUNG_COLS})


def _rung_choice_rows(s, game, ev, ref, mu_hat, mu_mkt, sig_mkt, cands, state, mode):
    """Both candidate rung rules for one signal, for later settlement.

    WHY THIS EXISTS. The trader buys the MAX-EDGE rung. That rule's advantage was
    measured in maker framing on synthetic boards where the pricing model was
    correct by construction (maker_figure_provenance.py draws truth and market
    from the same normal with the same sigma), so maximising modelled EV had to
    win. On real 2025-26 books as a taker it did WORSE than simply buying the
    rung nearest the line -- crewshock -7.89% vs -4.73%, final7 -1.81% vs
    +5.96% -- but the paired test over one season is not significant (t +0.79
    and +1.16). Logging both choices settles it out of sample at zero cost.

    The counterfactual is NOT traded. gate() is evaluated against a COPY of the
    cap state so no budget is consumed by the rung that is only recorded.
    """
    st = dict(state)
    gated = [c for c in cands if gate(c, st) is None]
    if not gated:
        return []
    maxedge = gated[0]                                   # cands is sorted by -edge
    nearline = min(gated, key=lambda c: abs(c["strike"] - ref))
    # THIRD RULE, and testing is why it is here. `nearline` is the nearest rung
    # AMONG THOSE PASSING MIN_EDGE, and on a ladder where the at-the-line rung
    # fails that gate it falls back to something far away -- a synthetic check
    # put it +3.50 pts out. The variant that actually performed best in
    # RUNG_SELECTION_TAKER.md was nearest-line with the gate BYPASSED
    # ("nearest-line, always": crewshock -4.67%, final7 +4.97%), which is also
    # the faithful translation of a sportsbook strategy that always bets the
    # line. Log it too; `would_gate` records whether it was tradeable.
    inband = [c for c in cands if MIN_PRICE <= c["price"] <= MAX_PRICE]
    nearline_all = (min(inband, key=lambda c: abs(c["strike"] - ref))
                    if inband else None)
    ts = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    agree = int(maxedge["ticker"] == nearline["ticker"])
    out = []
    trio = [("maxedge", maxedge), ("nearline", nearline)]
    if nearline_all is not None:
        trio.append(("nearline_all", nearline_all))
    for rule, c in trio:
        out.append(dict(ts_utc=ts, mode=mode, strategy=s["strategy"], game=game,
                        event=ev, dir=s["dir"], ref_line=ref,
                        mu_hat=round(mu_hat, 2), mu_mkt=round(mu_mkt, 2),
                        sigma_mkt=round(sig_mkt, 2), n_cands=len(cands),
                        n_gated=len(gated), rule=rule, ticker=c["ticker"],
                        strike=c["strike"], offset_pts=round(c["strike"] - ref, 2),
                        price=c["price"], p_model=round(c["p_model"], 4),
                        edge=round(c["edge"], 4),
                        is_traded=int(rule == RUNG_RULE), rules_agree=agree,
                        would_gate=int(gate(c, dict(state)) is None)))
    return out


def _log(rows):
    new = not os.path.exists(FILLS)
    os.makedirs(os.path.dirname(FILLS), exist_ok=True)
    with open(FILLS, "a", newline="") as f:
        w = csv.DictWriter(f, FILL_COLS)
        if new: w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in FILL_COLS})


def run(day, arm=False, demo=False, only=None, take=True, verbose=True):
    if os.path.exists(KILL_SWITCH):
        print(f"HALT  kill switch present: {KILL_SWITCH}")
        return 2
    live = arm and not demo
    # SEASON GATE -- before anything else, so it cannot be bypassed by an early
    # return. Every strategy is validated on REGULAR-SEASON games only, and
    # preseason boards carry the same KXNBATOTAL tickers, so an armed cron would
    # otherwise trade them on an unvalidated rule.
    if live:
        try:
            if dt.date.fromisoformat(str(day)[:10]) < dt.date.fromisoformat(SEASON_START):
                print(f"REFUSED: {day} is before the regular season opens "
                      f"({SEASON_START}).\n  Every strategy here is validated on "
                      f"REGULAR-SEASON games only and preseason boards carry the "
                      f"same tickers.\n  Dry runs are fine -- drop --arm. Override "
                      f"deliberately with NBA_SEASON_START.")
                return 1
        except ValueError:
            print("REFUSED: cannot parse the run date or NBA_SEASON_START")
            return 1
    mode = ("LIVE" if live else ("DEMO" if demo else "DRY")) + ("/take" if take else "/make")
    k = NK.NBAKalshi(demo=demo)
    code, who = k.whoami()
    if code != 200:
        print(f"FAIL auth: {who}")
        return 1
    print(f"mode={mode}  base={k.c.base_url}  balance={who.get('balance')}")

    ab = _abbr()
    sigs = [s for s in signals(day) if only in (None, s["strategy"])]
    if not sigs:
        print(f"no signals for {day}")
        return 0
    # PREREGISTERED FIRST, then highest measured edge. Both keys matter.
    #
    # Ranking on delta alone would be wrong here. final7's honest 55.29%
    # inverts to 2.419 pts, ABOVE CrewShock's 1.925, so a pure edge sort would
    # let it claim all 73 games where the two overlap -- handing contested
    # games to the least-validated rule in the book. final7's window was chosen
    # by searching this same data and its promoting test has not been run;
    # CrewShock's number is a holdout. A larger point estimate from a weaker
    # design is not a better claim.
    #
    # So: the frozen prospective test is served first and is never displaced by
    # a discretionary addition. Within a tier, rank by what was measured.
    sigs.sort(key=lambda s: (not STRATS[s["strategy"]].get("prereg", False),
                             -STRATS[s["strategy"]]["delta"]))

    # Kalshi is the authority on which events exist; we match into its listing
    # rather than trusting a ticker we built ourselves.
    board = {e["event_ticker"]: e for e in k.open_events()}
    state = dict(day_contracts=0, day_notional=0.0)
    rows, placed, claimed = [], 0, {}
    rung_rows = []

    for s in sigs:
        a, h = ab.get(s["away"], s["away"]), ab.get(s["home"], s["home"])
        ev = NK.event_ticker(day, a, h)
        game = f"{a}@{h}"
        if ev not in board:
            rows.append(_decline(s, game, ev, "no Kalshi event"))
            if verbose: print(f"  {s['strategy']:<10} {game:<9} -- no Kalshi event {ev}")
            continue
        # ONE POSITION PER GAME, across all three strategies. They are not
        # independent -- PaceGap and MOVE_COMBINED both key off the opener and
        # both carry pace/efficiency state -- so stacking them would size
        # correlated bets as if they were independent and put 3x the intended
        # limit on one game. Each backtest is a single wager per game; there is
        # no measured result for the sum of three.
        if ev in claimed:
            rows.append(_decline(s, game, ev, f"already held by {claimed[ev]}"))
            if verbose:
                print(f"  {s['strategy']:<10} {game:<9} -- already held by {claimed[ev]}")
            continue

        rungs = k.ladder(ev)
        mu_mkt, sig_mkt = fit_ladder(rungs)
        if mu_mkt is None:
            rows.append(_decline(s, game, ev, "ladder not invertible"))
            if verbose: print(f"  {s['strategy']:<10} {game:<9} -- ladder not invertible")
            continue

        cfg = STRATS[s["strategy"]]
        # CrewShock's reference IS the close, and the ladder's mu is the market's
        # close. For the open-settled pair the captured opener is the reference,
        # and if the market has since moved past mu_hat the edge is gone.
        ref = s["ref"] if s["ref"] is not None else mu_mkt
        signed = cfg["delta"] if s["dir"] == "OVER" else -cfg["delta"]
        mu_hat = ref + signed

        # STALE-OPENER GUARD. A market that has moved AGAINST us by more than our
        # whole measured edge makes the opener a worse reference than the current
        # price -- and taking the trade anyway would show a LARGER edge precisely
        # because our reference is stale. That is a bet that the market's move was
        # wrong, and this programme measured the opposite: the market moves
        # +0.544 pts/sd on injury news (t=+16.16) and the impulse-response study
        # found no residual book error at any horizon. We have no result for that
        # regime, so we decline it rather than price it.
        drift = mu_mkt - ref
        against = -drift if s["dir"] == "OVER" else drift
        if against > abs(cfg["delta"]):
            rows.append(_decline(s, game, ev,
                                 f"stale opener: moved {against:+.2f} vs {abs(cfg['delta']):.2f} edge",
                                 mu_mkt=round(mu_mkt, 2), ref_line=ref))
            if verbose:
                print(f"  {s['strategy']:<10} {game:<9} {s['dir']:<5} -- SKIP, market "
                      f"moved {against:+.2f} pts against a {abs(cfg['delta']):.2f} pt edge "
                      f"(ref {ref:.1f}, mkt {mu_mkt:.1f})")
            continue

        state["game_contracts"] = 0
        cands = candidates(rungs, mu_hat, sig_mkt, (s["dir"],), take=take)
        # REPORTING ONLY: record both rung rules before anything is placed, so a
        # dry run accumulates the comparison too. Does not touch `cands`, the
        # cap state, or the placement loop below.
        rung_rows += _rung_choice_rows(s, game, ev, ref, mu_hat, mu_mkt,
                                       sig_mkt, cands, state, mode)
        if verbose:
            print(f"  {s['strategy']:<10} {game:<9} {s['dir']:<5} "
                  f"ref {ref:6.1f}  mu_hat {mu_hat:6.2f}  mkt {mu_mkt:6.2f}"
                  f"/{sig_mkt:4.1f}  drift {mu_mkt-ref:+5.2f}")
        # RUNG SELECTION. Under "nearline" exactly ONE rung is considered -- the
        # one nearest the reference line -- and if it fails the gate the game is
        # DECLINED rather than substituted with a farther strike. Substituting
        # would quietly reintroduce the thing this rule exists to avoid: the
        # backtest bets the line or it does not bet.
        if RUNG_RULE == "nearline":
            _inband = [c for c in cands
                       if MIN_PRICE <= c["price"] <= MAX_PRICE]
            tryme = ([min(_inband, key=lambda c: abs(c["strike"] - ref))]
                     if _inband else [])
        else:
            tryme = cands                      # maxedge: cands is sorted by -edge

        took = False
        for c in tryme:
            why = gate(c, state)
            n = 0 if why else size_for(c, state)
            if why is None and n < 1:
                why = "no room under caps"
            if why:
                if verbose and c["edge"] >= MIN_EDGE:
                    print(f"      skip {c['ticker'][-4:]:>5} {c['side']:<3} "
                          f"{c['price']:.2f} edge {c['edge']:+.3f}  [{why}]")
                continue
            http, resp = None, {}
            if live or demo:
                fn = k.buy_yes if c["side"] == "YES" else k.buy_no
                http, resp = fn(c["ticker"], n, c["price"], tag=s["strategy"])
                ok = http == 201
            else:
                ok = True
            if ok:
                state["day_contracts"] += n; state["game_contracts"] += n
                state["day_notional"] += n * c["price"]; placed += 1; took = True
                claimed[ev] = s["strategy"]
            print(f"      {'PLACE' if ok else 'REJECT'} {c['side']:<3} {n:>3} @ "
                  f"{c['price']:.2f}  K={c['strike']:.1f}  sp {c['spread_c']}c"
                  f"  p_model {c['p_model']:.3f}  edge {c['edge']:+.3f}"
                  + ("" if ok else f"  http={http} {resp.get('_hint','')}"))
            rows.append(dict(ts_utc=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z"),
                mode=mode, strategy=s["strategy"], game=game, event=ev,
                ticker=c["ticker"], strike=c["strike"], side=c["side"], count=n,
                limit_price=c["price"], p_model=round(c["p_model"],4),
                p_market=round(c["price"],4), edge=round(c["edge"],4),
                mu_hat=round(mu_hat,2), mu_mkt=round(mu_mkt,2),
                sigma_mkt=round(sig_mkt,2), ref_line=ref, http=http,
                order_id=(resp.get("order") or {}).get("order_id",""),
                client_order_id=resp.get("_client_order_id",""),
                note="" if ok else json.dumps(resp)[:160]))
            break          # ONE rung per game per strategy: the backtest is one
                           # wager per game, and laddering would lever it silently
        if not took and verbose and not cands:
            print("      no rung inside the validated span")

    _log(rows)
    _log_rungs(rung_rows)
    print(f"\n{mode}: {placed} order(s), {state['day_contracts']} contracts, "
          f"${state['day_notional']:.2f} premium.  log -> {FILLS}")
    if rung_rows:
        _n = len({(r["event"], r["strategy"]) for r in rung_rows})
        _ag = len({(r["event"], r["strategy"]) for r in rung_rows if r["rules_agree"]})
        print(f"rung-choice sidecar: {_n} signal(s), maxedge==nearline on "
              f"{_ag}/{_n}  ->  {RUNGLOG}")
    if not live and not demo:
        print("DRY RUN -- nothing was sent. Add --arm to trade.")
    return 0


def cancel_stale(arm=False, demo=False, minutes_to_tip=20):
    """Pull every resting NBA order whose game tips within `minutes_to_tip`.

    THIS IS A POSITION LIMIT. NBA totals keep trading in-play, so a pregame bid
    that survives the jump ball fills only when the score has already moved
    against it -- the worst fills of the night, selected for. Run it on its own
    cron entry, not as a tail of the placement run: if placement crashes the
    cancels still have to happen.

    Cancels only orders this system placed (client_order_id carries the
    strategy tag), so a manual position is never touched.
    """
    k = NK.NBAKalshi(demo=demo)
    code, _ = k.whoami()
    if code != 200:
        print("FAIL auth"); return 1
    tags = tuple(STRATS) + ("verify",)
    now = dt.datetime.now(dt.timezone.utc)
    n_cancel, n_seen = 0, 0
    for o in k.resting_orders():
        coid = o.get("client_order_id") or ""
        if not any(f"-{t}-" in coid for t in tags):
            continue
        n_seen += 1
        ticker = o.get("ticker", "")
        close = o.get("close_time") or o.get("expiration_time")
        due = True
        if close:
            try:
                t = dt.datetime.fromisoformat(str(close).replace("Z", "+00:00"))
                due = (t - now).total_seconds() <= minutes_to_tip * 60
            except Exception:
                due = True          # unparseable timestamp -> cancel, never hold
        if not due:
            continue
        if arm or demo:
            http, resp = k.cancel(o["order_id"])
            ok = http in (200, 204)
        else:
            http, ok = None, True
        n_cancel += int(ok)
        print(f"  {'CANCEL' if ok else 'FAIL  '} {ticker:<32} "
              f"{o.get('remaining_count', '?')} left  http={http}")
    print(f"{n_cancel}/{n_seen} of our resting orders cancelled"
          + ("" if (arm or demo) else "   DRY RUN -- add --arm"))
    return 0


def verify_no_side(arm=False, demo=False):
    """Prove the NO-side schema with ONE contract before any UNDER goes live.

    *** THIS COULD NEVER PASS BEFORE 2026-10-07. ***  It gated on
    `r.get("no_ask")`, but NBAKalshi.ladder() returned only the YES side, so
    that key was ALWAYS None, the branch never fired, and the function fell
    through to "no suitable NO quote found; retry when a slate is up" -- a
    message that reads like a quiet market rather than a bug, which is exactly
    why it stayed unresolved for weeks. ladder() now returns no_bid/no_ask from
    the exchange and mirrors the sizes. Do not re-introduce a NO-side read that
    depends on a key the ladder does not actually produce.

    Order of operations also changed: SELECT and REPORT the probe target first,
    from a read-only production call, and place an order only when --arm is
    given. Previously a failed demo auth returned before anything was inspected,
    so a run told you nothing at all.

    This is the single unproven call in the stack: buy_yes has placed real
    orders, buy_no has not. Until this prints PASS, gate() refuses every UNDER,
    which silently disables two thirds of PaceGap and MOVE_COMBINED rather than
    guessing at a schema with money behind it.

    DEMO NEEDS ITS OWN API KEY. Kalshi's demo environment does not accept
    production credentials, so `--verify-no-side` alone may return 401 without
    having tested anything -- which looks like a schema failure and is not. If
    you have no demo key, run it with `--arm` to probe PRODUCTION with ONE
    contract at a mid-book price: worst case is about a dollar, and unlike the
    demo it proves the exact path the trader will use. Any resulting position is
    reported below so it can be closed.
    """
    k = NK.NBAKalshi(demo=demo)
    code, who = k.whoami()
    print(f"auth {code} base={k.c.base_url} balance={who.get('balance')}")
    if code != 200:
        print("  auth failed -- nothing inspected." + ("\n  Kalshi demo needs a "
              "SEPARATE key; drop --demo to read production." if demo else ""))
        return 1

    # ---- select the probe target (READ ONLY) -----------------------------
    target, scanned, complement_bad = None, 0, 0
    for ev in list(k.open_events())[:6]:
        for r in k.ladder(ev["event_ticker"]):
            scanned += 1
            if not r.get("no_complement_ok"):
                complement_bad += 1
            na, sz = r.get("no_ask"), r.get("no_ask_size") or 0
            # mid-book so the probe is cheap and the fee is not the whole cost.
            # Pick the DEEPEST qualifying rung, not the first: a size-1 rung can
            # be taken between the preview and the order, and a probe that fails
            # for want of size would read as a schema failure when it is a race.
            if na and 0.2 < na < 0.8 and sz >= 1:
                if target is None or sz > (target.get("no_ask_size") or 0):
                    target = r
    print(f"scanned {scanned} rungs across {min(6, len(k.open_events()))} open events; "
          f"complement identity failed on {complement_bad}")
    if complement_bad:
        print("  WARNING: no_bid == 1-yes_ask / no_ask == 1-yes_bid does NOT hold on "
              "some rungs.\n  _quote() DERIVES the NO side from that identity -- "
              "investigate before arming UNDER.")
    if target is None:
        print("no suitable mid-book NO quote (0.20-0.80 with size >= 1) in the open "
              "slate.\n  This is now a real market condition, not the old bug.")
        return 1
    print(f"probe target: {target['ticker']}  NO ask {target['no_ask']:.2f}  "
          f"size {target['no_ask_size']:.0f}  (YES {target['yes_bid']:.2f}/"
          f"{target['yes_ask']:.2f})")

    if not arm:
        print(f"\nPREVIEW ONLY -- no order placed. Re-run with --arm to buy 1 "
              f"contract\nat {target['no_ask']:.2f} (~${target['no_ask']:.2f} at risk) "
              f"and prove the schema.")
        return 1

    # ---- place exactly one contract --------------------------------------
    # SHARD CHECK BEFORE SPENDING. Kalshi shards its exchange and funds do not
    # cross; NBA is on shard 3 while this account's balance sits on shard 0. An
    # order sent anyway returns 404 insufficient_shard_balance, which the first
    # version of this function reported as "side='ask' is not the NO schema" --
    # a flatly wrong conclusion from an account-routing error.
    bal = k.shard_balance()
    idx = k.series_shard()
    if idx is not None and bal:
        have = bal.get(int(idx), 0.0)
        print(f"shard check: {NK.SERIES} is on exchange_index {idx}; "
              f"balance there ${have:.2f}  (all shards: "
              + ", ".join(f"{i}=${v:.2f}" for i, v in sorted(bal.items())) + ")")
        if have < float(target["no_ask"]) + 0.05:
            print(f"  ABORT -- ${have:.2f} on shard {idx} cannot fund a "
                  f"${target['no_ask']:.2f} contract.\n"
                  f"  THIS IS NOT A SCHEMA PROBLEM. Transfer funds to exchange_index "
                  f"{idx} first;\n  intra-exchange transfers are active. The NO side "
                  f"stays UNVERIFIED either way.")
            return 1

    # SAME SEASON GATE AS run(). This path POSTs a real order and was not gated
    # when run() was, which is how two preseason orders went out on 2026-10-07
    # while "testing the gate". Any code path that can place an order needs it,
    # and a gate must be verified by reading the file -- never by firing an
    # order to see what happens.
    try:
        if dt.date.today() < dt.date.fromisoformat(SEASON_START):
            print(f"REFUSED: today is before the regular season opens "
                  f"({SEASON_START}); no live order on a preseason board.\n"
                  f"  Override deliberately with NBA_SEASON_START.")
            return 1
    except ValueError:
        print("REFUSED: cannot parse NBA_SEASON_START")
        return 1

    print(f"ARMED: buying 1 NO @ {target['no_ask']:.2f}")
    http, resp = k.buy_no(target["ticker"], 1, target["no_ask"], tag="verify")
    print(f"  http={http}  {json.dumps(resp)[:400]}")
    code = ((resp.get("error") or {}).get("code") or "") if isinstance(resp, dict) else ""
    if http != 201 and ("shard" in str(code) or "shard" in json.dumps(resp)):
        print("  INCONCLUSIVE -- account/routing error, NOT a verdict on the NO\n"
              "  schema. Funds are on the wrong exchange shard. Fix that and re-run.")
        return 1
    if http == 201:
        print("  PASS -- side='ask' buys NO. Set NBA_NO_SIDE_VERIFIED=1.")
        if not demo:
            print(f"  NOTE: 1 REAL contract of {target['ticker']} may now be held. "
                  f"Close it or let it settle.")
        return 0
    print("  FAIL -- side='ask' is not the NO schema; do NOT arm UNDER.\n"
          "  PaceGap and MOVE_COMBINED will trade OVER only; CrewShock is unaffected.")
    return 1


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--date", default=dt.date.today().isoformat())
    p.add_argument("--strategy", choices=list(STRATS), default=None)
    p.add_argument("--arm", action="store_true", help="place real orders")
    p.add_argument("--demo", action="store_true", help="Kalshi demo (fake money)")
    p.add_argument("--take", action="store_true",
                   help="(default, kept for compatibility) cross the spread")
    p.add_argument("--make", action="store_true",
                   help="NOT APPROVED -- rest at the bid. Analysis only, never arm.")
    p.add_argument("--cancel", action="store_true",
                   help="pull resting orders on games near tip (own cron entry)")
    p.add_argument("--verify-no-side", action="store_true")
    p.add_argument("--fund-shard", type=float, metavar="DOLLARS",
                   help="preallocate collateral on the NBA exchange shard "
                        "(dry run unless --arm)")
    a = p.parse_args()
    if a.fund_shard is not None:
        _k = NK.NBAKalshi()
        _idx = _k.series_shard()
        if _idx is None:
            sys.exit("no open NBA event -- cannot read the target exchange_index")
        _bal = _k.shard_balance()
        print("balance by shard: " + ", ".join(f"{i}=${v:.2f}" for i, v in sorted(_bal.items())))
        print(f"{NK.SERIES} trades on exchange_index {_idx}")
        if _bal.get(0, 0.0) < a.fund_shard:
            sys.exit(f"shard 0 holds ${_bal.get(0,0.0):.2f}; cannot send ${a.fund_shard:.2f}")
        code, out = _k.transfer_shard(a.fund_shard, _idx, src_shard=0, dry=not a.arm)
        if code is None:
            print("Re-run with --arm to send it.")
            sys.exit(1)
        print(f"  http={code}  {json.dumps(out)[:300]}")
        if code == 200:
            print("  balance after: " + ", ".join(
                f"{i}=${v:.2f}" for i, v in sorted(_k.shard_balance().items())))
        sys.exit(0 if code == 200 else 1)

    if a.verify_no_side:
        sys.exit(verify_no_side(arm=a.arm, demo=a.demo))
    if a.cancel:
        sys.exit(cancel_stale(arm=a.arm, demo=a.demo))
    take = not a.make
    if a.make and a.arm:
        sys.exit("REFUSED: --make --arm is market making, which is not approved.")
    sys.exit(run(a.date, arm=a.arm, demo=a.demo, only=a.strategy, take=take))
