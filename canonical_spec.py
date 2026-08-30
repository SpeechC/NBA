import sys; sys.path.insert(0,"/home/dpope/projects/nba_entropy_replication")
import warnings,numpy as np,pandas as pd; warnings.filterwarnings("ignore")
from scipy.stats import norm
SP="/tmp/claude-1000/-home-dpope/4fa2e81b-35e9-49e8-92da-7bffe4f69700/scratchpad/"
S=pd.read_csv(SP+"oracle_panel.csv"); S["date"]=pd.to_datetime(S.date)
S=S.sort_values("date").reset_index(drop=True)
S["actual"]=S.PTS_H+S.PTS_R; S["EffSum"]=S.sOH+S.sOR
S["P_book"]=np.nan
for y in sorted(S.yr.unique()):
    tr=S[S.yr<y]; te=S[S.yr==y]
    if len(tr)<400 or not len(te): continue
    X=np.column_stack([np.ones(len(tr)),tr.sP.values*tr.EffSum.values/100])
    b,*_=np.linalg.lstsq(X,tr.open.values,rcond=None)
    S.loc[te.index,"P_book"]=100*(te.open.values-b[0])/(b[1]*te.EffSum.values)
S["PaceGapPoints"]=(S.sP-S.P_book)*S.EffSum/100
T=S[S.yr>=2022].dropna(subset=["PaceGapPoints","actual","open"]).copy()
T["y"]=T.actual-T.open; T["push"]=(T.actual==T.open)
print(f"CANONICAL SPECIFICATION — maximal eligible sample")
print(f"  n = {len(T):,}   seasons {T.yr.min()}-{T.yr.max()}")
print(f"  pushes (actual == open): {T.push.sum()} ({100*T.push.mean():.2f}%)")
X=np.column_stack([np.ones(len(T)),T.PaceGapPoints]); yy=T.y.values
b,*_=np.linalg.lstsq(X,yy,rcond=None); r=yy-X@b
se=np.sqrt(np.diag((r@r/(len(yy)-2))*np.linalg.pinv(X.T@X)))
print(f"\n  PRIMARY:  Actual-Open ~ PaceGapPoints")
print(f"    beta {b[1]:+.4f}   se {se[1]:.4f}   t {b[1]/se[1]:+.2f}   95% CI [{b[1]-1.96*se[1]:+.4f},{b[1]+1.96*se[1]:+.4f}]")
# HC1 robust SEs
h=np.diag(X@np.linalg.pinv(X.T@X)@X.T); u=r/np.sqrt(np.maximum(1-h,1e-9))
V=np.linalg.pinv(X.T@X)@(X.T@np.diag(u**2)@X)@np.linalg.pinv(X.T@X)
print(f"    HC1 robust se {np.sqrt(V[1,1]):.4f}   t {b[1]/np.sqrt(V[1,1]):+.2f}")
sg=np.sign(T.PaceGapPoints); nz=sg!=0
win=((T.y*sg)>0)&nz; push=(T.y==0)&nz
hit=win.sum()/max((nz.sum()-push.sum()),1)
print(f"\n  ECONOMIC (bet the sign, no threshold, pushes voided):")
print(f"    bets {nz.sum()-push.sum():,}   pushes {push.sum()}   hit {100*hit:.2f}%"
      f"   ROI {100*(1.90909*hit-1):+.2f}%   break-even 52.381%")
sehit=np.sqrt(hit*(1-hit)/(nz.sum()-push.sum()))
print(f"    se(hit) {100*sehit:.2f}pp   95% CI [{100*(hit-1.96*sehit):.2f}%, {100*(hit+1.96*sehit):.2f}%]")
print(f"\n  DESCRIPTIVE magnitude bins (frozen now, NOT tunable):")
T["bin"]=pd.cut(T.PaceGapPoints,[-99,-4,-2,0,2,4,99],
                labels=["<-4","-4:-2","-2:0","0:+2","+2:+4",">+4"])
print(f"    {'bin':<10}{'n':>6}{'mean gap':>10}{'mean actual-open':>18}{'hit (signed)':>14}")
for k in T.bin.cat.categories:
    s=T[T.bin==k]
    sgn=np.sign(s.PaceGapPoints); w=((s.y*sgn)>0).mean()
    print(f"    {str(k):<10}{len(s):>6}{s.PaceGapPoints.mean():>10.2f}{s.y.mean():>+18.3f}{100*w:>13.1f}%")
print(f"\n  POWER for 2026-27 (~1,230 games):")
se1=se[1]*np.sqrt(len(T)/1230)
print(f"    se at n=1,230 = {se1:.4f}   MDE(80%, one-sided) = {2.487*se1:.4f}")
print(f"    discovery beta {b[1]:.4f} -> {'POWERED' if b[1]>2.487*se1 else 'UNDERPOWERED'}")
