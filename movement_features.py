"""Everything we can feed a line-movement model, including what was left out.

The first movement model used only: opening total, the score model's disagreement
with it, and the 19 lagged team features. Left unused:

  * rest / travel / streak variables -- built earlier and fed to the *score* model,
    never to the movement model. They do not predict game outcomes beyond the line,
    but the market adjusting for them between open and close is a different question.
  * intermediate quotes -- LINE MOVEMENT #1/#2/#3. These swap between spread and
    total row by row in the source file (a value >100 is a total, |v|<=30 a spread),
    which is why they looked unparseable at first glance.
  * the juice attached to the opening number, which signals which way the book wants
    action before the number itself moves.
  * calendar position and team identity -- public-team effects are a classic driver
    of line movement, distinct from anything about team quality.

Note the intermediate quotes support a *different* strategy: betting at quote k using
movement through k, rather than betting at the open. Both are built here and kept
separate, because the economics differ -- a later entry means a worse number but more
information.
"""

import numpy as np
import pandas as pd

MOVE_COLS = [("LINE \nMOVEMENT #1_H", "LINE \nMOVEMENT #1_R"),
             ("LINE \nMOVEMENT #2_H", "LINE \nMOVEMENT #2_R"),
             ("LINE \nMOVEMENT #3_H", "LINE \nMOVEMENT #3_R")]


def _first_num(s):
    """Parse the leading number from quotes like '-4.5 -15', '215.5o15', '+1 -06'."""
    return pd.to_numeric(
        s.astype(str).str.strip().str.replace("o", " ", regex=False)
         .str.split().str[0], errors="coerce")


def parse_quotes(raw):
    """Recover intermediate total and spread quotes, which swap columns per row."""
    out = {}
    for i, (ch, cr) in enumerate(MOVE_COLS, start=1):
        a, b = _first_num(raw[ch]), _first_num(raw[cr])
        # a value above 100 is a total; a small one is a spread (home perspective)
        tot = np.where(a.abs() > 100, a, np.where(b.abs() > 100, b, np.nan))
        spr = np.where(a.abs() <= 30, a, np.where(b.abs() <= 30, b, np.nan))
        out[f"q{i}_total"] = tot
        out[f"q{i}_spread"] = spr
    return pd.DataFrame(out, index=raw.index)


def _juice(s):
    """Second token of an odds string is the price, e.g. '-4.5 -15' -> -15."""
    t = s.astype(str).str.strip().str.replace("o", " ", regex=False).str.split()
    return pd.to_numeric(t.str[1], errors="coerce")


def market_features(raw):
    """Pre-open and at-open market context."""
    f = pd.DataFrame(index=raw.index)
    f["game_id"] = raw["GAME-ID"]
    f["open_total"] = pd.to_numeric(raw["OPENING TOTAL_H"], errors="coerce")
    f["open_margin"] = -pd.to_numeric(raw["OPENING SPREAD_H"], errors="coerce")
    f["close_total"] = pd.to_numeric(raw["CLOSING TOTAL_H"], errors="coerce")
    f["close_margin"] = -pd.to_numeric(raw["CLOSING SPREAD_H"], errors="coerce")
    f["open_juice"] = _juice(raw["OPENING ODDS_H"])
    f["abs_open_margin"] = f["open_margin"].abs()
    q = parse_quotes(raw)
    for c in q.columns:
        f[c] = q[c].values
    # movement realised by each intermediate quote
    for i in (1, 2, 3):
        f[f"mv{i}_total"] = f[f"q{i}_total"] - f["open_total"]
        f[f"mv{i}_spread"] = f[f"q{i}_spread"] - f["open_margin"]
    return f


def calendar_features(dates, seasons):
    f = pd.DataFrame(index=dates.index)
    f["dow"] = dates.dt.dayofweek.astype(float)
    f["month"] = dates.dt.month.astype(float)
    start = dates.groupby(seasons).transform("min")
    f["days_into_season"] = (dates - start).dt.days.astype(float)
    return f


def team_popularity(panel):
    """Expanding, walk-forward count of games played -- a crude proxy for how much
    public attention a team has drawn so far. Never uses future information."""
    p = panel.sort_values("date")
    return p.groupby("team").cumcount().astype(float)
