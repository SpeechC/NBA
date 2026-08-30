import sys; sys.path.insert(0,"/home/dpope/projects/nba_entropy_replication")
import warnings,numpy as np,pandas as pd; warnings.filterwarnings("ignore")
from scipy.stats import norm
SP="/tmp/claude-1000/-home-dpope/4fa2e81b-35e9-49e8-92da-7bffe4f69700/scratchpad/"
S=pd.read_csv(SP+"oracle_panel.csv"); S["date"]=pd.to_datetime(S.date)
S=S.sort_values("date").reset_index(drop=True)
S["actual"]=S.PTS_H+S.PTS_R; S["EffSum"]=S.sOH+S.sOR
# ---- team-level PRIOR-ONLY pace drift (mu) and volatility (sigma) ----
L=pd.concat([S[["date","yr","TEAM_H","dPace"]].rename(columns={"TEAM_H":"t"}),
             S[["date","yr","TEAM_R","dPace"]].rename(columns={"TEAM_R":"t"})]).sort_values(["t","date"])
g=L.groupby(["t","yr"])
L["mu5"]  =g.dPace.transform(lambda s:s.shift(1).rolling(5,min_periods=2).mean())    # DRIFT
L["mu15"] =g.dPace.transform(lambda s:s.shift(1).rolling(15,min_periods=4).mean())
L["sd10"] =g.dPace.transform(lambda s:s.shift(1).rolling(10,min_periods=4).std())    # VOLATILITY
km=L.set_index(["t","date"])
for c in ["mu5","mu15","sd10"]:
    S[c+"H"]=[km[c].get((t,d),np.nan) for t,d in zip(S.TEAM_H,S.date)]
    S[c+"R"]=[km[c].get((t,d),np.nan) for t,d in zip(S.TEAM_R,S.date)]
    S[c]=(S[c+"H"]+S[c+"R"])/2
S["short_long"]=(S.mu5-S.mu15).abs()
S["hr_gap"]=(S.mu5H-S.mu5R).abs()
S=S.dropna(subset=["mu5","sd10","EffSum","T0"]).reset_index(drop=True)
# ---- PREGAME pace SE model, chronological ----
UF=["sd10","short_long","hr_gap","sd10H","sd10R"]
def xfit(cols,tgt):
    pr=np.full(len(S),np.nan)
    for y in sorted(S.yr.unique()):
        tr=S[S.yr<y]; te=S[S.yr==y]
        if len(tr)<400 or not len(te): continue
        X=np.column_stack([np.ones(len(tr))]+[tr[c].values.astype(float) for c in cols])
        B=np.column_stack([np.ones(len(te))]+[te[c].values.astype(float) for c in cols])
        ok=np.isfinite(X).all(1)
        b,*_=np.linalg.lstsq(X[ok],tr[tgt].values[ok],rcond=None); pr[te.index]=B@b
    return pr
S["absdP"]=S.dPace.abs()
S["sigP"]=xfit(UF,"absdP")*1.2533          # E|x| -> sd for a normal
m=S.sigP.notna()
print(f"PREGAME PACE-UNCERTAINTY MODEL   n={m.sum():,}")
print(f"  OOS R2 of |pace error| ~ prior features = "
      f"{1-np.var((S.absdP-S.sigP)[m])/np.var(S.absdP[m]):.4f}")
q=pd.qcut(S.sigP[m],3,labels=['low','mid','high'])
D=S[m].copy(); D["qs"]=q.values
print(f"  {'sigma_P tercile':<18}{'n':>6}{'pred sigP':>11}{'ACTUAL sd(dPace)':>18}")
for k in ['low','mid','high']:
    s=D[D.qs==k]; print(f"  {k:<18}{len(s):>6}{s.sigP.mean():>11.3f}{s.dPace.std():>18.3f}")
# ---- BOOK-IMPLIED PACE by inversion ----
a_,b_=np.nan,np.nan
S["P_book"]=np.nan
for y in sorted(S.yr.unique()):
    tr=S[S.yr<y]; te=S[S.yr==y]
    if len(tr)<400 or not len(te): continue
    X=np.column_stack([np.ones(len(tr)),tr.T0.values*0+tr.sP.values*tr.EffSum.values/100])
    bb,*_=np.linalg.lstsq(X,tr.open.values,rcond=None)
    S.loc[te.index,"P_book"]=100*(te.open.values-bb[0])/(bb[1]*te.EffSum.values)
S["dP_book"]=S.sP-S.P_book                       # our pace minus book-implied pace
S["Zp"]=S.dP_book/S.sigP.clip(lower=0.3)
S["pace_pts"]=S.dP_book*S.EffSum/100             # pace disagreement in POINTS
T=S[S.yr>=2022].dropna(subset=["Zp","P_book","actual"]).copy()
T["y"]=T.actual-T.open; T["mv"]=T.close-T.open
print(f"\nBOOK-IMPLIED PACE   n={len(T):,}")
print(f"  P_book mean {T.P_book.mean():.2f}  our sP mean {T.sP.mean():.2f}"
      f"   gap sd {T.dP_book.std():.3f} poss = {T.pace_pts.std():.2f} pts")
def reg(s,x,y):
    X=np.column_stack([np.ones(len(s)),s[x]]); yy=s[y].values
    b,*_=np.linalg.lstsq(X,yy,rcond=None); r=yy-X@b
    se=np.sqrt(np.diag((r@r/(len(yy)-2))*np.linalg.pinv(X.T@X)))
    return b[1],b[1]/se[1]
print(f"\n  {'predictor':<26}{'-> close-open':>16}{'t':>7}{'-> ACTUAL-open':>17}{'t':>7}")
for nm,c in [("pace gap (points)","pace_pts"),("Z_pace (gap/sigma)","Zp"),("pace DRIFT mu5","mu5"),
             ("pace VOLATILITY sd10","sd10")]:
    b1,t1=reg(T,c,"mv"); b2,t2=reg(T,c,"y")
    print(f"  {nm:<26}{b1:>16.4f}{t1:>7.2f}{b2:>17.4f}{t2:>7.2f}")
print(f"\nGRID: pace gap x pace uncertainty  (economic test, {len(T):,} games)")
T["gq"]=pd.qcut(T.pace_pts,3,labels=["neg gap","mid","POS gap"])
T["uq"]=pd.qcut(T.sigP,2,labels=["low sigP","high sigP"])
print(f"  {'gap':<10}{'sigma':<12}{'n':>6}{'avg actual-open':>18}{'Over %':>9}{'avg close-open':>17}")
for gk in ["neg gap","mid","POS gap"]:
    for uk in ["low sigP","high sigP"]:
        s=T[(T.gq==gk)&(T.uq==uk)]
        ov=100*(s.actual>s.open).mean()
        print(f"  {gk:<10}{uk:<12}{len(s):>6}{s.y.mean():>+18.3f}{ov:>9.1f}{s.mv.mean():>+17.3f}")
print(f"\n  break-even at -110 = 52.381%   sd(actual-open) {T.y.std():.2f}"
      f"   se on a cell of ~780: {T.y.std()/np.sqrt(780):.2f} pts")
print(f"\nHIGH-TOTAL x HIGH-UNCERTAINTY (their specific hypothesis)")
T["tq"]=pd.cut(T.open,[0,220,230,240,999],labels=["<220","220-230","230-240","240+"])
for tk in T.tq.cat.categories:
    for uk in ["low sigP","high sigP"]:
        s=T[(T.tq==tk)&(T.uq==uk)]
        if len(s)<60: continue
        print(f"  {str(tk):<10}{uk:<12}{len(s):>6}{s.y.mean():>+18.3f}{100*(s.actual>s.open).mean():>9.1f}")
