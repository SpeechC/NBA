"""CrewShock in the PLAYOFFS — adjacent-population probe.

STATUS. This is not a conditioning attempt on the regular-season signal and
cannot modify anything. PROSPECTIVE.md freezes the book on regular-season games;
whatever this shows, the frozen rule, threshold and staking are unchanged. It
sits in the same category as the 2H-total, H1-price and OT-premium probes:
does the known omission extend to an adjacent population?

IDENTIFICATION WARNING, stated first because it governs every number below.
Playoff crews are SELECTED. The NBA assigns its highest-rated officials to the
postseason and narrows the pool each round. The five exogeneity checks that
identified the regular-season result -- assignment R^2, state correlation, team
slope dispersion, tail balance, individual HIGH/LOW assignment -- were all run
on regular-season assignment and DO NOT transfer. Anything found here is
descriptive. In particular, a crew's CrewShock in the playoffs is correlated
with being a highly rated official, which is plausibly correlated with series
quality and matchup, so a market gap cannot be read as an omission.

CONSTRUCTION. Each official's state is built from their prior REGULAR-SEASON
games only: the rolling mean of their last N=60 regular-season games as of the
most recent such game strictly BEFORE the playoff date, minus the league mean
over that identical calendar span, shrunk n/(n+k) with the frozen k from
ref_features.estimate_k. Playoff games never enter any referee history or any
league baseline. ref_features.py is not modified.

PRIMARY is the MECHANISM on continuous CrewShock (CrewShock -> foul rate ->
FTA -> points). With 671 games a continuous regressor is the only adequately
powered test.

SECONDARY is c_market vs c_true on the closing total.

The Q85 BETTING RULE is reported for completeness only and is NOT a test: at
~15% selection it yields ~100 games, where the SE of a win rate is ~5pp and the
detectable difference is ~10pp. It cannot resolve anything and no conclusion is
drawn from it.

Inference is clustered by SERIES (same two teams within one postseason), since
games within a series are repeated matchups and are not independent.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import ref_features as RF
import refs
from prepare_data import CSV, season_label

ADVF = RF.ADVF
N, MINN = RF.N, RF.MINN
THR = 0.8682                      # frozen development Q85, not re-derived


def load(kind):
    raw = pd.read_csv(CSV, low_memory=False)
    raw["lbl"] = season_label(raw).astype(str)
    d = raw[raw["lbl"].str.contains(kind, na=False)].copy()
    n = lambda c: pd.to_numeric(d[c], errors="coerce")
    d["gid"] = d["GAME-ID"].astype(str).str.strip()
    d["date"] = pd.to_datetime(d["DATE"], errors="coerce")
    d["yr"] = d["lbl"].str.extract(r"(\d{4})")[0].astype(int)
    d["total"] = n("CLOSING TOTAL_H")
    d["actual"] = n("PTS_H") + n("PTS_R")
    d["fta"] = n("TEAM_FTA_H") + n("TEAM_FTA_R")
    d["team_h"], d["team_r"] = d["TEAM_H"], d["TEAM_R"]
    RU_H, RU_R = "REFEREE\n&\nUMPIRE_H", "REFEREE\n&\nUMPIRE_R"
    d["ref1"] = d["MAIN REF_R"].fillna(d["CREW CHIEF_R"])
    d["ref2"] = d["CREW_R"].fillna(d[RU_R])
    d["ref3"] = d["CREW_H"].fillna(d[RU_H])
    for c in ("ref1", "ref2", "ref3"):
        d[c] = d[c].astype(str).str.strip().str.replace(r"\s+", " ", regex=True)
        d.loc[d[c].isin(["nan", ""]), c] = np.nan
    adv = pd.read_csv(ADVF, low_memory=False)
    adv["gid"] = adv["GAME-ID"].astype(str).str.strip()
    cols = [f"ADV_PF_PER100_OPP_POSS_{s}" for s in ("H", "R")]
    d = d.merge(adv[["gid"] + cols], on="gid", how="left")
    d["pf_rate"] = d[cols[0]] + d[cols[1]]
    keep = ["gid", "date", "yr", "lbl", "total", "actual", "fta", "pf_rate",
            "team_h", "team_r", "ref1", "ref2", "ref3"]
    return d.dropna(subset=["pf_rate", "ref1", "ref2", "ref3", "total"])[
        keep].sort_values("date").reset_index(drop=True)


def ref_state_from_rs(rs, po, k):
    """For each playoff game, each official's regular-season state as of their
    most recent RS game strictly before that date. Playoff games contribute to
    nothing."""
    rs = rs.sort_values("date").reset_index(drop=True)
    sd = rs["date"].values.astype("datetime64[ns]").astype(np.int64)
    cum = np.concatenate([[0.0], np.cumsum(rs["pf_rate"].values)])

    long = pd.concat([
        pd.DataFrame({"date": rs["date"], "ref": rs[f"ref{i}"],
                      "pf": rs["pf_rate"]}) for i in (1, 2, 3)])
    long = long.dropna(subset=["ref"]).sort_values(["ref", "date"],
                                                   kind="stable")
    g = long.groupby("ref", sort=False)["pf"]
    long["rm"] = g.transform(lambda s: s.rolling(N, min_periods=MINN).mean())
    long["rn"] = g.transform(lambda s: s.rolling(N, min_periods=MINN).count())
    # roll on an integer date: pandas cannot roll datetime64 dtypes
    long["dnum"] = long["date"].values.astype("datetime64[ns]").astype(np.int64)
    gd = long.groupby("ref", sort=False)["dnum"]
    long["d_end"] = gd.transform(lambda s: s.rolling(N, min_periods=MINN).max())
    long["d_start"] = gd.transform(
        lambda s: s.rolling(N, min_periods=MINN).min())
    long = long.dropna(subset=["rn", "d_start"])

    j1 = np.searchsorted(sd, long["d_start"].values, side="left")
    j2 = np.searchsorted(sd, long["d_end"].values, side="right")
    cnt = np.maximum(j2 - j1, 1)
    long["eff"] = ((long["rm"] - (cum[j2] - cum[j1]) / cnt)
                   * long["rn"] / (long["rn"] + k))
    long = long.sort_values("date", kind="stable")

    out = np.zeros(len(po))
    minn = np.full(len(po), np.nan)
    for i in (1, 2, 3):
        s = po[["date", f"ref{i}"]].rename(columns={f"ref{i}": "ref"}).copy()
        s["_o"] = np.arange(len(po))
        s = s.sort_values("date", kind="stable")
        m = pd.merge_asof(s, long[["date", "ref", "eff", "rn"]], on="date",
                          by="ref", direction="backward",
                          allow_exact_matches=False)
        m = m.sort_values("_o")
        out += m["eff"].fillna(0.0).values
        minn = np.fmin(minn, m["rn"].values) if i > 1 else m["rn"].values
    return out, minn


def clus_ols(y, X, cl):
    """OLS with cluster-robust SEs. Returns (b, t)."""
    A = np.column_stack([np.ones(len(y)), X])
    XtXi = np.linalg.pinv(A.T @ A)
    b = XtXi @ (A.T @ y)
    u = y - A @ b
    meat = np.zeros((A.shape[1], A.shape[1]))
    for c in np.unique(cl):
        m = cl == c
        s = A[m].T @ u[m]
        meat += np.outer(s, s)
    G = len(np.unique(cl))
    V = XtXi @ meat @ XtXi * (G / max(G - 1, 1))
    return b, b / np.sqrt(np.diag(V))


def main():
    rs = load("Regular Season")
    po = load("Playoffs")
    k, sig = RF.estimate_k(rs)
    print(f"  regular season {len(rs):,} games   playoffs {len(po):,} games")
    print(f"  frozen shrinkage k = {k:.1f} (development, from ref_features)")

    po["CrewShock"], po["min_prior"] = ref_state_from_rs(rs, po, k)
    rsf = pd.read_csv("ref_features.csv")
    rsf["gid"] = rsf["gid"].astype(str).str.strip()

    print("\n" + "=" * 92)
    print("SELECTION DIAGNOSTIC — playoff crews are chosen, not assigned")
    print("=" * 92)
    po_refs = set(pd.concat([po[f"ref{i}"] for i in (1, 2, 3)]).dropna())
    rs_refs = set(pd.concat([rs[f"ref{i}"] for i in (1, 2, 3)]).dropna())
    print(f"  distinct officials: regular season {len(rs_refs)}   "
          f"playoffs {len(po_refs)}  ({100*len(po_refs)/len(rs_refs):.0f}%)")
    print(f"  {'season':>8}{'RS refs':>10}{'PO refs':>10}{'PO games':>10}")
    for y in sorted(po["yr"].unique()):
        a = set(pd.concat([rs[rs["yr"] == y - 1][f"ref{i}"]
                           for i in (1, 2, 3)]).dropna())
        b = set(pd.concat([po[po["yr"] == y][f"ref{i}"]
                           for i in (1, 2, 3)]).dropna())
        print(f"  {y:>8}{len(a):>10}{len(b):>10}"
              f"{int((po['yr']==y).sum()):>10}")
    print(f"\n  CrewShock distribution")
    print(f"    regular season  mean {rsf['CrewShock'].mean():+.4f}  "
          f"sd {rsf['CrewShock'].std():.4f}")
    print(f"    playoffs        mean {po['CrewShock'].mean():+.4f}  "
          f"sd {po['CrewShock'].std():.4f}")
    print(f"    -> playoff sd / RS sd = "
          f"{po['CrewShock'].std()/rsf['CrewShock'].std():.3f}"
          f"   [<1 means the selected pool is truncated]")
    print(f"    share above the frozen Q85 threshold ({THR:+.4f}): "
          f"RS {100*(rsf['CrewShock']>=THR).mean():.1f}%   "
          f"playoffs {100*(po['CrewShock']>=THR).mean():.1f}%")

    # series = unordered team pair within one postseason
    po["series"] = po["lbl"] + "|" + po.apply(
        lambda r: "-".join(sorted([str(r["team_h"]), str(r["team_r"])])),
        axis=1)
    print(f"\n  {po['series'].nunique()} series, "
          f"{len(po)/po['series'].nunique():.1f} games each")

    s = po.dropna(subset=["CrewShock", "pf_rate", "fta", "actual", "total"])
    s = s[s["min_prior"].notna()]
    print(f"  usable playoff games {len(s):,}")
    cl = s["series"].values
    z = ((s["CrewShock"] - rsf["CrewShock"].mean())
         / rsf["CrewShock"].std()).values      # per RS standard deviation

    print("\n" + "=" * 92)
    print("PRIMARY — MECHANISM, per 1 regular-season SD of CrewShock")
    print("=" * 92)
    print(f"  {'link':34}{'playoffs':>12}{'t (series)':>13}"
          f"{'regular season':>18}")
    RSREF = {"pf_rate": "+0.834 fouls", "fta": "+1.159 FTA",
             "actual": "+0.813 points"}
    for col, nm in (("pf_rate", "CrewShock -> foul rate"),
                    ("fta", "CrewShock -> combined FTA"),
                    ("actual", "CrewShock -> actual total")):
        b, t = clus_ols(s[col].values, np.column_stack([z]), cl)
        print(f"  {nm:34}{b[1]:+12.3f}{t[1]:13.2f}{RSREF[col]:>18}")

    print("\n" + "=" * 92)
    print("SECONDARY — is it priced?  c_true vs c_market on the total")
    print("=" * 92)
    bt, tt = clus_ols(s["actual"].values, np.column_stack([z]), cl)
    bm, tm = clus_ols(s["total"].values, np.column_stack([z]), cl)
    be, te = clus_ols((s["actual"] - s["total"]).values,
                      np.column_stack([z]), cl)
    print(f"  c_true   (actual ~ CrewShock)   {bt[1]:+.4f}  t={tt[1]:+.2f}"
          f"    [regular season +0.922]")
    print(f"  c_market (closing ~ CrewShock)  {bm[1]:+.4f}  t={tm[1]:+.2f}"
          f"    [regular season +0.043]")
    print(f"  gap      (residual ~ CrewShock) {be[1]:+.4f}  t={te[1]:+.2f}")

    print("\n" + "=" * 92)
    print("REPORTED FOR COMPLETENESS ONLY — the frozen Q85 rule in playoffs")
    print("  NOT a test: n is far too small to resolve a ~2.4pp edge")
    print("=" * 92)
    hi = s[s["CrewShock"] >= THR]
    e = (s["actual"] - s["total"])
    print(f"  games at or above {THR:+.4f}: {len(hi)}")
    if len(hi):
        eh = (hi["actual"] - hi["total"])
        print(f"  mean residual {eh.mean():+.3f} (all playoff games "
              f"{e.mean():+.3f})   over rate {100*(eh>0).mean():.2f}% "
              f"on {len(hi)} games")
        print(f"  SE of that over rate: "
              f"{100*np.sqrt(0.25/len(hi)):.2f}pp -- the 2.4pp edge is "
              f"{'invisible' if np.sqrt(0.25/len(hi))*100 > 2.4 else 'marginal'}"
              f" at this n")


if __name__ == "__main__":
    main()
