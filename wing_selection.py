"""WHICH wing lotteries should we sell? Differentiating inside the wings.

The wings pay ~2.3%/fill on average. That average hides a mechanical asymmetry:
overtime ONLY ADDS points, so the total's left tail is thin and its right tail
is fat (VARIANCE.md; kalshi_shape.py). Therefore

    selling an UNDER-lottery (cheap No at a LOW strike)  should be SAFE
    selling an OVER-lottery  (cheap Yes at a HIGH strike) should be DANGEROUS

and a symmetric Gaussian ladder cannot price that difference.

MAKER ACCOUNTING. We sell the cheap side at its ask and pay $1 if it hits:
    collect = ask_cheap - maker_fee        pay = 1 if the lottery hits
    profit per contract = collect - hit
    risk    = 1 - collect
Everything realized; no modelling. Game-clustered SEs (11 rungs per game).

CUTS, all pre-specified:
  1  side: under-lottery vs over-lottery      <- the main event
  2  the OT CONFIRMATION: rerun excluding games that went to overtime. If the
     asymmetry is an OT artefact it should collapse.
  3  price bucket inside the wings
  4  spread width (what we collect)
  5  game state: CrewShock >= Q85 and final week -- do NOT sell over-lotteries
     when our own signals say the total should be higher
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import kalshi_calib as KC
import refs

THR = 0.8682
FEE_K = 0.07


def clus(df, val="prof", risk="risk"):
    """Game-clustered mean profit and ROI per dollar risked."""
    per = df.groupby("event_ticker")[[val, risk]].mean()
    n = len(per)
    if n < 5:
        return np.nan, np.nan, np.nan, 0
    mu = per[val].mean()
    se = per[val].std(ddof=1) / np.sqrt(n)
    roi = 100 * df[val].sum() / df[risk].sum()
    return 100 * mu, mu / se, roi, n


def build():
    m = refs.build()
    n_ = lambda c: pd.to_numeric(m[c], errors="coerce")
    J = sum(n_(f"OT{i}_{s}").fillna(0.0) for i in range(1, 6)
            for s in ("H", "R"))
    m["ot"] = J > 0
    m["gid"] = m["GAME-ID"].astype(str).str.strip()
    mp = pd.read_csv("team_mapping.csv").set_index(
        "bigdataball_name")["abbr"].to_dict()
    g = m[m["date"] >= "2025-10-01"].copy()
    g["H"] = g["TEAM_H"].map(mp)
    g["R"] = g["TEAM_R"].map(mp)
    mk = lambda d, a, b: (d.dt.strftime("%Y-%m-%d") + "|"
                          + np.where(a < b, a, b) + "-" + np.where(a < b, b, a))
    g["k"] = mk(g["date"], g["H"], g["R"])
    f = pd.read_csv("ref_features.csv")
    f["gid"] = f["gid"].astype(str).str.strip()
    g = g.merge(f[["gid", "CrewShock"]], on="gid", how="left")
    last = g[g["date"] <= "2026-04-12"]["date"].max()
    g["dl"] = (last - g["date"]).dt.days

    u = KC.load()
    u = u[~((u["bid"] <= 0) & (u["ask"] >= 1.0))]
    u = u[u["bucket"] == "regular"].copy()
    u = u.merge(g[["k", "ot", "CrewShock", "dl"]].drop_duplicates("k"),
                on="k", how="left")
    # wings only
    u = u[((u["mid"] >= 0.15) & (u["mid"] < 0.30))
          | ((u["mid"] > 0.70) & (u["mid"] <= 0.85))].copy()
    # the cheap side is the lottery; which side is it?
    u["lot_over"] = u["mid"] < 0.5          # cheap Yes at a high strike
    u["px"] = np.where(u["lot_over"], u["ask"], 1 - u["bid"])
    u["hit"] = np.where(u["lot_over"], u["win"], 1 - u["win"]).astype(float)
    u["collect"] = u["px"] - 0.25 * FEE_K * u["px"] * (1 - u["px"])
    u["prof"] = u["collect"] - u["hit"]
    u["risk"] = 1 - u["collect"]
    u["spread"] = u["ask"] - u["bid"]
    return u


def report(u, rows, title):
    print("\n" + "=" * 96)
    print(title)
    print("=" * 96)
    print(f"  {'cell':34}{'n':>7}{'games':>7}{'collect':>9}{'hit %':>8}"
          f"{'c/contract':>12}{'t':>7}{'ROI %':>8}")
    for lab, s in rows:
        if not len(s):
            continue
        c, t, roi, ng = clus(s)
        print(f"  {lab:34}{len(s):>7,}{ng:>7,}{100*s['collect'].mean():>9.1f}"
              f"{100*s['hit'].mean():>8.2f}{c:>+12.2f}{t:>+7.2f}{roi:>+8.2f}")


def main():
    u = build()
    print(f"  {len(u):,} wing rungs, {u['event_ticker'].nunique():,} games   "
          f"OT rate {100*u.drop_duplicates('event_ticker')['ot'].mean():.2f}%")

    report(u, [("ALL wings", u),
               ("UNDER-lottery (cheap No, low strike)", u[~u["lot_over"]]),
               ("OVER-lottery (cheap Yes, high strike)", u[u["lot_over"]])],
           "1 — THE SIDE ASYMMETRY (selling the lottery)")

    nz = u[~u["ot"].fillna(False)]
    report(nz, [("UNDER-lottery, NON-OT games", nz[~nz["lot_over"]]),
                ("OVER-lottery, NON-OT games", nz[nz["lot_over"]])],
           "2 — OT CONFIRMATION: same cuts, overtime games removed")
    ot = u[u["ot"].fillna(False)]
    report(ot, [("UNDER-lottery, OT games only", ot[~ot["lot_over"]]),
                ("OVER-lottery, OT games only", ot[ot["lot_over"]])],
           "2b — OT games only (where the damage should land)")

    b = []
    for lo, hi in ((0.15, 0.20), (0.20, 0.25), (0.25, 0.30)):
        s = u[(u["px"] >= lo) & (u["px"] < hi)]
        b.append((f"lottery priced {100*lo:.0f}-{100*hi:.0f}c", s))
    report(u, b, "3 — BY LOTTERY PRICE")

    s = []
    for lo, hi, lab in ((0, 2, "spread 1c"), (2, 3, "spread 2c"),
                        (3, 99, "spread 3c+")):
        s.append((lab, u[(100 * u["spread"] >= lo) & (100 * u["spread"] < hi)]))
    report(u, s, "4 — BY SPREAD WIDTH (what we collect)")

    hi_cs = u["CrewShock"].fillna(-9) >= THR
    fw = u["dl"].fillna(99) <= 7
    flag = hi_cs | fw
    report(u, [("OVER-lottery, signals QUIET", u[u["lot_over"] & ~flag]),
               ("OVER-lottery, signals SAY HIGHER", u[u["lot_over"] & flag]),
               ("UNDER-lottery, signals QUIET", u[~u["lot_over"] & ~flag]),
               ("UNDER-lottery, signals SAY HIGHER",
                u[~u["lot_over"] & flag])],
           "5 — GAME STATE: our own signals (CrewShock Q85 or final week)")


if __name__ == "__main__":
    main()
