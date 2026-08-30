import sys; sys.path.insert(0,"/home/dpope/projects/nba_entropy_replication")
import warnings,numpy as np,pandas as pd; warnings.filterwarnings("ignore")
SP="/tmp/claude-1000/-home-dpope/4fa2e81b-35e9-49e8-92da-7bffe4f69700/scratchpad/"
S=pd.read_csv(SP+"v5_panel.csv"); S["date"]=pd.to_datetime(S.date); S=S.sort_values("date").reset_index(drop=True)
teams=sorted(set(S.TEAM_H)|set(S.TEAM_R)); ti={t:i for i,t in enumerate(teams)}; NT=len(teams)
H=S.TEAM_H.map(ti).values; A=S.TEAM_R.map(ti).values
iH=S.impH.values; iR=S.impR.values; yr=S.yr.values; dates=S.date.values; N=len(S)
PH=S.PTS_H.values; PR=S.PTS_R.values
base=np.nanmean(iH); hfa=np.nanmean(iH-iR)/2
def linestate(k,lam,mix):
    Off=np.zeros(NT);Def=np.zeros(NT);pH=np.empty(N);pR=np.empty(N)
    OH=np.empty(N);DR=np.empty(N);OR_=np.empty(N);DH=np.empty(N)
    i=0;yp=None
    while i<N:
        j=i
        while j<N and dates[j]==dates[i]: j+=1
        if yp is not None and yr[i]!=yp: Off*=lam; Def*=lam
        yp=yr[i]
        for q in range(i,j):
            h,a=H[q],A[q]
            OH[q],DR[q],OR_[q],DH[q]=Off[h],Def[a],Off[a],Def[h]
            pH[q]=base+Off[h]+Def[a]+hfa; pR[q]=base+Off[a]+Def[h]-hfa
        for q in range(i,j):
            h,a=H[q],A[q]
            qH=iH[q]-pH[q]; qR=iR[q]-pR[q]
            uH=mix*qH+(1-mix)*(PH[q]-iH[q]); uR=mix*qR+(1-mix)*(PR[q]-iR[q])
            Off[h]+=k*uH; Def[a]+=k*uH; Off[a]+=k*uR; Def[h]+=k*uR
        i=j
    return pH,pR,OH,DR,OR_,DH
p2H,p2R,OH,DR,OR_,DH=linestate(0.30,0.6,1.0)
p4H,p4R,*_=linestate(0.20,0.6,0.75)
S["predH"]=(p2H+p4H)/2; S["predR"]=(p2R+p4R)/2
S["pred"]=S.predH+S.predR
S["err"]=S.open-S.pred; S["errH"]=S.impH-S.predH; S["errR"]=S.impR-S.predR
S["OH"]=OH; S["DR"]=DR; S["OR"]=OR_; S["DH"]=DH
B=pd.read_csv(SP+"stageB_panel.csv"); B["date"]=pd.to_datetime(B.date)
S=S.merge(B[["date","TEAM_H","doy","restH","restR","H_pace","R_pace","ospread"]],
          on=["date","TEAM_H"],how="left",suffixes=("","_b"))
V=pd.read_csv(SP+"vorp_features.csv"); V["date"]=pd.to_datetime(V.date)
S=S.merge(V[["date","team","vorp"]].rename(columns={"team":"TEAM_H","vorp":"vH"}),on=["date","TEAM_H"],how="left")
S=S.merge(V[["date","team","vorp"]].rename(columns={"team":"TEAM_R","vorp":"vR"}),on=["date","TEAM_R"],how="left")
S.to_csv(SP+"failure_panel.csv",index=False)
T=S[S.yr>=2022].copy(); T["ae"]=T.err.abs()
thr=T.ae.quantile(0.9); T["worst"]=T.ae>=thr
W=T[T.worst]; N_=T[~T.worst]
print(f"WORST-DECILE FAILURE ANALYSIS   n={len(T):,}   worst {len(W)}  threshold |err| >= {thr:.2f}")
print(f"\n1. DIRECTION — do we under- or over-predict?")
print(f"   worst decile: mean signed error {W.err.mean():+.3f}   ({100*(W.err>0).mean():.1f}% positive)")
print(f"   rest        : mean signed error {N_.err.mean():+.3f}   ({100*(N_.err>0).mean():.1f}% positive)")
print(f"   => {'DIRECTIONAL BIAS' if abs(W.err.mean())>0.5 else 'symmetric: the model is not biased, it is IMPRECISE'}")
print(f"\n2. WHICH SIDE FAILS? decompose into home-implied and road-implied points")
print(f"   worst: |errH| {W.errH.abs().mean():.3f}   |errR| {W.errR.abs().mean():.3f}"
      f"   corr(errH,errR) {W.errH.corr(W.errR):+.4f}")
print(f"   rest : |errH| {N_.errH.abs().mean():.3f}   |errR| {N_.errR.abs().mean():.3f}"
      f"   corr(errH,errR) {N_.errH.corr(N_.errR):+.4f}")
print(f"   => corr near +1 means BOTH sides move together (a GAME-level miss);")
print(f"      corr near 0 means ONE team's state is wrong (a TEAM-level miss)")
print(f"\n3. EVENT or STATE? is a worst-decile error a one-off spike or part of a run?")
L=pd.concat([T[["date","yr","TEAM_H","errH","worst"]].rename(columns={"TEAM_H":"t","errH":"e"}),
             T[["date","yr","TEAM_R","errR","worst"]].rename(columns={"TEAM_R":"t","errR":"e"})]).sort_values(["t","date"])
g=L.groupby(["t","yr"]); L["prev"]=g.e.shift(1); L["nxt"]=g.e.shift(-1)
for lab,sub in [("all team-games",L),("worst-decile games only",L[L.worst])]:
    s=sub.dropna(subset=["prev","nxt"])
    print(f"   {lab:<26} corr(e, prev) {s.e.corr(s.prev):+.4f}   corr(e, next) {s.e.corr(s.nxt):+.4f}  n={len(s):,}")
print(f"   => low autocorrelation in the worst games = EVENT-driven, not a stale state")
print(f"\n4. IS THE STATE STALE? worst-decile rate by games-into-season and by rest")
T["gis"]=pd.cut(T.doy,[-1,10,25,60,130,300],labels=["<10d","10-25d","25-60d","60-130d",">130d"])
r=T.groupby("gis").worst.agg(["mean","size"])
print("   "+"   ".join(f"{i}: {100*v['mean']:.1f}% (n={int(v['size'])})" for i,v in r.iterrows()))
print(f"\n5. EXTREME STATES? do worst games involve unusual team ratings")
T["absr"]=(T.OH.abs()+T.DR.abs()+T.OR.abs()+T.DH.abs())
print(f"   mean sum|rating|  worst {W.assign(a=W.OH.abs()+W.DR.abs()+W.OR.abs()+W.DH.abs()).a.mean():.3f}"
      f"   rest {N_.assign(a=N_.OH.abs()+N_.DR.abs()+N_.OR.abs()+N_.DH.abs()).a.mean():.3f}")
print(f"\n6. LEVEL OF THE LINE — are the misses at unusual totals?")
print(f"   worst: mean open {W.open.mean():.1f}  sd {W.open.std():.2f}"
      f"    rest: mean open {N_.open.mean():.1f}  sd {N_.open.std():.2f}")
print(f"\n7. TIME CLUSTERING — do worst games bunch on particular DATES?")
dd=T.groupby(T.date).worst.agg(["sum","size"]); dd=dd[dd["size"]>=4]
exp=T.worst.mean()
print(f"   dates with >=4 games: {len(dd)}   share of those dates where >=50% are worst-decile:"
      f" {100*(dd['sum']/dd['size']>=0.5).mean():.2f}%   (chance ~{100*exp**2*10:.2f}%)")
print(f"   corr(daily worst-rate, next-day worst-rate) = {dd['sum'].div(dd['size']).corr(dd['sum'].div(dd['size']).shift(1)):+.4f}")
S.to_csv(SP+"failure_panel.csv",index=False)
