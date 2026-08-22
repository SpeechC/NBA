"""STEP 3 — the frozen CrewShock rule priced against the Kalshi ladder.

NOTHING IS TUNED. The threshold is the frozen development Q85 (+0.8682), the
signal is ref_features.csv unchanged, the direction is OVER. This script only
prices an existing rule at a new venue.

POPULATION. 2025-26 regular season only. IST games are excluded because every
piece of frozen CrewShock work excluded them (separate season label), and the
playoffs are excluded because the mechanism is already established NOT to
extend there -- foul propensity survives (+0.635, t=2.76) but FTA conversion
dies (+0.170, t=0.68) and the scoring effect flips sign.

POWER, STATED FIRST. ~238 qualifying games. SE on a win rate at that n is
~3.2pp; establishing the 2.44pp edge needs ~3,292 bets. This season CANNOT
deliver a verdict. It is worth ~1 season of the 14 needed at -110, or ~1 of the
3 needed at the Kalshi maker hurdle. Furthermore 2025-26 triggered M1 and M2
(REFEREE_PROPENSITY_PERSISTENCE_WEAKENED, b_fouls +0.503 against a +0.95..+1.48
prior range), so it is the weakest mechanism season on record.

RUNG CHOICE, pre-specified: the strike NEAREST the book closing total, so the
Kalshi bet is the closest available analogue of the sportsbook bet. The offset
is reported.

VENUES, all on $100 at risk per bet so the P&L is directly comparable:
  book -110     risk 100, win 90.91
  Kalshi taker  buy Yes at the ASK, fee 0.07*p*(1-p)
  Kalshi maker  buy Yes at the BID, fee 25% of the taker fee
                *** assumes a 100% fill at the bid, which is OPTIMISTIC and
                    unverifiable: the candles table is empty, so there is no
                    order-book history to measure fills or adverse selection.
"""
import sqlite3
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

from prepare_data import CSV, season_label

DB = "/mnt/c/NBA2/Kalshi/data/kalshi_nba_totals.sqlite"
THR = 0.8682
FEE_K, MAKER_MULT = 0.07, 0.25


def fee(p, maker=False):
    f = FEE_K * p * (1.0 - p)
    return f * MAKER_MULT if maker else f


def build():
    con = sqlite3.connect(DB)
    k = pd.read_sql("""SELECT event_ticker, game_date, away_team, home_team,
                              floor_strike, pregame_yes_bid, pregame_yes_ask
                       FROM markets WHERE pregame_yes_bid IS NOT NULL""", con)
    for c in ("floor_strike", "pregame_yes_bid", "pregame_yes_ask"):
        k[c] = pd.to_numeric(k[c], errors="coerce")
    k["bid"] = k["pregame_yes_bid"] / 100.0
    k["ask"] = k["pregame_yes_ask"] / 100.0
    k = k[(k["bid"] > 0) | (k["ask"] < 1.0)]
    k["d"] = pd.to_datetime(k["game_date"])

    mp = pd.read_csv("team_mapping.csv").set_index(
        "bigdataball_name")["abbr"].to_dict()
    raw = pd.read_csv(CSV, low_memory=False)
    raw["lbl"] = season_label(raw).astype(str)
    raw["d"] = pd.to_datetime(raw["DATE"], errors="coerce")
    g = raw[raw["lbl"].str.contains("Regular Season", na=False)
            & (raw["d"] >= "2025-10-01")].copy()
    g["gid"] = g["GAME-ID"].astype(str).str.strip()
    g["H"] = g["TEAM_H"].map(mp)
    g["R"] = g["TEAM_R"].map(mp)
    g["actual"] = (pd.to_numeric(g["PTS_H"], errors="coerce")
                   + pd.to_numeric(g["PTS_R"], errors="coerce"))
    g["book"] = pd.to_numeric(g["CLOSING TOTAL_H"], errors="coerce")
    mk = lambda d, a, b: (d.dt.strftime("%Y-%m-%d") + "|"
                          + np.where(a < b, a, b) + "-" + np.where(a < b, b, a))
    g["key"] = mk(g["d"], g["H"], g["R"])
    k["key"] = mk(k["d"], k["home_team"].values, k["away_team"].values)

    f = pd.read_csv("ref_features.csv")
    f["gid"] = f["gid"].astype(str).str.strip()
    g = g.merge(f[["gid", "CrewShock", "pf_rate"]], on="gid", how="inner")
    g = g.dropna(subset=["CrewShock", "actual", "book"])

    # pick the strike nearest the book closing total
    k = k.merge(g[["key", "book"]].drop_duplicates("key"), on="key",
                how="inner")
    k["off"] = (k["floor_strike"] - k["book"]).abs()
    k = k.sort_values(["key", "off", "floor_strike"])
    sel = k.groupby("key", as_index=False).first()
    return g.merge(sel[["key", "floor_strike", "bid", "ask", "off"]],
                   on="key", how="inner")


def main():
    d = build()
    print(f"  {len(d):,} regular-season games with CrewShock and a Kalshi rung")
    print(f"  chosen strike offset from the book total: mean "
          f"{d['off'].mean():.2f}  max {d['off'].max():.2f} points")

    print("\n" + "=" * 96)
    print("THRESHOLD DRIFT on the frozen absolute cutoff (reported, not fixed)")
    print("=" * 96)
    print(f"  CrewShock 2025-26: mean {d['CrewShock'].mean():+.4f}  "
          f"sd {d['CrewShock'].std():.4f}")
    print(f"  qualifying at the frozen +{THR:.4f}: {int((d['CrewShock']>=THR).sum())} "
          f"({100*(d['CrewShock']>=THR).mean():.1f}%)   historical Q85 = 14.8%")

    print("\n" + "=" * 96)
    print("1 — MECHANISM in this sample (is the signal still doing anything?)")
    print("=" * 96)
    z = (d["CrewShock"] - 0.0047) / 0.8233        # per pooled SD, frozen scale
    for col, nm, ref in (("pf_rate", "combined foul rate", "+0.834"),
                         ("actual", "actual total", "+0.813")):
        s = d.dropna(subset=[col])
        A = np.column_stack([np.ones(len(s)), z[s.index]])
        b, *_ = np.linalg.lstsq(A, s[col].values, rcond=None)
        r = s[col].values - A @ b
        se = np.sqrt(np.diag(np.linalg.pinv(A.T @ A)) * (r @ r) / (len(s) - 2))
        print(f"  CrewShock -> {nm:20} {b[1]:+.4f} (t={b[1]/se[1]:+.2f})"
              f"   pooled history {ref}")

    print("\n" + "=" * 96)
    print("2 — IS THE OMISSION PRESENT ON KALSHI TOO?")
    print("=" * 96)
    # Kalshi's implied mean, recovered per game, vs the book, vs the truth
    import kalshi_calib as KC
    m = KC.load()
    u = m[~((m["bid"] <= 0) & (m["ask"] >= 1.0))]
    rows = []
    for ev, g2 in u.groupby("event_ticker"):
        f2 = KC.fit_ladder(g2)
        if f2:
            rows.append({"key": g2["k"].iloc[0], "kmu": f2[0]})
    K = pd.DataFrame(rows)
    dd = d.merge(K, on="key", how="inner")
    zz = (dd["CrewShock"] - 0.0047) / 0.8233
    print(f"  n={len(dd):,}")
    print(f"  {'target':28}{'coef':>10}{'t':>8}{'pooled history':>18}")
    for col, nm, ref in (("actual", "actual total  (c_true)", "+0.922"),
                         ("book", "book closing (c_market)", "+0.043"),
                         ("kmu", "Kalshi implied (c_market)", "n/a")):
        A = np.column_stack([np.ones(len(dd)), zz.values])
        b, *_ = np.linalg.lstsq(A, dd[col].values, rcond=None)
        r = dd[col].values - A @ b
        se = np.sqrt(np.diag(np.linalg.pinv(A.T @ A)) * (r @ r) / (len(dd) - 2))
        print(f"  {nm:28}{b[1]:>+10.4f}{b[1]/se[1]:>8.2f}{ref:>18}")
    print("  -> if Kalshi's coefficient is also ~0, the omission exists at "
          "BOTH venues")

    print("\n" + "=" * 96)
    print("3 — THE FROZEN RULE, PRICED AT THREE VENUES ($100 at risk per bet)")
    print("=" * 96)
    b = d[d["CrewShock"] >= THR].copy()
    b["over"] = (b["actual"] > b["book"]).astype(int)
    b["kwin"] = (b["actual"] > b["floor_strike"]).astype(int)
    n = len(b)
    print(f"  {n} qualifying bets   over rate vs the BOOK line "
          f"{100*b['over'].mean():.2f}%   vs the chosen KALSHI strike "
          f"{100*b['kwin'].mean():.2f}%")
    print(f"  mean residual vs book {(b['actual']-b['book']).mean():+.3f} "
          f"points   (pooled history +1.434)")
    print(f"\n  {'venue':16}{'n':>5}{'win %':>8}{'break-even':>12}"
          f"{'P&L $':>10}{'ROI %':>9}{'z vs BE':>9}")
    # book at -110
    w = int(b["over"].sum())
    pnl = w * 90.909 - (n - w) * 100
    be = 100 * 11 / 21
    wp = 100 * w / n
    print(f"  {'book -110':16}{n:>5}{wp:>8.2f}{be:>12.2f}{pnl:>10,.0f}"
          f"{100*pnl/(100*n):>9.2f}{(wp-be)/(100*np.sqrt(0.25/n)):>9.2f}")
    # kalshi taker and maker
    for lab, price_col, mk_ in (("Kalshi taker", "ask", False),
                                ("Kalshi maker", "bid", True)):
        p = b[price_col].values
        c = p + fee(p, maker=mk_)                    # cost per contract
        ok = (c > 0.02) & (c < 0.98)
        q = b[ok]
        cc = c[ok]
        nq = len(q)
        contracts = 100.0 / cc                       # $100 at risk per bet
        gain = np.where(q["kwin"].values == 1, contracts * (1.0 - cc),
                        -100.0)
        bew = 100 * float(np.mean(cc))
        wpk = 100 * q["kwin"].mean()
        print(f"  {lab:16}{nq:>5}{wpk:>8.2f}{bew:>12.2f}"
              f"{gain.sum():>10,.0f}{100*gain.sum()/(100*nq):>9.2f}"
              f"{(wpk-bew)/(100*np.sqrt(0.25/nq)):>9.2f}")
    print(f"\n  break-even for Kalshi is the mean cost (price + fee) of the "
          f"contracts actually bought")
    print(f"  maker rows assume a 100% fill at the bid -- unverifiable here")

    print("\n" + "=" * 96)
    print("4 — POWER")
    print("=" * 96)
    se = 100 * np.sqrt(0.25 / n)
    print(f"  n={n}   SE on a win rate {se:.2f}pp   detectable at 80% power "
          f"{2.8*se:.2f}pp")
    print(f"  bets to establish a 2.44pp edge: {7.84*0.25/0.0244**2:,.0f}   "
          f"-> this season supplies {n/(7.84*0.25/0.0244**2):.1%} of it")


if __name__ == "__main__":
    main()
