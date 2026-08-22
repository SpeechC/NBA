"""TEST 5 — ELIMINATION MARGINS, and TEST 3 — ALTITUDE H2 FATIGUE.

Both are rules/structure candidates on data we already hold (master quarters,
so all seasons through 2025-26; no PBP dependency).

TEST 5 — ELIMINATION. The final-week TOTALS signal is frozen and working. Its
margin sibling was never run: once a team cannot reach the play-in, its
objective changes (development minutes, tanking for lottery odds, resting
veterans). Institutional, standings-derived, pregame-observable.
  state: in the last ELIM_WIN days of the regular season, the team's
         season-to-date win% (strictly prior games only)
  test:  own spread cover, and own margin vs the market's implied own margin
  the comparison is BETWEEN teams within the same late-season window, so the
  known final-week TOTALS effect cannot drive it (that is a level effect on
  both sides; this is a differential).

TEST 3 — ALTITUDE. Denver (~5,280 ft) and Utah (~4,200 ft) are physiological
outliers. Full-game altitude advantage is certainly inside home-court pricing;
the untested question is the TIMING SIGNATURE -- fatigue should hit the SECOND
half specifically. That is only tradeable when half markets have flow
(KXNBA1HTOTAL / KXNBA2HTOTAL, listed June 2026), so this is preparation.
  test: visitor H1 and H2 points at altitude vs THAT SAME VISITOR's own
        season baseline (within-team comparison, so team quality cancels)
  prediction: H2 deficit, H1 neutral. A deficit in BOTH halves is altitude
        being priced as a level effect, not a fatigue signature.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import refs
from data_split import SPLIT_DATE
from dispersion_priced import ols

ELIM_WIN = 21          # days from the end of the regular season
ALT = ("Denver", "Utah")


def panel():
    m = refs.build()
    n = lambda c: pd.to_numeric(m[c], errors="coerce")
    d = pd.DataFrame({
        "date": m["date"], "yr": m["yr"],
        "H": m["TEAM_H"], "R": m["TEAM_R"],
        "spread": n("CLOSING SPREAD_H"),
        "pts_h": n("PTS_H"), "pts_r": n("PTS_R")})
    for p in (1, 2, 3, 4):
        d[f"h{p}"] = n(f"{p}Q_H")
        d[f"r{p}"] = n(f"{p}Q_R")
    d["H1_h"], d["H2_h"] = d["h1"] + d["h2"], d["h3"] + d["h4"]
    d["H1_r"], d["H2_r"] = d["r1"] + d["r2"], d["r3"] + d["r4"]
    d = d.dropna(subset=["spread", "pts_h", "pts_r", "H1_r", "H2_r"])
    rows = []
    for s, o in (("H", "R"), ("R", "H")):
        sign = 1.0 if s == "H" else -1.0
        rows.append(pd.DataFrame({
            "date": d["date"], "yr": d["yr"], "home": int(s == "H"),
            "team": d[s], "opp": d[o],
            "own_spread": sign * d["spread"],
            "own_margin": sign * (d["pts_h"] - d["pts_r"]),
            "win": (sign * (d["pts_h"] - d["pts_r"]) > 0).astype(float),
            "H1": d[f"H1_{s.lower()}"], "H2": d[f"H2_{s.lower()}"]}))
    L = pd.concat(rows, ignore_index=True)
    L["cover"] = (L["own_margin"] + L["own_spread"] > 0).astype(float)
    L["sres"] = L["own_margin"] + L["own_spread"]
    return L.sort_values("date").reset_index(drop=True)


def main():
    L = panel()
    print(f"  {len(L):,} team-games, seasons {sorted(L['yr'].unique())}")

    print("\n" + "=" * 92)
    print(f"TEST 5 — ELIMINATION MARGINS (last {ELIM_WIN} days of each season)")
    print("=" * 92)
    g = L.groupby(["yr", "team"])
    L["wpct"] = g["win"].transform(lambda s: s.shift(1).expanding().mean())
    L["gp"] = g["win"].transform(lambda s: s.shift(1).expanding().count())
    last = L.groupby("yr")["date"].transform("max")
    L["dleft"] = (last - L["date"]).dt.days
    late = L[(L["dleft"] <= ELIM_WIN) & (L["gp"] >= 40)].dropna(
        subset=["wpct", "cover"])
    print(f"  {len(late):,} late-season team-games with >=40 prior games")
    late = late.copy()
    late["tier"] = pd.qcut(late["wpct"], 3,
                           labels=["BOTTOM (likely out)", "middle",
                                   "TOP (playoff bound)"])
    print(f"  {'tier':22}{'n':>7}{'win%':>8}{'cover %':>10}{'mean sres':>12}"
          f"{'mean margin':>13}")
    for t, s in late.groupby("tier", observed=True):
        print(f"  {str(t):22}{len(s):>7,}{s['wpct'].mean():>8.3f}"
              f"{100*s['cover'].mean():>10.2f}{s['sres'].mean():>+12.3f}"
              f"{s['own_margin'].mean():>+13.3f}")
    b, se, t = ols(late["sres"].values,
                   np.column_stack([late["wpct"].values,
                                    late["own_spread"].values]))
    print(f"\n  sres ~ win% + own spread:  win% coef {b[1]:+.4f} "
          f"(t={t[1]:+.2f})")
    print(f"  [positive = better teams beat the spread late; negative = worse "
          f"teams do]")
    for lab, x in (("development", late[late["date"] < SPLIT_DATE]),
                   ("holdout", late[late["date"] >= SPLIT_DATE])):
        bb, _, tt = ols(x["sres"].values,
                        np.column_stack([x["wpct"].values,
                                         x["own_spread"].values]))
        bot = x[x["wpct"] <= x["wpct"].quantile(1/3)]
        print(f"  {lab:12} win% coef {bb[1]:+.4f} (t={tt[1]:+.2f})   "
              f"bottom-tier cover {100*bot['cover'].mean():.2f}% "
              f"(n={len(bot):,})")

    print("\n" + "=" * 92)
    print("TEST 3 — ALTITUDE H2 FATIGUE (visitors at Denver / Utah)")
    print("=" * 92)
    v = L[L["home"] == 0].copy()
    vg = v.groupby(["yr", "team"])
    for c in ("H1", "H2"):
        v[f"{c}_base"] = vg[c].transform("mean")
        v[f"{c}_dev"] = v[c] - v[f"{c}_base"]
    v["alt"] = v["opp"].isin(ALT)
    print(f"  visitor games at altitude {int(v['alt'].sum()):,}   "
          f"elsewhere {int((~v['alt']).sum()):,}")
    print(f"  {'cell':22}{'n':>7}{'H1 dev':>10}{'H2 dev':>10}"
          f"{'H2 - H1':>10}")
    for lab, s in (("at DEN/UTA", v[v["alt"]]), ("elsewhere", v[~v["alt"]])):
        print(f"  {lab:22}{len(s):>7,}{s['H1_dev'].mean():>+10.3f}"
              f"{s['H2_dev'].mean():>+10.3f}"
              f"{s['H2_dev'].mean()-s['H1_dev'].mean():>+10.3f}")
    for c in ("H1_dev", "H2_dev"):
        a, b_ = v[v["alt"]][c], v[~v["alt"]][c]
        dd = a.mean() - b_.mean()
        se = np.sqrt(a.var(ddof=1)/len(a) + b_.var(ddof=1)/len(b_))
        print(f"  {c}: altitude minus elsewhere {dd:+.4f} (t={dd/se:+.2f})")
    print("\n  by venue, and by split:")
    for ven in ALT:
        s = v[v["opp"] == ven]
        print(f"    {ven:8} n={len(s):>4}  H1 dev {s['H1_dev'].mean():+.3f}"
              f"   H2 dev {s['H2_dev'].mean():+.3f}")
    for lab, x in (("development", v[v["date"] < SPLIT_DATE]),
                   ("holdout", v[v["date"] >= SPLIT_DATE])):
        a = x[x["alt"]]
        print(f"    {lab:12} n={len(a):>4}  H1 dev {a['H1_dev'].mean():+.3f}"
              f"   H2 dev {a['H2_dev'].mean():+.3f}")


if __name__ == "__main__":
    main()
