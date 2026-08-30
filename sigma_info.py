import sys; sys.path.insert(0,"/home/dpope/projects/nba_entropy_replication")
import warnings,numpy as np,pandas as pd; warnings.filterwarnings("ignore")
from prepare_data import read_master, season_label
SP="/tmp/claude-1000/-home-dpope/4fa2e81b-35e9-49e8-92da-7bffe4f69700/scratchpad/"
raw=read_master(verbose=False); raw["season"]=season_label(raw).astype(str)
n=lambda c: pd.to_numeric(raw[c],errors="coerce")
d=raw.copy(); d["spread"]=n("CLOSING SPREAD_H")
d["restH"]=n("TEAM\nREST DAYS_H"); d["restR"]=n("TEAM\nREST DAYS_R")
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
M["b2b"]=(M.restmin<=1).astype(float)
M=M.dropna(subset=["t3r","pace","aspread","restmin","doy","sprd"])
print(f"n = {len(M):,}\n")
CLEAN=["mu","pace","t3r","aspread","restmin","b2b","doy"]
def ols(y,cols,X_):
    X=np.column_stack([np.ones(len(X_))]+[X_[c].values for c in cols])
    b,*_=np.linalg.lstsq(X,y,rcond=None); r=y-X@b
    se=np.sqrt(np.diag((r@r/(len(y)-len(cols)-1))*np.linalg.pinv(X.T@X)))
    return b,se,r,X
# 1. purge the quote-width artifact from implied sigma
b,se,r,_=ols(M.sig.values,["sprd"],M)
M["sig_clean"]=M.sig-b[1]*(M.sprd-M.sprd.mean())
print(f"sigma ~ quoted spread: coef {b[1]:+.2f} (t={b[1]/se[1]:+.1f}), R2 "
      f"{1-r.var()/M.sig.var():.4f}  -> purged")
print(f"  sd(implied sigma) {M.sig.std():.3f} -> sd(cleaned) {M.sig_clean.std():.3f}")
# 2. the MAKER-MODEL component: sigma predicted by real inputs
b2,se2,r2,X2=ols(M.sig_clean.values,CLEAN,M)
M["sig_hat"]=X2@b2
print(f"  clean-variable model on cleaned sigma: R2 {1-r2.var()/M.sig_clean.var():.4f}"
      f"   sd(fitted) {M.sig_hat.std():.4f}")
print("\nDOES ANY OF IT PREDICT HOW WIDE THE GAME ACTUALLY LANDS?")
print(f"  {'predictor':<26}{'coef':>10}{'t':>8}{'95% CI':>22}{'informative=2sig':>18}{'verdict':>12}")
tgt=2*M.sig.mean()
for lab,col in [("raw implied sigma","sig"),("spread-CLEANED sigma","sig_clean"),
                ("maker-MODEL component","sig_hat")]:
    bb,ss,_,_=ols((M.dev**2).values,[col,"close"],M)
    lo,hi=bb[1]-1.96*ss[1],bb[1]+1.96*ss[1]
    v=("INFORMATIVE" if lo>0 and hi>=tgt*0.5 else
       "NULL" if lo<=0<=hi else "NEGATIVE")
    print(f"  {lab:<26}{bb[1]:>10.2f}{bb[1]/ss[1]:>8.2f}   [{lo:>+8.1f},{hi:>+8.1f}]"
          f"{tgt:>18.1f}{v:>12}")
print(f"\n  (informative would be ~{tgt:.0f}; pure noise 0)")
print("\nREVISED LINK 5/6 COEFFICIENTS, now controlling for quote width")
for lab,cols in [("Link 5 pace (was +0.098)",["pace","mu","sprd"]),
                 ("Link 6 3PA  (was +3.259)",["t3r","pace","mu","sprd"])]:
    bb,ss,_,_=ols(M.sig.values,cols,M)
    print(f"  {lab:<28}{cols[0]:<6}{bb[1]:+9.4f} (t={bb[1]/ss[1]:+5.2f})"
          f"  95% CI [{bb[1]-1.96*ss[1]:+.4f}, {bb[1]+1.96*ss[1]:+.4f}]")
print("   Poisson pace benchmark +0.0911 ; corrected 3PA benchmark +4.87")
