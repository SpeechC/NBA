"""ROI backtest of the SECOND-ALGORITHM strategy on the Kalshi totals ladder.

THE STRATEGY. Quote/trade from a fair-value curve that differs from the
incumbent Gaussian in the ways this project has measured:

    fair mu  = ladder's own mu, shifted by the FROZEN mean signals
    fair sd  = ladder's own sd (variance is calibrated -- do not touch)
    fair SHAPE = the OT mixture (kalshi_shape.py: regulation Gaussian
                 + 5.24% one-sided OT jump, parameters from prior seasons)

ABLATION LEGS, fixed before running:
    L0  shape only
    L1  L0 + frozen signals: CrewShock Q85 -> mu += +1.434 on qualifying
        games; final week (days_left <= 7) -> mu += +2.693
        (both from PROSPECTIVE.md's historical slate; note the slate includes
        part of 2025-26, a mild look-ahead for this season -- flagged, small)
    L2  L1 + the league mean over-bias mu += +0.509 (sub-hurdle on its own;
        included to see whether it helps or hurts the bundle)

EXECUTION MODELS (bounds, not point estimates):
    TAKER  buy Yes at the quoted ask / No at (1 - bid), full fee
           0.07*p*(1-p). Pessimistic and fully executable.
    MAKER  fill assumed at the quoted bid (Yes) / (1 - ask) (No), fee 25%.
           OPTIMISTIC: 100% fill, no adverse selection. The truth is between.

TRADE RULE. One contract per game: the (rung, side) with the largest positive
net edge under the leg's fair value. Rungs with mid outside [0.05, 0.95]
excluded. Stake = cost; profit = 1 - cost on a win, -cost on a loss.

EXCLUDED: the intraday staleness edge (t=-8.24) -- no candles, cannot be
backtested; the fee seat's flow revenue -- no fill data. This is therefore a
backtest of the PRICING component only.

One season, ~1,100 games. SE on ROI at n~1,100 is ~3pp: this measures sign
and rough size, not establishment.
"""
import warnings

import numpy as np
import pandas as pd
from scipy.stats import norm

warnings.filterwarnings("ignore")

import kalshi_calib as KC
import refs

THR, CS_SHIFT, FW_SHIFT, BIAS = 0.8682, 1.434, 2.693, 0.509
P_OT, FEE_K = None, 0.07          # P_OT estimated below


def fee(p, maker=False):
    f = FEE_K * p * (1 - p)
    return 0.25 * f if maker else f


def build():
    global P_OT
    m = refs.build()
    n = lambda c: pd.to_numeric(m[c], errors="coerce")
    J = sum(n(f"OT{i}_{s}").fillna(0.0) for i in range(1, 6)
            for s in ("H", "R"))
    prior = pd.DataFrame({"yr": m["yr"], "J": J}).dropna()
    prior = prior[prior["yr"] <= 2024]
    P_OT = (prior["J"] > 0).mean()
    Js = prior.loc[prior["J"] > 0, "J"].values

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
            fits[ev] = (ft[0], ft[1])
    u = u[u["event_ticker"].isin(fits)]
    u["mu"] = u["event_ticker"].map(lambda e: fits[e][0])
    u["sdh"] = u["event_ticker"].map(lambda e: fits[e][1])
    u = u.merge(g[["k", "CrewShock", "days_left"]].drop_duplicates("k"),
                on="k", how="left")
    u = u[(u["mid"] > 0.05) & (u["mid"] < 0.95)]
    return u, Js


def mixture_S(K, mu, sd, Js):
    m0 = mu - P_OT * Js.mean()
    s2 = sd ** 2 - P_OT * (1 - P_OT) * Js.mean() ** 2 - P_OT * Js.var(ddof=1)
    s0 = np.sqrt(np.clip(s2, 1.0, None))
    S = (1 - P_OT) * (1.0 - norm.cdf((K - m0) / s0))
    ot = np.zeros(len(K))
    for j in Js:
        ot += 1.0 - norm.cdf((K - m0 - j) / s0)
    return S + P_OT * ot / len(Js)


def run_leg(u, Js, leg):
    x = u.copy()
    shift = np.zeros(len(x))
    if leg >= 1:
        shift = shift + CS_SHIFT * (x["CrewShock"].fillna(-9) >= THR).values
        shift = shift + FW_SHIFT * (x["days_left"].fillna(99) <= 7).values
    if leg >= 2:
        shift = shift + BIAS
    x["fair"] = mixture_S(x["floor_strike"].values,
                          x["mu"].values + shift, x["sdh"].values, Js)
    out = {}
    for mode, maker in (("TAKER", False), ("MAKER*", True)):
        py = (x["bid"] if maker else x["ask"]).values      # Yes entry price
        pn = (1 - (x["ask"] if maker else x["bid"])).values  # No entry price
        ey = x["fair"].values - (py + fee(py, maker))
        en = (1 - x["fair"].values) - (pn + fee(pn, maker))
        x["_e"] = np.maximum(ey, en)
        x["_side"] = np.where(ey >= en, 1, 0)
        x["_cost"] = np.where(ey >= en, py + fee(py, maker),
                              pn + fee(pn, maker))
        best = x.sort_values("_e", ascending=False).groupby(
            "event_ticker").first()
        b = best[best["_e"] > 0]
        won = np.where(b["_side"] == 1, b["win"], 1 - b["win"])
        prof = np.where(won == 1, 1 - b["_cost"], -b["_cost"])
        roi = prof.sum() / b["_cost"].sum() if len(b) else np.nan
        se = (prof.std(ddof=1) / np.sqrt(len(b)) / b["_cost"].mean()
              if len(b) > 2 else np.nan)
        out[mode] = dict(n=len(b), exp=100 * b["_e"].mean(),
                         win=100 * won.mean(), roi=100 * roi, se=100 * se,
                         yes=int((b["_side"] == 1).sum()),
                         atm=100 * ((b["mid"] - 0.5).abs() < 0.15).mean())
    return out


def main():
    u, Js = build()
    print(f"  {u['event_ticker'].nunique():,} games, {len(u):,} tradeable "
          f"rungs   OT mixture: p={100*P_OT:.2f}%, E[J]={Js.mean():.1f}")
    cs = u.drop_duplicates("event_ticker")
    print(f"  CrewShock >= Q85 on {int((cs['CrewShock'] >= THR).sum())} games"
          f"   final-week games {int((cs['days_left'] <= 7).sum())}")

    legs = {0: "L0 shape only",
            1: "L1 + frozen signals (CrewShock, final week)",
            2: "L2 + league mean bias"}
    print(f"\n  {'leg':42}{'mode':>8}{'n':>7}{'exp edge':>10}{'win %':>8}"
          f"{'ROI %':>8}{'se':>6}{'%Yes':>7}{'%ATM':>7}")
    for lg, nm in legs.items():
        r = run_leg(u, Js, lg)
        for mode in ("TAKER", "MAKER*"):
            d = r[mode]
            print(f"  {nm if mode=='TAKER' else '':42}{mode:>8}{d['n']:>7}"
                  f"{d['exp']:>9.2f}pp{d['win']:>8.2f}{d['roi']:>+8.2f}"
                  f"{d['se']:>6.2f}{100*d['yes']/max(d['n'],1):>7.1f}"
                  f"{d['atm']:>7.1f}")
    print("\n  MAKER* assumes a 100% fill at the quoted bid -- optimistic")
    print("  bound. TAKER is fully executable at the snapshot -- pessimistic.")
    print("  Excluded entirely: the intraday staleness edge and flow revenue.")


if __name__ == "__main__":
    main()
