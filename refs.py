"""Referee dummies: do officials differ in game scoring, and is it priced?

Three officials per game. The vendor changed layout mid-2022, so the crew is
assembled from whichever era's columns are populated:

    2017-2022   MAIN REF_R      CREW_R                 CREW_H
    2022-2026   CREW CHIEF_R    REFEREE&UMPIRE_R       REFEREE&UMPIRE_H

The _H/_R suffix is a column-splitting artifact, not home/away.

Stage 1  does the referee predict RAW scoring (season-demeaned points, and the
         foul-call mechanism: combined FTA)?
Stage 2  does the referee predict the CLOSING-TOTAL RESIDUAL?

Knowability: the NBA publishes crew assignments the morning of the game, so
unlike most features in this repo the close genuinely CAN contain this. A null
at Stage 2 with a live Stage 1 is the efficient outcome, not a measurement
failure.

Everything is permutation-tested by reshuffling whole crews across games within
season, which preserves crew co-assignment structure, ref workloads and the
seasonal scoring trend. Out-of-sample is walk-forward: ref effects fitted on
prior seasons only, scored on the next season.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

from sklearn.linear_model import RidgeCV

MIN_GAMES = 100        # for the descriptive leaderboard
NPERM = 2000
RNG = np.random.default_rng(20260813)
RU_H, RU_R = "REFEREE\n&\nUMPIRE_H", "REFEREE\n&\nUMPIRE_R"


def build():
    from prepare_data import CSV, season_label
    raw = pd.read_csv(CSV, low_memory=False)
    raw["lbl"] = season_label(raw).astype(str)
    d = raw[raw["lbl"].str.contains("Regular Season", na=False)].copy()
    n = lambda c: pd.to_numeric(d[c], errors="coerce")
    d["date"] = pd.to_datetime(d["DATE"], errors="coerce")
    d["yr"] = d["lbl"].str.extract(r"(\d{4})")[0].astype(int)
    d["total"] = n("CLOSING TOTAL_H")
    d["open"] = n("OPENING TOTAL_H")
    d["actual"] = d["PTS_H"] + d["PTS_R"]
    d["fta"] = n("TEAM_FTA_H") + n("TEAM_FTA_R")

    # assemble the three officials from whichever era's columns are live
    d["ref1"] = d["MAIN REF_R"].fillna(d["CREW CHIEF_R"])
    d["ref2"] = d["CREW_R"].fillna(d[RU_R])
    d["ref3"] = d["CREW_H"].fillna(d[RU_H])
    for c in ("ref1", "ref2", "ref3"):
        d[c] = d[c].astype(str).str.strip().str.replace(r"\s+", " ", regex=True)
        d.loc[d[c].isin(["nan", ""]), c] = np.nan

    d = d.dropna(subset=["total", "actual", "date", "ref1", "ref2", "ref3"])
    d = d[d["total"].between(150, 300)].sort_values("date").reset_index(drop=True)
    d["e"] = d["actual"] - d["total"]
    # season-demean the raw targets so Stage 1 is not just the scoring trend
    for src, tgt in (("actual", "pts_dm"), ("fta", "fta_dm")):
        d[tgt] = d[src] - d.groupby("yr")[src].transform("mean")
    return d


def codes(d, refs):
    """(n, 3) integer ref codes; -1 for an official not in `refs`."""
    idx = {r: i for i, r in enumerate(refs)}
    return np.column_stack([d[c].map(idx).fillna(-1).astype(int).values
                            for c in ("ref1", "ref2", "ref3")])


def incidence(d, refs):
    C = codes(d, refs)
    R = np.zeros((len(d), len(refs)))
    rows = np.repeat(np.arange(len(d)), 3)
    flat = C.ravel()
    ok = flat >= 0
    R[rows[ok], flat[ok]] = 1.0
    return R


def ref_means(C, y, nref, cnt):
    flat, rep = C.ravel(), np.repeat(y, 3)
    ok = flat >= 0
    s = np.bincount(flat[ok], weights=rep[ok], minlength=nref)
    return np.divide(s, cnt, out=np.zeros_like(s), where=cnt > 0)


def perm_test(d, y, refs, label):
    """Statistic: workload-weighted SD of ref mean outcomes.

    Null: crews are exchangeable across games within season. Reshuffling whole
    crew-triples across games is equivalent to reshuffling the outcomes across
    games, so the incidence structure is held fixed and y is permuted -- which
    preserves who works with whom, every ref's workload, and the season trend.
    """
    C = codes(d, refs)
    flat = C.ravel()
    cnt = np.bincount(flat[flat >= 0], minlength=len(refs)).astype(float)
    obs_m = ref_means(C, y, len(refs), cnt)
    keep = cnt >= MIN_GAMES
    w = cnt[keep] / cnt[keep].sum()
    cen0 = obs_m[keep] - np.sum(w * obs_m[keep])
    obs = np.sqrt(np.sum(w * cen0 ** 2))
    obs_max = np.max(np.abs(cen0))

    blocks = [np.where(d["yr"].values == u)[0] for u in d["yr"].unique()]
    null, null_max = np.empty(NPERM), np.empty(NPERM)
    for k in range(NPERM):
        yp = y.copy()
        for b in blocks:
            yp[b] = y[b][RNG.permutation(len(b))]
        m = ref_means(C, yp, len(refs), cnt)
        cen = m[keep] - np.sum(w * m[keep])
        null[k] = np.sqrt(np.sum(w * cen ** 2))
        null_max[k] = np.max(np.abs(cen))
    p = (1 + np.sum(null >= obs)) / (NPERM + 1)
    pm = (1 + np.sum(null_max >= obs_max)) / (NPERM + 1)
    print(f"    {label:28} SD {obs:.3f}  null {null.mean():.3f}"
          f"  pct {100*(null < obs).mean():5.1f}  p={p:.4f}   |"
          f"  max dev {obs_max:+.3f}  p_max={pm:.4f}")
    return obs_m, cnt, keep, p, pm


def leaderboard(d, refs, obs_m, cnt, keep, y, label):
    """Descriptive only. Shrunk toward zero by n/(n+k) with k = sigma_e^2 /
    sigma_ref^2 estimated by method of moments."""
    w = cnt[keep] / cnt[keep].sum()
    cen = obs_m[keep] - np.sum(w * obs_m[keep])
    se2 = y.var()
    var_obs = np.sum(w * cen ** 2)
    var_noise = se2 * np.mean(1.0 / cnt[keep])
    var_ref = max(var_obs - var_noise, 1e-9)
    k = se2 / var_ref
    names = np.array(refs)[keep]
    shr = cen * cnt[keep] / (cnt[keep] + k)
    t = cen / np.sqrt(se2 / cnt[keep])
    T = pd.DataFrame({"referee": names, "games": cnt[keep].astype(int),
                      "raw dev": np.round(cen, 2),
                      "shrunk": np.round(shr, 2), "t": np.round(t, 2)})
    T = T.sort_values("raw dev")
    print(f"\n    {label}: implied sigma_ref = {np.sqrt(var_ref):.3f} "
          f"(observed dispersion {np.sqrt(var_obs):.3f}, "
          f"sampling noise {np.sqrt(var_noise):.3f}), shrinkage k = {k:.0f} games")
    print("      lowest 6")
    print(T.head(6).to_string(index=False))
    print("      highest 6")
    print(T.tail(6).iloc[::-1].to_string(index=False))


def walk_forward(d, refs, target):
    d = d.dropna(subset=[target]).copy()
    """Fit ref effects on prior seasons, score the next season. Ridge alpha
    chosen by CV inside the training window only."""
    yrs = sorted(d["yr"].unique())
    out = []
    for i in range(3, len(yrs)):
        tr = d[d["yr"].isin(yrs[:i])]
        te = d[d["yr"] == yrs[i]].copy()
        if len(te) < 100:
            continue
        act = sorted(set(tr["ref1"]) | set(tr["ref2"]) | set(tr["ref3"]))
        Xtr, Xte = incidence(tr, act), incidence(te, act)
        m = RidgeCV(alphas=np.logspace(0, 4, 25)).fit(Xtr, tr[target])
        te["pred"] = m.predict(Xte)
        te["alpha"] = m.alpha_
        out.append(te)
    P = pd.concat(out)
    y, p = P[target].values, P["pred"].values
    r = np.corrcoef(p, y)[0, 1]
    t = r * np.sqrt(len(y) - 2) / np.sqrt(1 - r * r)
    r2 = 1 - ((y - p) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    print(f"    n={len(y):,}  corr {r:+.4f}  t={t:+.2f}  OOS R^2 {100*r2:+.3f}%"
          f"  pred sd {p.std():.3f} (actual sd {y.std():.2f})"
          f"  alphas {sorted(set(P['alpha'].round(0)))}")
    P["q"] = pd.qcut(P["pred"], 5, labels=[1, 2, 3, 4, 5], duplicates="drop")
    rows = []
    for q, s in P.groupby("q", observed=True):
        ov = (s["e"] > 0).mean()
        rows.append({"Q": q, "n": len(s), "pred": round(s["pred"].mean(), 2),
                     f"actual {target}": round(s[target].mean(), 2),
                     "over %": round(100 * ov, 2),
                     "1.96se": round(100 * 1.96 * np.sqrt(ov * (1 - ov) / len(s)), 2)})
    T = pd.DataFrame(rows)
    print(T.to_string(index=False))
    return P


def main():
    d = build()
    refs = sorted(set(d["ref1"]) | set(d["ref2"]) | set(d["ref3"]))
    cnt = pd.concat([d["ref1"], d["ref2"], d["ref3"]]).value_counts()
    print(f"{len(d):,} regular-season games, seasons {sorted(d['yr'].unique())}")
    print(f"{len(refs)} distinct officials, {3*len(d):,} ref-game observations")
    print(f"  games per ref: median {cnt.median():.0f}, "
          f"max {cnt.max()}, {(cnt >= MIN_GAMES).sum()} with >= {MIN_GAMES}")
    print(f"  closing-total residual e: mean {d['e'].mean():+.3f}  "
          f"sd {d['e'].std():.2f}")
    be = 1.08
    print(f"  POWER: to establish a break-even bias ({be} pts) for ONE ref needs "
          f"n = 7.84/({be:.2f}/{d['e'].std():.2f})^2 = "
          f"{7.84/(be/d['e'].std())**2:,.0f} games; busiest ref has {cnt.max()}.")

    print("\n" + "=" * 100)
    print("STAGE 1 — does the referee predict raw scoring?  (season-demeaned)")
    print("=" * 100)
    print(f"  permutation: {NPERM} within-season crew reshuffles, "
          f"refs with >= {MIN_GAMES} games")
    for tgt, lab in (("pts_dm", "total points"), ("fta_dm", "combined FTA")):
        sub = d.dropna(subset=[tgt]).copy()
        if len(sub) < len(d):
            print(f"    [{lab}: {len(sub):,} of {len(d):,} games have the column]")
        y = sub[tgt].values
        m, c, k, p, pm = perm_test(sub, y, refs, lab)
        leaderboard(sub, refs, m, c, k, y, lab)

    print("\n" + "=" * 100)
    print("STAGE 2 — does the referee predict the CLOSING-TOTAL residual?")
    print("=" * 100)
    y = d["e"].values
    m, c, k, p, pm = perm_test(d, y, refs, "closing-total residual")
    leaderboard(d, refs, m, c, k, y, "closing-total residual")
    d["oe"] = d["actual"] - d["open"]
    sub = d.dropna(subset=["oe"])
    perm_test(sub, sub["oe"].values, refs, "OPENING-total residual")

    print("\n" + "=" * 100)
    print("OUT OF SAMPLE — walk-forward, ref effects from prior seasons only")
    print("=" * 100)
    for tgt, lab in (("pts_dm", "raw points (Stage 1 sanity)"),
                     ("fta_dm", "combined FTA (mechanism)"),
                     ("e", "closing-total residual (the tradeable question)")):
        print(f"\n  {lab}")
        walk_forward(d, refs, tgt)


if __name__ == "__main__":
    main()
