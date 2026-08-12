"""Are lines less efficient early in the season?

The mechanism is plausible and nameable: at tip-off the book has no current-season
data, so its ratings are priors built from last season plus offseason
adjustments. Rosters turn over, rotations are unsettled, and the prior may be
systematically wrong until enough games arrive to correct it.

Four checks, because "less efficient" can mean two different things and only one
of them is tradeable:

  1 BIAS      Is there a DIRECTIONAL error early -- overs, unders, favourites or
              dogs? This is the only version that pays.
  2 VARIANCE  Are residuals merely WIDER early? A book that is uncertain and
              knows it is not mispriced, just noisy. Wider residuals with no
              directional bias is a non-finding, and is the likeliest outcome.
  3 MOVEMENT  Does the line move more between open and close early? Large moves
              mean the market is actively learning, which is evidence the OPENER
              is soft even if the CLOSE is not.
  4 LEARNING  Does the bias shrink as team-games accumulate? A prior being
              corrected should decay smoothly, not switch off.

Measured against the CLOSE unless stated. Uses raw odds so game 1 is included --
the modelling panel has a six-game feature burn-in that would discard exactly the
games this asks about.
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
    raw["season"] = season_label(raw).astype(str)
    d = raw[raw["season"].str.contains("Regular Season", na=False)].copy()
    d["date"] = pd.to_datetime(d["DATE"], errors="coerce")
    d["close_total"] = pd.to_numeric(d["CLOSING TOTAL_H"], errors="coerce")
    d["open_total"] = pd.to_numeric(d["OPENING TOTAL_H"], errors="coerce")
    d["spread"] = pd.to_numeric(d["CLOSING SPREAD_H"], errors="coerce")
    d["open_spread"] = pd.to_numeric(d["OPENING SPREAD_H"], errors="coerce")
    d["actual"] = d["PTS_H"] + d["PTS_R"]
    d["margin"] = d["PTS_H"] - d["PTS_R"]
    d = d.dropna(subset=["close_total", "spread", "date", "actual"])
    d = d[d["close_total"].between(150, 300)]
    d["r_total"] = d["actual"] - d["close_total"]
    d["home_cover"] = d["margin"] + d["spread"]
    d["dog_cover"] = np.where(d["spread"] > 0, d["home_cover"], -d["home_cover"])
    d["tot_move"] = (d["close_total"] - d["open_total"]).abs()
    d["spr_move"] = (d["spread"] - d["open_spread"]).abs()
    d = d.sort_values("date")

    # team-games played before this game, per side; use the smaller of the two
    h = d[["date", "season", "TEAM_H"]].rename(columns={"TEAM_H": "team"})
    a = d[["date", "season", "TEAM_R"]].rename(columns={"TEAM_R": "team"})
    L = pd.concat([h, a]).sort_values("date")
    L["g"] = L.groupby(["season", "team"]).cumcount()
    d = d.merge(L.rename(columns={"team": "TEAM_H", "g": "g_h"}),
                on=["season", "TEAM_H", "date"], how="left")
    d = d.merge(L.rename(columns={"team": "TEAM_R", "g": "g_a"}),
                on=["season", "TEAM_R", "date"], how="left")
    d["gp"] = d[["g_h", "g_a"]].min(axis=1)
    return d


def blk(s, lab, col, flip=False):
    r = s[col]
    hit = (r > 0).mean()
    se = np.sqrt(hit * (1 - hit) / len(s))
    return {"window": lab, "n": len(s), "mean resid": round(r.mean(), 3),
            "hit %": round(100 * hit, 2),
            "95% CI": f"[{100*(hit-1.96*se):.1f}, {100*(hit+1.96*se):.1f}]",
            "ROI110": round(100 * (hit * (100 / 110) - (1 - hit)), 2),
            "sd": round(r.std(), 2)}


def main():
    d = load()
    d = d[d["dog_cover"] != 0]
    print(f"{len(d):,} games, {d['season'].nunique()} seasons\n")

    bands = [(0, 3), (3, 6), (6, 10), (10, 20), (20, 40), (40, 100)]
    labs = ["first 3", "4-6", "7-10", "11-20", "21-40", "41+"]

    for col, name in (("r_total", "TOTALS — over rate"),
                      ("dog_cover", "SPREADS — underdog cover rate")):
        print("=" * 96)
        print(f"1/2. {name} by team-games played")
        print("=" * 96)
        rows = []
        for (lo, hi), lab in zip(bands, labs):
            s = d[(d["gp"] >= lo) & (d["gp"] < hi)]
            if len(s) >= 100:
                rows.append(blk(s, lab, col))
        print(pd.DataFrame(rows).to_string(index=False))
        print(f"  break-even {100*BE:.2f}%\n")

    print("=" * 96)
    print("3. MOVEMENT — is the opener soft early?")
    print("=" * 96)
    rows = []
    for (lo, hi), lab in zip(bands, labs):
        s = d[(d["gp"] >= lo) & (d["gp"] < hi)]
        if len(s) >= 100:
            rows.append({"window": lab, "n": len(s),
                         "mean |total move|": round(s["tot_move"].mean(), 3),
                         "mean |spread move|": round(s["spr_move"].mean(), 3)})
    print(pd.DataFrame(rows).to_string(index=False))

    print("\n" + "=" * 96)
    print("4. First 10 games, by season (consistency)")
    print("=" * 96)
    early = d[d["gp"] < 10]
    print(early.groupby("season").apply(lambda x: pd.Series({
        "n": len(x),
        "over %": round(100 * (x["r_total"] > 0).mean(), 2),
        "dog cover %": round(100 * (x["dog_cover"] > 0).mean(), 2)}),
        include_groups=False).to_string())

    print("\n--- first 3 team-games only ---")
    e3 = d[d["gp"] < 3]
    for col, nm in (("r_total", "over"), ("dog_cover", "dog cover")):
        hit = (e3[col] > 0).mean()
        se = np.sqrt(hit * (1 - hit) / len(e3))
        t, p = stats.ttest_1samp(e3[col], 0)
        print(f"  {nm:10} n={len(e3):,}  {100*hit:.2f}%  "
              f"CI [{100*(hit-1.96*se):.1f}, {100*(hit+1.96*se):.1f}]  "
              f"resid t={t:+.2f} p={p:.3f}")

    print("\n--- residual sd: early vs late (is it just noisier?) ---")
    for col in ("r_total", "dog_cover"):
        a = d[d["gp"] < 10][col].std()
        b = d[d["gp"] >= 20][col].std()
        print(f"  {col:11} first 10 games sd {a:.2f}   after 20 games sd {b:.2f}"
              f"   ratio {a/b:.3f}")


if __name__ == "__main__":
    main()
