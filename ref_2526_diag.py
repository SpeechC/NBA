"""Why is the 2025-26 referee mechanism weak?

Diagnostics only. Nothing here changes CrewShock or the trading signal.

The per-official internals of the frozen estimator are recomputed locally so
they can be inspected, and the recomputation is ASSERTED to reproduce
ref_features.csv exactly before any diagnostic is reported.

Coverage note stated up front: the foul-TYPE classification comes from the
play-by-play parquet, which ends at 2024-25. So defensive_fouls_per100 exists
for 2017-18..2024-25 only. Total fouls per 100 possessions
(ADV_PF_PER100_OPP_POSS, the series CrewShock is built on) spans all eight
seasons and is the mechanism metric used wherever 2025-26 must be included.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import foul_types
import ref_features as rf
import ref_shock as rsk
import refs
from dispersion_priced import ols

CTRL = rsk.CTRL
ADVF = "/mnt/c/NBA2/advanced_stats/game_advanced_stats.csv"
N, MINN = rf.N, rf.MINN


def internals():
    """Reproduce ref_features.matched_ref_effect, keeping the long frame."""
    d = rf.universe()
    k, sig = rf.estimate_k(d)
    dates = d["date"].values.astype("datetime64[ns]").astype(np.int64)
    order = np.argsort(dates, kind="stable")
    sd = dates[order]
    cum = np.concatenate([[0.0], np.cumsum(d["pf_rate"].values[order])])

    long = pd.concat([
        pd.DataFrame({"row": np.arange(len(d)), "slot": i, "date": dates,
                      "ref": d[f"ref{i}"].values, "pf": d["pf_rate"].values})
        for i in (1, 2, 3)])
    long = long.sort_values(["ref", "date"], kind="stable").reset_index(drop=True)
    g = long.groupby("ref", sort=False)
    p = g["pf"].shift(1)
    long["rm"] = p.groupby(long["ref"]).transform(
        lambda s: s.rolling(N, min_periods=MINN).mean())
    long["rn"] = p.groupby(long["ref"]).transform(
        lambda s: s.rolling(N, min_periods=MINN).count())
    long["career_prior"] = g.cumcount()          # full prior-game count
    dprev = g["date"].shift(1)
    long["d_end"] = dprev.groupby(long["ref"]).transform(
        lambda s: s.rolling(N, min_periods=MINN).max())
    long["d_start"] = dprev.groupby(long["ref"]).transform(
        lambda s: s.rolling(N, min_periods=MINN).min())
    ok = long["rn"].notna() & long["d_start"].notna()
    j1 = np.searchsorted(sd, long.loc[ok, "d_start"].values, side="left")
    j2 = np.searchsorted(sd, long.loc[ok, "d_end"].values, side="right")
    cnt = np.maximum(j2 - j1, 1)
    long["lg_matched"] = np.nan
    long.loc[ok, "lg_matched"] = (cum[j2] - cum[j1]) / cnt
    long["raw"] = long["rm"] - long["lg_matched"]
    long["shrink"] = long["rn"] / (long["rn"] + k)
    long["eff"] = (long["raw"] * long["shrink"]).fillna(0.0)
    long["yr"] = d["yr"].values[long["row"].values]
    agg = long.groupby("row")["eff"].sum()
    d["CrewShock_rc"] = agg.reindex(np.arange(len(d))).values

    frozen = pd.read_csv("ref_features.csv")
    frozen["gid"] = frozen["gid"].astype(str).str.strip()
    d["gid"] = d["gid"].astype(str).str.strip()
    chk = d[["gid", "CrewShock_rc"]].merge(frozen[["gid", "CrewShock"]],
                                           on="gid", how="inner")
    assert np.allclose(chk["CrewShock_rc"], chk["CrewShock"], atol=1e-9), \
        "recomputation does NOT reproduce the frozen feature"
    print(f"  recomputation reproduces ref_features.csv exactly on "
          f"{len(chk):,} games (k = {k:.1f}, sigma_ref = {sig:.3f})")
    return d, long, k


def mech_table(long):
    """Items 1-8, by season."""
    rows = []
    for y, g in long.groupby("yr"):
        act = g["ref"].nunique()
        cp = g["career_prior"]
        per_ref = g.groupby("ref").agg(raw=("raw", "mean"),
                                       eff=("eff", "mean"), n=("eff", "size"))
        per_ref = per_ref[per_ref["n"] >= 20]
        rows.append({
            "season": int(y), "officials": act,
            "<20": round(100 * (cp < 20).mean(), 1),
            "<40": round(100 * (cp < 40).mean(), 1),
            "<60": round(100 * (cp < 60).mean(), 1),
            "med prior": int(cp.median()),
            "shrink mean": round(g["shrink"].mean(), 4),
            "shrink med": round(g["shrink"].median(), 4),
            "sd raw": round(per_ref["raw"].std(), 4),
            "sd shrunk": round(per_ref["eff"].std(), 4)})
    return pd.DataFrame(rows)


def persistence(long, min_prior=0):
    """Item 9/10 — strictly forward: does the frozen PRIOR effect predict the
    official's realised foul deviation in that same season?"""
    g = long[long["career_prior"] >= min_prior].copy()
    g["realised"] = g["pf"] - g["lg_matched"]
    out = []
    for y, s in g.groupby("yr"):
        t = s.groupby("ref").agg(prior=("eff", "mean"),
                                 real=("realised", "mean"),
                                 n=("eff", "size"))
        t = t[t["n"] >= 20].dropna()
        if len(t) < 10:
            out.append({"season": int(y), "refs": len(t), "corr": np.nan,
                        "slope": np.nan})
            continue
        r = np.corrcoef(t["prior"], t["real"])[0, 1]
        b = np.polyfit(t["prior"], t["real"], 1)[0]
        out.append({"season": int(y), "refs": len(t), "corr": round(r, 4),
                    "slope": round(b, 4)})
    return pd.DataFrame(out)


def main():
    d, long, k = internals()

    print("\n" + "=" * 100)
    print("1 — MECHANISM COEFFICIENT BY SEASON")
    print("=" * 100)
    m = refs.build()
    m["gid"] = m["GAME-ID"].astype(str).str.strip()
    adv = pd.read_csv(ADVF, low_memory=False)
    adv["gid"] = adv["GAME-ID"].astype(str).str.strip()
    adv["pf_rate"] = (pd.to_numeric(adv["ADV_PF_PER100_OPP_POSS_H"],
                                    errors="coerce")
                      + pd.to_numeric(adv["ADV_PF_PER100_OPP_POSS_R"],
                                      errors="coerce"))
    adv["poss_g"] = (pd.to_numeric(adv["PBP_POSS_H"], errors="coerce")
                     + pd.to_numeric(adv["PBP_POSS_R"], errors="coerce"))
    m = m.merge(adv[["gid", "pf_rate", "poss_g"]], on="gid", how="left")
    F = foul_types.build()
    F["gid"] = F["gid"].astype(str).str.zfill(10)
    m["gidz"] = m["gid"].str.zfill(10)
    m = m.merge(F[["gid", "defensive_fouls"]].rename(columns={"gid": "gidz"}),
                on="gidz", how="left")
    m["def_per100"] = 100 * m["defensive_fouls"] / m["poss_g"]
    fr = pd.read_csv("ref_features.csv")
    fr["gid"] = fr["gid"].astype(str).str.strip()
    m = m.merge(fr[["gid", "CrewShock", "LeagueFoulState"]], on="gid",
                how="left")
    ctl = rsk.build()[["gid"] + CTRL]
    ctl["gid"] = ctl["gid"].astype(str).str.strip()
    m = m.merge(ctl, on="gid", how="left")
    s = m.dropna(subset=["CrewShock", "LeagueFoulState", "pf_rate"] + CTRL)

    print("  def_per100 exists 2017-18..2024-25 only (PBP parquet ends there).")
    print("  pf_rate (total fouls per 100) spans all eight seasons.")
    print(f"\n  {'season':8} {'n':>5} {'b(def/100)':>20} {'b(pf_rate)':>20}")
    coefs = {}
    for y, g in s.groupby("yr"):
        cells = []
        for col in ("def_per100", "pf_rate"):
            gg = g.dropna(subset=[col])
            if len(gg) < 100:
                cells.append(("n/a", "", np.nan, np.nan))
                continue
            X = np.column_stack([gg["CrewShock"], gg["LeagueFoulState"]]
                                + [gg[c] for c in CTRL])
            b, se, t = ols(gg[col].values, X)
            cells.append((f"{b[1]:+.4f}", f"({se[1]:.4f})", b[1], se[1]))
            if col == "pf_rate":
                coefs[int(y)] = (b[1], se[1], len(gg))
        print(f"  {int(y):<8} {len(g):5,} "
              f"{cells[0][0]:>11}{cells[0][1]:>9} "
              f"{cells[1][0]:>11}{cells[1][1]:>9}")

    print("\n" + "=" * 100)
    print("2-8 — REFEREE-POOL AND ESTIMATOR DIAGNOSTICS BY SEASON")
    print("=" * 100)
    T = mech_table(long)
    cs = d.groupby("yr")["CrewShock_rc"].agg(
        sd="std", q85=lambda v: v.quantile(0.85),
        q90=lambda v: v.quantile(0.90)).reset_index()
    cs.columns = ["season", "CS sd", "CS Q85", "CS Q90"]
    T = T.merge(cs, on="season")
    T["Q85-Q90"] = (T["CS Q90"] - T["CS Q85"]).round(4)
    print(T.to_string(index=False))

    print("\n" + "=" * 100)
    print("9/10 — STRICTLY FORWARD REFEREE PERSISTENCE")
    print("  realised foul deviation this season ~ frozen prior referee effect")
    print("=" * 100)
    tabs = {mp: persistence(long, mp) for mp in (0, 40, 60)}
    print(f"  {'season':8}" + "".join(
        f"{f'>= {mp} prior':>26}" for mp in (0, 40, 60)))
    print(f"  {'':8}" + "".join(f"{'refs':>7}{'corr':>9}{'slope':>10}"
                                for _ in (0, 40, 60)))
    for y in sorted(tabs[0]["season"]):
        line = f"  {y:<8}"
        for mp in (0, 40, 60):
            r = tabs[mp][tabs[mp]["season"] == y]
            if len(r) == 0 or np.isnan(r["corr"].iloc[0]):
                line += f"{'-':>7}{'-':>9}{'-':>10}"
            else:
                line += (f"{int(r['refs'].iloc[0]):>7}"
                         f"{r['corr'].iloc[0]:>9.4f}{r['slope'].iloc[0]:>10.4f}")
        print(line)

    print("\n" + "=" * 100)
    print("IS 2025-26 DIFFERENT FROM THE POOLED PRIOR SEASONS?")
    print("=" * 100)
    yrs = [y for y in coefs if y != 2025]
    w = np.array([1 / coefs[y][1] ** 2 for y in yrs])
    b_pool = np.sum(w * np.array([coefs[y][0] for y in yrs])) / w.sum()
    se_pool = np.sqrt(1 / w.sum())
    b25, se25, n25 = coefs[2025]
    z = (b25 - b_pool) / np.sqrt(se25 ** 2 + se_pool ** 2)
    from scipy import stats as st
    p = 2 * (1 - st.norm.cdf(abs(z)))
    print(f"  pooled 2017-18..2024-25  b = {b_pool:+.4f}  se {se_pool:.4f}")
    print(f"  2025-26                  b = {b25:+.4f}  se {se25:.4f}  n={n25:,}")
    print(f"  difference {b25-b_pool:+.4f}   z = {z:+.2f}   two-sided p = {p:.4f}")
    lo, hi = b25 - 1.96 * se25, b25 + 1.96 * se25
    print(f"  2025-26 95% CI [{lo:+.4f}, {hi:+.4f}]  "
          f"contains the pooled mean: {lo <= b_pool <= hi}")


if __name__ == "__main__":
    main()
