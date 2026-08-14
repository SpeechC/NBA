"""CrewShock extreme-group team-state balance test.

Diagnostic only. Nothing here changes the frozen estimator, thresholds, team
states or the trading strategy.

Question: do games assigned to extreme HIGH-CrewShock crews involve
systematically different teams or market environments than extreme LOW ones?

Thresholds are the FROZEN development quantiles that produced +0.8682 in
PREREG_ref_regime.md. The script reproduces that number from the same
development sample before using the corresponding Q15, and asserts the match.

Only pregame prior-only states enter. No realized same-game statistic of any
kind appears in this file.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import crew_team_diag as ctd
import ref_features as rf
import ref_regime as rg
from data_split import SPLIT_DATE

FROZEN_Q85 = 0.8682
NPERM = 400
BLOCK_DAYS = 7
RNG = RNG = np.random.default_rng(31337)

# mechanical game-level symmetric averages of existing frozen states only
AVG = {
    "PaceAvg": ("h_f_PACE", "a_f_PACE"),
    "OffEffAvg": ("h_f_OEFF", "a_f_OEFF"),
    "DefEffAvg": ("h_f_DEFF", "a_f_DEFF"),
    "FTAAvg": ("h_f_FTA", "a_f_FTA"),
    "FTPctAvg": ("h_f_FT%", "a_f_FT%"),
    "TOVAvg": ("h_f_TOV", "a_f_TOV"),
    "ORBAvg": ("h_f_ORB", "a_f_ORB"),
    "TPAAvg": ("h_f_3PA", "a_f_3PA"),
    "FoulDrawAvg": ("FD_h", "FD_a"),
    "FoulCommitAvg": ("FC_h", "FC_a"),
}


def smd(x, hi, lo, cols):
    """Standardised mean difference for each column."""
    a, b = x.loc[hi, cols].values, x.loc[lo, cols].values
    ma, mb = a.mean(0), b.mean(0)
    sa, sb = a.std(0, ddof=1), b.std(0, ddof=1)
    pooled = np.sqrt((sa ** 2 + sb ** 2) / 2.0)
    return ma, mb, ma - mb, np.divide(ma - mb, pooled,
                                      out=np.zeros_like(ma),
                                      where=pooled > 0)


def label(v):
    a = abs(v)
    return ("trivial" if a < 0.10 else "small" if a < 0.20
            else "potentially meaningful" if a < 0.30 else "SUBSTANTIAL")


def main():
    # ---- frozen thresholds, verified against the pre-registered value ----
    rgd, _, _ = rg.build()
    dev_rg = rgd[rgd["date"] < SPLIT_DATE]
    q85 = dev_rg["CrewShock"].quantile(0.85)
    q15 = dev_rg["CrewShock"].quantile(0.15)
    assert abs(q85 - FROZEN_Q85) < 5e-4, f"Q85 {q85} != frozen {FROZEN_Q85}"
    print(f"  reproduced frozen development Q85 = {q85:+.4f} "
          f"(pre-registered {FROZEN_Q85:+.4f})")
    print(f"  corresponding development Q15    = {q15:+.4f}")

    d = ctd.build()
    STATES = list(ctd.STATES)
    s = d.dropna(subset=["CrewShock"] + STATES).reset_index(drop=True)
    for nm, (a, b) in AVG.items():
        s[nm] = (s[a] + s[b]) / 2.0
    COLS = STATES + list(AVG)
    print(f"  {len(s):,} games, {len(COLS)} predeclared states "
          f"({len(STATES)} original + {len(AVG)} mechanical averages)")

    s["grp"] = np.where(s["CrewShock"] >= q85, "HIGH",
                        np.where(s["CrewShock"] <= q15, "LOW", "MID"))
    dev, hold = s[s["date"] < SPLIT_DATE], s[s["date"] >= SPLIT_DATE]
    for lab, x in (("pooled", s), ("development", dev), ("holdout", hold)):
        print(f"    {lab:12} HIGH {int((x['grp']=='HIGH').sum()):5,}  "
              f"MID {int((x['grp']=='MID').sum()):5,}  "
              f"LOW {int((x['grp']=='LOW').sum()):5,}")

    def tab(x):
        hi, lo = (x["grp"] == "HIGH").values, (x["grp"] == "LOW").values
        ma, mb, diff, sm = smd(x, hi, lo, COLS)
        return pd.DataFrame({"Variable": COLS, "HIGH mean": ma,
                             "LOW mean": mb, "Diff": diff, "SMD": sm}), \
            int(hi.sum()), int(lo.sum())

    Tp, nhp, nlp = tab(s)
    Td, _, _ = tab(dev)
    Th, _, _ = tab(hold)

    # ---------------- permutation ---------------------------------------
    uni, k, crew, blocks, keep = ctd.perm_setup(s)
    sub = uni.copy()
    Xall = s[COLS].values
    nullS = np.empty((NPERM, len(COLS)))
    teams = sorted(set(s["TEAM_H"]) | set(s["TEAM_R"]))
    ti = {t: i for i, t in enumerate(teams)}
    A = np.zeros((len(s), len(teams)))
    for r, (th, ta) in enumerate(zip(s["TEAM_H"], s["TEAM_R"])):
        A[r, ti[th]] = 1
        A[r, ti[ta]] = 1
    cA = A.sum(0)
    nullHi = np.empty((NPERM, len(teams)))
    for j in range(NPERM):
        perm = crew.copy()
        for b in blocks:
            if len(b) > 1:
                perm[b] = crew[b][RNG.permutation(len(b))]
        sub["ref1"], sub["ref2"], sub["ref3"] = perm[:, 0], perm[:, 1], perm[:, 2]
        c = rf.matched_ref_effect(sub, k)["CrewShock"].values[keep]
        hi, lo = c >= q85, c <= q15
        a_, b_ = Xall[hi], Xall[lo]
        pooled = np.sqrt((a_.std(0, ddof=1) ** 2 + b_.std(0, ddof=1) ** 2) / 2)
        nullS[j] = np.divide(a_.mean(0) - b_.mean(0), pooled,
                             out=np.zeros(len(COLS)), where=pooled > 0)
        nullHi[j] = (A[hi].sum(0)) / cA
    fw = np.abs(nullS).max(1)
    Tp["perm p"] = [(1 + (np.abs(nullS[:, i]) >= abs(v)).sum()) / (NPERM + 1)
                    for i, v in enumerate(Tp["SMD"])]

    print("\n" + "=" * 100)
    print("TOP 15 VARIABLES BY ABSOLUTE POOLED SMD")
    print("=" * 100)
    P = Tp.reindex(np.argsort(-np.abs(Tp["SMD"].values))).reset_index(drop=True)
    print(f"  {'Variable':22}{'HIGH mean':>12}{'LOW mean':>12}{'Diff':>10}"
          f"{'SMD':>9}{'perm p':>9}  magnitude")
    for _, r in P.head(15).iterrows():
        print(f"  {r['Variable']:22}{r['HIGH mean']:12.4f}{r['LOW mean']:12.4f}"
              f"{r['Diff']:10.4f}{r['SMD']:9.4f}{r['perm p']:9.4f}  "
              f"{label(r['SMD'])}")
    P.to_csv("crew_tail_balance.csv", index=False)
    print(f"\n  complete {len(P)}-variable table written to "
          f"crew_tail_balance.csv")

    print("\n" + "=" * 100)
    print("DEVELOPMENT vs HOLDOUT, same variables")
    print("=" * 100)
    md = dict(zip(Td["Variable"], Td["SMD"]))
    mh = dict(zip(Th["Variable"], Th["SMD"]))
    print(f"  {'Variable':22}{'Dev SMD':>10}{'Holdout SMD':>14}"
          f"{'Same sign?':>12}{'Similar mag?':>14}")
    for v in P.head(15)["Variable"]:
        a, b = md[v], mh[v]
        same = "Y" if np.sign(a) == np.sign(b) else "N"
        sim = "Y" if abs(abs(a) - abs(b)) < 0.10 else "N"
        print(f"  {v:22}{a:10.4f}{b:14.4f}{same:>12}{sim:>14}")

    print("\n" + "=" * 100)
    print("FAMILY-WISE PERMUTATION (primary decision rule)")
    print("=" * 100)
    mobs = np.abs(Tp["SMD"]).max()
    pfw = (1 + (fw >= mobs).sum()) / (NPERM + 1)
    print(f"  observed max |SMD|              {mobs:.4f} "
          f"({P['Variable'].iloc[0]})")
    print(f"  permutation-null mean max |SMD| {fw.mean():.4f}")
    print(f"  permutation SD                  {fw.std():.4f}")
    print(f"  permutation 95th percentile     {np.percentile(fw, 95):.4f}")
    print(f"  FAMILY-WISE empirical p         {pfw:.4f}")

    print("\n" + "=" * 100)
    print("MARKET ENVIRONMENT — closing total and spread")
    print("=" * 100)
    for v in ("total", "open_total", "abs_spread", "spread"):
        r = Tp[Tp["Variable"] == v].iloc[0]
        print(f"  {v:14} HIGH {r['HIGH mean']:8.3f}   LOW {r['LOW mean']:8.3f}"
              f"   diff {r['Diff']:+7.3f}   SMD {r['SMD']:+.4f}  "
              f"({label(r['SMD'])})")

    print("\n" + "=" * 100)
    print("HIGH and LOW versus MID — top 5 by |SMD|")
    print("=" * 100)
    mid = (s["grp"] == "MID").values
    hi_m, lo_m = (s["grp"] == "HIGH").values, (s["grp"] == "LOW").values
    print(f"  {'Variable':22}{'HIGH':>10}{'MID':>10}{'LOW':>10}"
          f"{'HIGH-MID':>11}{'LOW-MID':>10}{'Dev SMD':>10}{'Hold SMD':>10}")
    top5 = P.head(5)["Variable"].tolist()
    for v in top5:
        a = s.loc[hi_m, v].values
        m_ = s.loc[mid, v].values
        b = s.loc[lo_m, v].values
        p1 = np.sqrt((a.std(ddof=1) ** 2 + m_.std(ddof=1) ** 2) / 2)
        p2 = np.sqrt((b.std(ddof=1) ** 2 + m_.std(ddof=1) ** 2) / 2)
        print(f"  {v:22}{a.mean():10.4f}{m_.mean():10.4f}{b.mean():10.4f}"
              f"{(a.mean()-m_.mean())/p1:11.4f}"
              f"{(b.mean()-m_.mean())/p2:10.4f}{md[v]:10.4f}{mh[v]:10.4f}")

    print("\n" + "=" * 100)
    print("HOME / AWAY COMPONENTS of the largest game-level differences")
    print("=" * 100)
    shown = set()
    for v in top5:
        if v in AVG:
            for c in AVG[v]:
                r = Tp[Tp["Variable"] == c].iloc[0]
                print(f"  {v:16} <- {c:12} HIGH {r['HIGH mean']:9.4f}  "
                      f"LOW {r['LOW mean']:9.4f}  SMD {r['SMD']:+.4f}")
                shown.add(c)
    if not shown:
        print("  (no game-level average appears in the top 5; components "
              "already shown individually)")

    print("\n" + "=" * 100)
    print("TEAM-IDENTITY COMPOSITION — share of each team's games in HIGH")
    print("=" * 100)
    obs_hi = A[hi_m].sum(0) / cA
    z = (obs_hi - nullHi.mean(0)) / nullHi.std(0)
    fwT = np.abs((nullHi - nullHi.mean(0)) / nullHi.std(0)).max(1)
    T = pd.DataFrame({"Team": teams, "games": cA.astype(int),
                      "HIGH share %": (100 * obs_hi).round(2),
                      "LOW share %": (100 * A[lo_m].sum(0) / cA).round(2),
                      "perm z": z.round(2)})
    T["FWER p"] = [(1 + (fwT >= abs(v)).sum()) / (NPERM + 1) for v in z]
    T = T.sort_values("HIGH share %", ascending=False)
    print(T.head(6).to_string(index=False))
    print("  ...")
    print(T.tail(6).to_string(index=False))
    print(f"\n  max |z| across teams {np.abs(z).max():.2f}   "
          f"family-wise p = {(1 + (fwT >= np.abs(z).max()).sum())/(NPERM+1):.4f}")

    print("\n" + "=" * 100)
    print("SUMMARY")
    print("=" * 100)
    print(f"  HIGH games:                      {nhp:,}")
    print(f"  LOW games:                       {nlp:,}")
    print(f"  Maximum observed |SMD|:          {mobs:.4f}")
    print(f"  Permutation-null mean max |SMD|: {fw.mean():.4f}")
    print(f"  Permutation 95th percentile:     {np.percentile(fw, 95):.4f}")
    print(f"  Family-wise p:                   {pfw:.4f}")
    rt = Tp[Tp["Variable"] == "total"].iloc[0]
    ra = Tp[Tp["Variable"] == "abs_spread"].iloc[0]
    print(f"  Closing total HIGH:              {rt['HIGH mean']:.3f}")
    print(f"  Closing total LOW:               {rt['LOW mean']:.3f}")
    print(f"  Closing-total SMD:               {rt['SMD']:+.4f}")
    print(f"  Absolute spread HIGH:            {ra['HIGH mean']:.3f}")
    print(f"  Absolute spread LOW:             {ra['LOW mean']:.3f}")
    print(f"  Spread SMD:                      {ra['SMD']:+.4f}")


if __name__ == "__main__":
    main()
