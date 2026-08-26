"""NATIONAL TELEVISION — executes PREREG_national_tv.md."""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
from prepare_data import read_master, season_label, _side

NPERM = 5000
RNG = np.random.default_rng(42)
DEV_SEASONS = ("2017-2018", "2018-2019", "2020-2021", "2021-2022",
               "2022-2023", "2023 In-Season", "2023-2024")
CTRL = ["to_close", "abs_sp", "weekend", "tip_hour"]


def ols_t(y, cols):
    X = np.column_stack([np.ones(len(y))] + list(cols))
    ok = np.isfinite(y) & np.all(np.isfinite(X), axis=1)
    X, y = X[ok], y[ok]
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = y - X @ b
    n, k = X.shape
    se = np.sqrt(np.diag((r @ r / (n - k)) * np.linalg.pinv(X.T @ X)))
    return b, b / se, int(n)


def oos_r2(tr, te, cols, tgt):
    X = np.column_stack([np.ones(len(tr))] + [tr[c].values for c in cols])
    y = tr[tgt].values
    ok = np.isfinite(y) & np.all(np.isfinite(X), axis=1)
    b, *_ = np.linalg.lstsq(X[ok], y[ok], rcond=None)
    Xt = np.column_stack([np.ones(len(te))] + [te[c].values for c in cols])
    yt = te[tgt].values
    okt = np.isfinite(yt) & np.all(np.isfinite(Xt), axis=1)
    pr, yt = Xt[okt] @ b, yt[okt]
    return 1 - ((yt - pr) @ (yt - pr)) / ((yt - yt.mean()) @ (yt - yt.mean())), int(okt.sum())


def freedman_lane(x, y, keys, ctl, label, one_sided=True):
    """Permute the control-residualised target; controls stay attached."""
    Z = np.column_stack([np.ones(len(x))] + [x[c].values for c in ctl])
    bz, *_ = np.linalg.lstsq(Z, y, rcond=None)
    resid = y - Z @ bz
    kc = [x[k].values for k in keys]
    b, t, n = ols_t(y, kc + [x[c].values for c in ctl])
    obs = np.array([b[i + 1] for i in range(len(keys))])
    yrs = x["season"].values
    blocks = [np.where(yrs == u)[0] for u in np.unique(yrs)]
    null = np.empty((NPERM, len(keys)))
    for i in range(NPERM):
        r = resid.copy()
        for bl in blocks:
            r[bl] = resid[bl][RNG.permutation(len(bl))]
        bb, _, _ = ols_t(Z @ bz + r, kc + [x[c].values for c in ctl])
        null[i] = [bb[j + 1] for j in range(len(keys))]
    for j, k in enumerate(keys):
        p1 = (1 + np.sum(null[:, j] >= obs[j])) / (NPERM + 1)
        p2 = (1 + np.sum(np.abs(null[:, j]) >= abs(obs[j]))) / (NPERM + 1)
        pv = f"p1={p1:.4f}" if one_sided else f"p2={p2:.4f}"
        print(f"    {label} {k:10} n={n:>6,}  beta {obs[j]:+.4f} "
              f"(t={t[j+1]:+.2f})   FL sd {null[:, j].std():.4f}  {pv}")
    return obs, t, null.std(axis=0), n


def build():
    j = pd.read_csv("tv_panel.csv", parse_dates=["date"])
    j["gid"] = j.gid.astype(str).str.strip()
    raw = read_master(verbose=False)
    raw["season"] = season_label(raw)
    raw = raw[raw["season"].astype(str).str.contains(
        "Regular Season|In-Season", na=False)].copy()
    gid = raw["GAME-ID"].astype(str).str.strip()
    hp = _side(raw, "H")["Y"].values.astype(float)
    ap = _side(raw, "R")["Y"].values.astype(float)
    out = pd.DataFrame({"gid": gid.values, "actual_total": hp + ap,
                        "actual_margin": hp - ap})
    d = j.merge(out, on="gid", how="left")

    d["dev"] = d.actual_total - d.to_close
    d["dev_s"] = d.actual_margin + d.sp_close
    d["abs_sp"] = d.sp_close.abs()
    d["weekend"] = d.date.dt.dayofweek.isin([5, 6]).astype(float)
    d["national"] = d.bc_national.astype(float)
    nm = d.bc_names.fillna("")
    only_nbatv = nm.str.replace(r"NBA ?TV", "", case=False, regex=True) \
                   .str.strip("| ").eq("")
    d["nba_tv"] = (d.national.eq(1) & only_nbatv & nm.ne("")).astype(float)
    d["marquee"] = (d.national.eq(1) & d.nba_tv.eq(0)).astype(float)

    rf = pd.read_csv("ref_features.csv")          # FROZEN, read-only
    rf["gid"] = rf.gid.astype(str).str.strip()
    d = d.merge(rf[["gid", "CrewShock"]].drop_duplicates("gid"), on="gid", how="left")

    d["is_dev"] = d.season.str.contains("|".join(DEV_SEASONS))
    for col, floor in (("dev", 8000), ("national", 8000), ("to_close", 8000)):
        n = int(d[col].notna().sum())
        if n < floor:
            raise RuntimeError(f"JOIN FAILURE: {col} on {n} rows (need >= {floor})")
    return d


def main():
    d = build()
    dv = d[d.is_dev]
    print(f"built {len(d):,} games;  development {len(dv):,}  "
          f"holdout {int((~d.is_dev).sum()):,}")
    print(f"  national {int(dv.national.sum()):,} ({100*dv.national.mean():.1f}%)"
          f"   nba_tv {int(dv.nba_tv.sum()):,}   marquee {int(dv.marquee.sum()):,}"
          f"   CrewShock coverage {dv.CrewShock.notna().mean():.3f}")

    x = dv.dropna(subset=["dev", "national"] + CTRL)
    print("\n=== P1 PRIMARY — dev ~ national + controls (predicted > 0) ===")
    obs, t, nsd, n1 = freedman_lane(x, x.dev.values, ["national"], CTRL, "P1")

    print("\n=== P2 MECHANISM vs ATTENTION — interpretive, no pass/fail ===")
    freedman_lane(x, x.dev.values, ["nba_tv", "marquee"], CTRL, "P2",
                  one_sided=False)

    print("\n=== P3 CREW ASSIGNMENT — CrewShock ~ national (frozen, read-only) ===")
    xc = dv.dropna(subset=["CrewShock", "national"] + CTRL)
    freedman_lane(xc, xc.CrewShock.values, ["national"], CTRL, "P3",
                  one_sided=False)

    print("\n=== P4 SPREAD — dev_s ~ national (two-sided) ===")
    xs = dv.dropna(subset=["dev_s", "national"] + CTRL)
    freedman_lane(xs, xs.dev_s.values, ["national"], CTRL, "P4", one_sided=False)

    print("\n=== SECTION 5 INCREMENTAL (holdout, scored once) ===")
    tr = d[d.is_dev].dropna(subset=["dev", "national"] + CTRL)
    for lab, sub in (("pooled  ", d[~d.is_dev]),
                     ("2024-25 ", d[d.season.str.contains("2024-2025|2024 In-Season")]),
                     ("2025-26 ", d[d.season.str.contains("2025-2026|2025 In-Season")])):
        te = sub.dropna(subset=["dev", "national"] + CTRL)
        A, _ = oos_r2(tr, te, CTRL, "dev")
        B, nB = oos_r2(tr, te, CTRL + ["national"], "dev")
        print(f"    {lab} n_ho={nB:>5,}  A {A:+.6f}   B(+national) {B:+.6f}   "
              f"B-A {B-A:+.6f}   {'B WINS' if B > A else 'A WINS'}")

    print("\n=== SECTION 7 MINIMUM DETECTABLE EFFECT ===")
    mde = 1.96 * nsd[0]
    print(f"    FL sd of beta_national  {nsd[0]:.4f} total points")
    print(f"    MDE at 95%              {mde:.4f} total points")
    print(f"    observed                {obs[0]:+.4f} total points")
    # points -> hit-rate edge is the NORMAL DENSITY at the line, phi(0)/sigma,
    # NOT 1/sigma. Using 1/sigma overstates the edge by 1/0.3989 = 2.5x.
    sd_dev = float(np.nanstd(x.dev.values))
    dens = 0.3989 / sd_dev
    for lab, pts in (("MDE", mde), ("observed", abs(obs[0]))):
        e = pts * dens
        print(f"    {lab:9} {pts:.4f} pts -> {100*e:.2f}pp edge -> "
              f"n = {7.84*0.25/max(e,1e-9)**2:,.0f} games at 1 bet/game")
    print(f"    (sd of dev = {sd_dev:.2f}; density {dens:.4f} pp per point)")


if __name__ == "__main__":
    main()
