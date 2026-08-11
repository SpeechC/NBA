"""Stage 1 screen — NCAAB 2023-24, the only CBB season currently held.

Follows SPORT_SCREENING_BRIEF.md sections 2 and 5. Screens the CLOSING line
only; the opening total is included once, as a contrast, to show what screening
the opener would have told you instead.

⚠ ONE SEASON. Stage 3 (decay) cannot be run. A pooled figure from a single
season is exactly the thing the brief says never to trust, so nothing here can
advance past Stage 1 until more seasons are acquired. The by-month table is a
weak stand-in and is NOT a decay check.
"""
import numpy as np
import pandas as pd

from cbb_load import load
from screen_market import screen, report

GAMES_PER_SEASON = 6123          # observed, this dataset, regular season


def main():
    g = load()
    n_all = len(g)
    g = g.dropna(subset=["close_total", "close_spread", "total_pts"])
    print("=" * 130)
    print("STAGE 1 SCREEN — NCAAB 2023-24 regular season")
    print("=" * 130)
    print(f"games in file: {n_all}   with closing lines: {len(g)}   "
          f"({g.date.min():%Y-%m-%d} to {g.date.max():%Y-%m-%d})")
    print(f"median closing price: totals {g.price_total.median():.0f}, "
          f"sides {g.price_spread.median():.0f}")
    print()

    rows = []
    for price in (-110, -105, -102):
        rows.append(screen(g, "close_total", "total_pts",
                           f"NCAAB totals (close) @ {price}",
                           GAMES_PER_SEASON, price))
        rows.append(screen(g, "zero", "margin_vs_line",
                           f"NCAAB sides  (close) @ {price}",
                           GAMES_PER_SEASON, price))
    o = g.dropna(subset=["open_total"])
    rows.append(screen(o, "open_total", "total_pts",
                       "NCAAB totals (OPEN) @ -110", GAMES_PER_SEASON, -110))

    print(report(rows).to_string(index=False))

    print("\n" + "-" * 130)
    print("Bias by month (NOT a decay check — one season cannot provide one)")
    print("-" * 130)
    d = g.copy()
    d["resid_tot"] = d["total_pts"] - d["close_total"]
    d["month"] = d["date"].dt.to_period("M")
    m = d.groupby("month").agg(
        n=("resid_tot", "size"),
        bias=("resid_tot", "mean"),
        over_pct=("resid_tot", lambda s: 100 * (s > 0).mean()),
    ).round(3)
    m["side_bias"] = d.groupby("month")["margin_vs_line"].mean().round(3)
    m["home_cover_pct"] = (100 * d.assign(c=d.margin_vs_line > 0)
                           .groupby("month")["c"].mean()).round(2)
    print(m.to_string())


if __name__ == "__main__":
    main()
