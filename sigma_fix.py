import sqlite3,warnings,numpy as np,pandas as pd
from scipy.stats import norm
from scipy.optimize import minimize
warnings.filterwarnings("ignore")
SP="/tmp/claude-1000/-home-dpope/4fa2e81b-35e9-49e8-92da-7bffe4f69700/scratchpad/"
c=sqlite3.connect("file:/mnt/c/NBA2/Kalshi/data/kalshi_nba_totals.sqlite?mode=ro",uri=True)
m=pd.read_sql("SELECT event_ticker,game_date,floor_strike,pregame_mid,"
              "pregame_yes_bid,pregame_yes_ask FROM markets",c); c.close()
for col in ["floor_strike","pregame_mid","pregame_yes_bid","pregame_yes_ask"]:
    m[col]=pd.to_numeric(m[col],errors="coerce")
m["p"]=m.pregame_mid/100; m["bid"]=m.pregame_yes_bid/100; m["ask"]=m.pregame_yes_ask/100
m=m.dropna(subset=["floor_strike","p","bid","ask"])
m=m[(m.p>0.03)&(m.p<0.97)&m.floor_strike.between(150,300)&(m.ask>=m.bid)]
print("SPREAD BY MONEYNESS — where the quote width actually sits")
m["w"]=m.ask-m.bid
b=pd.cut(m.p,[0,.15,.35,.65,.85,1.0])
print("  ",{str(k):round(v,4) for k,v in m.groupby(b).w.mean().items()})

def ols_fit(K,p):
    z=norm.ppf(1-p); A=np.column_stack([np.ones(len(K)),K])
    b,*_=np.linalg.lstsq(A,z,rcond=None)
    return (1/b[1], -b[0]/b[1]) if b[1]>1e-9 else (np.nan,np.nan)
def wls_fit(K,p,w):
    """weight each rung by the PRECISION of its z: var(z) ~ (w/2)^2 / phi(z)^2"""
    z=norm.ppf(1-p); ww=np.maximum(w,0.005)/2.0
    om=(norm.pdf(z)/ww)**2
    A=np.column_stack([np.ones(len(K)),K]); W=np.diag(om)
    try: b=np.linalg.solve(A.T@W@A,A.T@W@z)
    except Exception: return np.nan,np.nan
    return (1/b[1], -b[0]/b[1]) if b[1]>1e-9 else (np.nan,np.nan)
def iv_fit(K,bid,ask,s0,m0):
    """treat [bid,ask] as a BAND: penalise only excursions outside it"""
    def loss(th):
        mu,ls=th; s=np.exp(ls)
        pm=1-norm.cdf((K-mu)/s)
        return np.sum(np.maximum(0,pm-ask)**2+np.maximum(0,bid-pm)**2)
    if not np.isfinite(s0) or not np.isfinite(m0): return np.nan,np.nan
    r=minimize(loss,[m0,np.log(max(s0,5))],method="Nelder-Mead",
               options=dict(maxiter=800,xatol=1e-4,fatol=1e-10))
    mu,s=r.x[0],np.exp(r.x[1])
    return (s,mu) if r.success or True else (np.nan,np.nan)

rows=[]
for ev,g in m.groupby("event_ticker"):
    g=g.drop_duplicates("floor_strike").sort_values("floor_strike")
    if len(g)<5: continue
    K,p,bid,ask,w=g.floor_strike.values,g.p.values,g.bid.values,g.ask.values,g.w.values
    so,mo=ols_fit(K,p); sw,mw=wls_fit(K,p,w)
    sb,_=ols_fit(K,np.clip(bid,.001,.999)); sa,_=ols_fit(K,np.clip(ask,.001,.999))
    si,mi=iv_fit(K,bid,ask,so,mo)
    rows.append((ev,g.game_date.iloc[0],len(K),w.mean(),so,mo,sw,si,mi,sb,sa))
S=pd.DataFrame(rows,columns=["ev","date","nrung","sprd","sig_ols","mu_ols",
                             "sig_wls","sig_iv","mu_iv","sig_bid","sig_ask"])
for c_ in ["sig_ols","sig_wls","sig_iv"]: S.loc[~S[c_].between(8,40),c_]=np.nan
S=S.dropna(subset=["sig_ols","sig_wls","sig_iv"])
print(f"\nfitted {len(S):,} ladders with all three estimators\n")
print(f"  {'estimator':<12}{'mean':>8}{'sd':>8}{'corr with QUOTE WIDTH':>24}")
for lab,c_ in [("OLS (old)","sig_ols"),("WLS","sig_wls"),("INTERVAL","sig_iv")]:
    print(f"  {lab:<12}{S[c_].mean():>8.3f}{S[c_].std():>8.3f}{S[c_].corr(S.sprd):>24.4f}")
print(f"\n  bid-only sigma {S.sig_bid.mean():.3f}   ask-only sigma {S.sig_ask.mean():.3f}"
      f"   gap {S.sig_ask.mean()-S.sig_bid.mean():+.3f}")
for lab,c_ in [("OLS","sig_ols"),("WLS","sig_wls"),("INTERVAL","sig_iv")]:
    X=np.column_stack([np.ones(len(S)),S.sprd]); y=S[c_].values
    b,*_=np.linalg.lstsq(X,y,rcond=None); r=y-X@b
    print(f"  {lab:<9} sigma ~ spread: coef {b[1]:+8.2f}  R2 {1-r.var()/y.var():.4f}")
S.to_csv(SP+"sigma_fixed.csv",index=False)
