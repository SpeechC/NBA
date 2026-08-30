import sys; sys.path.insert(0,"/home/dpope/projects/nba_entropy_replication")
import warnings,numpy as np,pandas as pd; warnings.filterwarnings("ignore")
SP="/tmp/claude-1000/-home-dpope/4fa2e81b-35e9-49e8-92da-7bffe4f69700/scratchpad/"
G=pd.read_csv(SP+"stageB_panel.csv"); G["date"]=pd.to_datetime(G.date); G["yr"]=G.yr.astype(int)
G=G.sort_values("date").reset_index(drop=True)
G["M"]=-G.ospread; G["impH"]=(G.open+G.M)/2; G["impR"]=(G.open-G.M)/2
G=G.dropna(subset=["impH","impR","open"]).reset_index(drop=True)
teams=sorted(set(G.TEAM_H)|set(G.TEAM_R)); ti={t:i for i,t in enumerate(teams)}
H=G.TEAM_H.map(ti).values; A=G.TEAM_R.map(ti).values
iH=G.impH.values; iR=G.impR.values; yr=G.yr.values; y=G.open.values
base=iH.mean(); hfa=(iH-iR).mean()/2; NT=len(teams)
def run2(kf,ks,w,lam):
    """two-speed: R = w*Fast + (1-w)*Slow, each updating on the SAME innovation"""
    Fo=np.zeros(NT); So=np.zeros(NT); Fd=np.zeros(NT); Sd=np.zeros(NT)
    pred=np.empty(len(G)); yp=None
    for i in range(len(G)):
        if yp is not None and yr[i]!=yp:
            Fo*=lam; So*=lam; Fd*=lam; Sd*=lam
        yp=yr[i]; h=H[i]; a=A[i]
        Roh=w*Fo[h]+(1-w)*So[h]; Rda=w*Fd[a]+(1-w)*Sd[a]
        Roa=w*Fo[a]+(1-w)*So[a]; Rdh=w*Fd[h]+(1-w)*Sd[h]
        pH=base+Roh+Rda+hfa; pR=base+Roa+Rdh-hfa
        pred[i]=pH+pR
        eH=iH[i]-pH; eR=iR[i]-pR
        Fo[h]+=kf*eH; So[h]+=ks*eH; Fd[a]+=kf*eH; Sd[a]+=ks*eH
        Fo[a]+=kf*eR; So[a]+=ks*eR; Fd[h]+=kf*eR; Sd[h]+=ks*eR
    return pred
def r2(p,m): e=y[m]-p[m]; return 1-e.var()/y[m].var()
DEV=yr<=2021; TEST=yr>=2022
print("STAGE D3 — TWO-SPEED LATENT STATE.  tuned on 2017-2021, applied to 2022-2026")
best=None
for kf in [0.20,0.30,0.40,0.50]:
    for ks in [0.02,0.05,0.10,0.15]:
        for w in [0.2,0.35,0.5,0.65,0.8]:
            for lam in [0.5,0.6,0.7]:
                v=r2(run2(kf,ks,w,lam),DEV)
                if best is None or v>best[0]: best=(v,kf,ks,w,lam)
_,kf,ks,w,lam=best
print(f"  selected kf={kf}, ks={ks}, w={w}, lambda={lam}   (dev R2 {best[0]:.4f})")
pD3=run2(kf,ks,w,lam)
# D2 comparator, its own tuned params
def run1(k,lam):
    Off=np.zeros(NT); Def=np.zeros(NT); pred=np.empty(len(G)); yp=None
    for i in range(len(G)):
        if yp is not None and yr[i]!=yp: Off*=lam; Def*=lam
        yp=yr[i]; h=H[i]; a=A[i]
        pH=base+Off[h]+Def[a]+hfa; pR=base+Off[a]+Def[h]-hfa
        pred[i]=pH+pR; eH=iH[i]-pH; eR=iR[i]-pR
        Off[h]+=k*eH; Def[a]+=k*eH; Off[a]+=k*eR; Def[h]+=k*eR
    return pred
pD2=run1(0.30,0.6)
print(f"\n  {'model (HELD-OUT 2022-2026)':<34}{'RMSE':>8}{'MAE':>8}{'R2':>9}{'<=1':>7}{'<=2':>7}")
for lbl,p in [("D2 single-speed (k=0.30)",pD2),("D3 two-speed",pD3)]:
    e=y[TEST]-p[TEST]
    print(f"  {lbl:<34}{np.sqrt((e**2).mean()):>8.3f}{np.abs(e).mean():>8.3f}{r2(p,TEST):>9.4f}"
          f"{100*(np.abs(e)<=1).mean():>7.1f}{100*(np.abs(e)<=2).mean():>7.1f}")
print(f"\n  effective one-step rate  w*kf+(1-w)*ks = {w*kf+(1-w)*ks:.4f}  (D2 used 0.30)")
np.save(SP+"pD3.npy",pD3); np.save(SP+"pD2.npy",pD2)
G[["date","TEAM_H","TEAM_R","yr","impH","impR","open"]].to_csv(SP+"d3_games.csv",index=False)
for nm,p in [("D2",pD2),("D3",pD3)]:
    G["predH_"+nm]=np.nan; G["predR_"+nm]=np.nan
G["pD3"]=pD3; G["pD2"]=pD2; G.to_csv(SP+"stageD3_panel.csv",index=False)
