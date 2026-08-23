"""Joint-survival test for the agent's movement candidate
  S = HOME high PBP_H1_POSS_SHARE (20-game prior-only, upper 20%)
      x ROAD high SCHED_ROAD_TRIP_GAME (ordinal, upper 20%)
against the FROZEN incumbent movement sources in move_signal_states.csv.

THE QUESTION. The agent reports "signed incremental beta" relative to ITS OWN
baseline. The question that decides whether the candidate is worth another
validation season is different: does it survive ALONGSIDE MOVE_RIDGE_OOS and
MOVE_LATENT_OOS?  PBP_H1_POSS_SHARE is a pace-family feature and the frozen
ridge already carries f_PACE / f_OEFF / f_DEFF and opponent versions, so
absorption is the live possibility.

RECIPE, reimplemented independently (not taken from the agent):
  home_h1share  = team's own H1 possession share, shift(1).rolling(20, min 10),
                  within season, taken from whichever side the team played
  road_trip     = the visitor's count of CONSECUTIVE away games including this
                  one (resets on any home game), known pregame from the schedule
  cell          = home_h1share >= q80  AND  road_trip >= q80   (thresholds
                  FROZEN on seasons <= 2023, evaluated later)

TARGET: open->close total movement (tmove), the same object MOVE_COMBINED
forecasts. Tests: candidate alone, then jointly with the two incumbents, on
the agent's validation season (2024-25), the unused season (2025-26), and
pooled. Nothing is tuned; the only free choice (threshold window) is frozen
before any joint regression is run.
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import opening_line_error_decomposition as OLE

ADV = "/mnt/c/NBA2/advanced_stats/game_advanced_stats.csv"
SIDECAR = "/mnt/c/NBA2/move_signal_states.csv"
W, MINP = 20, 10
FREEZE_MAX = 2023


def build():
    g = OLE.load()
    a = pd.read_csv(ADV, low_memory=False)
    a["gid"] = a["GAME-ID"].astype(str).str.strip()
    g = g.merge(a[["gid", "PBP_H1_POSS_SHARE_H", "PBP_H1_POSS_SHARE_R"]],
                on="gid", how="left")

    # team-game panel: own H1 possession share, and home/away flag
    rows = []
    for side, col in (("home", "PBP_H1_POSS_SHARE_H"),
                      ("away", "PBP_H1_POSS_SHARE_R")):
        rows.append(pd.DataFrame({
            "gid": g["gid"], "season": g["season"], "date": g["date"],
            "team": g[side], "is_home": int(side == "home"),
            "h1share": pd.to_numeric(g[col], errors="coerce")}))
    L = pd.concat(rows).sort_values(["date", "gid"]).reset_index(drop=True)

    # prior-only 20-game H1 share
    L["prior_h1"] = L.groupby(["season", "team"])["h1share"].transform(
        lambda s: s.shift(1).rolling(W, min_periods=MINP).mean())

    # consecutive away-game counter (pregame-known, from the schedule)
    L = L.sort_values(["season", "team", "date"])
    grp = L.groupby(["season", "team"], group_keys=False)
    L["road_trip"] = grp["is_home"].apply(
        lambda s: (1 - s).groupby(s.cumsum()).cumsum())

    home = L[L["is_home"] == 1][["gid", "prior_h1"]].rename(
        columns={"prior_h1": "home_h1"})
    away = L[L["is_home"] == 0][["gid", "road_trip"]]
    d = g[["gid", "season", "date", "tmove"]].merge(home, on="gid").merge(
        away, on="gid")

    sc = pd.read_csv(SIDECAR)
    sc["gid"] = sc["GAME-ID"].astype(str).str.strip()
    d = d.merge(sc[["gid", "MOVE_RIDGE_OOS", "MOVE_LATENT_OOS"]], on="gid",
                how="left")
    return d.dropna(subset=["home_h1", "road_trip", "tmove"])


def ols_t(y, X, names):
    A = np.column_stack([np.ones(len(y))] + X)
    b, *_ = np.linalg.lstsq(A, y, rcond=None)
    r = y - A @ b
    se = np.sqrt(np.diag(np.linalg.pinv(A.T @ A)) * (r @ r)
                 / (len(y) - A.shape[1]))
    r2 = 1 - r.var() / y.var()
    return b, b / se, r2


def main():
    d = build()
    fr = d[d["season"] <= FREEZE_MAX]
    q_h1 = fr["home_h1"].quantile(0.80)
    q_rt = fr["road_trip"].quantile(0.80)
    d["cell"] = ((d["home_h1"] >= q_h1) & (d["road_trip"] >= q_rt)).astype(float)
    print(f"  {len(d):,} games   FROZEN (seasons<={FREEZE_MAX}) thresholds: "
          f"H1 share >= {q_h1:.4f}   road-trip game >= {q_rt:.0f}")
    print(f"  road-trip distribution: "
          f"{d['road_trip'].value_counts().sort_index().head(6).to_dict()}")
    print(f"  cell fires on {int(d['cell'].sum()):,} games "
          f"({100*d['cell'].mean():.1f}%)   by season: "
          f"{d.groupby('season')['cell'].sum().astype(int).to_dict()}")

    have = d.dropna(subset=["MOVE_RIDGE_OOS", "MOVE_LATENT_OOS"])
    print(f"  with both incumbent signals: {len(have):,} games "
          f"(seasons {sorted(have['season'].unique())})")

    windows = [("2024-25 (agent's validation)", have[have["season"] == 2024]),
               ("2025-26 (UNUSED season)", have[have["season"] == 2025]),
               ("pooled 2021-2025", have)]

    print("\n" + "=" * 96)
    print("CANDIDATE ALONE  vs  JOINT WITH THE FROZEN INCUMBENTS")
    print("  target: open->close total movement")
    print("=" * 96)
    for lab, x in windows:
        if len(x) < 100:
            continue
        y = x["tmove"].values
        b1, t1, r2a = ols_t(y, [x["cell"].values], ["cell"])
        b2, t2, r2b = ols_t(
            y, [x["MOVE_RIDGE_OOS"].values, x["MOVE_LATENT_OOS"].values,
                x["cell"].values], ["ridge", "latent", "cell"])
        b3, t3, r2c = ols_t(
            y, [x["MOVE_RIDGE_OOS"].values, x["MOVE_LATENT_OOS"].values],
            ["ridge", "latent"])
        print(f"\n  {lab}   n={len(x):,}  cell fires {int(x['cell'].sum())}")
        print(f"    candidate ALONE      beta {b1[1]:+.4f} (t={t1[1]:+.2f})"
              f"   R2 {r2a:+.5f}")
        print(f"    incumbents only                              "
              f"      R2 {r2c:+.5f}")
        print(f"    JOINT   ridge {b2[1]:+.4f} (t={t2[1]:+.2f})   "
              f"latent {b2[2]:+.4f} (t={t2[2]:+.2f})   "
              f"cell {b2[3]:+.4f} (t={t2[3]:+.2f})")
        print(f"            R2 {r2b:+.5f}   incremental R2 from the cell "
              f"{r2b-r2c:+.6f}")

    print("\n" + "=" * 96)
    print("IS THE CANDIDATE ALREADY INSIDE THE INCUMBENTS?")
    print("=" * 96)
    x = have
    for nm, col in (("MOVE_RIDGE_OOS", "MOVE_RIDGE_OOS"),
                    ("MOVE_LATENT_OOS", "MOVE_LATENT_OOS")):
        b, t, r2 = ols_t(x[col].values, [x["cell"].values], ["cell"])
        print(f"  {nm:18} ~ cell:  beta {b[1]:+.4f} (t={t[1]:+.2f})"
              f"   [nonzero => the incumbent already encodes this state]")
    print(f"  mean predicted move in cell vs rest: "
          f"ridge {x[x.cell==1]['MOVE_RIDGE_OOS'].mean():+.3f} vs "
          f"{x[x.cell==0]['MOVE_RIDGE_OOS'].mean():+.3f}   "
          f"latent {x[x.cell==1]['MOVE_LATENT_OOS'].mean():+.3f} vs "
          f"{x[x.cell==0]['MOVE_LATENT_OOS'].mean():+.3f}")


if __name__ == "__main__":
    main()
