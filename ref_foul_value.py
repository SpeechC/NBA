"""Referee marginal scoring-value test.

CrewShock, LeagueFoulState and RefExposure = CrewShock * ExpPoss/100 are FROZEN
and loaded, never rebuilt.

  Stage 1  which offense receives the incremental whistles? -> freeze wH, wA
  Stage 2  RefFTValue = RefExposure * ExpectedFTPct, full chain, head to head
  Stage 3  replacement value: kappa from the development chain, lambda from
           foul mechanics in the play-by-play, then the anti-confound model

Prior-only FT% state recovered, window unaltered: walkforward.py LAG = 4,
h_f_FT% / a_f_FT% from symmetric_features.
"""
import glob
import os
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import ref_exposure as rex
import ref_shock as rsk
from data_split import SPLIT_DATE
from dispersion_priced import ols
from models_frozen import add_pace_terms
from symmetric_features import build as sym_build

CTRL = rsk.CTRL
THR = 0.8682
STAKE, WIN, BE = 100.0, 100.0 * 100.0 / 110.0, 110 / 210
PBP = "/mnt/c/NBA2/advanced_stats/pbp_rows"


def build():
    d = rex.build()
    G = add_pace_terms(sym_build())
    G["gid"] = G["gid"].astype(str).str.strip()
    G = G[["gid", "h_f_FT%", "a_f_FT%"]].dropna().drop_duplicates("gid")
    n0 = len(d)
    d = d.merge(G, on="gid", how="left")
    assert len(d) == n0
    nn = lambda c: pd.to_numeric(d[c], errors="coerce")
    d["pf_h"], d["pf_a"] = nn("PF_H"), nn("PF_R")
    d["ftm"] = nn("FT_H") + nn("FT_R")
    return d


def chain(x, var, links, lab):
    out = []
    for col, _ in links:
        X = np.column_stack([x[var], x["LeagueFoulState"]] + [x[c] for c in CTRL])
        b, se, t = ols(x[col].values, X)
        out.append((b[1], t[1]))
    return out


def main():
    d = build()
    core = ["CrewShock", "RefExposure", "ExpPoss", "LeagueFoulState", "e",
            "total", "actual", "fouls", "fta", "ftm", "pf_h", "pf_a",
            "h_f_FT%", "a_f_FT%"]
    s = d.dropna(subset=core + CTRL).copy()
    dev, hold = s[s["date"] < SPLIT_DATE], s[s["date"] >= SPLIT_DATE]
    print(f"  {len(s):,} games   develop {len(dev):,}   holdout {len(hold):,}")

    print("\n" + "=" * 100)
    print("STAGE 1 — which offense receives the incremental whistles?")
    print("  DEVELOPMENT ONLY. Mechanism diagnostic, not model selection.")
    print("=" * 100)
    co = {}
    for col, nm in (("pf_h", "fouls committed by HOME"),
                    ("pf_a", "fouls committed by AWAY")):
        X = np.column_stack([dev["RefExposure"], dev["LeagueFoulState"]]
                            + [dev[c] for c in CTRL])
        b, se, t = ols(dev[col].values, X)
        co[col] = b[1]
        print(f"    {nm:26} {b[1]:+.4f} (t={t[1]:+5.2f})")
    tot = co["pf_h"] + co["pf_a"]
    raw = (co["pf_h"] / tot, co["pf_a"] / tot)
    asym = abs(raw[0] - 0.5)
    print(f"    normalised split: home {raw[0]:.4f}  away {raw[1]:.4f}   "
          f"deviation from even {asym:.4f}")
    # A foul COMMITTED by the home team sends the AWAY offense to the line.
    if asym < 0.05:
        wH = wA = 0.5
        print(f"    approximately symmetric -> FROZEN wH = wA = 0.500")
    else:
        wH, wA = raw[1], raw[0]
        print(f"    materially asymmetric -> FROZEN wH = {wH:.4f}, wA = {wA:.4f}")
        print("    (a foul committed by HOME sends the AWAY offense to the line,")
        print("     so the weights are crossed)")

    s["ExpFTPct"] = wH * s["h_f_FT%"] + wA * s["a_f_FT%"]
    s["RefFTValue"] = s["RefExposure"] * s["ExpFTPct"]
    dev, hold = s[s["date"] < SPLIT_DATE], s[s["date"] >= SPLIT_DATE]

    print("\n" + "=" * 100)
    print("STAGE 2 — RefFTValue = RefExposure x ExpectedFTPct")
    print("=" * 100)
    print(f"  ExpFTPct mean {s['ExpFTPct'].mean():.4f}  sd {s['ExpFTPct'].std():.4f}"
          f"   ({100*s['ExpFTPct'].std()/s['ExpFTPct'].mean():.1f}% variation)")
    print(f"  corr(RefFTValue, CrewShock)   = "
          f"{np.corrcoef(s['RefFTValue'], s['CrewShock'])[0,1]:.6f}")
    print(f"  corr(RefFTValue, RefExposure) = "
          f"{np.corrcoef(s['RefFTValue'], s['RefExposure'])[0,1]:.6f}")
    print("  NOTE the FT% state is a LAG=4 window; with ~80 prior FTA its")
    print("  sampling SE is ~0.046 against a true team spread of ~0.031, so it")
    print("  is roughly 30% signal. The window is frozen and not altered.")

    LINKS = [("fta", "FTA"), ("ftm", "FTM"), ("actual", "ACTUAL TOTAL"),
             ("total", "CLOSING TOTAL"), ("e", "closing residual")]
    print(f"\n  THE CHAIN   Y ~ X + League + controls, identical rows")
    print(f"  {'link':18}" + "".join(f"{v:>26}" for v in
                                     ("CrewShock", "RefExposure", "RefFTValue")))
    for wlab, x in (("develop", dev), ("holdout", hold)):
        print(f"    [{wlab}]")
        for col, name in LINKS:
            cells = []
            for var in ("CrewShock", "RefExposure", "RefFTValue"):
                X = np.column_stack([x[var], x["LeagueFoulState"]]
                                    + [x[c] for c in CTRL])
                b, se, t = ols(x[col].values, X)
                cells.append(f"{b[1]:+11.4f} (t={t[1]:+5.2f})")
            print(f"    {name:18}" + "".join(f"{c:>26}" for c in cells))

    print("\n  c_true - c_market, identical rows")
    print(f"    {'window':9} {'variable':13} {'c_market':>10} {'c_true':>10} "
          f"{'gap':>9}")
    for wlab, x in (("develop", dev), ("holdout", hold), ("all", s)):
        for var in ("CrewShock", "RefExposure", "RefFTValue"):
            X = np.column_stack([x[var], x["LeagueFoulState"]]
                                + [x[c] for c in CTRL])
            bm, _, tm = ols(x["total"].values, X)
            bt, _, tt = ols(x["actual"].values, X)
            print(f"    {wlab:9} {var:13} {bm[1]:10.4f} {bt[1]:10.4f} "
                  f"{bt[1]-bm[1]:9.4f}")
        print()

    print("  season-by-season closing-residual coefficient")
    print(f"    {'season':8}" + "".join(f"{v:>14}" for v in
                                        ("CrewShock", "RefExposure", "RefFTValue")))
    for y, g in s.groupby("yr"):
        cells = []
        for var in ("CrewShock", "RefExposure", "RefFTValue"):
            X = np.column_stack([g[var], g["LeagueFoulState"]]
                                + [g[c] for c in CTRL])
            b, _, t = ols(g["e"].values, X)
            cells.append(f"{b[1]:+9.3f}")
        print(f"    {y:<8}" + "".join(f"{c:>14}" for c in cells))

    print("\n" + "=" * 100)
    print("STAGE 3 — replacement value")
    print("=" * 100)
    Xd = np.column_stack([dev["RefExposure"], dev["LeagueFoulState"]]
                         + [dev[c] for c in CTRL])
    bf, _, _ = ols(dev["fouls"].values, Xd)
    ba, _, _ = ols(dev["fta"].values, Xd)
    kappa = ba[1] / bf[1]
    print(f"  kappa = d(FTA)/d(raw fouls) on DEVELOPMENT chain = "
          f"{ba[1]:.4f} / {bf[1]:.4f} = {kappa:.4f} FTA per extra foul")

    lam, ok = foul_lambda()
    if not ok:
        print("  lambda not constructible -> stopping at RefFTValue")
        print("\n  CLASSIFICATION: REPLACEMENT_VALUE_NOT_IDENTIFIABLE")
        return
    print(f"  lambda from PBP foul mechanics (development only) = {lam:.4f}")
    print("    = share of foul events that terminate a possession in free")
    print("      throws with no field goal made, i.e. replace normal scoring")

    s["ExpPPP"] = s["oeff_s"] / 2.0 / 100.0
    s["FoulValue"] = kappa * s["ExpFTPct"] - lam * s["ExpPPP"]
    s["RefScoringShock"] = s["RefExposure"] * s["FoulValue"]
    dev, hold = s[s["date"] < SPLIT_DATE], s[s["date"] >= SPLIT_DATE]
    print(f"  FoulValue mean {s['FoulValue'].mean():.4f} "
          f"sd {s['FoulValue'].std():.4f}   "
          f"({100*s['FoulValue'].std()/abs(s['FoulValue'].mean()):.1f}% variation)")
    print(f"  corr(RefScoringShock, RefExposure) = "
          f"{np.corrcoef(s['RefScoringShock'], s['RefExposure'])[0,1]:.6f}")
    print(f"  corr(FoulValue, ExpPPP) = "
          f"{np.corrcoef(s['FoulValue'], s['ExpPPP'])[0,1]:+.4f}"
          "   [negative by construction]")

    print("\n  ANTI-CONFOUND — Residual ~ CrewShock + RefScoringShock")
    print("                            + ExpectedEfficiency + League + controls")
    for wlab, x in (("develop", dev), ("holdout", hold), ("all", s)):
        X = np.column_stack([x["CrewShock"], x["RefScoringShock"], x["ExpPPP"],
                             x["LeagueFoulState"]] + [x[c] for c in CTRL])
        b, se, t = ols(x["e"].values, X)
        print(f"    {wlab:9} bR {b[1]:+9.4f} (t={t[1]:+5.2f})   "
              f"bF {b[2]:+9.4f} (t={t[2]:+5.2f})   "
              f"bE {b[3]:+9.4f} (t={t[3]:+5.2f})")
    print("\n  and the corresponding realized / closing equations")
    for wlab, x in (("develop", dev), ("holdout", hold)):
        for tgt in ("actual", "total"):
            X = np.column_stack([x["CrewShock"], x["RefScoringShock"], x["ExpPPP"],
                                 x["LeagueFoulState"]] + [x[c] for c in CTRL])
            b, se, t = ols(x[tgt].values, X)
            print(f"    {wlab:9} {tgt:7} bF {b[2]:+9.4f} (t={t[2]:+5.2f})")

    print("\n" + "=" * 100)
    print("EQUAL-SELECTIVITY ECONOMICS — develop Q85 of each")
    print("=" * 100)
    print(f"  {'signal':17} {'window':9} {'bets':>6} {'win %':>7} {'$ won':>9} "
          f"{'ROI %':>7} {'mean e':>8}")
    for nm in ("CrewShock", "RefExposure", "RefFTValue", "RefScoringShock"):
        thr = THR if nm == "CrewShock" else dev[nm].quantile(0.85)
        for wlab, x in (("develop", dev), ("holdout", hold), ("all", s)):
            b = x[x[nm] >= thr]
            w = int((b["e"] > 0).sum())
            l = int((b["e"] < 0).sum())
            pnl = w * WIN - l * STAKE
            wp = 100 * w / (w + l) if w + l else np.nan
            roi = 100 * pnl / (STAKE * (w + l)) if w + l else np.nan
            print(f"  {nm:17} {wlab:9} {len(b):6,} {wp:7.2f} {pnl:9,.0f} "
                  f"{roi:7.2f} {b['e'].mean():8.3f}")
        print()


def foul_lambda():
    """Share of foul events that terminate a possession in free throws with no
    field goal made. Development seasons only. Pure foul mechanics -- no
    closing-residual or outcome fitting enters."""
    files = sorted(f for f in glob.glob(f"{PBP}/pbpstats_*_advanced.csv")
                   if "_po_" not in os.path.basename(f)
                   and not os.path.basename(f).endswith("2024_advanced.csv"))
    tot_term = 0
    for f in files:
        d = pd.read_csv(f, low_memory=False, usecols=[
            "ADV_IS_POSSESSION_FIRST_ROW", "ADV_FTA_POSS", "ADV_FGM_POSS"])
        d = d[d["ADV_IS_POSSESSION_FIRST_ROW"] == 1]
        term = ((pd.to_numeric(d["ADV_FTA_POSS"], errors="coerce").fillna(0) > 0)
                & (pd.to_numeric(d["ADV_FGM_POSS"], errors="coerce").fillna(0) == 0))
        tot_term += int(term.sum())
        print(f"    {os.path.basename(f):32} {int(term.sum()):7,} "
              f"FT-terminated possessions", flush=True)
    from ref_features import universe
    u = universe()
    u = u[u["yr"] <= 2023]
    n = 0
    adv = pd.read_csv("/mnt/c/NBA2/advanced_stats/game_advanced_stats.csv",
                      low_memory=False)
    adv["gid"] = adv["GAME-ID"].astype(str).str.strip()
    m = u.merge(adv[["gid", "EV_FOULS_H", "EV_FOULS_R"]], on="gid", how="left")
    n = (pd.to_numeric(m["EV_FOULS_H"], errors="coerce").fillna(0)
         + pd.to_numeric(m["EV_FOULS_R"], errors="coerce").fillna(0)).sum()
    if n <= 0:
        return 0.0, False
    return tot_term / n, True


if __name__ == "__main__":
    main()
