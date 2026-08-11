"""Development and holdout anchors under the fixed date-based split."""
import warnings, numpy as np, pandas as pd
warnings.filterwarnings("ignore")
import data_split as ds
from models_frozen import SPECS, add_pace_terms, walk_forward
from symmetric_features import build

G = add_pace_terms(build()).sort_values("date").reset_index(drop=True)

def met(s):
    if len(s) < 25: return None
    over=(s["actual_total"]>s["open_total"]).values
    win=np.where((s["pm"]>0).values, over, ~over).astype(float)
    clv=np.where(s["pm"]>0, s["move_total"], -s["move_total"])
    n,w=len(win),win.mean(); se=clv.std()/np.sqrt(n)
    return {"n":n,"CLV":round(clv.mean(),3),"lo":round(clv.mean()-1.96*se,3),
            "hi":round(clv.mean()+1.96*se,3),"beat%":round(100*(clv>0).mean(),2),
            "win%":round(100*w,2),"ROI110":round(100*(w*(100/110)-(1-w)),2),
            "ROI105":round(100*(w*(100/105)-(1-w)),2)}

for spec in ("A","D"):
    feats = SPECS[spec]
    d = G.dropna(subset=feats+["move_total","actual_total","open_total"]).sort_values("date").reset_index(drop=True)
    d["pm"] = walk_forward(d[feats].values, d["move_total"].values.astype(float), d["date"].values)
    d = d.dropna(subset=["pm"]).copy()
    dev, ho = ds.split(d)
    print("="*104); print(f"SPEC {spec}   scored panel {len(d):,}"); print("="*104)
    print(ds.describe(d).to_string(index=False)); print()
    rows=[]
    sets = [("DEV 2019-2024", dev),
            ("HO 2024-25", ho[ho["date"]<"2025-07-01"]),
            ("HO 2025-26", ho[ho["date"]>="2025-07-01"]),
            ("HO pooled",  ho)]
    for th in (1.00,1.25,1.50,2.00):
        for lab,sub in sets:
            b = sub[(sub["pm"].abs()>th)&(sub["actual_total"]!=sub["open_total"])]
            m = met(b)
            if m: rows.append({"set":lab,"thr":th,**m})
    t=pd.DataFrame(rows).sort_values(["thr","set"])
    print(t.to_string(index=False)); print()
    t.to_csv(f"split_anchors_{spec}.csv",index=False)
