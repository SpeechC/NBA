import sys; sys.path.insert(0,"/home/dpope/projects/nba_entropy_replication")
import warnings,numpy as np,pandas as pd; warnings.filterwarnings("ignore")
from prepare_data import read_master, season_label
SP="/tmp/claude-1000/-home-dpope/4fa2e81b-35e9-49e8-92da-7bffe4f69700/scratchpad/"
raw=read_master(verbose=False); raw["season"]=season_label(raw).astype(str)
n_=lambda c: pd.to_numeric(raw[c],errors="coerce")
d=pd.DataFrame({"season":raw["season"],"TEAM_H":raw["TEAM_H"],"TEAM_R":raw["TEAM_R"],
                "date":pd.to_datetime(raw["DATE"],errors="coerce")})
for c in ["PTS_H","PTS_R","PACE_H","PACE_R","OEFF_H","OEFF_R","OPENING TOTAL_H","OPENING SPREAD_H","CLOSING TOTAL_H"]:
    d[c]=n_(c)
d=d[d.season.str.contains("Regular Season",na=False)]
d["yr"]=d.season.str.extract(r"(\d{4})").astype(int)
d["open"]=d["OPENING TOTAL_H"]; d["close"]=d["CLOSING TOTAL_H"]
d=d.dropna(subset=["open","PACE_H","OEFF_H","PTS_H"]).sort_values("date").reset_index(drop=True)
d["gpace"]=(d.PACE_H+d.PACE_R)/2
teams=sorted(set(d.TEAM_H)|set(d.TEAM_R)); ti={t:i for i,t in enumerate(teams)}; NT=len(teams)
H=d.TEAM_H.map(ti).values; A=d.TEAM_R.map(ti).values
gp=d.gpace.values; oH=d.OEFF_H.values; oR=d.OEFF_R.values
dates=d.date.values; yr=d.yr.values; N=len(d)
hl=lambda h: 1-0.5**(1.0/h)
aP,aO,aD,aL=hl(5.7),hl(8.6),hl(7.4),hl(496.0); CARRY,SHARE=0.42,0.54
Pst=np.zeros(NT);Ost=np.zeros(NT);Dst=np.zeros(NT)
LP=np.nanmean(gp[:500]); LO=np.nanmean(np.r_[oH[:500],oR[:500]])
sP=np.empty(N);sOH=np.empty(N);sOR=np.empty(N)
i=0;yp=None
while i<N:
    j=i
    while j<N and dates[j]==dates[i]: j+=1
    if yp is not None and yr[i]!=yp: Pst*=CARRY;Ost*=CARRY;Dst*=CARRY
    yp=yr[i]
    for k in range(i,j):
        h,a=H[k],A[k]
        sP[k]=LP+(Pst[h]+Pst[a])/2; sOH[k]=LO+Ost[h]+Dst[a]; sOR[k]=LO+Ost[a]+Dst[h]
    for k in range(i,j):
        h,a=H[k],A[k]
        ep=gp[k]-sP[k]; Pst[h]+=aP*ep; Pst[a]+=aP*ep; LP+=aL*ep
        eH=oH[k]-sOH[k]; eR=oR[k]-sOR[k]
        Ost[h]+=SHARE*aO*eH; Dst[a]+=(1-SHARE)*aD*eH
        Ost[a]+=SHARE*aO*eR; Dst[h]+=(1-SHARE)*aD*eR
        LO+=aL*(eH+eR)/2
    i=j
d["sP"],d["sOH"],d["sOR"]=sP,sOH,sOR
d["dPace"]=gp-sP; d["dOEH"]=oH-sOH; d["dOER"]=oR-sOR
# ---- fit a,b chronologically on the STRUCTURAL form, then oracle-substitute ----
def struct(P,OH,OR): return P*(OH+OR)/100.0
d["X0"]=struct(sP,sOH,sOR)
pred={}
for nm,(P,OH,OR) in {"T0":(sP,sOH,sOR),"TP":(gp,sOH,sOR),"TE":(sP,oH,oR),
                     "TEH":(sP,oH,sOR),"TER":(sP,sOH,oR),"TPE":(gp,oH,oR)}.items():
    x=struct(P,OH,OR); out=np.full(N,np.nan)
    for y in sorted(set(yr))[1:]:
        tr=(yr<y)&np.isfinite(d.X0.values); te=yr==y
        if tr.sum()<400 or te.sum()==0: continue
        M=np.column_stack([np.ones(tr.sum()),d.X0.values[tr]])
        b,*_=np.linalg.lstsq(M,d.open.values[tr],rcond=None)   # coefficients from the BASELINE fit
        out[te]=b[0]+b[1]*x[te]
    pred[nm]=out
for k,v in pred.items(): d[k]=v
S=d[(d.yr>=2022)&d.T0.notna()].copy()
S["e0"]=(S.open-S.T0).abs()
for k in ["TP","TE","TEH","TER","TPE"]:
    S["imp_"+k]=S.e0-(S.open-S[k]).abs()
thr=S.e0.quantile(0.9); S["worst"]=S.e0>=thr
W=S[S.worst].copy()
print(f"ORACLE SUBSTITUTION ATTRIBUTION   n={len(S):,}  worst decile {len(W)}  |e0|>= {thr:.2f}")
print(f"  baseline structural RMSE {np.sqrt((S.open-S.T0).pow(2).mean()):.3f}")
print(f"\n  mean improvement from substituting the REALISED component (worst decile):")
for k,lbl in [("TP","actual PACE"),("TE","actual EFFICIENCY (both)"),("TEH","actual HOME eff"),
              ("TER","actual ROAD eff"),("TPE","actual PACE + EFFICIENCY")]:
    print(f"    {lbl:<28}{W['imp_'+k].mean():>+8.3f} pts   (all games {S['imp_'+k].mean():>+7.3f})")
# ---- classification ----
TH=1.0
def cls(r):
    p=r.imp_TP>TH; e=r.imp_TE>TH
    if p and e: return "pace + efficiency"
    if p: return "PACE state"
    if e:
        if r.imp_TEH>TH and r.imp_TER>TH: return "efficiency BOTH sides"
        if r.imp_TEH>TH: return "HOME efficiency"
        if r.imp_TER>TH: return "ROAD efficiency"
        return "efficiency (unsplit)"
    return "NEITHER (book-specific / unexplained)"
W["cls"]=W.apply(cls,axis=1)
sse=W.e0.pow(2).sum()
print(f"\n  SHARE OF WORST-DECILE SQUARED ERROR BY MECHANISM")
print(f"  {'mechanism':<40}{'n':>5}{'share of games':>16}{'share of SSE':>15}")
for k,g in W.groupby("cls"):
    print(f"  {k:<40}{len(g):>5}{100*len(g)/len(W):>15.1f}%{100*g.e0.pow(2).sum()/sse:>14.1f}%")
S.to_csv(SP+"oracle_panel.csv",index=False); W.to_csv(SP+"oracle_worst.csv",index=False)
