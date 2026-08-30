import sys; sys.path.insert(0,"/home/dpope/projects/nba_entropy_replication")
import warnings,numpy as np,pandas as pd; warnings.filterwarnings("ignore")
from prepare_data import read_master, season_label
SP="/tmp/claude-1000/-home-dpope/4fa2e81b-35e9-49e8-92da-7bffe4f69700/scratchpad/"
T=pd.read_csv(SP+"intersect_panel.csv"); T["date"]=pd.to_datetime(T.date)
VT=pd.read_csv(SP+"vorp_timing.csv"); VT["date"]=pd.to_datetime(VT.date)
RS=pd.read_csv(SP+"roster_state.csv"); RS["date"]=pd.to_datetime(RS.date)
RC=["roster_off","top8_out","rot_min_out_share","continuity","n_subs"]
for df,cols in [(VT,["v_prior"]),(RS,RC)]:
    T=T.merge(df[["date","team"]+cols].rename(columns={"team":"TEAM_H"}),on=["date","TEAM_H"],how="left")
    T=T.merge(df[["date","team"]+cols].rename(columns={"team":"TEAM_R",**{c:c+"_R" for c in cols}}),
              on=["date","TEAM_R"],how="left")
B=pd.read_csv(SP+"stageB_panel.csv"); B["date"]=pd.to_datetime(B.date)
T=T.merge(B[["date","TEAM_H","doy","restH","restR","H_pace","R_pace","H_oeff","R_oeff","H_deff","R_deff"]],
          on=["date","TEAM_H"],how="left",suffixes=("","_bb"))
raw=read_master(verbose=False); raw["season"]=season_label(raw).astype(str)
n_=lambda c: pd.to_numeric(raw[c],errors="coerce")
ac=pd.DataFrame({"date":pd.to_datetime(raw["DATE"],errors="coerce"),"TEAM_H":raw["TEAM_H"],
                 "actual":n_("PTS_H")+n_("PTS_R"),"close":n_("CLOSING TOTAL_H")})
T=T.merge(ac,on=["date","TEAM_H"],how="left",suffixes=("","_ac"))
T=T.dropna(subset=["v_prior","v_prior_R"]+RC+[c+"_R" for c in RC]+["doy","actual"]).reset_index(drop=True)
for c in ["v_prior"]+RC: T[c+"_g"]=T[c]+T[c+"_R"]
T["cont_min"]=T[["continuity","continuity_R"]].min(axis=1)
T["restmin"]=T[["restH","restR"]].min(axis=1); T["restmax"]=T[["restH","restR"]].max(axis=1)
T["exp_pace"]=(T.H_pace+T.R_pace)/2; T["pace_gap"]=(T.H_pace-T.R_pace).abs()
T["aspd"]=T.M.abs(); T["open_dev"]=(T.open-T.open.mean()).abs()
T["rat_abs"]=(T.sOsum-T.sOsum.mean()).abs()+(T.sP-T.sP.mean()).abs()
T["mdis"]=(T.predA-T.predB).abs()                    # MODEL-TO-MODEL DISAGREEMENT
T["early"]=(T.doy<25).astype(float)
FAM={
 "roster / injury instability":["v_prior_g","roster_off_g","cont_min","n_subs_g","rot_min_out_share_g"],
 "early season / state init":["doy","early"],
 "rest / schedule compression":["restmin","restmax"],
 "pace matchup":["exp_pace","pace_gap"],
 "offence-defence matchup extremes":["aspd","rat_abs"],
 "opening-total extremes":["open_dev"],
 "MODEL-TO-MODEL DISAGREEMENT":["mdis"],
}
def xf(cols,tgt="open"):
    pr=np.full(len(T),np.nan)
    for y in sorted(T.yr.unique()):
        tr=T[T.yr<y]; te=T[T.yr==y]
        if len(tr)<400 or not len(te): continue
        X=np.column_stack([np.ones(len(tr)),tr.predA]+[tr[c].values.astype(float) for c in cols])
        Bb=np.column_stack([np.ones(len(te)),te.predA]+[te[c].values.astype(float) for c in cols])
        ok=np.isfinite(X).all(1)
        b,*_=np.linalg.lstsq(X[ok],tr[tgt].values[ok],rcond=None); pr[te.index]=Bb@b
    return pr
p0=xf([]); ok=~np.isnan(p0); A=((T.bA&T.bB).values)&ok
sse0=np.sum((T.open.values-p0)[ok]**2); sse0A=np.sum((T.open.values-p0)[A]**2)
print(f"SSE ATTRIBUTION — fraction of residual squared error removed, strictly OOS")
print(f"  n={ok.sum():,}   Group A n={A.sum()}   baseline R2 {1-np.var((T.open.values-p0)[ok])/np.var(T.open.values[ok]):.4f}")
print(f"  {'mechanism family':<36}{'all games':>12}{'within Group A':>16}")
res={}
for k,v in FAM.items():
    p=xf(v); m=ok&~np.isnan(p)
    s=np.sum((T.open.values-p)[m]**2); sA=np.sum((T.open.values-p)[A&~np.isnan(p)]**2)
    f=1-s/np.sum((T.open.values-p0)[m]**2); fA=1-sA/np.sum((T.open.values-p0)[A&~np.isnan(p)]**2)
    res[k]=(f,fA); print(f"  {k:<36}{100*f:>11.2f}%{100*fA:>15.2f}%")
allf=sum(FAM.values(),[])
p=xf(allf); m=ok&~np.isnan(p)
f=1-np.sum((T.open.values-p)[m]**2)/np.sum((T.open.values-p0)[m]**2)
fA=1-np.sum((T.open.values-p)[A&~np.isnan(p)]**2)/np.sum((T.open.values-p0)[A&~np.isnan(p)]**2)
print(f"  {'ALL FAMILIES TOGETHER':<36}{100*f:>11.2f}%{100*fA:>15.2f}%")
T["p0"]=p0; T["ok"]=ok; T["A"]=A; T.to_csv(SP+"attrib_panel.csv",index=False)
