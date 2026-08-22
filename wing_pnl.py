"""2025-26 SEASON P&L AND DRAWDOWN — selling wing lotteries, $100 risk per line.

RULE (from wing_selection.py, applied as specified):
  universe   2025-26 regular season, Kalshi NBA totals ladders
  wing       the CHEAP side of a rung, priced 15-30c
  filter     spread >= 3c
  skip       over-lotteries on games where CrewShock >= Q85 or days_left <= 7
             (our own signals expect more scoring)
  side       we SELL the lottery at its ask; maker fee = 25% of taker fee
  size       contracts = 100 / (1 - collect)  ->  MAX LOSS PER LINE = $100
  settle     lottery hits -> we pay $1/contract (lose $100)
             lottery misses -> we keep the premium

Realized outcomes throughout -- no modelled hit rates.

FILL ASSUMPTIONS, reported as a range because fills are unmeasured:
  100%  every offer taken. Upper bound on both profit AND drawdown; this is the
        "what happened" case at full participation.
  25%   random quarter of offers taken, 400 simulations, for the drawdown
        DISTRIBUTION at realistic participation.

Drawdown is peak-to-trough on the cumulative P&L, computed day by day in
chronological order. Losses are CORRELATED: one overtime hits every
over-lottery on that ladder simultaneously, which is what drives the tail.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import kalshi_calib as KC
import refs

THR, FEE_K = 0.8682, 0.07
NSIM = 400
RNG = np.random.default_rng(20260825)


def build():
    m = refs.build()
    n_ = lambda c: pd.to_numeric(m[c], errors="coerce")
    J = sum(n_(f"OT{i}_{s}").fillna(0.0) for i in range(1, 6)
            for s in ("H", "R"))
    m["ot"] = J > 0
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
    u = u.merge(g[["k", "date", "ot", "CrewShock", "dl"]].drop_duplicates("k"),
                on="k", how="inner")
    u["lot_over"] = u["mid"] < 0.5
    u["px"] = np.where(u["lot_over"], u["ask"], 1 - u["bid"])
    u["hit"] = np.where(u["lot_over"], u["win"], 1 - u["win"]).astype(float)
    u["spread"] = u["ask"] - u["bid"]
    u["collect"] = u["px"] - 0.25 * FEE_K * u["px"] * (1 - u["px"])
    u["ncon"] = 100.0 / (1.0 - u["collect"])
    u["pnl"] = np.where(u["hit"] == 1, -100.0, u["ncon"] * u["collect"])
    return u


def select(u, spread_min=0.03, use_signals=True):
    s = u[(u["px"] >= 0.15) & (u["px"] <= 0.30)].copy()
    if spread_min:
        s = s[s["spread"] >= spread_min - 1e-9]
    if use_signals:
        flag = (s["CrewShock"].fillna(-9) >= THR) | (s["dl"].fillna(99) <= 7)
        s = s[~(s["lot_over"] & flag)]
    return s.sort_values(["date", "event_ticker", "floor_strike"])


def curve(s):
    d = s.groupby("date", as_index=False)["pnl"].sum().sort_values("date")
    d["cum"] = d["pnl"].cumsum()
    d["peak"] = d["cum"].cummax()
    d["dd"] = d["cum"] - d["peak"]
    return d


def summary(s, lab):
    d = curve(s)
    risk = 100.0 * len(s)
    nights = len(d)
    per_night = s.groupby("date").size()
    print(f"\n  {lab}")
    print(f"    lines {len(s):,}   nights {nights}   lines/night "
          f"{per_night.mean():.1f} (max {per_night.max()})")
    print(f"    max capital at risk in one night  "
          f"${100*per_night.max():,.0f}")
    print(f"    lottery hit rate {100*s['hit'].mean():.2f}%")
    print(f"    TOTAL P&L  ${s['pnl'].sum():,.0f}    "
          f"ROI on cumulative risk {100*s['pnl'].sum()/risk:+.2f}%")
    print(f"    mean per line ${s['pnl'].mean():+.2f}")
    print(f"    MAX DRAWDOWN  ${d['dd'].min():,.0f}   "
          f"(as a share of final P&L: "
          f"{abs(d['dd'].min())/max(s['pnl'].sum(),1):.2f}x)")
    print(f"    worst night ${d['pnl'].min():,.0f}   "
          f"best night ${d['pnl'].max():,.0f}   "
          f"losing nights {100*(d['pnl']<0).mean():.0f}%")
    return d


def main():
    u = build()
    print(f"  {u['event_ticker'].nunique():,} games, {len(u):,} rungs, "
          f"{u['date'].nunique()} playing nights")

    print("\n" + "=" * 92)
    print("100% FILL — every offer taken")
    print("=" * 92)
    a = select(u, spread_min=0.0, use_signals=False)
    summary(a, "ALL wings (15-30c), no filters")
    b = select(u, spread_min=0.03, use_signals=False)
    summary(b, "wings + spread >= 3c")
    c = select(u, spread_min=0.03, use_signals=True)
    d = summary(c, "wings + spread >= 3c + skip over-lotteries on signal games"
                   "   <-- THE RULE")

    print("\n    equity curve, month by month (the RULE):")
    mo = c.copy()
    mo["m"] = mo["date"].dt.to_period("M")
    t = mo.groupby("m").agg(lines=("pnl", "size"), pnl=("pnl", "sum"))
    t["cum"] = t["pnl"].cumsum()
    for k, r in t.iterrows():
        print(f"      {k}  lines {int(r['lines']):>4}   "
              f"P&L ${r['pnl']:>+9,.0f}   cumulative ${r['cum']:>+9,.0f}")

    print("\n" + "=" * 92)
    print(f"25% FILL — random quarter of offers taken, {NSIM} simulations")
    print("=" * 92)
    tot, dd, wn = [], [], []
    for _ in range(NSIM):
        s = c[RNG.random(len(c)) < 0.25]
        if not len(s):
            continue
        cc = curve(s)
        tot.append(s["pnl"].sum())
        dd.append(cc["dd"].min())
        wn.append(cc["pnl"].min())
    tot, dd, wn = np.array(tot), np.array(dd), np.array(wn)
    print(f"  lines/season ~{0.25*len(c):.0f}")
    print(f"  P&L        median ${np.median(tot):,.0f}   "
          f"5th pct ${np.percentile(tot,5):,.0f}   "
          f"95th pct ${np.percentile(tot,95):,.0f}   "
          f"P(loss) {100*(tot<0).mean():.0f}%")
    print(f"  MAX DD     median ${np.median(dd):,.0f}   "
          f"5th pct ${np.percentile(dd,5):,.0f} (worst)")
    print(f"  worst night median ${np.median(wn):,.0f}   "
          f"5th pct ${np.percentile(wn,5):,.0f}")


if __name__ == "__main__":
    main()
