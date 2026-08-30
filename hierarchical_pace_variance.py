import sys; sys.path.insert(0,"/home/dpope/projects/nba_entropy_replication")
import warnings,numpy as np,pandas as pd; warnings.filterwarnings("ignore")
from scipy import stats
SP="/tmp/claude-1000/-home-dpope/4fa2e81b-35e9-49e8-92da-7bffe4f69700/scratchpad/"
S=pd.read_csv(SP+"pace_var2.csv"); S["date"]=pd.to_datetime(S.date)
B=pd.read_csv(SP+"stageB_panel.csv"); B["date"]=pd.to_datetime(B.date)
S=S.merge(B[["date","TEAM_H","doy","restH","restR"]],on=["date","TEAM_H"],how="left")
R=pd.read_csv(SP+"roster_state.csv"); R["date"]=pd.to_datetime(R.date)
S=S.merge(R[["date","team","continuity","n_subs"]].rename(columns={"team":"TEAM_H"}),on=["date","TEAM_H"],how="left")
S=S.merge(R[["date","team","continuity","n_subs"]].rename(
    columns={"team":"TEAM_R","continuity":"continuity_R","n_subs":"n_subs_R"}),on=["date","TEAM_R"],how="left")
S=S.dropna(subset=["u","sP","doy"]).sort_values("date").reset_index(drop=True)
S["restmin"]=S[["restH","restR"]].min(axis=1).fillna(1)
S["rost"]=(2-S.continuity.fillna(0.85)-S.continuity_R.fillna(0.85))     # roster INSTABILITY
S["u2"]=S.u**2
teams=sorted(set(S.TEAM_H)|set(S.TEAM_R))
print(f"HIERARCHICAL PACE-VARIANCE MODEL   n={len(S):,}   teams {len(teams)}")
print(f"  grand mean sd(u) = {S.u.std():.4f}")
# ---- EMPIRICAL-BAYES team variance effects, estimated from PRIOR SEASONS ONLY ----
def team_effects(tr):
    L=pd.concat([tr[["TEAM_H","u2"]].rename(columns={"TEAM_H":"t"}),
                 tr[["TEAM_R","u2"]].rename(columns={"TEAM_R":"t"})])
    g=L.groupby("t").u2.agg(["mean","size"]); g=g[g["size"]>=30]
    gm=L.u2.mean()                                   # grand mean variance
    # sampling variance of a mean-of-squares ~ 2*sigma^4/n
    samp=2*gm**2/g["size"]
    tau2=max(g["mean"].var()-samp.mean(),0.0)        # method-of-moments between-team variance
    w=tau2/(tau2+samp)                               # shrinkage weight per team
    shrunk=w*g["mean"]+(1-w)*gm
    return shrunk,gm,tau2,w.mean(),g
print(f"\n  {'season':<9}{'tau^2':>10}{'mean shrink w':>15}{'implied sd range (shrunk)':>28}")
S["v_pred"]=np.nan
for y in sorted(S.yr.unique())[1:]:
    tr=S[S.yr<y]; te=S[S.yr==y]
    if len(tr)<600 or not len(te): continue
    sh,gm,tau2,wbar,g=team_effects(tr)
    vh=te.TEAM_H.map(sh).fillna(gm); vr=te.TEAM_R.map(sh).fillna(gm)
    # game variance = average of the two team effects, plus covariates (fit on train)
    trh=tr.TEAM_H.map(sh).fillna(gm); trr=tr.TEAM_R.map(sh).fillna(gm)
    Xtr=np.column_stack([np.ones(len(tr)),(trh+trr)/2,tr.sP,tr.restmin,tr.doy,tr.rost])
    b,*_=np.linalg.lstsq(Xtr,tr.u2.values,rcond=None)
    Xte=np.column_stack([np.ones(len(te)),(vh+vr)/2,te.sP,te.restmin,te.doy,te.rost])
    S.loc[te.index,"v_pred"]=Xte@b
    print(f"  {int(y):<9}{tau2:>10.4f}{wbar:>15.3f}"
          f"{f'{np.sqrt(sh.min()):.2f} - {np.sqrt(sh.max()):.2f}':>28}")
D=S.dropna(subset=["v_pred"]).copy(); D["sig_pred"]=np.sqrt(D.v_pred.clip(lower=1))
print(f"\nPROSPECTIVE TEST — do predicted-variance quintiles deliver?   n={len(D):,}")
q=pd.qcut(D.sig_pred,5,labels=False)
print(f"  {'quintile':<10}{'n':>6}{'predicted sd':>14}{'ACTUAL sd(u)':>15}{'+-noise':>9}")
for i in range(5):
    s=D[q==i]
    print(f"  {i+1:<10}{len(s):>6}{s.sig_pred.mean():>14.3f}{s.u.std():>15.3f}"
          f"{s.u.std()/np.sqrt(2*len(s)):>9.3f}")
lo,hi=D[q==0].u,D[q==4].u
F=hi.var()/lo.var(); p=2*min(stats.f.cdf(F,len(hi)-1,len(lo)-1),1-stats.f.cdf(F,len(hi)-1,len(lo)-1))
print(f"\n  Q1 {lo.std():.3f}  ->  Q5 {hi.std():.3f}   ratio {hi.std()/lo.std():.4f}   F p={p:.4f}"
      f"   {'SEPARATES' if p<0.05 else 'does NOT separate'}")
print(f"  their benchmark was Q1~3.5 vs Q5~4.5 (ratio 1.286)")
print(f"  spearman(predicted rank, actual sd by quintile) = "
      f"{pd.Series(range(5)).corr(pd.Series([D[q==i].u.std() for i in range(5)]),method='spearman'):+.3f}")
print(f"\n  in TOTAL-POINTS space (x EffSum/100 = {(S.sOH+S.sOR).mean()/100:.2f}):")
ef=(S.sOH+S.sOR).mean()/100
print(f"    Q1 {lo.std()*ef:.2f} pts   Q5 {hi.std()*ef:.2f} pts   difference {(hi.std()-lo.std())*ef:+.2f}")
print("\nARE THE SHRUNK TEAM EFFECTS STABLE? (last split)")
sh,gm,tau2,wbar,g=team_effects(S[S.yr<S.yr.max()])
z=pd.DataFrame({"raw_sd":np.sqrt(g["mean"]),"shrunk_sd":np.sqrt(sh),"n":g["size"]}).sort_values("shrunk_sd")
print(f"  raw sd range   {z.raw_sd.min():.2f} - {z.raw_sd.max():.2f}   (spread {z.raw_sd.max()-z.raw_sd.min():.2f})")
print(f"  SHRUNK range   {z.shrunk_sd.min():.2f} - {z.shrunk_sd.max():.2f}   (spread {z.shrunk_sd.max()-z.shrunk_sd.min():.2f})")
print(f"  mean shrinkage weight {wbar:.3f}  -> {100*(1-wbar):.0f}% of each team estimate is pulled to the mean")
print("  tightest:",{k:round(v,2) for k,v in z.shrunk_sd.head(3).items()})
print("  loosest :",{k:round(v,2) for k,v in z.shrunk_sd.tail(3).items()})
