"""SPREAD replication of the MOVE_COMBINED program. Strict, one pass, stop.

Components:
  ridge  = cal_margin - open_margin from walkforward_games.csv (the frozen
           walk-forward margin model's implied move view). Coverage ends
           2023-24; pre-noted: its pooled corr with the realized spread move
           is ~0.000 -- the model was built against the CLOSE, not the move.
  latent = PCA-OLS on a SPREAD-SPECIFIC error-state matrix (relative
           residuals, per the spec): for each of scoreerr / allowerr / sprerr,
           HOME-AWAY differences of all 11 transforms (33), plus both sides'
           full sprerr set (22), plus toterr rm10 sum and diff (2) = 57
           features. Same season folds, cumEV>=80% rule, strictly prior-only.

Steps (fixed): triangle on the latent; joint incremental test; recursive OOS
combiner; fixed economic grid at the OPEN spread incl 0.5-pt adverse
execution; season-by-season CLV. No threshold optimization, no variance work.

Decision rule (user-fixed): CLV >~ +0.75 in a populated fixed bucket, monotone,
season-consistent -> freeze SPREAD_MOVE_COMBINED; else close the branch.
Scale note: spread residual sd ~13.4 -> ~2.97pp/point at the money, so
+0.75 pts of spread CLV ~ 2.2pp (comparable to totals' +1.34 x 2.2pp/pt).
"""
import warnings

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")

from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

import opening_line_error_decomposition as OLE

EV_THRESH = 0.80
BE = 110.0 / 210.0


def spread_features(X):
    base = ["scoreerr", "allowerr", "sprerr"]
    tf = [f"lag{i}" for i in (1, 2, 3)] + \
         [f"rm{w}" for w in (3, 5, 10, 20)] + \
         [f"sd{w}" for w in (5, 10, 20)] + ["ewm"]
    cols = []
    for st in base:
        for t in tf:
            X[f"rel_{st}_{t}"] = X[f"h_{st}_{t}"] - X[f"a_{st}_{t}"]
            cols.append(f"rel_{st}_{t}")
    for t in tf:
        cols += [f"h_sprerr_{t}", f"a_sprerr_{t}"]
    X["sum_toterr10"] = X["h_toterr_rm10"] + X["a_toterr_rm10"]
    X["dif_toterr10"] = X["h_toterr_rm10"] - X["a_toterr_rm10"]
    cols += ["sum_toterr10", "dif_toterr10"]
    return X, cols


def pca_oos(X, featcols, targets):
    preds = {t: np.full(len(X), np.nan) for t in targets}
    seasons = sorted(X["season"].unique())
    for i in range(2, len(seasons)):
        tr = (X["season"] < seasons[i]).values
        te = (X["season"] == seasons[i]).values
        sc = StandardScaler().fit(X.loc[tr, featcols])
        Ztr, Zte = sc.transform(X.loc[tr, featcols]), \
            sc.transform(X.loc[te, featcols])
        p = PCA(n_components=min(30, Ztr.shape[1])).fit(Ztr)
        K = int(np.searchsorted(np.cumsum(p.explained_variance_ratio_),
                                EV_THRESH) + 1)
        Str, Ste = p.transform(Ztr)[:, :K], p.transform(Zte)[:, :K]
        for t in targets:
            A = np.column_stack([np.ones(Str.shape[0]), Str])
            b, *_ = np.linalg.lstsq(A, X.loc[tr, t].values, rcond=None)
            preds[t][te] = np.column_stack(
                [np.ones(Ste.shape[0]), Ste]) @ b
    return preds


def grid(D, col, label, adverse=0.0):
    tag = f"  (adverse {adverse:.1f})" if adverse else ""
    print(f"\n  {label}{tag}   forecast sd {D[col].std():.3f}, "
          f"corr with smove {np.corrcoef(D[col], D['smove'])[0,1]:+.4f}")
    print(f"  {'thr':>5}{'n':>7}{'win %':>8}{'ROI %':>8}{'t vs BE':>9}"
          f"{'mean CLV':>10}{'beat close %':>14}")
    for thr in (0.0, 0.5, 1.0, 1.5, 2.0, 2.5):
        b = D[D[col].abs() >= thr]
        if len(b) < 30:
            continue
        home = b[col] > 0
        line = np.where(home, b["om_open"] + adverse,
                        b["om_open"] - adverse)
        res = b["margin"].values - line
        push = res == 0
        win = np.where(home, res > 0, res < 0)[~push]
        if len(win) < 30:
            continue
        wr = win.mean()
        roi = wr * 100 / 110 - (1 - wr)
        se = np.sqrt(wr * (1 - wr) / len(win))
        clv = np.where(home, b["smove"], -b["smove"])
        print(f"  {thr:>5.1f}{len(win):>7,}{100*wr:>8.2f}{100*roi:>8.2f}"
              f"{(wr-BE)/se:>9.2f}{clv.mean():>10.3f}"
              f"{100*(clv>0).mean():>14.1f}")


def main():
    g = OLE.load()
    X, _ = OLE.design_matrix(g)
    X, fcols = spread_features(X)
    print(f"\n  {len(X):,} games, {len(fcols)} SPREAD-specific error-state "
          f"features")
    print(f"  smove sd {X['smove'].std():.3f}   se_open sd "
          f"{X['se_open'].std():.3f}")

    lat = pca_oos(X, fcols, ["smove"])["smove"]
    ok = ~np.isnan(lat)
    D = X.loc[ok, ["gid", "season", "margin", "om_open", "se_open",
                   "se_close", "smove", "date"]].copy()
    D["latent"] = lat[ok]

    print("\n" + "=" * 92)
    print("STEP 6 FIRST — THE TRIANGLE (spread-specific latent, pooled OOS)")
    print("=" * 92)
    n = len(D)
    tt = lambda c: c * np.sqrt(n - 2) / np.sqrt(1 - c ** 2)
    for y, nm in (("se_open", "ActualMargin - OpenMargin"),
                  ("smove", "CloseMargin - OpenMargin"),
                  ("se_close", "ActualMargin - CloseMargin")):
        c = np.corrcoef(D[y], D["latent"])[0, 1]
        print(f"  corr(latent, {nm:26}) = {c:+.4f}  (t={tt(c):+.2f})")

    print("\n" + "=" * 92)
    print("STEPS 1-3 — JOINT INCREMENTAL TEST on common OOS games")
    print("=" * 92)
    w = pd.read_csv("walkforward_games.csv")
    w["date"] = pd.to_datetime(w["date"])
    w["ridge"] = w["cal_margin"] - w["open_margin"]
    key = ["date", "om_open", "margin"]
    w2 = w.rename(columns={"open_margin": "om_open",
                           "actual_margin": "margin"})
    w2 = w2[key + ["ridge"]].drop_duplicates(key, keep=False)
    D2 = D.drop_duplicates(key, keep=False).merge(w2, on=key,
                                                  how="inner").dropna()
    print(f"  common OOS games {len(D2):,}  seasons "
          f"{sorted(D2['season'].unique())}   [ridge file ends 2023-24]")
    for nm, cols in (("ridge alone", ["ridge"]),
                     ("latent alone", ["latent"]),
                     ("BOTH", ["ridge", "latent"])):
        A = np.column_stack([np.ones(len(D2))] + [D2[c] for c in cols])
        b, *_ = np.linalg.lstsq(A, D2["smove"], rcond=None)
        r = D2["smove"] - A @ b
        se = np.sqrt(np.diag(np.linalg.pinv(A.T @ A)) * (r @ r)
                     / (len(D2) - A.shape[1]))
        r2 = 1 - r.var() / D2["smove"].var()
        s = "   ".join(f"{c} {b[i+1]:+.4f} (t={b[i+1]/se[i+1]:+.2f})"
                       for i, c in enumerate(cols))
        print(f"  {nm:14} R2 {r2:.5f}   {s}")
    print(f"  corr(ridge, latent) = "
          f"{np.corrcoef(D2['ridge'], D2['latent'])[0, 1]:+.4f}")

    print("\n" + "=" * 92)
    print("STEP 4 — RECURSIVE COMBINER (weights from prior OOS seasons only)")
    print("=" * 92)
    seasons = sorted(D2["season"].unique())
    D2["combined"] = np.nan
    for i, yr in enumerate(seasons):
        if i == 0:
            continue
        tr, te = D2["season"] < yr, D2["season"] == yr
        A = np.column_stack([np.ones(tr.sum()), D2.loc[tr, "ridge"],
                             D2.loc[tr, "latent"]])
        b, *_ = np.linalg.lstsq(A, D2.loc[tr, "smove"], rcond=None)
        D2.loc[te, "combined"] = (b[0] + b[1] * D2.loc[te, "ridge"]
                                  + b[2] * D2.loc[te, "latent"])
        print(f"  test {yr}: a {b[0]:+.3f}  ridge {b[1]:+.3f}  "
              f"latent {b[2]:+.3f}  (train n={tr.sum():,})")
    C = D2.dropna(subset=["combined"])

    print("\n" + "=" * 92)
    print("STEP 5 — FIXED ECONOMIC GRID at the OPEN spread, -110")
    print("=" * 92)
    grid(C, "combined", f"COMBINED (recursive, {len(C):,} games "
         f"{sorted(C['season'].unique())})")
    grid(D, "latent", f"LATENT ALONE (full OOS, {len(D):,} games "
         f"{sorted(D['season'].unique())})")
    grid(D, "latent", "LATENT ALONE", adverse=0.5)

    print("\n  season-by-season CLV, latent alone at |m| >= 0.5:")
    for yr, s in D.groupby("season"):
        b = s[s["latent"].abs() >= 0.5]
        if len(b) < 20:
            continue
        home = b["latent"] > 0
        clv = np.where(home, b["smove"], -b["smove"])
        res = b["margin"] - b["om_open"]
        win = np.where(home, res > 0, res < 0)[res != 0]
        print(f"    {yr}: n={len(b):>4}  win {100*win.mean():5.2f}%  "
              f"CLV {clv.mean():+.3f}")


if __name__ == "__main__":
    main()
