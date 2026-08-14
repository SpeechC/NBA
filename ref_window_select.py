"""Referee lookback-window comparison. Development-only selection.

CANDIDATES  N = 30, 60, 100, 150 prior referee games
INCUMBENT   N = 60 (the frozen estimator in ref_features.csv)
REFERENCE   expanding career (resembles the RETIRED crew_foul.py Test-1
            estimator; not a candidate for replacement)

Everything except the referee lookback is identical to the frozen estimator:
same foul-rate target, same trailing cross-season matched league baseline, same
empirical-Bayes shrinkage, same crew aggregation, same controls, same split,
strict prior-only construction.

min_periods is scaled proportionally (25/60 of N) so the estimator's
completeness requirement is the same fraction of the window at every horizon.

NO closing residual, win rate or ROI is computed in this file.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import ref_features as rf
import ref_shock as rsk
import refs
from dispersion_priced import ols

CTRL = rsk.CTRL
ADVF = "/mnt/c/NBA2/advanced_stats/game_advanced_stats.csv"
DEV_MAX = 2023
WINDOWS = [30, 60, 100, 150]


def minn(N):
    return max(10, int(round(N * 25.0 / 60.0)))


def ref_effect(d, k, N, expanding=False):
    """Exactly rf.matched_ref_effect but with the lookback parameterised."""
    dates = d["date"].values.astype("datetime64[ns]").astype(np.int64)
    order = np.argsort(dates, kind="stable")
    sd = dates[order]
    cum = np.concatenate([[0.0], np.cumsum(d["pf_rate"].values[order])])
    long = pd.concat([
        pd.DataFrame({"row": np.arange(len(d)), "date": dates,
                      "ref": d[f"ref{i}"].values, "pf": d["pf_rate"].values})
        for i in (1, 2, 3)])
    long = long.sort_values(["ref", "date"], kind="stable").reset_index(drop=True)
    g = long.groupby("ref", sort=False)
    p = g["pf"].shift(1)
    dprev = g["date"].shift(1)
    mp = minn(N)
    if expanding:
        roll = lambda s: s.expanding(min_periods=mp)
    else:
        roll = lambda s: s.rolling(N, min_periods=mp)
    long["rm"] = p.groupby(long["ref"]).transform(lambda s: roll(s).mean())
    long["rn"] = p.groupby(long["ref"]).transform(lambda s: roll(s).count())
    long["d_end"] = dprev.groupby(long["ref"]).transform(lambda s: roll(s).max())
    long["d_start"] = dprev.groupby(long["ref"]).transform(lambda s: roll(s).min())
    ok = long["rn"].notna() & long["d_start"].notna()
    j1 = np.searchsorted(sd, long.loc[ok, "d_start"].values, side="left")
    j2 = np.searchsorted(sd, long.loc[ok, "d_end"].values, side="right")
    cnt = np.maximum(j2 - j1, 1)
    long["lg"] = np.nan
    long.loc[ok, "lg"] = (cum[j2] - cum[j1]) / cnt
    long["raw"] = long["rm"] - long["lg"]
    long["eff"] = (long["raw"] * long["rn"] / (long["rn"] + k)).fillna(0.0)
    long["yr"] = d["yr"].values[long["row"].values]
    return long.groupby("row")["eff"].sum().reindex(np.arange(len(d))).values, long


def build():
    d = rf.universe()
    d["gid"] = d["gid"].astype(str).str.strip()
    k, _ = rf.estimate_k(d)
    m = refs.build()
    m["gid"] = m["GAME-ID"].astype(str).str.strip()
    adv = pd.read_csv(ADVF, low_memory=False)
    adv["gid"] = adv["GAME-ID"].astype(str).str.strip()
    adv["poss_g"] = (pd.to_numeric(adv["PBP_POSS_H"], errors="coerce")
                     + pd.to_numeric(adv["PBP_POSS_R"], errors="coerce"))
    import foul_types
    F = foul_types.build()
    F["gidz"] = F["gid"].astype(str).str.zfill(10)
    m["gidz"] = m["gid"].str.zfill(10)
    m = m.merge(F[["gidz", "defensive_fouls"]], on="gidz", how="left")
    m = m.merge(adv[["gid", "poss_g"]], on="gid", how="left")
    m["def_per100"] = 100 * m["defensive_fouls"] / m["poss_g"]
    fr = pd.read_csv("ref_features.csv")
    fr["gid"] = fr["gid"].astype(str).str.strip()
    m = m.merge(fr[["gid", "LeagueFoulState", "CrewShock"]], on="gid", how="left")
    ctl = rsk.build()[["gid"] + CTRL]
    ctl["gid"] = ctl["gid"].astype(str).str.strip()
    m = m.merge(ctl, on="gid", how="left")
    return d, k, m


def zbeta(x, col, sig):
    """Standardised beta and t on Y ~ sig + League + controls."""
    X = np.column_stack([x[sig] / x[sig].std(), x["LeagueFoulState"]]
                        + [x[c] for c in CTRL])
    b, se, t = ols(x[col].values / x[col].std(), X)
    return b[1], t[1]


def main():
    d, k, m = build()
    print(f"  universe {len(d):,} games   shrinkage k = {k:.1f} (frozen method)")
    print(f"  min_periods by window: "
          + "  ".join(f"N={N}:{minn(N)}" for N in WINDOWS))

    specs = {}
    for N in WINDOWS:
        eff, lg = ref_effect(d, k, N)
        specs[f"N{N}"] = (eff, lg)
    eff, lg = ref_effect(d, k, 150, expanding=True)
    specs["EXPAND"] = (eff, lg)

    cs = d[["gid", "pf_rate"]].copy()
    for nm, (e, _) in specs.items():
        cs[nm] = e
    m = m.merge(cs, on="gid", how="left")
    # sanity: N=60 must reproduce the frozen feature
    chk = m.dropna(subset=["CrewShock", "N60"])
    err = np.max(np.abs(chk["CrewShock"] - chk["N60"]))
    print(f"  N=60 reproduces frozen CrewShock, max abs error {err:.2e}")

    need = ["pf_rate", "LeagueFoulState"] + CTRL
    s = m.dropna(subset=need + list(specs)).copy()
    dev = s[s["yr"] <= DEV_MAX]
    print(f"  development games {len(dev):,}   (selection uses these only)")

    print("\n" + "=" * 104)
    print("DEVELOPMENT-ONLY FORWARD FORECAST OF FOUL BEHAVIOUR")
    print("=" * 104)
    print(f"  {'Window':9}{'corr':>8}{'std beta':>10}{'t':>8}{'incr R2 %':>11}"
          f"{'OOS R2 %':>10}{'RMSE':>8}{'defF beta':>11}")
    rows = []
    yrs = sorted(dev["yr"].unique())
    for nm in list(specs):
        r = np.corrcoef(dev[nm], dev["pf_rate"])[0, 1]
        bz, tz = zbeta(dev, "pf_rate", nm)
        Xf = np.column_stack([dev["LeagueFoulState"]] + [dev[c] for c in CTRL])
        b0, _, _ = ols(dev["pf_rate"].values, Xf)
        r0 = dev["pf_rate"].values - np.column_stack(
            [np.ones(len(dev)), Xf]) @ b0
        X1 = np.column_stack([dev[nm], dev["LeagueFoulState"]]
                             + [dev[c] for c in CTRL])
        b1, _, _ = ols(dev["pf_rate"].values, X1)
        r1 = dev["pf_rate"].values - np.column_stack(
            [np.ones(len(dev)), X1]) @ b1
        incr = 100 * (1 - (r1 ** 2).sum() / (r0 ** 2).sum())
        # chronological OOS: fit on prior seasons, score next
        num = den = 0.0
        for i in range(2, len(yrs)):
            tr = dev[dev["yr"].isin(yrs[:i])]
            te = dev[dev["yr"] == yrs[i]]
            Xtr = np.column_stack([np.ones(len(tr)), tr[nm],
                                   tr["LeagueFoulState"]]
                                  + [tr[c] for c in CTRL])
            bb = np.linalg.lstsq(Xtr, tr["pf_rate"].values, rcond=None)[0]
            Xte = np.column_stack([np.ones(len(te)), te[nm],
                                   te["LeagueFoulState"]]
                                  + [te[c] for c in CTRL])
            pr = Xte @ bb
            num += ((te["pf_rate"].values - pr) ** 2).sum()
            den += ((te["pf_rate"].values - tr["pf_rate"].mean()) ** 2).sum()
        oos = 100 * (1 - num / den)
        rmse = np.sqrt(num / max(len(dev), 1))
        dsub = dev.dropna(subset=["def_per100"])
        bd, _ = zbeta(dsub, "def_per100", nm) if len(dsub) > 500 else (np.nan,)*2
        rows.append({"Window": nm, "corr": r, "beta": bz, "t": tz,
                     "incr": incr, "oos": oos, "rmse": rmse, "defb": bd})
        print(f"  {nm:9}{r:8.4f}{bz:10.4f}{tz:8.2f}{incr:11.4f}{oos:10.4f}"
              f"{rmse:8.4f}{bd:11.4f}")

    print("\n  season-by-season standardised beta (development)")
    print(f"  {'season':9}" + "".join(f"{nm:>10}" for nm in specs))
    stab = {nm: [] for nm in specs}
    for y in yrs:
        g_ = dev[dev["yr"] == y]
        line = f"  {int(y):<9}"
        for nm in specs:
            bz, _ = zbeta(g_, "pf_rate", nm)
            stab[nm].append(bz)
            line += f"{bz:10.4f}"
        print(line)
    print(f"  {'min':9}" + "".join(f"{min(stab[nm]):10.4f}" for nm in specs))
    print(f"  {'sd':9}" + "".join(f"{np.std(stab[nm]):10.4f}" for nm in specs))

    print("\n  forward referee-effect persistence (development)")
    print(f"  {'Window':9}{'corr':>9}{'slope':>9}")
    for nm in list(specs):
        _, lg = specs[nm]
        lgd = lg[lg["yr"] <= DEV_MAX].copy()
        lgd["realised"] = lgd["pf"] - lgd["lg"]
        t = lgd.groupby(["yr", "ref"]).agg(prior=("eff", "mean"),
                                           real=("realised", "mean"),
                                           n=("eff", "size"))
        t = t[t["n"] >= 20].dropna()
        r = np.corrcoef(t["prior"], t["real"])[0, 1]
        b = np.polyfit(t["prior"], t["real"], 1)[0]
        print(f"  {nm:9}{r:9.4f}{b:9.4f}")

    print("\n" + "=" * 104)
    print("SELECTION (development only, incumbent N=60 retained unless clearly beaten)")
    print("=" * 104)
    R = pd.DataFrame(rows).set_index("Window")
    inc = R.loc["N60"]
    for nm in R.index:
        if nm == "N60":
            continue
        dr = R.loc[nm, "corr"] - inc["corr"]
        do = R.loc[nm, "oos"] - inc["oos"]
        di = R.loc[nm, "incr"] - inc["incr"]
        print(f"  {nm:9} vs N60:  d corr {dr:+.4f}   d incr R2 {di:+.4f}pp"
              f"   d chrono OOS R2 {do:+.4f}pp")
    R.to_csv("ref_window_development.csv")

    print("\n" + "=" * 104)
    print("DESCRIPTIVE — 2025-26 ONLY (not used for selection)")
    print("=" * 104)
    h = s[s["yr"] == 2025]
    print(f"  {'':26}" + "".join(f"{nm:>10}" for nm in specs))
    line = f"  {'CrewShock -> foul rate':26}"
    for nm in specs:
        bz, _ = zbeta(h, "pf_rate", nm)
        line += f"{bz:10.4f}"
    print(line)
    for lab, fn in (("CrewShock SD", lambda v: v.std()),
                    ("Q85", lambda v: v.quantile(0.85))):
        print(f"  {lab:26}" + "".join(f"{fn(h[nm]):10.4f}" for nm in specs))
    print(f"  {'fwd ref corr':26}", end="")
    for nm in specs:
        _, lg = specs[nm]
        lgh = lg[lg["yr"] == 2025].copy()
        lgh["realised"] = lgh["pf"] - lgh["lg"]
        t = lgh.groupby("ref").agg(prior=("eff", "mean"),
                                   real=("realised", "mean"), n=("eff", "size"))
        t = t[t["n"] >= 20].dropna()
        print(f"{np.corrcoef(t['prior'], t['real'])[0,1]:10.4f}", end="")
    print()
    print(f"  {'fwd ref slope':26}", end="")
    for nm in specs:
        _, lg = specs[nm]
        lgh = lg[lg["yr"] == 2025].copy()
        lgh["realised"] = lgh["pf"] - lgh["lg"]
        t = lgh.groupby("ref").agg(prior=("eff", "mean"),
                                   real=("realised", "mean"), n=("eff", "size"))
        t = t[t["n"] >= 20].dropna()
        print(f"{np.polyfit(t['prior'], t['real'], 1)[0]:10.4f}", end="")
    print()

    print("\n" + "=" * 104)
    print("ADAPTATION SPEED — N=30 vs frozen N=60, by season")
    print("=" * 104)
    print(f"  {'season':9}{'corr':>9}{'rank corr':>11}{'med |d|':>10}"
          f"{'Q90 |d|':>10}{'% sign flip':>13}")
    for y in sorted(s["yr"].unique()):
        g_ = s[s["yr"] == y]
        a, b = g_["N30"], g_["N60"]
        print(f"  {int(y):<9}{np.corrcoef(a, b)[0,1]:9.4f}"
              f"{a.corr(b, method='spearman'):11.4f}"
              f"{np.median(np.abs(a-b)):10.4f}"
              f"{np.quantile(np.abs(a-b), 0.90):10.4f}"
              f"{100*np.mean(np.sign(a) != np.sign(b)):13.2f}")


if __name__ == "__main__":
    main()
