"""Does the second-half total price CrewShock?

Executes PREREG_h2_crewshock.md exactly. CrewShock, LeagueFoulState, the N=60
estimator and the frozen threshold are loaded, never rebuilt.

SETTLEMENT: the OT convention could not be established from the data (OT games
are a selected subset, so both gradings shift their residual for reasons
unrelated to settlement). Per the pre-registration, NON-OT games are the primary
market-residual sample; the full sample is reported as sensitivity only.
Mechanism tests use regulation halves throughout, which is unambiguous.

Halftime information set used as controls -- what the book demonstrably sees
when it posts: pregame closing total, pregame closing spread, H1 points,
H1 margin, LeagueFoulState.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import h2_audit
import ref_features as rf
from data_split import SPLIT_DATE
from dispersion_priced import ols

DEV_MAX, SEALED = 2023, 2024
NPERM = 1000
BLOCK_DAYS = 7
RNG = np.random.default_rng(51413)
HT = ["pre_total", "pre_spread", "pts_h1", "h1_margin", "LeagueFoulState"]


def build():
    d = h2_audit.build()
    n = lambda c: pd.to_numeric(d[c], errors="coerce")
    d["pre_total"] = n("CLOSING TOTAL_H")
    d["pre_spread"] = n("CLOSING SPREAD_H")
    d["ot_pts"] = sum(n(f"OT{i}_{s}").fillna(0) for i in range(1, 6)
                      for s in ("H", "R"))
    d["h1_margin"] = (n("1Q_H") + n("2Q_H")) - (n("1Q_R") + n("2Q_R"))
    d["h2_resid"] = d["pts_h2"] - d["h2_line"]
    d = d.dropna(subset=["CrewShock", "fouls_h2", "fouls_h1"] + HT)
    return d.reset_index(drop=True)


def reg(x, y, extra=()):
    # drop any extra control already present in HT, else the design is singular
    extra = [c for c in extra if c not in HT]
    X = np.column_stack([x["CrewShock"]] + [x[c] for c in extra]
                        + [x[c] for c in HT])
    b, se, t = ols(x[y].values, X)
    return b[1], se[1], t[1]


def main():
    d = build()
    mk = d.dropna(subset=["h2_line", "h2_resid"])
    print(f"  mechanism sample {len(d):,}   market sample {len(mk):,}")
    dev, seal = d[d["yr"] <= DEV_MAX], d[d["yr"] == SEALED]
    mdev = mk[(mk["yr"] <= DEV_MAX) & (mk["ot_pts"] == 0)]
    mseal = mk[(mk["yr"] == SEALED) & (mk["ot_pts"] == 0)]
    print(f"  development {len(dev):,} / market non-OT {len(mdev):,}")
    print(f"  SEALED 2024-25 {len(seal):,} / market non-OT {len(mseal):,}")

    print("\n" + "=" * 96)
    print("THE KEY TEST — H2 fouls conditional on realized H1 fouls")
    print("  H2Fouls ~ CrewShock + H1Fouls + halftime information set")
    print("=" * 96)
    print(f"  {'window':16}{'b_CrewShock':>14}{'t':>8}{'b_H1Fouls':>12}{'t':>8}")
    for lab, x in (("development", dev), ("SEALED 2024-25", seal),
                   ("pooled", d)):
        X = np.column_stack([x["CrewShock"], x["fouls_h1"]]
                            + [x[c] for c in HT])
        b, se, t = ols(x["fouls_h2"].values, X)
        print(f"  {lab:16}{b[1]:+14.4f}{t[1]:8.2f}{b[2]:+12.4f}{t[2]:8.2f}")
    print("\n  unconditional reference (no H1 fouls control)")
    for lab, x in (("development", dev), ("SEALED 2024-25", seal)):
        b, se, t = reg(x, "fouls_h2")
        print(f"  {lab:16}{b:+14.4f}{t:8.2f}")

    print("\n" + "=" * 96)
    print("THE CHAIN, each conditional on its own H1 realization")
    print("=" * 96)
    print(f"  {'link':26}{'development':>22}{'SEALED 2024-25':>22}")
    for y, ctrl, nm in (("fouls_h2", ("fouls_h1",), "H2 fouls | H1 fouls"),
                        ("fta_h2", ("fta_h1",), "H2 FTA | H1 FTA"),
                        ("pts_h2", ("pts_h1",), "H2 points | H1 points"),
                        ("poss_h2", ("poss_h1",), "H2 poss | H1 poss [placebo]")):
        cells = []
        for x in (dev, seal):
            b, se, t = reg(x, y, ctrl)
            cells.append(f"{b:+11.4f} (t={t:+5.2f})")
        print(f"  {nm:26}{cells[0]:>22}{cells[1]:>22}")

    print("\n" + "=" * 96)
    print("MARKET — c_market vs c_true on the 2H line (non-OT primary)")
    print("=" * 96)
    print(f"  {'window':16}{'c_market':>12}{'t':>8}{'c_true':>10}{'t':>8}"
          f"{'gap':>10}")
    for lab, x in (("development", mdev), ("SEALED 2024-25", mseal),
                   ("pooled non-OT", mk[mk["ot_pts"] == 0])):
        bm, _, tm = reg(x, "h2_line")
        bt, _, tt = reg(x, "pts_h2")
        print(f"  {lab:16}{bm:+12.4f}{tm:8.2f}{bt:+10.4f}{tt:8.2f}"
              f"{bt-bm:+10.4f}")
    print("\n  sensitivity: full sample including OT games, graded Q3+Q4")
    for lab, x in (("development", mk[(mk['yr'] <= DEV_MAX)]),
                   ("SEALED 2024-25", mk[mk["yr"] == SEALED])):
        bm, _, tm = reg(x, "h2_line")
        bt, _, tt = reg(x, "pts_h2")
        print(f"  {lab:16}{bm:+12.4f}{tm:8.2f}{bt:+10.4f}{tt:8.2f}"
              f"{bt-bm:+10.4f}")

    print("\n" + "=" * 96)
    print("2H RESIDUAL ~ CrewShock + halftime information set (non-OT)")
    print("=" * 96)
    for lab, x in (("development", mdev), ("SEALED 2024-25", mseal),
                   ("pooled non-OT", mk[mk["ot_pts"] == 0])):
        b, se, t = reg(x, "h2_resid")
        print(f"  {lab:16} b {b:+.4f}  se {se:.4f}  t={t:+.2f}   "
              f"n={len(x):,}  mean resid {x['h2_resid'].mean():+.3f}")

    print("\n  monotonicity — development-frozen CrewShock quintiles, non-OT")
    q = mdev["CrewShock"].quantile([0, .2, .4, .6, .8, 1.0]).values.copy()
    q[0], q[-1] = -np.inf, np.inf
    for lab, x in (("development", mdev), ("SEALED 2024-25", mseal)):
        x = x.copy()
        x["b"] = pd.cut(x["CrewShock"], q, labels=[1, 2, 3, 4, 5])
        print(f"    {lab}")
        print(f"      {'Q':>3}{'n':>7}{'CrewShock':>11}{'mean resid':>12}"
              f"{'over %':>9}")
        for bq, g in x.groupby("b", observed=True):
            print(f"      {bq:>3}{len(g):7,}{g['CrewShock'].mean():11.3f}"
                  f"{g['h2_resid'].mean():12.3f}"
                  f"{100*(g['h2_resid'] > 0).mean():9.2f}")

    print("\n" + "=" * 96)
    print(f"TIME-LOCAL PERMUTATION, {NPERM} reshuffles")
    print("=" * 96)
    uni = rf.universe()
    uni["gid"] = uni["gid"].astype(str).str.strip()
    k = rf.estimate_k(uni)[0]
    blk = (uni["yr"].astype(str) + "_"
           + ((uni["date"] - uni.groupby("yr")["date"].transform("min"))
              .dt.days // BLOCK_DAYS).astype(str)).values
    crew = uni[["ref1", "ref2", "ref3"]].values
    blocks = [np.where(blk == b)[0] for b in pd.unique(blk)]
    idx = pd.Series(np.arange(len(uni)), index=uni["gid"])
    targets = {
        "H2 fouls | H1 fouls (dev)": (dev, "fouls_h2", ("fouls_h1",)),
        "H2 resid (dev, non-OT)": (mdev, "h2_resid", ()),
    }
    obs = {kk: reg(v[0], v[1], v[2])[0] for kk, v in targets.items()}
    null = {kk: np.empty(NPERM) for kk in targets}
    sub = uni.copy()
    maps = {kk: idx.reindex(v[0]["gid"]).values for kk, v in targets.items()}
    for j in range(NPERM):
        perm = crew.copy()
        for b in blocks:
            if len(b) > 1:
                perm[b] = crew[b][RNG.permutation(len(b))]
        sub["ref1"], sub["ref2"], sub["ref3"] = perm[:, 0], perm[:, 1], perm[:, 2]
        cs = rf.matched_ref_effect(sub, k)["CrewShock"].values
        for kk, (x, y, ctrl) in targets.items():
            xx = x.copy()
            xx["CrewShock"] = cs[maps[kk]]
            null[kk][j] = reg(xx, y, ctrl)[0]
    for kk in targets:
        o, n_ = obs[kk], null[kk]
        z = (o - n_.mean()) / n_.std()
        p = (1 + (n_ >= o).sum()) / (NPERM + 1)
        print(f"  {kk:28} observed {o:+.4f}   null {n_.mean():+.4f} "
              f"sd {n_.std():.4f}   z={z:+.2f}   one-sided p={p:.4f}")


if __name__ == "__main__":
    main()
