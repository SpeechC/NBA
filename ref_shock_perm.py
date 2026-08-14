"""Permutation null for the walk-forward referee-shock gap coefficient.

The gap regression treats games as independent, but games sharing an official
are not, and CrewFoul is built from the officials themselves. Reshuffling whole
crews within season and rerunning the ENTIRE procedure -- rebuilding CrewFoul,
refitting the controls and the projection on prior seasons, re-estimating the
coefficient on the held-out season -- puts the whole estimation chain inside the
null.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import crew_foul as cfm
import ref_shock as rsk
from data_split import SPLIT_DATE
from dispersion_priced import ols

NPERM = 500
RNG = np.random.default_rng(1729)


def gap(d, k):
    d = d.copy()
    d["CrewFoul"], _ = cfm.crew_signal(d, k)
    R = rsk.walk(d, "e")
    b_all = ols(R["resid"].values, R["shock"].values.reshape(-1, 1))[0][1]
    H = R[R["date"] >= SPLIT_DATE]
    b_hold = ols(H["resid"].values, H["shock"].values.reshape(-1, 1))[0][1]
    top = R.copy()
    top["dq"] = top.groupby("yr")["shock"].transform(
        lambda s: pd.qcut(s, 10, labels=False, duplicates="drop"))
    t10 = top[top["dq"] == 9]
    return b_all, b_hold, (t10["e"] > 0).mean()


def main():
    d = rsk.build()
    k = cfm.estimate_k(d[d["date"] < SPLIT_DATE])[0]
    o_all, o_hold, o_top = gap(d, k)
    print("=" * 96)
    print("PERMUTATION — within-season crew reshuffle, whole procedure inside")
    print("=" * 96)
    print(f"  observed   gap(all OOS) {o_all:+.4f}   gap(holdout) {o_hold:+.4f}"
          f"   top-decile over {100*o_top:.2f}%")

    crew = d[["ref1", "ref2", "ref3"]].values
    yrs = d["yr"].values
    blocks = [np.where(yrs == u)[0] for u in np.unique(yrs)]
    na, nh, nt = np.empty(NPERM), np.empty(NPERM), np.empty(NPERM)
    sub = d.copy()
    for j in range(NPERM):
        perm = crew.copy()
        for b in blocks:
            perm[b] = crew[b][RNG.permutation(len(b))]
        sub["ref1"], sub["ref2"], sub["ref3"] = perm[:, 0], perm[:, 1], perm[:, 2]
        na[j], nh[j], nt[j] = gap(sub, k)
    for lab, obs, null in (("gap, all OOS seasons", o_all, na),
                           ("gap, holdout only", o_hold, nh),
                           ("top-decile over rate", o_top, nt)):
        p = (1 + np.sum(null >= obs)) / (NPERM + 1)
        z = (obs - null.mean()) / null.std()
        print(f"  {lab:24} observed {obs:+.4f}   null mean {null.mean():+.4f} "
              f"sd {null.std():.4f}   z={z:+.2f}   one-sided p={p:.4f}")


if __name__ == "__main__":
    main()
