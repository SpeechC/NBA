import sys; sys.path.insert(0,"/home/dpope/projects/nba_entropy_replication")
import warnings,numpy as np,pandas as pd; warnings.filterwarnings("ignore")
from scipy.stats import norm
SP="/tmp/claude-1000/-home-dpope/4fa2e81b-35e9-49e8-92da-7bffe4f69700/scratchpad/"
S=pd.read_csv(SP+"style_panel.csv"); S["date"]=pd.to_datetime(S.date)
S=S.sort_values("date").reset_index(drop=True)
S["EffSum"]=S.sOH+S.sOR; S["actual"]=S.PTS_H+S.PTS_R
S["P_book"]=np.nan
for y in sorted(S.yr.unique()):
    tr=S[S.yr<y]; te=S[S.yr==y]
    if len(tr)<300 or not len(te): continue
    X=np.column_stack([np.ones(len(tr)),tr.sP.values*tr.EffSum.values/100])
    b,*_=np.linalg.lstsq(X,tr.open.values,rcond=None)
    S.loc[te.index,"P_book"]=100*(te.open.values-b[0])/(b[1]*te.EffSum.values)
PROF=["pace_H","pace_R","trans_H","trans_R","tov_H","tov_R","tovf_H","tovf_R",
      "ftr_H","ftr_R","ctrl_H","ctrl_R","mu5H","mu5R","ewvH","ewvR","sP",
      "PrefConflict","ControlConflict","TransComp","TovPressure","StyleDist"]
DRIFT=["mu5H","mu5R"]
S=S.dropna(subset=PROF+["dPace","actual"]).reset_index(drop=True)
S["D"]=S.sP-S.P_book
print(f"CONDITIONAL PACE-ERROR CORRECTION  m(X) = E[e | current profiles]   n={len(S):,}")
print("  m(X) is fit on PROFILE FEATURES ONLY -- no opener, no book pace, no |D|")
def xf(cols,lam=1.0,tgt="dPace"):
    pr=np.full(len(S),np.nan)
    for y in sorted(S.yr.unique()):
        tr=S[S.yr<y]; te=S[S.yr==y]
        if len(tr)<400 or not len(te): continue
        Xt=np.column_stack([np.ones(len(tr))]+[((tr[c]-S[c].mean())/S[c].std()).values for c in cols])
        Xe=np.column_stack([np.ones(len(te))]+[((te[c]-S[c].mean())/S[c].std()).values for c in cols])
        P=np.eye(Xt.shape[1])*lam; P[0,0]=0
        b=np.linalg.solve(Xt.T@Xt+P,Xt.T@tr[tgt].values)
        pr[te.index]=Xe@b
    return pr
S["m_drift"]=xf(DRIFT); S["m_full"]=xf(PROF,lam=20.0)
T=S.dropna(subset=["m_full","m_drift","P_book"]).copy()
print(f"  scored {len(T):,}   sd(e) {T.dPace.std():.3f}")
def ev(c,lbl):
    m=T[c]; X=np.column_stack([np.ones(len(T)),m]); y=T.dPace.values
    b,*_=np.linalg.lstsq(X,y,rcond=None); r=y-X@b
    se=np.sqrt(np.diag((r@r/(len(y)-2))*np.linalg.pinv(X.T@X)))
    print(f"  {lbl:<22} sd(m) {m.std():.4f}   e ~ m: beta {b[1]:+.4f} (t={b[1]/se[1]:+.2f})"
          f"   R2 {1-r.var()/y.var():+.5f}")
print("\n1. DOES m(X) PREDICT THE PACE ERROR?  (e ~ m_hat, beta>0 if informative)")
ev("m_drift","drift only (mu5)"); ev("m_full","full 22-dim profile")
print("\n2. DOES D* = D + m(X) BEAT D?")
T["Ds_d"]=T.D+T.m_drift; T["Ds_f"]=T.D+T.m_full
T["ap"]=T.gpace-T.P_book                      # actual pace - book pace
T["y"]=T.actual-T.open
def cmp(c,lbl):
    for tgt,tn in [("ap","ActualPace-BookPace"),("y","ActualTotal-Open")]:
        X=np.column_stack([np.ones(len(T)),T[c]*(T.EffSum/100 if tgt=="y" else 1)])
        yy=T[tgt].values; b,*_=np.linalg.lstsq(X,yy,rcond=None); r=yy-X@b
        se=np.sqrt(np.diag((r@r/(len(yy)-2))*np.linalg.pinv(X.T@X)))
        sg=np.sign(T[c]); hit=((yy*sg)>0).mean()
        print(f"  {lbl:<12}-> {tn:<22} beta {b[1]:+.4f} (t={b[1]/se[1]:+5.2f})"
              f"   hit {100*hit:.2f}%   ROI {100*(1.90909*hit-1):+.2f}%")
cmp("D","D (raw)"); cmp("Ds_d","D* drift"); cmp("Ds_f","D* full")
print(f"  break-even 52.381%")
print("\n3. DOES THE FULL PROFILE ADD BEYOND DRIFT?")
X=np.column_stack([np.ones(len(T)),T.m_drift,T.m_full]); y=T.dPace.values
b,*_=np.linalg.lstsq(X,y,rcond=None); r=y-X@b
se=np.sqrt(np.diag((r@r/(len(y)-3))*np.linalg.pinv(X.T@X)))
print(f"  e ~ m_drift + m_full:  drift {b[1]:+.4f} (t={b[1]/se[1]:+.2f})   full {b[2]:+.4f} (t={b[2]/se[2]:+.2f})")
print(f"  corr(m_drift, m_full) = {T.m_drift.corr(T.m_full):+.4f}")
print("\n4. INCREMENTAL VALUE ON THE BET")
for c,l in [("D","D raw"),("Ds_d","D + drift"),("Ds_f","D + full profile")]:
    sg=np.sign(T[c]); w=((T.y*sg)>0); h=w.mean(); s=np.sqrt(h*(1-h)/len(T))
    print(f"  {l:<18} hit {100*h:.2f}%  se {100*s:.2f}pp  edge/bet {(T.y*sg).mean():+.3f} pts")
