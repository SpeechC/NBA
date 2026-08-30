import sys; sys.path.insert(0,"/home/dpope/projects/nba_entropy_replication")
import warnings,numpy as np,pandas as pd; warnings.filterwarnings("ignore")
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
S["D"]=S.sP-S.P_book
# RICH CURRENT-PROFILE space (all prior-only, contemporaneous team state)
PROF=["pace_H","pace_R","trans_H","trans_R","tov_H","tov_R","tovf_H","tovf_R",
      "ftr_H","ftr_R","ctrl_H","ctrl_R","mu5H","mu5R","ewvH","ewvR","sP",
      "PrefConflict","ControlConflict","TransComp","TovPressure","StyleDist"]
S=S.dropna(subset=PROF+["D","dPace","actual"]).reset_index(drop=True)
Z=S[PROF].apply(lambda c:(c-c.mean())/c.std()).values
e=S.dPace.values; D=S.D.values
print(f"PROFILE-CONDITIONED SURVIVAL   n={len(S):,}   profile dim {len(PROF)}")
K=150; BURN=500
psurv=np.full(len(S),np.nan); q80=np.full(len(S),np.nan); nanl=np.full(len(S),np.nan)
for i in range(BURN,len(S)):
    d=np.abs(Z[:i]-Z[i]).sum(1)
    idx=np.argpartition(d,K)[:K]
    ae=np.abs(e[idx])
    q80[i]=np.quantile(ae,0.80)
    # P(pace direction survives): fraction of analog errors that do NOT erase D
    psurv[i]=np.mean(e[idx]>-D[i]) if D[i]>0 else np.mean(e[idx]<-D[i])
    nanl[i]=d[idx].mean()
S["psurv"]=psurv; S["q80p"]=q80
T=S.dropna(subset=["psurv"]).copy()
T["y"]=T.actual-T.open; T["gap_pts"]=T.D*T.EffSum/100
sg=np.sign(T.gap_pts); T["win"]=((T.y*sg)>0)
T["pace_ok"]=(np.sign(T.gpace-T.P_book)==sg)
print(f"  scored {len(T):,} games   q80 mean {T.q80p.mean():.3f}  sd {T.q80p.std():.3f}"
      f"  range {T.q80p.min():.2f}-{T.q80p.max():.2f}")
print(f"  vs the THIN analog space earlier: q80 mean 5.147, sd small")
print(f"  p_survive: mean {T.psurv.mean():.3f}  p10 {T.psurv.quantile(.1):.3f}  p90 {T.psurv.quantile(.9):.3f}")
print()
print("  CALIBRATION: does predicted survival match realised pace-direction success?")
b=pd.cut(T.psurv,[0,.45,.5,.55,.6,.65,1.01],labels=["<45","45-50","50-55","55-60","60-65",">65"])
print(f"  {'p_survive band':<16}{'n':>6}{'mean pred':>11}{'ACTUAL pace dir':>17}{'BET hit':>10}{'mean y*sign':>13}")
for k in b.cat.categories:
    s=T[b==k]
    if len(s)<40: continue
    print(f"  {k:<16}{len(s):>6}{s.psurv.mean():>11.3f}{100*s.pace_ok.mean():>16.1f}%"
          f"{100*s.win.mean():>9.1f}%{(s.y*np.sign(s.gap_pts)).mean():>+13.3f}")
print(f"  break-even 52.381%")
from scipy import stats
c=T.psurv.corr(T.pace_ok.astype(float))
print(f"\n  corr(p_survive, realised pace direction) = {c:+.4f}"
      f"   (t={c*np.sqrt(len(T)-2)/np.sqrt(1-c**2):+.2f})")
c2=T.psurv.corr(T.win.astype(float))
print(f"  corr(p_survive, BET win)                 = {c2:+.4f}"
      f"   (t={c2*np.sqrt(len(T)-2)/np.sqrt(1-c2**2):+.2f})")
print(f"\n  DOES THE RICH q80 DISCRIMINATE? (it did not in the thin space)")
qq=pd.qcut(T.q80p,4,labels=False)
for i in range(4):
    s=T[qq==i]; print(f"    Q{i+1} pred q80 {s.q80p.mean():.3f}   ACTUAL sd(e) {s.dPace.std():.3f}"
                      f"   ACTUAL P(|e|<=q80) {100*(s.dPace.abs()<=s.q80p).mean():.1f}%")
lo,hi=T[qq==0].dPace,T[qq==3].dPace; F=hi.var()/lo.var()
print(f"    Q1 sd {lo.std():.3f} -> Q4 sd {hi.std():.3f}  ratio {hi.std()/lo.std():.4f}  F p="
      f"{2*min(stats.f.cdf(F,len(hi)-1,len(lo)-1),1-stats.f.cdf(F,len(hi)-1,len(lo)-1)):.4f}")
T.to_csv(SP+"profile_survive.csv",index=False)
