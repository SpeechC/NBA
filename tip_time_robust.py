"""ADDENDUM to tip_time.py — NOT the confirmatory run.

Two defects in the pre-registered execution are addressed here, both reported
as clearly-labelled robustness rather than substituted for the primary:

  1 COVERAGE. rest_travel sets travel to NaN wherever the master's itinerary
    has a hole (a game removed from the file). Requiring it on both sides cuts
    the primary to n=2,233 of 6,631. The ESPN schedule is COMPLETE (12,067
    games, including the ones the master dropped), so travel can be rebuilt
    with no holes at all.

  2 INFERENCE. Plain within-season permutation of a regressor that is
    mechanically correlated with the travel controls decorrelates it and
    understates the null spread (perm sd 0.019 vs naive se ~0.100). Freedman-Lane
    permutation of the control-residualised target is used here instead.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
from rest_travel import ARENAS, haversine
from tip_time import (CTRL, DEV_SEASONS, NPERM, RNG, build, ols_t, oos_r2)

ABBR_LOC = {"GS": "Golden State", "GSW": "Golden State", "NO": "New Orleans",
            "NOP": "New Orleans", "NY": "New York", "NYK": "New York",
            "SA": "San Antonio", "SAS": "San Antonio", "WSH": "Washington",
            "WAS": "Washington", "UTAH": "Utah", "UTA": "Utah", "PHX": "Phoenix",
            "BKN": "Brooklyn", "CHA": "Charlotte", "PHI": "Philadelphia",
            "ATL": "Atlanta", "BOS": "Boston", "CHI": "Chicago",
            "CLE": "Cleveland", "DAL": "Dallas", "DEN": "Denver",
            "DET": "Detroit", "HOU": "Houston", "IND": "Indiana",
            "LAC": "LA Clippers", "LAL": "LA Lakers", "MEM": "Memphis",
            "MIA": "Miami", "MIL": "Milwaukee", "MIN": "Minnesota",
            "OKC": "Oklahoma City", "ORL": "Orlando", "POR": "Portland",
            "SAC": "Sacramento", "TOR": "Toronto"}


def complete_travel():
    """Per team-game travel from the FULL ESPN itinerary — no holes."""
    t = pd.read_csv("tipoffs_espn.csv")
    t["utc_ts"] = pd.to_datetime(t.utc, utc=True, format="mixed")
    t["home_city"] = t.home_abbr.map(ABBR_LOC)
    t["away_city"] = t.away_abbr.map(ABBR_LOC)
    t = t.dropna(subset=["home_city", "away_city"])
    long = pd.concat([
        t.assign(team=t.home_city, host=t.home_city),
        t.assign(team=t.away_city, host=t.home_city)])
    long = long.sort_values(["team", "utc_ts"])
    long["prev_host"] = long.groupby("team")["host"].shift(1)
    long["prev_ts"] = long.groupby("team")["utc_ts"].shift(1)
    # a gap over 60 days is an off-season break: no meaningful travel leg
    long.loc[(long.utc_ts - long.prev_ts).dt.days > 60, "prev_host"] = np.nan

    km, tz = [], []
    for h, p in zip(long.host, long.prev_host):
        if not isinstance(p, str) or h not in ARENAS or p not in ARENAS:
            km.append(np.nan); tz.append(np.nan); continue
        km.append(haversine(ARENAS[p][:2], ARENAS[h][:2]))
        tz.append(ARENAS[h][2] - ARENAS[p][2])
    long["km2"], long["tz2"] = km, tz
    long["local_date"] = (long.utc_ts.dt.tz_localize(None)
                          - pd.Timedelta(hours=5)).dt.normalize()
    return long[["local_date", "team", "host", "km2", "tz2"]]


def freedman_lane(x, y, key, ctl):
    """Permute the CONTROL-RESIDUALISED target; controls stay attached."""
    Z = np.column_stack([np.ones(len(x))] + [x[c].values for c in ctl])
    bz, *_ = np.linalg.lstsq(Z, y, rcond=None)
    resid = y - Z @ bz
    b, t, n = ols_t(y, [x[key].values] + [x[c].values for c in ctl])
    obs = b[1]
    yrs = x["season"].values
    blocks = [np.where(yrs == u)[0] for u in np.unique(yrs)]
    null = np.empty(NPERM)
    for i in range(NPERM):
        r = resid.copy()
        for bl in blocks:
            r[bl] = resid[bl][RNG.permutation(len(bl))]
        bb, _, _ = ols_t(Z @ bz + r, [x[key].values] + [x[c].values for c in ctl])
        null[i] = bb[1]
    p1 = (1 + np.sum(null >= obs)) / (NPERM + 1)
    print(f"    {key:10} n={n:>6,}  beta {obs:+.5f} (t={t[1]:+.2f})  "
          f"FL-null sd {null.std():.5f}  p1={p1:.4f}")
    return obs, t[1], p1, null.std()


def main():
    d = build()
    ct = complete_travel()
    for tag, side in (("H", "home"), ("R", "away")):
        m = d.merge(ct.rename(columns={"team": side}),
                    left_on=["date", side], right_on=["local_date", side],
                    how="left")
        d[f"tz2_{tag}"] = m["tz2"].values
        d[f"km2_{tag}"] = m["km2"].values
    C2 = [c for c in CTRL if c.startswith("st")] + ["tz2_H", "tz2_R", "km2_H", "km2_R"]

    print("COVERAGE — pre-registered controls vs complete-itinerary controls")
    for a, b in (("tz_H", "tz2_H"), ("tz_R", "tz2_R")):
        print(f"  {a} {d[a].notna().mean():.3f}   ->   {b} {d[b].notna().mean():.3f}")

    dv = d[d.is_dev]
    x = dv.dropna(subset=["dev", "H_sum"] + C2)
    print(f"\nP1 re-run, complete controls + Freedman-Lane (predicted beta > 0)")
    obs, tt, p1, nsd = freedman_lane(x, x.dev.values, "H_sum", C2)

    print("\nSecondaries, same treatment")
    for key, tgt in (("H_diff", "dev_s"), ("body_a", "dev_s"), ("early", "dev")):
        xx = dv.dropna(subset=[tgt, key] + C2)
        freedman_lane(xx, xx[tgt].values, key, C2)

    print("\nSection 5 incremental, complete controls (holdout, once)")
    tr = d[d.is_dev].dropna(subset=["dev", "H_sum"] + C2)
    te = d[~d.is_dev].dropna(subset=["dev", "H_sum"] + C2)
    A, _ = oos_r2(tr, te, C2, "dev")
    B, nB = oos_r2(tr, te, C2 + ["H_sum"], "dev")
    print(f"  n_ho={nB:,}  A {A:+.6f}   B(+H_sum) {B:+.6f}   B-A {B-A:+.6f}  "
          f"{'B WINS' if B > A else 'A WINS'}")

    sd_h = x.H_sum.std()
    print(f"\nSection 7 power at the improved coverage (n={len(x):,})")
    print(f"  MDE 95% = {1.96*nsd:.5f} pts/hour = {1.96*nsd*sd_h:.4f} pts per "
          f"1 SD of H_sum ({sd_h:.1f}h) = {1.96*nsd*24:.4f} pts per DAY of rest")
    print(f"  observed {obs:+.5f} pts/hour = {obs*24:+.4f} pts per day")


if __name__ == "__main__":
    main()
