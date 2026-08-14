"""HIGH-foul-ref games vs LOW-foul-ref games: direct team-state contrast.

One row per game. Diagnostic only; nothing frozen is altered and no same-game
outcome is used.

    HIGH game    >=1 HIGH ref and no LOW ref
    LOW  game    >=1 LOW  ref and no HIGH ref
    MIXED        both present            -> excluded from the primary contrast
    NEUTRAL      neither present         -> excluded

Referee identities are the development-frozen 9 HIGH / 9 LOW from
ref_assignment_balance.py. They are reproduced here and asserted, not redefined.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import crew_team_diag as ctd
import ref_2526_diag as r26
from data_split import SPLIT_DATE

NPERM = 2000
BLOCK_DAYS = 7
RNG = np.random.default_rng(271828)

PAIRS = [("OEFF", "h_f_OEFF", "a_f_OEFF"), ("DEFF", "h_f_DEFF", "a_f_DEFF"),
         ("Pace", "h_f_PACE", "a_f_PACE"), ("FTA", "h_f_FTA", "a_f_FTA"),
         ("FTpct", "h_f_FT%", "a_f_FT%"), ("TPA", "h_f_3PA", "a_f_3PA"),
         ("TOV", "h_f_TOV", "a_f_TOV"), ("ORB", "h_f_ORB", "a_f_ORB"),
         ("FoulDraw", "FD_h", "FD_a"), ("FoulCommit", "FC_h", "FC_a")]
MARKET = ["open_total", "total", "spread", "abs_spread", "LeagueFoulState",
          "pace_sum", "mu_state", "oeff_s", "deff_s", "ftr_s", "tpa_s", "M",
          "pace_s", "implied_minus_open"]


def label(v):
    a = abs(v)
    return ("trivial" if a < 0.10 else "small" if a < 0.20
            else "potentially meaningful" if a < 0.30 else "SUBSTANTIAL")


def frozen_groups(keep_gids):
    """Reproduce the development-frozen HIGH/LOW referee identities exactly as
    in ref_assignment_balance.py, which restricted to the control sample
    BEFORE computing referee-level means."""
    d, long, k = r26.internals()
    d["gid"] = d["gid"].astype(str).str.strip()
    d["row"] = np.arange(len(d))
    long = long.merge(d[["row", "gid", "date"]].rename(
        columns={"date": "gdate"}), on="row", how="inner")
    long["date_"] = pd.to_datetime(long["gdate"])
    L = long.dropna(subset=["eff"])
    L = L[L["gid"].isin(keep_gids)]
    dev = L[L["date_"] < SPLIT_DATE]
    m = dev.groupby("ref")["eff"].mean()
    c = dev.groupby("ref")["eff"].size()
    m = m[c >= 100]
    q85, q15 = m.quantile(0.85), m.quantile(0.15)
    return set(m[m >= q85].index), set(m[m <= q15].index), q85, q15


def smd(a, b):
    ma, mb = a.mean(0), b.mean(0)
    p = np.sqrt((a.std(0, ddof=1) ** 2 + b.std(0, ddof=1) ** 2) / 2)
    return ma, mb, ma - mb, np.divide(ma - mb, p, out=np.zeros_like(ma),
                                      where=p > 0)


def main():
    g = ctd.build()
    g["gid"] = g["gid"].astype(str).str.strip()
    need = [c for _, a, b in PAIRS for c in (a, b)] + MARKET
    s = g.dropna(subset=need + ["ref1", "ref2", "ref3"]).copy()
    s = s.drop_duplicates("gid").reset_index(drop=True)

    HIGH, LOW, q85, q15 = frozen_groups(set(s["gid"]))
    print(f"  frozen development referee Q15 {q15:+.4f}   Q85 {q85:+.4f}")
    assert len(HIGH) == 9 and len(LOW) == 9, (len(HIGH), len(LOW))
    print(f"  reproduced {len(HIGH)} HIGH and {len(LOW)} LOW referees")
    print(f"    HIGH: {', '.join(sorted(HIGH))}")
    print(f"    LOW : {', '.join(sorted(LOW))}")

    for nm, hc, ac in PAIRS:
        s[f"{nm}_H"] = s[hc]
        s[f"{nm}_A"] = s[ac]
        s[f"{nm}Avg"] = (s[hc] + s[ac]) / 2.0
    COLS = ([f"{n}Avg" for n, _, _ in PAIRS] + MARKET
            + [f"{n}_{x}" for n, _, _ in PAIRS for x in ("H", "A")])

    crew = s[["ref1", "ref2", "ref3"]].values
    nH = np.isin(crew, list(HIGH)).sum(1)
    nL = np.isin(crew, list(LOW)).sum(1)
    grp = np.where((nH >= 1) & (nL == 0), "HIGH",
                   np.where((nL >= 1) & (nH == 0), "LOW",
                            np.where((nH >= 1) & (nL >= 1), "MIXED",
                                     "NEUTRAL")))
    s["grp"] = grp
    print(f"\n  one row per game: {len(s):,} games")
    for k_ in ("HIGH", "LOW", "MIXED", "NEUTRAL"):
        print(f"    {k_:8} games: {int((grp == k_).sum()):5,}")

    X = s[COLS].values
    hi, lo = (grp == "HIGH"), (grp == "LOW")
    ma, mb, diff, sm = smd(X[hi], X[lo])
    T = pd.DataFrame({"Variable": COLS, "HIGH mean": ma, "LOW mean": mb,
                      "Diff": diff, "SMD": sm})
    T = T.reindex(np.argsort(-np.abs(T["SMD"].values))).reset_index(drop=True)

    print("\n" + "=" * 96)
    print("PRIMARY — HIGH-ref games vs LOW-ref games, sorted by |SMD|")
    print("=" * 96)
    print(f"  {'Variable':20}{'HIGH mean':>12}{'LOW mean':>12}{'Diff':>10}"
          f"{'SMD':>9}  magnitude")
    for _, r in T.iterrows():
        print(f"  {r['Variable']:20}{r['HIGH mean']:12.4f}{r['LOW mean']:12.4f}"
              f"{r['Diff']:10.4f}{r['SMD']:9.4f}  {label(r['SMD'])}")
    T.to_csv("ref_game_contrast.csv", index=False)

    print("\n" + "=" * 96)
    print("HOME / AWAY COMPONENTS")
    print("=" * 96)
    print(f"  {'State':12}{'Home HIGH':>11}{'Home LOW':>11}{'Home d':>9}"
          f"{'Away HIGH':>11}{'Away LOW':>11}{'Away d':>9}")
    md = dict(zip(T["Variable"], zip(T["HIGH mean"], T["LOW mean"])))
    for nm, _, _ in PAIRS:
        h1, h2 = md[f"{nm}_H"]
        a1, a2 = md[f"{nm}_A"]
        print(f"  {nm:12}{h1:11.4f}{h2:11.4f}{h1-h2:9.4f}"
              f"{a1:11.4f}{a2:11.4f}{a1-a2:9.4f}")

    print("\n" + "=" * 96)
    print("DEVELOPMENT / HOLDOUT")
    print("=" * 96)
    dv = (s["date"] < SPLIT_DATE).values
    _, _, _, sd_ = smd(X[hi & dv], X[lo & dv])
    _, _, _, sh = smd(X[hi & ~dv], X[lo & ~dv])
    print(f"  development HIGH {int((hi & dv).sum()):,} / LOW "
          f"{int((lo & dv).sum()):,}    holdout HIGH "
          f"{int((hi & ~dv).sum()):,} / LOW {int((lo & ~dv).sum()):,}")
    dmap, hmap = dict(zip(COLS, sd_)), dict(zip(COLS, sh))
    print(f"  {'Variable':20}{'Dev SMD':>10}{'Holdout SMD':>14}{'Same sign?':>12}")
    for v in T.head(12)["Variable"]:
        a, b = dmap[v], hmap[v]
        print(f"  {v:20}{a:10.4f}{b:14.4f}"
              f"{('Y' if np.sign(a) == np.sign(b) else 'N'):>12}")

    print("\n" + "=" * 96)
    print("PERMUTATION — 7-day blocks, frozen referee identities")
    print("=" * 96)
    blk = (s["yr"].astype(str) + "_"
           + ((s["date"] - s.groupby("yr")["date"].transform("min"))
              .dt.days // BLOCK_DAYS).astype(str)).values
    blocks = [np.where(blk == b)[0] for b in pd.unique(blk)]
    null = np.empty((NPERM, len(COLS)))
    for j in range(NPERM):
        perm = crew.copy()
        for b in blocks:
            if len(b) > 1:
                perm[b] = crew[b][RNG.permutation(len(b))]
        a_ = np.isin(perm, list(HIGH)).sum(1)
        b_ = np.isin(perm, list(LOW)).sum(1)
        h2 = (a_ >= 1) & (b_ == 0)
        l2 = (b_ >= 1) & (a_ == 0)
        if h2.sum() < 30 or l2.sum() < 30:
            null[j] = np.nan
            continue
        null[j] = smd(X[h2], X[l2])[3]
    ok = ~np.isnan(null).any(1)
    null = null[ok]
    fw = np.abs(null).max(1)
    mobs = np.abs(T["SMD"]).max()
    print(f"  {len(null):,} usable permutations")
    print(f"  observed max |SMD|            {mobs:.4f} "
          f"({T['Variable'].iloc[0]})")
    print(f"  permutation mean max |SMD|    {fw.mean():.4f}")
    print(f"  permutation 95th percentile   {np.percentile(fw, 95):.4f}")
    print(f"  FAMILY-WISE p                 "
          f"{(1 + (fw >= mobs).sum()) / (len(fw) + 1):.4f}")
    ci = {c: i for i, c in enumerate(COLS)}
    print(f"\n  individual permutation p-values (top 10 by |SMD|)")
    for _, r in T.head(10).iterrows():
        i = ci[r["Variable"]]
        p = (1 + (np.abs(null[:, i]) >= abs(r["SMD"])).sum()) / (len(null) + 1)
        print(f"    {r['Variable']:20} SMD {r['SMD']:+.4f}   perm p {p:.4f}")

    print("\n" + "=" * 96)
    print("FOUL-RELEVANT STATES (same thresholds, no extra search)")
    print("=" * 96)
    for v in ("FoulDrawAvg", "FoulCommitAvg", "FTAAvg", "FTpctAvg",
              "OEFFAvg", "DEFFAvg", "PaceAvg"):
        r = T[T["Variable"] == v].iloc[0]
        i = ci[v]
        p = (1 + (np.abs(null[:, i]) >= abs(r["SMD"])).sum()) / (len(null) + 1)
        print(f"  {v:16} HIGH {r['HIGH mean']:9.4f}  LOW {r['LOW mean']:9.4f}"
              f"  diff {r['Diff']:+8.4f}  SMD {r['SMD']:+.4f}  p {p:.4f}  "
              f"{label(r['SMD'])}")

    print("\n" + "=" * 96)
    print("SUMMARY")
    print("=" * 96)
    print(f"  HIGH-ref games:                {int(hi.sum()):,}")
    print(f"  LOW-ref games:                 {int(lo.sum()):,}")
    print(f"  MIXED games excluded:          {int((grp=='MIXED').sum()):,}")
    print(f"  NEUTRAL games excluded:        {int((grp=='NEUTRAL').sum()):,}")
    print(f"  Largest |SMD|:                 {mobs:.4f} "
          f"({T['Variable'].iloc[0]})")
    print(f"  Family-wise permutation p:     "
          f"{(1 + (fw >= mobs).sum()) / (len(fw) + 1):.4f}")
    print(f"  Variables |SMD| > 0.10:        "
          f"{int((np.abs(T['SMD']) > 0.10).sum())} of {len(T)}")
    print(f"  Variables |SMD| > 0.20:        "
          f"{int((np.abs(T['SMD']) > 0.20).sum())} of {len(T)}")
    dv_top = max(dmap, key=lambda c: abs(dmap[c]))
    print(f"  Development largest SMD:       {dmap[dv_top]:+.4f} ({dv_top})")
    print(f"  Holdout SMD, same variable:    {hmap[dv_top]:+.4f}")


if __name__ == "__main__":
    main()
