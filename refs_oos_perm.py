"""Permutation null for the WALK-FORWARD referee statistic.

The in-sample dispersion test is already permuted. This checks the separate
out-of-sample claim: fit ref effects on prior seasons, score the next season,
correlate. Under the null the crews carry no information, so shuffling crews
within season and rerunning the ENTIRE walk-forward (including alpha selection)
gives the distribution of the OOS correlation that the procedure produces by
construction.

Also splits the effect by crew role and checks season-to-season persistence.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

from sklearn.linear_model import Ridge

from refs import build, codes, incidence

NPERM = 300
ALPHA = 681.0        # the median alpha RidgeCV chose in the real folds
RNG = np.random.default_rng(11)


def wf_corr(d, target, alpha=ALPHA):
    yrs = sorted(d["yr"].unique())
    P, Y = [], []
    for i in range(3, len(yrs)):
        tr = d[d["yr"].isin(yrs[:i])]
        te = d[d["yr"] == yrs[i]]
        if len(te) < 100:
            continue
        act = sorted(set(tr["ref1"]) | set(tr["ref2"]) | set(tr["ref3"]))
        m = Ridge(alpha=alpha).fit(incidence(tr, act), tr[target])
        P.append(m.predict(incidence(te, act)))
        Y.append(te[target].values)
    p, y = np.concatenate(P), np.concatenate(Y)
    return np.corrcoef(p, y)[0, 1], len(y)


def main():
    d = build()
    refs = sorted(set(d["ref1"]) | set(d["ref2"]) | set(d["ref3"]))

    print("=" * 92)
    print("OOS PERMUTATION — is the walk-forward correlation manufactured?")
    print("=" * 92)
    obs, n = wf_corr(d, "e")
    crew = d[["ref1", "ref2", "ref3"]].values
    blocks = [np.where(d["yr"].values == u)[0] for u in d["yr"].unique()]
    null = np.empty(NPERM)
    dd = d.copy()
    for k in range(NPERM):
        perm = crew.copy()
        for b in blocks:
            perm[b] = crew[b][RNG.permutation(len(b))]
        dd["ref1"], dd["ref2"], dd["ref3"] = perm[:, 0], perm[:, 1], perm[:, 2]
        null[k], _ = wf_corr(dd, "e")
    p = (1 + np.sum(null >= obs)) / (NPERM + 1)
    print(f"  closing-total residual, n={n:,}  observed OOS corr {obs:+.4f}")
    print(f"  null over {NPERM} within-season crew reshuffles: "
          f"mean {null.mean():+.4f}  sd {null.std():.4f}  "
          f"95th pct {np.percentile(null, 95):+.4f}")
    print(f"  percentile of observed: {100*(null < obs).mean():.1f}   p = {p:.4f}")

    print("\n" + "=" * 92)
    print("WHICH SEAT?  crew chief (ref1) vs second (ref2) vs third (ref3)")
    print("=" * 92)
    C = codes(d, refs)
    y = d["e"].values
    for j, lab in ((0, "crew chief"), (1, "referee"), (2, "umpire")):
        col = C[:, j]
        cnt = np.bincount(col[col >= 0], minlength=len(refs)).astype(float)
        s = np.bincount(col[col >= 0], weights=y[col >= 0], minlength=len(refs))
        m = np.divide(s, cnt, out=np.zeros_like(s), where=cnt > 0)
        k = cnt >= 60
        w = cnt[k] / cnt[k].sum()
        cen = m[k] - np.sum(w * m[k])
        obs_sd = np.sqrt(np.sum(w * cen ** 2))
        noise = np.sqrt(y.var() * np.mean(1.0 / cnt[k]))
        print(f"  {lab:12} {k.sum():3d} officials with >=60 games in the seat   "
              f"dispersion {obs_sd:.3f}  sampling noise {noise:.3f}  "
              f"implied sigma_ref {np.sqrt(max(obs_sd**2-noise**2,0)):.3f}")

    print("\n" + "=" * 92)
    print("PERSISTENCE — does a ref's effect in season t predict season t+1?")
    print("=" * 92)
    rows = []
    for i in range(3):
        rows.append(pd.DataFrame({"yr": d["yr"], "ref": d[f"ref{i+1}"],
                                  "e": d["e"]}))
    L = pd.concat(rows)
    g = L.groupby(["yr", "ref"])["e"].agg(["mean", "size"]).reset_index()
    g = g[g["size"] >= 25]
    g["yr_next"] = g["yr"] + 1
    j = g.merge(g, left_on=["ref", "yr_next"], right_on=["ref", "yr"],
                suffixes=("_t", "_n"))
    r = np.corrcoef(j["mean_t"], j["mean_n"])[0, 1]
    t = r * np.sqrt(len(j) - 2) / np.sqrt(1 - r * r)
    b = np.polyfit(j["mean_t"], j["mean_n"], 1)[0]
    print(f"  {len(j):,} consecutive ref-season pairs (>=25 games each side)")
    print(f"  corr(mean e in t, mean e in t+1) = {r:+.4f}  t={t:+.2f}  "
          f"slope {b:+.4f}")
    print("  within-season ref-mean sd: "
          + "  ".join(f"{y_}:{gg['mean'].std():.2f}"
                      for y_, gg in g.groupby("yr")))


if __name__ == "__main__":
    main()
