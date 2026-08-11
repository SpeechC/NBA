"""Split the mismatch findings by development / holdout."""
import warnings, numpy as np, pandas as pd
from scipy import stats
warnings.filterwarnings("ignore")
import data_split as ds
from mismatch import build

d = build()
d = ds.tag(d)
print(f"{len(d):,} games   dev {int((~d['is_holdout']).sum()):,}   "
      f"holdout {int(d['is_holdout'].sum()):,}\n")

def rep(sub, label):
    live = sub[sub["total_pts"] != sub["CLOSING TOTAL_H"]]
    pf = sub[sub["fav_cover"] != 0]
    if len(live) < 30:
        return None
    ov = (live["over"] > 0).mean()
    se = np.sqrt(ov*(1-ov)/len(live))
    return {"set": label, "n": len(sub),
            "actual-close": round(sub["over"].mean(), 3),
            "over %": round(100*ov, 2),
            "over lo": round(100*(ov-1.96*se), 2),
            "over hi": round(100*(ov+1.96*se), 2),
            "ROI over @-110 %": round(100*(ov*(100/110)-(1-ov)), 2),
            "fav cover %": round(100*(pf["fav_cover"] > 0).mean(), 2)}

for name, f in (("|spread| >= 10", lambda x: x["spread_gap"] >= 10),
                ("|spread| >= 12", lambda x: x["spread_gap"] >= 12),
                ("|spread| >= 14", lambda x: x["spread_gap"] >= 14),
                ("wl gap > 0.35",  lambda x: x["wl_gap"] > 0.35)):
    sub = d[f(d)]
    rows = [r for r in (rep(sub[~sub["is_holdout"]], "DEV 2017-2024"),
                        rep(sub[sub["is_holdout"]], "HOLDOUT 2024-26"),
                        rep(sub, "pooled")) if r]
    print("="*96); print(name); print("="*96)
    print(pd.DataFrame(rows).to_string(index=False)); print()

print("="*96)
print("Season by season, |spread| >= 12")
print("="*96)
s12 = d[d["spread_gap"] >= 12].copy()
s12["yr"] = np.where(s12["date"].dt.month >= 7, s12["date"].dt.year,
                     s12["date"].dt.year - 1)
rows=[]
for y, sub in s12.groupby("yr"):
    live = sub[sub["total_pts"] != sub["CLOSING TOTAL_H"]]
    if len(live) < 20: continue
    ov = (live["over"] > 0).mean()
    rows.append({"season": f"{y}-{y+1}", "n": len(sub),
                 "actual-close": round(sub["over"].mean(), 2),
                 "over %": round(100*ov, 2),
                 "holdout": bool(sub["is_holdout"].iloc[0])})
print(pd.DataFrame(rows).to_string(index=False))
