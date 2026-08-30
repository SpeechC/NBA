import sys; sys.path.insert(0,"/home/dpope/projects/nba_entropy_replication")
import warnings,numpy as np,pandas as pd; warnings.filterwarnings("ignore")
from scipy import stats
SP="/tmp/claude-1000/-home-dpope/4fa2e81b-35e9-49e8-92da-7bffe4f69700/scratchpad/"
S=pd.read_csv(SP+"pace_var2.csv"); S["date"]=pd.to_datetime(S.date)
S=S.dropna(subset=["u"]).sort_values("date").reset_index(drop=True)
S["u2"]=S.u**2
teams=sorted(set(S.TEAM_H)|set(S.TEAM_R)); T=len(teams); ti={t:i for i,t in enumerate(teams)}
def design(D,mode):
    n=len(D); cols=[np.ones(n)]
    if mode=="M0": return np.column_stack(cols),0
    H=np.zeros((n,T)); R=np.zeros((n,T))
    H[np.arange(n),D.TEAM_H.map(ti).values]=1
    R[np.arange(n),D.TEAM_R.map(ti).values]=1
    if mode=="M1":                      # POOLED team effect (home+road same)
        P=H+R; return np.column_stack([np.ones(n),P[:,:-1]]),T-1
    return np.column_stack([np.ones(n),H[:,:-1],R[:,:-1]]),2*(T-1)   # M2: separate
def gamma_glm(X,y,lam,npen,iters=25):
    """Gamma(log-link) IRLS with ridge on the non-intercept block = hierarchical shrinkage"""
    b=np.zeros(X.shape[1]); b[0]=np.log(max(y.mean(),1e-6))
    P=np.eye(X.shape[1])*lam; P[0,0]=0.0
    for _ in range(iters):
        mu=np.exp(np.clip(X@b,-8,8))
        z=X@b+(y-mu)/np.maximum(mu,1e-8)
        try: b=np.linalg.solve(X.T@X+P,X.T@z)
        except Exception: break
    return b
def ll(u,sig2):
    sig2=np.clip(sig2,0.5,80.0)
    return (-0.5*np.log(2*np.pi*sig2)-u**2/(2*sig2)).sum()
print(f"TWO-WAY HIERARCHICAL PACE-VARIANCE MODEL   n={len(S):,}  teams {T}")
print("  log sigma^2 = alpha + H[home team] + R[road team],  ridge = hierarchical shrinkage")
yrs=sorted(S.yr.unique())
# pick lambda on the FIRST split only, then freeze
tr0=S[S.yr<yrs[-2]]; va0=S[S.yr==yrs[-2]]
best=None
for lam in [3,10,30,100,300,1000]:
    X,np_=design(tr0,"M2"); b=gamma_glm(X,tr0.u2.values,lam,np_)
    Xv,_=design(va0,"M2"); s2=np.exp(np.clip(Xv@b,-8,8))
    v=ll(va0.u.values,s2)
    if best is None or v>best[0]: best=(v,lam)
LAM=best[1]; print(f"  ridge lambda selected on the first split only: {LAM}")
print(f"\n  HELD-OUT GAUSSIAN LOG-LIKELIHOOD (higher is better)")
print(f"  {'season':<9}{'n':>6}{'M0 const':>12}{'M1 pooled':>12}{'M2 home/road':>15}{'M2-M1':>9}")
tot={"M0":0,"M1":0,"M2":0}; N=0
for y in yrs[1:]:
    tr=S[S.yr<y]; te=S[S.yr==y]
    if len(tr)<600 or len(te)<200: continue
    row=[]
    for m in ["M0","M1","M2"]:
        X,npen=design(tr,m); b=gamma_glm(X,tr.u2.values,LAM if m=="M2" else (LAM if m=="M1" else 0),npen)
        Xe,_=design(te,m); s2=np.exp(np.clip(Xe@b,-8,8))
        v=ll(te.u.values,s2); tot[m]+=v; row.append(v)
        if m=="M2": S.loc[te.index,"sig2"]=s2
    N+=len(te)
    print(f"  {int(y):<9}{len(te):>6}{row[0]:>12.1f}{row[1]:>12.1f}{row[2]:>15.1f}{row[2]-row[1]:>9.2f}")
print(f"  {'TOTAL':<9}{N:>6}{tot['M0']:>12.1f}{tot['M1']:>12.1f}{tot['M2']:>15.1f}{tot['M2']-tot['M1']:>9.2f}")
print(f"  M1 - M0 = {tot['M1']-tot['M0']:+.2f}   M2 - M1 = {tot['M2']-tot['M1']:+.2f}"
      f"   -> {'M2 WINS' if tot['M2']>tot['M1'] else 'M2 does NOT beat M1'}")
D=S.dropna(subset=["sig2"]).copy(); D["sig"]=np.sqrt(D.sig2)
print(f"\n  PROSPECTIVE QUINTILES (M2 predictions)   n={len(D):,}")
q=pd.qcut(D.sig,5,labels=False)
print(f"  {'quintile':<10}{'n':>6}{'pred sd':>10}{'ACTUAL sd(u)':>15}{'+-':>8}")
for i in range(5):
    s=D[q==i]; print(f"  {i+1:<10}{len(s):>6}{s.sig.mean():>10.3f}{s.u.std():>15.3f}{s.u.std()/np.sqrt(2*len(s)):>8.3f}")
lo,hi=D[q==0].u,D[q==4].u; F=hi.var()/lo.var()
p=2*min(stats.f.cdf(F,len(hi)-1,len(lo)-1),1-stats.f.cdf(F,len(hi)-1,len(lo)-1))
print(f"  Q1 {lo.std():.3f} -> Q5 {hi.std():.3f}  ratio {hi.std()/lo.std():.4f}  F p={p:.4f}")
# ---- the 60-parameter table ----
X,npen=design(S,"M2"); b=gamma_glm(X,S.u2.values,LAM,npen)
Hc=np.r_[b[1:T],0.0]; Rc=np.r_[b[T:2*T-1],0.0]; a=b[0]
tab=pd.DataFrame({"team":teams,
                  "home_sd":np.sqrt(np.exp(a+Hc+np.mean(Rc))),
                  "road_sd":np.sqrt(np.exp(a+np.mean(Hc)+Rc))})
tab["H_minus_R"]=tab.home_sd-tab.road_sd
tab["home_rank"]=tab.home_sd.rank().astype(int); tab["road_rank"]=tab.road_sd.rank().astype(int)
tab=tab.sort_values("H_minus_R")
print(f"\n  60 SHRUNK TEAM x VENUE STATES (full-sample fit, for description)")
print(f"  {'team':<15}{'home sd':>9}{'road sd':>9}{'H-R':>8}{'Hrank':>7}{'Rrank':>7}")
for _,r in pd.concat([tab.head(5),tab.tail(5)]).iterrows():
    print(f"  {r.team:<15}{r.home_sd:>9.3f}{r.road_sd:>9.3f}{r.H_minus_R:>+8.3f}{int(r.home_rank):>7}{int(r.road_rank):>7}")
print(f"\n  home sd range {tab.home_sd.min():.3f}-{tab.home_sd.max():.3f}"
      f"   road sd range {tab.road_sd.min():.3f}-{tab.road_sd.max():.3f}")
print(f"  sd of (home-road) across teams = {tab.H_minus_R.std():.4f}")
print(f"  corr(home_sd, road_sd) across teams = {tab.home_sd.corr(tab.road_sd):+.4f}")
tab.to_csv(SP+"team_venue_var.csv",index=False); S.to_csv(SP+"twoway_panel.csv",index=False)
