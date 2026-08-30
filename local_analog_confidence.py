import sys; sys.path.insert(0,"/home/dpope/projects/nba_entropy_replication")
import warnings,numpy as np,pandas as pd; warnings.filterwarnings("ignore")
SP="/tmp/claude-1000/-home-dpope/4fa2e81b-35e9-49e8-92da-7bffe4f69700/scratchpad/"
S=pd.read_csv(SP+"pace_var2.csv"); S["date"]=pd.to_datetime(S.date)
S=S.dropna(subset=["dPace","sP","mu5H","mu5R","p20H","p20R"]).sort_values("date").reset_index(drop=True)
S["EffSum"]=S.sOH+S.sOR; S["actual"]=S.PTS_H+S.PTS_R
S["P_book"]=np.nan
for y in sorted(S.yr.unique()):
    tr=S[S.yr<y]; te=S[S.yr==y]
    if len(tr)<400 or not len(te): continue
    X=np.column_stack([np.ones(len(tr)),tr.sP.values*tr.EffSum.values/100])
    b,*_=np.linalg.lstsq(X,tr.open.values,rcond=None)
    S.loc[te.index,"P_book"]=100*(te.open.values-b[0])/(b[1]*te.EffSum.values)
S["D"]=S.sP-S.P_book
S=S.dropna(subset=["P_book"]).reset_index(drop=True)
# ---- LOCAL ANALOGS in pace-state space, strictly PRIOR games ----
F=["p20H","p20R","mu5H","mu5R","sP"]
Z=S[F].copy()
for c in F: Z[c]=(Z[c]-Z[c].mean())/Z[c].std()
Z["gap"]=(S.p20H-S.p20R).abs(); Z["gap"]=(Z["gap"]-Z["gap"].mean())/Z["gap"].std()
A=Z.values; e=S.dPace.values; K=200
q80=np.full(len(S),np.nan); q90=np.full(len(S),np.nan); qn=np.full(len(S),np.nan)
order=np.argsort(S.date.values)
for i in range(len(S)):
    if i<600: continue
    d=np.abs(A[:i]-A[i]).sum(1)          # L1 in standardised state space, PRIOR games only
    idx=np.argpartition(d,K)[:K]
    ae=np.abs(e[idx])
    q80[i]=np.quantile(ae,0.80); q90[i]=np.quantile(ae,0.90); qn[i]=ae.mean()
S["q80"]=q80; S["q90"]=q90; S["qmae"]=qn
T=S.dropna(subset=["q80"]).copy()
print(f"LOCAL-ANALOG PACE-ERROR INTERVALS   n={len(T):,}  (K={K} nearest PRIOR games)")
print(f"  q80 of |pace error|: mean {T.q80.mean():.3f}  p10 {T.q80.quantile(.1):.3f}  p90 {T.q80.quantile(.9):.3f}")
print(f"  spread {T.q80.max()-T.q80.min():.3f} possessions")
print(f"\n  CALIBRATION: does the local q80 actually contain 80% of realised |e|?")
qq=pd.qcut(T.q80,4,labels=False)
print(f"  {'q80 quartile':<15}{'n':>6}{'mean q80':>10}{'ACTUAL P(|e|<=q80)':>21}{'ACTUAL sd(e)':>14}")
for i in range(4):
    s=T[qq==i]
    print(f"  {i+1:<15}{len(s):>6}{s.q80.mean():>10.3f}{100*(s.dPace.abs()<=s.q80).mean():>20.1f}%{s.dPace.std():>14.3f}")
print(f"  (a calibrated q80 should sit at 80% in EVERY quartile)")
# ---- PACE CONFIDENCE RATIO and the bet/pass test ----
T["ratio"]=T.D.abs()/T.q80
T["y"]=T.actual-T.open
T["gap_pts"]=T.D*T.EffSum/100
sg=np.sign(T.gap_pts)
T["win"]=((T.y*sg)>0)
T["dir_pace"]=(np.sign(T.dPace_book if False else (T.gpace-T.P_book))==sg)
print(f"\n  PACE CONFIDENCE RATIO = |model pace - book pace| / local q80")
print(f"  mean {T.ratio.mean():.3f}   p90 {T.ratio.quantile(.9):.3f}")
print(f"\\n  {'ratio band':<16}{'n':>6}{'mean |D|':>10}{'mean q80':>10}{'PACE dir %':>12}{'BET hit %':>11}{'mean y*sign':>13}")
bands=[(0,0.5,'<0.5 pass'),(0.5,1.0,'0.5-1.0 weak'),(1.0,1.5,'1.0-1.5 meaningful'),(1.5,99,'>1.5 strong')]
for lo,hi,lab in bands:
    s=T[(T.ratio>=lo)&(T.ratio<hi)]
    if len(s)<50: continue
    print(f"  {lab:<16}{len(s):>6}{s.D.abs().mean():>10.2f}{s.q80.mean():>10.2f}"
          f"{100*s.dir_pace.mean():>11.1f}%{100*s.win.mean():>10.1f}%{(s.y*np.sign(s.gap_pts)).mean():>+13.3f}")
print(f"  break-even 52.381%")
print(f"\n  does the RATIO beat the RAW GAP at ranking bets?")
for nm,c in [('raw |gap| quartile','gap_pts'),('ratio quartile','ratio')]:
    q=pd.qcut(T[c].abs() if nm.startswith('raw') else T[c],4,labels=False)
    hits=[100*T[q==i].win.mean() for i in range(4)]
    print(f"   {nm:<22}"+"  ".join(f"Q{i+1} {h:.1f}%" for i,h in enumerate(hits)))
T.to_csv(SP+"local_analog.csv",index=False)
