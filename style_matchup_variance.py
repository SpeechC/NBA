import sys; sys.path.insert(0,"/home/dpope/projects/nba_entropy_replication")
import warnings,numpy as np,pandas as pd; warnings.filterwarnings("ignore")
from prepare_data import read_master, season_label
SP="/tmp/claude-1000/-home-dpope/4fa2e81b-35e9-49e8-92da-7bffe4f69700/scratchpad/"
S=pd.read_csv(SP+"pace_var2.csv"); S["date"]=pd.to_datetime(S.date)
raw=read_master(verbose=False); raw["season"]=season_label(raw).astype(str)
n_=lambda c: pd.to_numeric(raw[c],errors="coerce")
M=pd.DataFrame({"date":pd.to_datetime(raw["DATE"],errors="coerce"),"TEAM_H":raw["TEAM_H"],"TEAM_R":raw["TEAM_R"]})
for c in ["TO_H","TO_R","FTA_H","FTA_R","FGA_H","FGA_R","POSS_H","POSS_R","3PA_H","3PA_R"]: M[c]=n_(c)
S=S.merge(M,on=["date","TEAM_H","TEAM_R"],how="left")
pb=pd.read_csv(SP+"s2_pbp_states.csv"); pb["date"]=pd.to_datetime(pb.GAMEDATE,errors="coerce")
tm=pd.read_csv("team_mapping.csv"); pb["team"]=pb.tm.map(dict(zip(tm.abbr,tm.bigdataball_name)))
pb=pb.dropna(subset=["team","date"])[["date","team","trans_share","live"]]
S=S.merge(pb.rename(columns={"team":"TEAM_H","trans_share":"trH","live":"lvH"}),on=["date","TEAM_H"],how="left")
S=S.merge(pb.rename(columns={"team":"TEAM_R","trans_share":"trR","live":"lvR"}),on=["date","TEAM_R"],how="left")
S=S.dropna(subset=["u","trH","trR"]).sort_values("date").reset_index(drop=True)
S["u2"]=S.u**2
# ---- prior-only STYLE STATES per team ----
def side(s):
    o="R" if s=="H" else "H"
    return pd.DataFrame({"gi":S.index,"date":S.date,"yr":S.yr,"t":S[f"TEAM_{s}"],"opp":S[f"TEAM_{o}"],
        "pace":S[f"PACE_{s}"],"gpace":S.gpace,"trans":S[f"tr{s}"],"live":S[f"lv{s}"],
        "tov":100*S[f"TO_{s}"]/S[f"POSS_{s}"],"tovf":100*S[f"TO_{o}"]/S[f"POSS_{o}"],
        "ftr":S[f"FTA_{s}"]/S[f"FGA_{s}"]})
L=pd.concat([side("H"),side("R")]).sort_values(["t","date"])
g=L.groupby(["t","yr"])
for c in ["pace","trans","live","tov","tovf","ftr"]:
    L["p_"+c]=g[c].transform(lambda x:x.shift(1).expanding(min_periods=5).mean())
K=L.set_index(["gi","t"])
for s in ["H","R"]:
    for c in ["pace","trans","live","tov","tovf","ftr"]:
        S[f"{c}_{s}"]=[K["p_"+c].get((i,t),np.nan) for i,t in zip(S.index,S[f"TEAM_{s}"])]
# ---- CONTROL coefficient: how much does team i's game pace follow the OPPONENT's preference? ----
LG=L.gpace.mean()
L["opp_pref"]=[np.nan]*len(L)
pref=L.groupby(["t","yr"]).p_pace.last()
ctrl={}
for (t,y),gg in L.groupby(["t","yr"]):
    gg=gg.dropna(subset=["p_pace"])
    op=np.array([pref.get((o,y),np.nan) for o in gg.opp])
    m=np.isfinite(op)&np.isfinite(gg.gpace.values)
    if m.sum()<20: continue
    x=op[m]-LG; yv=gg.gpace.values[m]-LG
    b=np.polyfit(x,yv,1)[0] if x.std()>0.2 else np.nan
    ctrl[(t,y+1)]=b                       # use in the NEXT season
raw_b=pd.Series(ctrl); mu_b=raw_b.mean(); sd_b=raw_b.std()
for s in ["H","R"]:
    S[f"ctrl_{s}"]=[0.5*(ctrl.get((t,y),mu_b) if np.isfinite(ctrl.get((t,y),np.nan)) else mu_b)+0.5*mu_b
                    for t,y in zip(S[f"TEAM_{s}"],S.yr)]     # heavy shrink toward the mean
S=S.dropna(subset=["pace_H","pace_R","trans_H","trans_R","tov_H","tov_R","ftr_H","ftr_R"]).reset_index(drop=True)
# ---- MATCHUP STYLE FEATURES ----
S["PrefConflict"]=(S.pace_H-S.pace_R).abs()
S["ControlConflict"]=S.PrefConflict*S.ctrl_H.abs()*S.ctrl_R.abs()
S["TransComp"]=S.trans_H*S.trans_R
S["TovPressure"]=S.tovf_H*S.tov_R+S.tovf_R*S.tov_H
S["FtrSum"]=S.ftr_H+S.ftr_R
sv=["pace","trans","tov","ftr"]
Z=lambda c: (S[c]-S[c].mean())/S[c].std()
S["StyleDist"]=np.sqrt(sum((Z(f"{c}_H")-Z(f"{c}_R"))**2 for c in sv))
S["VolH"]=S.ewvH; S["VolR"]=S.ewvR
print(f"STYLE-CONDITIONED MATCHUP VARIANCE MODEL   n={len(S):,}   seasons {S.yr.min()}-{S.yr.max()}")
print(f"  PrefConflict mean {S.PrefConflict.mean():.2f} p90 {S.PrefConflict.quantile(.9):.2f}")
print(f"  control coef: mean {mu_b:+.3f} sd {sd_b:.3f}  (low |b| = imposes own pace)")
teams=sorted(set(S.TEAM_H)|set(S.TEAM_R)); T=len(teams); ti={t:i for i,t in enumerate(teams)}
STY=["PrefConflict","ControlConflict","TransComp","TovPressure","FtrSum","StyleDist","VolH","VolR"]
S=S.dropna(subset=STY).reset_index(drop=True)
def design(D,mode):
    n=len(D); base=[np.ones(n)]
    if mode=="M0": return np.column_stack(base)
    if mode=="M1":
        H=np.zeros((n,T)); R=np.zeros((n,T))
        H[np.arange(n),D.TEAM_H.map(ti).values]=1; R[np.arange(n),D.TEAM_R.map(ti).values]=1
        return np.column_stack(base+[(H+R)[:,:-1]])
    X=[np.asarray((D[c]-S[c].mean())/S[c].std()) for c in STY]
    if mode=="M2": return np.column_stack(base+X)
    H=np.zeros((n,T)); R=np.zeros((n,T))
    H[np.arange(n),D.TEAM_H.map(ti).values]=1; R[np.arange(n),D.TEAM_R.map(ti).values]=1
    return np.column_stack(base+X+[(H+R)[:,:-1]])
def glm(X,y,lam):
    b=np.zeros(X.shape[1]); b[0]=np.log(max(y.mean(),1e-6))
    P=np.eye(X.shape[1])*lam; P[0,0]=0
    for _ in range(25):
        mu=np.exp(np.clip(X@b,-8,8)); z=X@b+(y-mu)/np.maximum(mu,1e-8)
        try: b=np.linalg.solve(X.T@X+P,X.T@z)
        except Exception: break
    return b
def ll(u,s2): s2=np.clip(s2,0.5,80); return (-0.5*np.log(2*np.pi*s2)-u**2/(2*s2)).sum()
print(f"\n  HELD-OUT LOG-LIKELIHOOD   {'season':<8}{'n':>6}{'M0':>11}{'M1 team':>11}{'M2 style':>11}{'M3 both':>11}{'M2-M1':>9}")
tot={k:0 for k in ["M0","M1","M2","M3"]}
for y in sorted(S.yr.unique())[1:]:
    tr=S[S.yr<y]; te=S[S.yr==y]
    if len(tr)<500 or len(te)<200: continue
    row={}
    for m in ["M0","M1","M2","M3"]:
        lam=0 if m=="M0" else (300 if m in("M1","M3") else 30)
        b=glm(design(tr,m),tr.u2.values,lam); s2=np.exp(np.clip(design(te,m)@b,-8,8))
        row[m]=ll(te.u.values,s2); tot[m]+=row[m]
        if m=="M2": S.loc[te.index,"s2_style"]=s2
    print(f"  {'':<20}{int(y):<8}{len(te):>6}{row['M0']:>11.1f}{row['M1']:>11.1f}{row['M2']:>11.1f}"
          f"{row['M3']:>11.1f}{row['M2']-row['M1']:>9.2f}")
print(f"  {'':<20}{'TOTAL':<8}{'':>6}{tot['M0']:>11.1f}{tot['M1']:>11.1f}{tot['M2']:>11.1f}{tot['M3']:>11.1f}"
      f"{tot['M2']-tot['M1']:>9.2f}")
print(f"\n  M1-M0 {tot['M1']-tot['M0']:+.2f}   M2-M0 {tot['M2']-tot['M0']:+.2f}   "
      f"M2-M1 {tot['M2']-tot['M1']:+.2f}   M3-M2 {tot['M3']-tot['M2']:+.2f}")
D=S.dropna(subset=["s2_style"]).copy(); D["sig"]=np.sqrt(D.s2_style)
q=pd.qcut(D.sig,5,labels=False)
print(f"\n  M2 QUINTILES   n={len(D):,}")
for i in range(5):
    s=D[q==i]; print(f"    Q{i+1}  n={len(s):>5}  pred sd {s.sig.mean():.3f}   ACTUAL sd(u) {s.u.std():.3f}  +-{s.u.std()/np.sqrt(2*len(s)):.3f}")
from scipy import stats
lo,hi=D[q==0].u,D[q==4].u; F=hi.var()/lo.var()
print(f"    Q1 {lo.std():.3f} -> Q5 {hi.std():.3f}  ratio {hi.std()/lo.std():.4f}  F p="
      f"{2*min(stats.f.cdf(F,len(hi)-1,len(lo)-1),1-stats.f.cdf(F,len(hi)-1,len(lo)-1)):.4f}")
b=glm(design(S,"M2"),S.u2.values,30)
print(f"\n  STYLE COEFFICIENTS (log-variance scale, standardised)")
for i,c in enumerate(STY): print(f"    {c:<18}{b[i+1]:>+9.4f}")
S.to_csv(SP+"style_panel.csv",index=False)
