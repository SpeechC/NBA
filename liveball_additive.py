"""Test 2 — live-ball turnover composition as an additive component.

Pre-registered in PREREG_liveball_additive.md. Development 2017-18..2023-24,
SEALED holdout 2024-25. CrewShock and LeagueFoulState are LOADED from
ref_features.csv and never rebuilt.

Games lacking possession context are excluded; missing is never read as zero.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import pbp_possessions as pp
import ref_shock as rsk
import refs
from dispersion_priced import ols

ADVF = "/mnt/c/NBA2/advanced_stats/game_advanced_stats.csv"
W, MINP = 20, 10
DEV_MAX, SEALED = 2023, 2024
CTRL = rsk.CTRL
BE = 110 / 210


def build():
    A = pp.build()
    A["gid"] = A["gid"].astype(str).str.strip()

    m = refs.build()
    m["gid"] = m["GAME-ID"].astype(str).str.strip()
    adv = pd.read_csv(ADVF, low_memory=False)
    adv["gid"] = adv["GAME-ID"].astype(str).str.strip()
    cols = {s: f"EV_LIVE_BALL_TOV_{s}" for s in ("H", "R")}
    ab = {s: f"ADV_TEAM_ABBR_{s}" for s in ("H", "R")}
    adv = adv[["gid"] + list(cols.values()) + list(ab.values())]
    n0 = len(m)
    m = m.merge(adv, on="gid", how="left")
    assert len(m) == n0

    # long form, one row per game-team, joining possessions to live-ball TOV
    rows = []
    for s, o in (("H", "R"), ("R", "H")):
        rows.append(pd.DataFrame({
            "gid": m["gid"], "yr": m["yr"], "date": m["date"],
            "team": m[ab[s]], "side": s,
            "lbto": pd.to_numeric(m[cols[s]], errors="coerce"),
            "opp_lbto": pd.to_numeric(m[cols[o]], errors="coerce")}))
    P = pd.concat(rows)
    P = P.merge(A[["gid", "team", "poss", "steal_poss", "steal_pts", "pts"]],
                on=["gid", "team"], how="left")
    opp = A[["gid", "team", "poss"]].rename(
        columns={"team": "oteam", "poss": "opp_poss"})
    P = P.merge(P[["gid", "side"]].assign(
        oside=np.where(P["side"] == "H", "R", "H")), on=["gid", "side"],
        how="left").drop_duplicates(["gid", "side"])
    o2 = P[["gid", "side", "poss"]].rename(
        columns={"side": "oside", "poss": "opp_poss"})
    P = P.merge(o2, on=["gid", "oside"], how="left")

    before = len(P)
    P = P.dropna(subset=["poss", "opp_poss", "lbto", "opp_lbto"])
    print(f"  possession-context exclusion: {before:,} -> {len(P):,} game-team "
          f"rows ({100*len(P)/before:.2f}% retained)")
    P = P.sort_values("date").reset_index(drop=True)

    g = P.groupby(["yr", "team"])
    for num, den, name in (("lbto", "poss", "off"),
                           ("opp_lbto", "opp_poss", "def")):
        sn = g[num].transform(
            lambda s: s.shift(1).rolling(W, min_periods=MINP).sum())
        sd = g[den].transform(
            lambda s: s.shift(1).rolling(W, min_periods=MINP).sum())
        P[f"LBTO_{name}"] = sn / sd
    return m, A, P


def main():
    m, A, P = build()
    dev_mask = P["yr"] <= DEV_MAX
    stats = {}
    for c in ("LBTO_off", "LBTO_def"):
        stats[c] = (P.loc[dev_mask, c].mean(), P.loc[dev_mask, c].std())
        P[f"z_{c}"] = (P[c] - stats[c][0]) / stats[c][1]
    print(f"  FROZEN develop standardisation: "
          + "  ".join(f"{c} mu={v[0]:.5f} sd={v[1]:.5f}"
                      for c, v in stats.items()))

    h = P[P["side"] == "H"][["gid", "z_LBTO_off", "z_LBTO_def"]].add_suffix("_h")
    a = P[P["side"] == "R"][["gid", "z_LBTO_off", "z_LBTO_def"]].add_suffix("_a")
    d = m.merge(h.rename(columns={"gid_h": "gid"}), on="gid").merge(
        a.rename(columns={"gid_a": "gid"}), on="gid")
    d["LBPressure"] = (d["z_LBTO_off_h"] + d["z_LBTO_def_a"]
                       + d["z_LBTO_off_a"] + d["z_LBTO_def_h"])

    # realised chain outcomes, combined over both teams
    W2 = A.groupby("gid").agg(poss=("poss", "sum"), pts=("pts", "sum"),
                              steal_poss=("steal_poss", "sum"),
                              steal_pts=("steal_pts", "sum")).reset_index()
    d = d.merge(W2, on="gid", how="left")
    lb = P.groupby("gid")["lbto"].sum().rename("lb_tot").reset_index()
    d = d.merge(lb, on="gid", how="left")
    d["lb_per100"] = 100 * d["lb_tot"] / d["poss"]
    d["steal_share"] = d["steal_poss"] / d["poss"]

    f = pd.read_csv("ref_features.csv")
    f["gid"] = f["gid"].astype(str).str.strip()
    n0 = len(d)
    d = d.merge(f[["gid", "CrewShock", "LeagueFoulState"]], on="gid", how="left")
    assert len(d) == n0
    print(f"  MERGE onto frozen ref_features: {d['CrewShock'].notna().sum():,} "
          f"matched, {d['CrewShock'].isna().sum():,} unmatched")
    ctl = rsk.build()[["gid"] + CTRL]
    ctl["gid"] = ctl["gid"].astype(str).str.strip()
    d = d.merge(ctl, on="gid", how="left")

    need = (["LBPressure", "CrewShock", "LeagueFoulState", "e", "total",
             "actual", "poss", "lb_per100"] + CTRL)
    s = d.dropna(subset=need).copy()
    s = s[s["yr"] <= SEALED]
    dev = s[s["yr"] <= DEV_MAX]
    seal = s[s["yr"] == SEALED]
    print(f"\n  analysis sample {len(s):,}   development {len(dev):,}   "
          f"SEALED 2024-25 {len(seal):,}")
    print(f"  LBPressure mean {s['LBPressure'].mean():+.4f} "
          f"sd {s['LBPressure'].std():.4f}")

    print("\n" + "=" * 96)
    print("INDEPENDENCE FROM CrewShock")
    print("=" * 96)
    for lab, x in (("development", dev), ("SEALED 2024-25", seal)):
        pr = np.corrcoef(x["LBPressure"], x["CrewShock"])[0, 1]
        sp = x[["LBPressure", "CrewShock"]].corr(method="spearman").iloc[0, 1]
        print(f"  {lab:16} pearson {pr:+.4f}   spearman {sp:+.4f}   "
              f"R^2 {pr**2:.5f}")

    print("\n" + "=" * 96)
    print("THE CHAIN — does LBPressure drive its own mechanism?")
    print("=" * 96)
    print("  each row: Y ~ LBPressure + LeagueFoulState + 11 team controls")
    print(f"  {'link':34} {'development':>22} {'SEALED 2024-25':>22}")
    for col, name in (("lb_per100", "live-ball TOV per 100 poss"),
                      ("steal_share", "steal-started poss share"),
                      ("steal_pts", "points on steal-start poss"),
                      ("actual", "ACTUAL TOTAL"),
                      ("total", "CLOSING TOTAL"),
                      ("e", "closing residual")):
        out = []
        for x in (dev, seal):
            X = np.column_stack([x["LBPressure"], x["LeagueFoulState"]]
                                + [x[c] for c in CTRL])
            b, se, t = ols(x[col].values, X)
            out.append(f"{b[1]:+10.4f} (t={t[1]:+5.2f})")
        print(f"  {name:34} {out[0]:>22} {out[1]:>22}")

    print("\n  c_market vs c_true for LBPressure")
    for lab, x in (("development", dev), ("SEALED 2024-25", seal)):
        X = np.column_stack([x["LBPressure"], x["LeagueFoulState"]]
                            + [x[c] for c in CTRL])
        bm, _, tm = ols(x["total"].values, X)
        bt, _, tt = ols(x["actual"].values, X)
        print(f"    {lab:16} c_market {bm[1]:+.4f} (t={tm[1]:+5.2f})   "
              f"c_true {bt[1]:+.4f} (t={tt[1]:+5.2f})   "
              f"gap {bt[1]-bm[1]:+.4f}")

    print("\n" + "=" * 96)
    print("ADDITIVE TEST — Residual ~ CrewShock + LBPressure + League + controls")
    print("=" * 96)
    for lab, x in (("development", dev), ("SEALED 2024-25", seal)):
        X = np.column_stack([x["CrewShock"], x["LBPressure"], x["LeagueFoulState"]]
                            + [x[c] for c in CTRL])
        b, se, t = ols(x["e"].values, X)
        Xr = np.column_stack([x["CrewShock"], x["LeagueFoulState"]]
                             + [x[c] for c in CTRL])
        br, _, tr = ols(x["e"].values, Xr)
        Xl = np.column_stack([x["LBPressure"], x["LeagueFoulState"]]
                             + [x[c] for c in CTRL])
        blo, _, tlo = ols(x["e"].values, Xl)
        print(f"  {lab}")
        print(f"    bR {b[1]:+.4f} (t={t[1]:+5.2f})   [alone {br[1]:+.4f}]")
        print(f"    bL {b[2]:+.4f} (t={t[2]:+5.2f})   [alone {blo[1]:+.4f} "
              f"(t={tlo[1]:+.2f})]")

    print("\n  season signs of bL (development diagnostic)")
    out = []
    for y, gg in dev.groupby("yr"):
        X = np.column_stack([gg["CrewShock"], gg["LBPressure"],
                             gg["LeagueFoulState"]] + [gg[c] for c in CTRL])
        b, _, t = ols(gg["e"].values, X)
        out.append(f"{y}:{b[2]:+.3f}")
    print("    " + "  ".join(out))
    s.to_csv("liveball_sample.csv", index=False)


if __name__ == "__main__":
    main()
