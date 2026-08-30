import sqlite3,warnings,numpy as np,pandas as pd
from scipy.stats import norm
from scipy.optimize import minimize
warnings.filterwarnings("ignore")
SP="/tmp/claude-1000/-home-dpope/4fa2e81b-35e9-49e8-92da-7bffe4f69700/scratchpad/"
c=sqlite3.connect("file:/mnt/c/NBA2/Kalshi/data/kalshi_nba_totals.sqlite?mode=ro",uri=True)
m=pd.read_sql("SELECT event_ticker,game_date,floor_strike,pregame_yes_bid,pregame_yes_ask,"
              "close_yes_bid,close_yes_ask,volume,open_interest FROM markets",c); c.close()
for col in ["floor_strike","pregame_yes_bid","pregame_yes_ask","close_yes_bid",
            "close_yes_ask","volume","open_interest"]:
    m[col]=pd.to_numeric(m[col],errors="coerce")
def prep(tag):
    x=m.copy(); x["bid"]=x[f"{tag}_yes_bid"]/100; x["ask"]=x[f"{tag}_yes_ask"]/100
    x=x.dropna(subset=["floor_strike","bid","ask"])
    x=x[(x.ask>=x.bid)&x.floor_strike.between(150,300)]
    x["mid"]=(x.bid+x.ask)/2; x["w"]=x.ask-x.bid
    return x[(x.mid>0.02)&(x.mid<0.98)]
def wls(K,mid,w):
    z=norm.ppf(1-mid); ww=np.maximum(w,0.005)/2
    om=(norm.pdf(z)/ww)**2
    A=np.column_stack([np.ones(len(K)),K])
    try: b=np.linalg.solve(A.T@(A*om[:,None]),A.T@(z*om))
    except Exception: return np.nan,np.nan
    return ((-b[0]/b[1]),(1/b[1])) if b[1]>1e-9 else (np.nan,np.nan)
def interval(K,bid,ask,mu0,s0):
    def loss(th):
        mu,ls=th; s=np.exp(ls); pm=1-norm.cdf((K-mu)/s)
        return np.sum(np.maximum(0,pm-ask)**2+np.maximum(0,bid-pm)**2)
    if not (np.isfinite(mu0) and np.isfinite(s0)): mu0,s0=float(np.mean(K)),18.0
    r=minimize(loss,[mu0,np.log(max(s0,6))],method="Nelder-Mead",
               options=dict(maxiter=1200,xatol=1e-5,fatol=1e-12))
    return r.x[0],np.exp(r.x[1]),r.fun
rows=[];rung=[]
for tag in ["pregame"]:
    X=prep(tag)
    for ev,g in X.groupby("event_ticker"):
        g=g.drop_duplicates("floor_strike").sort_values("floor_strike")
        if len(g)<6: continue
        K,bid,ask,mid,w=(g.floor_strike.values,g.bid.values,g.ask.values,g.mid.values,g.w.values)
        mu_w,s_w=wls(K,mid,w)
        mu_i,s_i,fun=interval(K,bid,ask,mu_w,s_w)
        if not (8<s_w<40 and 8<s_i<40 and 150<mu_w<300 and 150<mu_i<300): continue
        pw=1-norm.cdf((K-mu_w)/s_w); pi=1-norm.cdf((K-mu_i)/s_i)
        ew=mid-pw
        # excursion outside the quoted band (spread-aware error)
        exc_w=np.maximum(0,pw-ask)+np.maximum(0,bid-pw)
        exc_i=np.maximum(0,pi-ask)+np.maximum(0,bid-pi)
        rows.append(dict(ev=ev,date=g.game_date.iloc[0],n=len(K),span=K.max()-K.min(),
            wbar=w.mean(),vol=g.volume.sum(),mu_w=mu_w,s_w=s_w,mu_i=mu_i,s_i=s_i,
            mae=np.abs(ew).mean(),rmse=np.sqrt((ew**2).mean()),maxe=np.abs(ew).max(),
            exc_w=exc_w.mean(),exc_i=exc_i.mean(),inband_w=(exc_w<=0).mean()))
        for j in range(len(K)):
            rung.append((ev,K[j],(K[j]-mu_w)/s_w,mid[j],pw[j],ew[j],w[j],bid[j],ask[j],exc_w[j]))
L=pd.DataFrame(rows); Rg=pd.DataFrame(rung,columns=["ev","K","z","mid","pmod","e","w","bid","ask","exc"])
print(f"A1/A2 — LADDERS FITTED: {len(L):,}   rungs {len(Rg):,}")
print(f"  rungs/game median {L.n.median():.0f}  span median {L.span.median():.0f} pts"
      f"  mean quote width {L.wbar.mean():.4f}")
print(f"\n  {'param':<10}{'WLS mean':>10}{'WLS sd':>9}{'INT mean':>10}{'INT sd':>9}")
print(f"  {'mu':<10}{L.mu_w.mean():>10.3f}{L.mu_w.std():>9.3f}{L.mu_i.mean():>10.3f}{L.mu_i.std():>9.3f}")
print(f"  {'sigma':<10}{L.s_w.mean():>10.3f}{L.s_w.std():>9.3f}{L.s_i.mean():>10.3f}{L.s_i.std():>9.3f}")

print("\nA2 — DOES ONE (mu,sigma) REPRODUCE THE LADDER?  (probability points, NOT R2)")
print(f"  per-rung |error| vs mid : MAE {Rg.e.abs().mean()*100:.3f}c   RMSE {np.sqrt((Rg.e**2).mean())*100:.3f}c"
      f"   max {Rg.e.abs().max()*100:.2f}c")
print(f"  per-game max|error|     : median {L.maxe.median()*100:.3f}c   p90 {L.maxe.quantile(.9)*100:.3f}c")
print(f"  SPREAD-AWARE: rungs where the fitted model lies INSIDE the quoted [bid,ask] band:"
      f" {100*(Rg.exc<=0).mean():.1f}%")
print(f"  mean excursion outside the band  WLS {L.exc_w.mean()*100:.3f}c   INTERVAL {L.exc_i.mean()*100:.3f}c")

print("\nA3 — WLS vs INTERVAL IDENTIFICATION")
print(f"  corr(mu_WLS, mu_INT)    = {L.mu_w.corr(L.mu_i):.6f}   mean diff {(L.mu_w-L.mu_i).mean():+.4f}"
      f"  sd diff {(L.mu_w-L.mu_i).std():.4f}")
print(f"  corr(sig_WLS, sig_INT)  = {L.s_w.corr(L.s_i):.6f}   mean diff {(L.s_w-L.s_i).mean():+.4f}"
      f"  sd diff {(L.s_w-L.s_i).std():.4f}")
L["dmu"]=L.mu_w-L.mu_i; L["dsg"]=L.s_w-L.s_i
print(f"\n  disagreement vs market conditions (corr):")
for v in ["wbar","n","span","vol"]:
    print(f"    {v:<6}  d(mu) {L.dmu.abs().corr(L[v]):+.4f}   d(sigma) {L.dsg.abs().corr(L[v]):+.4f}")
print(f"  sigma vs quote width:  WLS {L.s_w.corr(L.wbar):+.4f}   INTERVAL {L.s_i.corr(L.wbar):+.4f}")
L.to_csv(SP+"stageA_fits.csv",index=False); Rg.to_csv(SP+"stageA_rungs.csv",index=False)

print("\nA4 — RESIDUAL SHAPE ACROSS STANDARDISED STRIKE DISTANCE (is Normal the engine?)")
b=pd.cut(Rg.z,[-9,-2,-1.25,-0.6,0.6,1.25,2,9],
         labels=["far under","mod under","near under","centre","near over","mod over","far over"])
t=Rg.groupby(b).agg(n=("e","size"),mkt=("mid","mean"),mod=("pmod","mean"),
                    err=("e","mean"),abserr=("e",lambda s:s.abs().mean()))
t["err_c"]=t.err*100; t["abs_c"]=t.abserr*100
print(t[["n","mkt","mod","err_c","abs_c"]].round(4).to_string())
print("  err_c > 0 means the MARKET prices the rung ABOVE the fitted normal")
