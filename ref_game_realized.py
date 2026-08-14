"""HIGH-foul-ref games vs LOW-foul-ref games using REALIZED same-game stats.

Companion to ref_game_contrast.py, which used pregame prior-only states and
found the two groups balanced. This version deliberately uses same-game
outcomes, so it is NOT an assignment test: any difference here mixes
assignment composition with the referee's own causal effect, and the foul and
free-throw channels are already established to be causal.

The pregame table is the control. Read the two together:
    pregame balanced + realized different  ->  referee effect
    pregame different                      ->  assignment composition

Same frozen groups, same game classification, same permutation framework.
Nothing frozen is altered.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import crew_team_diag as ctd
import foul_types
import refs
from data_split import SPLIT_DATE
from ref_game_contrast import frozen_groups, label, smd

ADVF = "/mnt/c/NBA2/advanced_stats/game_advanced_stats.csv"
NPERM = 2000
BLOCK_DAYS = 7
RNG = np.random.default_rng(271828)

# realized per-game team stats: (name, home col, away col)
PAIRS = [("PTS", "PTS_H", "PTS_R"), ("OEFF", "OEFF_H", "OEFF_R"),
         ("DEFF", "DEFF_H", "DEFF_R"), ("Pace", "PACE_H", "PACE_R"),
         ("Fouls", "PF_H", "PF_R"), ("FTA", "FTA_H", "FTA_R"),
         ("FTM", "FT_H", "FT_R"), ("FGA", "FGA_H", "FGA_R"),
         ("FG3A", "3PA_H", "3PA_R"), ("TOV", "TO_H", "TO_R"),
         ("ORB", "OR_H", "OR_R"), ("Poss", "POSS_H", "POSS_R")]
GAME = ["total_points", "total_fouls", "total_FTA", "total_FTM",
        "defensive_fouls", "offensive_fouls", "def_shooting",
        "def_nonshooting", "fta_def", "pf_rate", "ftpct_game"]
CONTROL = ["open_total", "total", "abs_spread"]      # pregame, for contrast


def build():
    g = ctd.build()
    g["gid"] = g["gid"].astype(str).str.strip()
    m = refs.build()
    m["gid"] = m["GAME-ID"].astype(str).str.strip()
    n = lambda c: pd.to_numeric(m[c], errors="coerce")
    cols = {}
    for nm, hc, ac in PAIRS:
        cols[f"{nm}_H"] = n(hc)
        cols[f"{nm}_A"] = n(ac)
    R = pd.DataFrame(cols)
    R["gid"] = m["gid"].values

    adv = pd.read_csv(ADVF, low_memory=False)
    adv["gid"] = adv["GAME-ID"].astype(str).str.strip()
    adv["pf_rate"] = (pd.to_numeric(adv["ADV_PF_PER100_OPP_POSS_H"],
                                    errors="coerce")
                      + pd.to_numeric(adv["ADV_PF_PER100_OPP_POSS_R"],
                                      errors="coerce"))
    R = R.merge(adv[["gid", "pf_rate"]], on="gid", how="left")

    F = foul_types.build()
    F["gid"] = F["gid"].astype(str).str.zfill(10)
    R["gidz"] = R["gid"].str.zfill(10)
    F = F.rename(columns={"gid": "gidz", "n_def_shooting": "def_shooting",
                          "n_def_nonshooting": "def_nonshooting"})
    R = R.merge(F[["gidz", "defensive_fouls", "offensive_fouls",
                   "def_shooting", "def_nonshooting", "fta_def"]],
                on="gidz", how="left")

    # restrict to EXACTLY the games used by the pregame contrast, so the only
    # thing that changes between the two analyses is pregame -> realized stats
    need = [c for _, a, b in
            [("OEFF", "h_f_OEFF", "a_f_OEFF"), ("DEFF", "h_f_DEFF", "a_f_DEFF"),
             ("Pace", "h_f_PACE", "a_f_PACE"), ("FTA", "h_f_FTA", "a_f_FTA"),
             ("FTpct", "h_f_FT%", "a_f_FT%"), ("TPA", "h_f_3PA", "a_f_3PA"),
             ("TOV", "h_f_TOV", "a_f_TOV"), ("ORB", "h_f_ORB", "a_f_ORB"),
             ("FoulDraw", "FD_h", "FD_a"), ("FoulCommit", "FC_h", "FC_a")]
            for c in (a, b)]
    need += ["open_total", "total", "spread", "abs_spread", "LeagueFoulState",
             "pace_sum", "mu_state", "oeff_s", "deff_s", "ftr_s", "tpa_s", "M",
             "pace_s", "implied_minus_open"]
    g = g.dropna(subset=need + ["ref1", "ref2", "ref3"]).copy()
    s = g[["gid", "yr", "date", "ref1", "ref2", "ref3"] + CONTROL].merge(
        R.drop(columns=["gidz"]), on="gid", how="inner")
    for nm, _, _ in PAIRS:
        s[f"{nm}Avg"] = (s[f"{nm}_H"] + s[f"{nm}_A"]) / 2.0
    s["total_points"] = s["PTS_H"] + s["PTS_A"]
    s["total_fouls"] = s["Fouls_H"] + s["Fouls_A"]
    s["total_FTA"] = s["FTA_H"] + s["FTA_A"]
    s["total_FTM"] = s["FTM_H"] + s["FTM_A"]
    s["ftpct_game"] = s["total_FTM"] / s["total_FTA"].replace(0, np.nan)
    return s.drop_duplicates("gid").reset_index(drop=True)


def main():
    s = build()
    HIGH, LOW, q85, q15 = frozen_groups(set(s["gid"]))
    print(f"  frozen development referee Q15 {q15:+.4f}   Q85 {q85:+.4f}")
    print(f"  reproduced {len(HIGH)} HIGH and {len(LOW)} LOW referees")

    COLS = ([f"{n}Avg" for n, _, _ in PAIRS] + GAME + CONTROL
            + [f"{n}_{x}" for n, _, _ in PAIRS for x in ("H", "A")])
    base = [c for c in COLS if c not in
            ("defensive_fouls", "offensive_fouls", "def_shooting",
             "def_nonshooting", "fta_def")]
    s = s.dropna(subset=base).reset_index(drop=True)

    crew = s[["ref1", "ref2", "ref3"]].values
    nH = np.isin(crew, list(HIGH)).sum(1)
    nL = np.isin(crew, list(LOW)).sum(1)
    grp = np.where((nH >= 1) & (nL == 0), "HIGH",
                   np.where((nL >= 1) & (nH == 0), "LOW",
                            np.where((nH >= 1) & (nL >= 1), "MIXED",
                                     "NEUTRAL")))
    print(f"\n  one row per game: {len(s):,} games")
    for k_ in ("HIGH", "LOW", "MIXED", "NEUTRAL"):
        print(f"    {k_:8} games: {int((grp == k_).sum()):5,}")
    ftc = s["defensive_fouls"].notna()
    print(f"  foul-type classification present on {int(ftc.sum()):,} games "
          f"(PBP parquet ends 2024-25)")

    hi, lo = (grp == "HIGH"), (grp == "LOW")
    rows = []
    for c in COLS:
        v = s[c].values
        ok = ~np.isnan(v)
        a, b = v[hi & ok], v[lo & ok]
        p = np.sqrt((a.std(ddof=1) ** 2 + b.std(ddof=1) ** 2) / 2)
        rows.append({"Variable": c, "HIGH mean": a.mean(), "LOW mean": b.mean(),
                     "Diff": a.mean() - b.mean(),
                     "SMD": (a.mean() - b.mean()) / p if p > 0 else 0.0,
                     "n": len(a) + len(b)})
    T = pd.DataFrame(rows)
    T = T.reindex(np.argsort(-np.abs(T["SMD"].values))).reset_index(drop=True)

    print("\n" + "=" * 100)
    print("REALIZED SAME-GAME TEAM STATS — HIGH-ref games vs LOW-ref games")
    print("=" * 100)
    print(f"  {'Variable':20}{'HIGH mean':>12}{'LOW mean':>12}{'Diff':>10}"
          f"{'SMD':>9}  magnitude")
    for _, r in T.iterrows():
        print(f"  {r['Variable']:20}{r['HIGH mean']:12.4f}{r['LOW mean']:12.4f}"
              f"{r['Diff']:10.4f}{r['SMD']:9.4f}  {label(r['SMD'])}")
    T.to_csv("ref_game_realized.csv", index=False)

    print("\n" + "=" * 100)
    print("HOME / AWAY COMPONENTS")
    print("=" * 100)
    md = dict(zip(T["Variable"], zip(T["HIGH mean"], T["LOW mean"])))
    print(f"  {'State':10}{'Home HIGH':>11}{'Home LOW':>11}{'Home d':>9}"
          f"{'Away HIGH':>11}{'Away LOW':>11}{'Away d':>9}")
    for nm, _, _ in PAIRS:
        h1, h2 = md[f"{nm}_H"]
        a1, a2 = md[f"{nm}_A"]
        print(f"  {nm:10}{h1:11.4f}{h2:11.4f}{h1-h2:9.4f}"
              f"{a1:11.4f}{a2:11.4f}{a1-a2:9.4f}")

    print("\n" + "=" * 100)
    print("DEVELOPMENT / HOLDOUT")
    print("=" * 100)
    dv = (s["date"] < SPLIT_DATE).values
    dmap, hmap = {}, {}
    for c in COLS:
        v = s[c].values
        ok = ~np.isnan(v)
        for mask, store in ((dv, dmap), (~dv, hmap)):
            a, b = v[hi & ok & mask], v[lo & ok & mask]
            if len(a) < 30 or len(b) < 30:
                store[c] = np.nan
                continue
            p = np.sqrt((a.std(ddof=1) ** 2 + b.std(ddof=1) ** 2) / 2)
            store[c] = (a.mean() - b.mean()) / p if p > 0 else 0.0
    print(f"  {'Variable':20}{'Dev SMD':>10}{'Holdout SMD':>14}{'Same sign?':>12}")
    for v in T.head(12)["Variable"]:
        a, b = dmap[v], hmap[v]
        same = "-" if np.isnan(b) else ("Y" if np.sign(a) == np.sign(b) else "N")
        print(f"  {v:20}{a:10.4f}{b:14.4f}{same:>12}")

    print("\n" + "=" * 100)
    print("PERMUTATION — 7-day blocks, frozen referee identities")
    print("=" * 100)
    X = s[COLS].values
    okc = ~np.isnan(X)
    blk = (s["yr"].astype(str) + "_"
           + ((s["date"] - s.groupby("yr")["date"].transform("min"))
              .dt.days // BLOCK_DAYS).astype(str)).values
    blocks = [np.where(blk == b)[0] for b in pd.unique(blk)]
    null = np.full((NPERM, len(COLS)), np.nan)
    for j in range(NPERM):
        perm = crew.copy()
        for b in blocks:
            if len(b) > 1:
                perm[b] = crew[b][RNG.permutation(len(b))]
        a_ = np.isin(perm, list(HIGH)).sum(1)
        b_ = np.isin(perm, list(LOW)).sum(1)
        h2 = (a_ >= 1) & (b_ == 0)
        l2 = (b_ >= 1) & (a_ == 0)
        for i in range(len(COLS)):
            m1 = h2 & okc[:, i]
            m2 = l2 & okc[:, i]
            if m1.sum() < 30 or m2.sum() < 30:
                continue
            aa, bb = X[m1, i], X[m2, i]
            p = np.sqrt((aa.std(ddof=1) ** 2 + bb.std(ddof=1) ** 2) / 2)
            null[j, i] = (aa.mean() - bb.mean()) / p if p > 0 else 0.0
    fw = np.nanmax(np.abs(null), axis=1)
    mobs = np.abs(T["SMD"]).max()
    print(f"  observed max |SMD|            {mobs:.4f} "
          f"({T['Variable'].iloc[0]})")
    print(f"  permutation mean max |SMD|    {np.nanmean(fw):.4f}")
    print(f"  permutation 95th percentile   {np.nanpercentile(fw, 95):.4f}")
    print(f"  FAMILY-WISE p                 "
          f"{(1 + np.nansum(fw >= mobs)) / (np.sum(~np.isnan(fw)) + 1):.4f}")
    ci = {c: i for i, c in enumerate(COLS)}
    print(f"\n  individual permutation p-values (top 12 by |SMD|)")
    for _, r in T.head(12).iterrows():
        i = ci[r["Variable"]]
        col = null[:, i]
        col = col[~np.isnan(col)]
        p = (1 + (np.abs(col) >= abs(r["SMD"])).sum()) / (len(col) + 1)
        print(f"    {r['Variable']:20} SMD {r['SMD']:+.4f}   perm p {p:.4f}")

    print("\n" + "=" * 100)
    print("SUMMARY")
    print("=" * 100)
    print(f"  HIGH-ref games:                {int(hi.sum()):,}")
    print(f"  LOW-ref games:                 {int(lo.sum()):,}")
    print(f"  MIXED games excluded:          {int((grp=='MIXED').sum()):,}")
    print(f"  Largest |SMD|:                 {mobs:.4f} "
          f"({T['Variable'].iloc[0]})")
    print(f"  Variables |SMD| > 0.10:        "
          f"{int((np.abs(T['SMD']) > 0.10).sum())} of {len(T)}")
    print(f"  Variables |SMD| > 0.20:        "
          f"{int((np.abs(T['SMD']) > 0.20).sum())} of {len(T)}")


if __name__ == "__main__":
    main()
