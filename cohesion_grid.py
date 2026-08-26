"""ROBUSTNESS: does P1 survive the parameter choices I fixed in advance?

ROT_W and TOPN were pre-registered, not searched. This sweep asks whether the
pre-registered cell is special. If most cells show the effect, it is robust; if
only mine does, it is mining. Reported either way.
"""
import sys, warnings, itertools
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
import cohesion_build as CB

def run(rot_w, topn):
    CB.ROT_W, CB.TOPN = rot_w, topn
    out=[]
    for s in ["2017-18","2018-19","2020-21","2021-22","2022-23","2023-24","2024-25"]:
        out.append(CB.cohesion_for_season(s))
    d=pd.concat(out, ignore_index=True)
    n=d.groupby("gid").size()
    return d[d.gid.isin(n[n==2].index)]

import cohesion as CH
rows=[]
for rot_w, topn in [(5,10),(3,10),(10,10),(5,8),(5,12)]:
    panel=run(rot_w,topn)
    panel.to_csv("cohesion_panel.csv", index=False)
    d=CH.build(); dv=d[d.is_dev]
    x=dv.dropna(subset=["dev_s","C_diff"]+CH.CTRL)
    b,t,n=CH.ols_t(x.dev_s.values,[x.C_diff.values]+[x[c].values for c in CH.CTRL])
    ho=d[~d.is_dev].dropna(subset=["dev_s","C_diff"]+CH.CTRL)
    bh,th,nh=CH.ols_t(ho.dev_s.values,[ho.C_diff.values]+[ho[c].values for c in CH.CTRL])
    xp=dv.dropna(subset=["actual_margin","C_diff"]+CH.CTRL)
    bp,tp,_=CH.ols_t(xp.actual_margin.values,[xp.C_diff.values]+[xp[c].values for c in CH.CTRL])
    tag="  <-- PRE-REGISTERED" if (rot_w,topn)==(5,10) else ""
    rows.append((rot_w,topn,n,b[1],t[1],bh[1],th[1],bp[1],tp[1]))
    print(f"  ROT_W={rot_w:<3} TOPN={topn:<3} n={n:,}  DEV beta {b[1]:+.4f} (t={t[1]:+.2f})"
          f"   HOLDOUT beta {bh[1]:+.4f} (t={th[1]:+.2f})"
          f"   P3 margin {bp[1]:+.2f} (t={tp[1]:+.1f}){tag}", flush=True)

a=np.array([(r[3],r[5]) for r in rows])
print(f"\n  DEV betas positive in {int((a[:,0]>0).sum())}/{len(a)} cells; "
      f"HOLDOUT positive in {int((a[:,1]>0).sum())}/{len(a)}")
print(f"  pre-registered cell rank among DEV betas: "
      f"{sorted(a[:,0], reverse=True).index(a[0,0])+1} of {len(a)}")
