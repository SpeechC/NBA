"""Is the full-game Over anomaly decaying, or only its composition shifting?

The favourite-H1 conditioned effect fell from ~+2.4 in 2018-2022 to ~+0.6 in the
last three seasons. That is a DIFFERENT variable from the one the strategy bets:

    fav_H1 residual   = fav_H1 actual  - E[fav_H1 | market's closing numbers]
    strategy variable = actual total   - closing total

The second is directly observed and settled at a real price. The first is a
reconstruction from a regression. Inferring decay in the second from decay in the
first is invalid if other scoring components compensate.

This tests that directly: full-game residual and over rate in the final 7 days,
by season, set beside the four-cell decomposition for the same seasons. If the
aggregate holds while the cells rotate, then the source of the late-season
scoring excess is evolving while the pricing error persists -- which would make
the full-game bet MORE secure than the derivative hypothesis, not less.

⚠ Play-by-play stops at 2024-25, so 2025-26 has a full-game residual but no
component decomposition.
"""
import warnings

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")

WINDOW = 7
FIT_OUTSIDE = 14
BE = 110 / 210


def main():
    from eos_confirm import build, residualise
    from prepare_data import CSV, season_label

    # full-game side: all seasons, odds only
    raw = pd.read_csv(CSV, low_memory=False)
    raw["season"] = season_label(raw).astype(str)
    d = raw[raw["season"].str.contains("Regular Season", na=False)].copy()
    d["date"] = pd.to_datetime(d["DATE"], errors="coerce")
    d["close_total"] = pd.to_numeric(d["CLOSING TOTAL_H"], errors="coerce")
    d["actual"] = d["PTS_H"] + d["PTS_R"]
    d = d.dropna(subset=["close_total", "date", "actual"])
    d = d[d["close_total"].between(150, 300)]
    d["resid"] = d["actual"] - d["close_total"]
    d["days_left"] = (d.groupby("season")["date"].transform("max")
                      - d["date"]).dt.days
    d = d[d["resid"] != 0]
    late = d[d["days_left"] <= WINDOW]

    print("=" * 104)
    print("THE STRATEGY VARIABLE — full-game residual, final 7 days, by season")
    print("=" * 104)
    rows = []
    for s in sorted(late["season"].unique()):
        x = late[late["season"] == s]
        ov = (x["resid"] > 0).mean()
        se = np.sqrt(ov * (1 - ov) / len(x))
        rows.append({"season": s[4:13], "n": len(x),
                     "residual": round(x["resid"].mean(), 2),
                     "median": round(x["resid"].median(), 2),
                     "over %": round(100 * ov, 2),
                     "ROI110": round(100 * (ov * (100 / 110) - (1 - ov)), 2)})
    F = pd.DataFrame(rows)
    print(F.to_string(index=False))
    y = F["over %"].values
    sl, ic, r, p, se = stats.linregress(np.arange(len(y)), y)
    print(f"\n  over-rate trend: {sl:+.3f} pp/season (se {se:.3f}, p={p:.3f})")
    print(f"  first 4 seasons: {y[:4].mean():.2f}%    "
          f"last 4 seasons: {y[-4:].mean():.2f}%   break-even {100*BE:.2f}%")
    print(f"  seasons above break-even: {int((y > 100*BE).sum())}/{len(y)}")

    # components
    m = build()
    for t_ in ("fav_h1", "fav_h2", "dog_h1", "dog_h2"):
        m[f"r_{t_}"], _ = residualise(m, t_, ["imp_fav_tt", "close_total",
                                              "abs_spread"])
    print("\n" + "=" * 104)
    print("COMPOSITION — the four cells by season (raw), and their sum")
    print("=" * 104)
    rows = []
    for s in sorted(m["season"].unique()):
        sm = m[m["season"] == s]
        L = sm[sm["late"]]
        R = sm[~sm["late"] & (sm["days_left"] > FIT_OUTSIDE)]
        e = {c: L[c].mean() - R[c].mean()
             for c in ("fav_h1", "fav_h2", "dog_h1", "dog_h2")}
        rows.append({"season": s[4:13], "n late": len(L),
                     "fav H1": round(e["fav_h1"], 2),
                     "fav H2": round(e["fav_h2"], 2),
                     "dog H1": round(e["dog_h1"], 2),
                     "dog H2": round(e["dog_h2"], 2),
                     "SUM": round(sum(e.values()), 2),
                     "fav H1 share": f"{100*e['fav_h1']/sum(e.values()):.0f}%"
                     if sum(e.values()) > 0.3 else "—"})
    C = pd.DataFrame(rows)
    print(C.to_string(index=False))

    print("\n" + "=" * 104)
    print("SIDE BY SIDE — does the aggregate hold while the source rotates?")
    print("=" * 104)
    j = F.merge(C[["season", "fav H1", "SUM", "fav H1 share"]], on="season",
                how="left")
    print(j[["season", "n", "over %", "residual", "SUM", "fav H1",
             "fav H1 share"]].to_string(index=False))
    k = j.dropna(subset=["fav H1"])
    print(f"\n  corr(full-game over %, fav-H1 effect) across seasons: "
          f"{np.corrcoef(k['over %'], k['fav H1'])[0,1]:+.3f}")
    print(f"  corr(full-game residual, cell SUM):                    "
          f"{np.corrcoef(k['residual'], k['SUM'])[0,1]:+.3f}")
    print("\n  A near-zero first correlation with a solid over rate in the recent")
    print("  seasons is the compensation pattern: the aggregate error persists")
    print("  while which component produces it moves around.")


if __name__ == "__main__":
    main()
