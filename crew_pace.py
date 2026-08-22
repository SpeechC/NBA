"""CrewPace STAGE 1 — is possession propensity a persistent referee trait?

Pre-registered in PREREG_crew_pace.md. Stage 1 only: this script never reads
the closing total, the actual total, or any market quantity, so a gate failure
cannot have been influenced by an outcome.

    pace48   = ((PBP_POSS_H + PBP_POSS_R)/2) * 240/MIN
    pace_net = pace48 - (a + b*pf_rate),  a,b fit on DEVELOPMENT ONLY

pace_net is the PRIMARY: fouls stop the clock, so a raw pace propensity would
largely be CrewShock re-expressed. Raw pace48 is carried alongside for
diagnosis only.

Estimator architecture identical to ref_features.py / crew_tilt.py.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import crew_tilt as CT
import refs
from data_split import SPLIT_DATE
from dispersion_priced import ols
from prepare_data import CSV

ADVF = CT.ADVF
NPERM = 2000
RNG = np.random.default_rng(20260818)


def universe():
    d = refs.build()
    d["gid"] = d["GAME-ID"].astype(str).str.strip()
    adv = pd.read_csv(ADVF, low_memory=False)
    adv["gid"] = adv["GAME-ID"].astype(str).str.strip()
    cH, cR = "ADV_PF_PER100_OPP_POSS_H", "ADV_PF_PER100_OPP_POSS_R"
    n0 = len(d)
    d = d.merge(adv[["gid", cH, cR, "PBP_POSS_H", "PBP_POSS_R"]], on="gid",
                how="left")
    assert len(d) == n0
    raw = pd.read_csv(CSV, low_memory=False)
    raw["gid"] = raw["GAME-ID"].astype(str).str.strip()
    raw["mins"] = pd.to_numeric(raw["MIN_H"], errors="coerce")
    d = d.merge(raw[["gid", "mins"]].drop_duplicates("gid"), on="gid",
                how="left")

    d["pf_rate"] = d[cH] + d[cR]
    poss = (pd.to_numeric(d["PBP_POSS_H"], errors="coerce")
            + pd.to_numeric(d["PBP_POSS_R"], errors="coerce")) / 2.0
    d["pace48"] = poss * 240.0 / d["mins"]
    d = d[d["mins"].between(235, 340)]
    d = d.dropna(subset=["pace48", "pf_rate", "ref1", "ref2", "ref3"])
    return d.sort_values(["date", "gid"]).reset_index(drop=True)


def gates(d, col, lab, crew_col, league_col):
    """Run G1a-G1d for one state. Returns the four booleans."""
    dev = d[d["date"] < SPLIT_DATE].copy()
    print("\n" + "=" * 92)
    print(f"GATES for {lab}")
    print("=" * 92)

    long = pd.concat([dev[[f"ref{i}", col]].rename(columns={f"ref{i}": "ref"})
                      for i in (1, 2, 3)])
    per = long.groupby("ref")[col].agg(["mean", "size", "std"])
    per = per[per["size"] >= 100]
    se2 = (per["std"] ** 2 / per["size"]).mean()
    vobs = per["mean"].var(ddof=1)
    tau2 = vobs - se2
    print(f"  G1a  officials>=100 games {len(per)}   observed var {vobs:.5f}"
          f"   noise var {se2:.5f}")
    print(f"       TRUE between-official var {tau2:+.5f} -> SD "
          f"{np.sqrt(max(tau2,0)):.4f} poss/48   signal share "
          f"{max(tau2,0)/vobs:.3f}")
    g1a = tau2 > 0
    print(f"       GATE G1a: {'PASS' if g1a else 'FAIL'}")

    L = pd.concat([dev[["yr", "date", f"ref{i}", col]].rename(
        columns={f"ref{i}": "ref"}) for i in (1, 2, 3)]).sort_values("date")
    L["gn"] = L.groupby(["yr", "ref"]).cumcount()
    A = L[L["gn"] % 2 == 0].groupby(["yr", "ref"])[col].agg(["mean", "size"])
    B = L[L["gn"] % 2 == 1].groupby(["yr", "ref"])[col].agg(["mean", "size"])
    j = A.join(B, lsuffix="_a", rsuffix="_b").dropna()
    j = j[(j["size_a"] >= 20) & (j["size_b"] >= 20)]
    r = np.corrcoef(j["mean_a"], j["mean_b"])[0, 1]
    tb = r * np.sqrt(len(j) - 2) / np.sqrt(1 - r * r)
    ts = L.groupby(["yr", "ref"])[col].agg(["mean", "size"]).reset_index()
    ts = ts[ts["size"] >= 40]
    ts["nxt"] = ts["yr"] + 1
    jj = ts.merge(ts, left_on=["ref", "nxt"], right_on=["ref", "yr"],
                  suffixes=("_t", "_n"))
    rs = np.corrcoef(jj["mean_t"], jj["mean_n"])[0, 1]
    print(f"  G1b  official-seasons {len(j)}   split-half r {r:+.4f} "
          f"(t={tb:+.2f})   season-to-season {rs:+.4f} (n={len(jj)})")
    g1b = (r > 0) and (tb > 2)
    print(f"       GATE G1b: {'PASS' if g1b else 'FAIL'}")

    s = dev.dropna(subset=[crew_col, league_col, col])
    b, se, tt = ols(s[col].values,
                    np.column_stack([s[crew_col], s[league_col]]))
    print(f"  G1c  n={len(s):,}   {crew_col} slope {b[1]:+.4f} "
          f"(t={tt[1]:+.2f})   league state {b[2]:+.4f} (t={tt[2]:+.2f})")
    print(f"       [CrewShock's analogous slope ran 1.43-2.33 by season]")
    g1c = (b[1] > 0) and (tt[1] > 2)
    print(f"       GATE G1c: {'PASS' if g1c else 'FAIL'}")

    y = s[col].values
    lg = s[league_col].values
    cv = s[crew_col].values
    blk = ((s["date"] - s["date"].min()).dt.days // 7).values
    blocks = [np.where(blk == u)[0] for u in np.unique(blk)]
    null = np.empty(NPERM)
    for i in range(NPERM):
        p = cv.copy()
        for bl in blocks:
            if len(bl) > 1:
                p[bl] = cv[bl][RNG.permutation(len(bl))]
        bb, _, _ = ols(y, np.column_stack([p, lg]))
        null[i] = bb[1]
    pv = (1 + np.sum(np.abs(null) >= abs(b[1]))) / (NPERM + 1)
    print(f"  G1d  observed {b[1]:+.4f}   null {null.mean():+.4f} "
          f"sd {null.std():.4f}   two-sided p={pv:.4f}")
    g1d = pv < 0.05
    print(f"       GATE G1d: {'PASS' if g1d else 'FAIL'}")
    return g1a, g1b, g1c, g1d


def main():
    d = universe()
    print(f"  universe {len(d):,} games, seasons {sorted(d['yr'].unique())}")
    print(f"  [PBP_POSS absent for 2025-26; holdout here is 2024-25 only]")
    print(f"  pace48 mean {d['pace48'].mean():.3f}  sd {d['pace48'].std():.3f} "
          f"possessions per 48")

    # isolation step: strip the foul channel, coefficients from DEVELOPMENT
    dev = d[d["date"] < SPLIT_DATE]
    bb, _, tt = ols(dev["pace48"].values,
                    np.column_stack([dev["pf_rate"].values]))
    d["pace_net"] = d["pace48"] - (bb[0] + bb[1] * d["pf_rate"])
    print(f"\n  isolation: pace48 ~ pf_rate  b {bb[1]:+.4f} (t={tt[1]:+.2f}) "
          f"on development")
    print(f"  corr(pace48, pf_rate) = "
          f"{d[['pace48','pf_rate']].corr().iloc[0,1]:+.4f}"
          f"   -> foul channel removed for the PRIMARY state")
    print(f"  pace_net sd {d['pace_net'].std():.3f}")

    for col, crew, lg in (("pace_net", "CrewPaceNet", "LeaguePaceNetState"),
                          ("pace48", "CrewPace", "LeaguePaceState")):
        k, sig, _, _ = CT.estimate_k(d, col)
        d[lg] = CT.league_climate(d, col)
        d[crew] = CT.matched_ref_effect(d, k, col)["eff"].values
        print(f"  {crew:12} k={k:,.1f}  sigma_ref={sig:.4f}  "
              f"sd={d[crew].std():.4f}")

    ck, _ = __import__("ref_features").estimate_k(d)
    d["CrewShock"] = CT.matched_ref_effect(d, ck, "pf_rate")["eff"].values
    print(f"\n  corr(CrewPaceNet, CrewShock) = "
          f"{d[['CrewPaceNet','CrewShock']].corr().iloc[0,1]:+.4f}"
          f"   [must be small or the isolation failed]")
    print(f"  corr(CrewPace   , CrewShock) = "
          f"{d[['CrewPace','CrewShock']].corr().iloc[0,1]:+.4f}"
          f"   [raw version, expected larger]")

    prim = gates(d, "pace_net", "PRIMARY — CrewPaceNet (foul channel removed)",
                 "CrewPaceNet", "LeaguePaceNetState")
    diag = gates(d, "pace48", "DIAGNOSTIC ONLY — CrewPace (raw, not the test)",
                 "CrewPace", "LeaguePaceState")

    print("\n" + "=" * 92)
    print("STAGE 1 VERDICT")
    print("=" * 92)
    nm = ("G1a heterogeneity", "G1b split-half", "G1c forward persistence",
          "G1d permutation")
    print(f"  {'gate':28}{'PRIMARY pace_net':>20}{'diagnostic raw':>18}")
    for i, n_ in enumerate(nm):
        print(f"  {n_:28}{'PASS' if prim[i] else 'FAIL':>20}"
              f"{'PASS' if diag[i] else 'FAIL':>18}")
    allp = all(prim)
    print(f"\n  -> {'ALL GATES PASS: proceed to Stage 2' if allp else 'GATE FAILED: STOP. No market quantity is computed.'}")


if __name__ == "__main__":
    main()
