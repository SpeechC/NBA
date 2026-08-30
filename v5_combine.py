import sys; sys.path.insert(0,"/home/dpope/projects/nba_entropy_replication")
import warnings,numpy as np,pandas as pd; warnings.filterwarnings("ignore")
from prepare_data import read_master, season_label
SP="/tmp/claude-1000/-home-dpope/4fa2e81b-35e9-49e8-92da-7bffe4f69700/scratchpad/"
raw=read_master(verbose=False); raw["season"]=season_label(raw).astype(str)
n=lambda c: pd.to_numeric(raw[c],errors="coerce")
d=pd.DataFrame({"season":raw["season"],"TEAM_H":raw["TEAM_H"],"TEAM_R":raw["TEAM_R"],
                "date":pd.to_datetime(raw["DATE"],errors="coerce")})
for c in ["PTS_H","PTS_R","PACE_H","PACE_R","OEFF_H","OEFF_R","OPENING TOTAL_H","OPENING SPREAD_H"]:
    d[c]=n(c)
d=d[d.season.str.contains("Regular Season",na=False)]
d["yr"]=d.season.str.extract(r"(\d{4})").astype(int)
d["open"]=d["OPENING TOTAL_H"]; d["M"]=-d["OPENING SPREAD_H"]
# their erroneous-target exclusions, retained for state construction
BAD=((d.date==pd.Timestamp("2022-11-30"))&(d.open==109.5))|((d.date==pd.Timestamp("2026-03-13"))&(d.open==136.5))
d["target_ok"]=~BAD
d=d.dropna(subset=["open","M","PACE_H","OEFF_H","PTS_H"]).sort_values("date").reset_index(drop=True)
d["impH"]=(d.open+d.M)/2; d["impR"]=(d.open-d.M)/2
d["gpace"]=(d.PACE_H+d.PACE_R)/2
teams=sorted(set(d.TEAM_H)|set(d.TEAM_R)); ti={t:i for i,t in enumerate(teams)}; NT=len(teams)
H=d.TEAM_H.map(ti).values; A=d.TEAM_R.map(ti).values
gp=d.gpace.values; oH=d.OEFF_H.values; oR=d.OEFF_R.values
iH=d.impH.values; iR=d.impR.values; yr=d.yr.values
dates=d.date.values; N=len(d)
hl=lambda h: 1-0.5**(1.0/h)
aP,aO,aD,aL=hl(5.7),hl(8.6),hl(7.4),hl(496.0)
CARRY,SHARE=0.42,0.54
# ---------- LAYER 1: v5 structural latent states, SAME-DAY SAFE ----------
Pst=np.zeros(NT); Ost=np.zeros(NT); Dst=np.zeros(NT)
LP=np.nanmean(gp[:500]); LO=np.nanmean(np.r_[oH[:500],oR[:500]])
sP=np.empty(N); sOH=np.empty(N); sOR=np.empty(N); sLP=np.empty(N); sLO=np.empty(N)
i=0; yp=None
while i<N:
    j=i
    while j<N and dates[j]==dates[i]: j+=1          # one DATE batch
    if yp is not None and yr[i]!=yp:
        Pst*=CARRY; Ost*=CARRY; Dst*=CARRY
    yp=yr[i]
    for k in range(i,j):                            # PREDICT the whole batch first
        h,a=H[k],A[k]
        sP[k]=LP+(Pst[h]+Pst[a])/2
        sOH[k]=LO+Ost[h]+Dst[a]; sOR[k]=LO+Ost[a]+Dst[h]
        sLP[k]=LP; sLO[k]=LO
    for k in range(i,j):                            # THEN update from the batch's results
        h,a=H[k],A[k]
        ep=gp[k]-sP[k]
        Pst[h]+=aP*ep; Pst[a]+=aP*ep; LP+=aL*ep
        eH=oH[k]-sOH[k]; eR=oR[k]-sOR[k]
        Ost[h]+=SHARE*aO*eH; Dst[a]+=(1-SHARE)*aD*eH
        Ost[a]+=SHARE*aO*eR; Dst[h]+=(1-SHARE)*aD*eR
        LO+=aL*(eH+eR)/2
    i=j
d["struct5"]=sP*(sOH+sOR)/100.0
d["sP"]=sP; d["sOsum"]=sOH+sOR
# ---------- LAYER 2: my two-way LINE state, SAME-DAY SAFE ----------
def linestate(k,lam,mix):
    Off=np.zeros(NT); Def=np.zeros(NT); pr=np.empty(N); pH=np.empty(N); pR=np.empty(N)
    base=np.nanmean(iH); hfa=np.nanmean(iH-iR)/2
    i=0; yp=None
    while i<N:
        j=i
        while j<N and dates[j]==dates[i]: j+=1
        if yp is not None and yr[i]!=yp: Off*=lam; Def*=lam
        yp=yr[i]
        for q in range(i,j):
            h,a=H[q],A[q]
            pH[q]=base+Off[h]+Def[a]+hfa; pR[q]=base+Off[a]+Def[h]-hfa; pr[q]=pH[q]+pR[q]
        for q in range(i,j):
            h,a=H[q],A[q]
            qH=iH[q]-pH[q]; qR=iR[q]-pR[q]
            sH=(d.PTS_H.values[q]-iH[q]); sR=(d.PTS_R.values[q]-iR[q])
            uH=mix*qH+(1-mix)*sH; uR=mix*qR+(1-mix)*sR
            Off[h]+=k*uH; Def[a]+=k*uH; Off[a]+=k*uR; Def[h]+=k*uR
        i=j
    return pr
d["lineD2"]=linestate(0.30,0.6,1.0); d["lineD4"]=linestate(0.20,0.6,0.75)
S=d[d.target_ok].reset_index(drop=True)
def xfit(cols,tgt="open"):
    pr=np.full(len(S),np.nan)
    for y in sorted(S.yr.unique())[1:]:
        tr=S[S.yr<y]; te=S[S.yr==y]
        if len(tr)<300 or not len(te): continue
        X=np.column_stack([np.ones(len(tr))]+[tr[c].values.astype(float) for c in cols])
        B=np.column_stack([np.ones(len(te))]+[te[c].values.astype(float) for c in cols])
        ok=np.isfinite(X).all(1)
        b,*_=np.linalg.lstsq(X[ok],tr[tgt].values[ok],rcond=None); pr[te.index]=B@b
    return pr
T=(S.yr>=2022).values
def sc(p,lbl):
    m=T&~np.isnan(p); y=S.open.values; e=y[m]-p[m]
    print(f"  {lbl:<48}{np.abs(e).mean():>7.3f}{np.sqrt((e**2).mean()):>8.3f}{1-e.var()/y[m].var():>9.4f}")
print(f"SAME-DAY-SAFE COMBINATION   n={len(S):,}  held-out {T.sum():,} (2022+)")
print(f"  {'model':<48}{'MAE':>7}{'RMSE':>8}{'R2':>9}")
sc(xfit(["struct5"]),"LAYER 1 only: v5 structural (their spec)")
sc(xfit(["sP","sOsum"]),"  structural, components free")
sc(xfit(["lineD2"]),"LAYER 2 only: two-way line state D2")
sc(xfit(["lineD4"]),"LAYER 2 only: two-way line state D4")
sc(xfit(["lineD2","lineD4"]),"  both line states")
sc(xfit(["struct5","lineD2"]),"L1 + L2 (D2)")
sc(xfit(["struct5","lineD2","lineD4"]),"L1 + L2 (both)")
sc(xfit(["sP","sOsum","lineD2","lineD4"]),"L1 components + L2 (both)")
S.to_csv(SP+"v5_panel.csv",index=False)
