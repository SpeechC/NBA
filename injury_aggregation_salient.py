"""EXPLORATORY, POST-HOC. Not part of PREREG_injury_surprise.md.

The pre-registered aggregation test (item 5) was declared NOT EVALUABLE after
the cell counts were seen: UNLISTED->Out fires on nearly every game, so 3,985
of 4,019 treated games landed in N_LATE>=3 while the 1- and 2-event cells held
6 and 28 games.

This re-runs it restricted to SALIENT players (top-3 trailing minutes share on
their team that date) -- the frozen Hypothesis B event set, pre-specified in
PREREG_injury.md s2 and NOT chosen now. That defends against cherry-picking the
cut, but does NOT make this confirmatory: the restriction was applied after
observing that the pre-registered version failed. Treat as descriptive.

Question: are simultaneous late OUTs additive? Is the 2-absence effect about
twice the 1-absence effect, or is there a threshold?
"""
import warnings

import duckdb
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import injury_surprise as ISU
from injury_market import SQL, norm_name

W, MINP = 20, 10


def ols(y, X):
    A = np.column_stack([np.ones(len(y))] + X)
    b, *_ = np.linalg.lstsq(A, y, rcond=None)
    r = y - A @ b
    se = np.sqrt(np.diag(np.linalg.pinv(A.T @ A)) * (r @ r)
                 / (len(y) - A.shape[1]))
    return b, b / se


def main():
    d, E = ISU.build()

    # ---- salience: top-3 trailing minutes share on the team that date ------
    M = duckdb.connect().execute(SQL).fetchdf()
    M["gid"] = M.gid.astype(str)
    M["key"] = M.pname.map(norm_name)
    import opening_line_error_decomposition as OLE
    g = OLE.load()
    g["gid"] = g.gid.astype(str).str.strip().str.zfill(10)
    g = g[(g.season >= 2020) & (g.season <= 2024)]
    M = M.merge(g[["gid", "season", "date"]], on="gid", how="inner")
    M["tot"] = M.groupby(["gid", "abbr"])["events"].transform("sum")
    M["share"] = M.events / M.tot
    M = M.sort_values("date")
    M["min_share"] = M.groupby(["season", "key"])["share"].transform(
        lambda s: s.shift(1).rolling(W, min_periods=MINP).mean())
    state = M.loc[M.min_share.notna(),
                  ["date", "key", "abbr", "min_share"]].sort_values("date")
    roster = M[["season", "abbr", "key"]].drop_duplicates()
    tdates = M[["season", "abbr", "date"]].drop_duplicates()
    cross = roster.merge(tdates, on=["season", "abbr"]).sort_values("date")
    cross = pd.merge_asof(
        cross, state[["date", "key", "min_share"]].sort_values("date"),
        on="date", by="key", direction="backward",
        allow_exact_matches=False).dropna(subset=["min_share"])
    cross["rk"] = cross.groupby(["abbr", "date"])["min_share"].rank(
        ascending=False, method="first")
    sal = cross.loc[cross.rk <= 3, ["date", "key"]].assign(salient=True)

    L = E[E.out_late].merge(sal, on=["date", "key"], how="left")
    L["salient"] = L.salient.fillna(False)
    S = L[L.salient]
    print(f"  late-OUT events: {len(L):,}   SALIENT-restricted: {len(S):,} "
          f"({100*len(S)/len(L):.1f}%)")
    print(f"  prior-status mix among salient late-OUT events:")
    vc = S.prior.value_counts()
    for st in ISU.STATUSES:
        print(f"    {st:14} {int(vc.get(st,0)):>6,}")

    agg = S.groupby("gk").agg(N=("out_late", "sum"),
                              SHOCK=("shock", "sum")).reset_index()
    d = d.merge(agg, on="gk", how="left").fillna({"N": 0.0, "SHOCK": 0.0})
    dev = d[d.season <= 2023]
    hold = d[d.season == 2024]

    print("\n" + "=" * 88)
    print("AGGREGATION, SALIENT-RESTRICTED  (EXPLORATORY / POST-HOC)")
    print("=" * 88)
    for lab, x in (("development", dev), ("holdout 2024-25", hold)):
        print(f"\n  {lab}   n={len(x):,}")
        print(f"    {'N salient late-OUT':>22}{'games':>8}{'mean tmove':>13}")
        for n, nm in ((0, "0"), (1, "exactly 1"), (2, "exactly 2"),
                      (3, ">= 3")):
            c = x[x.N == n] if n < 3 else x[x.N >= 3]
            if len(c):
                print(f"    {nm:>22}{len(c):>8,}{c.tmove.mean():>+13.3f}")

    print("\n  ADDITIVITY: dummies vs the 0-absence base, controls "
          "ridge+latent")
    for lab, x in (("development", dev), ("holdout 2024-25", hold)):
        d1 = (x.N == 1).astype(float).values
        d2 = (x.N == 2).astype(float).values
        d3 = (x.N >= 3).astype(float).values
        b, t = ols(x.tmove.values, [x.MOVE_RIDGE_OOS.values,
                                    x.MOVE_LATENT_OOS.values, d1, d2, d3])
        r = b[4] / b[3] if b[3] else np.nan
        print(f"    {lab:16} b(1)={b[3]:+.3f}(t={t[3]:+.2f})  "
              f"b(2)={b[4]:+.3f}(t={t[4]:+.2f})  b(>=3)={b[5]:+.3f}"
              f"(t={t[5]:+.2f})   b(2)/b(1)={r:+.2f}")
        print(f"    {'':16}  [additive => ratio ~2.0; threshold => ratio ~1.0]")

    print("\n  LINEAR vs SATURATED (development): does N enter linearly?")
    x = dev
    bl, tl = ols(x.tmove.values, [x.MOVE_RIDGE_OOS.values,
                                  x.MOVE_LATENT_OOS.values, x.N.values])
    print(f"    linear in N: {bl[3]:+.4f} per absence (t={tl[3]:+.2f})")
    bs, ts = ols(x.tmove.values, [x.MOVE_RIDGE_OOS.values,
                                  x.MOVE_LATENT_OOS.values, x.SHOCK.values])
    print(f"    linear in SHOCK (surprise x importance): {bs[3]:+.4f} "
          f"(t={ts[3]:+.2f})")


if __name__ == "__main__":
    main()
