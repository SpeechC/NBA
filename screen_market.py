"""Stage 1 market screen. Portable to any sport with a line history.

Needs four columns and nothing else:

    date | line | actual | (price, optional -- defaults to -110)

`actual` is whatever the line is quoted against: total points for a totals
market, or margin-plus-spread for a sides market. Everything else is arithmetic.

    b        mean signed residual (actual - line)
    sigma    sd of that residual
    b/sigma  bias in sd units -- THE comparable quantity across sports
    z_vig    bias required to break even at the quoted price
    ratio    (b/sigma) / z_vig      > 1.0 means exploitable
    n_req    games needed to DETECT a bias this size at 80% power
    seasons  n_req / games-per-season -- detection time

The last two matter as much as `ratio`. An edge that takes eight seasons to
establish may die before it is confirmed: the mismatch bias in FINDINGS_LATE.md
section 14 lasted six seasons. Detection must outrun decay.

Usage as a library:

    from screen_market import screen
    screen(df, line_col="close_total", actual_col="total_pts",
           label="MLB totals", games_per_season=2430, price=-110)
"""
import numpy as np
import pandas as pd
from scipy import stats

POWER_K = 7.84          # (1.96 + 0.84)^2, two-sided alpha .05 at 80% power


def z_for_price(price):
    """Bias in sd units required to break even at an American price."""
    p = (-price) / (-price + 100) if price < 0 else 100 / (price + 100)
    return stats.norm.ppf(p), p


def screen(df, line_col, actual_col, label, games_per_season,
           price=-110, date_col="date", drop_push=True):
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
        "n to detect": int(n_req) if np.isfinite(n_req) else None,
        "seasons to detect": round(n_req / games_per_season, 1)
        if np.isfinite(n_req) else None,
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
    t = pd.DataFrame(rows).sort_values("edge pp", ascending=False)
    cols = ["market", "n", "b", "sigma", "b/sigma", "t", "price", "z_vig",
            "ratio (param)", "best side %", "break-even %", "edge pp", "edge t",
            "ROI %", "seasons to detect"]
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
