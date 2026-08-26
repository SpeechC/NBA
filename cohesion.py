"""LINEUP COHESION — executes PREREG_cohesion.md."""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
from prepare_data import read_master, season_label, _side

NPERM = 5000
RNG = np.random.default_rng(42)
DEV = ["2017-18", "2018-19", "2020-21", "2021-22", "2022-23"]
HOLD = ["2023-24", "2024-25"]
NBIN = 10


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


def freedman_lane(x, y, key, ctl, label, one_sided=True):
    Z = np.column_stack([np.ones(len(x))] + [x[c].values for c in ctl])
    bz, *_ = np.linalg.lstsq(Z, y, rcond=None)
    resid = y - Z @ bz
    b, t, n = ols_t(y, [x[key].values] + [x[c].values for c in ctl])
    obs = b[1]
    yrs = x["season"].values
    blocks = [np.where(yrs == u)[0] for u in np.unique(yrs)]
    null = np.empty(NPERM)
    for i in range(NPERM):
        r = resid.copy()
        for bl in blocks:
            r[bl] = resid[bl][RNG.permutation(len(bl))]
        bb, _, _ = ols_t(Z @ bz + r, [x[key].values] + [x[c].values for c in ctl])
        null[i] = bb[1]
    p1 = (1 + np.sum(null >= obs)) / (NPERM + 1)
    p2 = (1 + np.sum(np.abs(null) >= abs(obs))) / (NPERM + 1)
    pv = f"p1={p1:.4f}" if one_sided else f"p2={p2:.4f}"
    print(f"    {label:32} n={n:>6,}  beta {obs:+.4f} (t={t[1]:+.2f})  "
          f"FL sd {null.std():.4f}  {pv}")
    return obs, t[1], (p1 if one_sided else p2), null.std()


def build():
    c = pd.read_csv("cohesion_panel.csv")
    c["gid"] = c.gid.astype(str).str.strip()

    raw = read_master(verbose=False)
    raw["season"] = season_label(raw)
    raw = raw[raw["season"].astype(str).str.contains(
        "Regular Season|In-Season", na=False)].copy()
    gid = raw["GAME-ID"].astype(str).str.strip()
    hp = _side(raw, "H")["Y"].values.astype(float)
    ap = _side(raw, "R")["Y"].values.astype(float)
    m = pd.DataFrame({
        "gid": gid.values,
        "home": raw["TEAM_H"].astype(str).str.strip().values,
        "away": raw["TEAM_R"].astype(str).str.strip().values,
        "to_close": pd.to_numeric(raw["CLOSING TOTAL_H"], errors="coerce").values,
        "sp_close": pd.to_numeric(raw["CLOSING SPREAD_H"], errors="coerce").values,
        "actual_total": hp + ap, "actual_margin": hp - ap})

    # cohesion rows carry team ABBREVIATIONS; map to the master's city names
    from tip_time_structure import ABBR
    c["city"] = c.team.map(ABBR)
    j = m.merge(c[["gid", "city", "cohesion", "gameno"]], on="gid", how="inner")
    H = j[j.city == j.home].set_index("gid")
    A = j[j.city == j.away].set_index("gid")
    d = m.set_index("gid").copy()
    d["coh_H"] = H["cohesion"]; d["gn_H"] = H["gameno"]
    d["coh_A"] = A["cohesion"]; d["gn_A"] = A["gameno"]
    d["season"] = c.drop_duplicates("gid").set_index("gid")["season"]
    d = d.dropna(subset=["coh_H", "coh_A"]).reset_index()

    d["C_diff"] = d.coh_H - d.coh_A
    d["C_sum"] = d.coh_H + d.coh_A
    d["dev"] = d.actual_total - d.to_close
    d["dev_s"] = d.actual_margin + d.sp_close
    d["abs_sp"] = d.sp_close.abs()
    for tag in ("H", "A"):
        b = pd.cut(d[f"gn_{tag}"], NBIN, labels=False)
        for k in range(1, NBIN):
            d[f"gb{tag}{k}"] = (b == k).astype(float)
    d["is_dev"] = d.season.isin(DEV)

    for col, floor in (("dev_s", 5000), ("C_diff", 5000), ("to_close", 5000)):
        n = int(d[col].notna().sum())
        if n < floor:
            raise RuntimeError(f"JOIN FAILURE: {col} on {n} rows (need >= {floor})")
    return d


CTRL = ([f"gb{t}{k}" for t in ("H", "A") for k in range(1, NBIN)]
        + ["to_close", "abs_sp"])


def main():
    d = build()
    dv = d[d.is_dev]
    print(f"built {len(d):,} games;  development {len(dv):,}  "
          f"holdout {int((~d.is_dev).sum()):,}")
    print(f"  C_diff mean {dv.C_diff.mean():+.4f} sd {dv.C_diff.std():.4f}   "
          f"C_sum mean {dv.C_sum.mean():.3f} sd {dv.C_sum.std():.3f}")

    print("\n=== P3 POSITIVE CONTROL — actual_margin ~ C_diff (no market) ===")
    xp = dv.dropna(subset=["actual_margin", "C_diff"] + CTRL)
    freedman_lane(xp, xp.actual_margin.values, "C_diff", CTRL,
                  "P3 C_diff -> margin (>0)")

    print("\n=== P1 PRIMARY — dev_s ~ C_diff + controls (predicted > 0) ===")
    x = dv.dropna(subset=["dev_s", "C_diff"] + CTRL)
    obs, tt, p1, nsd = freedman_lane(x, x.dev_s.values, "C_diff", CTRL,
                                     "P1 C_diff -> dev_s (>0)")

    print("\n=== P2 SECONDARY — dev ~ C_sum (TWO-SIDED, direction ambiguous) ===")
    xt = dv.dropna(subset=["dev", "C_sum"] + CTRL)
    freedman_lane(xt, xt.dev.values, "C_sum", CTRL, "P2 C_sum -> dev",
                  one_sided=False)

    print("\n=== SECTION 5 INCREMENTAL (holdout, scored once) ===")
    tr = d[d.is_dev].dropna(subset=["dev_s", "C_diff"] + CTRL)
    for lab, sub in (("pooled ", d[~d.is_dev]),
                     ("2023-24", d[d.season.eq("2023-24")]),
                     ("2024-25", d[d.season.eq("2024-25")])):
        te = sub.dropna(subset=["dev_s", "C_diff"] + CTRL)
        A, _ = oos_r2(tr, te, CTRL, "dev_s")
        B, nB = oos_r2(tr, te, CTRL + ["C_diff"], "dev_s")
        print(f"    {lab} n_ho={nB:>5,}  A {A:+.6f}   B(+C_diff) {B:+.6f}   "
              f"B-A {B-A:+.6f}   {'B WINS' if B > A else 'A WINS'}")

    print("\n=== SECTION 7 MINIMUM DETECTABLE EFFECT ===")
    mde = 1.96 * nsd
    sd_t = float(np.nanstd(x.dev_s.values))
    dens = 0.3989 / sd_t
    print(f"    FL sd of beta {nsd:.4f}   MDE(95%) {mde:.4f} pts per unit of C_diff")
    print(f"    observed {obs:+.4f};  1 SD of C_diff = {x.C_diff.std():.3f} "
          f"-> observed {obs*x.C_diff.std():+.4f} pts, MDE {mde*x.C_diff.std():.4f} pts")
    for lab, pts in (("MDE", mde * x.C_diff.std()),
                     ("observed", abs(obs) * x.C_diff.std())):
        e = pts * dens
        print(f"    {lab:9} {pts:.4f} pts -> {100*e:.2f}pp -> "
              f"n = {7.84*0.25/max(e,1e-9)**2:,.0f} games")
    print(f"    (sd of dev_s = {sd_t:.2f}; density {dens:.4f} pp per point)")


if __name__ == "__main__":
    main()
