import sys; sys.path.insert(0,"/home/dpope/projects/nba_entropy_replication")
import warnings,numpy as np,pandas as pd; warnings.filterwarnings("ignore")
from prepare_data import read_master, season_label
SP="/tmp/claude-1000/-home-dpope/4fa2e81b-35e9-49e8-92da-7bffe4f69700/scratchpad/"
F=pd.read_csv(SP+"injury_features.csv"); F["gd"]=pd.to_datetime(F.gd)
G=pd.read_csv(SP+"stageB_panel.csv"); G["date"]=pd.to_datetime(G.date); G["yr"]=G.yr.astype(int)
G=G.sort_values("date").reset_index(drop=True)
G["M"]=-G.ospread; G["impH"]=(G.open+G.M)/2; G["impR"]=(G.open-G.M)/2
G=G.dropna(subset=["impH","impR","open","close"]).reset_index(drop=True)
rw=read_master(verbose=False); rw["season"]=season_label(rw).astype(str)
nn=lambda c: pd.to_numeric(rw[c],errors="coerce")
pm=pd.DataFrame({"date":pd.to_datetime(rw["DATE"],errors="coerce"),"TEAM_H":rw["TEAM_H"],
                 "pH":nn("PTS_H"),"pR":nn("PTS_R")})
G=G.merge(pm,on=["date","TEAM_H"],how="left")
# --- team-name join: "GoldenStateWarriors" -> "Golden State" ---
tm=pd.read_csv("team_mapping.csv")
cn=lambda s: s.astype(str).str.replace(r"[^A-Za-z]","",regex=True).str.lower()
F["tk"]=cn(F.team_raw)
mp={}
for _,r in tm.iterrows():
    pref=cn(pd.Series([r.bigdataball_name])).iloc[0]
    hit=F.tk[F.tk.str.startswith(pref)].unique()
    for h in hit: mp[h]=r.bigdataball_name
F["team"]=F.tk.map(mp)
print(f"team-name join: {100*F.team.notna().mean():.1f}% of injury team-games mapped"
      f"  ({F.tk[F.team.isna()].nunique()} unmapped labels)")
COLS=["e_n_out","e_pts_out","d_e_pts_out","late_news","l_pts_out"]
FH=F.dropna(subset=["team"])[["gd","team"]+COLS].rename(columns={"gd":"date","team":"TEAM_H"})
FR=FH.rename(columns={"TEAM_H":"TEAM_R",**{c:c+"_R" for c in COLS}})
G=G.merge(FH,on=["date","TEAM_H"],how="left").merge(FR,on=["date","TEAM_R"],how="left")
have=G.e_pts_out.notna()&G.e_pts_out_R.notna()
print(f"games with BOTH teams' injury data: {have.sum():,} of {len(G):,}"
      f"  seasons {G.loc[have,'yr'].min()}-{G.loc[have,'yr'].max()}")
for c in COLS: G[c+"_sum"]=G[c]+G[c+"_R"]
# --- latent ratings (D2 + D4) ---
teams=sorted(set(G.TEAM_H)|set(G.TEAM_R)); ti={t:i for i,t in enumerate(teams)}
H=G.TEAM_H.map(ti).values; A=G.TEAM_R.map(ti).values
iH=G.impH.values; iR=G.impR.values; yr=G.yr.values; PH=G.pH.values; PR=G.pR.values
base=iH.mean(); hfa=(iH-iR).mean()/2; NT=len(teams)
def rate(k,lam,mix):
    Off=np.zeros(NT);Def=np.zeros(NT);pr=np.empty(len(G));yp=None
    for i in range(len(G)):
        if yp is not None and yr[i]!=yp: Off*=lam; Def*=lam
        yp=yr[i];h=H[i];a=A[i]
        ph=base+Off[h]+Def[a]+hfa; prr=base+Off[a]+Def[h]-hfa; pr[i]=ph+prr
        qH=iH[i]-ph; qR=iR[i]-prr
        sH=(PH[i]-iH[i]) if np.isfinite(PH[i]) else qH
        sR=(PR[i]-iR[i]) if np.isfinite(PR[i]) else qR
        Off[h]+=k*(mix*qH+(1-mix)*sH); Def[a]+=k*(mix*qH+(1-mix)*sH)
        Off[a]+=k*(mix*qR+(1-mix)*sR); Def[h]+=k*(mix*qR+(1-mix)*sR)
    return pr
G["ratD2"]=rate(0.30,0.6,1.0); G["ratD4"]=rate(0.20,0.6,0.75)
REC=["Hs_pace","Rs_pace","Hs_oeff","Rs_oeff","Hs_deff","Rs_deff"]
ALL=["H_oeff","R_oeff","H_deff","R_deff","H_pace","R_pace","H_efg","R_efg","H_tov","R_tov",
     "H_ftr","R_ftr","H_reb","R_reb","H_t3r","R_t3r","H_t3p","R_t3p","restH","restR","b2bH","b2bR","doy"]+REC
S=G[have].reset_index(drop=True)
def xfit(cols,tgt="open",D=None):
    D=S if D is None else D; pr=np.full(len(D),np.nan)
    for y in sorted(D.yr.unique())[1:]:
        tr=D[D.yr<y]; te=D[D.yr==y]
        if len(tr)<300 or not len(te): continue
        Aa=np.column_stack([np.ones(len(tr))]+[tr[c].values.astype(float) for c in cols])
        Bb=np.column_stack([np.ones(len(te))]+[te[c].values.astype(float) for c in cols])
        ok=np.isfinite(Aa).all(1)
        b,*_=np.linalg.lstsq(Aa[ok],tr[tgt].values[ok],rcond=None); pr[te.index]=Bb@b
    return pr
T=(S.yr>=2022).values
def sc(p,tgt,lbl):
    m=T&~np.isnan(p); y=S[tgt].values; e=y[m]-p[m]
    print(f"  {lbl:<46}{np.sqrt((e**2).mean()):>8.3f}{1-e.var()/y[m].var():>9.4f}")
INJ=["e_pts_out_sum","d_e_pts_out_sum","e_n_out_sum"]
print(f"\nHELD-OUT 2022+ on the injury-covered sample  (n={T.sum():,})")
print(f"  {'model':<46}{'RMSE':>8}{'R2':>9}")
print("  --- target: OPENING TOTAL ---")
sc(xfit(ALL+["ratD2","ratD4"]),"open","baseline: M6 + D2 + D4")
sc(xfit(ALL+["ratD2","ratD4"]+INJ),"open","+ INJURY (early report, level + change)")
sc(xfit(ALL+["ratD2","ratD4"]+INJ+["late_news_sum"]),"open","+ late news (post-opener, diagnostic)")
print("  --- target: CLOSING TOTAL ---")
sc(xfit(ALL+["ratD2","ratD4"],"close"),"close","baseline: M6 + D2 + D4")
sc(xfit(ALL+["ratD2","ratD4"]+INJ,"close"),"close","+ INJURY early")
sc(xfit(ALL+["ratD2","ratD4"]+INJ+["l_pts_out_sum","late_news_sum"],"close"),"close","+ INJURY early + LATE")
S.to_csv(SP+"inj_panel.csv",index=False)
