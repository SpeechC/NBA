"""PREREG_ref_fatigue.md — run once. Referee schedule fatigue -> totals."""
import warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
import ref_shock as rsk

NPERM = 5000
RNG = np.random.default_rng(20260826)


def build():
    d = rsk.build()                      # gid, date, yr, ref1-3, CTRL, fouls, fta, actual, total, e, CrewFoul
    d = d.sort_values("date").reset_index(drop=True)
    # ---- per-official prior-only rest / load ---------------------------------
    L = pd.concat([pd.DataFrame({"row": np.arange(len(d)), "date": d["date"],
                                 "ref": d[f"ref{i}"]}) for i in (1, 2, 3)])
    L = L.dropna(subset=["ref"]).sort_values(["ref", "date"], kind="stable")
    L["rest"] = L.groupby("ref")["date"].diff().dt.days
    L["nprior"] = L.groupby("ref").cumcount()
    # trailing 7d count, EXCLUSIVE of the current game
    load = []
    for ref, s in L.groupby("ref", sort=False):
        dts = s["date"].values
        load.append(pd.Series(
            [int(((dts[i] - dts[:i]) <= np.timedelta64(7, "D")).sum()) for i in range(len(dts))],
            index=s.index))
    L["load7"] = pd.concat(load)
    L["b2b"] = (L["rest"] == 1).astype(float)
    g = L.groupby("row").agg(CREW_B2B_N=("b2b", "sum"),
                             CREW_LOAD7=("load7", "sum"),
                             MIN_NPRIOR=("nprior", "min"))
    d = d.join(g)
    d = d[d["MIN_NPRIOR"] >= 10].reset_index(drop=True)      # warm-up rule
    return d


def ols(y, X):
    A = np.column_stack([np.ones(len(y))] + list(X))
    b, *_ = np.linalg.lstsq(A, y, rcond=None)
    r = y - A @ b
    se = np.sqrt(np.diag(np.linalg.pinv(A.T @ A)) * (r @ r) / (len(y) - A.shape[1]))
    return b, b / se


def link(x, target, state, lab):
    X = [x[state].values] + [x[c].values for c in rsk.CTRL]
    b, t = ols(x[target].values, X)
    print(f"    {lab:34}{b[1]:>+10.4f}{t[1]:>8.2f}")
    return b[1], t[1]


def main():
    d = build()
    dev = d[d["yr"] <= 2023]
    q75 = dev["CREW_LOAD7"].quantile(0.75)
    d["CREW_FATIGUE"] = ((d["CREW_B2B_N"] >= 1) & (d["CREW_LOAD7"] >= q75)).astype(float)
    dev, hold = d[d["yr"] <= 2023], d[d["yr"] >= 2024]
    print(f"  games {len(d):,}  dev {len(dev):,}  holdout {len(hold):,}")
    print(f"  FROZEN dev Q75 of CREW_LOAD7 = {q75:.1f}")
    print(f"  CREW_FATIGUE fires on {int(d.CREW_FATIGUE.sum()):,} games "
          f"({100*d.CREW_FATIGUE.mean():.1f}%)   dev {100*dev.CREW_FATIGUE.mean():.1f}% "
          f"hold {100*hold.CREW_FATIGUE.mean():.1f}%")

    print("\n  POSITIVE CONTROL — CrewShock -> fouls on this sample (bar |t|>=4)")
    _, tc = link(dev, "fouls", "CrewFoul", "CrewFoul -> fouls")
    ok = abs(tc) >= 4
    print(f"    control {'PASS' if ok else 'FAIL'}")
    if not ok:
        print("    harness unverified — halting per prereg s4."); return

    print(f"\n  CHAIN (development, {len(dev):,} games)   [all predicted NEGATIVE except link 4 ~0]")
    print(f"    {'link':34}{'coef':>10}{'t':>8}")
    r = {}
    for tgt, lab in (("fouls", "1  fatigue -> fouls"), ("fta", "2  fatigue -> FTA"),
                     ("actual", "3  fatigue -> ACTUAL total"),
                     ("total", "4  fatigue -> CLOSING total"),
                     ("e", "5  fatigue -> closing residual")):
        r[tgt] = link(dev, tgt, "CREW_FATIGUE", lab)

    # permutation on link 5
    y = dev["e"].values
    ctl = [dev[c].values for c in rsk.CTRL]
    v = dev["CREW_FATIGUE"].values
    obs = r["e"][0]
    yrs = dev["yr"].values
    blocks = [np.where(yrs == u)[0] for u in np.unique(yrs)]
    null = np.empty(NPERM)
    for i in range(NPERM):
        p = v.copy()
        for bl in blocks:
            p[bl] = v[bl][RNG.permutation(len(bl))]
        bb, _ = ols(y, [p] + ctl)
        null[i] = bb[1]
    pv = (1 + np.sum(np.abs(null) >= abs(obs))) / (NPERM + 1)
    print(f"\n  permutation (link 5, within-season): observed {obs:+.4f}  p={pv:.4f}")

    print(f"\n  HOLDOUT ({len(hold):,} games)")
    print(f"    {'link':34}{'coef':>10}{'t':>8}")
    hb, ht = link(hold, "e", "CREW_FATIGUE", "5  fatigue -> closing residual")
    ha, hat = link(hold, "actual", "CREW_FATIGUE", "3  fatigue -> ACTUAL total")

    print("\n  DECISION (prereg s5)")
    c1 = all(r[k][0] < 0 and abs(r[k][1]) >= 2 for k in ("fouls", "fta", "actual"))
    c2 = abs(r["total"][1]) < 2
    c3 = (r["e"][0] < 0) and (pv < 0.05)
    c4 = np.sign(hb) == np.sign(r["e"][0])
    c5 = abs(r["e"][0]) >= 1.0
    for nm, c in (("links 1-3 negative, |t|>=2", c1), ("link 4 not significant", c2),
                  ("link 5 negative, perm p<0.05", c3), ("holdout link 5 same sign", c4),
                  ("economic >= 1.0 point", c5)):
        print(f"    {nm:36} {'PASS' if c else 'FAIL'}")
    print(f"    -> {'PASS' if all((c1,c2,c3,c4,c5)) else 'NOT TRADABLE / NULL — branch closes'}")


if __name__ == "__main__":
    main()
