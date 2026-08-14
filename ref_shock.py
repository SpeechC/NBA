"""Referee-shock identification.

Test 1 showed an unconditional gap: the actual total moves with crew foul
propensity, the closing total barely does. That is consistent with a real
omitted state variable, but it is also consistent with high-foul crews being
assigned to games the market happens to misprice for other reasons.

This separates the two. The claim to be established is:

    conditional on everything observable about the teams and the game,
    being assigned an unusually whistle-heavy crew produces incremental
    scoring that the closing market does not absorb.

SPECIFICATION

    closing total = a + c_m * CrewFoul + X'b + e
    actual  total = a + c_a * CrewFoul + X'b + e
    H0: c_a - c_m = 0

Because e = actual - closing, the coefficient on CrewFoul in

    e = a + (c_a - c_m) * CrewFoul + X'b + u

IS the gap, so that is the primary regression. c_m and c_a are reported
separately for interpretation.

X is prior-only conventional basketball state, deliberately including the team
foul environment, so CrewFoul cannot be proxying for foul-prone teams:

    scoring   trailing mean points, home + away
    pace      trailing mean PACE, home + away
    quality   trailing mean OEFF and DEFF, home + away
    fouls     FC and FD for each team, and the matchup product M
    shooting  trailing FTA rate and 3PA rate, home + away
    schedule  rest days, home and away

REF SHOCK

    RefShock = CrewFoul - E[CrewFoul | X],  E fitted on PRIOR seasons only

If crew assignment is orthogonal to team state, E[CrewFoul|X] is nearly
constant and the R^2 of that projection is near zero -- which is itself an
identification result worth reporting.

Everything is walk-forward: X coefficients and the projection are fitted on
prior seasons and applied to the held-out season, so no test-season information
enters any estimate.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

from sklearn.linear_model import LinearRegression, Ridge

import crew_foul as cfm
import crew_matchup as cmm
from data_split import SPLIT_DATE
from dispersion_priced import ols

W, MINP = 20, 10
BE = 110 / 210

# Rest days are only 64-66% covered in the master and requiring both sides
# costs over half the sample, so rest is a SECONDARY robustness spec rather
# than a primary control.
CTRL = ["mu_state", "pace_s", "oeff_s", "deff_s", "FC_h", "FC_a", "FD_h",
        "FD_a", "M", "ftr_s", "tpa_s"]
CTRL_REST = CTRL + ["rest_h", "rest_a"]


def build():
    d = cmm.build()                # CrewFoul, M, FC_*, FD_*, mu_state, e, ...
    from prepare_data import CSV, season_label
    raw = pd.read_csv(CSV, low_memory=False)
    raw["gid"] = raw["GAME-ID"].astype(str).str.strip()
    n = lambda c: pd.to_numeric(raw[c], errors="coerce")
    extra = pd.DataFrame({"gid": raw["gid"]})
    for s in ("H", "R"):
        extra[f"pace_{s}"] = n(f"PACE_{s}")
        extra[f"oeff_{s}"] = n(f"OEFF_{s}")
        extra[f"deff_{s}"] = n(f"DEFF_{s}")
        extra[f"ftr_{s}"] = n(f"FTA_{s}") / n(f"FGA_{s}")
        extra[f"tpa_{s}"] = n(f"3PA_{s}") / n(f"FGA_{s}")
        extra[f"rest_{s}"] = n("TEAM\nREST DAYS_" + s)
    extra = extra.drop_duplicates("gid")
    assert not (set(extra.columns) & set(d.columns)) - {"gid"}
    n0 = len(d)
    d = d.merge(extra, on="gid", how="left")
    assert len(d) == n0

    P = pd.concat([
        pd.DataFrame({"gid": d["gid"], "yr": d["yr"], "date": d["date"],
                      "team": d[f"TEAM_{s}"], "side": s,
                      **{v: d[f"{v}_{s}"] for v in
                         ("pace", "oeff", "deff", "ftr", "tpa")}})
        for s in ("H", "R")]).sort_values("date").reset_index(drop=True)
    g = P.groupby(["yr", "team"])
    for v in ("pace", "oeff", "deff", "ftr", "tpa"):
        P[f"m_{v}"] = g[v].transform(
            lambda s: s.shift(1).rolling(W, min_periods=MINP).mean())
    mc = [f"m_{v}" for v in ("pace", "oeff", "deff", "ftr", "tpa")]
    h = P[P.side == "H"][["gid"] + mc].add_suffix("_h").rename(
        columns={"gid_h": "gid"})
    a = P[P.side == "R"][["gid"] + mc].add_suffix("_a").rename(
        columns={"gid_a": "gid"})
    assert not (set(h.columns) | set(a.columns)) & set(d.columns) - {"gid"}
    d = d.merge(h, on="gid").merge(a, on="gid")
    for v, nm in (("pace", "pace_s"), ("oeff", "oeff_s"), ("deff", "deff_s"),
                  ("ftr", "ftr_s"), ("tpa", "tpa_s")):
        d[nm] = d[f"m_{v}_h"] + d[f"m_{v}_a"]
    d["rest_h"] = d["rest_H"].clip(0, 5)
    d["rest_a"] = d["rest_R"].clip(0, 5)
    return d.dropna(subset=CTRL + ["CrewFoul", "e", "total", "actual"]
                    ).reset_index(drop=True)


def with_rest(d):
    return d.dropna(subset=CTRL_REST).reset_index(drop=True)


def walk(d, target, extra_col="CrewFoul", ctrl=None):
    ctrl = CTRL if ctrl is None else ctrl
    """Walk-forward: X (and the CrewFoul projection) fitted on prior seasons
    only, coefficient measured on the held-out season."""
    yrs = sorted(d["yr"].unique())
    out = []
    for i in range(2, len(yrs)):
        tr = d[d["yr"].isin(yrs[:i])]
        te = d[d["yr"] == yrs[i]].copy()
        if len(te) < 100:
            continue
        mx = Ridge(alpha=1.0).fit(tr[ctrl], tr[target])
        te["resid"] = te[target].values - mx.predict(te[ctrl])
        mp = Ridge(alpha=1.0).fit(tr[ctrl], tr[extra_col])
        te["shock"] = te[extra_col].values - mp.predict(te[ctrl])
        te["proj_r2"] = mp.score(tr[ctrl], tr[extra_col])
        out.append(te)
    return pd.concat(out)


def main():
    d = build()
    dev = d[d["date"] < SPLIT_DATE]
    print("=" * 100)
    print("REFEREE-SHOCK IDENTIFICATION")
    print("=" * 100)
    print(f"  {len(d):,} games   develop {len(dev):,}   "
          f"holdout {len(d)-len(dev):,}   {len(CTRL)} controls")

    print("\n  IS CREW ASSIGNMENT ORTHOGONAL TO TEAM STATE?")
    m = LinearRegression().fit(dev[CTRL], dev["CrewFoul"])
    print(f"    R^2 of CrewFoul on the {len(CTRL)} pregame controls (develop): "
          f"{m.score(dev[CTRL], dev['CrewFoul']):.5f}")
    for c in ("M", "FC_h", "FD_h", "pace_s", "oeff_s"):
        print(f"      corr(CrewFoul, {c:8}) = "
              f"{np.corrcoef(d['CrewFoul'], d[c])[0,1]:+.4f}")

    print("\n" + "=" * 100)
    print("PRIMARY — H0: c_a - c_m = 0,  in sample by window")
    print("=" * 100)
    print(f"    {'window':10} {'n':>6} {'c_market':>10} {'c_true':>10} "
          f"{'GAP = c_a-c_m':>15} {'t':>7}")
    for lab, x in (("develop", dev), ("holdout", d[d["date"] >= SPLIT_DATE]),
                   ("all", d)):
        X = np.column_stack([x["CrewFoul"]] + [x[c] for c in CTRL])
        bm, sem, tm = ols(x["total"].values, X)
        bt, set_, tt = ols(x["actual"].values, X)
        bg, seg, tg = ols(x["e"].values, X)
        print(f"    {lab:10} {len(x):6,} {bm[1]:10.3f} {bt[1]:10.3f} "
              f"{bg[1]:15.3f} {tg[1]:7.2f}")
    print("    (the gap regression is e = actual - closing on the same X,")
    print("     so its CrewFoul coefficient is exactly c_a - c_m)")

    print("\n" + "=" * 100)
    print("WALK-FORWARD — controls and projection fitted on PRIOR seasons only")
    print("=" * 100)
    R = walk(d, "e")
    print(f"    projection R^2 of CrewFoul on X, by fold: "
          + " ".join(f"{g['proj_r2'].iloc[0]:.4f}" for _, g in R.groupby("yr")))
    for lab, x in (("all OOS seasons", R),
                   ("HOLDOUT only", R[R["date"] >= SPLIT_DATE])):
        b, se, t = ols(x["resid"].values, x["shock"].values.reshape(-1, 1))
        print(f"    {lab:18} n={len(x):5,}  gap coefficient {b[1]:+.4f} "
              f"se {se[1]:.4f}  t={t[1]:+.2f}")
    print(f"\n    {'season':8} {'n':>6} {'gap coef':>10} {'t':>7} "
          f"{'mean e':>9}")
    for y, g in R.groupby("yr"):
        b, se, t = ols(g["resid"].values, g["shock"].values.reshape(-1, 1))
        print(f"    {y:<8} {len(g):6,} {b[1]:10.4f} {t[1]:7.2f} "
              f"{g['e'].mean():9.3f}")

    print("\n" + "=" * 100)
    print("ECONOMIC SHAPE — is it monotonic, or concentrated in the tail?")
    print("=" * 100)
    for lab, x in (("all OOS seasons", R),
                   ("HOLDOUT only", R[R["date"] >= SPLIT_DATE])):
        x = x.copy()
        x["dq"] = x.groupby("yr")["shock"].transform(
            lambda s: pd.qcut(s, 10, labels=False, duplicates="drop"))
        print(f"\n  {lab}  (deciles of RefShock, formed within season)")
        print(f"    {'D':>3} {'n':>6} {'shock':>8} {'mean e':>9} "
              f"{'resid e':>9} {'over %':>8} {'1.96se':>8}")
        for q, g in x.groupby("dq", observed=True):
            ov = (g["e"] > 0).mean()
            print(f"    {int(q)+1:3d} {len(g):6,} {g['shock'].mean():8.3f} "
                  f"{g['e'].mean():9.3f} {g['resid'].mean():9.3f} "
                  f"{100*ov:8.2f} {100*1.96*np.sqrt(ov*(1-ov)/len(g)):8.2f}")
        top = x[x["dq"] == x["dq"].max()]
        ov = (top["e"] > 0).mean()
        print(f"    top decile n={len(top):,}  over {100*ov:.2f}%  "
              f"(break-even {100*BE:.2f}%)  "
              f"edge {100*ov-100*BE:+.2f}pp")


    print("\n" + "=" * 100)
    print("ROBUSTNESS — adding rest days (costs half the sample to coverage)")
    print("=" * 100)
    dr = with_rest(d)
    X = np.column_stack([dr["CrewFoul"]] + [dr[c] for c in CTRL_REST])
    bg, seg, tg = ols(dr["e"].values, X)
    print(f"    in sample, all   n={len(dr):,}  gap {bg[1]:+.3f}  t={tg[1]:+.2f}")
    Rr = walk(dr, "e", ctrl=CTRL_REST)
    b, se, t = ols(Rr["resid"].values, Rr["shock"].values.reshape(-1, 1))
    print(f"    walk-forward     n={len(Rr):,}  gap {b[1]:+.4f} "
          f"se {se[1]:.4f}  t={t[1]:+.2f}")
    Xc = np.column_stack([dr["CrewFoul"]] + [dr[c] for c in CTRL])
    bg2, _, tg2 = ols(dr["e"].values, Xc)
    print(f"    same rows, NO rest controls: gap {bg2[1]:+.3f} t={tg2[1]:+.2f}"
          "   [isolates the control set from the sample change]")


if __name__ == "__main__":
    main()
