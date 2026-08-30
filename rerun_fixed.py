import sys; sys.path.insert(0,"/home/dpope/projects/nba_entropy_replication")
import warnings,numpy as np,pandas as pd; warnings.filterwarnings("ignore")
from prepare_data import read_master, season_label
SP="/tmp/claude-1000/-home-dpope/4fa2e81b-35e9-49e8-92da-7bffe4f69700/scratchpad/"
S=pd.read_csv(SP+"sigma_fixed.csv"); S["home"]=S.ev.str.extract(r"([A-Z]{3})$")
tm=pd.read_csv("team_mapping.csv"); mp=dict(zip(tm.abbr,tm.bigdataball_name))
S["home_n"]=S.home.map(mp); S["date"]=pd.to_datetime(S.date).dt.strftime("%Y-%m-%d")
E=pd.read_csv(SP+"eff_panel.csv"); E["date"]=pd.to_datetime(E.date).dt.strftime("%Y-%m-%d")
M=S.merge(E[["date","TEAM_H","t3r","pace","close","dev","total"]],
          left_on=["date","home_n"],right_on=["date","TEAM_H"],how="inner").dropna(subset=["t3r"])
print(f"n = {len(M):,} regular-season ladders, fixed estimators\n")
def ols(y,cols,X_):
    X=np.column_stack([np.ones(len(X_))]+[X_[c].values for c in cols])
    b,*_=np.linalg.lstsq(X,y,rcond=None); r=y-X@b
    se=np.sqrt(np.diag((r@r/(len(y)-len(cols)-1))*np.linalg.pinv(X.T@X)))
    return b,se
EST=[("OLS (old)","sig_ols"),("WLS","sig_wls"),("INTERVAL","sig_iv")]

print("1. CALIBRATION — mean implied sigma vs realised")
rs=M.dev.std()
for lab,c in EST:
    print(f"   {lab:<11} mean {M[c].mean():.3f}  vs realised sd(dev) {rs:.3f}"
          f"   -> {100*(M[c].mean()/rs-1):+.2f}%")
print("\n2. LINK 4 — sigma ~ implied mu   (Poisson +0.0396, TRUE +0.0403)")
for lab,c in EST:
    b,se=ols(M[c].values,["mu_iv"],M)
    print(f"   {lab:<11}{b[1]:+8.5f} (t={b[1]/se[1]:+5.2f})  CI [{b[1]-1.96*se[1]:+.5f},"
          f" {b[1]+1.96*se[1]:+.5f}]  Poisson {'IN' if b[1]-1.96*se[1]<=0.0396<=b[1]+1.96*se[1] else 'OUT'}")
print("\n3. LINK 5 — pace | mu    (Poisson benchmark +0.0911)")
for lab,c in EST:
    b,se=ols(M[c].values,["pace","mu_iv"],M)
    print(f"   {lab:<11}{b[1]:+8.4f} (t={b[1]/se[1]:+5.2f})  CI [{b[1]-1.96*se[1]:+.4f},"
          f" {b[1]+1.96*se[1]:+.4f}]  Poisson {'IN' if b[1]-1.96*se[1]<=0.0911<=b[1]+1.96*se[1] else 'OUT'}")
print("\n4. LINK 6 — 3PA rate | pace, mu   (corrected benchmark +4.87)")
for lab,c in EST:
    b,se=ols(M[c].values,["t3r","pace","mu_iv"],M)
    print(f"   {lab:<11}{b[1]:+8.4f} (t={b[1]/se[1]:+5.2f})  CI [{b[1]-1.96*se[1]:+.4f},"
          f" {b[1]+1.96*se[1]:+.4f}]  bench {'IN' if b[1]-1.96*se[1]<=4.87<=b[1]+1.96*se[1] else 'OUT'}")
print("\n5. THE OPEN QUESTION — is the sigma variation INFORMATION or ERROR?")
tgt=2*M.sig_iv.mean()
print(f"   informative = {tgt:.1f};  pure noise = 0")
for lab,c in EST:
    b,se=ols((M.dev**2).values,[c,"close"],M)
    lo,hi=b[1]-1.96*se[1],b[1]+1.96*se[1]
    v="RESOLVED: NOISE" if hi<tgt and lo<=0<=hi else ("INFORMATIVE" if lo>0 else "unresolved")
    print(f"   {lab:<11}{b[1]:+9.2f} (t={b[1]/se[1]:+5.2f})  CI [{lo:+8.1f}, {hi:+8.1f}]"
          f"  MDE {1.96*se[1]:6.1f}  {v}")
print(f"\n   {'quintile of INTERVAL sigma':<28}{'n':>6}{'mean sigma':>12}{'realised sd(dev)':>18}{'+-':>7}")
q=pd.qcut(M.sig_iv,5,labels=False)
for i in range(5):
    s=M[q==i]
    print(f"   {i+1:<28}{len(s):>6}{s.sig_iv.mean():>12.3f}{s.dev.std():>18.3f}"
          f"{s.dev.std()/np.sqrt(2*len(s)):>7.3f}")
