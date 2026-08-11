"""Load the BigDataBall CBB team-box workbook into one row per GAME.

The workbook is two rows per game (Home / Road). Lines are quoted from the
HOME side, so the game-level frame is built on the home row and the road row
supplies only the opponent's points.

Produces the four columns `screen_market.screen` wants, plus the real price:

    date | close_total | total_pts        <- totals market
    date | zero        | margin_vs_line   <- sides market (resid already signed)
    price_total, price_spread             <- parsed from the CLOSING ODDS cells

⚠ The CLOSING ODDS cell quotes ONE SIDE ONLY. A game's two rows carry one
spread quote and one total quote, but *which row* holds which varies — it is
not Home=spread / Road=total. So the parsed price tells you what the over cost,
or what one team's spread cost, and says nothing about the opposite side. Do not
feed it to `screen()` as if it priced both sides: `screen()` bets whichever side
won more often, which is frequently the side that was not quoted. Screen at
fixed prices and use `price_total` / `price_spread` only to establish what
prices this market actually trades at.
"""
import re
import numpy as np
import pandas as pd

XLSX = "/mnt/c/NBA/Data/2023-2024_CBB_Box_Score_Team-Stats.xlsx"
SHEET = "NCAAB-2023-24-TEAM"

# "o139.5 -106" / "u143.5 -108" / "-30.5 -110" / "+4000"
_PRICE = re.compile(r"([+-]\d{3,})\s*$")


def _price(cell):
    """Trailing American price in a CLOSING ODDS cell; NaN if absent."""
    if not isinstance(cell, str):
        return np.nan
    m = _PRICE.search(cell.strip())
    return float(m.group(1)) if m else np.nan


def _market(cell):
    """Which market a CLOSING ODDS cell quotes: 'total', 'spread', or NaN."""
    if not isinstance(cell, str):
        return np.nan
    s = cell.strip()
    if s.startswith(("o", "u")):
        return "total"
    if s.startswith(("-", "+")):
        return "spread"
    return np.nan


def _side(cell):
    """Which side of the total was quoted: 'over' / 'under' / NaN."""
    if not isinstance(cell, str):
        return np.nan
    s = cell.strip()
    return {"o": "over", "u": "under"}.get(s[:1], np.nan)


def load(path=XLSX, sheet=SHEET, regular_season_only=True):
    d = pd.read_excel(path, sheet_name=sheet)
    d.columns = [re.sub(r"\s+", " ", str(c)).strip() for c in d.columns]

    if regular_season_only:
        d = d[d["BIGDATABALL DATASET"].str.contains("Regular Season", na=False)]

    for c in ("CLOSING SPREAD", "CLOSING TOTAL", "OPENING TOTAL",
              "OPENING SPREAD", "PTS"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["odds_price"] = d["CLOSING ODDS"].map(_price)
    d["odds_market"] = d["CLOSING ODDS"].map(_market)
    d["odds_side"] = d["CLOSING ODDS"].map(_side)

    # one quote per market per game, taken from whichever row carries it
    q = d.dropna(subset=["odds_market"])
    tot = (q[q.odds_market == "total"]
           .drop_duplicates("GAME-ID")
           .set_index("GAME-ID")[["odds_price", "odds_side"]]
           .rename(columns={"odds_price": "price_total",
                            "odds_side": "quoted_side_total"}))
    spr = (q[q.odds_market == "spread"]
           .drop_duplicates("GAME-ID")
           .set_index("GAME-ID")[["odds_price", "VENUE"]]
           .rename(columns={"odds_price": "price_spread",
                            "VENUE": "quoted_side_spread"}))

    home = d[d["VENUE"] == "Home"]
    road = d[d["VENUE"] == "Road"]
    g = home.merge(road[["GAME-ID", "PTS", "CONFERENCE", "TEAM"]],
                   on="GAME-ID", suffixes=("_h", "_r"), validate="1:1")
    g = g.merge(tot, left_on="GAME-ID", right_index=True, how="left")
    g = g.merge(spr, left_on="GAME-ID", right_index=True, how="left")

    g = g.rename(columns={"DATE": "date",
                          "CLOSING TOTAL": "close_total",
                          "OPENING TOTAL": "open_total",
                          "CLOSING SPREAD": "close_spread",
                          "CONFERENCE_h": "conf_h", "CONFERENCE_r": "conf_r"})
    g["date"] = pd.to_datetime(g["date"], errors="coerce")
    g["total_pts"] = g["PTS_h"] + g["PTS_r"]
    # sides, home perspective: >0 means the home side covered
    g["margin_vs_line"] = (g["PTS_h"] - g["PTS_r"]) + g["close_spread"]
    g["zero"] = 0.0

    cols = ["GAME-ID", "date", "TEAM_h", "TEAM_r", "conf_h", "conf_r",
            "ASSOCIATION & DIVISION", "close_total", "open_total",
            "close_spread", "total_pts", "margin_vs_line", "zero",
            "price_total", "quoted_side_total",
            "price_spread", "quoted_side_spread", "CLOSING MONEYLINE"]
    return g[cols]


if __name__ == "__main__":
    g = load()
    print(f"games: {len(g)}   dates: {g.date.min():%Y-%m-%d} .. {g.date.max():%Y-%m-%d}")
    print(f"conferences: {g.conf_h.nunique()}")
    print(f"with closing total: {g.close_total.notna().sum()}")
    print(f"with closing spread: {g.close_spread.notna().sum()}")
    print()
    for c in ("price_total", "price_spread"):
        s = g[c].dropna()
        print(f"{c}: n={len(s)}  median={s.median():.0f}  "
              f"mean={s.mean():.1f}  IQR=({s.quantile(.25):.0f}, {s.quantile(.75):.0f})")
    print()
    print("quoted side, totals:")
    print(g["quoted_side_total"].value_counts(dropna=False).to_string())
    print()
    print("price_total distribution:")
    print(g["price_total"].value_counts().head(10).to_string())
