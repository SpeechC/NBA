import sys; sys.path.insert(0,"/home/dpope/projects/nba_entropy_replication")
import warnings,numpy as np,pandas as pd; warnings.filterwarnings("ignore")
SP="/tmp/claude-1000/-home-dpope/4fa2e81b-35e9-49e8-92da-7bffe4f69700/scratchpad/"
G=pd.read_csv(SP+"emulator_panel.csv")     # Stage 1 PIT features, frozen
G["date"]=pd.to_datetime(G.date); G["yr"]=G.yr.astype(int)
G=G.sort_values("date").reset_index(drop=True)
# ---- market-persistence states: each team's PRIOR market-implied points ----
G["M_open"]=-pd.to_numeric(G.ospread,errors="coerce")
G["impH"]=(G.open+G.M_open)/2; G["impR"]=(G.open-G.M_open)/2
T=pd.concat([G[["date","yr","TEAM_H","impH"]].rename(columns={"TEAM_H":"t","impH":"ip"}),
             G[["date","yr","TEAM_R","impR"]].rename(columns={"TEAM_R":"t","impR":"ip"})])
T=T.sort_values(["t","date"]).reset_index(drop=True)
pv=T.groupby(["t","yr"]).ip.mean().reset_index(); pv["yr"]=pv.yr+1
pv=pv.rename(columns={"ip":"ip_pv"})
T=T.merge(pv,on=["t","yr"],how="left").sort_values(["t","date"]).reset_index(drop=True)
g=T.groupby(["t","yr"])
cs=g.ip.transform(lambda s:s.shift(1).expanding(min_periods=1).mean())
cn=g.ip.transform(lambda s:s.shift(1).expanding(min_periods=1).count())
pvf=T.ip_pv.fillna(T.groupby("yr").ip.transform("mean"))
T["mkt_prior"]=((cn.fillna(0)*cs.fillna(0)+10*pvf)/(cn.fillna(0)+10)).fillna(pvf)
mp=T.set_index(["date","t"]).mkt_prior
G["mkH"]=[mp.get((d,t),np.nan) for d,t in zip(G.date,G.TEAM_H)]
G["mkR"]=[mp.get((d,t),np.nan) for d,t in zip(G.date,G.TEAM_R)]
G["mk_sum"]=G.mkH+G.mkR
BLK={"M0 league baseline":[],
 "M1 + off/def strength":["H_oeff","R_oeff","H_deff","R_deff"],
 "M2 + expected pace":["H_pace","R_pace"],
 "M3 + four factors":["H_efg","R_efg","H_tov","R_tov","H_ftr","R_ftr","H_reb","R_reb"],
 "M4 + shot composition":["H_t3r","R_t3r","H_t3p","R_t3p"],
 "M5 + rest / schedule":["restH","restR","b2bH","b2bR","doy"],
 "M6 + recent state":["Hs_pace","Rs_pace","Hs_oeff","Rs_oeff","Hs_deff","Rs_deff"]}
YRS=sorted(G.yr.unique())
def xfit(cols,tgt="open",extra=None):
    """expanding chronological: train through season Y-1, predict season Y"""
    pr=pd.Series(index=G.index,dtype=float)
    use=list(cols)+(extra or [])
    for y in YRS[1:]:
        tr=G[(G.yr<y)&G[tgt].notna()]; te=G[G.yr==y]
        if len(tr)<300 or not len(te): continue
        A=np.column_stack([np.ones(len(tr))]+[tr[c].values.astype(float) for c in use]) if use else np.ones((len(tr),1))
        B=np.column_stack([np.ones(len(te))]+[te[c].values.astype(float) for c in use]) if use else np.ones((len(te),1))
        ok=np.isfinite(A).all(1); A=A[ok]
        b,*_=np.linalg.lstsq(A,tr[tgt].values[ok],rcond=None)
        pr.loc[te.index]=B@b
    return pr
def rep(pred,y,lbl,base=None):
    m=pred.notna()&y.notna(); e=(y[m]-pred[m])
    rm=np.sqrt((e**2).mean()); r2=1-e.var()/y[m].var()
    d="" if base is None else f"{rm-base:+.3f}"
    print(f"  {lbl:<26}{rm:>8.3f}{e.abs().mean():>8.3f}{r2:>9.4f}{e.abs().median():>9.3f}"
          f"{100*(e.abs()<=0.5).mean():>8.1f}{100*(e.abs()<=1).mean():>8.1f}"
          f"{100*(e.abs()<=2).mean():>8.1f}{d:>9}")
    return rm
print("STAGE B — CHRONOLOGICAL CROSS-FIT (train through season Y-1, predict Y)")
print("  target: OPENING TOTAL (ladder mu exists for 2025-26 only; tested separately below)")
print(f"  n {len(G):,}  seasons {YRS[0]}..{YRS[-1]}   NO actual scores used anywhere\n")
print(f"  {'model':<26}{'RMSE':>8}{'MAE':>8}{'R2':>9}{'medAE':>9}{'<=0.5':>8}{'<=1':>8}{'<=2':>8}{'dRMSE':>9}")
cum=[]; prev=None
for k,v in BLK.items():
    cum+=v; prev=rep(xfit(cum),G.open,k,prev)
print(f"\n  Stage-1 IN-SAMPLE M6: RMSE 3.508  R2 0.8689   <- OPTIMISTIC UPPER BOUND, not comparable")
print("\nBENCHMARKS")
rep(xfit([]),G.open,"league mean (M0)")
rep(G.mk_sum,G.open,"MARKET PERSISTENCE only")
rep(xfit(["struct"]),G.open,"structural term only")
rep(xfit(sum(BLK.values(),[])+["mk_sum"]),G.open,"M6 + MARKET PERSISTENCE")
print("\nPACE FUNCTIONAL FORM (OOS RMSE on the opener, pace block only)")
G["p_avg"]=(G.H_pace+G.R_pace)/2; G["p_geo"]=np.sqrt(G.H_pace.clip(lower=1)*G.R_pace.clip(lower=1))
G["p_dif"]=(G.H_pace-G.R_pace)**2; G["p_prod"]=G.H_pace*G.R_pace
base=["H_oeff","R_oeff","H_deff","R_deff"]
for lbl,extra in [("(P_H+P_R)/2",["p_avg"]),("sqrt(P_H*P_R)",["p_geo"]),
                  ("a+bH*P_H+bR*P_R",["H_pace","R_pace"]),
                  ("+ (P_H-P_R)^2",["H_pace","R_pace","p_dif"]),
                  ("+ P_H*P_R",["H_pace","R_pace","p_prod"])]:
    rep(xfit(base+extra),G.open,"  "+lbl)
print("\nSTRUCTURAL IDENTITY, OOS")
rep(xfit(["struct"]),G.open,"  struct alone")
rep(xfit(["struct"]+BLK["M6 + recent state"]),G.open,"  struct + recent state")
rep(xfit(["struct","mk_sum"]),G.open,"  struct + market persistence")
G.to_csv(SP+"stageB_panel.csv",index=False)
