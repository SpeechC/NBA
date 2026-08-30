import sys; sys.path.insert(0,"/home/dpope/projects/nba_entropy_replication")
import warnings,numpy as np,pandas as pd; warnings.filterwarnings("ignore")
from prepare_data import read_master, season_label
SP="/tmp/claude-1000/-home-dpope/4fa2e81b-35e9-49e8-92da-7bffe4f69700/scratchpad/"
raw=read_master(verbose=False); raw["season"]=season_label(raw).astype(str)
n=lambda c: pd.to_numeric(raw[c],errors="coerce")
d=pd.DataFrame({"season":raw["season"],"TEAM_H":raw["TEAM_H"],"TEAM_R":raw["TEAM_R"],
                "date":pd.to_datetime(raw["DATE"],errors="coerce")})
for c in ["PTS_H","PTS_R","POSS_H","POSS_R","FG_H","FGA_H","3P_H","FTA_H","TO_H",
          "FG_R","FGA_R","3P_R","FTA_R","TO_R","OPENING TOTAL_H","OPENING SPREAD_H"]:
    d[c]=n(c)
d=d[d.season.str.contains("Regular Season",na=False)]
d["yr"]=d.season.str.extract(r"(\d{4})").astype(int)
d["open"]=d["OPENING TOTAL_H"]; d["M"]=-d["OPENING SPREAD_H"]
d=d.dropna(subset=["open","M","PTS_H","POSS_H","date"]).sort_values("date").reset_index(drop=True)
d["impH"]=(d.open+d.M)/2; d["impR"]=(d.open-d.M)/2
teams=sorted(set(d.TEAM_H)|set(d.TEAM_R)); ti={t:i for i,t in enumerate(teams)}
# ---- rerun D2 (k=0.30, lambda=0.6) storing the PRIOR prediction for BOTH sides ----
Off=np.zeros(len(teams)); Def=np.zeros(len(teams))
base=d.impH.mean(); hfa=(d.impH-d.impR).mean()/2
pH=np.zeros(len(d)); pR=np.zeros(len(d)); yp=None
for i,r in enumerate(d.itertuples()):
    if yp is not None and r.yr!=yp: Off*=0.6; Def*=0.6
    yp=r.yr; h,a=ti[r.TEAM_H],ti[r.TEAM_R]
    pH[i]=base+Off[h]+Def[a]+hfa; pR[i]=base+Off[a]+Def[h]-hfa
    eH=r.impH-pH[i]; eR=r.impR-pR[i]
    Off[h]+=0.30*eH; Def[a]+=0.30*eH; Off[a]+=0.30*eR; Def[h]+=0.30*eR
d["predH"]=pH; d["predR"]=pR
# ---- TEAM-GAME PANEL: two observations per game ----
def side(s):
    o="R" if s=="H" else "H"
    x=pd.DataFrame({"date":d.date,"yr":d.yr,"t":d[f"TEAM_{s}"],"opp":d[f"TEAM_{o}"]})
    x["imp"]=d[f"imp{s}"]; x["pred"]=d[f"pred{s}"]
    x["opp_imp"]=d[f"imp{o}"]; x["opp_pred"]=d[f"pred{o}"]
    x["pts"]=d[f"PTS_{s}"]; x["opp_pts"]=d[f"PTS_{o}"]; x["poss"]=d[f"POSS_{s}"]
    x["efg"]=(d[f"FG_{s}"]+0.5*d[f"3P_{s}"])/d[f"FGA_{s}"]
    x["tov"]=100*d[f"TO_{s}"]/d[f"POSS_{s}"]; x["ftr"]=d[f"FTA_{s}"]/d[f"FGA_{s}"]
    return x
P=pd.concat([side("H"),side("R")]).sort_values(["t","date"]).reset_index(drop=True)
P["e"]=P.imp-P.pred                                  # THE MARKET INNOVATION
g=P.groupby(["t","yr"])
# prior-only expectations for the surprise variables
for c in ["poss","efg","tov","ftr"]:
    P["E_"+c]=g[c].transform(lambda s:s.shift(1).expanding(min_periods=3).mean())
# LAST GAME's surprises (own offence)
P["L_pts"]=g.pts.shift(1); P["L_imp"]=g.imp.shift(1); P["L_poss"]=g.poss.shift(1)
P["L_Eposs"]=g["E_poss"].shift(1); P["L_date"]=g.date.shift(1)
P["L_opppts"]=g.opp_pts.shift(1); P["L_oppimp"]=g.opp_imp.shift(1)
for c in ["efg","tov","ftr"]:
    P["L_"+c]=g[c].shift(1); P["L_E"+c]=g["E_"+c].shift(1)
P["OffShock"]=P.L_pts-P.L_imp                        # scored above the market's expectation
P["DefShockOwn"]=P.L_oppimp-P.L_opppts               # allowed fewer than expected (positive = good)
# decompose the points shock: PointsShock ~ E[PPP]*PaceShock + E[Poss]*EffShock
P["EPPP"]=P.L_imp/P.L_Eposs
P["PaceShock"]=(P.L_poss-P.L_Eposs)*P.EPPP           # in POINTS
P["EffShock"]=P.OffShock-P.PaceShock                 # residual, in POINTS (exactly additive)
for c in ["efg","tov","ftr"]:
    P[c+"Shock"]=P["L_"+c]-P["L_E"+c]
# opponent's last-game DEFENSIVE surprise (today's opponent j)
key=P.set_index(["t","date"])
P["opp_DefShock"]=np.nan
tmp=P[["t","date","DefShockOwn"]].rename(columns={"t":"opp","DefShockOwn":"oppDS"})
P=P.merge(tmp,on=["opp","date"],how="left")
P["rest"]=(P.date-P.L_date).dt.days
print(f"STAGE E — WHAT MOVES THE MARKET'S LATENT STATE?   team-games {len(P):,}")
print(f"  dependent variable: e = market implied pts - D2 carried-forward prediction")
print(f"  sd(e) = {P.e.std():.4f} pts\n")
print("TIMING SAFEGUARD (no opener timestamps exist, so a conservative rule is enforced)")
print(f"  team-games whose previous game was <=1 day earlier (back-to-back): "
      f"{100*(P.rest<=1).mean():.1f}%")
print("  primary sample EXCLUDES them: the opener may have been posted before that game ended.\n")
S=P[(P.rest>=2)].dropna(subset=["e","OffShock","oppDS","PaceShock","EffShock",
                                "efgShock","tovShock","ftrShock"]).copy()
print(f"  primary n = {len(S):,}   (all-rest robustness n = "
      f"{len(P.dropna(subset=['e','OffShock','oppDS','PaceShock','EffShock','efgShock','tovShock','ftrShock'])):,})")
def rep(cols,lbl,D=None):
    D=S if D is None else D
    X=np.column_stack([np.ones(len(D))]+[D[c].values.astype(float) for c in cols]) if cols else np.ones((len(D),1))
    y=D.e.values; b,*_=np.linalg.lstsq(X,y,rcond=None); r=y-X@b
    se=np.sqrt(np.diag((r@r/(len(y)-len(cols)-1))*np.linalg.pinv(X.T@X))) if cols else [0]
    R2=1-r.var()/y.var()
    print(f"  {lbl:<34}{R2:>8.4f}"+"".join(
        f"  {c}={b[i+1]:+.4f}({b[i+1]/se[i+1]:+.1f})" for i,c in enumerate(cols) if abs(b[i+1]/se[i+1])>1.9))
    return R2
print(f"\nUPDATE-RULE HIERARCHY   {'model':<28}{'R2':>10}   significant coefficients (t)")
rep([],"U0 no performance update")
rep(["OffShock"],"U1 own points surprise")
rep(["OffShock","oppDS"],"U1b + opponent def surprise")
rep(["PaceShock","EffShock","oppDS"],"U2 pace + efficiency split")
rep(["PaceShock","EffShock","oppDS","efgShock"],"U3 + eFG surprise")
rep(["PaceShock","EffShock","oppDS","efgShock","tovShock"],"U4 + turnover surprise")
rep(["PaceShock","EffShock","oppDS","efgShock","tovShock","ftrShock"],"U5 + FTA surprise")
rep(["PaceShock","EffShock","oppDS","efgShock","tovShock","ftrShock","rest"],"U7 + rest")
print("\nROBUSTNESS — including back-to-backs (timing not guaranteed)")
S2=P.dropna(subset=["e","OffShock","oppDS","PaceShock","EffShock","efgShock","tovShock","ftrShock"])
rep(["PaceShock","EffShock","oppDS"],"U2 on ALL rest",D=S2)
P.to_csv(SP+"stageE_panel.csv",index=False)
