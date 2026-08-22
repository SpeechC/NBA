"""MOVE_COMBINED -> Kalshi tip-surface repricing (Analyses 1 and 3 of the
exchange-laboratory program; 2 and 4 are DATA-BLOCKED, see below).

DATA LIMITATION, GOVERNING EVERYTHING. The Kalshi capture holds ONE pregame
horizon: the T-1min snapshot (median 1 minute before tip). The candles table
is empty. Therefore:
  - Analysis 1 runs in its AT-TIP form: does the frozen sportsbook signal
    forecast where the exchange's probability surface sits at tip RELATIVE TO
    THE STALE OPENER?  The value is SYNTHETIC (open-centred reference), not a
    multi-horizon path.
  - Analysis 2 (fraction of repricing complete by horizon h) and Analysis 4
    (maker fills) CANNOT be run and are not simulated. High-resolution
    quote/order-book capture is the mandatory 2026-27 requirement.

SIGNAL, fully frozen. m = recursive-combiner MOVE_COMBINED exactly as in
move_combined_econ.py; the 2025-26 weights are trained on joint OOS data
through 2024-25 only, so combiner weights, latent mapping and ridge are all
out-of-sample for the evaluation season. No Kalshi information enters m.

TESTS
  A1  game level:   (mu_Kalshi_tip - open_total)  ~  m      [exchange CLV]
      residual:     (mu_Kalshi_tip - close_total) ~  m      [expect ~0]
  A3  coherence:    sd_Kalshi ~ m and |m|                   [expect ~0: the
      forecast is a LOCATION shift; variance was killed nine times]
  RUNG SYNTHETIC REPRICING VALUE (cents): per rung, sign-adjusted
      SRV = sign(m) * [ P_tip(K) - Phibar((K - open_total)/sd_tip) ]
      TERMINOLOGY, of record: this is NOT realized mark-to-market. No early
      Kalshi surface was observed; SRV is a COUNTERFACTUAL repricing value
      conditional on Kalshi initially being centred on the sportsbook opener.
      If early Kalshi already sat at the close, the capturable value is ~0.
      over the FIXED grid |m| >= 0 / .5 / 1 / 1.5 / 2. Clustered by game
      (11 rungs share one shift); date-cluster check on the headline.
  RUNG SENSITIVITY (analytic, not P&L-selected): cents per 1-point location
      shift by moneyness, phi(z)/sd -- the a-priori answer to 'which rungs'.

PROHIBITED, per instruction: threshold optimization, rung selection on
realized P&L, new Kalshi predictors, variance reopening, outcome endpoints.
"""
import warnings

import numpy as np
import pandas as pd
from scipy.stats import norm

warnings.filterwarnings("ignore")

import kalshi_calib as KC
import opening_line_error_decomposition as OLE
import resid_variance as RV

GRID = (0.0, 0.5, 1.0, 1.5, 2.0)


def build_signal():
    """Recursive MOVE_COMBINED, weights strictly from prior OOS seasons."""
    g = OLE.load()
    X, fc = OLE.design_matrix(g)
    lat = RV.pca_oos(X, fc, ["tmove"])["tmove"]
    ok = ~np.isnan(lat)
    D = X.loc[ok, ["gid", "season", "date", "home", "away", "tmove",
                   "ot_open", "ot_close", "total"]].copy()
    D["latent"] = lat[ok]
    mv = pd.read_csv("movement_full_games.csv",
                     usecols=["game_id", "pred_move", "clean"])
    mv["gid"] = mv["game_id"].astype(str).str.strip()
    D = D.merge(mv.loc[mv["clean"] == True, ["gid", "pred_move"]],
                on="gid", how="inner").dropna()
    seasons = sorted(D["season"].unique())
    D["m"] = np.nan
    for i, yr in enumerate(seasons):
        if i == 0:
            continue
        tr, te = D["season"] < yr, D["season"] == yr
        A = np.column_stack([np.ones(tr.sum()), D.loc[tr, "pred_move"],
                             D.loc[tr, "latent"]])
        b, *_ = np.linalg.lstsq(A, D.loc[tr, "tmove"], rcond=None)
        D.loc[te, "m"] = (b[0] + b[1] * D.loc[te, "pred_move"]
                          + b[2] * D.loc[te, "latent"])
        if yr == 2025:
            print(f"  2025-26 combiner (trained through 2024-25): "
                  f"a {b[0]:+.4f}  ridge {b[1]:+.4f}  latent {b[2]:+.4f}")
    return D.dropna(subset=["m"])


def cluster_t(vals, groups):
    per = pd.Series(vals).groupby(pd.Series(groups)).mean()
    return per.mean(), per.mean() / (per.std(ddof=1) / np.sqrt(len(per))), \
        len(per)


def main():
    D = build_signal()
    S = D[D["season"] == 2025].copy()
    print(f"  2025-26 games with a frozen OOS signal: {len(S):,}   "
          f"m sd {S['m'].std():.3f}")

    # Kalshi tip surface
    u = KC.load()
    u = u[~((u["bid"] <= 0) & (u["ask"] >= 1.0))]
    u = u[u["bucket"] == "regular"]
    fits, rungs = [], []
    for ev, gg in u.groupby("event_ticker"):
        f = KC.fit_ladder(gg)
        if f:
            fits.append({"k": gg["k"].iloc[0], "mu": f[0], "sd": f[1]})
            rungs.append(gg[["k", "floor_strike", "mid"]])
    F = pd.DataFrame(fits)
    R = pd.concat(rungs)

    mp = pd.read_csv("team_mapping.csv").set_index(
        "bigdataball_name")["abbr"].to_dict()
    S["H"], S["A"] = S["home"].map(mp), S["away"].map(mp)
    mk = lambda d, a, b: (d.dt.strftime("%Y-%m-%d") + "|"
                          + np.where(a < b, a, b) + "-"
                          + np.where(a < b, b, a))
    S["k"] = mk(S["date"], S["H"].values, S["A"].values)
    G = S.merge(F, on="k", how="inner")
    print(f"  matched to a fitted Kalshi ladder: {len(G):,} games")

    print("\n" + "=" * 92)
    print("A1 — GAME LEVEL: does the frozen signal forecast the exchange "
          "surface's position?")
    print("=" * 92)
    for y, nm, expect in (
            (G["mu"] - G["ot_open"], "mu_Kalshi - OPEN  (exchange CLV)",
             "positive slope"),
            (G["mu"] - G["ot_close"], "mu_Kalshi - CLOSE (residual)",
             "~0"),
            (G["tmove"], "book close - open  (reference)", "positive")):
        A = np.column_stack([np.ones(len(G)), G["m"]])
        b, *_ = np.linalg.lstsq(A, y, rcond=None)
        r = y - A @ b
        se = np.sqrt(np.diag(np.linalg.pinv(A.T @ A)) * (r @ r)
                     / (len(G) - 2))
        cr = np.corrcoef(G["m"], y)[0, 1]
        # date-cluster check
        res = pd.DataFrame({"d": G["date"].dt.date,
                            "x": G["m"] - G["m"].mean(), "y": y})
        num = res.groupby("d").apply(lambda s: (s.x * s.y).sum())
        den = res.groupby("d").apply(lambda s: (s.x ** 2).sum())
        bd = num.sum() / den.sum()
        u_d = res.groupby("d").apply(
            lambda s: (s.x * (s.y - bd * s.x)).sum())
        se_d = np.sqrt((u_d ** 2).sum()) / den.sum()
        print(f"  {nm:34} slope {b[1]:+.4f} (t={b[1]/se[1]:+.2f}; "
              f"date-clustered t={bd/se_d:+.2f})   corr {cr:+.4f}   "
              f"[{expect}]")

    print("\n" + "=" * 92)
    print("A3 — COHERENCE: location shift, not scale shift")
    print("=" * 92)
    for x, nm in ((G["m"], "sd_Kalshi ~ m"), (G["m"].abs(),
                                              "sd_Kalshi ~ |m|")):
        A = np.column_stack([np.ones(len(G)), x])
        b, *_ = np.linalg.lstsq(A, G["sd"], rcond=None)
        r = G["sd"] - A @ b
        se = np.sqrt(np.diag(np.linalg.pinv(A.T @ A)) * (r @ r)
                     / (len(G) - 2))
        print(f"  {nm:18} slope {b[1]:+.4f} (t={b[1]/se[1]:+.2f})"
              f"   [expect ~0]")

    print("\n" + "=" * 92)
    print("RUNG-LEVEL SYNTHETIC REPRICING VALUE (counterfactual; cents, "
          "game-clustered)")
    print("=" * 92)
    RR = R.merge(G[["k", "m", "ot_open", "sd"]], on="k", how="inner")
    RR["p_ref"] = 1.0 - norm.cdf(
        (RR["floor_strike"] - RR["ot_open"]) / RR["sd"])
    RR["mtm"] = np.sign(RR["m"]) * (RR["mid"] - RR["p_ref"])
    print(f"  {len(RR):,} rungs on {RR['k'].nunique():,} games")
    print(f"  {'|m| >=':>8}{'games':>7}{'rungs':>8}{'mean SRV c':>12}"
          f"{'game-clust t':>14}{'% rungs +':>11}")
    for thr in GRID:
        s = RR[RR["m"].abs() >= thr]
        if s["k"].nunique() < 25:
            continue
        mu, t, ng = cluster_t(s["mtm"].values, s["k"].values)
        print(f"  {thr:>8.1f}{ng:>7,}{len(s):>8,}{100*mu:>12.2f}"
              f"{t:>14.2f}{100*(s['mtm']>0).mean():>10.1f}%")

    print("\n" + "=" * 92)
    print("RUNG SENSITIVITY — analytic cents per 1-point location shift "
          "(a-priori, not P&L-picked)")
    print("=" * 92)
    RR["z"] = (RR["floor_strike"] - RR["ot_open"]) / RR["sd"]
    RR["sens"] = norm.pdf(RR["z"]) / RR["sd"]
    RR["zb"] = pd.cut(RR["z"].abs(), [0, 0.25, 0.5, 0.75, 1.0, 1.5, 9])
    t = RR.groupby("zb", observed=True).agg(
        n=("sens", "size"), cents_per_pt=("sens", "mean"),
        mean_srv=("mtm", "mean"))
    t["cents_per_pt"] *= 100
    t["mean_srv"] *= 100
    print(t.round(2).to_string())
    print("\n  centre rungs carry ~2x the sensitivity of |z|>1 rungs; the")
    print("  extreme-price contracts the Polymarket paper flags as loss-"
          "associated")
    print("  are also the LEAST useful expression of a location forecast.")


if __name__ == "__main__":
    main()
