"""On CrewShock and final-week games, which SEAT is more profitable?

On games where we hold a signal, market-making symmetrically means being the
counterparty to our own edge. Three seats are possible; all three are priced
here on the same games, same rungs, same snapshot.

  1 TAKER OVER      buy Yes at the ASK, pay the taker fee (0.07*p*(1-p)).
                    Pays the spread, keeps the signal edge.
  2 MAKER SHORT     post an offer to SELL Yes; informed flow lifts it.
                    Sells at the ask, pays the MAKER fee (25%).
                    Collects the spread, gives up the signal edge.
                    This is the exact mirror of seat 1 (sum = -both fees).
  3 MAKER LEANED    post only a BID to BUY Yes at the bid; never offer to sell.
                    Buys at the bid, pays the maker fee.
                    Collects the spread AND keeps the signal edge -- but only
                    fills when someone wants to sell the over to us.

Rung = the strike nearest the book closing total (the closest analogue of a
sportsbook over bet). Stake normalised to $100 of capital at risk per bet so
the seats are directly comparable.

Two hit-rate scenarios:
  REALISED 2025-26  what actually happened (a weak CrewShock season)
  HISTORICAL        the 8-season frozen slate: CrewShock Q85 54.40% over,
                    final week 56.04% over (PROSPECTIVE.md). Applied as a
                    scenario to the same prices to show a normal-mechanism year.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import kalshi_calib as KC
import refs

THR, FEE_K = 0.8682, 0.07
HIST = {"CrewShock": 0.5440, "final week": 0.5604}


def build():
    m = refs.build()
    m["gid"] = m["GAME-ID"].astype(str).str.strip()
    mp = pd.read_csv("team_mapping.csv").set_index(
        "bigdataball_name")["abbr"].to_dict()
    g = m[m["date"] >= "2025-10-01"].copy()
    g["H"], g["R"] = g["TEAM_H"].map(mp), g["TEAM_R"].map(mp)
    mk = lambda d, a, b: (d.dt.strftime("%Y-%m-%d") + "|"
                          + np.where(a < b, a, b) + "-" + np.where(a < b, b, a))
    g["k"] = mk(g["date"], g["H"], g["R"])
    f = pd.read_csv("ref_features.csv")
    f["gid"] = f["gid"].astype(str).str.strip()
    g = g.merge(f[["gid", "CrewShock"]], on="gid", how="left")
    last = g[g["date"] <= "2026-04-12"]["date"].max()
    g["dl"] = (last - g["date"]).dt.days

    u = KC.load()
    u = u[~((u["bid"] <= 0) & (u["ask"] >= 1.0))]
    u = u[u["bucket"] == "regular"].copy()
    u = u.merge(g[["k", "total", "CrewShock", "dl"]].drop_duplicates("k"),
                on="k", how="inner")
    u["off"] = (u["floor_strike"] - u["total"]).abs()
    u = u.sort_values(["k", "off", "floor_strike"])
    return u.groupby("k", as_index=False).first()


def seats(s, hit=None):
    """Returns per-seat (roi, pnl, n) at $100 risk per bet."""
    ask, bid = s["ask"].values, s["bid"].values
    win = s["win"].values.astype(float) if hit is None else None
    out = {}
    # 1 TAKER OVER: cost = ask + taker fee, risk = cost
    c1 = ask + FEE_K * ask * (1 - ask)
    n1 = 100.0 / c1
    w1 = win if hit is None else None
    # 2 MAKER SHORT: sold at ask, maker fee; risk = 1 - (ask - fee)
    coll = ask - 0.25 * FEE_K * ask * (1 - ask)
    r2 = 1 - coll
    n2 = 100.0 / r2
    # 3 MAKER LEANED: bought at bid + maker fee; risk = cost
    c3 = bid + 0.25 * FEE_K * bid * (1 - bid)
    n3 = 100.0 / c3

    def pack(name, n, cost_or_risk, payoff_if_over, payoff_if_under):
        if hit is None:
            p = np.where(win == 1, payoff_if_over, payoff_if_under)
        else:
            p = hit * payoff_if_over + (1 - hit) * payoff_if_under
        tot = float(np.sum(n * p))
        risk = float(np.sum(n * cost_or_risk))
        out[name] = (100 * tot / risk, tot, len(s))

    pack("1 TAKER OVER", n1, c1, 1 - c1, -c1)
    pack("2 MAKER SHORT", n2, r2, coll - 1, coll)
    pack("3 MAKER LEANED", n3, c3, 1 - c3, -c3)
    return out


def main():
    u = build()
    cells = [("CrewShock", u[u["CrewShock"].fillna(-9) >= THR]),
             ("final week", u[u["dl"].fillna(99) <= 7]),
             ("either (the book)",
              u[(u["CrewShock"].fillna(-9) >= THR) | (u["dl"].fillna(99) <= 7)])]
    print(f"  rung used: nearest the book total   mean spread "
          f"{100*(u['ask']-u['bid']).mean():.2f}c")

    for lab, s in cells:
        over = 100 * s["win"].mean()
        print("\n" + "=" * 84)
        print(f"{lab.upper()}   n={len(s)}   realised over rate {over:.2f}%")
        print("=" * 84)
        print(f"  {'seat':18}{'ROI % (realised)':>19}{'$ (realised)':>15}"
              f"{'ROI % (historical)':>21}")
        r_real = seats(s)
        h = HIST.get(lab)
        if h is None:
            # blended historical rate, weighted by cell sizes
            n_cs = int((u["CrewShock"].fillna(-9) >= THR).sum())
            n_fw = int((u["dl"].fillna(99) <= 7).sum())
            h = (HIST["CrewShock"] * n_cs + HIST["final week"] * n_fw) \
                / (n_cs + n_fw)
        r_hist = seats(s, hit=h)
        for k in ("1 TAKER OVER", "2 MAKER SHORT", "3 MAKER LEANED"):
            print(f"  {k:18}{r_real[k][0]:>+19.2f}{r_real[k][1]:>+15,.0f}"
                  f"{r_hist[k][0]:>+21.2f}")
        print(f"  [historical scenario uses a {100*h:.2f}% over rate on the "
              f"same prices]")

    print("\n" + "=" * 84)
    print("ZERO-SUM CHECK")
    print("=" * 84)
    s = cells[2][1]
    r = seats(s)
    print(f"  seat 1 + seat 2 dollars = "
          f"${r['1 TAKER OVER'][1] + r['2 MAKER SHORT'][1]:,.0f}  "
          f"(negative = the exchange's fees)")
    print(f"  seats 1 and 2 are exact mirrors; seat 3 is seat 1 executed "
          f"{100*(s['ask']-s['bid']).mean():.1f}c cheaper with a 75% lower fee")


if __name__ == "__main__":
    main()
