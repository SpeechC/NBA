"""Exactly which games the frozen model sees, season by season.

Three populations, and they are not the same thing:
  SOURCE  games in the odds export
  PANEL   games that survive feature construction (usable as TRAINING data)
  SCORED  games that additionally carry a walk-forward prediction (evaluated)
"""
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import data_split as ds
from models_frozen import SPECS, add_pace_terms, walk_forward
from prepare_data import CSV, season_label
from symmetric_features import build

raw = pd.read_csv(CSV, low_memory=False)
raw["_season"] = season_label(raw).astype(str)
raw["_date"] = pd.to_datetime(raw["DATE"], errors="coerce")
src = raw[raw["_season"].str.contains("Regular Season|In-Season", na=False)]
src_n = src.groupby("_season").size()

G = add_pace_terms(build()).sort_values("date").reset_index(drop=True)
feats = SPECS["A"]
d = G.dropna(subset=feats + ["move_total", "actual_total", "open_total"])
d = d.sort_values("date").reset_index(drop=True)
d["pm"] = walk_forward(d[feats].values, d["move_total"].values.astype(float),
                       d["date"].values)

pan_n = G.groupby(G["season"].astype(str)).size()
sc_n = d.dropna(subset=["pm"]).groupby(lambda i: str(d.loc[i, "season"])).size()

rows = []
for s in sorted(set(src_n.index) | set(pan_n.index)):
    rows.append({"season": s, "source": int(src_n.get(s, 0)),
                 "panel (trainable)": int(pan_n.get(s, 0)),
                 "scored (evaluated)": int(sc_n.get(s, 0))})
t = pd.DataFrame(rows)
t["missing"] = t["source"] - t["panel (trainable)"]
print(t.to_string(index=False))
print(f"\nTOTAL source {t['source'].sum():,}   panel {t['panel (trainable)'].sum():,}"
      f"   scored {t['scored (evaluated)'].sum():,}")

dev_panel = ds.dev(G)
dev_scored = ds.dev(d.dropna(subset=["pm"]))
print(f"\nDEVELOPMENT panel  {len(dev_panel):,} games  "
      f"{dev_panel['date'].min().date()} .. {dev_panel['date'].max().date()}")
print(f"DEVELOPMENT scored {len(dev_scored):,} games  "
      f"{dev_scored['date'].min().date()} .. {dev_scored['date'].max().date()}")

print("\n--- playoff / play-in games in the source, all excluded ---")
po = raw[raw["_season"].str.contains("Playoffs|Play-in|Play-In", na=False)]
print(f"{len(po):,} games across {po['_season'].nunique()} labels")
