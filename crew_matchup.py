"""Test 2 — crew foul propensity x matchup foul pressure.

Pre-registered in PREREG_crew_matchup.md. The decisive comparison is not
whether the interaction predicts scoring, but whether

    Crew x Matchup -> fouls -> FTA -> ACTUAL total     strengthens
    Crew x Matchup -> CLOSING total                    stays weak

Everything is prior-only and expressed as a ratio to the trailing 500-game
league foul level, because league foul rates fell steadily 2017-2026 and Test 1
showed unadjusted thresholds partition by season.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import crew_foul as cfm
import refs
from data_split import SPLIT_DATE
from dispersion_priced import ols

W, MINP = 20, 10
NPERM = 1000
BE = 110 / 210
RNG = np.random.default_rng(2718)

LINKS = [("pf_rate", "fouls per 100 poss"), ("fouls", "raw fouls"),
         ("fta", "free throw attempts"), ("actual", "ACTUAL TOTAL"),
         ("total", "CLOSING TOTAL"), ("e", "closing residual")]


def build():
    d = cfm.build()                     # has pf_rate, fouls, fta, lg, y, mu_state
    adv = pd.read_csv(cfm.ADVF, low_memory=False)
    adv["gid"] = adv["GAME-ID"].astype(str).str.strip()
    cols = {s: f"ADV_PF_PER100_OPP_POSS_{s}" for s in ("H", "R")}
    adv = adv[["gid"] + list(cols.values())]
    keep = [c for c in adv.columns if c not in d.columns or c == "gid"]
    n0 = len(d)
    d = d.merge(adv[keep], on="gid", how="left")
    assert len(d) == n0
    for s in ("H", "R"):
        if cols[s] not in d.columns:
            d[cols[s]] = d[f"{cols[s]}_x"] if f"{cols[s]}_x" in d else np.nan

    # per-team commits / draws, as ratios to the trailing league level
    opp = {"H": "R", "R": "H"}
    P = pd.concat([
        pd.DataFrame({"gid": d["gid"], "yr": d["yr"], "date": d["date"],
                      "team": d[f"TEAM_{s}"], "side": s,
                      "commits": d[cols[s]] / (d["lg"] / 2.0),
                      "draws": d[cols[opp[s]]] / (d["lg"] / 2.0)})
        for s in ("H", "R")]).sort_values("date").reset_index(drop=True)
    g = P.groupby(["yr", "team"])
    for c in ("commits", "draws"):
        P[f"m_{c}"] = g[c].transform(
            lambda s: s.shift(1).rolling(W, min_periods=MINP).mean())
    h = P[P.side == "H"][["gid", "m_commits", "m_draws"]].rename(
        columns={"m_commits": "FC_h", "m_draws": "FD_h"})
    a = P[P.side == "R"][["gid", "m_commits", "m_draws"]].rename(
        columns={"m_commits": "FC_a", "m_draws": "FD_a"})
    assert not (set(h.columns) | set(a.columns)) & set(d.columns) - {"gid"}
    d = d.merge(h, on="gid").merge(a, on="gid")
    d["M"] = d["FD_h"] * d["FC_a"] + d["FD_a"] * d["FC_h"]
    d["CrewFoul"], _ = cfm.crew_signal(d, cfm.estimate_k(
        d[d["date"] < SPLIT_DATE])[0])
    return d.dropna(subset=["M", "CrewFoul", "mu_state"]).reset_index(drop=True)


def cells(d, qc, qm, lab):
    d = d.copy()
    d["C"] = d["CrewFoul"] >= qc
    d["Mh"] = d["M"] >= qm
    grp = {"neither": d[~d.C & ~d.Mh], "crew only": d[d.C & ~d.Mh],
           "matchup only": d[~d.C & d.Mh], "BOTH": d[d.C & d.Mh]}
    print(f"\n  {lab}   n={len(d):,}   "
          + "  ".join(f"{k} {len(v):,}" for k, v in grp.items()))
    print(f"    {'link':22}" + "".join(f"{k:>14}" for k in grp)
          + f"{'INTERACTION':>14}{'t':>7}")
    out = {}
    for col, name in LINKS:
        mus = {k: v[col].mean() for k, v in grp.items()}
        var = {k: v[col].var(ddof=1) / len(v) for k, v in grp.items()}
        inter = (mus["BOTH"] - mus["crew only"]) - (mus["matchup only"]
                                                    - mus["neither"])
        se = np.sqrt(sum(var.values()))
        print(f"    {name:22}" + "".join(f"{mus[k]:14.3f}" for k in grp)
              + f"{inter:14.3f}{inter/se:7.2f}")
        out[col] = (inter, inter / se, mus)
    for k, v in grp.items():
        ov = (v["e"] > 0).mean()
        print(f"    over rate {k:14} {100*ov:7.2f}% +/- "
              f"{100*1.96*np.sqrt(ov*(1-ov)/len(v)):.2f}   n={len(v):,}")
    return out, grp


def main():
    d = build()
    dev = d[d["date"] < SPLIT_DATE]
    hold = d[d["date"] >= SPLIT_DATE]
    qc = dev["CrewFoul"].quantile(0.75)
    qm = dev["M"].quantile(0.75)
    print("=" * 110)
    print("TEST 2 — CREW FOUL PROPENSITY x MATCHUP FOUL PRESSURE")
    print("=" * 110)
    print(f"  {len(d):,} games   develop {len(dev):,}   holdout {len(hold):,}")
    print(f"  M: mean {d['M'].mean():.4f} sd {d['M'].std():.4f}   "
          f"CrewFoul: mean {d['CrewFoul'].mean():+.3f} sd {d['CrewFoul'].std():.3f}")
    print(f"  FROZEN develop Q75:  CrewFoul {qc:+.4f}   M {qm:.4f}")
    r = np.corrcoef(d["CrewFoul"], d["M"])[0, 1]
    print(f"  corr(CrewFoul, M) = {r:+.4f}   [near zero keeps the 2x2 clean]")
    print(f"  M season means: "
          + " ".join(f"{y}:{g['M'].mean():.3f}"
                     for y, g in d.groupby("yr")))

    print("\n" + "=" * 110)
    print("THE 2x2 — cell means and the interaction contrast")
    print("   interaction = (BOTH - crew only) - (matchup only - neither)")
    print("=" * 110)
    od, gd = cells(dev, qc, qm, "DEVELOP")
    oh, gh = cells(hold, qc, qm, "HOLDOUT 2024-25 + 2025-26")
    for y in sorted(hold["yr"].unique()):
        cells(hold[hold["yr"] == y], qc, qm, f"  holdout season {y}")

    print("\n" + "=" * 110)
    print("CRITERION 3 — does the CLOSING total contain the interaction?")
    print("=" * 110)
    print(f"    {'':26}{'ACTUAL total':>16}{'CLOSING total':>16}"
          f"{'captured':>12}")
    for lab, o in (("develop", od), ("holdout", oh)):
        ia, ta = o["actual"][0], o["actual"][1]
        ic, tc = o["total"][0], o["total"][1]
        cap = 100 * ic / ia if abs(ia) > 1e-9 else np.nan
        print(f"    {lab:26}{ia:11.3f} (t={ta:+4.2f}){ic:11.3f} "
              f"(t={tc:+4.2f}){cap:11.1f}%")

    print("\n" + "=" * 110)
    print("MARKET TEST — coefficient on the CrewFoul x M product")
    print("=" * 110)
    for lab, x in (("develop", dev), ("holdout", hold), ("all", d)):
        X = np.column_stack([x["mu_state"], x["CrewFoul"], x["M"],
                             x["CrewFoul"] * x["M"]])
        bm, sem, tm = ols(x["total"].values, X)
        bt, set_, tt = ols(x["actual"].values, X)
        gap = bt[4] - bm[4]
        sg = np.sqrt(set_[4] ** 2 + sem[4] ** 2)
        print(f"  {lab:8} n={len(x):5,}   c_market {bm[4]:+7.3f} "
              f"(t={tm[4]:+5.2f})   c_true {bt[4]:+7.3f} (t={tt[4]:+5.2f})"
              f"   gap {gap:+7.3f} (t={gap/sg:+5.2f})")

    print("\n" + "=" * 110)
    print("PERMUTATION — matched-size, within-season crew reshuffle")
    print("=" * 110)
    k = cfm.estimate_k(dev)[0]
    for lab, x in (("develop", dev), ("holdout", hold)):
        both = x[(x["CrewFoul"] >= qc) & (x["M"] >= qm)]
        obs = both["e"].mean()
        nboth = len(both)
        idx = x.index.values
        crew = d.loc[idx, ["ref1", "ref2", "ref3"]].values
        yrs = d.loc[idx, "yr"].values
        blocks = [np.where(yrs == u)[0] for u in np.unique(yrs)]
        sub = d.loc[idx].reset_index(drop=True).copy()
        mh = (sub["M"] >= qm).values
        null = np.empty(NPERM)
        for j in range(NPERM):
            perm = crew.copy()
            for b in blocks:
                perm[b] = crew[b][RNG.permutation(len(b))]
            sub["ref1"], sub["ref2"], sub["ref3"] = perm[:, 0], perm[:, 1], perm[:, 2]
            cf, _ = cfm.crew_signal(sub, k)
            # matched size: top-nboth CrewFoul games among the same M-high pool
            pool = np.where(mh)[0]
            top = pool[np.argsort(cf[pool])[-nboth:]]
            null[j] = sub.iloc[top]["e"].mean()
        p = (1 + np.sum(null >= obs)) / (NPERM + 1)
        ov = (both["e"] > 0).mean()
        print(f"  {lab:8} BOTH cell n={nboth:4,}  mean residual {obs:+.3f}  "
              f"over {100*ov:.2f}%   null mean {null.mean():+.3f} "
              f"sd {null.std():.3f}   one-sided p={p:.4f}")


if __name__ == "__main__":
    main()
