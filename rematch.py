"""Consecutive games against the same opponent — a repeated-matchup experiment.

PRE-SPECIFIED before looking:

    Game 2 = a regular-season game in which the same two teams played each other
             within the previous 1-3 days.

STRUCTURAL HYPOTHESIS: under in Game 2. Tactical familiarity and immediate
defensive adaptation cut scoring by more than the book lowers the total.

The clean paired test, which holds the matchup exactly constant:

    dR = (actual - close)_G2 - (actual - close)_G1

and the decomposition that separates real adaptation from the book's response:

    (actual_2 - actual_1) = (close_2 - close_1) + (R_2 - R_1)
      real change            book adjustment      remaining error

If scoring falls 5 and the book lowers the total 2, the remaining error is -3 and
that is the tradeable quantity. If the book lowers it 5, the adaptation is real
and fully priced.

Splits reported, all fixed in advance: gap of 1 / 2 / 3 days, and same venue
versus a home-away swap. Playoffs are excluded -- every playoff game is a
repeated matchup, so they carry no contrast.
"""
import warnings

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")

BE = 110 / 210


def load():
    from prepare_data import CSV, season_label
    raw = pd.read_csv(CSV, low_memory=False)
    raw["lbl"] = season_label(raw).astype(str)
    d = raw[raw["lbl"].str.contains("Regular Season", na=False)].copy()
    d["date"] = pd.to_datetime(d["DATE"], errors="coerce")
    d["close"] = pd.to_numeric(d["CLOSING TOTAL_H"], errors="coerce")
    d["open"] = pd.to_numeric(d["OPENING TOTAL_H"], errors="coerce")
    d["actual"] = d["PTS_H"] + d["PTS_R"]
    d = d.dropna(subset=["close", "open", "date", "actual"])
    d = d[d["close"].between(150, 300)].copy()
    d["r"] = d["actual"] - d["close"]
    d["pair"] = [tuple(sorted([a, b])) for a, b in zip(d["TEAM_H"], d["TEAM_R"])]
    return d.sort_values("date").reset_index(drop=True)


def find_pairs(d):
    """Consecutive meetings 1-3 days apart, within the same season."""
    rows = []
    for (lbl, pair), g in d.groupby(["lbl", "pair"]):
        g = g.sort_values("date")
        for i in range(1, len(g)):
            a, b = g.iloc[i - 1], g.iloc[i]
            gap = (b["date"] - a["date"]).days
            if 1 <= gap <= 3:
                rows.append({
                    "lbl": lbl, "pair": pair, "gap": gap,
                    "date1": a["date"], "date2": b["date"],
                    "same_venue": a["TEAM_H"] == b["TEAM_H"],
                    "close1": a["close"], "close2": b["close"],
                    "open2": b["open"],
                    "act1": a["actual"], "act2": b["actual"],
                    "r1": a["r"], "r2": b["r"]})
    P = pd.DataFrame(rows)
    P["dR"] = P["r2"] - P["r1"]
    P["book_adj"] = P["close2"] - P["close1"]
    P["real_chg"] = P["act2"] - P["act1"]
    P["yr"] = P["lbl"].str.extract(r"(\d{4})")[0].astype(int)
    return P


def batt(s, lab):
    live = s[s["r2"] != 0]
    if len(live) < 20:
        return None
    un = (live["r2"] < 0).mean()
    se = np.sqrt(un * (1 - un) / len(live))
    t, p = stats.ttest_1samp(s["r2"], 0.0)
    td, pd_ = stats.ttest_rel(s["r2"], s["r1"])
    return {"subset": lab, "n": len(s),
            "R Game1": round(s["r1"].mean(), 3),
            "R Game2": round(s["r2"].mean(), 3),
            "dR": round(s["dR"].mean(), 3),
            "dR median": round(s["dR"].median(), 2),
            "G2 UNDER %": round(100 * un, 2),
            "95% CI": f"[{100*(un-1.96*se):.1f}, {100*(un+1.96*se):.1f}]",
            "ROI110": round(100 * (un * (100 / 110) - (1 - un)), 2),
            "t(R2=0)": round(t, 2), "p": round(p, 4),
            "t(dR)": round(td, 2), "p(dR)": round(pd_, 4)}


def main():
    d = load()
    P = find_pairs(d)
    print(f"{len(d):,} regular-season games -> {len(P):,} consecutive "
          f"meetings 1-3 days apart\n")
    print("  by season:")
    print(P.groupby("yr").size().to_string())
    print(f"\n  gap: {P['gap'].value_counts().sort_index().to_dict()}")
    print(f"  same venue: {int(P['same_venue'].sum())} / "
          f"{len(P)-int(P['same_venue'].sum())} swapped")

    print("\n" + "=" * 122)
    print("BATTERY — Game 2 residual and the paired change (negative = under)")
    print("=" * 122)
    rows = [batt(P, "ALL consecutive rematches")]
    for g in (1, 2, 3):
        rows.append(batt(P[P["gap"] == g], f"gap = {g} day(s)"))
    rows.append(batt(P[P["same_venue"]], "same venue"))
    rows.append(batt(P[~P["same_venue"]], "home/away swapped"))
    print(pd.DataFrame([r for r in rows if r]).to_string(index=False))
    print(f"\n  break-even {100*BE:.2f}%")

    print("\n" + "=" * 122)
    print("DECOMPOSITION — real adaptation vs the book's adjustment")
    print("=" * 122)
    for lab, s in (("all rematches", P), ("gap = 1 day", P[P["gap"] == 1]),
                   ("same venue", P[P["same_venue"]])):
        rc, ba, dr = s["real_chg"].mean(), s["book_adj"].mean(), s["dR"].mean()
        t1, p1 = stats.ttest_1samp(s["real_chg"], 0)
        t2, p2 = stats.ttest_1samp(s["book_adj"], 0)
        print(f"  {lab:16} n={len(s):4d}")
        print(f"    real change in scoring (act2-act1)  {rc:+7.3f}  "
              f"t={t1:+.2f} p={p1:.4f}")
        print(f"    book adjustment (close2-close1)     {ba:+7.3f}  "
              f"t={t2:+.2f} p={p2:.4f}")
        print(f"    remaining error (dR)                {dr:+7.3f}  "
              f"= {rc:+.3f} - ({ba:+.3f})")
        if abs(rc) > 0.3:
            print(f"    book captured {100*ba/rc:.1f}% of the real change")

    print("\n" + "=" * 122)
    print("CONTROL — Game 2 vs all other games involving the same two teams")
    print("=" * 122)
    ctrl = []
    for _, r in P.iterrows():
        m = d[(d["lbl"] == r["lbl"])
              & (d["pair"].apply(lambda p: len(set(p) & set(r["pair"])) >= 1))
              & (~d["date"].isin([r["date1"], r["date2"]]))]
        if len(m):
            ctrl.append(m["r"].mean())
    print(f"  mean residual in other games involving these teams: "
          f"{np.mean(ctrl):+.3f}  (n pairs={len(ctrl)})")
    print(f"  Game 2 residual: {P['r2'].mean():+.3f}   "
          f"Game 1 residual: {P['r1'].mean():+.3f}")

    print("\n--- by season, Game 2 ---")
    r = []
    for y, s in P.groupby("yr"):
        live = s[s["r2"] != 0]
        r.append({"season": y, "n": len(s),
                  "R Game1": round(s["r1"].mean(), 2),
                  "R Game2": round(s["r2"].mean(), 2),
                  "dR": round(s["dR"].mean(), 2),
                  "G2 under %": round(100 * (live["r2"] < 0).mean(), 1)})
    print(pd.DataFrame(r).to_string(index=False))


if __name__ == "__main__":
    main()
