"""HIGH/LOW referee games: realized effects, market residuals, and the
walk-forward economics of the frozen CrewShock rule.

Nothing frozen is altered. The HIGH/LOW groups are the development-frozen
9 + 9 identities; the trading rule is the already-frozen CrewShock Q85.
HIGH/LOW group economics are mechanism diagnostics, not a new strategy.

CrewShock in ref_features.csv is strictly prior-only by construction: each
official's effect at game t uses only that official's games strictly before t.
The Q85 threshold was frozen on development and applied unchanged to holdout,
so betting on it is genuinely walk-forward.

Staking convention reproduced from ref_final.py: flat $100 risk at -110,
win +$90.91, loss -$100.00, push $0.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import crew_team_diag as ctd
import foul_types
import refs
from data_split import SPLIT_DATE
from ref_game_contrast import frozen_groups, label

ADVF = "/mnt/c/NBA2/advanced_stats/game_advanced_stats.csv"
THR = 0.8682
STAKE, WIN = 100.0, 100.0 * 100.0 / 110.0
NPERM = 2000
BLOCK_DAYS = 7
RNG = np.random.default_rng(161803)


def build():
    g = ctd.build()
    g["gid"] = g["gid"].astype(str).str.strip()
    need = ["h_f_OEFF", "a_f_OEFF", "h_f_DEFF", "a_f_DEFF", "h_f_PACE",
            "a_f_PACE", "h_f_FTA", "a_f_FTA", "h_f_FT%", "a_f_FT%", "h_f_3PA",
            "a_f_3PA", "h_f_TOV", "a_f_TOV", "h_f_ORB", "a_f_ORB", "FD_h",
            "FD_a", "FC_h", "FC_a", "open_total", "total", "spread",
            "abs_spread", "LeagueFoulState", "pace_sum", "mu_state", "oeff_s",
            "deff_s", "ftr_s", "tpa_s", "M", "pace_s", "implied_minus_open"]
    g = g.dropna(subset=need + ["ref1", "ref2", "ref3"]).copy()

    m = refs.build()
    m["gid"] = m["GAME-ID"].astype(str).str.strip()
    n = lambda c: pd.to_numeric(m[c], errors="coerce")
    R = pd.DataFrame({"gid": m["gid"].values})
    for nm, hc, ac in (("PTS", "PTS_H", "PTS_R"), ("Fouls", "PF_H", "PF_R"),
                       ("FTA", "FTA_H", "FTA_R"), ("FTM", "FT_H", "FT_R"),
                       ("FGA", "FGA_H", "FGA_R"), ("FGM", "FG_H", "FG_R"),
                       ("FG3M", "3P_H", "3P_R"), ("Poss", "POSS_H", "POSS_R"),
                       ("Pace", "PACE_H", "PACE_R"), ("OEFF", "OEFF_H", "OEFF_R")):
        R[f"{nm}_H"], R[f"{nm}_A"] = n(hc).values, n(ac).values
    adv = pd.read_csv(ADVF, low_memory=False)
    adv["gid"] = adv["GAME-ID"].astype(str).str.strip()
    adv["pf_rate"] = (pd.to_numeric(adv["ADV_PF_PER100_OPP_POSS_H"],
                                    errors="coerce")
                      + pd.to_numeric(adv["ADV_PF_PER100_OPP_POSS_R"],
                                      errors="coerce"))
    R = R.merge(adv[["gid", "pf_rate"]], on="gid", how="left")
    F = foul_types.build()
    F["gidz"] = F["gid"].astype(str).str.zfill(10)
    R["gidz"] = R["gid"].str.zfill(10)
    R = R.merge(F[["gidz", "defensive_fouls", "offensive_fouls"]], on="gidz",
                how="left").drop(columns="gidz")

    s = g[["gid", "yr", "date", "ref1", "ref2", "ref3", "open_total", "total",
           "actual", "e", "TEAM_H", "TEAM_R"]].merge(R, on="gid", how="inner")
    s["total_fouls"] = s["Fouls_H"] + s["Fouls_A"]
    s["total_FTA"] = s["FTA_H"] + s["FTA_A"]
    s["total_FTM"] = s["FTM_H"] + s["FTM_A"]
    s["total_FGA"] = s["FGA_H"] + s["FGA_A"]
    s["FGM"] = s["FGM_H"] + s["FGM_A"]
    s["FG3M"] = s["FG3M_H"] + s["FG3M_A"]
    s["FG2M"] = s["FGM"] - s["FG3M"]
    s["ftpct"] = s["total_FTM"] / s["total_FTA"].replace(0, np.nan)
    s["poss"] = s["Poss_H"]
    s["pace"] = s["Pace_H"]
    s["oeff"] = (s["OEFF_H"] + s["OEFF_A"]) / 2
    s["total_points"] = s["PTS_H"] + s["PTS_A"]
    s["open_resid"] = s["actual"] - s["open_total"]
    s["close_resid"] = s["actual"] - s["total"]
    return s.drop_duplicates("gid").reset_index(drop=True)


def classify(crew, HIGH, LOW):
    nH = np.isin(crew, list(HIGH)).sum(1)
    nL = np.isin(crew, list(LOW)).sum(1)
    return np.where((nH >= 1) & (nL == 0), "HIGH",
                    np.where((nL >= 1) & (nH == 0), "LOW",
                             np.where((nH >= 1) & (nL >= 1), "MIXED",
                                      "NEUTRAL")))


def pnl(g, line_col):
    a = g["actual"].values
    p = g[line_col].values
    w = int((a > p).sum())
    l = int((a < p).sum())
    pu = int((a == p).sum())
    money = w * WIN - l * STAKE
    wp = 100 * w / (w + l) if w + l else np.nan
    roi = 100 * money / (STAKE * (w + l)) if w + l else np.nan
    return w, l, pu, wp, money, roi


def main():
    s = build()
    HIGH, LOW, q85r, q15r = frozen_groups(set(s["gid"]))
    assert len(HIGH) == 9 and len(LOW) == 9, (len(HIGH), len(LOW))
    grp = classify(s[["ref1", "ref2", "ref3"]].values, HIGH, LOW)
    s["grp"] = grp
    nHI, nLO = int((grp == "HIGH").sum()), int((grp == "LOW").sum())
    print(f"  HIGH games {nHI:,}   LOW games {nLO:,}   "
          f"MIXED {int((grp=='MIXED').sum()):,}   "
          f"NEUTRAL {int((grp=='NEUTRAL').sum()):,}")
    assert nHI == 1374 and nLO == 1465, "group counts do not reproduce"
    print("  counts reproduce the prior run exactly")
    hi, lo = grp == "HIGH", grp == "LOW"

    print("\n" + "=" * 92)
    print("PART A — REALIZED BASKETBALL DECOMPOSITION")
    print("=" * 92)
    rows = []
    for c, nm in (("total_fouls", "Total fouls"),
                  ("defensive_fouls", "Defensive fouls"),
                  ("offensive_fouls", "Offensive fouls"),
                  ("pf_rate", "Fouls/100 poss"), ("total_FTA", "FTA"),
                  ("total_FTM", "FTM"), ("ftpct", "FT%"),
                  ("total_FGA", "FGA"), ("FG2M", "2PM"), ("FG3M", "3PM"),
                  ("FGM", "FGM"), ("poss", "Possessions"), ("pace", "Pace"),
                  ("oeff", "OEFF"), ("total_points", "Total points")):
        v = s[c].values
        ok = ~np.isnan(v)
        a, b = v[hi & ok], v[lo & ok]
        p = np.sqrt((a.std(ddof=1) ** 2 + b.std(ddof=1) ** 2) / 2)
        rows.append({"Variable": nm, "HIGH mean": a.mean(), "LOW mean": b.mean(),
                     "HIGH-LOW": a.mean() - b.mean(),
                     "SMD": (a.mean() - b.mean()) / p if p else 0.0})
    A = pd.DataFrame(rows)
    print(f"  {'Variable':18}{'HIGH mean':>11}{'LOW mean':>11}"
          f"{'HIGH-LOW':>11}{'SMD':>9}")
    for _, r in A.iterrows():
        print(f"  {r['Variable']:18}{r['HIGH mean']:11.4f}{r['LOW mean']:11.4f}"
              f"{r['HIGH-LOW']:11.4f}{r['SMD']:9.4f}")
    d = dict(zip(A["Variable"], A["HIGH-LOW"]))
    chk = [("Total fouls", 2.66), ("FTA", 3.00), ("FTM", 2.21),
           ("Total points", 0.51)]
    print("\n  reproduction check against the prior run")
    for k_, exp in chk:
        print(f"    {k_:16} expected ~{exp:+.2f}   observed {d[k_]:+.2f}   "
              f"{'OK' if abs(d[k_]-exp) < 0.25 else 'MISMATCH'}")

    print("\n" + "=" * 92)
    print("SCORING ACCOUNTING IDENTITY   Points = 2*2PM + 3*3PM + FTM")
    print("=" * 92)
    fg_pts = 2 * d["2PM"] + 3 * d["3PM"]
    recon = fg_pts + d["FTM"]
    print(f"  HIGH-LOW 2PM                    {d['2PM']:+.4f}")
    print(f"  HIGH-LOW 3PM                    {d['3PM']:+.4f}")
    print(f"  field-goal point difference     {fg_pts:+.4f}"
          f"   = 2*({d['2PM']:+.4f}) + 3*({d['3PM']:+.4f})")
    print(f"  HIGH-LOW FTM                    {d['FTM']:+.4f}")
    print(f"  reconstructed point difference  {recon:+.4f}")
    print(f"  observed point difference       {d['Total points']:+.4f}")
    print(f"  identity error                  {recon - d['Total points']:+.6f}")
    print(f"\n  of {d['FTM']:+.2f} extra free-throw points, "
          f"{-fg_pts:+.2f} is given back in field-goal scoring "
          f"({100*(-fg_pts)/d['FTM']:.0f}% offset)")
    pd.DataFrame({"component": ["2PM", "3PM", "FG points", "FTM",
                                "reconstructed", "observed", "error"],
                  "HIGH_minus_LOW": [d["2PM"], d["3PM"], fg_pts, d["FTM"],
                                     recon, d["Total points"],
                                     recon - d["Total points"]]}
                 ).to_csv("ref_high_low_scoring_accounting.csv", index=False)

    print("\n" + "=" * 92)
    print("PART B — MARKET-RELATIVE SCORING")
    print("=" * 92)
    print(f"  {'':24}{'HIGH refs':>12}{'LOW refs':>12}{'HIGH-LOW':>12}")
    mk = []
    for c, nm in (("actual", "Actual total"), ("open_total", "Opening total"),
                  ("total", "Closing total"), ("open_resid", "Actual - opening"),
                  ("close_resid", "Actual - closing")):
        a, b = s.loc[hi, c].mean(), s.loc[lo, c].mean()
        print(f"  {nm:24}{a:12.4f}{b:12.4f}{a-b:12.4f}")
        mk.append({"metric": nm, "HIGH": a, "LOW": b, "diff": a - b})
    for c, nm in (("open_resid", "opening"), ("close_resid", "closing")):
        ah = 100 * (s.loc[hi, c] > 0).mean()
        al = 100 * (s.loc[lo, c] > 0).mean()
        ph = 100 * (s.loc[hi, c] == 0).mean()
        pl = 100 * (s.loc[lo, c] == 0).mean()
        print(f"  {'Over % vs ' + nm:24}{ah:12.2f}{al:12.2f}{ah-al:12.2f}")
        print(f"  {'Push % vs ' + nm:24}{ph:12.2f}{pl:12.2f}{ph-pl:12.2f}")
        mk.append({"metric": f"Over% vs {nm}", "HIGH": ah, "LOW": al,
                   "diff": ah - al})
    pd.DataFrame(mk).to_csv("ref_high_low_market.csv", index=False)

    print("\n  by window and season")
    print(f"  {'season':10}{'HIGH n':>7}{'LOW n':>7}{'HIGH resid':>12}"
          f"{'LOW resid':>11}{'HIGH-LOW':>10}{'HIGH ov%':>10}{'LOW ov%':>9}")
    dv = (s["date"] < SPLIT_DATE).values
    for lab, m_ in (("development", dv), ("holdout", ~dv), ("POOLED", np.ones(len(s), bool))):
        a, b = s[hi & m_], s[lo & m_]
        print(f"  {lab:10}{len(a):7,}{len(b):7,}{a['close_resid'].mean():12.4f}"
              f"{b['close_resid'].mean():11.4f}"
              f"{a['close_resid'].mean()-b['close_resid'].mean():10.4f}"
              f"{100*(a['close_resid']>0).mean():10.2f}"
              f"{100*(b['close_resid']>0).mean():9.2f}")
    for y in sorted(s["yr"].unique()):
        m_ = (s["yr"] == y).values
        a, b = s[hi & m_], s[lo & m_]
        print(f"  {int(y):<10}{len(a):7,}{len(b):7,}{a['close_resid'].mean():12.4f}"
              f"{b['close_resid'].mean():11.4f}"
              f"{a['close_resid'].mean()-b['close_resid'].mean():10.4f}"
              f"{100*(a['close_resid']>0).mean():10.2f}"
              f"{100*(b['close_resid']>0).mean():9.2f}")

    print("\n" + "=" * 92)
    print("TIME-LOCAL PERMUTATION on the residual contrast")
    print("=" * 92)
    crew = s[["ref1", "ref2", "ref3"]].values
    blk = (s["yr"].astype(str) + "_"
           + ((s["date"] - s.groupby("yr")["date"].transform("min"))
              .dt.days // BLOCK_DAYS).astype(str)).values
    blocks = [np.where(blk == b)[0] for b in pd.unique(blk)]
    obs = {c: s.loc[hi, c].mean() - s.loc[lo, c].mean()
           for c in ("close_resid", "open_resid")}
    null = {c: np.empty(NPERM) for c in obs}
    for j in range(NPERM):
        perm = crew.copy()
        for b in blocks:
            if len(b) > 1:
                perm[b] = crew[b][RNG.permutation(len(b))]
        gg = classify(perm, HIGH, LOW)
        h2, l2 = gg == "HIGH", gg == "LOW"
        for c in obs:
            null[c][j] = s.loc[h2, c].mean() - s.loc[l2, c].mean()
    for c, nm in (("close_resid", "CLOSING"), ("open_resid", "OPENING")):
        o, n_ = obs[c], null[c]
        z = (o - n_.mean()) / n_.std()
        p1 = (1 + (n_ >= o).sum()) / (NPERM + 1)
        p2 = (1 + (np.abs(n_ - n_.mean()) >= abs(o - n_.mean())).sum()) / (NPERM + 1)
        print(f"  {nm:8} observed HIGH-LOW {o:+.4f}   null mean {n_.mean():+.4f}"
              f"  sd {n_.std():.4f}   z={z:+.2f}   "
              f"one-sided p={p1:.4f}   two-sided p={p2:.4f}")

    print("\n" + "=" * 92)
    print("PART C — WALK-FORWARD FROZEN CrewShock Q85")
    print("=" * 92)
    full = refs.build()
    full["gid"] = full["GAME-ID"].astype(str).str.strip()
    n2 = lambda c: pd.to_numeric(full[c], errors="coerce")
    full["open_total"] = n2("OPENING TOTAL_H")
    f2 = pd.read_csv("ref_features.csv")
    f2["gid"] = f2["gid"].astype(str).str.strip()
    full = full.merge(f2[["gid", "CrewShock"]], on="gid", how="inner").dropna(
        subset=["CrewShock", "actual", "total"])
    print(f"  threshold recovered from the frozen files: CrewShock >= {THR:+.4f}")
    print(f"  staking: flat ${STAKE:.0f} risk at -110  "
          f"(win +${WIN:.2f}, loss -${STAKE:.0f}, push $0)")
    b = full[full["CrewShock"] >= THR].sort_values("date").reset_index(drop=True)
    print(f"  qualifying games: {len(b):,}")

    print(f"\n  {'season':10}{'bets':>6}{'W':>5}{'L':>5}{'P':>4}{'win %':>8}"
          f"{'$ won':>10}{'ROI %':>8}{'cum $':>11}")
    cum = 0.0
    for y, g_ in b.groupby("yr"):
        w, l, pu, wp, money, roi = pnl(g_, "total")
        cum += money
        tag = "" if y < 2024 else "  <- holdout"
        print(f"  {int(y):<10}{len(g_):6,}{w:5}{l:5}{pu:4}{wp:8.2f}"
              f"{money:10,.0f}{roi:8.2f}{cum:11,.0f}{tag}")
    print()
    hold_m = b["date"] >= SPLIT_DATE
    for lab, g_ in (("DEVELOPMENT", b[~hold_m]), ("HOLDOUT", b[hold_m]),
                    ("POOLED", b)):
        w, l, pu, wp, money, roi = pnl(g_, "total")
        print(f"  {lab:12} bets {len(g_):5,}  W {w:4}  L {l:4}  P {pu:3}  "
              f"win {wp:6.2f}%  ${money:9,.0f}  ROI {roi:6.2f}%")

    b["profit"] = np.where(b["actual"] > b["total"], WIN,
                           np.where(b["actual"] < b["total"], -STAKE, 0.0))
    b["cum"] = b["profit"].cumsum()
    b["result"] = np.where(b["actual"] > b["total"], "W",
                           np.where(b["actual"] < b["total"], "L", "P"))
    out = b[["date", "gid", "TEAM_H", "TEAM_R", "CrewShock", "total", "actual",
             "result", "profit", "cum", "yr"]].rename(
        columns={"gid": "game_id", "total": "posted_total",
                 "actual": "actual_total", "cum": "cumulative_profit",
                 "yr": "season"})
    out.to_csv("crewshock_walkforward_bets.csv", index=False)
    run = b["result"].values
    def streak(ch):
        best = cur = 0
        for r in run:
            if r == ch:
                cur += 1; best = max(best, cur)
            elif r != "P":
                cur = 0
        return best
    dd = (b["cum"].cummax() - b["cum"]).max()
    print(f"\n  max cumulative ${b['cum'].max():,.0f}   "
          f"min cumulative ${b['cum'].min():,.0f}   "
          f"max drawdown ${dd:,.0f}")
    print(f"  longest winning streak {streak('W')}   "
          f"longest losing streak {streak('L')}")

    print("\n  OPENING vs CLOSING grading of the same qualifying games")
    bo = b.dropna(subset=["open_total"])
    print(f"  {'':10}{'bets':>7}{'win %':>8}{'$ won':>10}{'ROI %':>8}"
          f"{'mean Actual-Line':>18}")
    for lab, col in (("OPEN", "open_total"), ("CLOSE", "total")):
        w, l, pu, wp, money, roi = pnl(bo, col)
        print(f"  {lab:10}{len(bo):7,}{wp:8.2f}{money:10,.0f}{roi:8.2f}"
              f"{(bo['actual']-bo[col]).mean():18.4f}")

    print("\n" + "=" * 92)
    print("HIGH / LOW REFEREE GROUP OVER ECONOMICS (diagnostic, not a strategy)")
    print("=" * 92)
    print(f"  {'group':22}{'bets':>7}{'win %':>8}{'$ won':>10}{'ROI %':>8}")
    econ = {}
    for gname, mask in (("HIGH-ref", hi), ("LOW-ref", lo)):
        for lab, m_ in (("Dev", dv), ("Holdout", ~dv),
                        ("Pooled", np.ones(len(s), bool))):
            g_ = s[mask & m_]
            w, l, pu, wp, money, roi = pnl(g_, "total")
            econ[(gname, lab)] = (len(g_), wp, money, roi)
            print(f"  {gname + ' ' + lab:22}{len(g_):7,}{wp:8.2f}"
                  f"{money:10,.0f}{roi:8.2f}")
    print(f"\n  HIGH minus LOW (pooled): win rate "
          f"{econ[('HIGH-ref','Pooled')][1]-econ[('LOW-ref','Pooled')][1]:+.2f}pp"
          f"   ROI {econ[('HIGH-ref','Pooled')][3]-econ[('LOW-ref','Pooled')][3]:+.2f}pp"
          f"   $/bet {econ[('HIGH-ref','Pooled')][2]/econ[('HIGH-ref','Pooled')][0] - econ[('LOW-ref','Pooled')][2]/econ[('LOW-ref','Pooled')][0]:+.2f}")

    print("\n" + "=" * 92)
    print("STRATEGY SUMMARY")
    print("=" * 92)
    print(f"  {'Strategy':34}{'Bets':>7}{'Win %':>8}{'$ Won':>10}{'ROI':>8}")
    srows = []
    for lab, g_ in (("Frozen CrewShock Q85 Dev", b[~hold_m]),
                    ("Frozen CrewShock Q85 Holdout", b[hold_m]),
                    ("Frozen CrewShock Q85 Pooled", b)):
        w, l, pu, wp, money, roi = pnl(g_, "total")
        print(f"  {lab:34}{len(g_):7,}{wp:8.2f}{money:10,.0f}{roi:8.2f}")
        srows.append({"strategy": lab, "bets": len(g_), "win_pct": round(wp, 2),
                      "dollars": round(money), "roi": round(roi, 2)})
    for gname, mask in (("HIGH-ref Over", hi), ("LOW-ref Over", lo)):
        for lab, m_ in (("Dev", dv), ("Holdout", ~dv),
                        ("Pooled", np.ones(len(s), bool))):
            g_ = s[mask & m_]
            w, l, pu, wp, money, roi = pnl(g_, "total")
            print(f"  {gname + ' ' + lab:34}{len(g_):7,}{wp:8.2f}"
                  f"{money:10,.0f}{roi:8.2f}")
            srows.append({"strategy": f"{gname} {lab}", "bets": len(g_),
                          "win_pct": round(wp, 2), "dollars": round(money),
                          "roi": round(roi, 2)})
    pd.DataFrame(srows).to_csv("crewshock_walkforward_summary.csv", index=False)
    print("\n  CrewShock Q85 is the frozen trading rule.")
    print("  HIGH/LOW referee groups are mechanism diagnostics; no new")
    print("  strategy is selected from them.")


if __name__ == "__main__":
    main()
