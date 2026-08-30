import sys; sys.path.insert(0,"/home/dpope/projects/nba_entropy_replication")
import warnings,numpy as np,pandas as pd; warnings.filterwarnings("ignore")
from scipy import stats
SP="/tmp/claude-1000/-home-dpope/4fa2e81b-35e9-49e8-92da-7bffe4f69700/scratchpad/"
S=pd.read_csv(SP+"pace_var2.csv"); S["date"]=pd.to_datetime(S.date)
S=S.sort_values("date").reset_index(drop=True)
S["actual"]=S.PTS_H+S.PTS_R; S["EffSum"]=S.sOH+S.sOR
# book-implied pace, a/b refit on PRIOR seasons only
S["P_book"]=np.nan
for y in sorted(S.yr.unique()):
    tr=S[S.yr<y]; te=S[S.yr==y]
    if len(tr)<400 or not len(te): continue
    X=np.column_stack([np.ones(len(tr)),tr.sP.values*tr.EffSum.values/100])
    b,*_=np.linalg.lstsq(X,tr.open.values,rcond=None)
    S.loc[te.index,"P_book"]=100*(te.open.values-b[0])/(b[1]*te.EffSum.values)
S["PaceGap"]=S.sP-S.P_book
S["PaceGapPoints"]=S.PaceGap*S.EffSum/100
T=S[(S.yr>=2022)].dropna(subset=["PaceGapPoints","volx","actual","close"]).copy()
T["y"]=T.actual-T.open; T["mv"]=T.close-T.open
# standardise volx so the interaction is interpretable
T["vz"]=(T.volx-T.volx.mean())/T.volx.std()
T["gz"]=T.PaceGapPoints
print(f"THE DECISIVE TEST — does the pace signal attenuate when pace is volatile?   n={len(T):,}")
def ols(cols,y="y",D=None):
    D=T if D is None else D
    X=np.column_stack([np.ones(len(D))]+[D[c].values for c in cols]); yy=D[y].values
    b,*_=np.linalg.lstsq(X,yy,rcond=None); r=yy-X@b
    se=np.sqrt(np.diag((r@r/(len(yy)-len(cols)-1))*np.linalg.pinv(X.T@X)))
    return b,se
b,se=ols(["gz"]); print(f"  baseline:  PaceGapPoints {b[1]:+.4f} (t={b[1]/se[1]:+.2f})")
T["ix"]=T.gz*T.vz
b,se=ols(["gz","vz","ix"])
print(f"  with interaction:")
for i,c in enumerate(["PaceGapPoints","volX (z)","GAP x volX"]):
    print(f"    {c:<18}{b[i+1]:>+9.4f} (t={b[i+1]/se[i+1]:>+5.2f})")
b3,se3=b[3],se[3]
print(f"  H: beta3 < 0 (signal weakens as volatility rises)")
print(f"    beta3 {b3:+.4f}  95% CI [{b3-1.96*se3:+.4f},{b3+1.96*se3:+.4f}]  one-sided p={stats.norm.cdf(b3/se3):.4f}")
print(f"    MDE(80% power, one-sided) = {2.487*se3:.4f}   -> {'POWERED' if 2.487*se3<abs(b[1])*0.5 else 'UNDERPOWERED for a 50% attenuation'}")
print()
print("SPLIT: the signal within volx terciles")
T["vq"]=pd.qcut(T.volx,3,labels=["low vol","mid","high vol"])
print(f"  {'volx tercile':<14}{'n':>6}{'beta(gap->actual)':>20}{'t':>7}{'beta(gap->move)':>18}{'t':>7}")
for k in ["low vol","mid","high vol"]:
    s=T[T.vq==k]
    b1,s1=ols(["gz"],"y",s); b2,s2=ols(["gz"],"mv",s)
    print(f"  {k:<14}{len(s):>6}{b1[1]:>20.4f}{b1[1]/s1[1]:>7.2f}{b2[1]:>18.4f}{b2[1]/s2[1]:>7.2f}")
print()
print("BUCKET GRID: pace-gap magnitude x pace volatility  (their table)")
T["gq"]=pd.qcut(T.gz.abs(),2,labels=["small gap","LARGE gap"])
print(f"  {'gap':<12}{'volatility':<12}{'n':>6}{'hit rate':>10}{'avg |edge|':>12}{'avg actual-open x sign':>24}")
for gk in ["small gap","LARGE gap"]:
    for vk in ["low vol","mid","high vol"]:
        s=T[(T.gq==gk)&(T.vq==vk)]
        if len(s)<80: continue
        sg=np.sign(s.gz); win=((s.y*sg)>0).mean()
        print(f"  {gk:<12}{vk:<12}{len(s):>6}{100*win:>9.1f}%{s.gz.abs().mean():>12.2f}{(s.y*sg).mean():>+24.3f}")
print(f"  break-even 52.381%")
print()
print("IS THE INTERACTION NECESSARY IN THE VARIANCE EQUATION?")
V=S.dropna(subset=["u","ewvH","ewvR"]).copy(); V["u2"]=V.u**2
V["vh"]=(V.ewvH-V.ewvH.mean())/V.ewvH.std(); V["vr"]=(V.ewvR-V.ewvR.mean())/V.ewvR.std()
V["vi"]=V.vh*V.vr
X=np.column_stack([np.ones(len(V)),V.vh,V.vr,V.vi]); yy=V.u2.values
b,*_=np.linalg.lstsq(X,yy,rcond=None); r=yy-X@b
se=np.sqrt(np.diag((r@r/(len(yy)-4))*np.linalg.pinv(X.T@X)))
for i,c in enumerate(["Vol_H","Vol_R","Vol_H x Vol_R"]):
    print(f"   {c:<16}{b[i+1]:>+9.4f} (t={b[i+1]/se[i+1]:>+5.2f})")
print(f"   -> if only the INTERACTION matters, that is a structural result")
