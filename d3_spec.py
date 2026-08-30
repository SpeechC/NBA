import sys; sys.path.insert(0,"/home/dpope/projects/nba_entropy_replication")
import warnings,numpy as np,pandas as pd; warnings.filterwarnings("ignore")
from prepare_data import read_master, season_label
SP="/tmp/claude-1000/-home-dpope/4fa2e81b-35e9-49e8-92da-7bffe4f69700/scratchpad/"
raw=read_master(verbose=False); raw["season"]=season_label(raw).astype(str)
n=lambda c: pd.to_numeric(raw[c],errors="coerce")
d=pd.DataFrame({"season":raw["season"],"TEAM_H":raw["TEAM_H"],"TEAM_R":raw["TEAM_R"],
                "date":pd.to_datetime(raw["DATE"],errors="coerce")})
for c in ["PTS_H","PTS_R","POSS_H","POSS_R","OPENING TOTAL_H","OPENING SPREAD_H"]: d[c]=n(c)
d=d[d.season.str.contains("Regular Season",na=False)]
d["yr"]=d.season.str.extract(r"(\d{4})").astype(int)
d["open"]=d["OPENING TOTAL_H"]; d["M"]=-d["OPENING SPREAD_H"]
d=d.dropna(subset=["open","M","PTS_H","POSS_H","date"]).sort_values("date").reset_index(drop=True)
d["impH"]=(d.open+d.M)/2; d["impR"]=(d.open-d.M)/2
teams=sorted(set(d.TEAM_H)|set(d.TEAM_R)); ti={t:i for i,t in enumerate(teams)}
H=d.TEAM_H.map(ti).values; A=d.TEAM_R.map(ti).values
iH=d.impH.values; iR=d.impR.values; yr=d.yr.values
base=iH.mean(); hfa=(iH-iR).mean()/2; NT=len(teams)
def run(mode,kf,ks,w,lam):
    Fo=np.zeros(NT);So=np.zeros(NT);Fd=np.zeros(NT);Sd=np.zeros(NT)
    pH=np.empty(len(d));pR=np.empty(len(d));yp=None
    for i in range(len(d)):
        if yp is not None and yr[i]!=yp:
            for X in (Fo,So,Fd,Sd): X*=lam
        yp=yr[i];h=H[i];a=A[i]
        if mode=="one": Roh,Rda,Roa,Rdh=Fo[h],Fd[a],Fo[a],Fd[h]
        else:
            Roh=w*Fo[h]+(1-w)*So[h]; Rda=w*Fd[a]+(1-w)*Sd[a]
            Roa=w*Fo[a]+(1-w)*So[a]; Rdh=w*Fd[h]+(1-w)*Sd[h]
        pH[i]=base+Roh+Rda+hfa; pR[i]=base+Roa+Rdh-hfa
        eH=iH[i]-pH[i]; eR=iR[i]-pR[i]
        if mode=="one":
            Fo[h]+=kf*eH; Fd[a]+=kf*eH; Fo[a]+=kf*eR; Fd[h]+=kf*eR
        else:
            Fo[h]+=kf*eH; So[h]+=ks*eH; Fd[a]+=kf*eH; Sd[a]+=ks*eH
            Fo[a]+=kf*eR; So[a]+=ks*eR; Fd[h]+=kf*eR; Sd[h]+=ks*eR
    return pH,pR
def panel(pH,pR):
    def side(s,p):
        o="R" if s=="H" else "H"
        x=pd.DataFrame({"date":d.date,"yr":d.yr,"t":d[f"TEAM_{s}"]})
        x["imp"]=d[f"imp{s}"]; x["pred"]=p; x["pts"]=d[f"PTS_{s}"]
        x["opp_pts"]=d[f"PTS_{o}"]; x["opp_imp"]=d[f"imp{o}"]
        return x
    P=pd.concat([side("H",pH),side("R",pR)]).sort_values(["t","date"]).reset_index(drop=True)
    P["e"]=P.imp-P.pred
    g=P.groupby(["t","yr"])
    P["sh1"]=g.pts.shift(1)-g.imp.shift(1)
    for L in [2,3,4]: P[f"sh{L}"]=g.apply(lambda x:(x.pts-x.imp).shift(L),include_groups=False).reset_index(level=[0,1],drop=True)
    P["ds"]=g.opp_imp.shift(1)-g.opp_pts.shift(1)
    P["rest"]=(P.date-g.date.shift(1)).dt.days
    return P.dropna(subset=["e","sh1","sh2","sh3","sh4","ds"]).query("rest>=2")
def lagtest(P,lbl):
    print(f"  {lbl}")
    for cols in [["sh1","ds"],["sh1","sh2","sh3","sh4","ds"]]:
        X=np.column_stack([np.ones(len(P))]+[P[c].values for c in cols]); yv=P.e.values
        b,*_=np.linalg.lstsq(X,yv,rcond=None); r=yv-X@b
        se=np.sqrt(np.diag((r@r/(len(yv)-len(cols)-1))*np.linalg.pinv(X.T@X)))
        print(f"    R2 {1-r.var()/yv.var():.4f}  "+"  ".join(
            f"{c}={b[i+1]:+.4f}(t={b[i+1]/se[i+1]:+.1f})" for i,c in enumerate(cols)))
print("SPECIFICATION TEST — do lags 2-4 collapse under the two-speed state?")
print("  if the defect were LONGER MEMORY, they should.\n")
pH,pR=run("one",0.30,0,0,0.6); lagtest(panel(pH,pR),"D2 single-speed (k=0.30)")
pH,pR=run("two",0.50,0.10,0.65,0.6); lagtest(panel(pH,pR),"D3 two-speed (kf=.50, ks=.10, w=.65)")

print("\n"+"="*76)
print("WHAT THE PERSISTENCE ACTUALLY MEANS")
print("  positive lag-2..4 coefficients = after a team overperforms, the market KEEPS")
print("  raising its quote for several games. That is GRADUAL ADJUSTMENT, not memory length.")
print("  Test: update the rating from REALISED PERFORMANCE instead of the quote error.\n")
pts_H=d.PTS_H.values; pts_R=d.PTS_R.values
def runP(k,lam,mix):
    """mix=0 -> update purely on the SCORING surprise; mix=1 -> purely on the quote error"""
    Off=np.zeros(NT); Def=np.zeros(NT); pH=np.empty(len(d)); pR=np.empty(len(d)); yp=None
    for i in range(len(d)):
        if yp is not None and yr[i]!=yp: Off*=lam; Def*=lam
        yp=yr[i]; h=H[i]; a=A[i]
        pH[i]=base+Off[h]+Def[a]+hfa; pR[i]=base+Off[a]+Def[h]-hfa
        qH=iH[i]-pH[i]; qR=iR[i]-pR[i]            # quote error
        sH=pts_H[i]-iH[i]; sR=pts_R[i]-iR[i]      # scoring surprise vs the market's own number
        uH=mix*qH+(1-mix)*sH; uR=mix*qR+(1-mix)*sR
        Off[h]+=k*uH; Def[a]+=k*uH; Off[a]+=k*uR; Def[h]+=k*uR
    return pH,pR
yv=d.open.values; DEV=yr<=2021; TEST=yr>=2022
print(f"  {'update source':<34}{'k':>6}{'dev R2':>9}{'TEST R2':>10}{'TEST RMSE':>11}")
bestm=None
for mix in [0.0,0.25,0.5,0.75,1.0]:
    bk=None
    for k in [0.02,0.05,0.10,0.20,0.30,0.40]:
        a_,b_=runP(k,0.6,mix); p=a_+b_
        v=1-((yv[DEV]-p[DEV]).var()/yv[DEV].var())
        if bk is None or v>bk[0]: bk=(v,k,p)
    v,k,p=bk; e=yv[TEST]-p[TEST]
    t2=1-e.var()/yv[TEST].var()
    lbl={0.0:"100% scoring surprise",1.0:"100% quote error (=D2)"}.get(mix,f"{int(100*(1-mix))}% scoring / {int(100*mix)}% quote")
    print(f"  {lbl:<34}{k:>6.2f}{v:>9.4f}{t2:>10.4f}{np.sqrt((e**2).mean()):>11.3f}")
    if bestm is None or t2>bestm[0]: bestm=(t2,mix,k)
print(f"\n  best held-out: mix={bestm[1]} (k={bestm[2]})")
print("\n  lag structure under the best performance-driven variant:")
pH,pR=runP(bestm[2],0.6,bestm[1]); lagtest(panel(pH,pR),f"  mix={bestm[1]}")
