import sys; sys.path.insert(0,"/home/dpope/projects/nba_entropy_replication")
import warnings,numpy as np,pandas as pd; warnings.filterwarnings("ignore")
from prepare_data import read_master, season_label
SP="/tmp/claude-1000/-home-dpope/4fa2e81b-35e9-49e8-92da-7bffe4f69700/scratchpad/"
raw=read_master(verbose=False); raw["season"]=season_label(raw).astype(str)
n=lambda c: pd.to_numeric(raw[c],errors="coerce")
d=raw.copy()
d["spread"]=n("CLOSING SPREAD_H"); d["restH"]=n("TEAM\nREST DAYS_H"); d["restR"]=n("TEAM\nREST DAYS_R")
d["date"]=pd.to_datetime(d["DATE"],errors="coerce")
d=d[d.season.str.contains("Regular Season",na=False)]
d["doy"]=(d.date-d.groupby("season").date.transform("min")).dt.days
E=pd.read_csv(SP+"eff_panel.csv"); E["date"]=pd.to_datetime(E.date)
E=E.merge(d[["date","TEAM_H","spread","restH","restR","doy"]],on=["date","TEAM_H"],how="left")
E["date"]=E.date.dt.strftime("%Y-%m-%d")
L=pd.read_csv(SP+"ladder_sigma.csv"); L["home"]=L.ev.str.extract(r"([A-Z]{3})$")
tm=pd.read_csv("team_mapping.csv"); mp=dict(zip(tm.abbr,tm.bigdataball_name))
L["home_n"]=L.home.map(mp); L["date"]=pd.to_datetime(L.date).dt.strftime("%Y-%m-%d")
M=L.merge(E,left_on=["date","home_n"],right_on=["date","TEAM_H"],how="inner")
M["aspread"]=M.spread.abs(); M["restmin"]=M[["restH","restR"]].min(axis=1)
M["restmax"]=M[["restH","restR"]].max(axis=1); M["b2b"]=(M.restmin<=1).astype(float)
M=M.dropna(subset=["t3r","pace","aspread","restmin","doy"])
print(f"n = {len(M):,} ladders with the full candidate set\n")

def fit(cols,lbl):
    X=np.column_stack([np.ones(len(M))]+[M[c].values for c in cols])
    b,*_=np.linalg.lstsq(X,M.sig.values,rcond=None); r=M.sig.values-X@b
    se=np.sqrt(np.diag((r@r/(len(M)-len(cols)-1))*np.linalg.pinv(X.T@X)))
    R2=1-r.var()/M.sig.var()
    print(f"  {lbl:<34} R2 {R2:6.4f}")
    for i,c in enumerate(cols):
        t=b[i+1]/se[i+1]
        if abs(t)>1.7: print(f"      {c:<12}{b[i+1]:+10.5f} (t={t:+5.2f})")
    return R2
print("BACKING OUT THE FORMULA — nested, each block added to the last")
fit(["mu"],"mu")
fit(["mu","pace"],"+ pace")
fit(["mu","pace","t3r"],"+ 3PA rate")
fit(["mu","pace","t3r","aspread"],"+ |spread|")
fit(["mu","pace","t3r","aspread","restmin","restmax","b2b"],"+ rest / B2B")
fit(["mu","pace","t3r","aspread","restmin","restmax","b2b","doy"],"+ day of season")
R2f=fit(["mu","pace","t3r","aspread","restmin","restmax","b2b","doy","esd","sprd"],
        "+ prior eff sd + quoted spread")
print(f"\n  EVERYTHING WE HAVE: R2 {R2f:.4f} of observed; of TRUE variation "
      f"{100*R2f*M.sig.var()/(M.sig.var()-0.2246):.1f}%")

print("\nIS THE LADDER'S SIGMA INFORMATION OR ERROR?")
print("  test: does the ladder's own sigma predict how wide the game LANDS?")
X=np.column_stack([np.ones(len(M)),M.sig.values,M.close.values]); y=(M.dev**2).values
b,*_=np.linalg.lstsq(X,y,rcond=None); r=y-X@b
se=np.sqrt(np.diag((r@r/(len(y)-3))*np.linalg.pinv(X.T@X)))
pred=2*M.sig.mean()
print(f"  dev^2 ~ implied_sigma + close    sigma {b[1]:+8.3f} (t={b[1]/se[1]:+.2f})")
print(f"  FULLY-INFORMATIVE prediction d(sigma^2)/d(sigma) = 2*sigma = {pred:.1f}")
print(f"  PURE-NOISE prediction = 0.0")
print(f"  se {se[1]:.2f} -> 95% CI [{b[1]-1.96*se[1]:+.1f}, {b[1]+1.96*se[1]:+.1f}]")
print(f"    informative ({pred:.0f}) is {'INSIDE' if b[1]-1.96*se[1]<=pred<=b[1]+1.96*se[1] else 'OUTSIDE'};"
      f"  noise (0) is {'INSIDE' if b[1]-1.96*se[1]<=0<=b[1]+1.96*se[1] else 'OUTSIDE'}")
print(f"  MDE {1.96*se[1]:.1f} vs {pred:.1f} -> {'POWERED' if 1.96*se[1]<pred else 'UNDERPOWERED'}")
print(f"\n  {'implied-sigma quintile':<24}{'n':>6}{'mean implied':>14}{'REALISED sd(dev)':>18}{'+-':>7}")
q=pd.qcut(M.sig,5,labels=False)
for i in range(5):
    s=M[q==i]
    print(f"  {i+1:<24}{len(s):>6}{s.sig.mean():>14.3f}{s.dev.std():>18.3f}"
          f"{s.dev.std()/np.sqrt(2*len(s)):>7.3f}")
print(f"\n  corr(implied sigma, |dev|) = {M.sig.corr(M.dev.abs()):+.4f}")
