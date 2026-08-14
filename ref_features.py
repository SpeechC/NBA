"""Build referee state features ONCE, on the complete game universe.

Pre-registered in PREREG_ref_regime.md. Written to ref_features.csv and merged
into regression samples afterwards, so analysis-sample filtering can never
change the features themselves -- which it did in the previous version.

Two states, deliberately separated:

  CrewShock         referee IDENTITY, matched horizons. Each official's last
                    N games minus the league level over that SAME calendar
                    span, shrunk, summed over the crew.

  LeagueFoulState   the contemporaneous foul CLIMATE: trailing 200-game league
                    mean minus trailing 1230-game league mean.

Everything is strictly prior-only.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import refs

ADVF = "/mnt/c/NBA2/advanced_stats/game_advanced_stats.csv"
OUT = "ref_features.csv"
N, MINN = 60, 25            # official's horizon
SHORT, LONG = 200, 1230     # league climate horizons


def universe():
    """Every regular-season game with officials and foul data. No control
    filtering of any kind."""
    d = refs.build()
    d["gid"] = d["GAME-ID"].astype(str).str.strip()
    adv = pd.read_csv(ADVF, low_memory=False)
    adv["gid"] = adv["GAME-ID"].astype(str).str.strip()
    cols = [f"ADV_PF_PER100_OPP_POSS_{s}" for s in ("H", "R")]
    adv = adv[["gid"] + cols]
    n0 = len(d)
    d = d.merge(adv, on="gid", how="left")
    assert len(d) == n0
    d["pf_rate"] = d[cols[0]] + d[cols[1]]
    d = d.dropna(subset=["pf_rate", "ref1", "ref2", "ref3"])
    return d.sort_values(["date", "gid"]).reset_index(drop=True)


def league_climate(d):
    """Trailing short-window minus trailing long-window league foul level."""
    s = d["pf_rate"].shift(1)
    short = s.rolling(SHORT, min_periods=SHORT // 2).mean()
    long = s.rolling(LONG, min_periods=LONG // 2).mean()
    return short - long


def matched_ref_effect(d, k):
    """Each official's last N games minus the league level over the SAME span.

    The league term is measured over the identical calendar window as the
    referee term, so both see the same foul climate and the difference is
    identity only.
    """
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
    lgm = (cum[j2] - cum[j1]) / cnt
    long["lg_matched"] = np.nan
    long.loc[ok, "lg_matched"] = lgm
    long["eff"] = ((long["rm"] - long["lg_matched"])
                   * long["rn"] / (long["rn"] + k)).fillna(0.0)
    long["span_games"] = np.nan
    long.loc[ok, "span_games"] = cnt
    agg = long.groupby("row").agg(
        CrewShock=("eff", "sum"), min_n=("rn", "min"),
        span=("span_games", "mean"))
    return agg.reindex(np.arange(len(d)))


def estimate_k(d):
    """Method of moments on DEVELOP only, on the matched-horizon scale."""
    from data_split import SPLIT_DATE
    dev = d[d["date"] < SPLIT_DATE]
    lg = dev["pf_rate"].shift(1).rolling(SHORT, min_periods=50).mean()
    y = (dev["pf_rate"] - lg).dropna()
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
    return se2 / vr, np.sqrt(vr)


def build(save=True):
    d = universe()
    k, sig = estimate_k(d)
    d["LeagueFoulState"] = league_climate(d)
    agg = matched_ref_effect(d, k)
    d["CrewShock"] = agg["CrewShock"].values
    d["min_prior"] = agg["min_n"].values
    out = d[["gid", "date", "yr", "CrewShock", "LeagueFoulState", "min_prior",
             "pf_rate", "ref1", "ref2", "ref3"]].copy()
    if save:
        out.to_csv(OUT, index=False)
    return out, k, sig, agg


def main():
    out, k, sig, agg = build()
    print(f"complete universe: {len(out):,} regular-season games, "
          f"seasons {sorted(out['yr'].unique())}")
    print(f"shrinkage k (develop, matched scale) = {k:.1f}   "
          f"sigma_ref = {sig:.3f}")
    print(f"matched league span: median {agg['span'].median():.0f} league "
          f"games behind each official's {N}-game window")
    print(f"\nCrewShock       mean {out['CrewShock'].mean():+.4f}  "
          f"sd {out['CrewShock'].std():.4f}  "
          f"nonzero {100*(out['CrewShock']!=0).mean():.1f}%")
    print(f"LeagueFoulState mean {out['LeagueFoulState'].mean():+.4f}  "
          f"sd {out['LeagueFoulState'].std():.4f}  "
          f"coverage {100*out['LeagueFoulState'].notna().mean():.1f}%")
    print(f"corr(CrewShock, LeagueFoulState) = "
          f"{out[['CrewShock','LeagueFoulState']].corr().iloc[0,1]:+.4f}")
    print("\nseason means  [CrewShock must be flat; that was the old defect]")
    t = out.groupby("yr")[["CrewShock", "LeagueFoulState"]].agg(
        ["mean", "std"]).round(4)
    print(t.to_string())
    d2 = out.copy()
    d2["doy"] = (d2["date"] - d2.groupby("yr")["date"].transform("min")).dt.days
    print(f"\ncorr(CrewShock, day-of-season)       = "
          f"{d2[['CrewShock','doy']].corr().iloc[0,1]:+.4f}")
    print(f"corr(LeagueFoulState, day-of-season) = "
          f"{d2[['LeagueFoulState','doy']].corr().iloc[0,1]:+.4f}"
          "   [this one SHOULD carry time structure]")
    print(f"\nwritten to {OUT}")


if __name__ == "__main__":
    main()
