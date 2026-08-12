"""Characterising the end-of-season overs effect.

Detected in §21 by an omnibus variance-components test that flagged monthly
clustering before any month was inspected. April carries it: over 54.52% against
a 52.38% break-even, and the last 7 days of a season give 55.87%.

Five questions that decide whether it is tradeable and whether the proposed
mechanism -- teams stop competing, so scoring rises -- is actually the cause:

  1 WINDOW    Days-remaining ladder. Is "April" the right cut, or is the effect
              concentrated in a narrower window?
  2 MOTIVE    If motivation is the mechanism, the effect should be U-SHAPED in
              team quality: strong for bad teams (tanking) and locked-in good
              teams (resting), weakest for bubble teams still fighting. That is
              a falsifiable prediction the calendar alone does not make.
  3 MARKET    Does the book already move late-season totals up? If the closing
              total is raised and the residual survives anyway, the market sees
              the effect and under-corrects. If it does not move, the market is
              blind to it.
  4 REAL      Is scoring actually higher, or is the line simply set too low?
              Compares realised totals, not just residuals.
  5 MONEY     Bets per season and dollars, honestly.

Records are computed WALK-FORWARD: a team's win rate uses only games completed
before the one being tested.
"""
import warnings

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")


def load():
    from prepare_data import CSV, season_label
    raw = pd.read_csv(CSV, low_memory=False)
    raw["season"] = season_label(raw).astype(str)
    d = raw[raw["season"].str.contains("Regular Season", na=False)].copy()
    d["date"] = pd.to_datetime(d["DATE"], errors="coerce")
    d["close_total"] = pd.to_numeric(d["CLOSING TOTAL_H"], errors="coerce")
    d["open_total"] = pd.to_numeric(d["OPENING TOTAL_H"], errors="coerce")
    d["actual"] = d["PTS_H"] + d["PTS_R"]
    d = d.dropna(subset=["close_total", "date", "actual"])
    d = d[d["close_total"].between(150, 300)]
    d["resid"] = d["actual"] - d["close_total"]
    d["move"] = d["close_total"] - d["open_total"]
    d["days_left"] = (d.groupby("season")["date"].transform("max")
                      - d["date"]).dt.days

    # walk-forward win rate for both teams
    h = d[["date", "season", "TEAM_H"]].assign(
        win=(d["PTS_H"] > d["PTS_R"]).astype(int)).rename(columns={"TEAM_H": "team"})
    a = d[["date", "season", "TEAM_R"]].assign(
        win=(d["PTS_R"] > d["PTS_H"]).astype(int)).rename(columns={"TEAM_R": "team"})
    L = pd.concat([h, a]).sort_values("date")
    L["cum_w"] = L.groupby(["season", "team"])["win"].cumsum() - L["win"]
    L["cum_g"] = L.groupby(["season", "team"]).cumcount()
    L["wpct"] = L["cum_w"] / L["cum_g"].replace(0, np.nan)
    key = ["season", "team", "date"]
    d = d.merge(L[key + ["wpct", "cum_g"]].rename(columns={"team": "TEAM_H",
                "wpct": "wpct_h", "cum_g": "g_h"}),
                left_on=["season", "TEAM_H", "date"],
                right_on=["season", "TEAM_H", "date"], how="left")
    d = d.merge(L[key + ["wpct", "cum_g"]].rename(columns={"team": "TEAM_R",
                "wpct": "wpct_a", "cum_g": "g_a"}),
                left_on=["season", "TEAM_R", "date"],
                right_on=["season", "TEAM_R", "date"], how="left")
    return d


def blk(s, lab):
    r = s["resid"]
    ov = (r > 0).mean()
    se = np.sqrt(ov * (1 - ov) / len(s))
    return {"window": lab, "n": len(s),
            "mean close": round(s["close_total"].mean(), 2),
            "mean actual": round(s["actual"].mean(), 2),
            "residual": round(r.mean(), 3),
            "over %": round(100 * ov, 2),
            "95% CI": f"[{100*(ov-1.96*se):.1f}, {100*(ov+1.96*se):.1f}]",
            "ROI110": round(100 * (ov * (100 / 110) - (1 - ov)), 2)}


def main():
    d = load()
    print(f"{len(d):,} games\n")

    print("=" * 104)
    print("1. WINDOW — days remaining in the season")
    print("=" * 104)
    rows = []
    for k in (3, 5, 7, 10, 14, 21, 30):
        rows.append(blk(d[d["days_left"] <= k], f"last {k} days"))
    rows.append(blk(d[d["days_left"] > 30], "rest of season"))
    print(pd.DataFrame(rows).to_string(index=False))

    print("\n" + "=" * 104)
    print("2. MOTIVE — U-shape in team quality? (last 21 days)")
    print("=" * 104)
    late = d[d["days_left"] <= 21].dropna(subset=["wpct_h", "wpct_a"]).copy()
    late["worst"] = late[["wpct_h", "wpct_a"]].min(axis=1)
    late["best"] = late[["wpct_h", "wpct_a"]].max(axis=1)
    late["both_bad"] = late["best"] < 0.40
    late["both_mid"] = (late["worst"] >= 0.40) & (late["best"] <= 0.62)
    late["has_tanker"] = late["worst"] < 0.33
    late["both_good"] = late["worst"] > 0.62
    rows = []
    for lab, m in (("both teams poor (<.400)", late["both_bad"]),
                   ("contains a tanker (<.333)", late["has_tanker"]),
                   ("both mid — fighting (.400–.620)", late["both_mid"]),
                   ("both strong (>.620)", late["both_good"])):
        if m.sum() >= 60:
            rows.append(blk(late[m], lab))
    print(pd.DataFrame(rows).to_string(index=False))
    print("\n  Motivation predicts: poor and strong high, 'fighting' low.")

    print("\n" + "=" * 104)
    print("3. MARKET — does the book raise late-season totals?")
    print("=" * 104)
    rows = []
    for lab, m in (("last 7 days", d["days_left"] <= 7),
                   ("last 21 days", d["days_left"] <= 21),
                   ("rest of season", d["days_left"] > 21)):
        s = d[m]
        rows.append({"window": lab, "n": len(s),
                     "mean OPEN total": round(s["open_total"].mean(), 2),
                     "mean CLOSE total": round(s["close_total"].mean(), 2),
                     "open→close move": round(s["move"].mean(), 3),
                     "mean actual": round(s["actual"].mean(), 2),
                     "residual vs close": round(s["resid"].mean(), 3)})
    print(pd.DataFrame(rows).to_string(index=False))
    print("\n  If the close is raised but the residual survives, the market")
    print("  sees the effect and under-corrects.")

    print("\n" + "=" * 104)
    print("4. REAL — is scoring genuinely higher late?")
    print("=" * 104)
    for lab, m in (("last 7 days", d["days_left"] <= 7),
                   ("last 21 days", d["days_left"] <= 21),
                   ("rest of season", d["days_left"] > 21)):
        s = d[m]
        print(f"  {lab:16} actual {s['actual'].mean():7.2f}   "
              f"close {s['close_total'].mean():7.2f}   "
              f"gap {s['resid'].mean():+.3f}")
    t, p = stats.ttest_ind(d[d["days_left"] <= 21]["actual"],
                           d[d["days_left"] > 21]["actual"], equal_var=False)
    print(f"\n  actual totals, last 21 days vs rest: t={t:+.2f}, p={p:.4f}")

    print("\n" + "=" * 104)
    print("5. MONEY — $100 flat, -110")
    print("=" * 104)
    ns = d["season"].nunique()
    for k in (7, 14, 21):
        s = d[d["days_left"] <= k]
        ov = (s["resid"] > 0).mean()
        roi = ov * (100 / 110) - (1 - ov)
        print(f"  last {k:2} days: {len(s):5,} bets ({len(s)/ns:5.1f}/season)  "
              f"over {100*ov:5.2f}%  ROI {100*roi:+5.2f}%  "
              f"${100*roi*len(s)/ns:+,.0f}/season")

    print("\n--- last 21 days, by season ---")
    s = d[d["days_left"] <= 21]
    print(s.groupby("season").apply(lambda x: pd.Series({
        "n": len(x), "residual": round(x["resid"].mean(), 2),
        "over %": round(100 * (x["resid"] > 0).mean(), 2)}),
        include_groups=False).to_string())


if __name__ == "__main__":
    main()
