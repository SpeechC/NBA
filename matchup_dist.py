"""Can a MATCHUP model of the totals distribution beat the Kalshi ladder?

The proposal: model each game's total-points distribution from matchup stats
(pace, 3-point profile, volatility, schedule) and trade rungs where it
disagrees with the ladder.

The MEAN half is settled -- BETTING_TOTALS.md, five variants including pace16
and matchup+rest+travel, every one worse than the closing line (RMSE 19.2-20.0
vs 18.10, incremental t <= 0). So the live question is the DISTRIBUTION: can
stats rank games by dispersion better than the ladder's implied sd does?

DESIGN (fit and evaluation strictly separated):
  1  per-team prior-only states, shift(1).rolling(20, min 10) within season:
     pace, 3PA rate, 3P%, and the rolling SDs of 3P% and points (shooting and
     scoring volatility -- the mechanism the 3-point story needs)
  2  game level: two-team means/sums, plus closing total and |spread|
  3  fit |e| on DEVELOPMENT (2017-18..2023-24), e = actual - closing total
  4  evaluate on HOLDOUT (2024-25 + 2025-26): decile ranking of predicted
     dispersion vs realized
  5  THE RACE, on the 2025-26 Kalshi season: |e| ~ model prediction + implied
     sd. Whichever carries the information survives; the other's coefficient
     dies. This is the direct test of the proposal.

POWER NOTE. n=4,700 development games. A model that truly differentiated
game-level sd by +/-10% (the size a wing trade needs) implies an |e|
regression R^2 of roughly 0.5-1%%, which this n detects easily. A null here is
a powered null, not an absence of evidence.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import refs
from data_split import SPLIT_DATE
from dispersion_priced import ols

W, MINP = 20, 10


def build():
    m = refs.build()
    n = lambda c: pd.to_numeric(m[c], errors="coerce")
    m["gid"] = m["GAME-ID"].astype(str).str.strip()
    m["spread"] = n("CLOSING SPREAD_H")
    rows = []
    for s in ("H", "R"):
        rows.append(pd.DataFrame({
            "gid": m["gid"], "yr": m["yr"], "date": m["date"],
            "team": m[f"TEAM_{s}"],
            "pace": n(f"PACE_{s}"),
            "tpa": n(f"3PA_{s}") / n(f"FGA_{s}"),
            "p3": n(f"3P_{s}") / n(f"3PA_{s}").replace(0, np.nan),
            "pts": n(f"PTS_{s}")}))
    L = pd.concat(rows).sort_values("date")
    g = L.groupby(["yr", "team"])
    for c, out, how in (("pace", "p_pace", "mean"), ("tpa", "p_tpa", "mean"),
                        ("p3", "p_p3", "mean"), ("p3", "p_p3sd", "std"),
                        ("pts", "p_ptssd", "std")):
        f = (lambda s: s.shift(1).rolling(W, min_periods=MINP).mean()) \
            if how == "mean" else \
            (lambda s: s.shift(1).rolling(W, min_periods=MINP).std())
        L[out] = g[c].transform(f)
    G = L.groupby("gid", as_index=False).agg(
        yr=("yr", "first"), date=("date", "first"),
        pace=("p_pace", "mean"), tpa=("p_tpa", "mean"), p3=("p_p3", "mean"),
        p3sd=("p_p3sd", "mean"), ptssd=("p_ptssd", "mean"),
        nn=("p_pace", "count"))
    G = G[G["nn"] == 2]
    G = G.merge(m[["gid", "total", "actual", "e", "spread"]], on="gid")
    G["abs_e"] = G["e"].abs()
    G["abs_spr"] = G["spread"].abs()
    return G.dropna(subset=["pace", "tpa", "p3", "p3sd", "ptssd", "abs_e",
                            "total", "abs_spr"])


FEATS = ["pace", "tpa", "p3", "p3sd", "ptssd", "total", "abs_spr"]


def main():
    G = build()
    dev = G[G["date"] < SPLIT_DATE]
    hold = G[G["date"] >= SPLIT_DATE]
    print(f"  {len(G):,} games   development {len(dev):,}   holdout "
          f"{len(hold):,}")

    print("\n" + "=" * 96)
    print("1 — THE MATCHUP DISPERSION MODEL, fit on development")
    print("    |e| ~ pace + 3PA rate + 3P% + 3P% vol + scoring vol + total "
          "+ |spread|")
    print("=" * 96)
    X = np.column_stack([dev[c].values for c in FEATS])
    b, se, t = ols(dev["abs_e"].values, X)
    r2 = 1 - np.var(dev["abs_e"].values
                    - np.column_stack([np.ones(len(dev)), X]) @ b) \
        / np.var(dev["abs_e"].values)
    print(f"  {'feature':12}{'coef':>12}{'t':>8}")
    for i, c in enumerate(FEATS):
        print(f"  {c:12}{b[i+1]:>+12.4f}{t[i+1]:>8.2f}")
    print(f"  R^2 = {r2:.5f}   (a +/-10%-sd model implies ~0.005-0.01)")

    def pred(x):
        return np.column_stack([np.ones(len(x))]
                               + [x[c].values for c in FEATS]) @ b

    print("\n" + "=" * 96)
    print("2 — HOLDOUT: can the model RANK games by dispersion?")
    print("=" * 96)
    h = hold.copy()
    h["pr"] = pred(h)
    h["dec"] = pd.qcut(h["pr"], 5, labels=False, duplicates="drop") + 1
    print(f"  {'quintile':>9}{'n':>7}{'predicted |e|':>15}{'realized |e|':>14}"
          f"{'realized sd(e)':>16}")
    for q, gg in h.groupby("dec"):
        print(f"  {q:>9}{len(gg):>7}{gg['pr'].mean():>15.3f}"
              f"{gg['abs_e'].mean():>14.3f}{gg['e'].std(ddof=1):>16.3f}")
    r = np.corrcoef(h["pr"], h["abs_e"])[0, 1]
    tt = r * np.sqrt(len(h) - 2) / np.sqrt(1 - r * r)
    print(f"  holdout corr(predicted, realized |e|) = {r:+.4f} (t={tt:+.2f})")

    print("\n" + "=" * 96)
    print("3 — THE RACE, 2025-26: matchup model vs the ladder's implied sd")
    print("=" * 96)
    import kalshi_calib as KC
    u = KC.load()
    u = u[~((u["bid"] <= 0) & (u["ask"] >= 1.0))]
    u = u[u["bucket"] == "regular"]
    rows = []
    for ev, gg in u.groupby("event_ticker"):
        f = KC.fit_ladder(gg)
        if f:
            rows.append({"k": gg["k"].iloc[0], "sd_imp": f[1], "mu": f[0]})
    K = pd.DataFrame(rows)
    mp = pd.read_csv("team_mapping.csv").set_index(
        "bigdataball_name")["abbr"].to_dict()
    m2 = refs.build()
    m2 = m2[m2["date"] >= pd.Timestamp("2025-10-01")].copy()
    m2["gid"] = m2["GAME-ID"].astype(str).str.strip()
    m2["H"] = m2["TEAM_H"].map(mp)
    m2["R"] = m2["TEAM_R"].map(mp)
    mk = lambda d, a, bb: (d.dt.strftime("%Y-%m-%d") + "|"
                           + np.where(a < bb, a, bb) + "-"
                           + np.where(a < bb, bb, a))
    m2["k"] = mk(m2["date"], m2["H"], m2["R"])
    D = h.merge(m2[["gid", "k"]], on="gid").merge(K, on="k")
    D = D.dropna(subset=["pr", "sd_imp", "abs_e"])
    print(f"  {len(D):,} games with both a model prediction and a fitted "
          f"ladder")
    for lab, cols in (("model alone", ["pr"]),
                      ("implied sd alone", ["sd_imp"]),
                      ("BOTH", ["pr", "sd_imp"])):
        Xr = np.column_stack([D[c].values for c in cols])
        br, ser, tr = ols(D["abs_e"].values, Xr)
        s = "   ".join(f"{c} {br[i+1]:+.4f} (t={tr[i+1]:+.2f})"
                       for i, c in enumerate(cols))
        print(f"  {lab:18} {s}")
    print("\n  if the ladder's sd survives and the model's coefficient dies,")
    print("  the matchup information is already inside the ladder.")


if __name__ == "__main__":
    main()
