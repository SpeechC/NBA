"""Stage 1 market screen. Portable to any sport with a line history.

Needs four columns and nothing else:

    date | line | actual | (price, optional -- defaults to -110)

`actual` is whatever the line is quoted against: total points for a totals
market, or margin-plus-spread for a sides market. Everything else is arithmetic.

    edge pp  best_side_% - break_even_%   <-- THE DECISION. Positive = candidate.
    b        mean signed residual (actual - line)
    sigma    sd of that residual
    b/sigma  bias in sd units -- comparable across sports, DIAGNOSTIC ONLY
    z_vig    bias required to break even at the quoted price
    ratio    (b/sigma) / z_vig -- deprecated criterion, see below
    centrl b contribution to `b` from the central 80% of |resid| -- diagnostic
    tail b   contribution from the 20% tails, where extra points pay nothing
    C        tail/total -- REPORT ONLY, not a gate. See central_vs_tail().
    pp/pt    win-rate points bought per point of line movement
    pts nd   central bias, in points, needed to break even from a coin flip
    n_req    games needed to DETECT a bias this size at 80% power
    seasons  n_req / games-per-season -- detection time

`b` is FORECAST bias; `edge pp` is BETTING bias. They are different quantities
and a market can have a large, highly significant amount of the first and none
of the second. `C` is the diagnostic that separates them: it reports how much
of `b` sits in the tails, where extra points pay nothing. A market with a real
bias and C near 1 is economically dead however good its t-statistic looks.
`pp/pt` gives the exchange rate between the two, and `pts needed` turns the
price into a points target you can compare `central b` against directly.

Rank on `edge pp`, never on `ratio`. An earlier version of this tool called a
market exploitable when `ratio > 1.0`. That rule produces false positives: a
binary bet depends on probability mass NEAR THE LINE, not on the mean, and fat
tails (blowouts already going over) inflate `b` without moving a single game
across the number. Measured on NBA totals at -102, `ratio` reads 2.28 while the
empirical best side is 50.38% against a 50.50% break-even -- no edge at all.
Both columns are reported; where they disagree, believe `edge pp`.

Detection time matters as much as edge size. An edge that takes eight seasons
to establish may die before it is confirmed -- the one genuine conditional edge
found in the prior project ran six seasons and then vanished. Detection must
outrun decay.

Screen against the CLOSING line. Screening against the opener measures how
beatable the opener is, which is a different and much less valuable question:
the open-to-close move is largely the market correcting itself, and predicting
it yields CLV without a win rate.

Bias and liquidity run opposite, so pass `limit` whenever you know it. The
honest ranking is `edge pp x limit`, not `edge pp` -- otherwise the top of the
table fills with markets where a $200 bet moves the line.

Usage as a library:

    from screen_market import screen
    screen(df, line_col="close_total", actual_col="total_pts",
           label="MLB totals", games_per_season=2430, price=-110, limit=5000)
"""
import numpy as np
import pandas as pd
from scipy import stats

POWER_K = 7.84          # (1.96 + 0.84)^2, two-sided alpha .05 at 80% power


def z_for_price(price):
    """Bias in sd units required to break even at an American price."""
    p = (-price) / (-price + 100) if price < 0 else 100 / (price + 100)
    return stats.norm.ppf(p), p


def central_vs_tail(resid, q=0.80):
    """Split the mean bias into central and tail contributions.

    A binary bet pays on which side of the line, not by how much, so bias
    living in the tails is worth nothing: an over by 25 pays what an over by 1
    pays. Splits on the q-quantile of |resid| and returns each region's
    contribution to the overall mean.

        C = tail_contribution / total_bias

    ⚠ REPORT C, DO NOT GATE ON IT. It explains why `b` and `edge_pp` disagree;
    it cannot decide anything. Three failures, all measured:

      * No shape-independent threshold. A pure level shift -- the fully
        payoff-relevant case -- gives C = 0.64 on a normal but C = 1.16 on the
        actual CBB residual shape. "C near 1 is dead" is wrong: on a skewed
        residual, 1.16 is what a genuine edge looks like.
      * The denominator explodes. At mean bias ~0, C ran to 1.8e15 on real
        CBB data. Every low-bias market produces garbage.
      * It does not separate cleanly. Genuine +1.0 shift = 1.16, the same
        bias loaded entirely into a 2% tail = 1.56, CBB as observed = 1.10.
        The margins are too tight to threshold.

    `edge_pp` already measures what C proxies for, and measures it correctly.
    Use C to understand a cell, never to accept or reject one.
    """
    r = np.asarray(resid, dtype=float)
    r = r[~np.isnan(r)]
    n = len(r)
    cut = np.quantile(np.abs(r), q)
    central = r[np.abs(r) <= cut].sum() / n
    tail = r[np.abs(r) > cut].sum() / n
    total = r.mean()
    return {"total": total, "central": central, "tail": tail,
            "C": tail / total if total else np.nan, "cut": cut}


def pp_per_point(resid):
    """Win-rate points bought by moving the line one point, measured locally.

    This is the exchange rate between a bias in POINTS and a bias in WIN RATE,
    and it is what tells you whether a given central bias is big enough to
    matter. Averages the two one-point windows either side of the line rather
    than assuming normality (~phi(0)/sigma).

    NCAAB totals 2023-24: 2.24 pp per point, so beating -110 from a coin flip
    needs ~1.06 points of CENTRAL bias, and -105 needs ~0.54.
    """
    r = np.asarray(resid, dtype=float)
    r = r[~np.isnan(r)]
    base = (r > 0).mean()
    down = (r > -1).mean() - base          # mass in (-1, 0]
    up = base - (r > 1).mean()             # mass in (0, 1]
    return 100 * (down + up) / 2


def points_needed(resid, price):
    """Central bias, in points, required to reach break-even from a coin flip."""
    _, p_be = z_for_price(price)
    rate = pp_per_point(resid)
    return (100 * (p_be - 0.5)) / rate if rate else np.inf


def screen(df, line_col, actual_col, label, games_per_season,
           price=-110, date_col="date", drop_push=True, limit=None):
    d = df[[date_col, line_col, actual_col]].dropna()
    d = d.copy()
    d["resid"] = d[actual_col] - d[line_col]
    if drop_push:
        d = d[d["resid"] != 0]
    n = len(d)
    b, sd = d["resid"].mean(), d["resid"].std()
    bs = b / sd
    z, p_be = z_for_price(price)
    se = sd / np.sqrt(n)
    over = (d["resid"] > 0).mean()
    n_req = POWER_K / bs ** 2 if bs else np.inf
    ct = central_vs_tail(d["resid"])
    ppp = pp_per_point(d["resid"])

    # EMPIRICAL edge -- the ground truth. Bet whichever side is ahead.
    side = max(over, 1 - over)
    payout = 100 / abs(price) if price < 0 else price / 100
    roi = side * payout - (1 - side)
    se_w = np.sqrt(side * (1 - side) / n)

    return {
        "market": label, "n": n, "games/season": games_per_season,
        "b": round(b, 3), "sigma": round(sd, 2), "b/sigma": round(bs, 4),
        "t": round(b / se, 2),
        "price": price, "z_vig": round(z, 4),
        # parametric ratio: assumes normality, OVERSTATES the edge (see below)
        "ratio (param)": round(abs(bs) / z, 2),
        # empirical: what actually happened
        "best side %": round(100 * side, 2),
        "break-even %": round(100 * p_be, 2),
        "edge pp": round(100 * (side - p_be), 2),
        "edge t": round((side - p_be) / se_w, 2),
        "ROI %": round(100 * roi, 2),
        # payoff-relevance: is the bias where bets are decided, or in blowouts?
        "central b": round(ct["central"], 3),
        "tail b": round(ct["tail"], 3),
        "C": round(ct["C"], 2),
        "pp/pt": round(ppp, 2),
        "pts needed": round(100 * (p_be - 0.5) / ppp, 2) if ppp else None,
        "n to detect": int(n_req) if np.isfinite(n_req) else None,
        "seasons to detect": round(n_req / games_per_season, 1)
        if np.isfinite(n_req) else None,
        # liquidity. edge you cannot fund is not edge -- see report().
        "limit": limit,
        "edge x limit": round(100 * (side - p_be) * limit, 1)
        if limit is not None else None,
    }


def by_season(df, line_col, actual_col, date_col="date", month_cut=7):
    """Bias per season -- ALWAYS look at this, never trust a pooled figure."""
    d = df[[date_col, line_col, actual_col]].dropna().copy()
    d["resid"] = d[actual_col] - d[line_col]
    d = d[d["resid"] != 0]
    y = pd.to_datetime(d[date_col]).dt.year
    m = pd.to_datetime(d[date_col]).dt.month
    d["season"] = np.where(m >= month_cut, y, y - 1)
    out = d.groupby("season")["resid"].agg(["size", "mean"]).round(3)
    out.columns = ["n", "bias"]
    out["over %"] = (d[d["resid"] > 0].groupby("season").size() /
                     d.groupby("season").size() * 100).round(2)
    return out


def report(rows):
    """Ranked screen table.

    Sorts on `edge x limit` when limits are known for every row, because bias
    and liquidity run opposite and a table ranked on `edge pp` alone puts the
    unfundable markets on top. Falls back to `edge pp` when limits are absent,
    and says so.
    """
    t = pd.DataFrame(rows)
    cols = ["market", "n", "b", "sigma", "b/sigma", "t", "price",
            "ratio (param)", "best side %", "break-even %", "edge pp", "edge t",
            "ROI %", "central b", "tail b", "C", "pp/pt", "pts needed",
            "seasons to detect"]
    if t["limit"].notna().all():
        t = t.sort_values("edge x limit", ascending=False)
        cols += ["limit", "edge x limit"]
        if (t["edge pp"] <= 0).any():
            print("  [report] `edge x limit` orders only the cells with "
                  "edge pp > 0. Rows at or below zero are dead at that price "
                  "regardless of limit — read them as nulls, not as a ranking.")
    else:
        t = t.sort_values("edge pp", ascending=False)
        if t["limit"].notna().any():
            print("  [report] limits known for only some cells — ranking on "
                  "`edge pp`. Fill in the rest to rank on `edge x limit`.")
    return t[cols]


# ---------------------------------------------------------------- NBA demo ---
def _demo():
    """Run the screen on the two NBA markets already in this repo."""
    from prepare_data import CSV, season_label
    raw = pd.read_csv(CSV, low_memory=False)
    raw["season"] = season_label(raw).astype(str)
    d = raw[raw["season"].str.contains("Regular Season", na=False)].copy()
    d["date"] = pd.to_datetime(d["DATE"], errors="coerce")
    d["total_pts"] = d["PTS_H"] + d["PTS_R"]
    d["close_total"] = pd.to_numeric(d["CLOSING TOTAL_H"], errors="coerce")
    d["open_total"] = pd.to_numeric(d["OPENING TOTAL_H"], errors="coerce")
    d["close_spread"] = pd.to_numeric(d["CLOSING SPREAD_H"], errors="coerce")
    d = d[d["close_total"].between(150, 300)].dropna(subset=["date", "total_pts"])
    # sides: positive residual = home covered
    d["margin_vs_line"] = (d["PTS_H"] - d["PTS_R"]) + d["close_spread"]
    d["zero"] = 0.0

    rows = []
    for price in (-110, -105, -102):
        rows.append(screen(d, "close_total", "total_pts",
                           f"NBA totals (close) @ {price}", 1230, price))
        rows.append(screen(d, "zero", "margin_vs_line",
                           f"NBA sides  (close) @ {price}", 1230, price))
    rows.append(screen(d, "open_total", "total_pts",
                       "NBA totals (OPEN) @ -110", 1230, -110))

    print("=" * 124)
    print("STAGE 1 SCREEN — NBA, from data already in this repo")
    print("=" * 124)
    print(report(rows).to_string(index=False))
    print("\n  `ratio (param)` assumes a normal residual and OVERSTATES the edge:")
    print("  it converts the MEAN bias to a win rate, but a binary bet depends on")
    print("  mass near the line, not on the mean. Fat tails -- blowouts that were")
    print("  already going over -- inflate b without moving any game across the")
    print("  number. `edge pp` is the ground truth. Where they disagree, believe")
    print("  the empirical column.")
    print("\nBias by season, NBA totals (decay check — never trust the pooled figure):")
    print(by_season(d, "close_total", "total_pts").to_string())


if __name__ == "__main__":
    _demo()
