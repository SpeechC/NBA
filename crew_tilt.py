"""CrewTilt STAGE 1 — is home/road whistle tilt a persistent referee trait?

Pre-registered in PREREG_crew_tilt.md. This script runs ONLY the Stage 1
persistence gate. It does not read the spread, the margin, or any market
quantity: if the gate fails, no outcome can have influenced the decision to
stop.

    tilt = ADV_PF_PER100_OPP_POSS_R - ADV_PF_PER100_OPP_POSS_H

positive = the road team is whistled more = officiating favours the home side.

Architecture copied from ref_features.py with the outcome variable swapped and
nothing else changed: N=60 min 25, matched league horizon, EB shrinkage with k
by method of moments on development only. ref_features.py is NOT modified.

Four gates, all of which must pass:
  G1a  between-official true SD > 0 after removing sampling noise
  G1b  within-season split-half correlation of official mean tilt, t > 2
  G1c  forward persistence slope > 0, t > 2, on development
  G1d  time-local (7-day block) crew permutation of G1c, p < 0.05
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import ref_features as RF
import refs
from data_split import SPLIT_DATE
from dispersion_priced import ols

ADVF = RF.ADVF
N, MINN = RF.N, RF.MINN              # 60, 25 -- identical to CrewShock
SHORT, LONG = RF.SHORT, RF.LONG      # 200, 1230
NPERM = 2000
RNG = np.random.default_rng(20260817)


def universe():
    """Every regular-season game with officials and per-side foul rates."""
    d = refs.build()
    d["gid"] = d["GAME-ID"].astype(str).str.strip()
    adv = pd.read_csv(ADVF, low_memory=False)
    adv["gid"] = adv["GAME-ID"].astype(str).str.strip()
    cH, cR = "ADV_PF_PER100_OPP_POSS_H", "ADV_PF_PER100_OPP_POSS_R"
    n0 = len(d)
    d = d.merge(adv[["gid", cH, cR]], on="gid", how="left")
    assert len(d) == n0
    # positive tilt = ROAD whistled more = pro-home officiating
    d["tilt"] = d[cR] - d[cH]
    d["pf_rate"] = d[cH] + d[cR]
    d = d.dropna(subset=["tilt", "ref1", "ref2", "ref3"])
    return d.sort_values(["date", "gid"]).reset_index(drop=True)


def league_climate(d, col):
    s = d[col].shift(1)
    return (s.rolling(SHORT, min_periods=SHORT // 2).mean()
            - s.rolling(LONG, min_periods=LONG // 2).mean())


def matched_ref_effect(d, k, col):
    """Each official's last N games on `col`, minus the league level over the
    SAME calendar span, shrunk n/(n+k), summed over the crew."""
    dates = d["date"].values.astype("datetime64[ns]").astype(np.int64)
    sd = np.sort(dates)
    cum = np.concatenate([[0.0], np.cumsum(d[col].values[np.argsort(
        dates, kind="stable")])])

    long = pd.concat([
        pd.DataFrame({"row": np.arange(len(d)), "slot": i, "date": dates,
                      "ref": d[f"ref{i}"].values, "v": d[col].values})
        for i in (1, 2, 3)])
    long = long.sort_values(["ref", "date"], kind="stable").reset_index(drop=True)
    g = long.groupby("ref", sort=False)
    p = g["v"].shift(1)
    long["rm"] = p.groupby(long["ref"]).transform(
        lambda s: s.rolling(N, min_periods=MINN).mean())
    long["rn"] = p.groupby(long["ref"]).transform(
        lambda s: s.rolling(N, min_periods=MINN).count())
    dprev = g["date"].shift(1)
    long["d_end"] = dprev.groupby(long["ref"]).transform(
        lambda s: s.rolling(N, min_periods=MINN).max())
    long["d_start"] = dprev.groupby(long["ref"]).transform(
        lambda s: s.rolling(N, min_periods=MINN).min())

    ok = long["rn"].notna() & long["d_start"].notna()
    j1 = np.searchsorted(sd, long.loc[ok, "d_start"].values, side="left")
    j2 = np.searchsorted(sd, long.loc[ok, "d_end"].values, side="right")
    cnt = np.maximum(j2 - j1, 1)
    long["lg_matched"] = np.nan
    long.loc[ok, "lg_matched"] = (cum[j2] - cum[j1]) / cnt
    long["eff"] = ((long["rm"] - long["lg_matched"])
                   * long["rn"] / (long["rn"] + k)).fillna(0.0)
    agg = long.groupby("row").agg(eff=("eff", "sum"), min_n=("rn", "min"))
    return agg.reindex(np.arange(len(d)))


def estimate_k(d, col):
    """Method of moments on DEVELOPMENT only, on the matched-horizon scale."""
    dev = d[d["date"] < SPLIT_DATE]
    lg = dev[col].shift(1).rolling(SHORT, min_periods=50).mean()
    y = (dev[col] - lg).dropna()
    reflist = sorted(set(dev["ref1"]) | set(dev["ref2"]) | set(dev["ref3"]))
    sub = dev.loc[y.index]
    C = refs.codes(sub, reflist)
    flat = C.ravel()
    cnt = np.bincount(flat[flat >= 0], minlength=len(reflist)).astype(float)
    m = refs.ref_means(C, y.values, len(reflist), cnt)
    keep = cnt >= 100
    w = cnt[keep] / cnt[keep].sum()
    cen = m[keep] - np.sum(w * m[keep])
    se2 = y.var()
    vr = max(np.sum(w * cen ** 2) - se2 * np.mean(1.0 / cnt[keep]), 1e-9)
    return se2 / vr, np.sqrt(vr), len(reflist), int(keep.sum())


def main():
    d = universe()
    print(f"  universe {len(d):,} regular-season games, seasons "
          f"{sorted(d['yr'].unique())}")
    print(f"  league mean tilt {d['tilt'].mean():+.4f} "
          f"(sd {d['tilt'].std():.4f}) fouls/100 -- positive = pro-home")
    print("  by season (the secular decline in home advantage lives here):")
    t = d.groupby("yr")["tilt"].agg(["size", "mean", "std"]).round(4)
    print("   " + t.to_string().replace("\n", "\n   "))

    k, sig, nref, nkeep = estimate_k(d, "tilt")
    print(f"\n  shrinkage k (development, matched scale) = {k:.1f}"
          f"   sigma_ref = {sig:.4f}")
    print(f"  officials {nref}, of which {nkeep} with >=100 development games")

    d["LeagueTiltState"] = league_climate(d, "tilt")
    agg = matched_ref_effect(d, k, "tilt")
    d["CrewTilt"] = agg["eff"].values
    d["min_prior"] = agg["min_n"].values
    ck, _ = RF.estimate_k(d)
    d["CrewShock"] = matched_ref_effect(d, ck, "pf_rate")["eff"].values
    # GENEROSITY CHECK: if MoM returns tau^2 <= 0 the shrinkage constant blows
    # up and CrewTilt collapses to ~0, which would make G1c/G1d degenerate for
    # a numerical reason rather than a substantive one. Carry an UNSHRUNK
    # (k=0) version so the persistence gates get a strictly more favourable
    # test. Pre-registered spec stays primary; this is reported alongside.
    d["CrewTiltRaw"] = matched_ref_effect(d, 0.0, "tilt")["eff"].values
    print(f"  CrewTiltRaw (k=0, unshrunk)  sd {d['CrewTiltRaw'].std():.4f}"
          f"   [generosity check, see docstring]")

    print(f"\n  CrewTilt   mean {d['CrewTilt'].mean():+.4f}  "
          f"sd {d['CrewTilt'].std():.4f}  "
          f"nonzero {100*(d['CrewTilt']!=0).mean():.1f}%")
    print(f"  CrewShock  mean {d['CrewShock'].mean():+.4f}  "
          f"sd {d['CrewShock'].std():.4f}   [rebuilt here for orthogonality "
          f"only; the frozen file is untouched]")
    print(f"  corr(CrewTilt, CrewShock) = "
          f"{d[['CrewTilt','CrewShock']].corr().iloc[0,1]:+.4f}"
          f"   [near zero means tilt is a genuinely new channel]")

    dev = d[d["date"] < SPLIT_DATE].copy()
    print("\n" + "=" * 92)
    print("G1a — BETWEEN-OFFICIAL HETEROGENEITY (method of moments)")
    print("=" * 92)
    # noise-corrected variance of per-official mean tilt, development
    long = pd.concat([dev[[f"ref{i}", "tilt"]].rename(
        columns={f"ref{i}": "ref"}) for i in (1, 2, 3)])
    per = long.groupby("ref")["tilt"].agg(["mean", "size", "std"])
    per = per[per["size"] >= 100]
    se2 = (per["std"] ** 2 / per["size"]).mean()
    tau2 = per["mean"].var(ddof=1) - se2
    share = max(tau2, 0) / per["mean"].var(ddof=1)
    print(f"  officials with >=100 games: {len(per)}")
    print(f"  observed variance of official mean tilt {per['mean'].var(ddof=1):.5f}")
    print(f"  sampling-noise variance                 {se2:.5f}")
    print(f"  implied TRUE between-official variance  {tau2:+.5f}"
          f"   -> true SD {np.sqrt(max(tau2,0)):.4f} fouls/100")
    print(f"  signal share {share:.3f}")
    g1a = tau2 > 0
    print(f"  GATE G1a (tau^2 > 0): {'PASS' if g1a else 'FAIL'}")

    print("\n" + "=" * 92)
    print("G1b — WITHIN-SEASON SPLIT-HALF RELIABILITY")
    print("=" * 92)
    dv = dev.sort_values("date").copy()
    rows = []
    for i in (1, 2, 3):
        rows.append(dv[["yr", "date", f"ref{i}", "tilt"]].rename(
            columns={f"ref{i}": "ref"}))
    L = pd.concat(rows).sort_values("date")
    L["gn"] = L.groupby(["yr", "ref"]).cumcount()
    A = L[L["gn"] % 2 == 0].groupby(["yr", "ref"])["tilt"].agg(["mean", "size"])
    B = L[L["gn"] % 2 == 1].groupby(["yr", "ref"])["tilt"].agg(["mean", "size"])
    j = A.join(B, lsuffix="_a", rsuffix="_b").dropna()
    j = j[(j["size_a"] >= 20) & (j["size_b"] >= 20)]
    r = np.corrcoef(j["mean_a"], j["mean_b"])[0, 1]
    tb = r * np.sqrt(len(j) - 2) / np.sqrt(1 - r * r)
    print(f"  official-seasons with >=20 games per half: {len(j)}")
    print(f"  split-half corr {r:+.4f} (t={tb:+.2f})")
    ts = L.groupby(["yr", "ref"])["tilt"].agg(["mean", "size"]).reset_index()
    ts = ts[ts["size"] >= 40]
    ts["nxt"] = ts["yr"] + 1
    jj = ts.merge(ts, left_on=["ref", "nxt"], right_on=["ref", "yr"],
                  suffixes=("_t", "_n"))
    rs = np.corrcoef(jj["mean_t"], jj["mean_n"])[0, 1]
    print(f"  season-to-season corr {rs:+.4f} (n={len(jj)} pairs)"
          f"   [reported, not a gate]")
    g1b = (r > 0) and (tb > 2)
    print(f"  GATE G1b (r>0 and t>2): {'PASS' if g1b else 'FAIL'}")

    print("\n" + "=" * 92)
    print("G1c — FORWARD PERSISTENCE  (realized tilt ~ CrewTilt + LeagueTilt)")
    print("=" * 92)
    s = dev.dropna(subset=["CrewTilt", "CrewTiltRaw", "LeagueTiltState",
                           "tilt"])
    X = np.column_stack([s["CrewTilt"], s["LeagueTiltState"]])
    b, se, tt = ols(s["tilt"].values, X)
    print(f"  n={len(s):,}")
    print(f"  PRE-REGISTERED (shrunk)  CrewTilt slope {b[1]:+.4f} "
          f"(t={tt[1]:+.2f})   LeagueTiltState {b[2]:+.4f} (t={tt[2]:+.2f})")
    Xr = np.column_stack([s["CrewTiltRaw"], s["LeagueTiltState"]])
    br, _, tr = ols(s["tilt"].values, Xr)
    print(f"  GENEROSITY (unshrunk)    CrewTilt slope {br[1]:+.4f} "
          f"(t={tr[1]:+.2f})")
    print(f"  [CrewShock's analogous persistence slope ran 1.43-2.33 by season]")
    g1c = (b[1] > 0) and (tt[1] > 2)
    g1c_raw = (br[1] > 0) and (tr[1] > 2)
    print(f"  GATE G1c (slope>0 and t>2): {'PASS' if g1c else 'FAIL'}"
          f"   [unshrunk would be {'PASS' if g1c_raw else 'FAIL'}]")

    print("\n" + "=" * 92)
    print(f"G1d — TIME-LOCAL PERMUTATION, whole crews reshuffled within 7-day "
          f"blocks ({NPERM} reps)")
    print("=" * 92)
    # permute the UNSHRUNK state: it is the more favourable of the two and the
    # shrunk one is numerically collapsed
    obs = br[1]
    y = s["tilt"].values
    lts = s["LeagueTiltState"].values
    ct = s["CrewTiltRaw"].values
    blk = ((s["date"] - s["date"].min()).dt.days // 7).values
    blocks = [np.where(blk == u)[0] for u in np.unique(blk)]
    null = np.empty(NPERM)
    for i in range(NPERM):
        p = ct.copy()
        for bl in blocks:
            if len(bl) > 1:
                p[bl] = ct[bl][RNG.permutation(len(bl))]
        bb, _, _ = ols(y, np.column_stack([p, lts]))
        null[i] = bb[1]
    pv = (1 + np.sum(np.abs(null) >= abs(obs))) / (NPERM + 1)
    print(f"  observed slope {obs:+.4f}   null {null.mean():+.4f} "
          f"sd {null.std():.4f}   two-sided p={pv:.4f}")
    g1d = pv < 0.05
    print(f"  GATE G1d (p<0.05): {'PASS' if g1d else 'FAIL'}")

    print("\n" + "=" * 92)
    print("STAGE 1 VERDICT")
    print("=" * 92)
    for nm, ok in (("G1a heterogeneity", g1a), ("G1b split-half", g1b),
                   ("G1c forward persistence", g1c), ("G1d permutation", g1d)):
        print(f"  {nm:28} {'PASS' if ok else 'FAIL'}")
    allp = g1a and g1b and g1c and g1d
    print(f"\n  -> {'ALL GATES PASS: proceed to Stage 2' if allp else
                    'GATE FAILED: STOP. No spread quantity is computed.'}")


if __name__ == "__main__":
    main()
