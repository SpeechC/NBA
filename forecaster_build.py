"""Panel for PREREG_probabilistic_forecaster. Frozen inputs only."""
import warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
from prepare_data import read_master, season_label


def build():
    raw = read_master(verbose=False); raw["season"] = season_label(raw).astype(str)
    raw = raw[raw.season.str.contains("Regular Season", na=False)].copy()
    n = lambda c: pd.to_numeric(raw[c], errors="coerce")
    d = pd.DataFrame({
        "gid": raw["GAME-ID"].astype(str).str.strip(),
        "season": raw.season.values,
        "date": pd.to_datetime(raw["DATE"], errors="coerce"),
        "close": n("CLOSING TOTAL_H"),
        "actual": n("PTS_H") + n("PTS_R")}).dropna()
    d = d[d.close.between(150, 300)]
    d["yr"] = d.season.str.extract(r"(\d{4})")[0].astype(int)
    # final7 — from the schedule of PLAYED games, matching CLOSING.md's definition
    d["days_left"] = (d.groupby("season")["date"].transform("max") - d["date"]).dt.days
    d["final7"] = (d.days_left <= 7).astype(float)

    rf = pd.read_csv("ref_features.csv"); rf["gid"] = rf.gid.astype(str).str.strip()
    d = d.merge(rf[["gid", "CrewShock"]].drop_duplicates("gid"), on="gid", how="left")

    s = pd.read_csv("/mnt/c/NBA2/move_signal_states.csv")
    s["gid"] = s["GAME-ID"].astype(str).str.strip()
    d = d.merge(s[["gid", "MOVE_COMBINED_OOS"]].drop_duplicates("gid"),
                on="gid", how="left").rename(columns={"MOVE_COMBINED_OOS": "m"})

    d["dev"] = d.actual - d.close
    d = d.dropna(subset=["m", "CrewShock"])          # all three inputs required
    d = d[d.dev != 0]                                 # pushes carry no outcome
    d["y"] = (d.dev > 0).astype(int)
    return d.sort_values("date").reset_index(drop=True)


if __name__ == "__main__":
    d = build()
    print(f"panel with ALL THREE frozen inputs and a decided outcome: {len(d):,}")
    print(f"  seasons: {sorted(d.yr.unique())}")
    print(d.groupby("yr").agg(n=("y","size"), over=("y","mean"),
                              final7=("final7","sum")).to_string())
    print(f"\n  over rate overall {100*d.y.mean():.2f}%  "
          f"(baseline p=0.5 -> Brier {((0.5-d.y)**2).mean():.5f})")
    print(f"  m: sd {d.m.std():.3f}   CrewShock: sd {d.CrewShock.std():.3f}   "
          f"final7 fires {int(d.final7.sum()):,}")
