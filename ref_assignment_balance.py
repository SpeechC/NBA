"""Individual referee foul-propensity x team-type assignment diagnostic.

Composition only. Nothing here changes the frozen estimator, the shrinkage,
the team-state definitions or the CrewShock strategy. No same-game outcome
enters any comparison.

Questions, asked separately:
    E[X | HIGH-foul ref assignment] - E[X | contemporaneous league]
    E[X | LOW-foul  ref assignment] - E[X | contemporaneous league]

The league reference is WITHIN SEASON: every state is standardised against its
own season mean and SD, so league-wide drift in pace, efficiency, 3PA or fouls
cannot manufacture an assignment difference. The mean standardised value over a
group of assignments IS its SMD versus the contemporaneous league.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import crew_team_diag as ctd
import ref_2526_diag as r26
from data_split import SPLIT_DATE

NPERM = 400
BLOCK_DAYS = 7
RNG = np.random.default_rng(112358)

# own-team prior-only states: (panel name, home column, away column)
TEAM_ST = [("OEFF", "h_f_OEFF", "a_f_OEFF"), ("DEFF", "h_f_DEFF", "a_f_DEFF"),
           ("PACE", "h_f_PACE", "a_f_PACE"), ("FTA", "h_f_FTA", "a_f_FTA"),
           ("FTpct", "h_f_FT%", "a_f_FT%"), ("TPA", "h_f_3PA", "a_f_3PA"),
           ("TOV", "h_f_TOV", "a_f_TOV"), ("ORB", "h_f_ORB", "a_f_ORB"),
           ("FoulDraw", "FD_h", "FD_a"), ("FoulCommit", "FC_h", "FC_a")]
GAME_ST = ["total", "open_total", "spread", "abs_spread", "LeagueFoulState",
           "pace_sum", "mu_state", "oeff_s", "deff_s", "ftr_s", "tpa_s", "M",
           "pace_s", "implied_minus_open"]
COLS = [t[0] for t in TEAM_ST] + GAME_ST


def label(v):
    a = abs(v)
    return ("trivial" if a < 0.10 else "small" if a < 0.20
            else "potentially meaningful" if a < 0.30 else "SUBSTANTIAL")


def build():
    """Referee x game x team panel with within-season standardised states."""
    d, long, k = r26.internals()          # asserts match with ref_features.csv
    g = ctd.build()
    g["gid"] = g["gid"].astype(str).str.strip()
    d["gid"] = d["gid"].astype(str).str.strip()
    need = [c for _, a, b in TEAM_ST for c in (a, b)] + GAME_ST
    g = g.dropna(subset=need)
    keep = set(g["gid"])
    # `long["row"]` indexes the FULL universe. Stamp that index BEFORE any
    # filtering, otherwise a later reset_index silently re-points every
    # referee assignment at the wrong game.
    d["row"] = np.arange(len(d))
    d = d[d["gid"].isin(keep)].copy()

    # within-season standardisation = contemporaneous league reference
    z = g[["gid", "yr", "date", "TEAM_H", "TEAM_R"]].copy()
    for nm, hc, ac in TEAM_ST:
        for side, col in (("H", hc), ("R", ac)):
            v = g[col]
            mu = v.groupby(g["yr"]).transform("mean")
            sd = v.groupby(g["yr"]).transform("std")
            z[f"{nm}_{side}"] = (v - mu) / sd
    for c in GAME_ST:
        v = g[c]
        z[c] = (v - v.groupby(g["yr"]).transform("mean")) \
            / v.groupby(g["yr"]).transform("std")
        z[c + "_raw"] = v
    return d, long, k, z


def main():
    d, long, k, z = build()
    # referee-level frozen effect: shrunk prior-only effect at each assignment
    long = long.merge(d[["row", "gid", "yr"]], on="row", how="inner",
                      suffixes=("", "_d"))
    long["date_"] = pd.to_datetime(long["date"])
    if "yr_d" in long:
        long["yr"] = long["yr_d"]
    L = long.dropna(subset=["eff"]).copy()
    assert L["date_"].max() >= SPLIT_DATE, "holdout rows lost in the join"

    print("=" * 100)
    print("1 — INDIVIDUAL REFEREE FOUL EFFECT (frozen estimator, reproduced)")
    print("=" * 100)
    per = L.groupby("ref").agg(obs=("eff", "size"), raw=("raw", "mean"),
                               shrunk=("eff", "mean"),
                               prior=("career_prior", "median")).reset_index()
    per = per[per["obs"] >= 100].sort_values("shrunk", ascending=False)
    print(f"  {len(per)} officials with >= 100 assignment observations")

    devL = L[L["date_"] < SPLIT_DATE]
    dper = devL.groupby("ref")["eff"].mean()
    dcnt = devL.groupby("ref")["eff"].size()
    dper = dper[dcnt >= 100]
    q85, q15 = dper.quantile(0.85), dper.quantile(0.15)
    HIGH = set(dper[dper >= q85].index)
    LOW = set(dper[dper <= q15].index)
    print(f"\n  development referee Q15: {q15:+.4f}")
    print(f"  development referee Q85: {q85:+.4f}")
    print(f"  number of HIGH refs: {len(HIGH)}   number of LOW refs: {len(LOW)}")
    print("\n  HIGH-foul referees (development-frozen identity)")
    print(per[per["ref"].isin(HIGH)][["ref", "obs", "raw", "shrunk", "prior"]]
          .round(4).to_string(index=False))
    print("\n  LOW-foul referees")
    print(per[per["ref"].isin(LOW)][["ref", "obs", "raw", "shrunk", "prior"]]
          .round(4).to_string(index=False))

    # ---- two classification schemes -----------------------------------
    L["grp_frozen"] = np.where(L["ref"].isin(HIGH), "HIGH",
                               np.where(L["ref"].isin(LOW), "LOW", "MID"))
    L["grp_live"] = np.where(L["eff"] >= q85, "HIGH",
                             np.where(L["eff"] <= q15, "LOW", "MID"))

    # ---- attach standardised team states, two rows per assignment -----
    zz = z.set_index("gid")
    rows = []
    for side in ("H", "R"):
        t = L.copy()
        t["side"] = side
        t["team"] = zz[f"TEAM_{side}"].reindex(t["gid"]).values
        for nm, _, _ in TEAM_ST:
            t[nm] = zz[f"{nm}_{side}"].reindex(t["gid"]).values
        for c in GAME_ST:
            t[c] = zz[c].reindex(t["gid"]).values
            t[c + "_raw"] = zz[c + "_raw"].reindex(t["gid"]).values
        rows.append(t)
    P = pd.concat(rows, ignore_index=True).dropna(subset=COLS)
    P["hold"] = P["date_"] >= SPLIT_DATE
    print(f"\n  assignment panel: {len(P):,} referee x game x team rows "
          f"({P['gid'].nunique():,} games)")

    def tabulate(mask, lab):
        sub = P[mask]
        m = sub[COLS].mean()
        return pd.DataFrame({"Variable": COLS, f"{lab} mean": m.values,
                             f"{lab} SMD": m.values})

    for scheme in ("grp_frozen", "grp_live"):
        hi = (P[scheme] == "HIGH").values
        lo = (P[scheme] == "LOW").values
        print("\n" + "=" * 100)
        print(f"SCHEME: {scheme}   HIGH rows {int(hi.sum()):,}   "
              f"LOW rows {int(lo.sum()):,}")
        print("=" * 100)
        smH = P.loc[hi, COLS].mean()
        smL = P.loc[lo, COLS].mean()
        raws = {c: P.loc[hi, c + "_raw"].mean() if c in GAME_ST else np.nan
                for c in COLS}
        T = pd.DataFrame({"Variable": COLS, "HIGH SMD": smH.values,
                          "LOW SMD": smL.values})
        T["absmax"] = np.maximum(T["HIGH SMD"].abs(), T["LOW SMD"].abs())
        T = T.sort_values("absmax", ascending=False)
        print(f"  {'Variable':18}{'HIGH SMD':>11}{'LOW SMD':>11}  magnitude(H)")
        for _, r in T.head(15).iterrows():
            print(f"  {r['Variable']:18}{r['HIGH SMD']:+11.4f}"
                  f"{r['LOW SMD']:+11.4f}  {label(r['HIGH SMD'])}")
        if scheme == "grp_frozen":
            Tf, hif, lof = T, hi, lo

    # ---- development / holdout ----------------------------------------
    print("\n" + "=" * 100)
    print("DEVELOPMENT / HOLDOUT REPLICATION (development-frozen identities)")
    print("=" * 100)
    dv, hd = ~P["hold"].values, P["hold"].values
    print(f"  {'Variable':18}{'H dev':>9}{'H hold':>9}{'same':>6}"
          f"{'L dev':>9}{'L hold':>9}{'same':>6}")
    for v in Tf.head(10)["Variable"]:
        hdv = P.loc[hif & dv, v].mean(); hhd = P.loc[hif & hd, v].mean()
        ldv = P.loc[lof & dv, v].mean(); lhd = P.loc[lof & hd, v].mean()
        print(f"  {v:18}{hdv:+9.4f}{hhd:+9.4f}"
              f"{('Y' if np.sign(hdv)==np.sign(hhd) else 'N'):>6}"
              f"{ldv:+9.4f}{lhd:+9.4f}"
              f"{('Y' if np.sign(ldv)==np.sign(lhd) else 'N'):>6}")

    # ---- permutation ---------------------------------------------------
    print("\n" + "=" * 100)
    print("ASSIGNMENT PERMUTATION — 7-day blocks, referee labels held fixed")
    print("=" * 100)
    uni = r26.rf.universe()
    uni["gid"] = uni["gid"].astype(str).str.strip()
    ok = uni["gid"].isin(set(P["gid"]))
    uni = uni[ok].reset_index(drop=True)
    blk = (uni["yr"].astype(str) + "_"
           + ((uni["date"] - uni.groupby("yr")["date"].transform("min"))
              .dt.days // BLOCK_DAYS).astype(str)).values
    crew = uni[["ref1", "ref2", "ref3"]].values
    blocks = [np.where(blk == b)[0] for b in pd.unique(blk)]
    gidx = pd.Series(np.arange(len(uni)), index=uni["gid"])
    # game-level standardised states, one row per game per side
    Zg = np.zeros((len(uni), 2, len(COLS)))
    for si, side in enumerate(("H", "R")):
        for ci, c in enumerate(COLS):
            src = f"{c}_{side}" if c in [t[0] for t in TEAM_ST] else c
            Zg[:, si, ci] = zz[src].reindex(uni["gid"]).values
    nullmax = np.empty(NPERM)
    nullH = np.empty((NPERM, len(COLS)))
    nullL = np.empty((NPERM, len(COLS)))
    for j in range(NPERM):
        perm = crew.copy()
        for b in blocks:
            if len(b) > 1:
                perm[b] = crew[b][RNG.permutation(len(b))]
        isH = np.isin(perm, list(HIGH)).sum(1)
        isL = np.isin(perm, list(LOW)).sum(1)
        wH = np.repeat(isH, 2).reshape(-1, 2)
        wL = np.repeat(isL, 2).reshape(-1, 2)
        for arr, w in ((nullH, wH), (nullL, wL)):
            num = (Zg * w[:, :, None]).sum((0, 1))
            arr[j] = num / max(w.sum(), 1)
        nullmax[j] = max(np.abs(nullH[j]).max(), np.abs(nullL[j]).max())
    obsmax = max(np.abs(Tf["HIGH SMD"]).max(), np.abs(Tf["LOW SMD"]).max())
    pfw = (1 + (nullmax >= obsmax).sum()) / (NPERM + 1)
    print(f"  observed max |SMD|              {obsmax:.4f}")
    print(f"  null mean max |SMD|             {nullmax.mean():.4f}")
    print(f"  null SD                         {nullmax.std():.4f}")
    print(f"  null 95th percentile            {np.percentile(nullmax,95):.4f}")
    print(f"  FAMILY-WISE empirical p         {pfw:.4f}")
    print(f"\n  per-variable permutation p (top 8 by |SMD|)")
    for _, r in Tf.head(8).iterrows():
        i = COLS.index(r["Variable"])
        ph = (1 + (np.abs(nullH[:, i]) >= abs(r["HIGH SMD"])).sum()) / (NPERM+1)
        pl = (1 + (np.abs(nullL[:, i]) >= abs(r["LOW SMD"])).sum()) / (NPERM+1)
        print(f"    {r['Variable']:18} HIGH SMD {r['HIGH SMD']:+.4f} p={ph:.4f}"
              f"    LOW SMD {r['LOW SMD']:+.4f} p={pl:.4f}")

    # ---- per-referee ---------------------------------------------------
    print("\n" + "=" * 100)
    print("PER-REFEREE TEAM-STATE IMBALANCE (vs contemporaneous league)")
    print("=" * 100)
    show = ["OEFF", "DEFF", "PACE", "FoulDraw", "FoulCommit", "FTA", "TOV",
            "ORB", "TPA"]
    for grp, nm in ((HIGH, "HIGH"), (LOW, "LOW")):
        print(f"\n  {nm}-foul referees")
        print(f"    {'Referee':22}{'effect':>8}{'games':>7}"
              + "".join(f"{c:>11}" for c in show))
        rows2 = []
        for rf_ in sorted(grp):
            g2 = P[P["ref"] == rf_]
            if len(g2) < 100:
                continue
            vals = [g2[c].mean() for c in show]
            rows2.append(vals)
            print(f"    {rf_:22}{g2['eff'].mean():+8.3f}"
                  f"{g2['gid'].nunique():7,}"
                  + "".join(f"{v:+11.3f}" for v in vals))
        R = np.array(rows2)
        print(f"    {'MEDIAN':22}{'':8}{'':7}"
              + "".join(f"{np.median(R[:, i]):+11.3f}" for i in range(len(show))))
        print(f"    {'% same sign as median':22}{'':8}{'':7}"
              + "".join(f"{100*np.mean(np.sign(R[:,i])==np.sign(np.median(R[:,i]))):>10.0f}%"
                        for i in range(len(show))))

    # ---- team identity exposure ---------------------------------------
    print("\n" + "=" * 100)
    print("TEAM EXPOSURE TO HIGH / LOW REFEREES")
    print("=" * 100)
    tg = P.groupby("team").agg(rows=("gid", "size"))
    ex = P.assign(isH=(P["grp_frozen"] == "HIGH").astype(float),
                  isL=(P["grp_frozen"] == "LOW").astype(float)) \
        .groupby("team")[["isH", "isL"]].mean()
    ex = ex.join(tg)
    ex["HIGH %"] = (100 * ex["isH"]).round(2)
    ex["LOW %"] = (100 * ex["isL"]).round(2)
    lgH, lgL = 100 * (P["grp_frozen"] == "HIGH").mean(), \
        100 * (P["grp_frozen"] == "LOW").mean()
    ex = ex.sort_values("HIGH %", ascending=False)
    print(f"  league expected HIGH {lgH:.2f}%   LOW {lgL:.2f}%")
    print(ex[["rows", "HIGH %", "LOW %"]].head(5).to_string())
    print("  ...")
    print(ex[["rows", "HIGH %", "LOW %"]].tail(5).to_string())

    # ---- market environment -------------------------------------------
    print("\n" + "=" * 100)
    print("MARKET ENVIRONMENT (raw units)")
    print("=" * 100)
    print(f"  {'':18}{'HIGH refs':>12}{'League':>12}{'LOW refs':>12}"
          f"{'HIGH SMD':>11}{'LOW SMD':>10}")
    for c, nm in (("open_total", "Opening total"), ("total", "Closing total"),
                  ("abs_spread", "|Closing spread|")):
        print(f"  {nm:18}{P.loc[hif, c+'_raw'].mean():12.3f}"
              f"{P[c+'_raw'].mean():12.3f}{P.loc[lof, c+'_raw'].mean():12.3f}"
              f"{P.loc[hif, c].mean():+11.4f}{P.loc[lof, c].mean():+10.4f}")

    print("\n" + "=" * 100)
    print("SUMMARY")
    print("=" * 100)
    print(f"  Number HIGH refs:            {len(HIGH)}")
    print(f"  Number LOW refs:             {len(LOW)}")
    print(f"  HIGH-ref assignments:        {int(hif.sum()):,} rows "
          f"({P.loc[hif,'gid'].nunique():,} games)")
    print(f"  LOW-ref assignments:         {int(lof.sum()):,} rows "
          f"({P.loc[lof,'gid'].nunique():,} games)")
    print(f"  Largest HIGH-vs-league |SMD|: "
          f"{np.abs(Tf['HIGH SMD']).max():.4f}")
    print(f"  Largest LOW-vs-league |SMD|:  "
          f"{np.abs(Tf['LOW SMD']).max():.4f}")
    print(f"  Family-wise maximum-SMD p:    {pfw:.4f}")


if __name__ == "__main__":
    main()
