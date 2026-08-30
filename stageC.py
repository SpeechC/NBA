import sys; sys.path.insert(0,"/home/dpope/projects/nba_entropy_replication")
import warnings,numpy as np,pandas as pd; warnings.filterwarnings("ignore")
from prepare_data import read_master, season_label
SP="/tmp/claude-1000/-home-dpope/4fa2e81b-35e9-49e8-92da-7bffe4f69700/scratchpad/"
G=pd.read_csv(SP+"stageB_panel.csv"); G["date"]=pd.to_datetime(G.date)
# ---- prior-only TEAM SCORING DISPERSION (does the ladder use it? Link 4b, re-tested) ----
raw=read_master(verbose=False); raw["season"]=season_label(raw).astype(str)
n_=lambda c: pd.to_numeric(raw[c],errors="coerce")
d=pd.DataFrame({"season":raw["season"],"TEAM_H":raw["TEAM_H"],"TEAM_R":raw["TEAM_R"],
                "ph":n_("PTS_H"),"pr":n_("PTS_R")})
d["date"]=pd.to_datetime(raw["DATE"],errors="coerce")
d=d[d.season.str.contains("Regular Season",na=False)].dropna(subset=["ph","pr","date"])
d["yr"]=d.season.str.extract(r"(\d{4})").astype(float)
L=pd.concat([d[["date","yr","TEAM_H","ph"]].rename(columns={"TEAM_H":"t","ph":"p"}),
             d[["date","yr","TEAM_R","pr"]].rename(columns={"TEAM_R":"t","pr":"p"})]).sort_values(["t","date"])
g=L.groupby(["t","yr"])
L["psd"]=g.p.transform(lambda s:s.shift(1).expanding(min_periods=10).std())
pv=g.p.std().reset_index(); pv["yr"]=pv.yr+1; pv=pv.rename(columns={"p":"psd_pv"})
L=L.merge(pv,on=["t","yr"],how="left")
L["psd"]=L.psd.fillna(L.psd_pv).fillna(L.psd.mean())
mp=L.set_index(["date","t"]).psd
G["sdH"]=[mp.get((dd,t),np.nan) for dd,t in zip(G.date,G.TEAM_H)]
G["sdR"]=[mp.get((dd,t),np.nan) for dd,t in zip(G.date,G.TEAM_R)]
G["team_sd"]=np.sqrt(G.sdH**2+G.sdR**2)
A=pd.read_csv(SP+"stageA_fits.csv"); A=A[A.maxe<=0.10]
A["mu_lad"]=(A.mu_w+A.mu_i)/2; A["sg_lad"]=(A.s_w+A.s_i)/2
A["home"]=A.ev.str.extract(r"([A-Z]{3})$"); A["date"]=pd.to_datetime(A.date)
tm=pd.read_csv("team_mapping.csv"); A["TEAM_H"]=A.home.map(dict(zip(tm.abbr,tm.bigdataball_name)))
M=G.merge(A[["date","TEAM_H","mu_lad","sg_lad","s_w","s_i","wbar","n","vol"]],on=["date","TEAM_H"],how="inner")
M["pace_g"]=(M.H_pace+M.R_pace)/2; M["t3r_g"]=(M.H_t3r+M.R_t3r)/2
M["t3p_g"]=(M.H_t3p+M.R_t3p)/2;    M["ftr_g"]=(M.H_ftr+M.R_ftr)/2
M["efg_g"]=(M.H_efg+M.R_efg)/2;    M["tov_g"]=(M.H_tov+M.R_tov)/2
M["aspd"]=M.ospread.abs(); M["restmin"]=M[["restH","restR"]].min(axis=1)
M=M.dropna(subset=["sg_lad","mu_lad","wbar","pace_g","t3r_g","team_sd","aspd"]).sort_values("date")
M=M.reset_index(drop=True)
print(f"STAGE C — n={len(M):,}  sd(sigma)={M.sg_lad.std():.4f}")
print("  ladder sigma exists for ONE season -> cross-fit is CHRONOLOGICAL WITHIN SEASON")
print("  explainable ceiling ~86% (14% measurement noise, disjoint-rung split-half)\n")
BLK={"C0 baseline":[],
 "C1 + mu (scale)":["mu_lad"],
 "C2 + pace":["pace_g"],
 "C3 + shot composition":["t3r_g","t3p_g"],
 "C4 + FT / turnover rate":["ftr_g","tov_g"],
 "C5 + team scoring dispersion":["team_sd"],
 "C6 + |spread|, rest":["aspd","restmin"]}
def fit(cols,tgt,ctl=False,oos=False):
    use=list(cols)+(["wbar"] if ctl else [])
    y=M[tgt].values
    if not oos:
        X=np.column_stack([np.ones(len(M))]+[M[c].values.astype(float) for c in use]) if use else np.ones((len(M),1))
        b,*_=np.linalg.lstsq(X,y,rcond=None); r=y-X@b
        return 1-r.var()/y.var(),np.sqrt((r**2).mean())
    pr=np.full(len(M),np.nan); step=100
    for s in range(300,len(M),step):
        tr=slice(0,s); te=slice(s,min(s+step,len(M)))
        Xt=np.column_stack([np.ones(s)]+[M[c].values[tr].astype(float) for c in use]) if use else np.ones((s,1))
        Xe=np.column_stack([np.ones(te.stop-te.start)]+[M[c].values[te].astype(float) for c in use]) if use else np.ones((te.stop-te.start,1))
        b,*_=np.linalg.lstsq(Xt,y[tr],rcond=None); pr[te]=Xe@b
    m=~np.isnan(pr); e=y[m]-pr[m]
    return 1-e.var()/y[m].var(),np.sqrt((e**2).mean())
print("C1-C6 HIERARCHY on the CANONICAL sigma")
print(f"  {'model':<30}{'IS R2':>8}{'IS RMSE':>9}{'OOS R2':>9}{'OOS RMSE':>10}{'+width IS R2':>14}")
cum=[]
for k,v in BLK.items():
    cum+=v
    i2,ir=fit(cum,"sg_lad"); o2,orm=fit(cum,"sg_lad",oos=True); w2,_=fit(cum,"sg_lad",ctl=True)
    print(f"  {k:<30}{i2:>8.4f}{ir:>9.4f}{o2:>9.4f}{orm:>10.4f}{w2:>14.4f}")
print(f"\n  reached {fit(cum,'sg_lad')[0]:.1%} of a ~86% ceiling"
      f"  ({fit(cum,'sg_lad')[0]/0.86:.1%} of what is explainable)")
print("\nESTIMATOR ROBUSTNESS — full model, all three, with/without width")
print(f"  {'estimator':<12}{'no width R2':>13}{'with width R2':>15}")
for est,nm in [("s_w","WLS"),("s_i","INTERVAL"),("sg_lad","canonical")]:
    print(f"  {nm:<12}{fit(cum,est)[0]:>13.4f}{fit(cum,est,ctl=True)[0]:>15.4f}")
print("\nCOEFFICIENTS vs PHYSICAL BENCHMARKS (width controlled, all three estimators)")
def coef(tgt,cols,which):
    use=list(cols)+["wbar"]
    X=np.column_stack([np.ones(len(M))]+[M[c].values.astype(float) for c in use])
    y=M[tgt].values; b,*_=np.linalg.lstsq(X,y,rcond=None); r=y-X@b
    se=np.sqrt(np.diag((r@r/(len(y)-len(use)-1))*np.linalg.pinv(X.T@X)))
    i=use.index(which)+1; return b[i],se[i]
CORE=["mu_lad","pace_g","t3r_g","t3p_g","ftr_g","tov_g","team_sd","aspd","restmin"]
for var,bench,bl in [("pace_g",0.0911,"Poisson d(sig)/d(pace)"),("t3r_g",4.87,"shot-mix benchmark"),
                     ("team_sd",None,"team dispersion (Link 4b said ~0)")]:
    print(f"  {bl}")
    for est,nm in [("s_w","WLS"),("s_i","INTERVAL"),("sg_lad","canonical")]:
        b,se=coef(est,CORE,var)
        ins="" if bench is None else ("  bench INSIDE" if b-1.96*se<=bench<=b+1.96*se else "  bench OUTSIDE")
        print(f"    {nm:<11}{b:>+9.4f} (t={b/se:>+5.2f})  CI [{b-1.96*se:>+8.4f},{b+1.96*se:>+8.4f}]{ins}")
M.to_csv(SP+"stageC_panel.csv",index=False)
