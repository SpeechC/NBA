"""Overtime hypothesis — Part I magnitude and coverage audit ONLY.

No modelling. This report is the gate that decides whether the hypothesis is
worth pursuing, and it deliberately stops there.

went_overtime is taken from the presence of OT-period scoring columns
(OT1..OT5), never inferred from the final margin.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

from prepare_data import CSV, season_label

OTC = [f"OT{i}_{s}" for i in range(1, 6) for s in ("H", "R")]


def build():
    raw = pd.read_csv(CSV, low_memory=False)
    raw["lbl"] = season_label(raw).astype(str)
    d = raw[raw["lbl"].str.contains("Regular Season", na=False)].copy()
    n = lambda c: pd.to_numeric(d[c], errors="coerce")
    d["date"] = pd.to_datetime(d["DATE"], errors="coerce")
    d["yr"] = d["lbl"].str.extract(r"(\d{4})")[0].astype(int)
    d["gid"] = d["GAME-ID"].astype(str).str.strip()
    d["closing_total"] = n("CLOSING TOTAL_H")
    d["opening_total"] = n("OPENING TOTAL_H")
    d["closing_spread"] = n("CLOSING SPREAD_H")
    for s in ("H", "R"):
        for q in (1, 2, 3, 4):
            d[f"q{q}_{s}"] = n(f"{q}Q_{s}")
        d[f"reg_{s}"] = sum(d[f"q{q}_{s}"] for q in (1, 2, 3, 4))
        d[f"ot_{s}"] = sum(n(f"OT{i}_{s}").fillna(0) for i in range(1, 6))
        d[f"final_{s}"] = n(f"F_{s}")
        d[f"h1_{s}"] = d[f"q1_{s}"] + d[f"q2_{s}"]
    d["n_ot"] = sum((n(f"OT{i}_H").fillna(0) + n(f"OT{i}_R").fillna(0)) > 0
                    for i in range(1, 6))
    d["went_overtime"] = (d["n_ot"] > 0).astype(int)
    d["regulation_total"] = d["reg_H"] + d["reg_R"]
    d["final_total"] = d["final_H"] + d["final_R"]
    d["ot_points"] = d["final_total"] - d["regulation_total"]
    d["h1_total"] = d["h1_H"] + d["h1_R"]
    d["h1_margin"] = d["h1_H"] - d["h1_R"]
    d["reg_margin"] = d["reg_H"] - d["reg_R"]
    return d


def main():
    d = build()
    s = d.dropna(subset=["final_total", "regulation_total"])
    print("=" * 96)
    print("IDENTITY AND COVERAGE CHECKS")
    print("=" * 96)
    id_ok = np.isclose(s["reg_H"] + s["ot_H"], s["final_H"]) & \
        np.isclose(s["reg_R"] + s["ot_R"], s["final_R"])
    print(f"  regulation + OT == final, both sides: "
          f"{100*id_ok.mean():.2f}% of {len(s):,} games")
    tie = s["reg_margin"] == 0
    print(f"  regulation tie <-> went_overtime agreement: "
          f"{100*(tie == (s['went_overtime'] == 1)).mean():.2f}%")
    print(f"  OT games with ot_points == 0: "
          f"{int(((s['went_overtime']==1) & (s['ot_points']==0)).sum())}")
    print(f"  non-OT games with ot_points != 0: "
          f"{int(((s['went_overtime']==0) & (s['ot_points']!=0)).sum())}")
    print(f"  halftime quarter scores present: "
          f"{100*s['h1_total'].notna().mean():.2f}%")
    print(f"  HALFTIME_H column agrees with q1+q2: "
          f"{100*np.isclose(pd.to_numeric(s['HALFTIME_H'],errors='coerce'), s['h1_H']).mean():.2f}%")

    print("\n  by season")
    t = s.groupby("yr").agg(
        games=("gid", "size"), ot=("went_overtime", "sum"),
        multi=("n_ot", lambda v: int((v >= 2).sum())),
        mean_ot_pts=("ot_points", lambda v: np.nan))
    t["OT %"] = (100 * t["ot"] / t["games"]).round(2)
    t["multi %"] = (100 * t["multi"] / t["games"]).round(2)
    otg = s[s["went_overtime"] == 1]
    t["mean OT pts"] = otg.groupby("yr")["ot_points"].mean().round(2)
    t["med OT pts"] = otg.groupby("yr")["ot_points"].median()
    print(t[["games", "ot", "OT %", "multi", "multi %",
             "mean OT pts", "med OT pts"]].to_string())

    mo = otg["ot_points"].mean()
    print(f"\n  OT-point distribution (conditional on OT, n={len(otg):,})")
    qs = otg["ot_points"].quantile([.05, .25, .5, .75, .95]).round(1)
    print(f"    mean {mo:.2f}  sd {otg['ot_points'].std():.2f}  "
          f"p5 {qs.iloc[0]:.0f}  p25 {qs.iloc[1]:.0f}  med {qs.iloc[2]:.0f}  "
          f"p75 {qs.iloc[3]:.0f}  p95 {qs.iloc[4]:.0f}  "
          f"max {otg['ot_points'].max():.0f}")
    print(f"    n_OT periods: "
          + "  ".join(f"{k}:{v}" for k, v in
                      otg["n_ot"].value_counts().sort_index().items()))

    print("\n" + "=" * 96)
    print("MAGNITUDE GATE — fair-total value of an OT-probability error")
    print(f"  FairAdjustment = dP(OT) x E[OT points | OT] = dP x {mo:.2f}")
    print("=" * 96)
    for dp in (0.005, 0.01, 0.02, 0.03, 0.05):
        print(f"    +{100*dp:>4.1f} pp  ->  {dp*mo:+.3f} points")
    print(f"\n  unconditional OT premium in the total: "
          f"{s['went_overtime'].mean()*mo:.3f} points "
          f"({100*s['went_overtime'].mean():.2f}% x {mo:.2f})")

    print("\n" + "=" * 96)
    print("BASELINE OT RATE BY |CLOSING SPREAD|  (frozen buckets)")
    print("=" * 96)
    x = s.dropna(subset=["closing_spread"]).copy()
    x["absp"] = x["closing_spread"].abs()
    bins = [0, 1.5, 3.5, 5.5, 7.5, 10.5, 14.5, 100]
    x["b"] = pd.cut(x["absp"], bins, right=False)
    g = x.groupby("b", observed=True).agg(n=("gid", "size"),
                                          ot=("went_overtime", "mean"))
    g["OT %"] = (100 * g["ot"]).round(2)
    g["premium pts"] = (g["ot"] * mo).round(3)
    print(g[["n", "OT %", "premium pts"]].to_string())

    print("\n" + "=" * 96)
    print("BASELINE OT RATE BY |HALFTIME MARGIN|  (frozen buckets)")
    print("=" * 96)
    y = s.dropna(subset=["h1_margin"]).copy()
    y["absm"] = y["h1_margin"].abs()
    b2 = [0, 2, 4, 6, 9, 12, 16, 100]
    y["b"] = pd.cut(y["absm"], b2, right=False)
    g2 = y.groupby("b", observed=True).agg(n=("gid", "size"),
                                           ot=("went_overtime", "mean"))
    g2["OT %"] = (100 * g2["ot"]).round(2)
    g2["premium pts"] = (g2["ot"] * mo).round(3)
    print(g2[["n", "OT %", "premium pts"]].to_string())
    spread_disp = g["ot"].max() - g["ot"].min()
    ht_disp = g2["ot"].max() - g2["ot"].min()
    print(f"\n  achievable premium SPREAD across |closing spread| buckets: "
          f"{spread_disp*mo:.3f} points")
    print(f"  achievable premium SPREAD across |H1 margin| buckets:      "
          f"{ht_disp*mo:.3f} points")

    print("\n" + "=" * 96)
    print("TEAM OT PERSISTENCE — is the data even sufficient to estimate it?")
    print("=" * 96)
    rows = []
    for side in ("H", "R"):
        rows.append(pd.DataFrame({"yr": s["yr"], "team": s[f"TEAM_{side}"],
                                  "ot": s["went_overtime"]}))
    P = pd.concat(rows)
    per = P.groupby(["yr", "team"])["ot"].agg(["sum", "size"]).reset_index()
    print(f"  team-seasons: {len(per):,}   median OT games per team-season: "
          f"{per['sum'].median():.0f}   mean {per['sum'].mean():.2f}")
    print(f"  a team-season carries ~{per['size'].median():.0f} games, so the "
          f"binomial SE on a team's OT rate is "
          f"{np.sqrt(0.06*0.94/per['size'].median()):.4f} "
          f"({100*np.sqrt(0.06*0.94/per['size'].median()):.2f} pp)")
    per["nxt"] = per["yr"] + 1
    j = per.merge(per, left_on=["team", "nxt"], right_on=["team", "yr"],
                  suffixes=("_t", "_n"))
    j["r_t"] = j["sum_t"] / j["size_t"]
    j["r_n"] = j["sum_n"] / j["size_n"]
    r = np.corrcoef(j["r_t"], j["r_n"])[0, 1]
    tt = r * np.sqrt(len(j) - 2) / np.sqrt(1 - r * r)
    print(f"  RAW season-to-season team OT-rate correlation: {r:+.4f} "
          f"(t={tt:+.2f}, n={len(j)} pairs)   [uncontrolled, descriptive]")
    v_obs = per["ot" if "ot" in per else "sum"].div(per["size"]).var(ddof=1)
    p_bar = per["sum"].sum() / per["size"].sum()
    v_noise = p_bar * (1 - p_bar) / per["size"].mean()
    print(f"  cross-team variance of season OT rate {v_obs:.6f} vs "
          f"binomial-noise variance {v_noise:.6f}   "
          f"implied true SD {np.sqrt(max(v_obs-v_noise,0)):.4f} "
          f"({100*np.sqrt(max(v_obs-v_noise,0)):.2f} pp)")

    print("\n" + "=" * 96)
    print("MARKET-DATA AUDIT — halftime LIVE full-game total")
    print("=" * 96)
    print("  searched /mnt/c/NBA and /mnt/c/NBA2:")
    print("    nba_draftkings_totals_historical.csv  967 rows, 2023-24 only")
    print("      -> full_game_total_open/close and h1_total_open/close.")
    print("         These are PREGAME markets: the full-game total is the")
    print("         pregame close, the h1 total is the pregame first-half")
    print("         line. Neither is a halftime live price.")
    print("    nba_draftkings_halves_historical.csv    5 rows, market_key")
    print("      = 'totals_h1', market_scope = 'game_total', period = 'H1'")
    print("      -> pregame first-half totals again, and essentially empty.")
    print("    nba_oddsapi_events.csv                 34 rows, event metadata")
    print("      only, no prices.")
    print("\n  historical halftime live FG total available? ......... NO")
    print("  rows / seasons / books ............................... 0 / - / -")


if __name__ == "__main__":
    main()
