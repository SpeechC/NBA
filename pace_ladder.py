import sys; sys.path.insert(0,"/home/dpope/projects/nba_entropy_replication")
import warnings,numpy as np,pandas as pd; warnings.filterwarnings("ignore")
from scipy import stats
SP="/tmp/claude-1000/-home-dpope/4fa2e81b-35e9-49e8-92da-7bffe4f69700/scratchpad/"
G=pd.read_csv(SP+"pace_panel.csv"); G["date"]=pd.to_datetime(G.date).dt.strftime("%Y-%m-%d")
L=pd.read_csv(SP+"ladder_sigma.csv"); L["home"]=L.ev.str.extract(r"([A-Z]{3})$")
tm=pd.read_csv("team_mapping.csv"); mp=dict(zip(tm.abbr,tm.bigdataball_name))
L["home_n"]=L.home.map(mp); L["date"]=pd.to_datetime(L.date).dt.strftime("%Y-%m-%d")
M=L.merge(G[["date","TEAM_H","pp","close","dev","is_ot"]],left_on=["date","home_n"],
          right_on=["date","TEAM_H"],how="inner").dropna(subset=["pp"])
print(f"ladder x pace panel: {len(M):,} games   pace sd {M.pp.std():.3f}")

def reg(y,cols,X_,lbl):
    X=np.column_stack([np.ones(len(X_))]+[X_[c].values for c in cols])
    b,*_=np.linalg.lstsq(X,y,rcond=None); r=y-X@b
    se=np.sqrt(np.diag((r@r/(len(y)-len(cols)-1))*np.linalg.pinv(X.T@X)))
    print(f"  {lbl:<44}"+"   ".join(f"{c} {b[i+1]:+8.4f} (t={b[i+1]/se[i+1]:+5.2f})"
                                    for i,c in enumerate(cols)))
    return b,se

sg=M.sig.mean(); v=sg**2/(2*M.pp.mean()); pred=2*v/(2*sg)
print(f"\nPOISSON PREDICTION for a pace-aware ladder: d(sigma)/d(pace) = v/sigma = {pred:+.4f}")
print(f"  over the observed pace range that is {pred*(M.pp.max()-M.pp.min()):.2f} pts of sigma")
print("\nQ3. DOES THE LADDER PRICE PACE?")
reg(M.sig.values,["pp"],M,"implied_sigma ~ exp_pace")
b,se=reg(M.sig.values,["pp","mu"],M,"implied_sigma ~ exp_pace + implied_mu")
print(f"  MDE on the pace coefficient = {1.96*se[1]:+.4f}  vs Poisson {pred:+.4f}"
      f"  -> {'POWERED' if 1.96*se[1]<pred else 'UNDERPOWERED'}")
print(f"  95% CI on pace coef [{b[1]-1.96*se[1]:+.4f}, {b[1]+1.96*se[1]:+.4f}]"
      f"   Poisson {pred:+.4f} is {'INSIDE' if b[1]-1.96*se[1]<=pred<=b[1]+1.96*se[1] else 'OUTSIDE'}")

print("\nQ4. DIRECT — high vs low expected pace, within line terciles (LADDER side)")
M["lq"]=pd.qcut(M.close,3,labels=False)
print(f"  {'line tercile':<14}{'pace half':<11}{'n':>6}{'mean pace':>10}{'LADDER sig':>12}")
for i in range(3):
    s=M[M.lq==i]; med=s.pp.median()
    for lab,ss in [("LOW pace",s[s.pp<=med]),("HIGH pace",s[s.pp>med])]:
        print(f"  {i+1:<14}{lab:<11}{len(ss):>6}{ss.pp.mean():>10.2f}{ss.sig.mean():>12.3f}")
med=M.pp.median(); hi,lo=M[M.pp>med],M[M.pp<=med]
t_,p_=stats.ttest_ind(hi.sig,lo.sig,equal_var=False)
print(f"\n  overall HIGH-LOW pace ladder sigma {hi.sig.mean()-lo.sig.mean():+.4f} (t={t_:+.2f}, p={p_:.4f})")

print("\nQ5. RECONCILE — is the Q2 reality pattern robust? (full sample, OT split)")
for tag,S in [("with OT",G),("no OT",G[G.is_ot==0])]:
    S=S.copy(); S["lq"]=pd.qcut(S.close,3,labels=False); ds=[]
    for i in range(3):
        s=S[S.lq==i]; m=s.pp.median()
        a,b_=s[s.pp>m],s[s.pp<=m]
        d_=a.dev.std()-b_.dev.std()
        sd_=np.sqrt(a.dev.std()**2/(2*len(a))+b_.dev.std()**2/(2*len(b_)))
        ds.append((i+1,d_,sd_,d_/sd_))
    print(f"  {tag:<9}"+"  ".join(f"T{i}: {d_:+.3f} (t={z:+.2f})" for i,d_,s_,z in ds))
