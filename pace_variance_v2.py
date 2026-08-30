import sys; sys.path.insert(0,"/home/dpope/projects/nba_entropy_replication")
import warnings,numpy as np,pandas as pd; warnings.filterwarnings("ignore")
SP="/tmp/claude-1000/-home-dpope/4fa2e81b-35e9-49e8-92da-7bffe4f69700/scratchpad/"
S=pd.read_csv(SP+"oracle_panel.csv"); S["date"]=pd.to_datetime(S.date)
S=S.sort_values("date").reset_index(drop=True)
# team-game pace panel with SHORT and LONG state estimates
P=pd.concat([S[["date","yr","TEAM_H","PACE_H","dPace","sP"]].rename(columns={"TEAM_H":"t","PACE_H":"pace"}),
             S[["date","yr","TEAM_R","PACE_R","dPace","sP"]].rename(columns={"TEAM_R":"t","PACE_R":"pace"})]
            ).sort_values(["t","date"])
g=P.groupby(["t","yr"])
P["p5"] =g.pace.transform(lambda s:s.shift(1).rolling(5,min_periods=2).mean())
P["p20"]=g.pace.transform(lambda s:s.shift(1).rolling(20,min_periods=5).mean())
P["p40"]=g.pace.transform(lambda s:s.shift(1).rolling(40,min_periods=8).mean())
P["Dp"] =(P.p5-P.p20).abs()                       # STATE AMBIGUITY (epistemic)
P["Dp2"]=(P.p20-P.p40).abs()
P["mu5"]=g.dPace.transform(lambda s:s.shift(1).rolling(5,min_periods=2).mean())   # DRIFT
P["mu15"]=g.dPace.transform(lambda s:s.shift(1).rolling(15,min_periods=4).mean())
P["ewv"]=g.dPace.transform(lambda s:s.shift(1).pow(2).ewm(halflife=8,min_periods=4).mean())  # EWMA variance
P["sd10"]=g.dPace.transform(lambda s:s.shift(1).rolling(10,min_periods=4).std())
P["flip"]=g.dPace.transform(lambda s:(np.sign(s)!=np.sign(s.shift(1))).shift(1).rolling(10,min_periods=4).mean())
K=P.set_index(["t","date"])
for c in ["p5","p20","Dp","Dp2","mu5","mu15","ewv","sd10","flip"]:
    S[c+"H"]=[K[c].get((t,d),np.nan) for t,d in zip(S.TEAM_H,S.date)]
    S[c+"R"]=[K[c].get((t,d),np.nan) for t,d in zip(S.TEAM_R,S.date)]
S["Dp_g"]=(S.DpH+S.DpR)/2; S["Dp2_g"]=(S.Dp2H+S.Dp2R)/2
S["ewv_g"]=(S.ewvH+S.ewvR)/2; S["sd10_g"]=(S.sd10H+S.sd10R)/2
S["flip_g"]=(S.flipH+S.flipR)/2
S["clash"]=(S.p20H-S.p20R).abs()                  # pace-preference clash
S["volx"]=S.ewvH*S.ewvR                           # interaction
S["mu_g"]=(S.mu5H+S.mu5R)/2
S["early"]=(S.groupby(["yr"]).cumcount()<200).astype(float)
S=S.dropna(subset=["Dp_g","ewv_g","sd10_g","mu_g","dPace"]).reset_index(drop=True)
def xf(cols,tgt):
    pr=np.full(len(S),np.nan)
    for y in sorted(S.yr.unique()):
        tr=S[S.yr<y]; te=S[S.yr==y]
        if len(tr)<400 or not len(te): continue
        X=np.column_stack([np.ones(len(tr))]+[tr[c].values.astype(float) for c in cols])
        B=np.column_stack([np.ones(len(te))]+[te[c].values.astype(float) for c in cols])
        ok=np.isfinite(X).all(1)
        b,*_=np.linalg.lstsq(X[ok],tr[tgt].values[ok],rcond=None); pr[te.index]=B@b
    return pr
# ---- STEP 1: model the DRIFT, then residualise ----
S["mu_hat"]=xf(["mu_g","Dp_g","Dp2_g"],"dPace")
S["u"]=S.dPace-S.mu_hat
m0=S.mu_hat.notna()
print(f"STEP 1 — DRIFT MODEL   n={m0.sum():,}")
print(f"  var(raw pace error) {S.dPace[m0].var():.3f}  ->  var(u after drift removal) {S.u[m0].var():.3f}"
      f"   ({100*(1-S.u[m0].var()/S.dPace[m0].var()):.1f}% removed)")
# ---- STEP 2: variance model on the RESIDUALISED u ----
S["u2"]=S.u**2
VF=["ewv_g","sd10_g","Dp_g","Dp2_g","clash","volx","flip_g","sP","early"]
S=S.dropna(subset=VF+["u","u2","mu_hat"]).reset_index(drop=True)
S["v_hat"]=xf(VF,"u2"); S["sig"]=np.sqrt(S.v_hat.clip(lower=0.5))
m=S.sig.notna()&S.u.notna()
D=S[m].copy(); D["q"]=pd.qcut(D.sig,3,labels=["low","mid","high"])
print(f"\nSTEP 2 — VARIANCE MODEL ON RESIDUALISED u   n={len(D):,}")
print("  EVALUATED BY CALIBRATION, NOT R2 (their correction)")
print(f"  {'sigma tercile':<16}{'n':>6}{'pred sigma':>12}{'ACTUAL sd(u)':>14}{'sd(u/sigma)':>13}{'P(|u|>5)':>11}")
for k in ["low","mid","high"]:
    s=D[D.q==k]
    print(f"  {k:<16}{len(s):>6}{s.sig.mean():>12.3f}{s.u.std():>14.3f}"
          f"{(s.u/s.sig).std():>13.3f}{100*(s.u.abs()>5).mean():>10.1f}%")
lo,hi=D[D.q=="low"],D[D.q=="high"]
print(f"\n  ACTUAL sd(u):  low {lo.u.std():.3f}  ->  high {hi.u.std():.3f}"
      f"   ratio {hi.u.std()/lo.u.std():.3f}")
from scipy import stats
F=hi.u.var()/lo.u.var()
p=2*min(stats.f.cdf(F,len(hi)-1,len(lo)-1),1-stats.f.cdf(F,len(hi)-1,len(lo)-1))
print(f"  variance ratio {F:.4f}   F-test p={p:.4f}   "
      f"{'SEPARATES' if p<0.05 else 'does NOT separate'}")
print(f"  tail rate P(|u|>5):  low {100*(lo.u.abs()>5).mean():.1f}%  high {100*(hi.u.abs()>5).mean():.1f}%")
print(f"  if calibrated, sd(u/sigma) should be ~CONSTANT across terciles")
print(f"\n  R2 on u^2 (the metric they said NOT to use) = "
      f"{1-np.var((S.u2-S.v_hat)[m])/np.var(S.u2[m]):.4f}")
print(f"\nWHICH FEATURE CARRIES IT?  (univariate variance separation, high vs low tercile)")
for c in ["Dp_g","Dp2_g","ewv_g","sd10_g","clash","flip_g","volx"]:
    t3=pd.qcut(D[c],3,labels=[0,1,2],duplicates="drop")
    a=D[t3==0].u.std(); b=D[t3==2].u.std()
    print(f"   {c:<10} low-tercile sd(u) {a:.3f}   high-tercile sd(u) {b:.3f}   ratio {b/a:.4f}")
S.to_csv(SP+"pace_var2.csv",index=False)
