"""COHESION STRUCTURE CHECKS — before the prereg. Feature + market cols only."""
import warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
from prepare_data import read_master, season_label

c = pd.read_csv("cohesion_panel.csv")
c["gid"] = c.gid.astype(str).str.strip()
raw = read_master(verbose=False); raw["season"] = season_label(raw)
raw = raw[raw["season"].astype(str).str.contains("Regular Season|In-Season", na=False)].copy()
m = pd.DataFrame({"gid": raw["GAME-ID"].astype(str).str.strip().values,
                  "season_m": raw["season"].astype(str).values})
j = c.merge(m, on="gid", how="inner")
print(f"=== GATE 1 CONTENT — cohesion games {c.gid.nunique():,}; "
      f"joined to master {j.gid.nunique():,} ===")
print("  seasons after join:", sorted(j.season.unique()))

print("\n=== GATE 2 RANGE ===")
print(f"  cohesion  min {c.cohesion.min():.3f}  max {c.cohesion.max():.3f}  "
      f"NaN {int(c.cohesion.isna().sum())}")
print(f"  rot_size  {c.rot_size.value_counts().sort_index().to_dict()}")
print(f"  gameno    min {c.gameno.min()}  max {c.gameno.max()}")

print("\n=== GATE 3 ERA STABILITY ===")
print(f"  {'season':<10}{'gameteams':>11}{'mean':>8}{'sd':>7}{'p10':>8}{'p90':>8}")
r=[]
for s,g in c.groupby("season"):
    r.append((len(g), g.cohesion.mean(), g.cohesion.std()))
    print(f"  {s:<10}{len(g):>11,}{g.cohesion.mean():>8.3f}{g.cohesion.std():>7.3f}"
          f"{g.cohesion.quantile(.1):>8.3f}{g.cohesion.quantile(.9):>8.3f}")
a=np.array(r,float)
print(f"  ratios: rows {a[:,0].max()/a[:,0].min():.2f}x  mean "
      f"{a[:,1].max()/a[:,1].min():.2f}x  sd {a[:,2].max()/a[:,2].min():.2f}x")

print("\n=== THE CONFOUND — cohesion rises mechanically through the season ===")
b = pd.cut(c.gameno, [0,10,20,40,60,82], include_lowest=True)
print(c.groupby(b).cohesion.agg(["size","mean","std"]).to_string())
print(f"  corr(cohesion, gameno) = {c.cohesion.corr(c.gameno):+.4f}")
print(f"  corr within season-decile of gameno, residualised: ", end="")
x = c.dropna(subset=["cohesion"])
res = x.cohesion - x.groupby(pd.cut(x.gameno,20)).cohesion.transform("mean")
print(f"sd raw {x.cohesion.std():.3f} -> sd after removing gameno mean {res.std():.3f}")
