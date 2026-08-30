import sys; sys.path.insert(0,"/home/dpope/projects/nba_entropy_replication")
import warnings,numpy as np,pandas as pd; warnings.filterwarnings("ignore")
SP="/tmp/claude-1000/-home-dpope/4fa2e81b-35e9-49e8-92da-7bffe4f69700/scratchpad/"
S=pd.read_csv(SP+"inj_panel.csv"); S["date"]=pd.to_datetime(S.date)
V=pd.read_csv(SP+"vorp_features.csv"); V["date"]=pd.to_datetime(V.date)
VC=["vorp","raw_pts","min_out","d_vorp"]
VH=V[["date","team"]+VC].rename(columns={"team":"TEAM_H"})
VR=VH.rename(columns={"TEAM_H":"TEAM_R",**{c:c+"_R" for c in VC}})
S=S.merge(VH,on=["date","TEAM_H"],how="left").merge(VR,on=["date","TEAM_R"],how="left")
S=S[S.vorp.notna()&S.vorp_R.notna()].sort_values("date").reset_index(drop=True)
for c in VC: S[c+"_sum"]=S[c]+S[c+"_R"]
print(f"panel with VORP on BOTH teams: n={len(S):,}  seasons {S.yr.min()}-{S.yr.max()}")
teams=sorted(set(S.TEAM_H)|set(S.TEAM_R)); ti={t:i for i,t in enumerate(teams)}
H=S.TEAM_H.map(ti).values; A=S.TEAM_R.map(ti).values
iH=S.impH.values; iR=S.impR.values; yr=S.yr.values; PH=S.pH.values; PR=S.pR.values
base=iH.mean(); hfa=(iH-iR).mean()/2; NT=len(teams)
def rate(k,lam,mix,store=False):
    Off=np.zeros(NT);Def=np.zeros(NT);pr=np.empty(len(S));ph_=np.empty(len(S));pr_=np.empty(len(S));yp=None
    for i in range(len(S)):
        if yp is not None and yr[i]!=yp: Off*=lam; Def*=lam
        yp=yr[i];h=H[i];a=A[i]
        ph_[i]=base+Off[h]+Def[a]+hfa; pr_[i]=base+Off[a]+Def[h]-hfa; pr[i]=ph_[i]+pr_[i]
        qH=iH[i]-ph_[i]; qR=iR[i]-pr_[i]
        sH=(PH[i]-iH[i]) if np.isfinite(PH[i]) else qH
        sR=(PR[i]-iR[i]) if np.isfinite(PR[i]) else qR
        Off[h]+=k*(mix*qH+(1-mix)*sH); Def[a]+=k*(mix*qH+(1-mix)*sH)
        Off[a]+=k*(mix*qR+(1-mix)*sR); Def[h]+=k*(mix*qR+(1-mix)*sR)
    return (pr,ph_,pr_) if store else pr
S["ratD2"]=rate(0.30,0.6,1.0); S["ratD4"],phD,prD=rate(0.20,0.6,0.75,store=True)
REC=["Hs_pace","Rs_pace","Hs_oeff","Rs_oeff","Hs_deff","Rs_deff"]
ALL=["H_oeff","R_oeff","H_deff","R_deff","H_pace","R_pace","H_efg","R_efg","H_tov","R_tov",
     "H_ftr","R_ftr","H_reb","R_reb","H_t3r","R_t3r","H_t3p","R_t3p","restH","restR","b2bH","b2bR","doy"]+REC
def xfit(cols,tgt="open"):
    pr=np.full(len(S),np.nan)
    for y in sorted(S.yr.unique())[1:]:
        tr=S[S.yr<y]; te=S[S.yr==y]
        if len(tr)<300 or not len(te): continue
        Aa=np.column_stack([np.ones(len(tr))]+[tr[c].values.astype(float) for c in cols])
        Bb=np.column_stack([np.ones(len(te))]+[te[c].values.astype(float) for c in cols])
        ok=np.isfinite(Aa).all(1)
        b,*_=np.linalg.lstsq(Aa[ok],tr[tgt].values[ok],rcond=None); pr[te.index]=Bb@b
    return pr
T=(S.yr>=2022).values
def sc(p,tgt,lbl):
    m=T&~np.isnan(p); y=S[tgt].values; e=y[m]-p[m]
    print(f"  {lbl:<44}{np.sqrt((e**2).mean()):>8.3f}{1-e.var()/y[m].var():>9.4f}")
B=ALL+["ratD2","ratD4"]
RAWF=["e_pts_out_sum","d_e_pts_out_sum","e_n_out_sum"]
VF=["vorp_sum","d_vorp_sum","min_out_sum"]
print(f"\nHELD-OUT 2022+  (n={T.sum():,})    {'RMSE':>36}{'R2':>9}")
print("  --- OPENING TOTAL ---")
sc(xfit(B),"open","baseline: M6 + D2 + D4")
sc(xfit(B+RAWF),"open","+ injury RAW (gross points out)")
sc(xfit(B+VF),"open","+ injury VORP (net of replacement)")
sc(xfit(B+RAWF+VF),"open","+ BOTH raw and VORP")
print("  --- CLOSING TOTAL ---")
sc(xfit(B,"close"),"close","baseline")
sc(xfit(B+RAWF,"close"),"close","+ injury RAW")
sc(xfit(B+VF,"close"),"close","+ injury VORP")
print("\nINNOVATION TEST (team-game, D4 state)")
rows=[]
for s,p in [("H",phD),("R",prD)]:
    o="R" if s=="H" else "H"
    rows.append(pd.DataFrame({"e":S[f"imp{s}"]-p,
        "vorp":S["vorp"] if s=="H" else S["vorp_R"], "raw":S["e_pts_out"] if s=="H" else S["e_pts_out_R"],
        "ovorp":S["vorp_R"] if s=="H" else S["vorp"], "oraw":S["e_pts_out_R"] if s=="H" else S["e_pts_out"],
        "dv":S["d_vorp"] if s=="H" else S["d_vorp_R"]}))
P=pd.concat(rows).dropna()
def rr(cols,lbl):
    X=np.column_stack([np.ones(len(P))]+[P[c].values for c in cols]); y=P.e.values
    b,*_=np.linalg.lstsq(X,y,rcond=None); res=y-X@b
    se=np.sqrt(np.diag((res@res/(len(y)-len(cols)-1))*np.linalg.pinv(X.T@X)))
    print(f"  {lbl:<40}R2 {1-res.var()/y.var():.4f}   "+"  ".join(
        f"{c}={b[i+1]:+.4f}(t={b[i+1]/se[i+1]:+.1f})" for i,c in enumerate(cols)))
rr(["raw","oraw"],"RAW gross points out")
rr(["vorp","ovorp"],"VORP net of replacement")
rr(["vorp","ovorp","dv"],"VORP + change")
rr(["raw","oraw","vorp","ovorp"],"both")
