import sys; sys.path.insert(0,"/home/dpope/projects/nba_entropy_replication")
import warnings,numpy as np,pandas as pd; warnings.filterwarnings("ignore")
from prepare_data import read_master, season_label
SP="/tmp/claude-1000/-home-dpope/4fa2e81b-35e9-49e8-92da-7bffe4f69700/scratchpad/"
raw=read_master(verbose=False); raw["season"]=season_label(raw).astype(str)
n=lambda c: pd.to_numeric(raw[c],errors="coerce")
d=pd.DataFrame({"season":raw["season"]})
for c in ["PTS_H","PTS_R","FG_H","FGA_H","3P_H","3PA_H","FT_H","FTA_H","TO_H","TEAM_Reb_H",
          "POSS_H","PACE_H","OEFF_H","DEFF_H","PTS_R","FG_R","FGA_R","3P_R","3PA_R","FT_R",
          "FTA_R","TO_R","TEAM_Reb_R","POSS_R","PACE_R","OEFF_R","DEFF_R",
          "OPENING TOTAL_H","OPENING SPREAD_H","CLOSING TOTAL_H","TEAM\nREST DAYS_H","TEAM\nREST DAYS_R"]:
    d[c]=n(c)
d["TEAM_H"]=raw["TEAM_H"]; d["TEAM_R"]=raw["TEAM_R"]
d["date"]=pd.to_datetime(raw["DATE"],errors="coerce")
d["yr"]=d.season.str.extract(r"(\d{4})").astype(float)
d=d[d.season.str.contains("Regular Season",na=False)]
d["open"]=d["OPENING TOTAL_H"]; d["ospread"]=d["OPENING SPREAD_H"]; d["close"]=d["CLOSING TOTAL_H"]
d["total"]=d.PTS_H+d.PTS_R
d=d.dropna(subset=["open","total","PACE_H","OEFF_H","FGA_H","yr"]).sort_values("date")
d=d.reset_index(drop=True); d["gi"]=d.index
print(f"games {len(d):,}   sd(open) {d.open.std():.3f}   open->close corr {d.open.corr(d.close):.4f}")

# ---- team-game long panel with derived rates ----
def side(s):
    o="R" if s=="H" else "H"
    x=pd.DataFrame({"gi":d.gi,"yr":d.yr,"date":d.date,"t":d[f"TEAM_{s}"],"opp":d[f"TEAM_{o}"]})
    x["pace"]=d[f"PACE_{s}"]; x["oeff"]=d[f"OEFF_{s}"]; x["deff"]=d[f"DEFF_{s}"]
    x["efg"]=(d[f"FG_{s}"]+0.5*d[f"3P_{s}"])/d[f"FGA_{s}"]
    x["tov"]=100*d[f"TO_{s}"]/d[f"POSS_{s}"]; x["ftr"]=d[f"FTA_{s}"]/d[f"FGA_{s}"]
    x["t3r"]=d[f"3PA_{s}"]/d[f"FGA_{s}"]; x["t3p"]=d[f"3P_{s}"]/d[f"3PA_{s}"].replace(0,np.nan)
    x["reb"]=d[f"TEAM_Reb_{s}"]; x["home"]=1.0 if s=="H" else 0.0
    return x
T=pd.concat([side("H"),side("R")]).sort_values(["t","date"])
FE=["pace","oeff","deff","efg","tov","ftr","t3r","t3p","reb"]
# PIT: current-season prior mean shrunk toward PRIOR-SEASON mean (what a book has in October)
K=10.0
prev=T.groupby(["t","yr"])[FE].mean().reset_index(); prev["yr"]=prev.yr+1
prev=prev.rename(columns={c:c+"_prev" for c in FE})
T=T.merge(prev,on=["t","yr"],how="left")
g=T.groupby(["t","yr"])
for c in FE:
    cs=g[c].transform(lambda s:s.shift(1).expanding(min_periods=1).mean())
    cn=g[c].transform(lambda s:s.shift(1).expanding(min_periods=1).count())
    pv=T[c+"_prev"].fillna(T.groupby("yr")[c].transform("mean"))
    T["p_"+c]=(cn.fillna(0)*cs.fillna(0)+K*pv)/(cn.fillna(0)+K)
    T["p_"+c]=T["p_"+c].fillna(pv)
# short-window recent state
for c in ["pace","oeff","deff"]:
    T["s_"+c]=g[c].transform(lambda s:s.shift(1).rolling(10,min_periods=3).mean())
    T["s_"+c]=T["s_"+c].fillna(T["p_"+c])
H=T[T.home==1].set_index("gi"); R=T[T.home==0].set_index("gi")
X=pd.DataFrame(index=H.index)
for c in FE: X["H_"+c]=H["p_"+c]; X["R_"+c]=R["p_"+c]
for c in ["pace","oeff","deff"]: X["Hs_"+c]=H["s_"+c]; X["Rs_"+c]=R["s_"+c]
G=d.set_index("gi").join(X)
G["restH"]=G["TEAM\nREST DAYS_H"].clip(0,5); G["restR"]=G["TEAM\nREST DAYS_R"].clip(0,5)
G["b2bH"]=(G.restH<=1).astype(float); G["b2bR"]=(G.restR<=1).astype(float)
G["doy"]=(G.date-G.groupby("season").date.transform("min")).dt.days
for c_ in ["restH","restR","b2bH","b2bR","doy"]:
    G[c_]=pd.to_numeric(G[c_],errors="coerce")
    G[c_]=G[c_].fillna(G[c_].median())
G=G.dropna(subset=[c for c in X.columns])
# structural identity features: Total = Pace * (PPP_h + PPP_r)
G["mpace"]=(G.H_pace+G.R_pace)/2.0
G["ppp_h"]=(G.H_oeff+G.R_deff)/200.0
G["ppp_r"]=(G.R_oeff+G.H_deff)/200.0
G["struct"]=G.mpace*(G.ppp_h+G.ppp_r)
G["ms"]=G.mpace*(G.ppp_h-G.ppp_r)
print(f"emulator panel {len(G):,}\n")

BLK={
 "M0 league baseline":[],
 "M1 + off/def strength":["H_oeff","R_oeff","H_deff","R_deff"],
 "M2 + expected pace":["H_pace","R_pace"],
 "M3 + four factors":["H_efg","R_efg","H_tov","R_tov","H_ftr","R_ftr","H_reb","R_reb"],
 "M4 + shot composition":["H_t3r","R_t3r","H_t3p","R_t3p"],
 "M5 + rest / schedule":["restH","restR","b2bH","b2bR","doy"],
 "M6 + recent state":["Hs_pace","Rs_pace","Hs_oeff","Rs_oeff","Hs_deff","Rs_deff"],
}
def run(cols,y):
    D=pd.get_dummies(G.season,prefix="s",drop_first=True).astype(float)
    A=np.column_stack([np.ones(len(G)),D.values]+([G[c].values.astype(float) for c in cols] if cols else []))
    b,*_=np.linalg.lstsq(A,y,rcond=None); r=y-A@b
    return np.sqrt((r**2).mean()),1-r.var()/y.var(),r
print("STRUCTURAL IDENTITY  Total = Pace x (PPP_h + PPP_r)")
for lbl,cols in [("structural term ALONE",["struct"]),
                 ("additive pace+eff",["H_pace","R_pace","H_oeff","R_oeff","H_deff","R_deff"]),
                 ("structural + additive",["struct","H_pace","R_pace","H_oeff","R_oeff","H_deff","R_deff"])]:
    rm,r2,_=run(cols,G.open.values.astype(float))
    print(f"  {lbl:<26}RMSE {rm:6.3f}   R2 {r2:.4f}")
print()
d_=G.copy()
mrg=-d_.ospread
print("HOME/ROAD DECOMPOSITION  implied pts = (T +- M)/2   (M = -opening spread)")
print(f"  sanity corr(M, actual home margin) = {mrg.corr(d_.PTS_H-d_.PTS_R):+.4f}")
G["imp_H"]=(G.open+mrg)/2; G["imp_R"]=(G.open-mrg)/2
for tt,ll in [("imp_H","implied HOME points"),("imp_R","implied ROAD points")]:
    cum2=[]; pr=None
    print(f"  {ll}  (sd {G[tt].std():.3f})")
    for k,v in BLK.items():
        cum2+=v; rm,r2,_=run(cum2,G[tt].values.astype(float))
        print(f"     {k:<24}RMSE {rm:6.3f}  R2 {r2:.4f}" + ("" if pr is None else f"  dR2 {r2-pr:+.4f}")); pr=r2
print()
for tgt,lbl in [("open","OPENING TOTAL"),("close","CLOSING TOTAL")]:
    y=G[tgt].values.astype(float); cum=[]; prev_r2=None
    print(f"RECONSTRUCTING THE {lbl}   (sd {y.std():.3f})")
    print(f"  {'model':<26}{'RMSE':>8}{'R2':>9}{'dR2':>9}")
    for k,v in BLK.items():
        cum+=v; rm,r2,res=run(cum,y)
        dd="" if prev_r2 is None else f"{r2-prev_r2:+.4f}"
        print(f"  {k:<26}{rm:>8.3f}{r2:>9.4f}{dd:>9}"); prev_r2=r2
        if tgt=="open": G["L_"+k[:2]]=res
    print()
G.reset_index().to_csv(SP+"emulator_panel.csv",index=False)
print(f"residual L (M6) : sd {G.L_M6.std():.3f}  vs sd(open) {G.open.std():.3f}")
print(f"corr(L_M6, actual-open) {G.L_M6.corr(G.total-G.open):+.4f}")
