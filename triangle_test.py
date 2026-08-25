"""
===============================================================================
 #3 — THE TRIANGLE: moneyline vs spread vs total, on boards that qualify
===============================================================================
 Pre-filter first (the standing discipline): of every WNBA/NBA per-game board,
 only three are tight enough to trade -- GAME (moneyline) 1.0c, SPREAD 1.0c,
 TOTAL 1.0c. Every half/quarter spread and winner board runs 9-65c and the
 dedicated overtime board is 36c, so they are excluded on cost, not on
 interest.

 Two tests, in increasing order of assumption:

 T-A  MONEYLINE SUMS TO ONE. Basketball has no ties, so
        P(home wins) + P(away wins) = 1
      exactly. This needs NO model, NO outcome and NO clock -- it is pure
      arithmetic on two simultaneous quotes. A sum below 1 is a risk-free buy
      of both sides; above 1, a risk-free sell. Costed properly: you cross
      two spreads and pay two fees, so the violation must exceed that.

 T-B  MONEYLINE vs SPREAD@1.5. The ladder's lowest strike is 1.5, NOT 0.5,
      so the spread board prices P(margin>=2) while the moneyline prices
      P(margin>=1). Their difference must equal P(margin == 1) exactly.
      (Interpolating to k=0 is wrong twice: np.interp CLAMPS below the range,
      and the lowest strike varies 1.5-12.5 by game, manufacturing a large
      spurious bias. An earlier pass made both errors.)

 RESULTS (2026-08-25), both leagues:

 T-A  MONEYLINE IS PERFECTLY ARBITRAGED. Sum of the two sides: WNBA mean
      1.0012 (vig 0.12c), NBA 1.0027 (vig 0.27c), median exactly 1.0000.
      Tradeable violations: 1 of 147,972 WNBA quotes and 11 of 893,479 NBA
      quotes -- 0.001%, median edge 0.5-1.5c. On over a million quotes there
      is no two-sided arbitrage. This board is machine-tight.

 T-B  A REAL, CROSS-LEAGUE MISPRICING THAT IS STRUCTURALLY UNTRADEABLE.
      Implied P(margin==1) vs realised:
        WNBA  0.0263 implied vs 0.0530 real -> underpriced by 2.67c
        NBA   0.0236 implied vs 0.0409 real -> underpriced by 1.72c
      The market prices a one-point win at roughly HALF its true frequency,
      consistently in both leagues. But the synthetic requires BUY YES
      moneyline + BUY NO spread@1.5 -- two ~50c legs to manufacture a ~5c
      tail contract -- and Kalshi's fee 0.07p(1-p) is MAXIMISED at p=0.5:
        WNBA  fees 2.72c + spreads 1.60c vs a 2.67c edge -> NET -1.65c
        NBA   fees 2.81c + spreads 7.42c vs a 1.72c edge -> NET -8.51c
      The fee structure itself defeats it. This is the cleanest example yet
      of the standing law: the mispricing is real, and the cost of touching
      it is larger.

 Read-only.
===============================================================================
"""
import os
import sqlite3
import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wnba_anchor_audit as A                                # noqa: E402

WNBA_DB = "/mnt/c/NBA2/Kalshi/data/kalshi_wnba_halves.sqlite"
NBA_DB = "/mnt/c/NBA2/Kalshi/data/kalshi_nba_triangle.sqlite"
FEE = 1.75


def load(db, like, want_sub=False):
    if not os.path.exists(db):
        return pd.DataFrame()
    con = sqlite3.connect(db)
    cols = "ticker, event_ticker e, end_period_ts ts, yes_bid_close b, yes_ask_close a"
    mk = pd.read_sql(
        f"select ticker, floor_strike, yes_sub_title from markets "
        f"where ticker like '{like}'", con)
    cd = pd.read_sql(f"select {cols} from candles where period_interval=1 "
                     f"and ticker like '{like}'", con)
    con.close()
    if not len(cd):
        return pd.DataFrame()
    d = cd.dropna(subset=["b", "a"]).merge(mk, on="ticker", how="left")
    d["mid"] = (d.b + d.a) / 200.0
    d["sp"] = d.a - d.b
    d["key"] = d.e.str.split("-").str[1]
    return d


def test_a(game, tag):
    """Moneyline two-sided sum. Pure arithmetic, no outcomes needed.
    NB: spreads are stored in CENTS; every cost must be divided by 100 before
    comparing to a probability deviation."""
    print(f"\n T-A  MONEYLINE SUMS TO ONE — {tag}")
    if not len(game):
        print("   no data")
        return
    g = game.dropna(subset=["mid"])
    piv = g.groupby(["key", "ts"]).agg(n=("mid", "size"), s=("mid", "sum"),
                                       sp=("sp", "sum")).reset_index()
    piv = piv[piv.n == 2]
    if not len(piv):
        print("   no simultaneous two-sided quotes")
        return
    piv["dev"] = piv.s - 1.0
    # buy BOTH sides at the ask: total cost = sum(mid) + sum(spread)/2 + fees
    cost = piv.sp / 200.0 + 2 * FEE / 100.0        # cents -> probability
    piv["tradeable"] = piv.dev.abs() > cost
    print(f"   {len(piv):,} simultaneous two-sided quotes across "
          f"{piv.key.nunique()} games")
    print(f"   sum of the two sides: mean {piv.s.mean():.4f}  median "
          f"{piv.s.median():.4f}  sd {piv.s.std():.4f}")
    print(f"   implied vig: {(piv.s.mean()-1)*100:+.2f}c per contract pair")
    print(f"   |deviation| > two-leg cost in {piv.tradeable.mean():.3%} of "
          f"quotes ({int(piv.tradeable.sum()):,})")
    if piv.tradeable.any():
        t = piv[piv.tradeable]
        print(f"     of those: median edge "
              f"{(t.dev.abs()-(t.sp/200.0+2*FEE/100.0)).median()*100:.2f}c"
              f", across {t.key.nunique()} games")


def test_b(game, spread, tag, p1=None):
    """Spread ladder interpolated to k=0 vs the moneyline."""
    print(f"\n T-B  SPREAD LADDER vs MONEYLINE — {tag}")
    if not len(game) or not len(spread):
        print("   missing a board")
        return
    sp = spread.dropna(subset=["floor_strike", "mid"]).copy()
    sp["k"] = sp.floor_strike.astype(float)
    # sub_title names the team the spread is quoted FOR; use one side only
    sp["team"] = (sp.yes_sub_title.astype(str)
                  .str.extract(r'^(.*?)\s+wins\s', expand=False).str.strip())
    # The ladder's LOWEST strike is 1.5, not 0.5 -- there is no "wins by over
    # 0.5" market. So the spread board prices P(margin >= 2) while the
    # moneyline prices P(margin >= 1). They must differ by EXACTLY
    # P(margin == 1). Interpolating to k=0 is wrong twice over: np.interp
    # CLAMPS below the range (returning the lowest strike's price) and the
    # lowest strike varies by game (1.5 to 12.5+), which manufactures a large
    # spurious negative bias.
    ps = sp[np.isclose(sp.k, 1.5)][["key", "ts", "team", "mid"]].copy()
    ps = ps.rename(columns={"mid": "p_spread"})
    if not len(ps):
        print("   spread ladders never bracket 0")
        return
    gm = game.dropna(subset=["yes_sub_title"]).copy()
    gm["team"] = gm.yes_sub_title.astype(str).str.strip()
    j = ps.merge(gm[["key", "ts", "team", "mid", "sp"]], on=["key", "ts", "team"],
                 how="inner")
    if not len(j):
        print("   no simultaneous spread+moneyline snapshots for the same team")
        return
    j["gap"] = j.mid - j.p_spread          # must equal P(margin == 1)
    print(f"   {len(j):,} matched snapshots across {j.key.nunique()} games "
          f"(spread strike 1.5 only)")
    print(f"   moneyline - spread@1.5 = implied P(win by exactly 1): "
          f"mean {j.gap.mean():+.4f}  median {j.gap.median():+.4f}  "
          f"sd {j.gap.std():.4f}")
    if p1 is not None:
        print(f"   REALISED P(margin == 1) = {p1:.4f}")
        j["dev"] = j.gap - p1
        cost = j.sp / 200.0 + 2 * FEE / 100.0
        print(f"   mispricing = implied - realised: mean {j.dev.mean():+.4f}  "
              f"|dev|>2c in {(j.dev.abs()>0.02).mean():.1%}")
        print(f"   beats the two-leg cost ({cost.median()*100:.1f}c) in "
              f"{(j.dev.abs()>cost).mean():.2%} of snapshots")


def p1_for(tag):
    """Realised P(|margin| == 1) -- what the moneyline/spread gap must equal."""
    try:
        if tag == "WNBA":
            import wnba_reconcile as R
            b = pd.read_csv(R.BREF)
            m = (b.a_final - b.h_final).abs()
        else:
            from prepare_data import CSV, season_label
            r = pd.read_csv(CSV, low_memory=False)
            r["season"] = season_label(r).astype(str)
            r = r[r["season"].str.contains("Regular Season", na=False)]
            m = (pd.to_numeric(r.PTS_H, errors="coerce")
                 - pd.to_numeric(r.PTS_R, errors="coerce")).abs()
        m = m.dropna()
        return float((m == 1).mean())
    except Exception:
        return None


def main():
    for tag, db, pre in (("WNBA", WNBA_DB, "KXWNBA"), ("NBA", NBA_DB, "KXNBA")):
        print("=" * 68)
        print(tag)
        print("=" * 68)
        game = load(db, f"{pre}GAME-%")
        spread = load(db, f"{pre}SPREAD-%")
        print(f"  boards: GAME {game.key.nunique() if len(game) else 0} events, "
              f"SPREAD {spread.key.nunique() if len(spread) else 0} events")
        test_a(game, tag)
        test_b(game, spread, tag, p1_for(tag))


if __name__ == "__main__":
    main()
