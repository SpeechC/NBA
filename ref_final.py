"""Final robustness on the definitive CrewShock, plus season P&L.

1  CONCENTRATION. Is CrewShock a broad officiating phenomenon or a handful of
   officials? Two views:
     - exact additive decomposition of the OLS slope into per-official
       contributions, since CrewShock is itself a sum over the crew
     - leave-one-referee-out: drop every game an official worked, refit
2  MECHANICAL CHAIN on the definitive signal:
       CrewShock -> fouls per 100 -> FTA -> actual total -> closing total
   The first link must be overwhelming or the feature is not what it claims.
3  SEASON-BY-SEASON P&L betting OVER at the frozen develop Q85 threshold,
   flat $100 at -110.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import ref_features as rf
import ref_regime as rg
import ref_shock as rsk
import refs
from data_split import SPLIT_DATE
from dispersion_priced import ols

THR = 0.8682          # frozen develop Q85 from PREREG_ref_regime.md
STAKE, PRICE = 100.0, -110
WIN = STAKE * 100.0 / 110.0
BE = 110 / 210


def resid(x, col, ctrl):
    """Residualise a column against the controls (Frisch-Waugh)."""
    X = np.column_stack([np.ones(len(x))] + [x[c].values for c in ctrl])
    b = np.linalg.lstsq(X, x[col].values, rcond=None)[0]
    return x[col].values - X @ b


def main():
    d, k, sig = rg.build()
    ctrl = ["LeagueFoulState"] + rsk.CTRL
    print("=" * 100)
    print("1 — IS CrewShock A CREW PHENOMENON OR A FEW OFFICIALS?")
    print("=" * 100)
    s = resid(d, "CrewShock", ctrl)
    ee = resid(d, "e", ctrl)
    denom = float(s @ s)
    slope = float(s @ ee) / denom
    print(f"  {len(d):,} games   pooled gap slope {slope:+.4f}")

    # exact additive decomposition: CrewShock = sum of RefEffect over the crew
    uni = rf.universe()
    _, kk, _, agg = rf.build(save=False)
    dates = uni["date"].values.astype("datetime64[ns]").astype(np.int64)
    long = pd.concat([
        pd.DataFrame({"gid": uni["gid"].values, "ref": uni[f"ref{i}"].values})
        for i in (1, 2, 3)])
    contrib = pd.DataFrame({"gid": d["gid"].values, "ee": ee, "s": s})
    L = long.merge(contrib, on="gid", how="inner")
    # per-official share of the slope numerator, weighted by their own share
    # of that game's CrewShock is not identified without re-deriving RefEffect,
    # so use the game-level attribution: each official on a game is credited
    # with 1/3 of that game's s*ee product.
    L["num"] = L["s"] * L["ee"] / 3.0
    per = L.groupby("ref").agg(num=("num", "sum"), games=("gid", "size"))
    per["slope_share"] = per["num"] / (denom * slope)
    per = per[per["games"] >= 50].sort_values("slope_share", ascending=False)
    tot = per["slope_share"].sum()
    print(f"  {len(per)} officials with >= 50 games in the sample "
          f"(covering {100*tot:.1f}% of the slope)")
    for j in (1, 3, 5, 10):
        print(f"    top {j:2d} officials account for "
              f"{100*per['slope_share'].head(j).sum():6.1f}% of the slope")
    print(f"    officials with positive contribution: "
          f"{(per['slope_share'] > 0).sum()} of {len(per)}")
    hhi = float((per["slope_share"] / tot).pow(2).sum())
    print(f"    HHI of contributions {hhi:.4f} "
          f"(1/{len(per)} = {1/len(per):.4f} would be perfectly even)")
    print("\n    largest individual contributors")
    print(per.head(5)[["games", "slope_share"]].round(4).to_string())

    print("\n  LEAVE-ONE-REFEREE-OUT: drop every game an official worked")
    refset = sorted(set(d["ref1"]) | set(d["ref2"]) | set(d["ref3"]))
    rows = []
    for r in refset:
        m = ~((d["ref1"] == r) | (d["ref2"] == r) | (d["ref3"] == r))
        if m.sum() < 2000:
            continue
        x = d[m]
        b = float(resid(x, "CrewShock", ctrl) @ resid(x, "e", ctrl)) / float(
            resid(x, "CrewShock", ctrl) @ resid(x, "CrewShock", ctrl))
        rows.append({"ref": r, "dropped": int((~m).sum()), "slope": b})
    T = pd.DataFrame(rows).sort_values("slope")
    print(f"    {len(T)} leave-one-out refits   slope range "
          f"[{T['slope'].min():+.4f}, {T['slope'].max():+.4f}]   "
          f"median {T['slope'].median():+.4f}   full-sample {slope:+.4f}")
    print(f"    refits still positive: {(T['slope'] > 0).sum()} of {len(T)}")
    print("    most damaging drops:")
    print(T.head(4).to_string(index=False))

    print("\n" + "=" * 100)
    print("2 — MECHANICAL CHAIN on the definitive CrewShock")
    print("=" * 100)
    print("   each row: Y ~ CrewShock + LeagueFoulState + 11 team controls")
    print(f"    {'link':24} {'coef':>10} {'t':>8} {'per 1sd':>10}")
    sd = d["CrewShock"].std()
    for col, name in (("pf_rate", "fouls per 100 poss"), ("fouls", "raw fouls"),
                      ("fta", "free throw attempts"),
                      ("actual", "ACTUAL TOTAL"),
                      ("total", "CLOSING TOTAL"), ("e", "closing residual")):
        X = np.column_stack([d["CrewShock"]] + [d[c] for c in ctrl])
        b, se, t = ols(d[col].values, X)
        print(f"    {name:24} {b[1]:10.4f} {t[1]:8.2f} {b[1]*sd:10.3f}")
    print(f"    CrewShock sd = {sd:.4f}")

    print("\n" + "=" * 100)
    print(f"3 — SEASON P&L, BET OVER WHEN CrewShock >= {THR:+.4f}")
    print(f"    flat ${STAKE:.0f} at {PRICE}: win +${WIN:.2f}, loss -${STAKE:.0f}, "
          f"push $0   break-even {100*BE:.2f}%")
    print("=" * 100)

    full = refs.build()
    full["gid"] = full["GAME-ID"].astype(str).str.strip()
    feat, _, _, _ = rf.build(save=False)
    full = full.merge(feat[["gid", "CrewShock", "min_prior"]], on="gid",
                      how="inner").dropna(subset=["CrewShock", "e"])

    for lab, x in (("A. FULL UNIVERSE (CrewShock + a total, no control filter)",
                    full),
                   ("B. REGRESSION SAMPLE (controls required)", d)):
        b = x[x["CrewShock"] >= THR].copy()
        print(f"\n  {lab}")
        print(f"    {'season':10} {'bets':>6} {'W':>5} {'L':>5} {'P':>4} "
              f"{'win %':>7} {'$ won':>10} {'ROI %':>8} {'cum $':>11}")
        cum = 0.0
        tot_w = tot_l = tot_p = 0
        for y, g in b.groupby("yr"):
            w = int((g["e"] > 0).sum())
            l = int((g["e"] < 0).sum())
            p = int((g["e"] == 0).sum())
            pnl = w * WIN - l * STAKE
            cum += pnl
            tot_w, tot_l, tot_p = tot_w + w, tot_l + l, tot_p + p
            wp = 100 * w / (w + l) if w + l else np.nan
            roi = 100 * pnl / (STAKE * (w + l)) if w + l else np.nan
            tag = "" if y < 2024 else "  <- holdout"
            print(f"    {y:<10} {len(g):6,} {w:5} {l:5} {p:4} {wp:7.2f} "
                  f"{pnl:10,.0f} {roi:8.2f} {cum:11,.0f}{tag}")
        dev = b[b["date"] < SPLIT_DATE]
        hold = b[b["date"] >= SPLIT_DATE]
        for nm, g in (("DEVELOP", dev), ("HOLDOUT", hold), ("ALL", b)):
            w = int((g["e"] > 0).sum())
            l = int((g["e"] < 0).sum())
            pnl = w * WIN - l * STAKE
            wp = 100 * w / (w + l) if w + l else np.nan
            roi = 100 * pnl / (STAKE * (w + l)) if w + l else np.nan
            se = 1.96 * np.sqrt((wp / 100) * (1 - wp / 100) / (w + l)) * 100
            print(f"    {nm:10} {len(g):6,} {w:5} {l:5} "
                  f"{int((g['e']==0).sum()):4} {wp:7.2f} {pnl:10,.0f} "
                  f"{roi:8.2f}    +/-{se:.2f}pp")
        n = tot_w + tot_l
        if n:
            edge = 100 * tot_w / n - 100 * BE
            need = 7.84 * 0.25 / (edge / 100) ** 2 if edge > 0 else np.nan
            print(f"    edge vs break-even {edge:+.2f}pp;  bets needed to "
                  f"establish it: {need:,.0f}"
                  + (f"  ({need/ (len(b)/8):.0f} seasons at this rate)"
                     if edge > 0 else ""))


if __name__ == "__main__":
    main()
