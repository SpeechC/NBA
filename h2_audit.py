"""Coverage audit for the 2H-total branch and the crew-chief seat question.

Runs BEFORE any pre-registration so the frozen document carries honest
sample sizes. No outcome is examined here beyond coverage and seat structure.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import pbp_halves
import refs
from data_split import SPLIT_DATE


def build():
    d = refs.build()
    d["gid"] = d["GAME-ID"].astype(str).str.strip()
    n = lambda c: pd.to_numeric(d[c], errors="coerce")
    a, b = n("HALFTIME_H"), n("HALFTIME_R")
    # same convention as half_totals.py: 2H total and 2H spread swap columns
    d["h2_line"] = np.where(a.between(80, 160), a,
                            np.where(b.between(80, 160), b, np.nan))
    d["h2_spread"] = np.where(a.between(-30, 30), a,
                              np.where(b.between(-30, 30), b, np.nan))
    H = pbp_halves.build()
    H["gidz"] = H["gid"].astype(str).str.zfill(10)
    d["gidz"] = d["gid"].str.zfill(10)
    d = d.merge(H.drop(columns=["gid"]), on="gidz", how="left")
    f = pd.read_csv("ref_features.csv")
    f["gid"] = f["gid"].astype(str).str.strip()
    d = d.merge(f[["gid", "CrewShock", "LeagueFoulState"]], on="gid", how="left")
    d["h2_actual"] = d["pts_h2"]
    return d


def main():
    d = build()
    print("=" * 96)
    print("1 — 2H LINE x H2 PLAY-BY-PLAY COVERAGE, BY SEASON")
    print("=" * 96)
    d["has_line"] = d["h2_line"].notna()
    d["has_pbp"] = d["fouls_h2"].notna()
    d["has_cs"] = d["CrewShock"].notna()
    d["usable"] = d["has_line"] & d["has_pbp"] & d["has_cs"]
    t = d.groupby("yr").agg(games=("gid", "size"),
                            line=("has_line", "sum"),
                            pbp=("has_pbp", "sum"),
                            usable=("usable", "sum"))
    t["line %"] = (100 * t["line"] / t["games"]).round(1)
    t["pbp %"] = (100 * t["pbp"] / t["games"]).round(1)
    t["USABLE %"] = (100 * t["usable"] / t["games"]).round(1)
    print(t[["games", "line", "line %", "pbp", "pbp %", "usable",
             "USABLE %"]].to_string())
    u = d[d["usable"]]
    dev = u[u["date"] < SPLIT_DATE]
    hold = u[u["date"] >= SPLIT_DATE]
    print(f"\n  usable total {len(u):,}   development {len(dev):,}   "
          f"holdout {len(hold):,}")
    print(f"  holdout seasons present: {sorted(hold['yr'].unique())}")

    print("\n  sanity on the parsed 2H line")
    s = u.dropna(subset=["h2_line", "h2_actual"])
    print(f"    h2_line mean {s['h2_line'].mean():.2f}  sd {s['h2_line'].std():.2f}"
          f"   h2_actual mean {s['h2_actual'].mean():.2f} "
          f"sd {s['h2_actual'].std():.2f}")
    r = np.corrcoef(s["h2_line"], s["h2_actual"])[0, 1]
    print(f"    corr(line, actual) {r:+.4f}   mean residual "
          f"{(s['h2_actual'] - s['h2_line']).mean():+.3f}")
    print(f"    over rate vs 2H line {100*(s['h2_actual'] > s['h2_line']).mean():.2f}%"
          f"   push {100*(s['h2_actual'] == s['h2_line']).mean():.2f}%")

    print("\n  where the fouls actually are (all games with PBP)")
    p = d[d["has_pbp"]]
    for c in ("fouls", "fta", "pts", "poss"):
        print(f"    {c:6} H1 {p[f'{c}_h1'].mean():8.3f}   "
              f"H2 {p[f'{c}_h2'].mean():8.3f}   "
              f"H2 share {100*p[f'{c}_h2'].mean()/(p[f'{c}_h1'].mean()+p[f'{c}_h2'].mean()):5.1f}%")

    print("\n" + "=" * 96)
    print("2 — CREW SEAT STRUCTURE (is ref1 the crew chief in BOTH eras?)")
    print("=" * 96)
    raw = pd.read_csv("/mnt/c/NBA2/dfMaster_OT_2017-2026.csv", low_memory=False)
    raw["yr"] = pd.to_datetime(raw["DATE"], errors="coerce").dt.year
    print("  refs.build maps ref1 = MAIN REF_R (old era) or CREW CHIEF_R (new)")
    print("  coverage of each source column by calendar year:")
    cc = raw.groupby("yr")[["MAIN REF_R", "CREW CHIEF_R"]].apply(
        lambda g: (100 * g.notna().mean()).round(1))
    print(cc.to_string())

    e = d.dropna(subset=["ref1", "ref2", "ref3"]).copy()
    e["era"] = np.where(e["yr"] <= 2021, "2017-2021", "2022-2025")
    print("\n  officials appearing in seat 1 (chief) vs seats 2/3, by era")
    for era, g in e.groupby("era"):
        s1 = set(g["ref1"])
        s23 = set(g["ref2"]) | set(g["ref3"])
        print(f"    {era}: {len(s1)} distinct chiefs, {len(s23)} in seats 2/3, "
              f"{len(s1 & s23)} appear in both")
    s1a = set(e[e["era"] == "2017-2021"]["ref1"])
    s1b = set(e[e["era"] == "2022-2025"]["ref1"])
    print(f"    chiefs common to both eras: {len(s1a & s1b)} of "
          f"{len(s1a)} / {len(s1b)}")

    print("\n  seat-1 rate per official (share of their games in the chief seat)")
    rows = []
    for _, g in e.iterrows():
        pass
    long = pd.concat([
        pd.DataFrame({"ref": e[f"ref{i}"], "seat": i, "yr": e["yr"]})
        for i in (1, 2, 3)])
    pr = long.groupby("ref").agg(games=("seat", "size"),
                                 chief=("seat", lambda s: (s == 1).mean()))
    pr = pr[pr["games"] >= 100].sort_values("chief", ascending=False)
    print(f"    {len(pr)} officials with >=100 games")
    print(f"    chief-share distribution: p10 {pr['chief'].quantile(.1):.3f}  "
          f"median {pr['chief'].median():.3f}  p90 {pr['chief'].quantile(.9):.3f}")
    print(f"    officials never in seat 1: {int((pr['chief'] == 0).sum())}   "
          f"always in seat 1: {int((pr['chief'] == 1).sum())}")
    print("\n    top 8 by chief share")
    print(pr.head(8).round(3).to_string())
    print("    bottom 5 by chief share")
    print(pr.tail(5).round(3).to_string())


if __name__ == "__main__":
    main()
