"""Does weighting the crew chief more heavily forecast fouls better?

Development-only selection, identical to the window test's discipline:
everything except the crew aggregation weights is the frozen estimator, and
the incumbent (equal weights) is retained unless clearly beaten.

    CrewShock_w = w * eff(chief) + (1-w)/2 * (eff(ref2) + eff(ref3))

w = 1/3 is the frozen incumbent (equal weighting). Candidates 0.45, 0.55, 0.70,
plus 1.00 (chief only) as a reference bound.

Seat identity: refs.build maps ref1 = MAIN REF_R (2017-2021) or CREW CHIEF_R
(2022+), so the chief seat is identified in every season. Face validity is
checked before any forecast is run.

NO closing residual, win rate or ROI appears in this file.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import ref_features as rf
import ref_shock as rsk
import refs
from dispersion_priced import ols
from ref_window_select import build as ws_build

CTRL = rsk.CTRL
DEV_MAX = 2023
WEIGHTS = [1.0 / 3.0, 0.45, 0.55, 0.70, 1.00]


def seat_effects(d, k):
    """Per-seat shrunk effect using the frozen N=60 matched-horizon method."""
    N, MINN = rf.N, rf.MINN
    dates = d["date"].values.astype("datetime64[ns]").astype(np.int64)
    order = np.argsort(dates, kind="stable")
    sd = dates[order]
    cum = np.concatenate([[0.0], np.cumsum(d["pf_rate"].values[order])])
    long = pd.concat([
        pd.DataFrame({"row": np.arange(len(d)), "slot": i, "date": dates,
                      "ref": d[f"ref{i}"].values, "pf": d["pf_rate"].values})
        for i in (1, 2, 3)])
    long = long.sort_values(["ref", "date"], kind="stable").reset_index(drop=True)
    g = long.groupby("ref", sort=False)
    p = g["pf"].shift(1)
    dprev = g["date"].shift(1)
    long["rm"] = p.groupby(long["ref"]).transform(
        lambda s: s.rolling(N, min_periods=MINN).mean())
    long["rn"] = p.groupby(long["ref"]).transform(
        lambda s: s.rolling(N, min_periods=MINN).count())
    long["d_end"] = dprev.groupby(long["ref"]).transform(
        lambda s: s.rolling(N, min_periods=MINN).max())
    long["d_start"] = dprev.groupby(long["ref"]).transform(
        lambda s: s.rolling(N, min_periods=MINN).min())
    ok = long["rn"].notna() & long["d_start"].notna()
    j1 = np.searchsorted(sd, long.loc[ok, "d_start"].values, side="left")
    j2 = np.searchsorted(sd, long.loc[ok, "d_end"].values, side="right")
    cnt = np.maximum(j2 - j1, 1)
    long["lg"] = np.nan
    long.loc[ok, "lg"] = (cum[j2] - cum[j1]) / cnt
    long["eff"] = ((long["rm"] - long["lg"])
                   * long["rn"] / (long["rn"] + k)).fillna(0.0)
    W = long.pivot(index="row", columns="slot", values="eff").reindex(
        np.arange(len(d)))
    return W[1].values, W[2].values, W[3].values


def zbeta(x, col, sig):
    X = np.column_stack([x[sig] / x[sig].std(), x["LeagueFoulState"]]
                        + [x[c] for c in CTRL])
    b, se, t = ols(x[col].values / x[col].std(), X)
    return b[1], t[1]


def main():
    d, k, m = ws_build()
    e1, e2, e3 = seat_effects(d, k)
    cs = d[["gid", "pf_rate"]].copy()
    for w in WEIGHTS:
        cs[f"w{int(round(100*w))}"] = w * e1 + (1 - w) / 2 * (e2 + e3)
    cs["chief_eff"] = e1
    cs["other_eff"] = (e2 + e3) / 2
    m = m.merge(cs, on="gid", how="left")
    inc = "w33"
    chk = m.dropna(subset=["CrewShock", inc])
    # w=1/3 is the equal-weighted MEAN; frozen CrewShock is the SUM, so the two
    # differ by a factor of 3. Every metric used below is scale-invariant, so
    # the check is that they are perfectly collinear, not numerically equal.
    rr = np.corrcoef(chk["CrewShock"], chk[inc])[0, 1]
    sc = (chk["CrewShock"] / chk[inc]).replace([np.inf, -np.inf], np.nan).median()
    print(f"  equal-weight vs frozen CrewShock: corr {rr:.10f}, "
          f"scale factor {sc:.4f} (expected 3.0)")

    print("\n" + "=" * 96)
    print("SEAT FACE VALIDITY (chief seat = ref1 in both vendor eras)")
    print("=" * 96)
    long = pd.concat([pd.DataFrame({"ref": d[f"ref{i}"], "seat": i})
                      for i in (1, 2, 3)])
    pr = long.groupby("ref").agg(games=("seat", "size"),
                                 chief=("seat", lambda s: (s == 1).mean()))
    pr = pr[pr["games"] >= 100].sort_values("chief", ascending=False)
    print(f"  {len(pr)} officials with >=100 games; chief share median "
          f"{pr['chief'].median():.3f}, p10 {pr['chief'].quantile(.1):.3f}, "
          f"p90 {pr['chief'].quantile(.9):.3f}")
    print(f"  never chief: {int((pr['chief']==0).sum())}   "
          f"always chief: {int((pr['chief']==1).sum())}")
    print("  most-chief:  " + ", ".join(pr.head(5).index))
    print("  never-chief: " + ", ".join(pr.tail(5).index))

    need = ["pf_rate", "LeagueFoulState"] + CTRL
    cols = [f"w{int(round(100*w))}" for w in WEIGHTS]
    s = m.dropna(subset=need + cols + ["chief_eff", "other_eff"]).copy()
    dev = s[s["yr"] <= DEV_MAX]
    print(f"\n  development games {len(dev):,} (selection uses these only)")

    print("\n" + "=" * 96)
    print("DO THE SEATS DIFFER AT ALL?  chief vs the other two, development")
    print("=" * 96)
    for nm, c in (("chief effect", "chief_eff"), ("other two (mean)", "other_eff")):
        bz, tz = zbeta(dev, "pf_rate", c)
        r = np.corrcoef(dev[c], dev["pf_rate"])[0, 1]
        print(f"  {nm:20} sd {dev[c].std():.4f}   std beta {bz:+.4f} "
              f"(t={tz:+5.2f})   corr {r:+.4f}")
    X = np.column_stack([dev["chief_eff"], 2 * dev["other_eff"],
                         dev["LeagueFoulState"]] + [dev[c] for c in CTRL])
    b, se, t = ols(dev["pf_rate"].values, X)
    print(f"\n  joint model, fouls/100 ~ chief + (sum of other two) + controls")
    print(f"    chief      {b[1]:+.4f} (t={t[1]:+5.2f})")
    print(f"    other two  {b[2]:+.4f} (t={t[2]:+5.2f})")
    print(f"    ratio chief/other {b[1]/b[2]:.3f}   "
          f"(1.00 = equal weighting is correct)")
    dif = b[1] - b[2]
    sed = np.sqrt(se[1] ** 2 + se[2] ** 2)
    print(f"    difference {dif:+.4f}  se {sed:.4f}  t={dif/sed:+.2f}")

    print("\n" + "=" * 96)
    print("WEIGHT COMPARISON — development forward forecast of fouls/100")
    print("=" * 96)
    print(f"  {'weight':10}{'corr':>9}{'std beta':>10}{'t':>8}{'incr R2 %':>11}"
          f"{'chrono OOS R2 %':>17}")
    yrs = sorted(dev["yr"].unique())
    Xf = np.column_stack([dev["LeagueFoulState"]] + [dev[c] for c in CTRL])
    b0, _, _ = ols(dev["pf_rate"].values, Xf)
    r0 = dev["pf_rate"].values - np.column_stack([np.ones(len(dev)), Xf]) @ b0
    res = {}
    for w, c in zip(WEIGHTS, cols):
        r = np.corrcoef(dev[c], dev["pf_rate"])[0, 1]
        bz, tz = zbeta(dev, "pf_rate", c)
        X1 = np.column_stack([dev[c], dev["LeagueFoulState"]]
                             + [dev[cc] for cc in CTRL])
        b1, _, _ = ols(dev["pf_rate"].values, X1)
        r1 = dev["pf_rate"].values - np.column_stack(
            [np.ones(len(dev)), X1]) @ b1
        incr = 100 * (1 - (r1 ** 2).sum() / (r0 ** 2).sum())
        num = den = 0.0
        for i in range(2, len(yrs)):
            tr, te = dev[dev["yr"].isin(yrs[:i])], dev[dev["yr"] == yrs[i]]
            Xtr = np.column_stack([np.ones(len(tr)), tr[c],
                                   tr["LeagueFoulState"]]
                                  + [tr[cc] for cc in CTRL])
            bb = np.linalg.lstsq(Xtr, tr["pf_rate"].values, rcond=None)[0]
            Xte = np.column_stack([np.ones(len(te)), te[c],
                                   te["LeagueFoulState"]]
                                  + [te[cc] for cc in CTRL])
            num += ((te["pf_rate"].values - Xte @ bb) ** 2).sum()
            den += ((te["pf_rate"].values - tr["pf_rate"].mean()) ** 2).sum()
        oos = 100 * (1 - num / den)
        res[c] = (r, bz, incr, oos)
        tag = "  <- INCUMBENT" if c == inc else ""
        lab = f"w={w:.2f}" + (" (chief only)" if w == 1.0 else "")
        print(f"  {lab:10}{r:9.4f}{bz:10.4f}{tz:8.2f}{incr:11.4f}"
              f"{oos:17.4f}{tag}")

    print("\n  deltas versus the incumbent equal weighting")
    ri = res[inc]
    for w, c in zip(WEIGHTS, cols):
        if c == inc:
            continue
        print(f"    w={w:.2f}:  d corr {res[c][0]-ri[0]:+.4f}   "
              f"d incr R2 {res[c][2]-ri[2]:+.4f}pp   "
              f"d chrono OOS R2 {res[c][3]-ri[3]:+.4f}pp")

    print("\n  season-by-season standardised beta (development)")
    print(f"  {'season':9}" + "".join(f"{c:>10}" for c in cols))
    stab = {c: [] for c in cols}
    for y in yrs:
        g_ = dev[dev["yr"] == y]
        line = f"  {int(y):<9}"
        for c in cols:
            bz, _ = zbeta(g_, "pf_rate", c)
            stab[c].append(bz)
            line += f"{bz:10.4f}"
        print(line)
    print(f"  {'min':9}" + "".join(f"{min(stab[c]):10.4f}" for c in cols))
    print(f"  {'sd':9}" + "".join(f"{np.std(stab[c]):10.4f}" for c in cols))


if __name__ == "__main__":
    main()
