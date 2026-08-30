import sys; sys.path.insert(0,"/home/dpope/projects/nba_entropy_replication")
import warnings,numpy as np,pandas as pd; warnings.filterwarnings("ignore")
from scipy import stats
SP="/tmp/claude-1000/-home-dpope/4fa2e81b-35e9-49e8-92da-7bffe4f69700/scratchpad/"
G=pd.read_csv(SP+"eff_panel.csv"); G["date"]=pd.to_datetime(G.date).dt.strftime("%Y-%m-%d")
L=pd.read_csv(SP+"ladder_sigma.csv"); L["home"]=L.ev.str.extract(r"([A-Z]{3})$")
tm=pd.read_csv("team_mapping.csv"); mp=dict(zip(tm.abbr,tm.bigdataball_name))
L["home_n"]=L.home.map(mp); L["date"]=pd.to_datetime(L.date).dt.strftime("%Y-%m-%d")
M=L.merge(G[["date","TEAM_H","t3r","pace","esd","close","dev","is_ot","FGA_H","FGA_R"]],
          left_on=["date","home_n"],right_on=["date","TEAM_H"],how="inner").dropna(subset=["t3r"])
print(f"ladder x efficiency panel: {len(M):,} games")
print(f"  matchup 3PA rate: mean {M.t3r.mean():.4f}  sd {M.t3r.std():.4f}  range {M.t3r.min():.3f}..{M.t3r.max():.3f}")
print("\nORTHOGONALITY — is 3PA rate separable from what the ladder already uses?")
for a in ["pace","mu","close"]:
    print(f"  corr(3PArate, {a:<6}) = {M.t3r.corr(M[a]):+.4f}")
r2=M.t3r.corr(M.pace)**2+0  # report simple
X=np.column_stack([np.ones(len(M)),M.pace,M.mu]); b,*_=np.linalg.lstsq(X,M.t3r.values,rcond=None)
res=M.t3r.values-X@b
print(f"  residual 3PA-rate sd after pace+mu = {res.std():.4f} of {M.t3r.std():.4f}"
      f"  ({100*res.std()/M.t3r.std():.0f}% orthogonal)")

v3,v2=9*.36*.64,4*.53*.47; fga=(M.FGA_H+M.FGA_R).mean()
sg=M.sig.mean(); pred=fga*(v3-v2)/(2*sg)
print(f"\nPOISSON/SHOT-MIX PREDICTION for a 3PA-aware ladder")
print(f"  d(sigma)/d(3PArate) = FGA*(v3-v2)/(2*sigma) = {pred:.2f}")
print(f"  over the observed range that is {pred*(M.t3r.max()-M.t3r.min()):.2f} pts of sigma")

def reg(y,cols,X_,lbl):
    X=np.column_stack([np.ones(len(X_))]+[X_[c].values for c in cols])
    b,*_=np.linalg.lstsq(X,y,rcond=None); r=y-X@b
    se=np.sqrt(np.diag((r@r/(len(y)-len(cols)-1))*np.linalg.pinv(X.T@X)))
    print(f"  {lbl:<44}"+"  ".join(f"{c} {b[i+1]:+8.3f}(t={b[i+1]/se[i+1]:+5.2f})"
                                   for i,c in enumerate(cols)))
    return b,se
print("\nQ. DOES THE LADDER PRICE SHOT MIX?")
reg(M.sig.values,["t3r"],M,"implied_sigma ~ 3PArate")
b,se=reg(M.sig.values,["t3r","pace","mu"],M,"implied_sigma ~ 3PArate + pace + mu")
print(f"  MDE on the 3PA coefficient {1.96*se[1]:.2f}  vs prediction {pred:.2f}"
      f"  -> {'POWERED' if 1.96*se[1]<pred else 'UNDERPOWERED'}")
print(f"  95% CI [{b[1]-1.96*se[1]:+.2f}, {b[1]+1.96*se[1]:+.2f}]   prediction {pred:+.2f} is "
      f"{'INSIDE' if b[1]-1.96*se[1]<=pred<=b[1]+1.96*se[1] else 'OUTSIDE'}")
b2,se2=reg(M.sig.values,["esd","pace","mu"],M,"implied_sigma ~ prior_eff_SD + pace + mu")

print("\nDIRECT — high vs low matchup 3PA rate")
med=M.t3r.median(); hi,lo=M[M.t3r>med],M[M.t3r<=med]
t_,p_=stats.ttest_ind(hi.sig,lo.sig,equal_var=False)
print(f"  LADDER  hi {hi.sig.mean():.3f} (3PAr {hi.t3r.mean():.3f})  lo {lo.sig.mean():.3f}"
      f" (3PAr {lo.t3r.mean():.3f})   diff {hi.sig.mean()-lo.sig.mean():+.4f} (t={t_:+.2f}, p={p_:.4f})")
print(f"  shot-mix prediction for that gap: {pred*(hi.t3r.mean()-lo.t3r.mean()):+.4f} pts")
GG=G.dropna(subset=["dev"]); mg=GG.t3r.median()
a,b_=GG[GG.t3r>mg],GG[GG.t3r<=mg]
F=a.dev.var()/b_.dev.var()
print(f"  REALITY sd(dev) hi {a.dev.std():.3f}  lo {b_.dev.std():.3f}  ratio {np.sqrt(F):.4f}"
      f"  F p={2*min(stats.f.cdf(F,len(a)-1,len(b_)-1),1-stats.f.cdf(F,len(a)-1,len(b_)-1)):.4f}  (n={len(GG):,})")
