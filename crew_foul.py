"""Test 1 — crew-level referee foul aggregation. Pre-registered in
PREREG_crew_foul.md, which freezes the signal and the regimes.

Signal is built from FOUL propensity only. The scoring residual is the economic
target, never an input.

    f_hat(r,t)  = sum of prior demeaned foul rates / (prior count + k)
    CrewFoul_t  = f_hat(r1,t) + f_hat(r2,t) + f_hat(r3,t)
    HIGH = CrewFoul >= develop Q85      LOW = CrewFoul <= develop Q15

Chain: CrewFoul -> fouls -> FTA -> actual total -> closing residual.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import refs
from data_split import SPLIT_DATE

ADVF = "/mnt/c/NBA2/advanced_stats/game_advanced_stats.csv"
LG_WIN, MIN_LG = 500, 200
W, MINP = 20, 10
NPERM = 2000
BE = 110 / 210
RNG = np.random.default_rng(31415)


def build():
    d = refs.build()                      # gid, yr, date, ref1..3, total, e, ...
    adv = pd.read_csv(ADVF, low_memory=False)
    adv["gid"] = adv["GAME-ID"].astype(str).str.strip()
    cols = [f"ADV_PF_PER100_OPP_POSS_{s}" for s in ("H", "R")]
    adv = adv[["gid"] + cols]
    d["gid"] = d["GAME-ID"].astype(str).str.strip()
    assert not (set(adv.columns) & set(d.columns)) - {"gid"}
    n0 = len(d)
    d = d.merge(adv, on="gid", how="left")
    assert len(d) == n0
    n = lambda c: pd.to_numeric(d[c], errors="coerce")
    d["pf_rate"] = d[cols[0]] + d[cols[1]]
    d["fouls"] = n("PF_H") + n("PF_R")
    d["fta"] = n("FTA_H") + n("FTA_R")
    d = d.sort_values("date").reset_index(drop=True)

    # League level: TRAILING window over prior games, running CONTINUOUSLY
    # across seasons. An expanding within-season mean was tried first and is
    # wrong here -- league foul rates fell steadily from 2017 to 2026, so an
    # expanding mean lags the multi-year drift, f_hat accumulates that lag over
    # a referee's career, and frozen thresholds then partition by SEASON rather
    # than by crew. Diagnosed from the feature's own season means before any
    # outcome was examined; see PREREG_crew_foul.md.
    d["lg"] = d["pf_rate"].shift(1).rolling(LG_WIN, min_periods=MIN_LG).mean()
    d["y"] = d["pf_rate"] - d["lg"]

    # mean state for the pricing regression, prior-only
    P = pd.concat([
        pd.DataFrame({"gid": d["gid"], "yr": d["yr"], "date": d["date"],
                      "team": d[f"TEAM_{s}"], "side": s,
                      "pts": pd.to_numeric(d[f"PTS_{s}"], errors="coerce")})
        for s in ("H", "R")]).sort_values("date").reset_index(drop=True)
    P["m_pts"] = P.groupby(["yr", "team"])["pts"].transform(
        lambda s: s.shift(1).rolling(W, min_periods=MINP).mean())
    h = P[P.side == "H"][["gid", "m_pts"]].rename(columns={"m_pts": "mp_h"})
    a = P[P.side == "R"][["gid", "m_pts"]].rename(columns={"m_pts": "mp_a"})
    d = d.merge(h, on="gid").merge(a, on="gid")
    d["mu_state"] = d["mp_h"] + d["mp_a"]
    return d.dropna(subset=["y", "mu_state", "fouls", "fta"]).reset_index(drop=True)


def crew_signal(d, k, ycol="y"):
    """Prior-only shrunk foul effect per official, summed over the crew.

    f_hat = (sum of y over the official's games strictly before this one)
            / (count of those games + k)
    An official with no prior games contributes exactly 0.
    """
    long = pd.concat([
        pd.DataFrame({"row": np.arange(len(d)), "date": d["date"],
                      "ref": d[f"ref{i}"], "y": d[ycol]})
        for i in (1, 2, 3)]).sort_values(["ref", "date"], kind="stable")
    g = long.groupby("ref")["y"]
    prior_sum = g.transform(lambda s: s.shift(1).expanding().sum()).fillna(0.0)
    prior_cnt = g.transform(lambda s: s.shift(1).expanding().count()).fillna(0.0)
    long["f"] = prior_sum / (prior_cnt + k)
    long["npri"] = prior_cnt
    out = long.groupby("row")[["f", "npri"]].agg({"f": "sum", "npri": "min"})
    return out["f"].reindex(np.arange(len(d))).values, \
        out["npri"].reindex(np.arange(len(d))).values


def estimate_k(dev):
    """Method of moments on develop only: k = sigma_e^2 / sigma_ref^2."""
    reflist = sorted(set(dev["ref1"]) | set(dev["ref2"]) | set(dev["ref3"]))
    C = refs.codes(dev, reflist)
    flat = C.ravel()
    cnt = np.bincount(flat[flat >= 0], minlength=len(reflist)).astype(float)
    y = dev["y"].values
    m = refs.ref_means(C, y, len(reflist), cnt)
    keep = cnt >= 100
    w = cnt[keep] / cnt[keep].sum()
    cen = m[keep] - np.sum(w * m[keep])
    se2 = y.var()
    var_ref = max(np.sum(w * cen ** 2) - se2 * np.mean(1.0 / cnt[keep]), 1e-9)
    return se2 / var_ref, np.sqrt(var_ref)


def chain(d, lab, q15, q85):
    hi = d[d["CrewFoul"] >= q85]
    lo = d[d["CrewFoul"] <= q15]
    print(f"\n  {lab}   n={len(d):,}   HIGH n={len(hi):,}   LOW n={len(lo):,}")
    print(f"    {'link':22} {'LOW':>10} {'HIGH':>10} {'HIGH-LOW':>10} "
          f"{'t':>7}")
    rows = []
    for col, name in (("pf_rate", "fouls per 100 poss"), ("fouls", "raw fouls"),
                      ("fta", "free throw attempts"),
                      ("actual", "ACTUAL TOTAL"), ("total", "closing total"),
                      ("e", "CLOSING RESIDUAL")):
        a, b = lo[col].dropna(), hi[col].dropna()
        diff = b.mean() - a.mean()
        se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
        print(f"    {name:22} {a.mean():10.3f} {b.mean():10.3f} "
              f"{diff:10.3f} {diff/se:7.2f}")
        rows.append((name, diff, diff / se))
    for nm, g in (("LOW", lo), ("HIGH", hi)):
        ov = (g["e"] > 0).mean()
        se = 1.96 * np.sqrt(ov * (1 - ov) / len(g))
        print(f"    over rate {nm:5}          {100*ov:9.2f}% +/- {100*se:.2f}"
              f"   (break-even {100*BE:.2f}%)")
    return rows


def main():
    d = build()
    dev = d[d["date"] < SPLIT_DATE]
    print("=" * 96)
    print("TEST 1 — CREW-LEVEL REFEREE FOUL AGGREGATION")
    print("=" * 96)
    print(f"  {len(d):,} games  develop {len(dev):,}  holdout "
          f"{len(d)-len(dev):,}  seasons {sorted(d['yr'].unique())}")
    k, sig = estimate_k(dev)
    print(f"  shrinkage k estimated on DEVELOP only = {k:.1f} games "
          f"(sigma_ref = {sig:.3f} fouls per 100 poss), frozen")
    print(f"  sanity, per-game columns: fouls mean {d['fouls'].mean():.1f} "
          f"sd {d['fouls'].std():.1f}   FTA mean {d['fta'].mean():.1f} "
          f"sd {d['fta'].std():.1f}")

    d["CrewFoul"], d["npri"] = crew_signal(d, k)
    dev = d[d["date"] < SPLIT_DATE]
    hold = d[d["date"] >= SPLIT_DATE]
    q15, q85 = dev["CrewFoul"].quantile([0.15, 0.85])
    print(f"  CrewFoul: mean {d['CrewFoul'].mean():+.3f} "
          f"sd {d['CrewFoul'].std():.3f}   FROZEN develop "
          f"Q15 {q15:+.4f}   Q85 {q85:+.4f}")
    print(f"  min prior games among the three officials: median "
          f"{np.median(d['npri']):.0f}")

    print("\n" + "=" * 96)
    print("THE CHAIN")
    print("=" * 96)
    rd = chain(dev, "DEVELOP", q15, q85)
    rh = chain(hold, "HOLDOUT 2024-25 + 2025-26", q15, q85)
    for y in sorted(hold["yr"].unique()):
        chain(hold[hold["yr"] == y], f"  holdout season {y}", q15, q85)

    print("\n" + "=" * 96)
    print("MARKET TEST — does the book move its total with CrewFoul?")
    print("=" * 96)
    from dispersion_priced import ols
    for lab, x in (("develop", dev), ("holdout", hold), ("all", d)):
        X = np.column_stack([x["mu_state"], x["CrewFoul"]])
        bm, sem, tm = ols(x["total"].values, X)
        bt, set_, tt = ols(x["actual"].values, X)
        gap = bt[2] - bm[2]
        sg = np.sqrt(set_[2] ** 2 + sem[2] ** 2)
        print(f"  {lab:8} n={len(x):5,}   c_market {bm[2]:+7.3f} (t={tm[2]:+5.2f})"
              f"   c_true {bt[2]:+7.3f} (t={tt[2]:+5.2f})"
              f"   gap {gap:+7.3f} (t={gap/sg:+5.2f})")
    print("  c_market 0 with c_true > 0 = book ignores it;  equal = priced;")
    print("  0 < c_market < c_true = partial pricing, the hypothesis under test")

    print("\n" + "=" * 96)
    print("PERMUTATION — within-season crew reshuffle")
    print("=" * 96)
    print(f"  Rebuilds CrewFoul from scratch on each reshuffle, so the whole")
    print(f"  estimation procedure is inside the null.")
    for lab, x in (("develop", dev), ("holdout", hold)):
        obs = (x[x["CrewFoul"] >= q85]["e"].mean()
               - x[x["CrewFoul"] <= q15]["e"].mean())
        idx = x.index.values
        crew = d.loc[idx, ["ref1", "ref2", "ref3"]].values
        yrs = d.loc[idx, "yr"].values
        blocks = [np.where(yrs == u)[0] for u in np.unique(yrs)]
        sub = d.loc[idx].reset_index(drop=True).copy()
        null = np.empty(NPERM)
        for j in range(NPERM):
            perm = crew.copy()
            for b in blocks:
                perm[b] = crew[b][RNG.permutation(len(b))]
            sub["ref1"], sub["ref2"], sub["ref3"] = perm[:, 0], perm[:, 1], perm[:, 2]
            cf, _ = crew_signal(sub, k)
            a = sub.loc[cf >= q85, "e"].mean()
            bb = sub.loc[cf <= q15, "e"].mean()
            null[j] = a - bb
        p = (1 + np.sum(np.abs(null) >= abs(obs))) / (NPERM + 1)
        print(f"  {lab:8} observed HIGH-LOW residual {obs:+.3f}   "
              f"null mean {null.mean():+.3f} sd {null.std():.3f}   "
              f"two-sided p={p:.4f}")


if __name__ == "__main__":
    main()
