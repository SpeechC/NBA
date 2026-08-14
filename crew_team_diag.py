"""CrewShock x team diagnostic. Nothing here changes the frozen estimator or
the trading strategy.

  Part 1  team-level CrewShock exposure, family-wise permutation z
  Part 2  correlation with predeclared prior-only team states, family-wise
          max-|r| permutation
  Part 3  multivariate assignment model, R^2 with permutation null
  Part 4  team response heterogeneity on defensive fouls per 100, shrunk
  Part 5  predeclared team-type interactions, one at a time

Parts 1-3 use all eight seasons. Parts 4-5 need the foul-type classification,
which comes from the play-by-play parquet and ends at 2024-25.

All permutations are the existing 7-day-block crew reshuffle, rebuilding
CrewShock from scratch on the full universe each time.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import foul_types
import ref_features as rf
import ref_shock as rsk
import refs
from crew_offense import cluster_ols
from dispersion_priced import ols

ADVF = "/mnt/c/NBA2/advanced_stats/game_advanced_stats.csv"
NPERM, NPERM4 = 400, 300
BLOCK_DAYS = 7
RNG = np.random.default_rng(90210)

# ---- PREDECLARED prior-only state list. Frozen states only; nothing new. ----
LAG4 = ["h_f_OEFF", "a_f_OEFF", "h_f_DEFF", "a_f_DEFF", "h_f_PACE", "a_f_PACE",
        "h_f_FT%", "a_f_FT%", "h_f_FTA", "a_f_FTA", "h_f_3PA", "a_f_3PA",
        "h_f_TOV", "a_f_TOV", "h_f_ORB", "a_f_ORB", "pace_sum",
        "implied_minus_open"]
W20 = rsk.CTRL                      # mu_state pace_s oeff_s deff_s FC/FD M ftr tpa
MARKET = ["open_total", "total", "spread", "abs_spread"]
STATES = LAG4 + W20 + MARKET + ["LeagueFoulState"]


def build():
    from models_frozen import add_pace_terms
    from symmetric_features import build as sym_build
    m = refs.build()
    m["gid"] = m["GAME-ID"].astype(str).str.strip()
    n = lambda c: pd.to_numeric(m[c], errors="coerce")
    m["spread"] = n("CLOSING SPREAD_H")
    m["abs_spread"] = m["spread"].abs()

    G = add_pace_terms(sym_build())
    G["gid"] = G["gid"].astype(str).str.strip()
    G = G[["gid"] + [c for c in LAG4 if c in G.columns]
          + ["open_total"]].drop_duplicates("gid")
    m = m.merge(G, on="gid", how="left")

    f = pd.read_csv("ref_features.csv")
    f["gid"] = f["gid"].astype(str).str.strip()
    m = m.merge(f[["gid", "CrewShock", "LeagueFoulState"]], on="gid", how="left")
    ctl = rsk.build()[["gid"] + W20]
    ctl["gid"] = ctl["gid"].astype(str).str.strip()
    m = m.merge(ctl, on="gid", how="left")

    adv = pd.read_csv(ADVF, low_memory=False)
    adv["gid"] = adv["GAME-ID"].astype(str).str.strip()
    adv["poss_g"] = (pd.to_numeric(adv["PBP_POSS_H"], errors="coerce")
                     + pd.to_numeric(adv["PBP_POSS_R"], errors="coerce"))
    m = m.merge(adv[["gid", "poss_g", "PBP_POSS_H", "PBP_POSS_R"]], on="gid",
                how="left")
    F = foul_types.build()
    F["gid"] = F["gid"].astype(str).str.zfill(10)
    m["gidz"] = m["gid"].str.zfill(10)
    m = m.merge(F[["gid", "def_fouls_H", "def_fouls_R"]].rename(
        columns={"gid": "gidz"}), on="gidz", how="left")
    return m


def perm_setup(s):
    """7-day-block crew permutation machinery, shared by parts 1-3."""
    uni = rf.universe()
    k = rf.estimate_k(uni)[0]
    blk = (uni["yr"].astype(str) + "_"
           + ((uni["date"] - uni.groupby("yr")["date"].transform("min"))
              .dt.days // BLOCK_DAYS).astype(str)).values
    crew = uni[["ref1", "ref2", "ref3"]].values
    blocks = [np.where(blk == b)[0] for b in pd.unique(blk)]
    keep = pd.Series(np.arange(len(uni)),
                     index=uni["gid"].astype(str)).reindex(s["gid"]).values
    return uni, k, crew, blocks, keep


def main():
    d = build()
    s = d.dropna(subset=["CrewShock"] + STATES).reset_index(drop=True)
    print(f"  {len(s):,} games with CrewShock and all {len(STATES)} "
          f"predeclared states, seasons {sorted(s['yr'].unique())}")

    # ---------- incidence for team means -------------------------------
    teams = sorted(set(s["TEAM_H"]) | set(s["TEAM_R"]))
    ti = {t: i for i, t in enumerate(teams)}
    nT = len(teams)
    A = np.zeros((len(s), nT))          # all games
    H = np.zeros((len(s), nT))          # home
    Aw = np.zeros((len(s), nT))         # away
    for r, (th, ta) in enumerate(zip(s["TEAM_H"], s["TEAM_R"])):
        A[r, ti[th]] = 1; A[r, ti[ta]] = 1
        H[r, ti[th]] = 1; Aw[r, ti[ta]] = 1
    cA, cH, cAw = A.sum(0), H.sum(0), Aw.sum(0)

    X = s[STATES].values.astype(float)
    Xz = (X - X.mean(0)) / X.std(0)
    yrd = pd.get_dummies(s["yr"], drop_first=True).values.astype(float)
    mth = pd.get_dummies(s["date"].dt.month, drop_first=True).values.astype(float)
    D = np.column_stack([np.ones(len(s)), Xz, yrd, mth])
    Pmat = D @ np.linalg.pinv(D)

    cs = s["CrewShock"].values
    q85 = np.quantile(s.loc[s["date"] < pd.Timestamp("2024-07-01"),
                            "CrewShock"], 0.85)
    q15 = np.quantile(s.loc[s["date"] < pd.Timestamp("2024-07-01"),
                            "CrewShock"], 0.15)

    obs_mA = (A.T @ cs) / cA
    obs_mH = (H.T @ cs) / cH
    obs_mAw = (Aw.T @ cs) / cAw
    obs_r = np.array([np.corrcoef(cs, Xz[:, j])[0, 1]
                      for j in range(Xz.shape[1])])
    obs_rs = np.array([pd.Series(cs).corr(pd.Series(X[:, j]), method="spearman")
                       for j in range(X.shape[1])])
    fit = Pmat @ cs
    obs_r2 = 1 - ((cs - fit) ** 2).sum() / ((cs - cs.mean()) ** 2).sum()

    # ---------- shared permutation loop --------------------------------
    uni, k, crew, blocks, keep = perm_setup(s)
    sub = uni.copy()
    nullA = np.empty((NPERM, nT))
    nullR = np.empty((NPERM, Xz.shape[1]))
    nullR2 = np.empty(NPERM)
    for j in range(NPERM):
        perm = crew.copy()
        for b in blocks:
            if len(b) > 1:
                perm[b] = crew[b][RNG.permutation(len(b))]
        sub["ref1"], sub["ref2"], sub["ref3"] = perm[:, 0], perm[:, 1], perm[:, 2]
        c = rf.matched_ref_effect(sub, k)["CrewShock"].values[keep]
        nullA[j] = (A.T @ c) / cA
        cc = c - c.mean()
        nullR[j] = (Xz.T @ cc) / (np.sqrt((cc ** 2).sum())
                                  * np.sqrt((Xz ** 2).sum(0)))
        f2 = Pmat @ c
        nullR2[j] = 1 - ((c - f2) ** 2).sum() / ((c - c.mean()) ** 2).sum()

    print("\n" + "=" * 104)
    print("A. TEAM ASSIGNMENT TABLE (all seasons pooled)")
    print("=" * 104)
    zt = (obs_mA - nullA.mean(0)) / nullA.std(0)
    fw = np.abs((nullA - nullA.mean(0)) / nullA.std(0)).max(1)
    T = pd.DataFrame({
        "Team": teams, "Games": cA.astype(int),
        "Mean CS": obs_mA.round(4), "Home": obs_mH.round(4),
        "Away": obs_mAw.round(4),
        "Q85%": [round(100 * ((A[:, i] == 1) & (cs >= q85)).sum() / cA[i], 1)
                 for i in range(nT)],
        "Q15%": [round(100 * ((A[:, i] == 1) & (cs <= q15)).sum() / cA[i], 1)
                 for i in range(nT)],
        "perm z": zt.round(2),
        "FWER p": [(1 + (fw >= abs(z)).sum()) / (NPERM + 1) for z in zt]})
    T = T.sort_values("Mean CS", ascending=False)
    print(T.to_string(index=False))
    print(f"\n  max |z| across teams = {np.abs(zt).max():.2f}   "
          f"family-wise p = {(1 + (fw >= np.abs(zt).max()).sum())/(NPERM+1):.4f}")
    T.to_csv("crew_team_assignment.csv", index=False)

    print("\n" + "=" * 104)
    print("B. CrewShock CORRELATION WITH PREDECLARED PRIOR-ONLY STATES")
    print("=" * 104)
    fwr = np.abs(nullR).max(1)
    rows = []
    for j, nm in enumerate(STATES):
        p_ind = (1 + (np.abs(nullR[:, j]) >= abs(obs_r[j])).sum()) / (NPERM + 1)
        rows.append({"Pregame state": nm, "Pearson r": round(obs_r[j], 4),
                     "Spearman r": round(obs_rs[j], 4),
                     "perm p": round(p_ind, 4),
                     "FW status": "-" if (fwr >= abs(obs_r[j])).mean() > 0.05
                     else "EXCEEDS"})
    B = pd.DataFrame(rows).reindex(
        np.argsort(-np.abs(obs_r))).reset_index(drop=True)
    print(B.to_string(index=False))
    mx = np.abs(obs_r).max()
    print(f"\n  observed max |r| = {mx:.4f} ({STATES[int(np.argmax(np.abs(obs_r)))]})")
    print(f"  family-wise null max |r|: mean {fwr.mean():.4f} "
          f"sd {fwr.std():.4f}  95th {np.percentile(fwr,95):.4f}")
    print(f"  FAMILY-WISE p = {(1 + (fwr >= mx).sum())/(NPERM+1):.4f}")
    B.to_csv("crew_state_correlations.csv", index=False)

    print("\n" + "=" * 104)
    print("C. MULTIVARIATE ASSIGNMENT MODEL")
    print("=" * 104)
    p_ = D.shape[1] - 1
    adj = 1 - (1 - obs_r2) * (len(s) - 1) / (len(s) - p_ - 1)
    loso = []
    for y in sorted(s["yr"].unique()):
        tr, te = s["yr"] != y, s["yr"] == y
        bb = np.linalg.pinv(D[tr.values]) @ cs[tr.values]
        pr = D[te.values] @ bb
        loso.append(1 - ((cs[te.values] - pr) ** 2).sum()
                    / ((cs[te.values] - cs[tr.values].mean()) ** 2).sum())
    pr2 = (1 + (nullR2 >= obs_r2).sum()) / (NPERM + 1)
    print(f"  predictors: {len(STATES)} team states + season + month dummies "
          f"({p_} total)")
    print(f"  R^2 {100*obs_r2:.3f}%   adjusted R^2 {100*adj:.3f}%")
    print(f"  leave-one-season-out R^2 {100*np.mean(loso):+.3f}% "
          f"(per season: {' '.join(f'{100*v:+.2f}' for v in loso)})")
    print(f"  permutation null R^2: mean {100*nullR2.mean():.3f}% "
          f"sd {100*nullR2.std():.3f}%   empirical p = {pr2:.4f}")

    # ---------------- Part 4/5: response heterogeneity -----------------
    print("\n" + "=" * 104)
    print("D. TEAM RESPONSE HETEROGENEITY — defensive fouls per 100")
    print("=" * 104)
    rows = []
    for side, opp in (("H", "R"), ("R", "H")):
        rows.append(pd.DataFrame({
            "gid": s["gid"], "yr": s["yr"], "date": s["date"],
            "team": s[f"TEAM_{side}"], "home": 1 if side == "H" else 0,
            "dfouls": s[f"def_fouls_{side}"], "opp_poss": s[f"PBP_POSS_{opp}"],
            "CrewShock": s["CrewShock"], "LeagueFoulState": s["LeagueFoulState"],
            "pace_s": s["pace_s"], "deff": s[f"{'h' if side=='H' else 'a'}_f_DEFF"],
            "FC": s[f"FC_{'h' if side=='H' else 'a'}"]}))
    P = pd.concat(rows, ignore_index=True).dropna(
        subset=["dfouls", "opp_poss", "CrewShock"])
    P["y"] = 100 * P["dfouls"] / P["opp_poss"]
    P = P.sort_values("date").reset_index(drop=True)
    print(f"  {len(P):,} team-games, seasons {sorted(P['yr'].unique())} "
          f"(foul types end 2024-25)")

    base = np.column_stack([P["CrewShock"], P["home"], P["LeagueFoulState"],
                            P["pace_s"]])
    b0, se0, t0 = cluster_ols(P["y"].values, base, P["gid"].values)
    print(f"  pooled slope bR = {b0[1]:+.4f} (t={t0[1]:+.2f})")

    est = []
    for tm, g in P.groupby("team"):
        if len(g) < 200:
            continue
        Xg = np.column_stack([g["CrewShock"], g["home"], g["LeagueFoulState"],
                              g["pace_s"]])
        b, se, t = cluster_ols(g["y"].values, Xg, g["gid"].values)
        est.append({"Team": tm, "n": len(g), "slope": b[1], "se": se[1]})
    E = pd.DataFrame(est)
    v_obs = np.var(E["slope"], ddof=1)
    v_noise = np.mean(E["se"] ** 2)
    tau2 = max(v_obs - v_noise, 0.0)
    E["shrunk"] = (E["slope"] * tau2 / (tau2 + E["se"] ** 2)
                   + E["slope"].mean() * E["se"] ** 2 / (tau2 + E["se"] ** 2))
    E["reliab"] = (tau2 / (tau2 + E["se"] ** 2)).round(3)
    E = E.sort_values("shrunk", ascending=False)
    print(f"\n  mean team slope {E['slope'].mean():+.4f}   "
          f"observed between-team SD {np.sqrt(v_obs):.4f}   "
          f"sampling-noise SD {np.sqrt(v_noise):.4f}")
    print(f"  implied true between-team SD = {np.sqrt(tau2):.4f}   "
          f"mean reliability {E['reliab'].mean():.3f}")
    print(E[["Team", "n", "slope", "se", "shrunk", "reliab"]].round(4)
          .to_string(index=False))
    E.to_csv("crew_team_response.csv", index=False)

    # omnibus permutation on slope dispersion
    uni2, k2, crew2, blocks2, keep2 = perm_setup(s)
    sub2 = uni2.copy()
    gid_to_row = pd.Series(np.arange(len(s)), index=s["gid"])
    pidx = gid_to_row.reindex(P["gid"]).values
    nullv = np.empty(NPERM4)
    for j in range(NPERM4):
        perm = crew2.copy()
        for b in blocks2:
            if len(b) > 1:
                perm[b] = crew2[b][RNG.permutation(len(b))]
        sub2["ref1"], sub2["ref2"], sub2["ref3"] = perm[:, 0], perm[:, 1], perm[:, 2]
        c = rf.matched_ref_effect(sub2, k2)["CrewShock"].values[keep2]
        Pn = P.copy()
        Pn["CrewShock"] = c[pidx]
        sl = []
        for tm, g in Pn.groupby("team"):
            if len(g) < 200:
                continue
            Xg = np.column_stack([g["CrewShock"], g["home"],
                                  g["LeagueFoulState"], g["pace_s"]])
            bb = np.linalg.lstsq(np.column_stack([np.ones(len(g)), Xg]),
                                 g["y"].values, rcond=None)[0]
            sl.append(bb[1])
        nullv[j] = np.var(sl, ddof=1)
    pv = (1 + (nullv >= v_obs).sum()) / (NPERM4 + 1)
    print(f"\n  OMNIBUS: observed slope variance {v_obs:.5f}   "
          f"null mean {nullv.mean():.5f} sd {nullv.std():.5f}   p = {pv:.4f}")

    print("\n" + "=" * 104)
    print("E. PREDECLARED TEAM-TYPE INTERACTIONS (one at a time)")
    print("=" * 104)
    P["prop"] = P.groupby(["yr", "team"])["y"].transform(
        lambda v: v.shift(1).rolling(20, min_periods=10).mean())
    Q = P.dropna(subset=["prop", "deff", "FC"]).copy()
    for var, lab, note in (("prop", "prior def foul propensity",
                            "  [RETIRED reference row]"),
                           ("deff", "defensive efficiency", ""),
                           ("pace_s", "expected pace", ""),
                           ("FC", "foul-committing state (W20)", "")):
        z = (Q[var] - Q[var].mean()) / Q[var].std()
        Xq = np.column_stack([Q["CrewShock"], z, Q["CrewShock"] * z,
                              Q["home"], Q["LeagueFoulState"], Q["pace_s"]])
        b, se, t = cluster_ols(Q["y"].values, Xq, Q["gid"].values)
        print(f"  {lab:32} bR {b[1]:+.4f}({t[1]:+5.2f})  "
              f"bX {b[2]:+.4f}({t[2]:+5.2f})  "
              f"delta {b[3]:+.4f}({t[3]:+5.2f}){note}")


if __name__ == "__main__":
    main()
