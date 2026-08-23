"""MINER PASS 4 — the AGENT'S feature space, swept with the miner's machinery.

Passes 1-3 covered schedule/referee/market/team-form. The research agent works
a different space: lineup composition and rotation (16 stint-derived roots),
shot quality, rebounding, ball-security and coaching-intervention metrics.
It proposes mechanism-first hypotheses and has produced 0 validated candidates
in 371 attempts; it carries no multiplicity accounting.

This sweeps that space the way passes 1-3 swept theirs: enumerate cells, apply
the SAME frozen selection rules, and price the result against 200 phantom
books built by the identical pipeline on scrambled outcomes.

All lineup/advanced metrics are REALIZED in-game quantities, so every one is
used strictly prior-only: shift(1).rolling(20, min 10) within (season, team),
matching the agent's own 'historical HHI' construction.
"""
import itertools
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import opening_line_error_decomposition as OLE

RNG = np.random.default_rng(20260823); NREP = 200; DEVMAX = 2023; CAP = 4000
W, MINP = 20, 10

LINEUP = ["ROTATION_CONCENTRATION_HHI", "EFFECTIVE_LINEUP_COUNT", "UNIQUE_LINEUPS",
          "TOP_LINEUP_SHARE", "TOP2_LINEUP_SHARE", "STARTER5_SHARE",
          "AVG_STARTERS_ON_COURT", "MIXED_STARTER_SHARE", "BENCH_HEAVY_SHARE",
          "ALL_BENCH_SHARE", "FOUR_PLUS_STARTERS_SHARE", "SUBSTITUTIONS",
          "SUBS_PER48", "STINT_COUNT", "AVG_STINT_SECONDS", "MEDIAN_STINT_SECONDS"]
ADVR = ["ADV_OREB_PCT", "ADV_DREB_PCT", "ADV_EFG", "ADV_TOV_PER100",
        "ADV_STL_PER100_OPP_POSS", "ADV_BLK_PER100_OPP_2PA", "ADV_3PA_RATE",
        "ADV_FTA_PER100", "ADV_ASSISTED_FGM_SHARE", "EV_TIMEOUTS",
        "EV_LIVE_BALL_TOV_SHARE", "PBP_OREB_POSS_SHARE", "PBP_H1_POSS_SHARE",
        "PBP_POS_DUR_SD", "PBP_EARLY8_SHARE", "PBP_ZERO_PTS_SHARE",
        "PBP_3PLUS_PTS_SHARE", "PBP_START_STEAL_SHARE"]


def prior_only(g, wide, roots, hcol, acol):
    """Team-level prior-only rolling means -> per-game home/away columns."""
    rows = []
    for side, teamcol in (("h", "home"), ("a", "away")):
        pre = hcol if side == "h" else acol
        d = {"gid": g.gid, "season": g.season, "date": g.date, "team": g[teamcol]}
        for r in roots:
            col = f"{pre}{r}" if pre.endswith("_") else f"{r}_{pre}"
            d[r] = g.gid.map(wide[col]) if col in wide else np.nan
        rows.append(pd.DataFrame(d))
    P = pd.concat(rows).sort_values("date")
    grp = P.groupby(["season", "team"])
    out = {}
    for r in roots:
        P["f"] = grp[r].transform(
            lambda s: s.shift(1).rolling(W, min_periods=MINP).mean())
        piv = P.pivot_table(index="gid", values="f",
                            columns=P.groupby("gid").cumcount(), aggfunc="first")
        out[r] = piv
    return P, out


def main():
    g = OLE.load(); g["gid"] = g.gid.astype(str).str.strip()
    g = g.dropna(subset=["ot_close", "total"]).sort_values("date").reset_index(drop=True)
    g["e"] = g.total - g.ot_close

    LW = pd.read_csv("/mnt/c/NBA2/advanced_stats/game_lineup_advanced_wide.csv",
                     low_memory=False)
    LW["gid"] = LW["GAMEID"].astype(str).str.strip().str.lstrip("0")
    AD = pd.read_csv("/mnt/c/NBA2/advanced_stats/game_advanced_stats.csv",
                     low_memory=False)
    AD["gid"] = AD["GAME-ID"].astype(str).str.strip()

    # team-game panel of BOTH sources, prior-only
    recs = []
    for side, teamcol, lp, ap in (("h", "home", "H_", "_H"), ("a", "away", "R_", "_R")):
        d = {"gid": g.gid, "season": g.season, "date": g.date, "team": g[teamcol],
             "side": side}
        lw = LW.set_index("gid")
        ad = AD.set_index("gid")
        for r in LINEUP:
            c = lp + r
            d[r] = g.gid.map(lw[c]) if c in lw.columns else np.nan
        for r in ADVR:
            c = r + ap
            d[r] = g.gid.map(ad[c]) if c in ad.columns else np.nan
        recs.append(pd.DataFrame(d))
    P = pd.concat(recs).sort_values("date").reset_index(drop=True)
    roots = [r for r in LINEUP + ADVR if P[r].notna().mean() > 0.5]
    print(f"  roots with >50% coverage: {len(roots)} of {len(LINEUP)+len(ADVR)}")
    grp = P.groupby(["season", "team"])
    for r in roots:
        P["f_" + r] = pd.to_numeric(grp[r].transform(
            lambda s: s.shift(1).rolling(W, min_periods=MINP).mean()), errors="coerce")
    H = P[P.side == "h"].set_index("gid")[["f_" + r for r in roots]]
    A = P[P.side == "a"].set_index("gid")[["f_" + r for r in roots]]
    for r in roots:
        g["h_" + r] = g.gid.map(H["f_" + r])
        g["a_" + r] = g.gid.map(A["f_" + r])
        g["sum_" + r] = g["h_" + r] + g["a_" + r]
        g["dif_" + r] = (g["h_" + r] - g["a_" + r]).abs()

    # ---- conditions: median splits + tails on the SUM and |DIFF| ------------
    B = {}
    for r in roots:
        s, d_ = g["sum_" + r], g["dif_" + r]
        if s.notna().sum() < 2000:
            continue
        B[f"{r}_sum_hi"] = s >= s.median()
        B[f"{r}_sum_lo"] = s < s.median()
        B[f"{r}_sum_top20"] = s >= s.quantile(0.80)
        B[f"{r}_sum_bot20"] = s <= s.quantile(0.20)
        B[f"{r}_gap_hi"] = d_ >= d_.median()
    # schedule/referee anchors so cross-family pairs are reachable
    last = g.groupby("season")["date"].transform("max")
    g["frac"] = g.groupby("season")["date"].rank(pct=True)
    L2 = pd.concat([g[["gid","season","date","home"]].rename(columns={"home":"team"}),
                    g[["gid","season","date","away"]].rename(columns={"away":"team"})]).sort_values(["season","team","date"])
    L2["gap"] = L2.groupby(["season","team"])["date"].diff().dt.days
    d6=[]
    for _,x in L2.groupby(["season","team"]):
        dd=x.date.values
        d6+=[int(((dd[i]-dd[max(0,i-5):i])<=np.timedelta64(5,"D")).sum()>=3) for i in range(len(dd))]
    L2["c"]=d6
    g["cong"] = g.gid.map(L2.groupby("gid")["c"].max())
    g["b2b"] = g.gid.map(L2.groupby("gid")["gap"].min()) == 1
    rs = pd.read_csv("/mnt/c/NBA2/referee_game_states.csv"); rs["gid"]=rs["GAME-ID"].astype(str).str.strip()
    g["cs"] = g.gid.map(rs.set_index("gid")["CrewShock"])
    B["late_season"] = g.frac >= 0.8
    B["early_season"] = g.frac <= 0.2
    B["cong_4in6"] = g.cong == 1
    B["b2b_either"] = g.b2b
    B["cs_hi"] = g.cs >= g.cs.quantile(0.9)
    B["lvl_hi"] = g.ot_close >= g.ot_close.median()
    B["lvl_lo"] = g.ot_close < g.ot_close.median()

    names = list(B)
    M = np.column_stack([B[n].fillna(False).values.astype(bool) for n in names])
    dev = (g.season <= DEVMAX).values; hold = (g.season >= 2024).values
    seas = g.season.values; e = g.e.values; nonpush = e != 0; devnp = dev & nonpush
    cells = [(i,) for i in range(len(names))]
    for i, j in itertools.combinations(range(len(names)), 2):
        if (M[:, i] & M[:, j] & devnp).sum() >= 600:
            cells.append((i, j))
    npairs = len(cells) - len(names)
    for i, j in [c for c in cells if len(c) == 2]:
        if len(cells) >= CAP: break
        for k in range(j + 1, len(names)):
            if len(cells) >= CAP: break
            if (M[:, i] & M[:, j] & M[:, k] & devnp).sum() >= 600:
                cells.append((i, j, k))
    CMb = np.column_stack([np.logical_and.reduce([M[:, i] for i in c]) for c in cells])
    CM = CMb.astype(np.float32)
    labels = [" & ".join(names[i] for i in c) for c in cells]
    print(f"  cells: {len(cells):,} (singles {len(names)}, pairs {npairs:,}, "
          f"triples {len(cells)-len(names)-npairs:,})   games {len(g):,}")

    dseasons = np.unique(seas[dev])
    NS = np.stack([((dev & (seas == s) & nonpush).astype(np.float32) @ CM) for s in dseasons])
    covered = NS >= 30; navail = covered.sum(0)
    NDEV = devnp.astype(np.float32) @ CM

    def scan(evec):
        out = {}
        for side in ("O", "U"):
            w = ((evec > 0) if side == "O" else (evec < 0)) & nonpush
            wins = (w & dev).astype(np.float32) @ CM
            wr = np.divide(wins, NDEV, out=np.zeros_like(wins), where=NDEV > 0)
            stab = np.zeros(len(cells))
            for si, s in enumerate(dseasons):
                ws = (w & dev & (seas == s)).astype(np.float32) @ CM
                fr = np.divide(ws, NS[si], out=np.zeros(len(cells)), where=NS[si] > 0)
                stab += (fr > 0.5) & covered[si]
            out[side] = (wr, stab)
        return out

    def select(sc):
        picks = []
        for side in ("O", "U"):
            wr, stab = sc[side]
            ok = (wr >= 0.535) & (NDEV >= 600) & (navail >= 4) & (stab >= navail - 1)
            for k in np.where(ok)[0]: picks.append((wr[k], k, side))
        picks.sort(reverse=True); return picks[:15]

    def hold_eval(picks, evec):
        Wn = Nn = 0
        for wr, k, side in picks:
            w = ((evec > 0) if side == "O" else (evec < 0)) & nonpush
            Wn += int((CMb[:, k] & w & hold).sum()); Nn += int((CMb[:, k] & nonpush & hold).sum())
        return (Wn / Nn if Nn else np.nan), Nn

    sc = scan(e); book = select(sc)
    nq = sum(int(((sc[s][0] >= 0.535) & (NDEV >= 600) & (navail >= 4)
                  & (sc[s][1] >= navail - 1)).sum()) for s in ("O", "U"))
    print(f"\n  FROZEN BOOK — top {len(book)} of {nq} qualifying")
    ov = (e > 0) & nonpush; un = (e < 0) & nonpush
    for wr, k, side in book:
        w = ov if side == "O" else un
        hw = int((CMb[:, k] & w & hold).sum()); hn = int((CMb[:, k] & nonpush & hold).sum())
        print(f"  {labels[k][:58]:58}{side:>3}{int(NDEV[k]):>6,}{100*wr:>7.2f}%"
              f"{hn:>6,}{100*hw/hn if hn else 0:>7.2f}%")
    wrH, nH = hold_eval(book, e)
    gm = np.zeros(len(g), bool); gu = np.zeros(len(g), bool)
    for wr, k, side in book:
        (gm if side == "O" else gu)[:] |= CMb[:, k]
    dW = int((gm & ov & hold).sum()) + int((gu & un & hold).sum())
    dN = int((gm & nonpush & hold).sum()) + int((gu & nonpush & hold).sum())
    print(f"  PORTFOLIO holdout {100*wrH:.2f}% on {nH:,} seat-bets   "
          f"deduped {100*dW/dN if dN else 0:.2f}% on {dN:,} games")

    print(f"\n  FDR — {NREP} phantom pipelines")
    res = []; qc = []
    for r in range(NREP):
        ep = e.copy()
        for s in dseasons:
            ix = np.where(dev & (seas == s))[0]; ep[ix] = e[ix][RNG.permutation(len(ix))]
        scp = scan(ep); bp = select(scp)
        qc.append(sum(int(((scp[s][0] >= 0.535) & (NDEV >= 600) & (navail >= 4)
                           & (scp[s][1] >= navail - 1)).sum()) for s in ("O", "U")))
        if bp:
            w, _ = hold_eval(bp, e); res.append(w)
    res = np.array([x for x in res if np.isfinite(x)])
    print(f"  phantom qualifying: mean {np.mean(qc):.1f}  p95 {np.percentile(qc,95):.0f}   (real {nq})")
    if len(res):
        print(f"  phantom books {len(res)}/{NREP}: holdout mean {100*res.mean():.2f}"
              f"  p95 {100*np.percentile(res,95):.2f}   real {100*wrH:.2f}"
              f" -> {100*(res<wrH).mean():.0f}th pctile")


if __name__ == "__main__":
    main()
