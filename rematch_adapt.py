"""Consecutive rematches: does the market adjust ENOUGH from Game 1 to Game 2?

Tight formulation. For a pair of games between the same two teams 1-3 days apart:

    R1 = actual1 - close1        Game 1's surprise relative to its own line
    M  = close2  - close1        the market's adjustment for Game 2
    R2 = actual2 - close2        Game 2's residual

and the exact identity

    R2 = (actual2 - close1) - M

so regressing each piece on R1 decomposes market adequacy cleanly:

    (actual2 - close1) = a + c* R1     c* = how much Game 1's surprise ACTUALLY
                                            predicts Game 2 (the correct
                                            adjustment)
    M                  = a + c  R1     c  = how much the market DOES adjust
    R2                 = a + b  R1     b  = c* - c, the residual mispricing

  b > 0  market UNDER-adjusts -> bet with Game 1's surprise
  b < 0  market OVER-adjusts  -> fade it
  b ~ 0  the adjustment is right-sized

This is a within-matchup experiment: same teams, same venue in most cases, days
apart, so team quality and most of the environment are held constant.

TACTICAL CHANNEL. The hypothesis is adaptation, not revenge or momentum, so the
same decomposition is run on POSSESSIONS (pace) and EFFICIENCY separately, using
the corrected possession count. If Game 1 was played at an unusual pace for these
teams, does Game 2 revert, and does the market anticipate the reversion?

Stage 1 is c* -- is there anything to adjust for. If c* ~ 0 there is no
information in Game 1 and the market cannot be wrong about it. Stage 2 is b.
"""
import warnings

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")

BE = 110 / 210


def pairs():
    from poss_vs_eff import quarter_poss
    from prepare_data import CSV, season_label

    raw = pd.read_csv(CSV, low_memory=False)
    raw["lbl"] = season_label(raw).astype(str)
    d = raw[raw["lbl"].str.contains("Regular Season", na=False)].copy()
    d["gid"] = d["GAME-ID"].astype(str).str.zfill(10)
    d["date"] = pd.to_datetime(d["DATE"], errors="coerce")
    d["close"] = pd.to_numeric(d["CLOSING TOTAL_H"], errors="coerce")
    d["open"] = pd.to_numeric(d["OPENING TOTAL_H"], errors="coerce")
    d["actual"] = d["PTS_H"] + d["PTS_R"]
    d = d.dropna(subset=["close", "open", "date", "actual"])
    d = d[d["close"].between(150, 300)].copy()

    qp = quarter_poss()
    gp = qp.groupby("gid")["poss"].sum().rename("poss").reset_index()
    d = d.merge(gp, on="gid", how="left")
    d["ppp"] = d["actual"] / d["poss"]
    d["pair"] = [tuple(sorted([a, b])) for a, b in zip(d["TEAM_H"], d["TEAM_R"])]
    d = d.sort_values("date")

    rows = []
    for (lbl, pr), g in d.groupby(["lbl", "pair"]):
        g = g.sort_values("date")
        for i in range(1, len(g)):
            a, b = g.iloc[i - 1], g.iloc[i]
            gap = (b["date"] - a["date"]).days
            if 1 <= gap <= 3:
                rows.append({
                    "lbl": lbl, "gap": gap,
                    "same_venue": a["TEAM_H"] == b["TEAM_H"],
                    "close1": a["close"], "close2": b["close"],
                    "act1": a["actual"], "act2": b["actual"],
                    "poss1": a["poss"], "poss2": b["poss"],
                    "ppp1": a["ppp"], "ppp2": b["ppp"]})
    P = pd.DataFrame(rows)
    P["yr"] = P["lbl"].str.extract(r"(\d{4})")[0].astype(int)
    P["R1"] = P["act1"] - P["close1"]
    P["M"] = P["close2"] - P["close1"]
    P["R2"] = P["act2"] - P["close2"]
    P["A2_old"] = P["act2"] - P["close1"]
    return P.dropna(subset=["R1", "M", "R2"])


def reg(y, x, lab):
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = np.asarray(x)[ok], np.asarray(y)[ok]
    b, a = np.polyfit(x, y, 1)
    r = np.corrcoef(x, y)[0, 1]
    t = r * np.sqrt(len(x) - 2) / np.sqrt(1 - r * r)
    se = b / t if t else np.nan
    print(f"  {lab:38} slope {b:+.4f}  se {abs(se):.4f}  t={t:+.2f}  n={len(x)}")
    return b


def main():
    P = pairs()
    print(f"{len(P)} consecutive rematches 1-3 days apart, "
          f"{P['yr'].nunique()} seasons")
    print(f"  mean R1 {P['R1'].mean():+.3f}   mean M {P['M'].mean():+.3f}   "
          f"mean R2 {P['R2'].mean():+.3f}\n")

    print("=" * 92)
    print("THE DECOMPOSITION — everything regressed on Game 1's surprise R1")
    print("=" * 92)
    cstar = reg(P["A2_old"], P["R1"], "STAGE 1  (actual2-close1) ~ R1   = c*")
    c = reg(P["M"], P["R1"], "MARKET   (close2-close1)  ~ R1   = c")
    b = reg(P["R2"], P["R1"], "STAGE 2  (actual2-close2) ~ R1   = b")
    print(f"\n  identity check: c* - c = {cstar - c:+.4f}   vs measured b "
          f"{b:+.4f}")
    if abs(c) > 0.01:
        print(f"  the market adjusts {100*c/cstar:.0f}% of the optimal amount"
              if abs(cstar) > 0.01 else
              f"  c* is ~0, so there is nothing to adjust for")

    print("\n" + "=" * 92)
    print("TACTICAL CHANNEL — pace and efficiency, same decomposition")
    print("=" * 92)
    P["dposs1"] = P["poss1"] - P.groupby("yr")["poss1"].transform("mean")
    for lab, c1, c2 in (("POSSESSIONS", "poss1", "poss2"),
                        ("EFFICIENCY ppp", "ppp1", "ppp2")):
        s = P.dropna(subset=[c1, c2])
        x = s[c1] - s.groupby("yr")[c1].transform("mean")
        y = s[c2] - s.groupby("yr")[c2].transform("mean")
        r = np.corrcoef(x, y)[0, 1]
        t = r * np.sqrt(len(x) - 2) / np.sqrt(1 - r * r)
        print(f"  {lab:16} game1 -> game2 corr {r:+.4f}  t={t:+.2f}  n={len(s)}"
              f"   (does the style persist into the rematch?)")

    print("\n" + "=" * 92)
    print("SPLITS — is the under-adjustment concentrated anywhere?")
    print("=" * 92)
    for lab, m in (("same venue", P["same_venue"]),
                   ("home/away swapped", ~P["same_venue"]),
                   ("gap = 1 day", P["gap"] == 1),
                   ("gap = 2-3 days", P["gap"] >= 2)):
        s = P[m]
        if len(s) < 50:
            continue
        bb = np.polyfit(s["R1"], s["R2"], 1)[0]
        rr = np.corrcoef(s["R1"], s["R2"])[0, 1]
        tt = rr * np.sqrt(len(s) - 2) / np.sqrt(1 - rr * rr)
        print(f"  {lab:20} n={len(s):3d}  b={bb:+.4f}  t={tt:+.2f}")

    print("\n  by season (b = residual mispricing per point of R1):")
    for y, s in P.groupby("yr"):
        if len(s) < 20:
            continue
        bb = np.polyfit(s["R1"], s["R2"], 1)[0]
        print(f"    {y}  n={len(s):3d}  b={bb:+.4f}")

    print("\n" + "=" * 92)
    print("BETTING FORM — bet Game 2 in the direction b implies")
    print("=" * 92)
    if abs(b) < 0.01:
        print("  b is ~0: no rule to test.")
        return
    side = np.sign(b) * np.sign(P["R1"])       # +1 = over, -1 = under
    live = P[P["R2"] != 0].copy()
    sl = np.sign(b) * np.sign(live["R1"])
    won = np.where(sl > 0, live["R2"] > 0, live["R2"] < 0)
    wr = won.mean()
    se = np.sqrt(wr * (1 - wr) / len(live))
    print(f"  {len(live)} graded bets   win {100*wr:.2f}%  95% CI "
          f"[{100*(wr-1.96*se):.2f}, {100*(wr+1.96*se):.2f}]   "
          f"ROI {100*(wr*(100/110)-(1-wr)):+.2f}%   break-even {100*BE:.2f}%")
    q = pd.qcut(live["R1"].abs(), 4, labels=[1, 2, 3, 4])
    print("\n  by |R1| quartile (size of Game 1's surprise):")
    for qq, s in live.groupby(q, observed=True):
        w2 = np.where(np.sign(b) * np.sign(s["R1"]) > 0, s["R2"] > 0, s["R2"] < 0)
        print(f"    Q{qq} |R1| {s['R1'].abs().mean():5.1f}  n={len(s):3d}  "
              f"win {100*w2.mean():5.2f}%")


if __name__ == "__main__":
    main()
