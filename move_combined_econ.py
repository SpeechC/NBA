"""ONE retrospective economic test of the combined movement forecast.

Per instruction: no further searching. Reconstruct the combined signal
PROPERLY WALK-FORWARD -- the Part-1 joint coefficients were fit on pooled OOS
predictions, which is in-sample for the combination weights, so here the
combiner is refit each season on ONLY prior seasons' accumulated OOS
predictions (both component forecasts are available in real time):

    fold i:  weights (a, b1, b2) from OLS of move on (ridge, latent) over all
             OOS games in seasons < i;  applied to season i.

First combined season is therefore 2021-22 (needs >= 1 prior joint-OOS
season). Ridge-alone is evaluated on the IDENTICAL games as the comparator.

Fixed grid, stated in advance: thresholds 0 / .5 / 1 / 1.5 / 2 / 2.5 on |m|.
Bet at the OPENER at -110: over if m > 0. CLV = sign-adjusted (close - open).
Nothing else is computed.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import opening_line_error_decomposition as OLE
import resid_variance as RV

BE = 110.0 / 210.0


def grid(D, col, label):
    print(f"\n  {label}   (forecast sd {D[col].std():.3f}, "
          f"corr with move {np.corrcoef(D[col], D['tmove'])[0,1]:+.4f})")
    print(f"  {'thr':>5}{'n':>7}{'win %':>8}{'ROI %':>8}{'t vs BE':>9}"
          f"{'mean CLV':>10}{'beat close %':>14}")
    rows = []
    for thr in (0.0, 0.5, 1.0, 1.5, 2.0, 2.5):
        b = D[D[col].abs() >= thr]
        if len(b) < 30:
            continue
        over = b[col] > 0
        push = b["total"] == b["ot_open"]
        live = ~push
        win = np.where(over, b["total"] > b["ot_open"],
                       b["total"] < b["ot_open"])[live]
        wr = win.mean()
        roi = wr * 100 / 110 - (1 - wr)
        se = np.sqrt(wr * (1 - wr) / live.sum())
        clv = np.where(over, b["tmove"], -b["tmove"])
        rows.append((thr, live.sum(), wr, roi, clv.mean(),
                     (clv > 0).mean()))
        print(f"  {thr:>5.1f}{live.sum():>7,}{100*wr:>8.2f}{100*roi:>8.2f}"
              f"{(wr-BE)/se:>9.2f}{clv.mean():>10.3f}"
              f"{100*(clv>0).mean():>14.1f}")
    return rows


def main():
    g = OLE.load()
    X, featcols = OLE.design_matrix(g)
    lat = RV.pca_oos(X, featcols, ["tmove"])["tmove"]
    ok = ~np.isnan(lat)
    D = X.loc[ok, ["gid", "season", "date", "tmove", "total", "ot_open",
                   "ot_close"]].copy()
    D["latent"] = lat[ok]
    mv = pd.read_csv("movement_full_games.csv",
                     usecols=["game_id", "pred_move", "clean"])
    mv["gid"] = mv["game_id"].astype(str).str.strip()
    D = D.merge(mv.loc[mv["clean"] == True, ["gid", "pred_move"]],
                on="gid", how="inner").dropna()

    seasons = sorted(D["season"].unique())
    D["combined"] = np.nan
    print("WALK-FORWARD COMBINER WEIGHTS (fit on prior OOS seasons only)")
    for i, yr in enumerate(seasons):
        if i == 0:
            continue
        tr = D["season"] < yr
        te = D["season"] == yr
        A = np.column_stack([np.ones(tr.sum()), D.loc[tr, "pred_move"],
                             D.loc[tr, "latent"]])
        b, *_ = np.linalg.lstsq(A, D.loc[tr, "tmove"], rcond=None)
        D.loc[te, "combined"] = (b[0] + b[1] * D.loc[te, "pred_move"]
                                 + b[2] * D.loc[te, "latent"])
        print(f"  test {yr}: a {b[0]:+.3f}  ridge {b[1]:+.3f}  "
              f"latent {b[2]:+.3f}   (train n={tr.sum():,})")
    C = D.dropna(subset=["combined"]).copy()
    print(f"\n  combined-signal OOS sample: {len(C):,} games, seasons "
          f"{sorted(C['season'].unique())}")

    print("\n" + "=" * 92)
    print("FIXED ECONOMIC GRID — bet at the opener at -110")
    print("=" * 92)
    grid(C, "combined", "COMBINED (walk-forward weights)")
    grid(C, "pred_move", "RIDGE ALONE (same games)")

    print("\n  season-by-season at |m| >= 1.0:")
    print(f"  {'season':>8}{'model':>10}{'n':>6}{'win %':>8}{'mean CLV':>10}")
    for col, nm in (("combined", "combined"), ("pred_move", "ridge")):
        for yr, s in C.groupby("season"):
            b = s[s[col].abs() >= 1.0]
            over = b[col] > 0
            live = b["total"] != b["ot_open"]
            win = np.where(over, b["total"] > b["ot_open"],
                           b["total"] < b["ot_open"])[live]
            clv = np.where(over, b["tmove"], -b["tmove"])
            print(f"  {yr:>8}{nm:>10}{live.sum():>6,}{100*win.mean():>8.2f}"
                  f"{clv.mean():>10.3f}")


if __name__ == "__main__":
    main()
