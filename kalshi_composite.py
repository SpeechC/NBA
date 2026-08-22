"""COMPOSITE SECOND-LINE BACKTEST — season P&L and ROI of making markets on
every rung of the Kalshi NBA totals ladder, $100 max committed per line.

SETUP
  fair value  = the frozen SECOND_LINE.md curve: OT mixture on the ladder's own
                (mu, sd), mu shifted +1.434 on CrewShock>=Q85 games and +2.693
                in the final week. Nothing else.
  quoting     = JOIN the snapshot NBBO (never cross). Quote a side only if a
                fill there is +EV against our fair after the 25% maker fee:
                  quote the BID (buy Yes)  iff  fair - bid - fee > 0
                  quote the ASK (buy No)   iff  ask - fair - fee > 0
  size        = 100 contracts per quoted side per rung -> max loss per rung
                <= $100 (the user's constraint). Both sides filling locks the
                spread with ~zero risk.
  universe    = 2025-26 regular season, rungs with mid in [0.05, 0.95].

FILL MODEL (the unmeasured part, made explicit as a 2-parameter grid)
  phi   = P(a quoted side is crossed pregame)          grid 0.10 / 0.25 / 0.50
  kappa = adverse-selection tilt: the losing side of a rung fills at
          phi*(1+kappa), the winning side at phi*(1-kappa)
                                                       grid 0 / .15 / .30 / .50
  kappa=0 is pure noise flow; kappa=0.5 means fills are 3x likelier on the
  side that settles against us. The candles will eventually measure both;
  until then the GRID is the result, not any single cell.

CONTROL: the BLIND MAKER -- same prices, same sizes, but quotes BOTH sides of
every rung with no fair-value curve. The difference between the two books is
the measured value of the pricing stack.

CAVEAT of record: the snapshot is the closing book. Real quoting runs all day
at prices we cannot see; this treats the close as representative of quotable
levels. Staleness defense (SECOND_LINE.md section 5) is assumed perfect here --
kappa is where its failure would show up.
"""
import warnings

import numpy as np
import pandas as pd
from scipy.stats import norm

warnings.filterwarnings("ignore")

import kalshi_calib as KC
import refs

THR, CS_SHIFT, FW_SHIFT = 0.8682, 1.434, 2.693
FEE_K = 0.07
NCON = 100                      # contracts per quoted side -> <= $100 risk
NSIM = 400
RNG = np.random.default_rng(20260824)


def fee_m(p):
    return 0.25 * FEE_K * p * (1 - p)


def build():
    m = refs.build()
    n = lambda c: pd.to_numeric(m[c], errors="coerce")
    J = sum(n(f"OT{i}_{s}").fillna(0.0) for i in range(1, 6)
            for s in ("H", "R"))
    pr = pd.DataFrame({"yr": m["yr"], "J": J}).dropna()
    pr = pr[pr["yr"] <= 2024]
    p_ot = (pr["J"] > 0).mean()
    Js = pr.loc[pr["J"] > 0, "J"].values

    mp = pd.read_csv("team_mapping.csv").set_index(
        "bigdataball_name")["abbr"].to_dict()
    g = m[m["date"] >= "2025-10-01"].copy()
    g["gid"] = g["GAME-ID"].astype(str).str.strip()
    g["H"] = g["TEAM_H"].map(mp)
    g["R"] = g["TEAM_R"].map(mp)
    mk = lambda d, a, b: (d.dt.strftime("%Y-%m-%d") + "|"
                          + np.where(a < b, a, b) + "-" + np.where(a < b, b, a))
    g["k"] = mk(g["date"], g["H"], g["R"])
    f = pd.read_csv("ref_features.csv")
    f["gid"] = f["gid"].astype(str).str.strip()
    g = g.merge(f[["gid", "CrewShock"]], on="gid", how="left")
    last = g[g["date"] <= "2026-04-12"]["date"].max()
    g["days_left"] = (last - g["date"]).dt.days

    u = KC.load()
    u = u[~((u["bid"] <= 0) & (u["ask"] >= 1.0))]
    u = u[u["bucket"] == "regular"].copy()
    fits = {}
    for ev, gg in u.groupby("event_ticker"):
        ft = KC.fit_ladder(gg)
        if ft:
            fits[ev] = ft[:2]
    u = u[u["event_ticker"].isin(fits)]
    u["mu"] = u["event_ticker"].map(lambda e: fits[e][0])
    u["sdh"] = u["event_ticker"].map(lambda e: fits[e][1])
    u = u.merge(g[["k", "CrewShock", "days_left"]].drop_duplicates("k"),
                on="k", how="left")
    u = u[(u["mid"] > 0.05) & (u["mid"] < 0.95)].reset_index(drop=True)

    shift = (CS_SHIFT * (u["CrewShock"].fillna(-9) >= THR)
             + FW_SHIFT * (u["days_left"].fillna(99) <= 7)).values
    K = u["floor_strike"].values
    mu = u["mu"].values + shift
    sd = u["sdh"].values
    m0 = mu - p_ot * Js.mean()
    s2 = sd ** 2 - p_ot * (1 - p_ot) * Js.mean() ** 2 - p_ot * Js.var(ddof=1)
    s0 = np.sqrt(np.clip(s2, 1.0, None))
    S = (1 - p_ot) * (1.0 - norm.cdf((K - m0) / s0))
    ot = np.zeros(len(u))
    for j in Js:
        ot += 1.0 - norm.cdf((K - m0 - j) / s0)
    u["fair"] = S + p_ot * ot / len(Js)
    return u


def simulate(u, phi, kappa, blind):
    """One MC pass. Returns (spread $, inventory $, fills, dollars risked)."""
    bid, ask = u["bid"].values, u["ask"].values
    fair = u["fair"].values
    win = u["win"].values.astype(bool)
    q_yes = np.ones(len(u), bool) if blind else \
        (fair - bid - fee_m(bid) > 0)
    q_no = np.ones(len(u), bool) if blind else \
        (ask - fair - fee_m(ask) > 0)
    # losing side: Yes loses if the rung settles No, and vice versa
    py = np.where(win, phi * (1 - kappa), phi * (1 + kappa))
    pn = np.where(win, phi * (1 + kappa), phi * (1 - kappa))
    fy = q_yes & (RNG.random(len(u)) < py)
    fn = q_no & (RNG.random(len(u)) < pn)

    both = fy & fn
    only_y = fy & ~fn
    only_n = fn & ~fy
    spread_pnl = NCON * np.sum((ask - bid - fee_m(bid) - fee_m(ask))[both])
    inv_y = NCON * ((win.astype(float) - bid - fee_m(bid))[only_y])
    inv_n = NCON * (((~win).astype(float) - (1 - ask) - fee_m(ask))[only_n])
    risked = NCON * (bid[only_y].sum() + (1 - ask)[only_n].sum())
    return (spread_pnl, inv_y.sum() + inv_n.sum(),
            int(both.sum() * 2 + only_y.sum() + only_n.sum()), risked)


def run(u, blind, label):
    print(f"\n  {label}")
    print(f"  {'phi':>6}{'kappa':>7}{'fills/szn':>11}{'spread $':>11}"
          f"{'inventory $':>13}{'TOTAL $':>10}{'risked $':>11}{'ROI %':>8}")
    for phi in (0.10, 0.25, 0.50):
        for kappa in (0.0, 0.15, 0.30, 0.50):
            res = np.array([simulate(u, phi, kappa, blind)
                            for _ in range(NSIM)])
            sp, inv, fl, rk = res.mean(axis=0)
            tot = sp + inv
            roi = 100 * tot / rk if rk else np.nan
            print(f"  {phi:>6.2f}{kappa:>7.2f}{fl:>11,.0f}{sp:>11,.0f}"
                  f"{inv:>13,.0f}{tot:>10,.0f}{rk:>11,.0f}{roi:>8.2f}")


def main():
    u = build()
    ng = u["event_ticker"].nunique()
    print(f"  {ng:,} games, {len(u):,} quotable rungs "
          f"({len(u)/ng:.1f}/game)   max exposure "
          f"${len(u)/ng*100:,.0f}/game")
    qy = (u["fair"] - u["bid"] - fee_m(u["bid"]) > 0)
    qn = (u["ask"] - u["fair"] - fee_m(u["ask"]) > 0)
    print(f"  second line quotes: bid side {100*qy.mean():.1f}% of rungs, "
          f"ask side {100*qn.mean():.1f}%, both {100*(qy&qn).mean():.1f}%")

    run(u, blind=False, label="SECOND LINE (stack decides which sides to "
                              "quote)")
    run(u, blind=True, label="BLIND MAKER (control: both sides, no curve)")

    print("\n  Reading: kappa is the whole game. The candles measure it; this")
    print("  grid prices it. Break-even kappa is where TOTAL $ crosses zero.")


if __name__ == "__main__":
    main()
