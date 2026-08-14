"""Half-level aggregates from the advanced play-by-play, cached once.

  from pbp_rows     possessions and points, per game x half
  from event_rows   fouls, shooting fouls and FTA, per game x half

Regular season only (the _po playoff files are skipped). Development plus
2024-25; there is no 2025-26 play-by-play.
"""
import glob
import os
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

PBP = "/mnt/c/NBA2/advanced_stats/pbp_rows"
EVT = "/mnt/c/NBA2/advanced_stats/event_rows"
OUT = "pbp_halves.csv"


def _files(d, pat):
    return sorted(f for f in glob.glob(f"{d}/{pat}")
                  if "_po_" not in os.path.basename(f))


def build(force=False):
    if os.path.exists(OUT) and not force:
        return pd.read_csv(OUT, dtype={"gid": str})

    poss = []
    for f in _files(PBP, "pbpstats_*_advanced.csv"):
        d = pd.read_csv(f, low_memory=False, usecols=[
            "GAMEID", "PERIOD", "ADV_IS_POSSESSION_FIRST_ROW",
            "ADV_POINTS_POSS_CALC"])
        d = d[(d["ADV_IS_POSSESSION_FIRST_ROW"] == 1) & (d["PERIOD"] <= 4)]
        d["half"] = np.where(d["PERIOD"] <= 2, 1, 2)
        g = d.groupby(["GAMEID", "half"], as_index=False).agg(
            poss=("ADV_POINTS_POSS_CALC", "size"),
            pts=("ADV_POINTS_POSS_CALC", "sum"))
        poss.append(g)
        print(f"  poss {os.path.basename(f):32} {len(d):8,} -> {len(g):5,}",
              flush=True)
    P = pd.concat(poss, ignore_index=True).rename(columns={"GAMEID": "gid"})

    ev = []
    for f in _files(EVT, "nbastats_*_advanced.csv"):
        d = pd.read_csv(f, low_memory=False, usecols=[
            "GAME_ID", "PERIOD", "ADV_IS_FOUL", "ADV_IS_SHOOTING_FOUL",
            "ADV_IS_FTA"])
        d = d[d["PERIOD"] <= 4]
        d["half"] = np.where(d["PERIOD"] <= 2, 1, 2)
        g = d.groupby(["GAME_ID", "half"], as_index=False).agg(
            fouls=("ADV_IS_FOUL", "sum"),
            sfouls=("ADV_IS_SHOOTING_FOUL", "sum"),
            fta=("ADV_IS_FTA", "sum"))
        ev.append(g)
        print(f"  evt  {os.path.basename(f):32} {len(d):8,} -> {len(g):5,}",
              flush=True)
    E = pd.concat(ev, ignore_index=True).rename(columns={"GAME_ID": "gid"})

    for x in (P, E):
        x["gid"] = x["gid"].astype(str).str.strip()
    A = P.merge(E, on=["gid", "half"], how="inner")
    W = A.pivot(index="gid", columns="half",
                values=["poss", "pts", "fouls", "sfouls", "fta"])
    W.columns = [f"{a}_h{b}" for a, b in W.columns]
    W = W.reset_index().dropna()
    for v in ("poss", "pts", "fouls", "sfouls", "fta"):
        W[f"{v}_fg"] = W[f"{v}_h1"] + W[f"{v}_h2"]
    W["h1_poss_share"] = W["poss_h1"] / W["poss_fg"]
    W.to_csv(OUT, index=False)
    return W


def main():
    W = build(force=True)
    print(f"\n{len(W):,} games with both halves")
    for v in ("poss", "pts", "fouls", "fta"):
        print(f"  {v:6} H1 {W[f'{v}_h1'].mean():8.3f}   "
              f"H2 {W[f'{v}_h2'].mean():8.3f}   "
              f"H2-H1 {W[f'{v}_h2'].mean()-W[f'{v}_h1'].mean():+8.3f}")
    print(f"  H1 possession share: mean {W['h1_poss_share'].mean():.4f}  "
          f"sd {W['h1_poss_share'].std():.4f}")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
