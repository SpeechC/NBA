"""Full threshold ladder, development only, current data vintage."""
import warnings, numpy as np, pandas as pd
warnings.filterwarnings("ignore")
import data_split as ds
from models_frozen import SPECS, BACKTEST, add_pace_terms, walk_forward
from symmetric_features import build

G = add_pace_terms(build()).sort_values("date").reset_index(drop=True)
THR = [0.0,0.25,0.50,0.75,1.00,1.25,1.50,1.75,2.00]
out={}
for spec in ("A","D"):
    feats=SPECS[spec]
    d=G.dropna(subset=feats+["move_total","actual_total","open_total"]).sort_values("date").reset_index(drop=True)
    d["pm"]=walk_forward(d[feats].values,d["move_total"].values.astype(float),d["date"].values)
    d=d.dropna(subset=["pm"]).copy()
    dev,_=ds.split(d)
    ds.assert_no_holdout(dev, what=f"spec {spec} development ladder")
    rows=[]
    for th in THR:
        b=dev[(dev["pm"].abs()>th)&(dev["actual_total"]!=dev["open_total"])]
        over=(b["actual_total"]>b["open_total"]).values
        win=np.where((b["pm"]>0).values,over,~over).astype(float)
        w=win.mean(); roi=100*(w*(100/110)-(1-w))
        clv=np.where(b["pm"]>0,b["move_total"],-b["move_total"])
        rows.append({"thr":th,"n":len(b),"CLV":round(clv.mean(),3),
                     "win%":round(100*w,2),"ROI110":round(roi,2),
                     "frozen ROI":BACKTEST[spec][th],
                     "drift":round(roi-BACKTEST[spec][th],2)})
    t=pd.DataFrame(rows)
    print(f"\n=== SPEC {spec} — development only ({len(dev):,} games) ===")
    print(t.to_string(index=False))
    out[spec]={r["thr"]:r["ROI110"] for r in rows}
print("\n\nBACKTEST_CURRENT = {")
for s in ("A","D"):
    print(f'    "{s}": {{' + ", ".join(f"{k}: {v:+.2f}" for k,v in out[s].items()) + "},")
print("}")
