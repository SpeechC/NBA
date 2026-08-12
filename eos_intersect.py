"""Do the two measured effects actually intersect?

Test 3 produced two separate cuts of the same games:

    favourite's FULL-GAME points   +3.060  (p<0.001)   underdog +0.066 (p=0.91)
    combined FIRST-HALF total      +2.469  (p=0.0001)  H2       +0.686 (p=0.27)

The proposed bet -- the favourite's first-half team total -- assumes those
intersect, i.e. that the favourite's edge lands in the first half. That was never
measured. Three other arrangements fit the same two results equally well:

  * the favourite's +3.06 is spread evenly across halves, and the H1 concentration
    comes from the UNDERDOG's first half
  * both effects sit in H1 but in different games
  * the favourite's edge is in H2 while the underdog's is in H1, summing to an
    H1-weighted combined total

This resolves it by computing the 2x2 directly: favourite/underdog x H1/H2.

⚠ This measures SCORING, not a betting edge. No first-half or team-total lines
exist in this dataset, so a confirmed interaction would establish the mechanism
and the target market -- not that the market misprices it.

⚠ Period scores cover REGULATION ONLY (periods 1-4), so the favourite full-game
figure here is not the +3.060 from Test 3, which used final scores including
overtime. Halves must sum to regulation for the 2x2 to decompose cleanly, so
regulation is the right basis; the difference between the two is average OT.
"""
import warnings

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")

from halves import period_scores


def main():
    from prepare_data import CSV, season_label
    raw = pd.read_csv(CSV, low_memory=False)
    raw["season"] = season_label(raw).astype(str)
    d = raw[raw["season"].str.contains("Regular Season", na=False)].copy()
    d["gid"] = d["GAME-ID"].astype(str).str.zfill(10)
    d["date"] = pd.to_datetime(d["DATE"], errors="coerce")
    d["spread"] = pd.to_numeric(d["CLOSING SPREAD_H"], errors="coerce")
    d["close_total"] = pd.to_numeric(d["CLOSING TOTAL_H"], errors="coerce")
    d["days_left"] = (d.groupby("season")["date"].transform("max")
                      - d["date"]).dt.days
    d = d.dropna(subset=["spread", "date", "close_total"])

    w = period_scores()
    # period_scores() carries its own `season` (pbp format "2017-18"); keeping it
    # would collide with the odds-file season on merge and yield season_x/season_y.
    keep = ["gid", "h1", "h2"] + [f"{s_}_p{q}" for s_ in ("home", "vis")
                                  for q in (1, 2, 3, 4)]
    w = w[keep]
    assert "season" not in w.columns
    m = d.merge(w, on="gid", how="inner")
    m = m[(m["h1"] > 60) & (m["h2"] > 60)]
    home_fav = m["spread"] < 0
    m["fav_h1"] = np.where(home_fav, m["home_p1"] + m["home_p2"],
                           m["vis_p1"] + m["vis_p2"])
    m["fav_h2"] = np.where(home_fav, m["home_p3"] + m["home_p4"],
                           m["vis_p3"] + m["vis_p4"])
    m["dog_h1"] = np.where(home_fav, m["vis_p1"] + m["vis_p2"],
                           m["home_p1"] + m["home_p2"])
    m["dog_h2"] = np.where(home_fav, m["vis_p3"] + m["vis_p4"],
                           m["home_p3"] + m["home_p4"])
    m["fav_all"] = m["fav_h1"] + m["fav_h2"]
    m["dog_all"] = m["dog_h1"] + m["dog_h2"]

    late, rest = m[m["days_left"] <= 7], m[m["days_left"] > 14]
    print(f"{len(m):,} games with period scores and a spread")
    print(f"  last 7 days {len(late):,}   rest of season {len(rest):,}\n")

    print("=" * 96)
    print("THE 2x2 — favourite/underdog x first half/second half")
    print("=" * 96)
    rows = []
    for col, lab in (("fav_h1", "FAVOURITE  H1"), ("fav_h2", "FAVOURITE  H2"),
                     ("dog_h1", "underdog   H1"), ("dog_h2", "underdog   H2"),
                     ("fav_all", "favourite  full"), ("dog_all", "underdog   full"),
                     ("h1", "combined   H1"), ("h2", "combined   H2")):
        a, b = late[col], rest[col]
        t, p = stats.ttest_ind(a, b, equal_var=False)
        sd = np.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2)
        rows.append({"cell": lab, "last 7d": round(a.mean(), 3),
                     "rest": round(b.mean(), 3),
                     "diff": round(a.mean() - b.mean(), 3),
                     "diff SD": round((a.mean() - b.mean()) / sd, 3),
                     "t": round(t, 2), "p": round(p, 4),
                     "% of total effect": ""})
    t = pd.DataFrame(rows)
    tot = (t.loc[t["cell"] == "FAVOURITE  H1", "diff"].iloc[0]
           + t.loc[t["cell"] == "FAVOURITE  H2", "diff"].iloc[0]
           + t.loc[t["cell"] == "underdog   H1", "diff"].iloc[0]
           + t.loc[t["cell"] == "underdog   H2", "diff"].iloc[0])
    for i, r in t.iterrows():
        if r["cell"].endswith(("H1", "H2")) and "combined" not in r["cell"]:
            t.at[i, "% of total effect"] = f"{100*r['diff']/tot:.0f}%"
    print(t.to_string(index=False))
    print(f"\n  total game effect (sum of four cells): {tot:+.3f} points")

    print("\n" + "=" * 96)
    print("Season-by-season, the cell that matters")
    print("=" * 96)
    best = t.loc[t[t["cell"].str.contains("H1|H2") &
                   ~t["cell"].str.contains("combined")]["diff"].idxmax(), "cell"]
    col = {"FAVOURITE  H1": "fav_h1", "FAVOURITE  H2": "fav_h2",
           "underdog   H1": "dog_h1", "underdog   H2": "dog_h2"}[best]
    print(f"  largest cell: {best}\n")
    r = []
    for s in sorted(m["season"].unique()):
        a = m[(m["season"] == s) & (m["days_left"] <= 7)][col]
        b = m[(m["season"] == s) & (m["days_left"] > 14)][col]
        if len(a) < 20:
            continue
        r.append({"season": s[4:13], "n late": len(a),
                  "late": round(a.mean(), 2), "rest": round(b.mean(), 2),
                  "diff": round(a.mean() - b.mean(), 2)})
    r = pd.DataFrame(r)
    print(r.to_string(index=False))
    print(f"\n  seasons positive: {int((r['diff'] > 0).sum())}/{len(r)}")

    print("\n" + "=" * 96)
    print("Relative size against a plausible line for each market")
    print("=" * 96)
    for col, lab in (("h1", "combined 1H total"), ("fav_all", "favourite team total"),
                     ("fav_h1", "favourite 1H team total"),
                     ("dog_h1", "underdog 1H team total")):
        base = rest[col].mean()
        eff = late[col].mean() - base
        print(f"  {lab:26} base {base:7.2f}   effect {eff:+.3f}   "
              f"relative {100*eff/base:+.2f}%")


if __name__ == "__main__":
    main()
